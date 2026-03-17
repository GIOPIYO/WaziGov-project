"""
WaziGov Table Detection - Inference Script
============================================
Run table detection on new PDF pages using the fine-tuned model.
Falls back to the pretrained model if no fine-tuned model exists.

Usage:
    # On a single image
    python scripts/inference.py --image path/to/page.png

    # On a folder of images
    python scripts/inference.py --image-dir data/images/pages/

    # On a PDF
    python scripts/inference.py --pdf path/to/document.pdf

    # Using pretrained model (no fine-tuning needed)
    python scripts/inference.py --image page.png --model microsoft/table-transformer-detection
"""

import os
import sys
import argparse
import json
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import DetrImageProcessor, TableTransformerForObjectDetection


# ============================================================================
# Detection
# ============================================================================

def load_model(model_path, device):
    """Load the Table Transformer model and processor."""
    print(f"Loading model from: {model_path}")

    processor = DetrImageProcessor.from_pretrained(model_path)
    model = TableTransformerForObjectDetection.from_pretrained(model_path)
    model.to(device)
    model.eval()

    print(f"  Labels: {model.config.id2label}")
    return model, processor


def detect_tables(image, model, processor, device, threshold=0.5):
    """
    Detect tables in a single image.
    
    Returns list of dicts with keys: label, score, bbox (xmin, ymin, xmax, ymax)
    """
    # Preprocess
    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    # Forward pass
    with torch.no_grad():
        outputs = model(**inputs)

    # Post-process
    target_sizes = torch.tensor([image.size[::-1]], device=device)  # (height, width)
    results = processor.post_process_object_detection(
        outputs, target_sizes=target_sizes, threshold=threshold
    )[0]

    detections = []
    for score, label, box in zip(
        results["scores"].cpu().tolist(),
        results["labels"].cpu().tolist(),
        results["boxes"].cpu().tolist(),
    ):
        detections.append({
            "label": model.config.id2label.get(label, f"class_{label}"),
            "score": round(score, 4),
            "bbox": {
                "xmin": round(box[0], 1),
                "ymin": round(box[1], 1),
                "xmax": round(box[2], 1),
                "ymax": round(box[3], 1),
            },
        })

    return detections


def visualize_detections(image, detections, output_path):
    """Draw bounding boxes on the image and save."""
    draw = ImageDraw.Draw(image)

    colors = {
        "table": "#FF6B6B",
        "table_rotated": "#4ECDC4",
    }

    for det in detections:
        bbox = det["bbox"]
        color = colors.get(det["label"], "#FFFFFF")
        label_text = f"{det['label']} ({det['score']:.2f})"

        # Draw rectangle
        draw.rectangle(
            [bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]],
            outline=color,
            width=5,
        )

        # Draw label background
        text_bbox = draw.textbbox((0, 0), label_text)
        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]
        draw.rectangle(
            [bbox["xmin"], bbox["ymin"] - text_h - 8,
             bbox["xmin"] + text_w + 8, bbox["ymin"]],
            fill=color,
        )
        draw.text(
            (bbox["xmin"] + 4, bbox["ymin"] - text_h - 4),
            label_text,
            fill="white",
        )

    image.save(output_path)
    return output_path


# ============================================================================
# Process files
# ============================================================================

def process_image(image_path, model, processor, device, output_dir, threshold):
    """Process a single image."""
    image_path = Path(image_path)
    image = Image.open(image_path).convert("RGB")

    detections = detect_tables(image, model, processor, device, threshold)

    print(f"\n  {image_path.name}: {len(detections)} table(s) detected")
    for det in detections:
        print(f"    - {det['label']} (confidence: {det['score']:.2f}) "
              f"bbox: [{det['bbox']['xmin']:.0f}, {det['bbox']['ymin']:.0f}, "
              f"{det['bbox']['xmax']:.0f}, {det['bbox']['ymax']:.0f}]")

    # Save visualization
    if output_dir:
        vis_path = Path(output_dir) / f"detected_{image_path.name}"
        visualize_detections(image.copy(), detections, vis_path)
        print(f"    Visualization: {vis_path}")

    # Save JSON results
    if output_dir:
        json_path = Path(output_dir) / f"{image_path.stem}_detections.json"
        with open(json_path, "w") as f:
            json.dump({
                "image": str(image_path),
                "detections": detections,
            }, f, indent=2)

    return detections


def process_pdf(pdf_path, model, processor, device, output_dir, threshold):
    """Convert PDF to images and detect tables on each page."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF required. Install with: pip install PyMuPDF")
        sys.exit(1)

    pdf_path = Path(pdf_path)
    print(f"\nProcessing PDF: {pdf_path.name}")

    # Create temp dir for page images
    pages_dir = Path(output_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    all_detections = {}

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)

        img_path = pages_dir / f"{pdf_path.stem}_page_{page_num + 1:03d}.png"
        pix.save(str(img_path))

        detections = process_image(
            img_path, model, processor, device, output_dir, threshold
        )
        all_detections[f"page_{page_num + 1}"] = detections

    doc.close()

    # Save summary
    summary_path = Path(output_dir) / f"{pdf_path.stem}_all_detections.json"
    with open(summary_path, "w") as f:
        json.dump(all_detections, f, indent=2)
    print(f"\nSummary saved: {summary_path}")

    total = sum(len(d) for d in all_detections.values())
    print(f"Total: {total} tables detected across {len(doc)} pages")

    return all_detections


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="WaziGov Table Detection - Run inference"
    )
    parser.add_argument("--image", type=str, help="Path to a single image")
    parser.add_argument("--image-dir", type=str, help="Path to folder of images")
    parser.add_argument("--pdf", type=str, help="Path to a PDF file")
    parser.add_argument(
        "--model", type=str, default="models/table_detection/final_model",
        help="Model path or HuggingFace model name"
    )
    parser.add_argument(
        "--output-dir", type=str, default="outputs/detections/",
        help="Output directory for results"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Detection confidence threshold (default: 0.5)"
    )
    args = parser.parse_args()

    if not any([args.image, args.image_dir, args.pdf]):
        parser.error("Provide --image, --image-dir, or --pdf")

    # Setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Try fine-tuned model first, fall back to pretrained
    model_path = args.model
    if not Path(model_path).exists() and not model_path.startswith("microsoft/"):
        print(f"Fine-tuned model not found at {model_path}")
        model_path = "microsoft/table-transformer-detection"
        print(f"Falling back to pretrained: {model_path}")

    model, processor = load_model(model_path, device)

    # Create output dir
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process inputs
    if args.pdf:
        process_pdf(args.pdf, model, processor, device, str(output_dir), args.threshold)
    elif args.image:
        process_image(args.image, model, processor, device, str(output_dir), args.threshold)
    elif args.image_dir:
        img_dir = Path(args.image_dir)
        for img_path in sorted(img_dir.glob("*.png")):
            process_image(img_path, model, processor, device, str(output_dir), args.threshold)


if __name__ == "__main__":
    main()