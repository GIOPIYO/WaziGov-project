# GRiTS Dual-Mode Comparison Guide

## Overview

The `evaluate_grits.py` script now supports two scoring modes designed to measure different aspects of table structure quality:

1. **grits_style** (default): Practical, robust scoring aligned with current CV module outputs
2. **paper_like**: Stricter, slot-aligned scoring closer to proposal-style structure evaluation

## Mode Differences

### grits_style (Practical Mode)

- **Topology (grits_top)**: Detects when cell boundaries change owners using boundary maps
- **Content (grits_con)**: Flexible text matching per slot; empty cells treated as acceptable variation
- **Geometry (grits_loc)**: Greedy 1-to-1 bbox IoU matching across all cells
- **Use case**: Quick QA checks, real-world handoff validation where minor geometry shifts are acceptable

### paper_like (Stricter Mode)

- **Topology (grits_top)**: Exact slot owner equality (stricter than boundary maps)
- **Content (grits_con)**: Stricter slot-aligned content; requires occupied slot occupancy match
- **Geometry (grits_loc)**: Per-slot bbox IoU averaging only over GT-occupied slots
- **Use case**: Research evaluation, detecting fine-grained structure errors, comparing models

## Synthetic Test Cases

Run the demo to generate 6 test cases covering common error types:

```bash
python scripts/grits_comparison_demo.py
```

This creates:
- `case_none` — perfect match (baseline)
- `case_missing_cells` — structural error (detection miss)
- `case_wrong_boundaries` — geometry error (boundary misalignment)
- `case_bad_text` — content error (OCR or extraction failure)
- `case_merged_cells` — span error (merged cell misclassification)
- `case_low_confidence` — confidence error (low model confidence)

## Example Results

### Missing Cells (Structural Error)
```
grits_style:
  GRiTS-Top: 0.9697  (boundary logic tolerates some cell absences)
  GRiTS-Con: 0.8571  (text matching still works for present cells)
  GRiTS-Loc: 0.7500  (geometry unaffected by missing cells)
  GRiTS: 0.8589

paper_like:
  GRiTS-Top: 0.8571  (strict slot equality penalizes absence)
  GRiTS-Con: 0.8571  (same slot-based text matching)
  GRiTS-Loc: 0.7500  (same per-slot geometry)
  GRiTS: 0.8214
```

**Interpretation**: paper_like is stricter on structure (Top: 0.8571 vs 0.9697). Use paper_like to catch structural errors.

### Wrong Boundaries (Geometry Error)
```
grits_style:
  GRiTS-Loc: 0.7433 (greedy matching tolerates minor shifts)
  GRiTS: 0.9144

paper_like:
  GRiTS-Loc: 0.7433 (per-slot matching same result as greedy for this case)
  GRiTS: 0.9144
```

**Interpretation**: Both modes equally sensitive to geometry errors. Geometry is independent of scoring mode.

## Running Comparisons

### Compare both modes on a test case:
```bash
# grits_style (practical, tolerant)
python scripts/evaluate_grits.py \
  --gt outputs/grits_demo_inputs/case_missing_cells_gt.json \
  --pred outputs/grits_demo_inputs/case_missing_cells_pred.json \
  --mode grits_style \
  --output outputs/missing_cells_style_results.json

# paper_like (strict, research-grade)
python scripts/evaluate_grits.py \
  --gt outputs/grits_demo_inputs/case_missing_cells_gt.json \
  --pred outputs/grits_demo_inputs/case_missing_cells_pred.json \
  --mode paper_like \
  --output outputs/missing_cells_paper_results.json
```

## Recommendations

| Scenario | Recommended Mode | Reason |
|----------|------------------|--------|
| QA/validation in production | grits_style | Tolerates minor geometry shifts, faster to iterate |
| Research/benchmarking | paper_like | Strict measurement, closer to structure-only metrics |
| Debugging model errors | Both | Compare mode differences to isolate error type |
| Comparing two models | paper_like | Consistent, strict comparison |

## Metric Interpretation

- **GRiTS > 0.85**: Good table structure extraction
- **GRiTS 0.70-0.85**: Acceptable with minor corrections needed
- **GRiTS < 0.70**: Significant structure or content errors

Per-component scores indicate error type:
- Low grits_top: Structure/topology errors (missing/extra rows/columns)
- Low grits_con: Content errors (OCR issues, text extraction failure)
- Low grits_loc: Geometry errors (boundary misalignment)
