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
import hashlib
import base64
import importlib.util
import math
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

import torch
from PIL import Image, ImageDraw, ImageFont
from transformers import DetrImageProcessor, TableTransformerForObjectDetection

if importlib.util.find_spec("easyocr") is not None:
    easyocr = importlib.import_module("easyocr")
else:
    easyocr = None

easyocr_reader = None
backup_detector = {"model": None, "processor": None, "device": None}


def get_easyocr_reader():
    """Lazily initialize EasyOCR reader."""
    global easyocr_reader
    if easyocr is None:
        return None
    if easyocr_reader is None:
        easyocr_reader = easyocr.Reader(["en"], gpu=torch.cuda.is_available())
    return easyocr_reader


def resolve_path(path_value, project_dir):
    """Resolve a user path. Relative paths are anchored to current working dir, then project dir."""
    p = Path(path_value)
    if p.is_absolute():
        return p

    cwd_candidate = (Path.cwd() / p).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return (project_dir / p).resolve()


def shorten_filename_stem(stem: str, max_len: int = 50) -> str:
    """Shorten a filename stem to prevent MAX_PATH issues, appending a hash for uniqueness."""
    if len(stem) <= max_len:
        return stem
    # Use a short hash of the full stem to ensure uniqueness after truncation
    hash_suffix = hashlib.sha256(stem.encode()).hexdigest()[:8]
    truncated_stem = stem[:max_len - len(hash_suffix) - 1]  # -1 for separator
    return f"{truncated_stem}-{hash_suffix}"


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


def load_structure_model(model_path, device):
    """Load the table structure recognition model and processor."""
    print(f"Loading structure model from: {model_path}")

    processor = DetrImageProcessor.from_pretrained(model_path)
    model = TableTransformerForObjectDetection.from_pretrained(model_path)
    model.to(device)
    model.eval()

    print(f"  Structure labels: {model.config.id2label}")
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
            # Bounding boxes are clamped to image dimensions by clamp_bbox_to_image later.
            # _raw_bbox preserves the original model output (may have negative coords) so
            # is_plausible_table() can use off-edge position as a false-positive signal.
            "score": round(score, 4),
            "_raw_bbox": [round(box[0], 1), round(box[1], 1), round(box[2], 1), round(box[3], 1)],
            "bbox": {
                "xmin": round(box[0], 1),
                "ymin": round(box[1], 1),
                "xmax": round(box[2], 1),
                "ymax": round(box[3], 1),
            },
        })

    # Clamp all bounding boxes to image dimensions immediately after detection
    clamped_detections = []
    for det in detections:
        bbox = det["bbox"]
        clamped_coords = clamp_bbox_to_image(
            [bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]],
            image.width,
            image.height,
        )
        det["bbox"] = {"xmin": clamped_coords[0], "ymin": clamped_coords[1], "xmax": clamped_coords[2], "ymax": clamped_coords[3]}
        clamped_detections.append(det)

    return clamped_detections


def detect_structure(table_image, model, processor, device, threshold=0.5):
    """Detect rows/columns/header regions on a cropped table image."""
    inputs = processor(images=table_image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    target_sizes = torch.tensor([table_image.size[::-1]], device=device)
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
            "label": model.config.id2label.get(label, f"class_{label}").lower(),
            "score": float(score),
            "bbox": [float(box[0]), float(box[1]), float(box[2]), float(box[3])],
        })

    return detections


def bbox_intersection_ratio(a, b):
    """Return intersection area ratio over min bbox area."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    denom = min(area_a, area_b)
    return (inter / denom) if denom > 0 else 0.0


def dedupe_sorted_boxes(items, axis="y", overlap_threshold=0.7):
    """Sort and deduplicate near-identical row or column boxes."""
    idx = 1 if axis == "y" else 0
    items = sorted(items, key=lambda x: (x["bbox"][idx] + x["bbox"][idx + 2]) / 2.0)
    deduped = []
    for item in items:
        if not deduped:
            deduped.append(item)
            continue
        prev = deduped[-1]
        if bbox_intersection_ratio(item["bbox"], prev["bbox"]) >= overlap_threshold:
            if item["score"] > prev["score"]:
                deduped[-1] = item
        else:
            deduped.append(item)
    return deduped


def cell_image_to_b64(table_image, cell_bbox_local):
    """Crop cell image and encode as base64 PNG."""
    x1, y1, x2, y2 = [int(round(v)) for v in cell_bbox_local]
    x1 = max(0, min(x1, table_image.width - 1))
    y1 = max(0, min(y1, table_image.height - 1))
    x2 = max(x1 + 1, min(x2, table_image.width))
    y2 = max(y1 + 1, min(y2, table_image.height))
    crop = table_image.crop((x1, y1, x2, y2))
    buf = BytesIO()
    crop.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_pdf_text_for_cell(page_words, cell_bbox_px, dpi=300):
    """Extract text from PDF words that overlap with a cell bbox in image pixels."""
    scale = dpi / 72.0
    x1, y1, x2, y2 = cell_bbox_px
    cell_pt = [x1 / scale, y1 / scale, x2 / scale, y2 / scale]
    words = []
    for w in page_words:
        wx1, wy1, wx2, wy2, text = w[0], w[1], w[2], w[3], w[4]
        if not text:
            continue
        overlap = bbox_intersection_ratio(cell_pt, [wx1, wy1, wx2, wy2])
        if overlap >= 0.2:
            words.append((wy1, wx1, text))
    words.sort(key=lambda x: (round(x[0], 1), x[1]))
    return " ".join(t for _, _, t in words).strip()


def extract_ocr_text_for_cell(table_image, cell_bbox_local, padding=12, scale_factor=2):
    """Run EasyOCR on a cell crop when the PDF text layer is empty."""
    reader = get_easyocr_reader()
    if reader is None:
        return ""

    x1, y1, x2, y2 = [int(round(v)) for v in cell_bbox_local]
    x1 -= padding
    y1 -= padding
    x2 += padding
    y2 += padding
    x1 = max(0, min(x1, table_image.width - 1))
    y1 = max(0, min(y1, table_image.height - 1))
    x2 = max(x1 + 1, min(x2, table_image.width))
    y2 = max(y1 + 1, min(y2, table_image.height))

    cell_crop = table_image.crop((x1, y1, x2, y2))
    if scale_factor > 1:
        cell_crop = cell_crop.resize(
            (cell_crop.width * scale_factor, cell_crop.height * scale_factor),
            Image.Resampling.LANCZOS,
        )
    try:
        ocr_results = reader.readtext(
            __import__("numpy").array(cell_crop),
            detail=1,
            paragraph=False,
            decoder="greedy",
        )
    except Exception:
        return ""

    if not ocr_results:
        return ""

    ocr_results = sorted(ocr_results, key=lambda item: (item[0][0][1], item[0][0][0]))
    text_parts = [item[1] for item in ocr_results if item[1].strip()]
    return " ".join(text_parts).strip()


def extract_easyocr_words_from_image(image):
    """Extract OCR words with pixel bboxes from a full page image."""
    reader = get_easyocr_reader()
    if reader is None:
        return []

    try:
        ocr_results = reader.readtext(
            __import__("numpy").array(image),
            detail=1,
            paragraph=False,
            decoder="greedy",
        )
    except Exception:
        return []

    words = []
    for item in ocr_results:
        poly, text = item[0], item[1]
        if not text or not text.strip():
            continue
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        words.append([min(xs), min(ys), max(xs), max(ys), text.strip()])
    return words


def infer_table_bbox_from_ocr_words(ocr_words, margin=12.0):
    """Infer coarse table bbox from OCR word boxes in pixel space."""
    if not ocr_words:
        return None
    xmin = min(w[0] for w in ocr_words) - margin
    ymin = min(w[1] for w in ocr_words) - margin
    xmax = max(w[2] for w in ocr_words) + margin
    ymax = max(w[3] for w in ocr_words) + margin
    return [float(max(0.0, xmin)), float(max(0.0, ymin)), float(max(xmin + 1.0, xmax)), float(max(ymin + 1.0, ymax))]


def extract_ocr_word_text_for_cell(ocr_words, cell_bbox_px):
    """Extract text from full-page OCR words overlapping a cell bbox."""
    if not ocr_words:
        return ""
    x1, y1, x2, y2 = cell_bbox_px
    parts = []
    for word in ocr_words:
        wx1, wy1, wx2, wy2, text = word
        if bbox_intersection_ratio([x1, y1, x2, y2], [wx1, wy1, wx2, wy2]) >= 0.15:
            parts.append((wy1, wx1, text))
    if not parts:
        return ""
    parts.sort(key=lambda p: (round(p[0], 1), p[1]))
    return " ".join(p[2] for p in parts).strip()


def extract_cell_text(table_image, page_words, page_bbox, cell_bbox_local, ocr_words=None):
    """Prefer PDF text extraction and fall back to OCR only when needed."""
    raw_text = extract_pdf_text_for_cell(page_words, page_bbox)
    if raw_text:
        return raw_text, "pdf_text"

    ocr_word_text = extract_ocr_word_text_for_cell(ocr_words or [], page_bbox)
    if ocr_word_text:
        return ocr_word_text, "ocr"

    ocr_text = extract_ocr_text_for_cell(table_image, cell_bbox_local)
    if ocr_text:
        return ocr_text, "ocr"

    return "", "none"


def overlap_indices(segments, bbox, threshold=0.3):
    """Return indices of segments overlapping the bbox enough to be considered part of it."""
    indices = []
    for index, segment in enumerate(segments):
        if bbox_intersection_ratio(segment["bbox"], bbox) >= threshold:
            indices.append(index)
    return indices


def infer_row_hierarchy(row_cells):
    """Infer a hierarchy depth for a row from the first meaningful text cell."""
    text_cells = [cell for cell in row_cells if cell.get("raw_text", "").strip()]
    if not text_cells:
        return None

    first_cell = min(text_cells, key=lambda cell: cell["col_idx"])
    first_text = first_cell["raw_text"].strip()
    first_col = first_cell["col_idx"]

    if re.match(r"^(?:[A-Z]|[IVXLC]+|\d+)[\.)]\s+", first_text):
        return 1

    if first_col == 0:
        if first_cell.get("col_span", 1) > 1:
            return 1
        if len(text_cells) == 1:
            return 2
        return 2

    if first_col == 1:
        return 2

    if first_col >= 2:
        return 3

    return 2


def parse_numeric_value(text):
    """Parse a numeric value from a cell text when possible."""
    if not text:
        return None, False

    cleaned = text.strip().replace(",", "")
    is_percent = cleaned.endswith("%")
    if is_percent:
        cleaned = cleaned[:-1]

    cleaned = cleaned.replace(" ", "")
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None, is_percent

    try:
        return float(match.group(0)), is_percent
    except ValueError:
        return None, is_percent


def cosine_similarity(a, b):
    """Compute cosine similarity between two numeric vectors."""
    if not a or not b:
        return 0.0

    length = max(len(a), len(b))
    a = list(a) + [0.0] * (length - len(a))
    b = list(b) + [0.0] * (length - len(b))
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def resize_vector(values, target_length):
    """Resize a vector to target length using linear interpolation."""
    if not values:
        return [0.0] * target_length
    if len(values) == target_length:
        return list(values)
    if target_length <= 1:
        return [float(values[0])]

    src = [float(v) for v in values]
    src_len = len(src)
    out = []
    for i in range(target_length):
        pos = i * (src_len - 1) / (target_length - 1)
        left = int(math.floor(pos))
        right = int(math.ceil(pos))
        if left == right:
            out.append(src[left])
            continue
        t = pos - left
        out.append(src[left] * (1.0 - t) + src[right] * t)
    return out


def build_table_profile(col_segments, table_bbox_page):
    """Build a normalized column profile for continuation matching."""
    if not col_segments:
        return {"column_profile": [], "bbox": table_bbox_page}

    widths = [max(1.0, segment["bbox"][2] - segment["bbox"][0]) for segment in col_segments]
    total = sum(widths)
    if total <= 0:
        total = 1.0
    profile = [round(width / total, 6) for width in widths]
    return {"column_profile": profile, "bbox": table_bbox_page}


def cluster_sorted_positions(items, center_key, gap_threshold):
    """Cluster sorted positions by gaps larger than the threshold."""
    if not items:
        return []

    clusters = [[items[0]]]
    for item in items[1:]:
        previous = clusters[-1][-1]
        if abs(item[center_key] - previous[center_key]) <= gap_threshold:
            clusters[-1].append(item)
        else:
            clusters.append([item])
    return clusters


def infer_segments_from_words(page_words, table_bbox_page, axis, dpi=300):
    """Infer approximate row or column segments from PDF words when model output is sparse."""
    scale = dpi / 72.0
    tx1, ty1, tx2, ty2 = table_bbox_page

    word_items = []
    for word in page_words:
        wx1, wy1, wx2, wy2, text = word[0], word[1], word[2], word[3], word[4]
        if not text:
            continue
        wx1_px, wy1_px, wx2_px, wy2_px = wx1 * scale, wy1 * scale, wx2 * scale, wy2 * scale
        cx = (wx1_px + wx2_px) / 2.0
        cy = (wy1_px + wy2_px) / 2.0
        if cx < tx1 or cx > tx2 or cy < ty1 or cy > ty2:
            continue
        word_items.append({
            "text": text,
            "bbox_px": [wx1_px, wy1_px, wx2_px, wy2_px],
            "center_x": cx,
            "center_y": cy,
            "width": wx2_px - wx1_px,
            "height": wy2_px - wy1_px,
        })

    if not word_items:
        return []

    word_items.sort(key=lambda item: item["center_y"] if axis == "y" else item["center_x"])
    median_width = sorted(item["width"] for item in word_items)[len(word_items) // 2]
    median_height = sorted(item["height"] for item in word_items)[len(word_items) // 2]

    if axis == "y":
        gap_threshold = max(6.0, median_height * 1.7)
        clusters = cluster_sorted_positions(word_items, "center_y", gap_threshold)
        segments = []
        for cluster in clusters:
            top = min(item["bbox_px"][1] for item in cluster)
            bottom = max(item["bbox_px"][3] for item in cluster)
            segments.append({
                "bbox": [float(tx1), float(top), float(tx2), float(bottom)],
                "score": min(1.0, 0.5 + len(cluster) / 20.0),
            })
        return segments

    gap_threshold = max(30.0, median_width * 2.5)
    clusters = cluster_sorted_positions(word_items, "center_x", gap_threshold)
    segments = []
    for cluster in clusters:
        left = min(item["bbox_px"][0] for item in cluster)
        right = max(item["bbox_px"][2] for item in cluster)
        segments.append({
            "bbox": [float(left), float(ty1), float(right), float(ty2)],
            "score": min(1.0, 0.5 + len(cluster) / 20.0),
        })
    return segments


def infer_table_bbox_from_words(page_words, dpi=300, margin=12.0):
    """Infer a coarse table bounding box from all words on the page."""
    scale = dpi / 72.0
    word_boxes = []
    for word in page_words:
        wx1, wy1, wx2, wy2, text = word[0], word[1], word[2], word[3], word[4]
        if not text:
            continue
        word_boxes.append([wx1 * scale, wy1 * scale, wx2 * scale, wy2 * scale])

    if not word_boxes:
        return None

    xmin = min(box[0] for box in word_boxes) - margin
    ymin = min(box[1] for box in word_boxes) - margin
    xmax = max(box[2] for box in word_boxes) + margin
    ymax = max(box[3] for box in word_boxes) + margin
    return [float(max(0.0, xmin)), float(max(0.0, ymin)), float(max(xmin + 1.0, xmax)), float(max(ymin + 1.0, ymax))]


def pt_bbox_to_px_bbox(pt_bbox, dpi=300):
    """Convert a PDF-point bbox to pixel bbox at the target DPI."""
    scale = dpi / 72.0
    x1, y1, x2, y2 = pt_bbox
    return [x1 * scale, y1 * scale, x2 * scale, y2 * scale]


def get_pdf_table_candidates(page, dpi=300):
    """Return table bbox candidates from PyMuPDF's table finder in pixel coords."""
    try:
        tables_obj = page.find_tables()
    except Exception:
        return []

    tables = getattr(tables_obj, "tables", None)
    if not tables:
        return []

    candidates = []
    for table in tables:
        bbox = getattr(table, "bbox", None)
        if not bbox:
            continue
        px = pt_bbox_to_px_bbox(bbox, dpi=dpi)
        candidates.append([float(px[0]), float(px[1]), float(px[2]), float(px[3])])
    return candidates


def clamp_bbox_to_image(bbox, width, height):
    """Clamp a bbox to image bounds and ensure non-zero dimensions."""
    x1, y1, x2, y2 = bbox
    x1 = max(0.0, min(float(x1), float(width - 1)))
    y1 = max(0.0, min(float(y1), float(height - 1)))
    x2 = max(x1 + 1.0, min(float(x2), float(width)))
    y2 = max(y1 + 1.0, min(float(y2), float(height)))
    return [x1, y1, x2, y2]


def bbox_iou(a, b):
    """Compute IoU between two xyxy boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0:
        return 0.0
    return inter / union


def stabilize_detections_with_pdf_tables(detections, page, image_size, dpi=300):
    """Replace implausibly tiny detector boxes with PDF-native table bboxes when available."""
    width, height = image_size
    page_area = float(max(1, width * height))
    candidates = [clamp_bbox_to_image(c, width, height) for c in get_pdf_table_candidates(page, dpi=dpi)]

    if not candidates:
        stabilized = []
        for det in detections:
            box = det.get("bbox", {})
            bbox = clamp_bbox_to_image(
                [box.get("xmin", 0.0), box.get("ymin", 0.0), box.get("xmax", 1.0), box.get("ymax", 1.0)],
                width,
                height,
            )
            det["bbox"] = {
                "xmin": round(bbox[0], 1),
                "ymin": round(bbox[1], 1),
                "xmax": round(bbox[2], 1),
                "ymax": round(bbox[3], 1),
            }
            stabilized.append(det)
        return stabilized

    if not detections:
        injected = []
        for cand in candidates:
            injected.append(
                {
                    "label": "table",
                    "score": 0.55,
                    "bbox": {
                        "xmin": round(cand[0], 1),
                        "ymin": round(cand[1], 1),
                        "xmax": round(cand[2], 1),
                        "ymax": round(cand[3], 1),
                    },
                }
            )
        return injected

    stabilized = []
    for det in detections:
        box = det.get("bbox", {})
        bbox = clamp_bbox_to_image(
            [box.get("xmin", 0.0), box.get("ymin", 0.0), box.get("xmax", 1.0), box.get("ymax", 1.0)],
            width,
            height,
        )
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        area_ratio = (bw * bh) / page_area

        tiny_box = bw < 100 or bh < 100 or area_ratio < 0.002
        if tiny_box:
            best_cand = max(candidates, key=lambda c: bbox_iou(bbox, c))
            # If IoU is zero due tiny box near origin, choose closest center candidate.
            if bbox_iou(bbox, best_cand) == 0.0:
                cx = (bbox[0] + bbox[2]) / 2.0
                cy = (bbox[1] + bbox[3]) / 2.0
                best_cand = min(
                    candidates,
                    key=lambda c: abs(((c[0] + c[2]) / 2.0) - cx) + abs(((c[1] + c[3]) / 2.0) - cy),
                )
            bbox = best_cand

        det["bbox"] = {
            "xmin": round(bbox[0], 1),
            "ymin": round(bbox[1], 1),
            "xmax": round(bbox[2], 1),
            "ymax": round(bbox[3], 1),
        }
        stabilized.append(det)

    return stabilized


def detection_quality_score(detections, image_size):
    """Score detection geometry quality using area coverage and count."""
    width, height = image_size
    page_area = float(max(1, width * height))
    if not detections:
        return 0.0

    areas = []
    for det in detections:
        box = det.get("bbox", {})
        w = max(0.0, float(box.get("xmax", 0.0)) - float(box.get("xmin", 0.0)))
        h = max(0.0, float(box.get("ymax", 0.0)) - float(box.get("ymin", 0.0)))
        areas.append((w * h) / page_area)

    max_area = max(areas) if areas else 0.0
    mean_area = sum(areas) / max(1, len(areas))
    count_bonus = min(0.2, len(detections) * 0.03)
    return max_area * 0.8 + mean_area * 0.2 + count_bonus


def detections_are_implausible(detections, image_size):
    """Flag detections that are too small to represent realistic page tables."""
    width, height = image_size
    page_area = float(max(1, width * height))
    if not detections:
        return True

    max_ratio = 0.0
    for det in detections:
        box = det.get("bbox", {})
        w = max(0.0, float(box.get("xmax", 0.0)) - float(box.get("xmin", 0.0)))
        h = max(0.0, float(box.get("ymax", 0.0)) - float(box.get("ymin", 0.0)))
        max_ratio = max(max_ratio, (w * h) / page_area)

    return max_ratio < 0.01


def get_backup_detector(device):
    """Lazily load pretrained detector used for geometry fallback."""
    global backup_detector
    if (
        backup_detector["model"] is None
        or backup_detector["processor"] is None
        or backup_detector["device"] != str(device)
    ):
        print("Loading geometry backup detector: microsoft/table-transformer-detection")
        processor = DetrImageProcessor.from_pretrained("microsoft/table-transformer-detection")
        model = TableTransformerForObjectDetection.from_pretrained("microsoft/table-transformer-detection")
        model.to(device)
        model.eval()
        backup_detector = {"model": model, "processor": processor, "device": str(device)}
    return backup_detector["model"], backup_detector["processor"]


def is_plausible_table(
    raw_bbox: list,
    img_width: int,
    img_height: int,
    off_edge_tolerance: float = 5.0,
) -> bool:
    """
    Reject detections that are geometrically implausible as real tables.

    Accepts the RAW (pre-clamp) bbox from the model so that off-edge origins
    can be used as a reliable signal.  Clamping happens internally for the
    area / width / aspect checks.

    Real tables in Kenyan government reports share predictable geometry:
      - They do not originate significantly off the page edge
      - They span a meaningful portion of the page width (≥ 15 %)
      - They are not extremely tall relative to their width (aspect guard)
      - They cover at least 1 % of the total page area

    This filter eliminates false positives caused by decorative page elements
    (cover borders, logo frames, margin rules) that the pretrained model
    sometimes mistakes for tables because they are rectangular regions with
    visible outlines — structurally similar to the bordered tables the model
    was trained on (PubTables-1M).

    The checks are intentionally conservative so that legitimate narrow
    tables (e.g. a two-column appendix key) are never discarded.

    Args:
        raw_bbox:  [xmin, ymin, xmax, ymax] in pixels, BEFORE clamping.
        img_width:  full page image width in pixels.
        img_height: full page image height in pixels.
        off_edge_tolerance: how many pixels off-edge is still acceptable
                            (accounts for minor floating-point noise).

    Returns:
        True  → keep the detection.
        False → discard as implausible.
    """
    xmin, ymin, xmax, ymax = raw_bbox

    if xmax <= xmin or ymax <= ymin:
        return False

    # ── 1. Off-edge origin check (uses raw, pre-clamp coordinates) ───────────
    # A detection that starts significantly beyond the page boundary is almost
    # always a margin decoration or cover-page ornament, never a data table.
    # Example: the COB cover-page left border produces xmin = -33.1 px.
    if xmin < -off_edge_tolerance:
        return False
    if ymin < -off_edge_tolerance:
        return False

    # Clamp for the remaining spatial checks
    cx1 = max(0.0, xmin)
    cy1 = max(0.0, ymin)
    cx2 = min(float(img_width),  xmax)
    cy2 = min(float(img_height), ymax)
    cw  = cx2 - cx1
    ch  = cy2 - cy1

    if cw <= 0 or ch <= 0:
        return False

    page_area = float(img_width * img_height)

    # ── 2. Minimum area: must cover at least 1 % of the page ─────────────────
    # Eliminates tiny margin ornaments and logo boxes.
    if (cw * ch) / page_area < 0.01:
        return False

    # ── 3. Minimum width: must span at least 15 % of page width ──────────────
    # Real tables nearly always stretch across most of the text column.
    # A narrow vertical stripe (like a border rule) will fail this check.
    if cw / img_width < 0.15:
        return False

    # ── 4. Aspect ratio guard: height must not exceed 10× the width ──────────
    # A region that is 10× taller than it is wide is almost certainly a
    # vertical border/margin decoration, not a data table.
    if ch / cw > 10.0:
        return False

    return True


def get_final_detections_for_page(
    image,
    page, # PyMuPDF page object, can be None for single image processing
    model,
    processor,
    device,
    threshold,
    use_pdf_table_finder,
    use_backup_detector,
    dpi=300,
    min_table_area_ratio=0.001, # Minimum area for a table to be considered valid (0.1% of page)
):
    """
    Runs initial detection, applies stabilization, and falls back to backup detector if needed.
    Returns a list of final, refined detections for the page.
    """
    initial_detections = detect_tables(image, model, processor, device, threshold)
    final_detections = initial_detections

    if use_pdf_table_finder and page is not None:
        final_detections = stabilize_detections_with_pdf_tables(
            initial_detections,
            page,
            image.size,
            dpi=dpi,
        )

    if use_backup_detector and detections_are_implausible(final_detections, image.size):
        backup_model, backup_processor = get_backup_detector(device)
        backup_detections = detect_tables(image, backup_model, backup_processor, device, threshold)
        if use_pdf_table_finder and page is not None:
            backup_detections = stabilize_detections_with_pdf_tables(
                backup_detections,
                page,
                image.size,
                dpi=dpi,
            )

        if detection_quality_score(backup_detections, image.size) > detection_quality_score(final_detections, image.size):
            print(f"    Geometry fallback used pretrained detector on page (quality score improved)")
            final_detections = backup_detections

    # ── Final filtering: remove geometrically implausible detections ─────────
    #
    # Two complementary checks are applied in sequence:
    #
    #   1. is_plausible_table() — geometry heuristics tuned for Kenyan
    #      government report layouts (off-edge origin, area, width fraction,
    #      aspect ratio).  Uses the raw pre-clamp bbox so that detections
    #      originating off the page edge (e.g. cover-page border decorations)
    #      are reliably rejected.
    #
    #   2. Legacy min_table_area_ratio guard — kept as a safety net for any
    #      edge cases that slip through the geometry filter.
    #
    # Both must pass for a detection to be kept.
    # _raw_bbox is an internal field and is stripped before returning.
    image_area = float(image.width * image.height)
    filtered_detections = []
    for det in final_detections:
        bbox     = det["bbox"]
        raw_bbox = det.get("_raw_bbox", [bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]])
        width    = bbox["xmax"] - bbox["xmin"]
        height   = bbox["ymax"] - bbox["ymin"]

        # Legacy area check
        if image_area > 0 and (width * height) / image_area < min_table_area_ratio:
            continue

        # Geometry plausibility check (covers false positives like cover borders)
        if not is_plausible_table(raw_bbox, image.width, image.height):
            continue

        # Strip the internal raw bbox field before the detection leaves this function
        det.pop("_raw_bbox", None)
        filtered_detections.append(det)

    return filtered_detections


def validate_table(table_entry):
    """Attach validation checks and warnings to a table entry."""
    warnings = []
    checks = []

    cells = table_entry.get("cells", [])
    bbox = table_entry.get("bbox", {})
    table_bounds = [bbox.get("xmin", 0.0), bbox.get("ymin", 0.0), bbox.get("xmax", 0.0), bbox.get("ymax", 0.0)]

    if table_entry.get("grid", {}).get("rows", 0) > 0 and table_entry.get("grid", {}).get("cols", 0) > 0:
        checks.append("grid_reconstruction")
    else:
        warnings.append("empty_grid")

    text_sources = {cell.get("text_source", "none") for cell in cells}
    if any(cell.get("raw_text", "").strip() for cell in cells):
        if "pdf_text" in text_sources:
            checks.append("pdf_text_fill")
        if "ocr" in text_sources:
            checks.append("ocr_fallback")
    else:
        warnings.append("no_cell_text_extracted")

    checks.append("merged_cell_postprocessing")
    if not any(cell.get("row_span", 1) > 1 or cell.get("col_span", 1) > 1 for cell in cells):
        warnings.append("no_merged_cells_detected")

    if any(cell.get("hierarchy_level") is not None for cell in cells):
        checks.append("hierarchy_assignment")
    else:
        warnings.append("no_header_hierarchy_detected")

    checks.append("continuation_linking")

    # Numeric ratio validation for rows with percentage-like cells.
    row_map = {}
    for cell in cells:
        row_map.setdefault(cell["row_idx"], []).append(cell)

    numeric_ratio_checked = False
    for row_cells in row_map.values():
        parsed = []
        for cell in sorted(row_cells, key=lambda c: c["col_idx"]):
            value, is_percent = parse_numeric_value(cell.get("raw_text", ""))
            if value is not None:
                parsed.append((cell, value, is_percent))

        percent_cells = [item for item in parsed if item[2]]
        numeric_cells = [item for item in parsed if not item[2]]
        if len(percent_cells) >= 1 and len(numeric_cells) >= 2:
            approved = numeric_cells[0][1]
            actual = numeric_cells[1][1]
            reported_pct = percent_cells[-1][1]
            if approved:
                expected_pct = (actual / approved) * 100.0
                numeric_ratio_checked = True
                if abs(expected_pct - reported_pct) > 2.0:
                    warnings.append(
                        f"numeric_ratio_mismatch_row_{row_cells[0]['row_idx']}: expected {expected_pct:.1f} vs reported {reported_pct:.1f}"
                    )
            break

    if numeric_ratio_checked:
        checks.append("numeric_ratio_check")

    # Ensure all cell boxes fit within the table box.
    out_of_bounds = 0
    for cell in cells:
        cb = cell.get("bbox", {})
        cell_box = [cb.get("xmin", 0.0), cb.get("ymin", 0.0), cb.get("xmax", 0.0), cb.get("ymax", 0.0)]
        if bbox_intersection_ratio(table_bounds, cell_box) <= 0.0:
            out_of_bounds += 1
    if out_of_bounds == 0:
        checks.append("bounded_boxes")
    else:
        warnings.append(f"{out_of_bounds}_cell_boxes_outside_table")

    table_entry["validation"] = {
        "is_valid": len(warnings) == 0,
        "checks_performed": checks,
        "warnings": warnings,
    }

    return table_entry


def link_continuations(per_page_tables):
    """Link tables across consecutive pages when their layout profiles are similar."""
    page_numbers = sorted(per_page_tables.keys())
    for current_page in page_numbers:
        if current_page == 0:
            continue

        prev_page = current_page - 1
        if prev_page not in per_page_tables:
            continue

        for current_index, current_table in enumerate(per_page_tables[current_page]):
            current_profile = current_table.get("_profile", {}).get("column_profile", [])
            current_bbox = current_table.get("bbox", {})
            current_width = max(1.0, current_bbox.get("xmax", 0.0) - current_bbox.get("xmin", 0.0))
            best_match = None
            best_score = 0.0

            for prev_index, prev_table in enumerate(per_page_tables[prev_page]):
                prev_profile = prev_table.get("_profile", {}).get("column_profile", [])
                prev_bbox = prev_table.get("bbox", {})
                prev_width = max(1.0, prev_bbox.get("xmax", 0.0) - prev_bbox.get("xmin", 0.0))

                if len(prev_profile) < 1 or len(current_profile) < 1:
                    continue

                common_len = max(3, min(len(prev_profile), len(current_profile)))
                prev_profile_cmp = resize_vector(prev_profile, common_len)
                current_profile_cmp = resize_vector(current_profile, common_len)

                profile_sim = cosine_similarity(prev_profile_cmp, current_profile_cmp)
                width_sim = 1.0 - min(1.0, abs(prev_width - current_width) / max(prev_width, current_width, 1.0))
                x_shift_sim = 1.0 - min(
                    1.0,
                    abs(prev_bbox.get("xmin", 0.0) - current_bbox.get("xmin", 0.0)) / max(prev_width, current_width, 1.0),
                )

                score = 0.7 * profile_sim + 0.2 * width_sim + 0.1 * x_shift_sim
                if score > best_score:
                    best_score = score
                    best_match = (prev_index, prev_table, score)

            if best_match and best_score >= 0.82:
                prev_index, prev_table, score = best_match
                current_id = current_table["table_id"]
                prev_id = prev_table["table_id"]

                current_table["continuation"] = {
                    "is_continuation": True,
                    "continues_from": prev_id,
                    "continues_on_next_page": False,
                    "linked_table_id": None,
                    "match_score": round(score, 4),
                }
                prev_table["continuation"]["continues_on_next_page"] = True
                prev_table["continuation"]["linked_table_id"] = current_id
                prev_table["continuation"]["match_score"] = round(score, 4)


def finalize_table_entries(per_page_tables):
    """Remove internal fields and ensure validation blocks are filled."""
    for page_tables in per_page_tables.values():
        for table_entry in page_tables:
            table_entry.pop("_profile", None)
            validate_table(table_entry)


def build_cells_from_structure(
    table_image,
    table_bbox_page,
    structure_detections,
    page_words,
    ocr_words,
    page_number,
    table_idx,
):
    """Build cell grid from row/column detections and enrich with text/image crops."""
    rows = [d for d in structure_detections if d["label"] == "table row"]
    cols = [d for d in structure_detections if d["label"] == "table column"]
    col_headers = [d for d in structure_detections if d["label"] == "table column header"]
    spanning = [d for d in structure_detections if d["label"] in {"table spanning cell", "table projected row header"}]

    rows = dedupe_sorted_boxes(rows, axis="y")
    cols = dedupe_sorted_boxes(cols, axis="x")

    if len(rows) < 2:
        fallback_rows = infer_segments_from_words(page_words, table_bbox_page, axis="y")
        if len(fallback_rows) > len(rows):
            rows = fallback_rows

    if len(cols) < 2:
        fallback_cols = infer_segments_from_words(page_words, table_bbox_page, axis="x")
        if len(fallback_cols) > len(cols):
            cols = fallback_cols

    if not rows:
        rows = [{"bbox": [0.0, 0.0, float(table_image.width), float(table_image.height)], "score": 0.0}]
    if not cols:
        cols = [{"bbox": [0.0, 0.0, float(table_image.width), float(table_image.height)], "score": 0.0}]

    row_segments = [{"bbox": row["bbox"], "score": float(row.get("score", 0.0))} for row in rows]
    col_segments = [{"bbox": col["bbox"], "score": float(col.get("score", 0.0))} for col in cols]

    merged_spans = []
    for span_det in spanning:
        span_bbox = span_det["bbox"]
        row_hits = overlap_indices(row_segments, span_bbox, threshold=0.25)
        col_hits = overlap_indices(col_segments, span_bbox, threshold=0.25)
        if not row_hits or not col_hits:
            continue

        merged_spans.append({
            "anchor_row": min(row_hits),
            "anchor_col": min(col_hits),
            "row_span": max(1, len(row_hits)),
            "col_span": max(1, len(col_hits)),
            "row_hits": row_hits,
            "col_hits": col_hits,
            "label": span_det["label"],
            "score": float(span_det.get("score", 0.0)),
            "bbox": span_bbox,
        })

    skip_cells = set()
    for merged in merged_spans:
        for r_idx in merged["row_hits"]:
            for c_idx in merged["col_hits"]:
                if r_idx == merged["anchor_row"] and c_idx == merged["anchor_col"]:
                    continue
                skip_cells.add((r_idx, c_idx))

    tx1, ty1, _, _ = table_bbox_page
    raw_cells = []
    for r_idx, row in enumerate(row_segments):
        ry1, ry2 = row["bbox"][1], row["bbox"][3]
        for c_idx, col in enumerate(col_segments):
            if (r_idx, c_idx) in skip_cells:
                continue

            cx1, cx2 = col["bbox"][0], col["bbox"][2]
            local_bbox = [cx1, ry1, cx2, ry2]
            page_bbox = [tx1 + cx1, ty1 + ry1, tx1 + cx2, ty1 + ry2]
            if page_bbox[2] <= page_bbox[0] or page_bbox[3] <= page_bbox[1]:
                continue

            merged = next((m for m in merged_spans if m["anchor_row"] == r_idx and m["anchor_col"] == c_idx), None)
            if r_idx == 0:
                cell_type = "column_header"
            elif merged and merged["label"] in {"table spanning cell", "table projected row header"}:
                cell_type = "header"
            else:
                cell_type = "data"

            raw_text, text_source = extract_cell_text(
                table_image,
                page_words,
                page_bbox,
                local_bbox,
                ocr_words=ocr_words,
            )
            confidence = round((row.get("score", 0.0) + col.get("score", 0.0)) / 2.0, 4)

            cell = {
                "cell_id": f"page_{page_number:03d}_table_{table_idx:02d}_r{r_idx}_c{c_idx}",
                "row_idx": r_idx,
                "col_idx": c_idx,
                "row_span": merged["row_span"] if merged else 1,
                "col_span": merged["col_span"] if merged else 1,
                "cell_type": cell_type,
                "hierarchy_level": None,
                "bbox": {
                    "xmin": round(page_bbox[0], 1),
                    "ymin": round(page_bbox[1], 1),
                    "xmax": round(page_bbox[2], 1),
                    "ymax": round(page_bbox[3], 1),
                },
                "raw_text": raw_text,
                "text_source": text_source,
                "image_b64": cell_image_to_b64(table_image, local_bbox),
                "confidence": confidence,
            }

            if merged:
                cell["cell_type"] = "header" if r_idx > 0 else "column_header"

            raw_cells.append(cell)

    row_groups = {}
    for cell in raw_cells:
        row_groups.setdefault(cell["row_idx"], []).append(cell)

    for row_idx, row_cells in row_groups.items():
        row_level = infer_row_hierarchy(row_cells)
        if row_level is None:
            continue

        text_cells = [cell for cell in row_cells if cell.get("raw_text", "").strip()]
        if not text_cells:
            continue

        first_text_col = min(cell["col_idx"] for cell in text_cells)
        for cell in row_cells:
            if cell["row_idx"] == 0:
                continue
            if cell["col_idx"] == first_text_col and cell.get("raw_text", "").strip():
                if cell["cell_type"] == "header" or first_text_col > 0:
                    cell["hierarchy_level"] = row_level
                elif re.match(r"^(?:[A-Z]|[IVXLC]+|\d+)[\.)]\s+", cell["raw_text"].strip()):
                    cell["hierarchy_level"] = row_level

    if raw_cells:
        # Promote explicit merged section headers even when the text is on the first row.
        for cell in raw_cells:
            if cell["row_idx"] > 0 and cell["row_span"] > 1 and cell["col_span"] >= 1:
                if cell.get("raw_text", "").strip():
                    cell["hierarchy_level"] = 1

    profile = build_table_profile(col_segments, table_bbox_page)

    return raw_cells, len(rows), len(cols), profile, len(merged_spans)


def build_cv_handoff_for_pdf(pdf_path, page_count, per_page_detections, model_version, per_page_tables=None):
    """Build a document-level JSON payload compatible with NLP handoff schema."""
    source_name = Path(pdf_path).name
    hash_input = f"{source_name}:{datetime.now(timezone.utc).isoformat()}".encode("utf-8")
    document_id = hashlib.sha256(hash_input).hexdigest()

    tables = []
    if per_page_tables:
        for _, page_tables in sorted(per_page_tables.items()):
            tables.extend(page_tables)
        return {
            "document_id": document_id,
            "source_file": source_name,
            "page_count": int(page_count),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "model_version": model_version,
            "tables": tables,
        }

    for page_idx, detections in per_page_detections.items():
        page_number = page_idx + 1
        for table_idx, det in enumerate(detections):
            table_id = f"page_{page_number:03d}_table_{table_idx:02d}"
            bbox = det.get("bbox", {})
            tables.append({
                "table_id": table_id,
                "page_number": page_number,
                "bbox": {
                    "xmin": float(bbox.get("xmin", 0.0)),
                    "ymin": float(bbox.get("ymin", 0.0)),
                    "xmax": float(bbox.get("xmax", 0.0)),
                    "ymax": float(bbox.get("ymax", 0.0)),
                },
                "confidence": float(det.get("score", 0.0)),
                "label": det.get("label", "table"),
                "grid": {"rows": 0, "cols": 0},
                "continuation": {
                    "is_continuation": False,
                    "continues_from": None,
                    "continues_on_next_page": False,
                    "linked_table_id": None,
                    "match_score": None,
                },
                "cells": [],
                "validation": {
                    "is_valid": False,
                    "checks_performed": [],
                    "warnings": [
                        "structure_recognition_not_run",
                        "cell_extraction_not_run",
                        "post_processing_not_run",
                    ],
                },
            })

    return {
        "document_id": document_id,
        "source_file": source_name,
        "page_count": int(page_count),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "model_version": model_version,
        "tables": tables,
    }


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

    # For single image processing, we don't have a PyMuPDF page object,
    # so we skip PDF table finder and backup detector for simplicity.
    # We still apply the final area filter.
    detections = get_final_detections_for_page(
        image=image,
        page=None, # No PyMuPDF page object for single image
        model=model,
        processor=processor,
        device=device,
        threshold=threshold,
        use_pdf_table_finder=False, # Not applicable for single image
        use_backup_detector=False,  # Not applicable for single image
    )

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


def process_pdf(
    pdf_path,
    model,
    processor,
    device,
    output_dir,
    threshold,
    model_version,
    cv_output_path=None,
    structure_model=None,
    structure_processor=None,
    structure_threshold=0.5,
    max_pages=None,
    use_pdf_table_finder=True,
    use_backup_detector=True,
):
    """Convert PDF to images and detect tables on each page."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("ERROR: PyMuPDF required. Install with: pip install PyMuPDF")
        sys.exit(1)

    pdf_path = Path(pdf_path)
    print(f"\nProcessing PDF: {pdf_path.name}")

    # Create temp dir for page images
    short_pdf_stem = shorten_filename_stem(pdf_path.stem)
    pages_dir = Path(output_dir) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    all_detections = {}
    per_page_detections = {}
    per_page_tables = {}
    page_total = len(doc)
    if max_pages is not None:
        page_total = min(page_total, max(0, int(max_pages)))

    for page_num in range(page_total):
        print(f"    Page {page_num + 1}/{page_total}...", end="\r", flush=True)
        page = doc.load_page(page_num)
        page_words = page.get_text("words")
        page_ocr_words = []
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)

        img_path = pages_dir / f"{short_pdf_stem}_page_{page_num + 1:03d}.png"
        pix.save(str(img_path))

        image = Image.open(img_path).convert("RGB")
        detections = get_final_detections_for_page(
            image=image,
            page=page,
            model=model,
            processor=processor,
            device=device,
            threshold=threshold,
            use_pdf_table_finder=use_pdf_table_finder,
            use_backup_detector=use_backup_detector,
            dpi=300,
        )

        all_detections[f"page_{page_num + 1}"] = detections
        per_page_detections[page_num] = detections
        page_tables = []
        for table_idx, det in enumerate(detections):
            bbox = det["bbox"]
            x1, y1 = max(0, int(round(bbox["xmin"]))), max(0, int(round(bbox["ymin"])))
            x2, y2 = int(round(bbox["xmax"])), int(round(bbox["ymax"]))
            x2 = min(image.width, max(x1 + 1, x2))
            y2 = min(image.height, max(y1 + 1, y2))

            table_id = f"page_{page_num + 1:03d}_table_{table_idx:02d}"
            table_entry = {
                "table_id": table_id,
                "page_number": page_num + 1,
                "bbox": {
                    "xmin": float(bbox["xmin"]),
                    "ymin": float(bbox["ymin"]),
                    "xmax": float(bbox["xmax"]),
                    "ymax": float(bbox["ymax"]),
                },
                "confidence": float(det.get("score", 0.0)),
                "label": det.get("label", "table"),
                "grid": {"rows": 0, "cols": 0},
                "continuation": {
                    "is_continuation": False,
                    "continues_from": None,
                    "continues_on_next_page": False,
                    "linked_table_id": None,
                    "match_score": None,
                },
                "cells": [],
                "validation": {
                    "is_valid": False,
                    "checks_performed": [],
                    "warnings": [],
                },
            }

            if structure_model and structure_processor:
                table_image = image.crop((x1, y1, x2, y2))
                structure_dets = detect_structure(
                    table_image,
                    structure_model,
                    structure_processor,
                    device,
                    threshold=structure_threshold,
                )
                cells, n_rows, n_cols, table_profile, merged_count = build_cells_from_structure(
                    table_image=table_image,
                    table_bbox_page=[float(x1), float(y1), float(x2), float(y2)],
                    structure_detections=structure_dets,
                    page_words=page_words,
                    ocr_words=page_ocr_words,
                    page_number=page_num + 1,
                    table_idx=table_idx,
                )
                table_entry["grid"] = {"rows": n_rows, "cols": n_cols}
                table_entry["cells"] = cells
                table_entry["_profile"] = table_profile
            else:
                table_entry["_profile"] = {"column_profile": [], "bbox": [float(x1), float(y1), float(x2), float(y2)]}

            page_tables.append(table_entry)

        per_page_tables[page_num] = page_tables
    print() # Newline after progress loop

    doc.close()

    link_continuations(per_page_tables)
    finalize_table_entries(per_page_tables)

    # Save summary
    summary_path = Path(output_dir) / f"{pdf_path.stem}_all_detections.json"
    with open(summary_path, "w") as f:
        json.dump(all_detections, f, indent=2)
    print(f"\nSummary saved: {summary_path}")

    total = sum(len(d) for d in all_detections.values())
    print(f"Total: {total} tables detected across {page_total} pages")

    if cv_output_path:
        cv_payload = build_cv_handoff_for_pdf(
            pdf_path=pdf_path,
            page_count=len(per_page_detections),
            per_page_detections=per_page_detections,
            model_version=model_version,
            per_page_tables=per_page_tables,
        )
        cv_output_path = Path(cv_output_path)
        cv_output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cv_output_path, "w", encoding="utf-8") as f:
            json.dump(cv_payload, f, indent=2)
        print(f"NLP handoff JSON saved: {cv_output_path}")
        if structure_model and structure_processor:
            print("Included: table grid, cell bboxes, base64 cell images, and PDF text per cell.")
            print("Included: continuation linking, merged-cell post-processing, and validation checks.")
            print("Note: table geometry stabilization is still pending for difficult layouts.")
        else:
            print("Note: cells/grid/continuation require structure recognition + post-processing.")

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
    parser.add_argument(
        "--cv-output", type=str, default=None,
        help="Optional document-level JSON output for NLP handoff (PDF mode only)"
    )
    parser.add_argument(
        "--structure-model", type=str, default="microsoft/table-transformer-structure-recognition",
        help="Structure model path or HuggingFace model name"
    )
    parser.add_argument(
        "--structure-threshold", type=float, default=0.5,
        help="Structure detection threshold (default: 0.5)"
    )
    parser.add_argument(
        "--skip-structure", action="store_true",
        help="Skip structure recognition even when --cv-output is provided"
    )
    parser.add_argument(
        "--max-pages", type=int, default=None,
        help="Optional number of first PDF pages to process (for fast testing)"
    )
    parser.add_argument(
        "--disable-pdf-table-finder",
        action="store_true",
        help="Disable PyMuPDF table finder geometry stabilization for PDF inference",
    )
    parser.add_argument(
        "--disable-backup-detector",
        action="store_true",
        help="Disable pretrained geometry fallback when primary detections are implausibly small",
    )
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parents[1]

    if not any([args.image, args.image_dir, args.pdf]):
        args.image_dir = "data/images/pages"
        print("No input provided; defaulting to --image-dir data/images/pages")

    if sum(bool(x) for x in [args.image, args.image_dir, args.pdf]) > 1:
        parser.error("Use only one input source: --image, --image-dir, or --pdf")

    # Setup
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Try fine-tuned model first, fall back to pretrained
    model_path = resolve_path(args.model, project_dir)
    model_path_str = str(model_path)
    if args.model.startswith("microsoft/"):
        model_path_str = args.model

    if not Path(model_path).exists() and not args.model.startswith("microsoft/"):
        print(f"Fine-tuned model not found at {model_path}")
        model_path_str = "microsoft/table-transformer-detection"
        print(f"Falling back to pretrained: {model_path_str}")

    model, processor = load_model(model_path_str, device)

    use_structure = bool(args.pdf and args.cv_output and not args.skip_structure)
    structure_model = None
    structure_processor = None
    if use_structure:
        structure_model_path = args.structure_model
        if not structure_model_path.startswith("microsoft/"):
            resolved_structure = resolve_path(structure_model_path, project_dir)
            structure_model_path = str(resolved_structure)
        structure_model, structure_processor = load_structure_model(structure_model_path, device)

    # Create output dir
    output_dir = resolve_path(args.output_dir, project_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process inputs
    if args.pdf:
        pdf_path = resolve_path(args.pdf, project_dir)
        cv_output_path = resolve_path(args.cv_output, project_dir) if args.cv_output else None
        process_pdf(
            pdf_path,
            model,
            processor,
            device,
            str(output_dir),
            args.threshold,
            model_version=model_path_str,
            cv_output_path=cv_output_path,
            structure_model=structure_model,
            structure_processor=structure_processor,
            structure_threshold=args.structure_threshold,
            max_pages=args.max_pages,
            use_pdf_table_finder=not args.disable_pdf_table_finder,
            use_backup_detector=not args.disable_backup_detector,
        )
        if args.cv_output and cv_output_path:
            print("Tip: Use this file as CV->NLP handoff input.")
    elif args.image:
        image_path = resolve_path(args.image, project_dir)
        process_image(image_path, model, processor, device, str(output_dir), args.threshold)
    elif args.image_dir:
        img_dir = resolve_path(args.image_dir, project_dir)
        if not img_dir.exists():
            parser.error(f"Image directory not found: {img_dir}")
        for img_path in sorted(img_dir.glob("*.png")):
            process_image(img_path, model, processor, device, str(output_dir), args.threshold)


if __name__ == "__main__":
    main()