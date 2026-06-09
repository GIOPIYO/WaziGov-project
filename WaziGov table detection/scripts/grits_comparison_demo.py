"""
GRiTS Dual-Mode Comparison Demo
================================
Generate synthetic table mismatches and score them with both grits_style and paper_like
to demonstrate mode sensitivity and error type detection.

Usage:
    python scripts/grits_comparison_demo.py --output outputs/grits_comparison_demo.json
"""

import argparse
import copy
import json
import random
from pathlib import Path


def create_simple_table(table_id: str, page_num: int, rows: int, cols: int) -> dict:
    """Create a simple ground-truth table with basic structure."""
    cells = []
    for r in range(rows):
        for c in range(cols):
            cells.append({
                "cell_id": f"{table_id}_r{r}_c{c}",
                "row_idx": r,
                "col_idx": c,
                "row_span": 1,
                "col_span": 1,
                "cell_type": "header" if r == 0 else "data",
                "hierarchy_level": 1 if r == 0 else None,
                "bbox": {
                    "xmin": c * 100.0,
                    "ymin": r * 50.0,
                    "xmax": (c + 1) * 100.0,
                    "ymax": (r + 1) * 50.0,
                },
                "raw_text": f"Cell_R{r}_C{c}",
                "text_source": "pdf_text",
                "image_b64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP49+8fAAX4AvvKn0zIAAAAAElFTkSuQmCC",
                "confidence": 0.95,
            })

    return {
        "table_id": table_id,
        "page_number": page_num,
        "bbox": {
            "xmin": 0.0,
            "ymin": 0.0,
            "xmax": cols * 100.0,
            "ymax": rows * 50.0,
        },
        "confidence": 0.98,
        "label": "table",
        "grid": {"rows": rows, "cols": cols},
        "continuation": {
            "is_continuation": False,
            "continues_from": None,
            "continues_on_next_page": False,
            "linked_table_id": None,
            "match_score": 0.0,
        },
        "cells": cells,
        "validation": {"is_valid": True, "checks": [], "warnings": []},
    }


def mutate_table_structure(table: dict, mutation_type: str) -> dict:
    """Apply a specific type of error to a table copy."""
    result = copy.deepcopy(table)

    if mutation_type == "missing_cells":
        # Remove some cells to simulate detection miss
        if result["cells"]:
            remove_count = max(1, len(result["cells"]) // 4)
            indices = random.sample(range(len(result["cells"])), remove_count)
            for idx in sorted(indices, reverse=True):
                result["cells"].pop(idx)

    elif mutation_type == "wrong_boundaries":
        # Shift cell boundaries
        for cell in result["cells"]:
            for key in ["xmin", "ymin", "xmax", "ymax"]:
                cell["bbox"][key] += random.uniform(-10.0, 10.0)

    elif mutation_type == "bad_text":
        # Corrupt text in half the cells
        for i, cell in enumerate(result["cells"]):
            if i % 2 == 0:
                cell["raw_text"] = "CORRUPTED_" + cell["raw_text"]
                cell["text_source"] = "ocr"

    elif mutation_type == "merged_cells":
        # Mark some adjacent cells as merged
        for i, cell in enumerate(result["cells"]):
            if i % 5 == 0 and i < len(result["cells"]) - 1:
                cell["row_span"] = 2

    elif mutation_type == "low_confidence":
        # Mark all cells with low confidence
        for cell in result["cells"]:
            cell["confidence"] = 0.5

    return result


def generate_test_handoffs() -> dict:
    """Generate GT + prediction handoff files with various mutation types."""
    random.seed(42)

    gt_table = create_simple_table("page_001_table_00", 1, 4, 3)
    mutations = [
        "none",
        "missing_cells",
        "wrong_boundaries",
        "bad_text",
        "merged_cells",
        "low_confidence",
    ]

    test_cases = {}
    for mut in mutations:
        case_name = f"case_{mut}"
        if mut == "none":
            pred_table = copy.deepcopy(gt_table)
        else:
            pred_table = mutate_table_structure(gt_table, mut)

        gt_payload = {
            "document_id": "gt_demo_doc",
            "source_file": "test.pdf",
            "page_count": 1,
            "processed_at": "2026-04-17T00:00:00Z",
            "model_version": "ground_truth",
            "tables": [gt_table],
        }

        pred_payload = {
            "document_id": "pred_demo_doc",
            "source_file": "test.pdf",
            "page_count": 1,
            "processed_at": "2026-04-17T00:00:00Z",
            "model_version": "demo_variant",
            "tables": [pred_table],
        }

        test_cases[case_name] = {
            "description": f"Mutation: {mut}",
            "gt_payload": gt_payload,
            "pred_payload": pred_payload,
        }

    return test_cases


def save_test_case(workdir: Path, case_name: str, gt_payload: dict, pred_payload: dict) -> tuple:
    """Save GT and prediction payloads."""
    workdir.mkdir(parents=True, exist_ok=True)
    gt_path = workdir / f"{case_name}_gt.json"
    pred_path = workdir / f"{case_name}_pred.json"
    gt_path.write_text(json.dumps(gt_payload, indent=2))
    pred_path.write_text(json.dumps(pred_payload, indent=2))
    return gt_path, pred_path


def main():
    parser = argparse.ArgumentParser(description="Generate GRiTS dual-mode comparison demo")
    parser.add_argument("--output", default="outputs/grits_comparison_demo.json", help="Output report path")
    args = parser.parse_args()

    # Generate test cases
    test_cases = generate_test_handoffs()
    workdir = Path(args.output).parent / "grits_demo_inputs"

    # This script generates the synthetic files but doesn't run the evaluator
    # (that would require subprocess, which is best done in bash/powershell)
    report = {
        "description": "GRiTS Dual-Mode Comparison Demo",
        "test_cases": {},
    }

    for case_name, case_data in test_cases.items():
        gt_path, pred_path = save_test_case(
            workdir, case_name, case_data["gt_payload"], case_data["pred_payload"]
        )
        report["test_cases"][case_name] = {
            "description": case_data["description"],
            "gt_file": str(gt_path),
            "pred_file": str(pred_path),
            "commands": {
                "grits_style": f"python scripts/evaluate_grits.py --gt {gt_path} --pred {pred_path} --mode grits_style",
                "paper_like": f"python scripts/evaluate_grits.py --gt {gt_path} --pred {pred_path} --mode paper_like",
            },
        }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2))

    print("=" * 70)
    print("GRiTS Dual-Mode Comparison Demo Setup")
    print("=" * 70)
    print(f"\nGenerated {len(test_cases)} test cases in: {workdir}")
    print(f"Report saved: {output_path}\n")

    print("Test cases generated:")
    for case_name, case_info in report["test_cases"].items():
        print(f"\n{case_name}: {case_info['description']}")
        print(f"  GT:   {case_info['gt_file']}")
        print(f"  Pred: {case_info['pred_file']}")
        print(f"\n  Test with grits_style mode:")
        print(f"    {case_info['commands']['grits_style']}")
        print(f"\n  Test with paper_like mode:")
        print(f"    {case_info['commands']['paper_like']}")

    print("\n" + "=" * 70)
    print("Usage: Run the commands above to compare scores between modes.")
    print("Expected: paper_like mode should be stricter (lower scores) on structure errors.")
    print("          grits_style should be more tolerant of minor geometry variations.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
