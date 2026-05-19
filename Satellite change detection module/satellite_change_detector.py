"""Satellite change-detection prototype for project-completion scoring.

This script trains a lightweight paired-image segmentation model on a change
detection dataset such as LEVIR-CD or OSCD. It is intentionally small and fast
to iterate on locally:

- trains a compact CNN on paired before/after images
- evaluates binary change masks with IoU/Dice
- exports a percent-complete style score from the predicted change mask
- includes a smoke-test mode that generates synthetic samples on disk

Example usage:

    python satellite_change_detector.py \
        --a-dir C:/data/LEVIR-CD/train/A \
        --b-dir C:/data/LEVIR-CD/train/B \
        --mask-dir C:/data/LEVIR-CD/train/label \
        --epochs 5 --batch-size 4 --image-size 128

    python satellite_change_detector.py --smoke-test
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw
from torch import nn
from torch.utils.data import DataLoader, Dataset, random_split

from dataset_loader import download_and_prepare, download_from_preset, list_dataset_presets, resolve_dataset_paths


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def find_matching_stems(a_dir: Path, b_dir: Path, mask_dir: Path) -> list[str]:
    def stems(directory: Path) -> set[str]:
        return {
            path.stem
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        }

    common = sorted(stems(a_dir) & stems(b_dir) & stems(mask_dir))
    return common


def _first_existing(directory: Path, stem: str) -> Optional[Path]:
    for ext in IMAGE_EXTENSIONS:
        candidate = directory / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    for path in directory.iterdir():
        if path.is_file() and path.stem == stem and path.suffix.lower() in IMAGE_EXTENSIONS:
            return path
    return None


def _load_rgb(path: Path, image_size: int) -> torch.Tensor:
    image = Image.open(path).convert("RGB")
    if image.size != (image_size, image_size):
        image = image.resize((image_size, image_size), Image.BILINEAR)
    array = np.asarray(image, dtype=np.float32) / 255.0
    return torch.from_numpy(array).permute(2, 0, 1)


def _load_mask(path: Path, image_size: int) -> torch.Tensor:
    mask = Image.open(path).convert("L")
    if mask.size != (image_size, image_size):
        mask = mask.resize((image_size, image_size), Image.NEAREST)
    array = np.asarray(mask, dtype=np.float32)
    array = (array > 0).astype(np.float32)
    return torch.from_numpy(array).unsqueeze(0)


class ChangePairDataset(Dataset):
    def __init__(self, a_dir: Path, b_dir: Path, mask_dir: Path, image_size: int = 128, limit: Optional[int] = None):
        self.a_dir = Path(a_dir)
        self.b_dir = Path(b_dir)
        self.mask_dir = Path(mask_dir)
        self.image_size = image_size

        if not self.a_dir.exists() or not self.b_dir.exists() or not self.mask_dir.exists():
            raise FileNotFoundError(
                f"Expected directories to exist: a={self.a_dir}, b={self.b_dir}, mask={self.mask_dir}"
            )

        stems = find_matching_stems(self.a_dir, self.b_dir, self.mask_dir)
        if limit is not None:
            stems = stems[:limit]
        self.stems = stems

        if not self.stems:
            raise ValueError(
                "No matching image stems were found. Make sure the before/after/mask folders share filenames."
            )

    def __len__(self) -> int:
        return len(self.stems)

    def __getitem__(self, index: int):
        stem = self.stems[index]
        a_path = _first_existing(self.a_dir, stem)
        b_path = _first_existing(self.b_dir, stem)
        mask_path = _first_existing(self.mask_dir, stem)

        if a_path is None or b_path is None or mask_path is None:
            raise FileNotFoundError(f"Missing sample files for stem {stem}")

        before = _load_rgb(a_path, self.image_size)
        after = _load_rgb(b_path, self.image_size)
        mask = _load_mask(mask_path, self.image_size)

        return {
            "before": before,
            "after": after,
            "mask": mask,
            "stem": stem,
        }


class SmallChangeNet(nn.Module):
    def __init__(self, in_channels: int = 6, base_channels: int = 32):
        super().__init__()
        c1 = base_channels
        c2 = base_channels * 2
        c3 = base_channels * 4

        self.encoder = nn.Sequential(
            nn.Conv2d(in_channels, c1, kernel_size=3, padding=1),
            nn.BatchNorm2d(c1),
            nn.ReLU(inplace=True),
            nn.Conv2d(c1, c1, kernel_size=3, padding=1),
            nn.BatchNorm2d(c1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(c1, c2, kernel_size=3, padding=1),
            nn.BatchNorm2d(c2),
            nn.ReLU(inplace=True),
            nn.Conv2d(c2, c2, kernel_size=3, padding=1),
            nn.BatchNorm2d(c2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(c2, c3, kernel_size=3, padding=1),
            nn.BatchNorm2d(c3),
            nn.ReLU(inplace=True),
            nn.Conv2d(c3, c3, kernel_size=3, padding=1),
            nn.BatchNorm2d(c3),
            nn.ReLU(inplace=True),
        )

        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(c3, c2, kernel_size=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(c2, c2, kernel_size=3, padding=1),
            nn.BatchNorm2d(c2),
            nn.ReLU(inplace=True),
            nn.ConvTranspose2d(c2, c1, kernel_size=2, stride=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(c1, c1, kernel_size=3, padding=1),
            nn.BatchNorm2d(c1),
            nn.ReLU(inplace=True),
            nn.Conv2d(c1, 1, kernel_size=1),
        )

    def forward(self, before: torch.Tensor, after: torch.Tensor) -> torch.Tensor:
        x = torch.cat([before, after], dim=1)
        x = self.encoder(x)
        return self.decoder(x)


def dice_loss(logits: torch.Tensor, targets: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    probs = probs.flatten(1)
    targets = targets.flatten(1)
    intersection = (probs * targets).sum(dim=1)
    union = probs.sum(dim=1) + targets.sum(dim=1)
    dice = (2.0 * intersection + eps) / (union + eps)
    return 1.0 - dice.mean()


@dataclass
class Metrics:
    loss: float
    iou: float
    dice: float
    pixel_accuracy: float
    percent_complete: float


def compute_batch_metrics(logits: torch.Tensor, targets: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    probs = torch.sigmoid(logits)
    preds = (probs >= 0.5).float()
    targets = (targets >= 0.5).float()

    intersection = (preds * targets).sum(dim=(1, 2, 3))
    pred_sum = preds.sum(dim=(1, 2, 3))
    target_sum = targets.sum(dim=(1, 2, 3))
    union = pred_sum + target_sum - intersection

    iou = torch.where(union > 0, intersection / torch.clamp(union, min=1.0), torch.ones_like(union))
    dice = torch.where(
        (pred_sum + target_sum) > 0,
        (2.0 * intersection) / torch.clamp(pred_sum + target_sum, min=1.0),
        torch.ones_like(union),
    )
    pixel_accuracy = (preds == targets).float().mean(dim=(1, 2, 3))
    percent_complete = preds.mean(dim=(1, 2, 3)) * 100.0
    return iou, dice, pixel_accuracy, percent_complete


def run_epoch(model: nn.Module, loader: DataLoader, optimizer: Optional[torch.optim.Optimizer], device: torch.device) -> Metrics:
    training = optimizer is not None
    model.train(training)

    total_loss = 0.0
    total_iou = 0.0
    total_dice = 0.0
    total_accuracy = 0.0
    total_percent = 0.0
    total_items = 0

    bce = nn.BCEWithLogitsLoss()

    for batch in loader:
        before = batch["before"].to(device)
        after = batch["after"].to(device)
        mask = batch["mask"].to(device)

        if training:
            optimizer.zero_grad(set_to_none=True)

        logits = model(before, after)
        loss = 0.6 * bce(logits, mask) + 0.4 * dice_loss(logits, mask)

        if training:
            loss.backward()
            optimizer.step()

        batch_size = before.shape[0]
        iou, dice, accuracy, percent = compute_batch_metrics(logits.detach(), mask.detach())

        total_loss += loss.item() * batch_size
        total_iou += iou.sum().item()
        total_dice += dice.sum().item()
        total_accuracy += accuracy.sum().item()
        total_percent += percent.sum().item()
        total_items += batch_size

    if total_items == 0:
        return Metrics(loss=0.0, iou=0.0, dice=0.0, pixel_accuracy=0.0, percent_complete=0.0)

    return Metrics(
        loss=total_loss / total_items,
        iou=total_iou / total_items,
        dice=total_dice / total_items,
        pixel_accuracy=total_accuracy / total_items,
        percent_complete=total_percent / total_items,
    )


def train_model(
    dataset: Dataset,
    epochs: int,
    batch_size: int,
    lr: float,
    val_ratio: float,
    seed: int,
    device: torch.device,
) -> Tuple[nn.Module, Metrics, Metrics]:
    val_size = max(1, int(len(dataset) * val_ratio))
    train_size = max(1, len(dataset) - val_size)
    if train_size + val_size > len(dataset):
        val_size = len(dataset) - train_size
    if train_size <= 0:
        train_size = len(dataset) - 1
        val_size = 1

    generator = torch.Generator().manual_seed(seed)
    train_dataset, val_dataset = random_split(dataset, [train_size, len(dataset) - train_size], generator=generator)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    model = SmallChangeNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

    best_state = None
    best_val_iou = -1.0
    last_train_metrics = Metrics(0.0, 0.0, 0.0, 0.0, 0.0)
    last_val_metrics = Metrics(0.0, 0.0, 0.0, 0.0, 0.0)

    for epoch in range(1, epochs + 1):
        last_train_metrics = run_epoch(model, train_loader, optimizer, device)
        last_val_metrics = run_epoch(model, val_loader, None, device)

        print(
            f"Epoch {epoch:02d}/{epochs} | "
            f"train loss {last_train_metrics.loss:.4f} iou {last_train_metrics.iou:.4f} dice {last_train_metrics.dice:.4f} | "
            f"val loss {last_val_metrics.loss:.4f} iou {last_val_metrics.iou:.4f} dice {last_val_metrics.dice:.4f}"
        )

        if last_val_metrics.iou > best_val_iou:
            best_val_iou = last_val_metrics.iou
            best_state = {key: value.cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    return model, last_train_metrics, last_val_metrics


def predict_sample(model: nn.Module, sample: dict, device: torch.device) -> dict:
    model.eval()
    before = sample["before"].unsqueeze(0).to(device)
    after = sample["after"].unsqueeze(0).to(device)
    mask = sample["mask"].unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(before, after)
        probs = torch.sigmoid(logits)
        pred = (probs >= 0.5).float()

    iou, dice, accuracy, percent = compute_batch_metrics(logits, mask)
    return {
        "stem": sample["stem"],
        "iou": float(iou.item()),
        "dice": float(dice.item()),
        "pixel_accuracy": float(accuracy.item()),
        "percent_complete": float(percent.item()),
        "predicted_change_fraction": float(pred.mean().item()),
        "actual_change_fraction": float(mask.mean().item()),
    }


def _draw_rectangles(draw: ImageDraw.ImageDraw, rectangles: Sequence[Tuple[int, int, int, int]], fill: Tuple[int, int, int]) -> None:
    for x1, y1, x2, y2 in rectangles:
        draw.rectangle((x1, y1, x2, y2), fill=fill)


def create_smoke_dataset(root: Path, image_size: int = 128, samples: int = 12, seed: int = 7) -> Tuple[Path, Path, Path]:
    rng = random.Random(seed)
    if root.exists():
        shutil.rmtree(root)
    a_dir = root / "before"
    b_dir = root / "after"
    mask_dir = root / "mask"
    a_dir.mkdir(parents=True, exist_ok=True)
    b_dir.mkdir(parents=True, exist_ok=True)
    mask_dir.mkdir(parents=True, exist_ok=True)

    for index in range(samples):
        base = Image.new("RGB", (image_size, image_size), (30, 35, 40))
        after = base.copy()
        mask = Image.new("L", (image_size, image_size), 0)

        base_draw = ImageDraw.Draw(base)
        after_draw = ImageDraw.Draw(after)
        mask_draw = ImageDraw.Draw(mask)

        # Existing structures present in both time steps.
        for _ in range(3):
            x1 = rng.randint(8, image_size // 2)
            y1 = rng.randint(8, image_size // 2)
            w = rng.randint(14, 28)
            h = rng.randint(14, 28)
            rect = (x1, y1, min(image_size - 1, x1 + w), min(image_size - 1, y1 + h))
            _draw_rectangles(base_draw, [rect], fill=(70, 90, 110))
            _draw_rectangles(after_draw, [rect], fill=(70, 90, 110))

        # New construction appearing in the after image only.
        for _ in range(2):
            x1 = rng.randint(image_size // 3, image_size - 40)
            y1 = rng.randint(image_size // 3, image_size - 40)
            w = rng.randint(12, 26)
            h = rng.randint(12, 26)
            rect = (x1, y1, min(image_size - 2, x1 + w), min(image_size - 2, y1 + h))
            _draw_rectangles(after_draw, [rect], fill=(180, 150, 80))
            _draw_rectangles(mask_draw, [rect], fill=255)

        base.save(a_dir / f"sample_{index:03d}.png")
        after.save(b_dir / f"sample_{index:03d}.png")
        mask.save(mask_dir / f"sample_{index:03d}.png")

    return a_dir, b_dir, mask_dir


def save_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fast satellite change-detection prototype.")
    parser.add_argument("--a-dir", type=Path, help="Directory with before images")
    parser.add_argument("--b-dir", type=Path, help="Directory with after images")
    parser.add_argument("--mask-dir", type=Path, help="Directory with binary change masks")
    parser.add_argument(
        "--dataset-root",
        type=Path,
        help="Root folder of an already extracted LEVIR-CD or OSCD dataset",
    )
    parser.add_argument(
        "--dataset-name",
        choices=["levir", "levir-cd", "oscd"],
        default="levir-cd",
        help="Dataset layout preset used with --dataset-root or --download-url",
    )
    parser.add_argument(
        "--dataset-preset",
        choices=["levir-cd-public", "oscd-public"],
        default="levir-cd-public",
        help="Dataset preset that downloads and prepares a known public mirror",
    )
    parser.add_argument(
        "--preset-url",
        type=str,
        help="Override URL for --dataset-preset (useful while settling the final mirror)",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="Print available dataset presets and exit",
    )
    parser.add_argument(
        "--download-url",
        type=str,
        help="Public ZIP URL for a LEVIR-CD or OSCD mirror to download before training",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("outputs") / "satellite_dataset_cache",
        help="Where downloaded archives and extracted data are stored",
    )
    parser.add_argument(
        "--overwrite-download",
        action="store_true",
        help="Re-download and re-extract even if cached files already exist",
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--val-ratio", type=float, default=0.25)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of samples loaded from disk")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs") / "satellite_change_prototype")
    parser.add_argument("--checkpoint-name", type=str, default="satellite_change_smallnet.pt")
    parser.add_argument("--smoke-test", action="store_true", help="Generate synthetic samples and run a quick local training pass")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    set_seed(args.seed)

    if args.list_presets:
        print("Available dataset presets:")
        for preset in list_dataset_presets():
            print(f"  - {preset.preset_name}: {preset.description} ({preset.dataset_name})")
            print(f"      URL from env var: {preset.env_var}")
        return

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.smoke_test:
        smoke_root = output_dir / "smoke_data"
        a_dir, b_dir, mask_dir = create_smoke_dataset(smoke_root, image_size=args.image_size, samples=12, seed=args.seed)
        print(f"Smoke-test dataset created at {smoke_root}")
    elif args.dataset_preset and args.a_dir is None and args.b_dir is None and args.mask_dir is None and args.dataset_root is None and args.download_url is None:
        prepared = download_from_preset(
            preset_name=args.dataset_preset,
            cache_dir=args.cache_dir,
            overwrite=args.overwrite_download,
            preset_url=args.preset_url,
        )
        a_dir, b_dir, mask_dir = prepared.a_dir, prepared.b_dir, prepared.mask_dir
        print(f"Prepared dataset preset {args.dataset_preset} under {prepared.root}")
    elif args.download_url:
        prepared = download_and_prepare(
            url=args.download_url,
            dataset_name=args.dataset_name,
            cache_dir=args.cache_dir,
            overwrite=args.overwrite_download,
        )
        a_dir, b_dir, mask_dir = prepared.a_dir, prepared.b_dir, prepared.mask_dir
        print(f"Downloaded and prepared {args.dataset_name} under {prepared.root}")
    elif args.dataset_root:
        prepared = resolve_dataset_paths(args.dataset_root, args.dataset_name)
        a_dir, b_dir, mask_dir = prepared.a_dir, prepared.b_dir, prepared.mask_dir
        print(f"Resolved {args.dataset_name} dataset from {prepared.root}")
    else:
        if args.a_dir is None or args.b_dir is None or args.mask_dir is None:
            raise SystemExit(
                "Provide --a-dir, --b-dir, and --mask-dir, or run with --smoke-test, --dataset-root, --download-url, or --dataset-preset."
            )
        a_dir, b_dir, mask_dir = args.a_dir, args.b_dir, args.mask_dir

    dataset = ChangePairDataset(a_dir, b_dir, mask_dir, image_size=args.image_size, limit=args.limit)
    print(f"Loaded {len(dataset)} paired samples")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model, train_metrics, val_metrics = train_model(
        dataset=dataset,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        val_ratio=args.val_ratio,
        seed=args.seed,
        device=device,
    )

    sample = dataset[0]
    sample_metrics = predict_sample(model, sample, device)

    checkpoint_path = output_dir / args.checkpoint_name
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "image_size": args.image_size,
            "checkpoint_name": args.checkpoint_name,
        },
        checkpoint_path,
    )

    report = {
        "dataset": {
            "a_dir": str(a_dir),
            "b_dir": str(b_dir),
            "mask_dir": str(mask_dir),
            "samples": len(dataset),
            "image_size": args.image_size,
        },
        "training": {
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "lr": args.lr,
            "train_metrics": train_metrics.__dict__,
            "val_metrics": val_metrics.__dict__,
        },
        "sample_prediction": sample_metrics,
        "checkpoint_path": str(checkpoint_path),
        "notes": [
            "percent_complete is the fraction of changed pixels in the predicted mask; later this can be normalized by a project footprint polygon",
            "for LEVIR-CD or OSCD, point the three directory arguments at the paired before/after/mask folders",
        ],
    }
    report_path = output_dir / "satellite_change_report.json"
    save_report(report_path, report)

    print("\nSatellite change-detection prototype complete")
    print(f"  Train IoU: {train_metrics.iou:.4f} | Val IoU: {val_metrics.iou:.4f}")
    print(f"  Sample percent complete: {sample_metrics['percent_complete']:.2f}%")
    print(f"  Saved checkpoint: {checkpoint_path}")
    print(f"  Saved report: {report_path}")


if __name__ == "__main__":
    main()