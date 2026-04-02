"""
WaziGov Table Detection - Evaluation Script
=============================================
Compute mAP, precision, recall on annotated data.

Usage:
    python scripts/evaluate.py --model models/table_detection/final_model --data-dir data/
"""

import argparse
import json
from pathlib import Path

import torch
from PIL import Image
from torchvision.ops import box_iou
from transformers import DetrImageProcessor, TableTransformerForObjectDetection
import xml.etree.ElementTree as ET


def resolve_path(path_value, project_dir):
    """Resolve a user path. Relative paths are anchored to current working dir, then project dir."""
    p = Path(path_value)
    if p.is_absolute():
        return p

    cwd_candidate = (Path.cwd() / p).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return (project_dir / p).resolve()


def parse_voc_annotation(xml_path):
    """Parse ground truth from PASCAL VOC XML."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    size = root.find("size")
    width = int(size.find("width").text)
    height = int(size.find("height").text)

    boxes = []
    labels = []

    for obj in root.findall("object"):
        label = obj.find("name").text
        bbox = obj.find("bndbox")
        xmin = float(bbox.find("xmin").text)
        ymin = float(bbox.find("ymin").text)
        xmax = float(bbox.find("xmax").text)
        ymax = float(bbox.find("ymax").text)
        boxes.append([xmin, ymin, xmax, ymax])
        labels.append(label)

    return boxes, labels, (width, height)


def compute_metrics(gt_boxes, pred_boxes, pred_scores, iou_threshold=0.5):
    """Compute precision, recall, F1 for a single image."""
    if len(gt_boxes) == 0 and len(pred_boxes) == 0:
        return {"tp": 0, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0}
    if len(gt_boxes) == 0:
        return {"tp": 0, "fp": len(pred_boxes), "fn": 0, "precision": 0.0, "recall": 1.0, "f1": 0.0}
    if len(pred_boxes) == 0:
        return {"tp": 0, "fp": 0, "fn": len(gt_boxes), "precision": 1.0, "recall": 0.0, "f1": 0.0}

    gt_tensor = torch.tensor(gt_boxes, dtype=torch.float32)
    pred_tensor = torch.tensor(pred_boxes, dtype=torch.float32)

    ious = box_iou(pred_tensor, gt_tensor)

    matched_gt = set()
    tp = 0
    fp = 0

    # Sort predictions by score (descending)
    sorted_indices = sorted(range(len(pred_scores)), key=lambda i: pred_scores[i], reverse=True)

    for pred_idx in sorted_indices:
        if ious.shape[1] == 0:
            fp += 1
            continue

        best_iou, best_gt = ious[pred_idx].max(dim=0)
        best_gt = best_gt.item()

        if best_iou >= iou_threshold and best_gt not in matched_gt:
            tp += 1
            matched_gt.add(best_gt)
        else:
            fp += 1

    fn = len(gt_boxes) - len(matched_gt)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate(args):
    """Run evaluation on annotated data."""
    print("=" * 60)
    print("WaziGov Table Detection - Evaluation")
    print("=" * 60)

    project_dir = Path(__file__).resolve().parents[1]
    data_dir = resolve_path(args.data_dir, project_dir)
    images_dir = (
        resolve_path(args.images_dir, project_dir)
        if args.images_dir
        else (data_dir / "images" / "pages")
    )
    annotations_dir = (
        resolve_path(args.annotations_dir, project_dir)
        if args.annotations_dir
        else (data_dir / "annotations" / "pascal_voc")
    )

    print(f"Project dir: {project_dir}")
    print(f"Data dir: {data_dir}")
    print(f"Annotations dir: {annotations_dir}")
    print(f"Images dir: {images_dir}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load model
    model_path = args.model
    if not Path(model_path).exists():
        model_path = "microsoft/table-transformer-detection"
        print(f"Using pretrained model: {model_path}")

    processor = DetrImageProcessor.from_pretrained(model_path)
    model = TableTransformerForObjectDetection.from_pretrained(model_path)
    model.to(device)
    model.eval()

    # Evaluate each annotated page
    results = []
    total_tp, total_fp, total_fn = 0, 0, 0

    xml_files = sorted(annotations_dir.glob("*.xml"))
    xml_total = len(xml_files)

    if args.split_file:
        split_path = resolve_path(args.split_file, project_dir)
        stems = {
            line.strip()
            for line in split_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        xml_files = [x for x in xml_files if x.stem in stems]

    print(f"\nEvaluating on {len(xml_files)} annotated pages...\n")
    if len(xml_files) == 0:
        print("No annotation XML files matched your inputs.")
        print(f"  annotations_dir: {annotations_dir}")
        if args.split_file:
            print(f"  split_file: {args.split_file}")
            print(f"  split_path_resolved: {split_path}")
            print(f"  xml_before_split: {xml_total}")
            print(f"  split_stems: {len(stems)}")
            overlaps = sum(1 for x in sorted(annotations_dir.glob("*.xml")) if x.stem in stems)
            print(f"  xml_split_overlap: {overlaps}")
            print("  Hint: split stems may not overlap this annotation set.")
        print(f"  images_dir: {images_dir}")
        print("Evaluation cannot proceed with zero matched pages.")
        return

    for xml_path in xml_files:
        gt_boxes, gt_labels, (w, h) = parse_voc_annotation(xml_path)

        # Find image
        tree = ET.parse(xml_path)
        img_filename = tree.getroot().find("filename").text
        img_path = images_dir / img_filename

        if not img_path.exists():
            # Search for matching file
            for f in images_dir.iterdir():
                if img_filename in f.name or f.name in img_filename:
                    img_path = f
                    break

        if not img_path.exists():
            print(f"  SKIP {xml_path.name} - image not found")
            continue

        # Run detection
        image = Image.open(img_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        target_sizes = torch.tensor([image.size[::-1]], device=device)
        det_results = processor.post_process_object_detection(
            outputs, target_sizes=target_sizes, threshold=args.threshold
        )[0]

        pred_boxes = det_results["boxes"].cpu().tolist()
        pred_scores = det_results["scores"].cpu().tolist()

        metrics = compute_metrics(gt_boxes, pred_boxes, pred_scores, args.iou_threshold)

        total_tp += metrics["tp"]
        total_fp += metrics["fp"]
        total_fn += metrics["fn"]

        results.append({
            "file": xml_path.name,
            "gt_tables": len(gt_boxes),
            "pred_tables": len(pred_boxes),
            **metrics,
        })

        status = "✅" if metrics["f1"] == 1.0 else "⚠️" if metrics["f1"] > 0 else "❌"
        print(f"  {status} {img_filename}: GT={len(gt_boxes)}, Pred={len(pred_boxes)}, "
              f"P={metrics['precision']:.2f}, R={metrics['recall']:.2f}, F1={metrics['f1']:.2f}")

    # Overall metrics
    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    overall_f1 = (2 * overall_precision * overall_recall / (overall_precision + overall_recall)
                  if (overall_precision + overall_recall) > 0 else 0)

    print(f"\n{'=' * 60}")
    print(f"OVERALL RESULTS (IoU threshold: {args.iou_threshold})")
    print(f"{'=' * 60}")
    print(f"  Total GT tables:   {total_tp + total_fn}")
    print(f"  Total predictions: {total_tp + total_fp}")
    print(f"  True positives:    {total_tp}")
    print(f"  False positives:   {total_fp}")
    print(f"  False negatives:   {total_fn}")
    print(f"  Precision:         {overall_precision:.4f}")
    print(f"  Recall:            {overall_recall:.4f}")
    print(f"  F1 Score:          {overall_f1:.4f}")

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({
            "config": {
                "model": str(model_path),
                "threshold": args.threshold,
                "iou_threshold": args.iou_threshold,
            },
            "overall": {
                "precision": round(overall_precision, 4),
                "recall": round(overall_recall, 4),
                "f1": round(overall_f1, 4),
                "tp": total_tp, "fp": total_fp, "fn": total_fn,
            },
            "per_image": results,
        }, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate table detection model")
    parser.add_argument("--model", type=str, default="models/table_detection/final_model")
    parser.add_argument("--data-dir", type=str, default="data/")
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
        "--split-file",
        type=str,
        default=None,
        help="Optional split file (train.txt/val.txt/test.txt) to evaluate a subset",
    )
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--output", type=str, default="outputs/evaluation_results.json")
    args = parser.parse_args()
    evaluate(args)