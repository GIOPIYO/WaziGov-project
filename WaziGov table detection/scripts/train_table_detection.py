"""
WaziGov Table Detection - Fine-tune Table Transformer (DETR-based)
===================================================================
Fine-tunes Microsoft's pretrained Table Transformer on WaziGov data.

Model: microsoft/table-transformer-detection (for table detection)
Architecture: DETR (DEtection TRansformer)
Pretrained on: PubTables-1M dataset

Usage:
    python scripts/train_table_detection.py --data-dir data/ --epochs 50 --batch-size 2
"""

import os
import sys
import argparse
import json
import random
from pathlib import Path
from datetime import datetime

import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import xml.etree.ElementTree as ET

from transformers import (
    DetrImageProcessor,
    TableTransformerForObjectDetection,
    DetrConfig,
)
from transformers import TrainingArguments, Trainer


# ============================================================================
# Dataset
# ============================================================================

class WaziGovTableDataset(Dataset):
    """
    Loads page images + PASCAL VOC annotations for table detection.
    Compatible with Table Transformer (DETR-based) model.
    """

    LABEL2ID = {"table": 0, "table_rotated": 1}
    ID2LABEL = {0: "table", 1: "table_rotated"}

    def __init__(self, image_dir, annotation_dir, processor, transform=None):
        self.image_dir = Path(image_dir)
        self.annotation_dir = Path(annotation_dir)
        self.processor = processor
        self.transform = transform

        # Find all annotation XMLs that have matching images
        self.samples = []
        for xml_file in sorted(self.annotation_dir.glob("*.xml")):
            tree = ET.parse(xml_file)
            root = tree.getroot()
            img_filename = root.find("filename").text

            # Try to find the image
            img_path = self.image_dir / img_filename
            if not img_path.exists():
                # Try without the UUID prefix
                for f in self.image_dir.iterdir():
                    if f.name.endswith(img_filename) or img_filename.endswith(f.name):
                        img_path = f
                        break

            if img_path.exists():
                self.samples.append((img_path, xml_file))
            else:
                print(f"  Warning: Image not found for {xml_file.name}, skipping")

        print(f"  Loaded {len(self.samples)} samples from {annotation_dir}")

    def __len__(self):
        return len(self.samples)

    def _parse_voc_xml(self, xml_path):
        """Parse PASCAL VOC annotation XML."""
        tree = ET.parse(xml_path)
        root = tree.getroot()

        size = root.find("size")
        width = int(size.find("width").text)
        height = int(size.find("height").text)

        boxes = []
        labels = []

        for obj in root.findall("object"):
            label = obj.find("name").text
            if label not in self.LABEL2ID:
                continue

            bbox = obj.find("bndbox")
            xmin = float(bbox.find("xmin").text)
            ymin = float(bbox.find("ymin").text)
            xmax = float(bbox.find("xmax").text)
            ymax = float(bbox.find("ymax").text)

            # DETR expects [center_x, center_y, width, height] normalized to [0, 1]
            cx = (xmin + xmax) / 2.0 / width
            cy = (ymin + ymax) / 2.0 / height
            w = (xmax - xmin) / width
            h = (ymax - ymin) / height

            boxes.append([cx, cy, w, h])
            labels.append(self.LABEL2ID[label])

        return {
            "boxes": boxes,
            "labels": labels,
            "orig_size": [height, width],
        }

    def __getitem__(self, idx):
        img_path, xml_path = self.samples[idx]

        # Load image
        image = Image.open(img_path).convert("RGB")

        # Parse annotations
        target = self._parse_voc_xml(xml_path)

        # Prepare DETR-format target
        target_dict = {
            "class_labels": torch.tensor(target["labels"], dtype=torch.long),
            "boxes": torch.tensor(target["boxes"], dtype=torch.float32),
        }

        # Process image with DETR processor
        encoding = self.processor(
            images=image,
            annotations=[{
                "image_id": idx,
                "annotations": [
                    {
                        "bbox": box,
                        "category_id": label,
                        "area": box[2] * box[3],  # w * h (normalized)
                        "iscrowd": 0,
                    }
                    for box, label in zip(target["boxes"], target["labels"])
                ],
            }],
            return_tensors="pt",
        )

        # Remove batch dimension
        pixel_values = encoding["pixel_values"].squeeze(0)
        labels = encoding["labels"][0]  # dict with boxes, class_labels, etc.

        return pixel_values, labels


def collate_fn(batch, processor):
    """Custom collate for DETR: pad variable-size images and build pixel masks."""
    pixel_values = [item[0] for item in batch]
    labels = [item[1] for item in batch]

    encoding = processor.pad(pixel_values, return_tensors="pt")
    return {
        "pixel_values": encoding["pixel_values"],
        "pixel_mask": encoding["pixel_mask"],
        "labels": labels,
    }


# ============================================================================
# Training
# ============================================================================

def split_dataset(dataset, val_ratio=0.2, seed=42):
    """Split dataset into train and validation sets."""
    n = len(dataset)
    indices = list(range(n))
    random.seed(seed)
    random.shuffle(indices)

    split = int(n * (1 - val_ratio))
    train_indices = indices[:split]
    val_indices = indices[split:]

    train_set = torch.utils.data.Subset(dataset, train_indices)
    val_set = torch.utils.data.Subset(dataset, val_indices)

    print(f"  Train: {len(train_set)} samples, Val: {len(val_set)} samples")
    return train_set, val_set


def split_dataset_from_files(dataset, split_dir):
    """Build train/val subsets from split text files with image stems."""
    split_dir = Path(split_dir)
    train_file = split_dir / "train.txt"
    val_file = split_dir / "val.txt"

    if not train_file.exists() or not val_file.exists():
        return None, None

    def read_stems(path):
        return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}

    train_stems = read_stems(train_file)
    val_stems = read_stems(val_file)

    stem_to_idx = {xml_path.stem: idx for idx, (_, xml_path) in enumerate(dataset.samples)}
    train_indices = sorted(stem_to_idx[s] for s in train_stems if s in stem_to_idx)
    val_indices = sorted(stem_to_idx[s] for s in val_stems if s in stem_to_idx)

    if not train_indices or not val_indices:
        return None, None

    train_set = torch.utils.data.Subset(dataset, train_indices)
    val_set = torch.utils.data.Subset(dataset, val_indices)
    print(f"  Train (split files): {len(train_set)} samples, Val (split files): {len(val_set)} samples")
    return train_set, val_set


class TableTrainer(Trainer):
    """Custom Trainer to handle DETR loss properly."""

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        pixel_values = inputs["pixel_values"]
        pixel_mask = inputs.get("pixel_mask")
        labels = inputs["labels"]

        outputs = model(pixel_values=pixel_values, pixel_mask=pixel_mask, labels=labels)
        loss = outputs.loss

        return (loss, outputs) if return_outputs else loss


def train(args):
    """Main training function."""
    print("=" * 60)
    print("WaziGov Table Detection - Fine-tuning Table Transformer")
    print("=" * 60)

    # Paths
    data_dir = Path(args.data_dir)
    images_dir = Path(args.images_dir) if args.images_dir else data_dir / "images" / "pages"
    annotations_dir = (
        Path(args.annotations_dir)
        if args.annotations_dir
        else data_dir / "annotations" / "pascal_voc"
    )
    split_dir = Path(args.split_dir) if args.split_dir else data_dir / "splits"
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\nDevice: {device}")
    if device.type == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        print(f"  VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")

    # Load pretrained model and processor
    print(f"\nLoading pretrained model: {args.model_name}")
    processor = DetrImageProcessor.from_pretrained(args.model_name)

    model = TableTransformerForObjectDetection.from_pretrained(
        args.model_name,
        num_labels=2,  # table, table_rotated
        id2label=WaziGovTableDataset.ID2LABEL,
        label2id=WaziGovTableDataset.LABEL2ID,
        ignore_mismatched_sizes=True,  # Allow resizing classification head
    )
    model.to(device)

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Total parameters: {total_params:,}")
    print(f"  Trainable parameters: {trainable_params:,}")

    # Optionally freeze backbone for few-shot fine-tuning
    if args.freeze_backbone:
        print("  Freezing backbone (ResNet-18)...")
        for param in model.model.backbone.parameters():
            param.requires_grad = False
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        print(f"  Trainable parameters after freeze: {trainable_params:,}")

    # Load dataset
    print(f"\nLoading dataset...")
    dataset = WaziGovTableDataset(
        image_dir=str(images_dir),
        annotation_dir=str(annotations_dir),
        processor=processor,
    )

    if len(dataset) == 0:
        print("ERROR: No samples found. Check your paths and annotations.")
        sys.exit(1)

    # Split into train/val (prefer proposal-compliant split files if available)
    train_dataset, val_dataset = None, None
    if not args.use_random_split:
        train_dataset, val_dataset = split_dataset_from_files(dataset, split_dir)

    if train_dataset is None or val_dataset is None:
        print("  Split files not found/usable, falling back to random split.")
        train_dataset, val_dataset = split_dataset(dataset, val_ratio=args.val_ratio)

    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        weight_decay=args.weight_decay,
        lr_scheduler_type="cosine",
        warmup_ratio=0.1,
        logging_dir=str(output_dir / "logs"),
        logging_steps=5,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        remove_unused_columns=False,
        fp16=torch.cuda.is_available(),
        dataloader_num_workers=args.num_workers,
        dataloader_pin_memory=torch.cuda.is_available(),
        report_to="none",  # Set to "tensorboard" if you want TB logging
    )

    # Trainer
    trainer = TableTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        data_collator=lambda batch: collate_fn(batch, processor),
    )

    # Train
    print(f"\nStarting training...")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch size: {args.batch_size}")
    print(f"  Learning rate: {args.learning_rate}")
    print(f"  Freeze backbone: {args.freeze_backbone}")
    print()

    train_result = trainer.train()

    # Save final model
    final_model_dir = output_dir / "final_model"
    print(f"\nSaving final model to: {final_model_dir}")
    trainer.save_model(str(final_model_dir))
    processor.save_pretrained(str(final_model_dir))

    # Save training metrics
    metrics = train_result.metrics
    metrics_path = output_dir / "training_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Training metrics saved to: {metrics_path}")

    # Evaluate
    print("\nFinal evaluation:")
    eval_metrics = trainer.evaluate()
    for k, v in eval_metrics.items():
        print(f"  {k}: {v:.4f}")

    eval_path = output_dir / "eval_metrics.json"
    with open(eval_path, "w") as f:
        json.dump(eval_metrics, f, indent=2)

    print("\n" + "=" * 60)
    print("Training complete!")
    print(f"Model saved to: {final_model_dir}")
    print("=" * 60)


# ============================================================================
# Entry point
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Fine-tune Table Transformer for WaziGov table detection"
    )
    parser.add_argument(
        "--data-dir", type=str, default="data/",
        help="Root data directory (default: data/)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="models/table_detection/",
        help="Output directory for model checkpoints (default: models/table_detection/)"
    )
    parser.add_argument(
        "--model-name", type=str,
        default="microsoft/table-transformer-detection",
        help="Pretrained model name from HuggingFace"
    )
    parser.add_argument(
        "--epochs", type=int, default=50,
        help="Number of training epochs (default: 50)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=2,
        help="Batch size (default: 2, increase if you have more VRAM)"
    )
    parser.add_argument(
        "--learning-rate", type=float, default=5e-5,
        help="Learning rate (default: 5e-5)"
    )
    parser.add_argument(
        "--weight-decay", type=float, default=0.01,
        help="Weight decay (default: 0.01)"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.2,
        help="Validation split ratio (default: 0.2)"
    )
    parser.add_argument(
        "--freeze-backbone", action="store_true",
        help="Freeze ResNet backbone (recommended for small datasets)"
    )
    parser.add_argument(
        "--num-workers", type=int, default=0,
        help="DataLoader workers (default: 0 for Windows compatibility)"
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=None,
        help="Override image directory (default: <data-dir>/images/pages)",
    )
    parser.add_argument(
        "--annotations-dir",
        type=str,
        default=None,
        help="Override annotation XML directory (default: <data-dir>/annotations/pascal_voc)",
    )
    parser.add_argument(
        "--split-dir",
        type=str,
        default=None,
        help="Directory containing train.txt/val.txt/test.txt (default: <data-dir>/splits)",
    )
    parser.add_argument(
        "--use-random-split",
        action="store_true",
        help="Ignore split files and use random train/val split",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(args)