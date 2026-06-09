"""
WaziGov GRiTS Evaluation
========================
Compute GRiTS-style table structure metrics between a ground-truth CV handoff
JSON and a predicted CV handoff JSON.

This implementation reports:
- grits_top: boundary/topology agreement of reconstructed table grids
- grits_con: content agreement using per-slot normalized cell text
- grits_loc: geometric agreement based on one-to-one bbox IoU matching
- grits: mean of (top, con, loc)

Usage:
    python scripts/evaluate_grits.py \
        --gt outputs/cv_handoff_gt.json \
        --pred outputs/cv_handoff_pred.json \
        --mode paper_like \
        --output outputs/grits_results.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def resolve_path(path_value: str, project_dir: Path) -> Path:
    """Resolve a user path. Relative paths are anchored to current working dir, then project dir."""
    p = Path(path_value)
    if p.is_absolute():
        return p

    cwd_candidate = (Path.cwd() / p).resolve()
    if cwd_candidate.exists():
        return cwd_candidate

    return (project_dir / p).resolve()


def normalize_text(value: Optional[str]) -> str:
    """Normalize text for content matching."""
    if not value:
        return ""
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def iou_xyxy(a: List[float], b: List[float]) -> float:
    """Compute IoU for [xmin, ymin, xmax, ymax] boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = max(0.0, ix2 - ix1)
    ih = max(0.0, iy2 - iy1)
    inter = iw * ih

    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter

    if union <= 0:
        return 0.0
    return inter / union


def f1_from_counts(tp: int, fp: int, fn: int) -> float:
    """F1 from confusion counts."""
    denom = (2 * tp + fp + fn)
    if denom == 0:
        return 1.0
    return (2 * tp) / denom


def table_bbox_xyxy(table: dict) -> Optional[List[float]]:
    """Read table bbox dict into xyxy list."""
    bbox = table.get("bbox") or {}
    required = ("xmin", "ymin", "xmax", "ymax")
    if not all(k in bbox for k in required):
        return None
    try:
        return [float(bbox["xmin"]), float(bbox["ymin"]), float(bbox["xmax"]), float(bbox["ymax"])]
    except (TypeError, ValueError):
        return None


def cell_bbox_xyxy(cell: dict) -> Optional[List[float]]:
    """Read cell bbox dict into xyxy list."""
    bbox = cell.get("bbox") or {}
    required = ("xmin", "ymin", "xmax", "ymax")
    if not all(k in bbox for k in required):
        return None
    try:
        return [float(bbox["xmin"]), float(bbox["ymin"]), float(bbox["xmax"]), float(bbox["ymax"])]
    except (TypeError, ValueError):
        return None


def infer_grid_shape(table: dict) -> Tuple[int, int]:
    """Infer grid shape from declared grid or cell spans."""
    declared = table.get("grid") or {}
    rows = int(declared.get("rows", 0) or 0)
    cols = int(declared.get("cols", 0) or 0)

    for cell in table.get("cells", []):
        try:
            r = int(cell.get("row_idx", 0) or 0)
            c = int(cell.get("col_idx", 0) or 0)
            rs = max(1, int(cell.get("row_span", 1) or 1))
            cs = max(1, int(cell.get("col_span", 1) or 1))
        except (TypeError, ValueError):
            continue
        rows = max(rows, r + rs)
        cols = max(cols, c + cs)

    return max(0, rows), max(0, cols)


def canonical_cell_key(cell: dict) -> str:
    """Stable key for a cell independent of generated ids."""
    r = int(cell.get("row_idx", 0) or 0)
    c = int(cell.get("col_idx", 0) or 0)
    rs = max(1, int(cell.get("row_span", 1) or 1))
    cs = max(1, int(cell.get("col_span", 1) or 1))
    return f"r{r}_c{c}_rs{rs}_cs{cs}"


def slot_bbox_map(table: dict) -> Dict[Tuple[int, int], List[float]]:
    """Map each occupied grid slot to its cell bbox."""
    slot_map: Dict[Tuple[int, int], List[float]] = {}

    for cell in table.get("cells", []):
        bbox = cell_bbox_xyxy(cell)
        if bbox is None:
            continue
        try:
            r = int(cell.get("row_idx", 0) or 0)
            c = int(cell.get("col_idx", 0) or 0)
            rs = max(1, int(cell.get("row_span", 1) or 1))
            cs = max(1, int(cell.get("col_span", 1) or 1))
        except (TypeError, ValueError):
            continue

        for rr in range(max(0, r), max(0, r + rs)):
            for cc in range(max(0, c), max(0, c + cs)):
                slot_map[(rr, cc)] = bbox

    return slot_map


def build_slot_owner_grid(table: dict) -> Tuple[List[List[Optional[str]]], Dict[str, str]]:
    """
    Build slot owner grid where each slot stores canonical owner key.
    Also return owner->normalized text map for content scoring.
    """
    rows, cols = infer_grid_shape(table)
    if rows == 0 or cols == 0:
        return [], {}

    grid: List[List[Optional[str]]] = [[None for _ in range(cols)] for _ in range(rows)]
    owner_text: Dict[str, str] = {}

    for cell in table.get("cells", []):
        try:
            r = int(cell.get("row_idx", 0) or 0)
            c = int(cell.get("col_idx", 0) or 0)
            rs = max(1, int(cell.get("row_span", 1) or 1))
            cs = max(1, int(cell.get("col_span", 1) or 1))
        except (TypeError, ValueError):
            continue

        owner = canonical_cell_key(cell)
        owner_text[owner] = normalize_text(cell.get("raw_text", ""))

        r_end = min(rows, r + rs)
        c_end = min(cols, c + cs)

        for rr in range(max(0, r), r_end):
            for cc in range(max(0, c), c_end):
                if grid[rr][cc] is None:
                    grid[rr][cc] = owner

    return grid, owner_text


def boundary_maps(grid: List[List[Optional[str]]]) -> Tuple[List[List[bool]], List[List[bool]]]:
    """Compute vertical and horizontal boundary maps from owner grid."""
    if not grid or not grid[0]:
        return [], []

    rows = len(grid)
    cols = len(grid[0])

    vertical = [[False for _ in range(max(0, cols - 1))] for _ in range(rows)]
    horizontal = [[False for _ in range(cols)] for _ in range(max(0, rows - 1))]

    for r in range(rows):
        for c in range(cols - 1):
            left_owner = grid[r][c]
            right_owner = grid[r][c + 1]
            vertical[r][c] = left_owner != right_owner

    for r in range(rows - 1):
        for c in range(cols):
            top_owner = grid[r][c]
            bottom_owner = grid[r + 1][c]
            horizontal[r][c] = top_owner != bottom_owner

    return vertical, horizontal


def pad_bool_grid(grid: List[List[bool]], rows: int, cols: int) -> List[List[bool]]:
    """Pad a bool matrix with False values to target shape."""
    out = [[False for _ in range(cols)] for _ in range(rows)]
    for r in range(min(rows, len(grid))):
        row = grid[r]
        for c in range(min(cols, len(row))):
            out[r][c] = bool(row[c])
    return out


def compare_bool_grids(gt: List[List[bool]], pred: List[List[bool]]) -> Tuple[int, int, int]:
    """Return tp/fp/fn for True positions after padding to common shape."""
    rows = max(len(gt), len(pred))
    cols = max(len(gt[0]) if gt else 0, len(pred[0]) if pred else 0)

    if rows == 0 or cols == 0:
        return 0, 0, 0

    gt_p = pad_bool_grid(gt, rows, cols)
    pred_p = pad_bool_grid(pred, rows, cols)

    tp = fp = fn = 0
    for r in range(rows):
        for c in range(cols):
            g = gt_p[r][c]
            p = pred_p[r][c]
            if p and g:
                tp += 1
            elif p and not g:
                fp += 1
            elif g and not p:
                fn += 1

    return tp, fp, fn


def grits_top(gt_table: dict, pred_table: dict) -> float:
    """Topology score from boundary agreement."""
    gt_grid, _ = build_slot_owner_grid(gt_table)
    pred_grid, _ = build_slot_owner_grid(pred_table)

    gt_v, gt_h = boundary_maps(gt_grid)
    pred_v, pred_h = boundary_maps(pred_grid)

    tp_v, fp_v, fn_v = compare_bool_grids(gt_v, pred_v)
    tp_h, fp_h, fn_h = compare_bool_grids(gt_h, pred_h)

    return f1_from_counts(tp_v + tp_h, fp_v + fp_h, fn_v + fn_h)


def grits_con(gt_table: dict, pred_table: dict) -> float:
    """Content score from per-slot normalized text agreement."""
    gt_grid, gt_text = build_slot_owner_grid(gt_table)
    pred_grid, pred_text = build_slot_owner_grid(pred_table)

    rows = max(len(gt_grid), len(pred_grid))
    cols = max(len(gt_grid[0]) if gt_grid else 0, len(pred_grid[0]) if pred_grid else 0)

    if rows == 0 or cols == 0:
        return 1.0

    tp = fp = fn = 0

    for r in range(rows):
        for c in range(cols):
            gt_owner = gt_grid[r][c] if r < len(gt_grid) and c < (len(gt_grid[0]) if gt_grid else 0) else None
            pred_owner = pred_grid[r][c] if r < len(pred_grid) and c < (len(pred_grid[0]) if pred_grid else 0) else None

            gt_val = gt_text.get(gt_owner, "") if gt_owner else ""
            pred_val = pred_text.get(pred_owner, "") if pred_owner else ""

            if not gt_val and not pred_val:
                continue
            if gt_val and pred_val and gt_val == pred_val:
                tp += 1
            else:
                if pred_val:
                    fp += 1
                if gt_val:
                    fn += 1

    return f1_from_counts(tp, fp, fn)


def greedy_iou_match(gt_boxes: List[List[float]], pred_boxes: List[List[float]], min_iou: float = 0.0) -> float:
    """Greedy one-to-one matching sum of IoUs."""
    candidates: List[Tuple[float, int, int]] = []
    for gi, g in enumerate(gt_boxes):
        for pi, p in enumerate(pred_boxes):
            score = iou_xyxy(g, p)
            if score >= min_iou:
                candidates.append((score, gi, pi))

    candidates.sort(key=lambda x: x[0], reverse=True)

    used_gt = set()
    used_pred = set()
    total = 0.0

    for score, gi, pi in candidates:
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        total += score

    return total


def grits_loc(gt_table: dict, pred_table: dict) -> float:
    """Location score from IoU matched cell boxes normalized by max cell count."""
    gt_cells = gt_table.get("cells", [])
    pred_cells = pred_table.get("cells", [])

    gt_boxes = [b for b in (cell_bbox_xyxy(c) for c in gt_cells) if b is not None]
    pred_boxes = [b for b in (cell_bbox_xyxy(c) for c in pred_cells) if b is not None]

    denom = max(len(gt_boxes), len(pred_boxes))
    if denom == 0:
        return 1.0

    matched_iou_sum = greedy_iou_match(gt_boxes, pred_boxes, min_iou=0.0)
    return matched_iou_sum / denom


def grits_top_paper_like(gt_table: dict, pred_table: dict) -> float:
    """Paper-like topology score from exact owner equality per aligned slot."""
    gt_grid, _ = build_slot_owner_grid(gt_table)
    pred_grid, _ = build_slot_owner_grid(pred_table)

    rows = max(len(gt_grid), len(pred_grid))
    cols = max(len(gt_grid[0]) if gt_grid else 0, len(pred_grid[0]) if pred_grid else 0)
    if rows == 0 or cols == 0:
        return 1.0

    tp = fp = fn = 0
    for r in range(rows):
        for c in range(cols):
            g = gt_grid[r][c] if r < len(gt_grid) and c < (len(gt_grid[0]) if gt_grid else 0) else None
            p = pred_grid[r][c] if r < len(pred_grid) and c < (len(pred_grid[0]) if pred_grid else 0) else None

            if g is None and p is None:
                continue
            if g is not None and p is not None and g == p:
                tp += 1
            else:
                if p is not None:
                    fp += 1
                if g is not None:
                    fn += 1

    return f1_from_counts(tp, fp, fn)


def grits_con_paper_like(gt_table: dict, pred_table: dict) -> float:
    """Paper-like content score requiring matching slot occupancy and text."""
    gt_grid, gt_text = build_slot_owner_grid(gt_table)
    pred_grid, pred_text = build_slot_owner_grid(pred_table)

    rows = max(len(gt_grid), len(pred_grid))
    cols = max(len(gt_grid[0]) if gt_grid else 0, len(pred_grid[0]) if pred_grid else 0)
    if rows == 0 or cols == 0:
        return 1.0

    tp = fp = fn = 0
    for r in range(rows):
        for c in range(cols):
            g_owner = gt_grid[r][c] if r < len(gt_grid) and c < (len(gt_grid[0]) if gt_grid else 0) else None
            p_owner = pred_grid[r][c] if r < len(pred_grid) and c < (len(pred_grid[0]) if pred_grid else 0) else None
            g_text = gt_text.get(g_owner, "") if g_owner else ""
            p_text = pred_text.get(p_owner, "") if p_owner else ""

            if not g_text and not p_text:
                continue
            if g_owner is not None and p_owner is not None and g_text == p_text:
                tp += 1
            else:
                if p_text:
                    fp += 1
                if g_text:
                    fn += 1

    return f1_from_counts(tp, fp, fn)


def grits_loc_paper_like(gt_table: dict, pred_table: dict) -> float:
    """Paper-like location score from per-slot bbox IoU averaging over GT slots."""
    gt_grid, _ = build_slot_owner_grid(gt_table)
    pred_grid, _ = build_slot_owner_grid(pred_table)
    gt_slot_bbox = slot_bbox_map(gt_table)
    pred_slot_bbox = slot_bbox_map(pred_table)

    rows = max(len(gt_grid), len(pred_grid))
    cols = max(len(gt_grid[0]) if gt_grid else 0, len(pred_grid[0]) if pred_grid else 0)
    if rows == 0 or cols == 0:
        return 1.0

    score_sum = 0.0
    gt_occupied = 0

    for r in range(rows):
        for c in range(cols):
            g_owner = gt_grid[r][c] if r < len(gt_grid) and c < (len(gt_grid[0]) if gt_grid else 0) else None
            p_owner = pred_grid[r][c] if r < len(pred_grid) and c < (len(pred_grid[0]) if pred_grid else 0) else None
            if g_owner is None:
                continue

            gt_occupied += 1
            g_bbox = gt_slot_bbox.get((r, c))
            p_bbox = pred_slot_bbox.get((r, c)) if p_owner is not None else None

            if g_bbox is None or p_bbox is None:
                continue
            score_sum += iou_xyxy(g_bbox, p_bbox)

    if gt_occupied == 0:
        return 1.0
    return score_sum / gt_occupied


def compute_table_scores(gt_table: dict, pred_table: dict, mode: str) -> Tuple[float, float, float, float]:
    """Compute per-table GRiTS components under requested mode."""
    if mode == "paper_like":
        top = grits_top_paper_like(gt_table, pred_table)
        con = grits_con_paper_like(gt_table, pred_table)
        loc = grits_loc_paper_like(gt_table, pred_table)
    else:
        top = grits_top(gt_table, pred_table)
        con = grits_con(gt_table, pred_table)
        loc = grits_loc(gt_table, pred_table)

    grits = (top + con + loc) / 3.0
    return top, con, loc, grits


def match_tables(
    gt_tables: List[dict], pred_tables: List[dict], strategy: str = "table_id", iou_threshold: float = 0.3
) -> List[Tuple[dict, dict, float, str]]:
    """
    Match gt/pred tables.

    Returns tuples: (gt_table, pred_table, match_score, method)
    """
    if strategy not in {"table_id", "bbox"}:
        raise ValueError("strategy must be 'table_id' or 'bbox'")

    pairs: List[Tuple[dict, dict, float, str]] = []

    if strategy == "table_id":
        pred_by_id = {t.get("table_id"): t for t in pred_tables if t.get("table_id")}
        for gt in gt_tables:
            gt_id = gt.get("table_id")
            if gt_id and gt_id in pred_by_id:
                pairs.append((gt, pred_by_id[gt_id], 1.0, "table_id"))
        return pairs

    # bbox matching within same page using greedy IoU
    candidates: List[Tuple[float, int, int]] = []
    for gi, gt in enumerate(gt_tables):
        gt_bbox = table_bbox_xyxy(gt)
        gt_page = gt.get("page_number")
        if gt_bbox is None:
            continue
        for pi, pred in enumerate(pred_tables):
            pred_bbox = table_bbox_xyxy(pred)
            pred_page = pred.get("page_number")
            if pred_bbox is None:
                continue
            if gt_page != pred_page:
                continue
            score = iou_xyxy(gt_bbox, pred_bbox)
            if score >= iou_threshold:
                candidates.append((score, gi, pi))

    candidates.sort(key=lambda x: x[0], reverse=True)
    used_gt = set()
    used_pred = set()

    for score, gi, pi in candidates:
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        pairs.append((gt_tables[gi], pred_tables[pi], score, "bbox"))

    return pairs


def evaluate_grits(args: argparse.Namespace) -> dict:
    """Run GRiTS evaluation and return report payload."""
    project_dir = Path(__file__).resolve().parents[1]
    gt_path = resolve_path(args.gt, project_dir)
    pred_path = resolve_path(args.pred, project_dir)

    if not gt_path.exists():
        raise FileNotFoundError(f"Ground-truth JSON not found: {gt_path}")
    if not pred_path.exists():
        raise FileNotFoundError(f"Prediction JSON not found: {pred_path}")

    gt_payload = json.loads(gt_path.read_text(encoding="utf-8"))
    pred_payload = json.loads(pred_path.read_text(encoding="utf-8"))

    gt_tables = gt_payload.get("tables", [])
    pred_tables = pred_payload.get("tables", [])

    matches = match_tables(
        gt_tables,
        pred_tables,
        strategy=args.match_by,
        iou_threshold=args.table_iou_threshold,
    )

    per_table = []
    weighted_sum_top = 0.0
    weighted_sum_con = 0.0
    weighted_sum_loc = 0.0
    weighted_sum_grits = 0.0
    total_weight = 0

    for gt_table, pred_table, match_score, method in matches:
        top, con, loc, grits = compute_table_scores(gt_table, pred_table, args.mode)

        gt_rows, gt_cols = infer_grid_shape(gt_table)
        table_weight = max(1, gt_rows * gt_cols)

        weighted_sum_top += top * table_weight
        weighted_sum_con += con * table_weight
        weighted_sum_loc += loc * table_weight
        weighted_sum_grits += grits * table_weight
        total_weight += table_weight

        per_table.append(
            {
                "gt_table_id": gt_table.get("table_id"),
                "pred_table_id": pred_table.get("table_id"),
                "page_number": gt_table.get("page_number"),
                "match_method": method,
                "match_score": round(match_score, 4),
                "weight": table_weight,
                "grits_top": round(top, 4),
                "grits_con": round(con, 4),
                "grits_loc": round(loc, 4),
                "grits": round(grits, 4),
            }
        )

    matched_gt_ids = {item[0].get("table_id") for item in matches}
    matched_pred_ids = {item[1].get("table_id") for item in matches}

    unmatched_gt = [t.get("table_id") for t in gt_tables if t.get("table_id") not in matched_gt_ids]
    unmatched_pred = [t.get("table_id") for t in pred_tables if t.get("table_id") not in matched_pred_ids]

    if total_weight == 0:
        overall_top = overall_con = overall_loc = overall_grits = 0.0
    else:
        overall_top = weighted_sum_top / total_weight
        overall_con = weighted_sum_con / total_weight
        overall_loc = weighted_sum_loc / total_weight
        overall_grits = weighted_sum_grits / total_weight

    report = {
        "config": {
            "gt": str(gt_path),
            "pred": str(pred_path),
            "match_by": args.match_by,
            "table_iou_threshold": args.table_iou_threshold,
            "mode": args.mode,
        },
        "summary": {
            "gt_tables": len(gt_tables),
            "pred_tables": len(pred_tables),
            "matched_tables": len(matches),
            "unmatched_gt_tables": len(unmatched_gt),
            "unmatched_pred_tables": len(unmatched_pred),
            "grits_top": round(overall_top, 4),
            "grits_con": round(overall_con, 4),
            "grits_loc": round(overall_loc, 4),
            "grits": round(overall_grits, 4),
        },
        "unmatched": {
            "gt_table_ids": unmatched_gt,
            "pred_table_ids": unmatched_pred,
        },
        "per_table": per_table,
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate GRiTS-style table structure metrics")
    parser.add_argument("--gt", required=True, help="Ground-truth cv_handoff JSON")
    parser.add_argument("--pred", required=True, help="Predicted cv_handoff JSON")
    parser.add_argument(
        "--mode",
        choices=["grits_style", "paper_like"],
        default="grits_style",
        help="Scoring mode: grits_style (current default) or paper_like (stricter alignment)",
    )
    parser.add_argument(
        "--match-by",
        choices=["table_id", "bbox"],
        default="table_id",
        help="Table matching strategy before metric computation",
    )
    parser.add_argument(
        "--table-iou-threshold",
        type=float,
        default=0.3,
        help="IoU threshold for bbox table matching (used only when --match-by bbox)",
    )
    parser.add_argument(
        "--output",
        default="outputs/grits_results.json",
        help="Path to save GRiTS results JSON",
    )

    args = parser.parse_args()
    report = evaluate_grits(args)

    print("=" * 60)
    print("WaziGov GRiTS Evaluation")
    print("=" * 60)
    print(f"Mode:            {report['config']['mode']}")
    print(f"GT tables:       {report['summary']['gt_tables']}")
    print(f"Pred tables:     {report['summary']['pred_tables']}")
    print(f"Matched tables:  {report['summary']['matched_tables']}")
    print(f"GRiTS-Top:       {report['summary']['grits_top']:.4f}")
    print(f"GRiTS-Con:       {report['summary']['grits_con']:.4f}")
    print(f"GRiTS-Loc:       {report['summary']['grits_loc']:.4f}")
    print(f"GRiTS:           {report['summary']['grits']:.4f}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
