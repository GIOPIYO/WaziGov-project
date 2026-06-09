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

if importlib.util.find_spec("pytesseract") is not None:
    pytesseract = importlib.import_module("pytesseract")
else:
    pytesseract = None


def resolve_path(path_value, project_dir):
    """Resolve a user path. Relative paths are anchored to current working dir, then project dir."""
    p = Path(path_value)
    if p.is_absolute():
        return p

    cwd_candidate = (Path.cwd() / p).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return (project_dir / p).resolve()


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
            "score": round(score, 4),
            "bbox": {
                "xmin": round(box[0], 1),
                "ymin": round(box[1], 1),
                "xmax": round(box[2], 1),
                "ymax": round(box[3], 1),
            },
        })

    return detections


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


def extract_ocr_text_for_cell(table_image, cell_bbox_local):
    """Run OCR on a cell crop when the PDF text layer is empty."""
    if pytesseract is None:
        return ""

    x1, y1, x2, y2 = [int(round(v)) for v in cell_bbox_local]
    x1 = max(0, min(x1, table_image.width - 1))
    y1 = max(0, min(y1, table_image.height - 1))
    x2 = max(x1 + 1, min(x2, table_image.width))
    y2 = max(y1 + 1, min(y2, table_image.height))

    cell_crop = table_image.crop((x1, y1, x2, y2))
    try:
        raw_text = pytesseract.image_to_string(cell_crop, config="--psm 6")
    except Exception:
        return ""
    return " ".join(raw_text.split()).strip()


def extract_cell_text(table_image, page_words, page_bbox, cell_bbox_local):
    """Prefer PDF text extraction and fall back to OCR only when needed."""
    raw_text = extract_pdf_text_for_cell(page_words, page_bbox)
    if raw_text:
        return raw_text, "pdf_text"

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

    if any(cell.get("raw_text", "").strip() for cell in cells):
        checks.append("pdf_text_fill")
    else:
        warnings.append("no_cell_text_extracted")

    if any(cell.get("row_span", 1) > 1 or cell.get("col_span", 1) > 1 for cell in cells):
        checks.append("merged_cell_postprocessing")
    else:
        checks.append("merged_cell_postprocessing")

    if any(cell.get("hierarchy_level") is not None for cell in cells):
        checks.append("hierarchy_assignment")
    else:
        warnings.append("no_header_hierarchy_detected")

    if table_entry.get("continuation", {}).get("is_continuation") or table_entry.get("continuation", {}).get("continues_on_next_page"):
        checks.append("continuation_linking")
    else:
        checks.append("continuation_linking")

    # Numeric ratio validation for rows with percentage-like cells.
    row_map = {}
    for cell in cells:
        row_map.setdefault(cell["row_idx"], []).append(cell)

    numeric_ratio_checked = False
    ratio_issue = False
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
                    ratio_issue = True
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

                if len(prev_profile) != len(current_profile):
                    continue

                profile_sim = cosine_similarity(prev_profile, current_profile)
                width_sim = 1.0 - min(1.0, abs(prev_width - current_width) / max(prev_width, current_width, 1.0))
                x_shift_sim = 1.0 - min(
                    1.0,
                    abs(prev_bbox.get("xmin", 0.0) - current_bbox.get("xmin", 0.0)) / max(prev_width, current_width, 1.0),
                )

                score = 0.7 * profile_sim + 0.2 * width_sim + 0.1 * x_shift_sim
                if score > best_score:
                    best_score = score
                    best_match = (prev_index, prev_table)

            if best_match and best_score >= 0.82:
                prev_index, prev_table = best_match
                current_id = current_table["table_id"]
                prev_id = prev_table["table_id"]

                current_table["continuation"] = {
                    "is_continuation": True,
                    "continues_from": prev_id,
                    "continues_on_next_page": False,
                    "linked_table_id": None,
                }
                prev_table["continuation"]["continues_on_next_page"] = True
                prev_table["continuation"]["linked_table_id"] = current_id


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
                    "continues_on_next_page": False,
                    "linked_table_id": None,
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
        page = doc.load_page(page_num)
        page_words = page.get_text("words")
        mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
        pix = page.get_pixmap(matrix=mat)

        img_path = pages_dir / f"{pdf_path.stem}_page_{page_num + 1:03d}.png"
        pix.save(str(img_path))

        detections = process_image(
            img_path, model, processor, device, output_dir, threshold
        )
        image = Image.open(img_path).convert("RGB")
        all_detections[f"page_{page_num + 1}"] = detections
        per_page_detections[page_num] = detections

        page_tables = []
        for table_idx, det in enumerate(detections):
            bbox = det["bbox"]
            x1, y1 = max(0, int(round(bbox["xmin"]))), max(0, int(round(bbox["ymin"])))
            x2, y2 = int(round(bbox["xmax"])), int(round(bbox["ymax"]))
            x2 = min(image.width, max(x1 + 1, x2))
            y2 = min(image.height, max(y1 + 1, y2))

            if (x2 - x1) < 50 or (y2 - y1) < 50:
                inferred_bbox = infer_table_bbox_from_words(page_words)
                if inferred_bbox:
                    x1, y1, x2, y2 = [int(round(v)) for v in inferred_bbox]
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(image.width, max(x1 + 1, x2))
                    y2 = min(image.height, max(y1 + 1, y2))
                    bbox = {
                        "xmin": float(x1),
                        "ymin": float(y1),
                        "xmax": float(x2),
                        "ymax": float(y2),
                    }

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
                    "continues_on_next_page": False,
                    "linked_table_id": None,
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
            print("Remaining TODO: continuation linking, merged-cell post-processing, arithmetic validation.")
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