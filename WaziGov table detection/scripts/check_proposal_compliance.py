"""
WaziGov Proposal Compliance Checker
==================================
Checks key proposal-aligned metrics for Stage 1 table detection workflow.

Usage:
    python scripts/check_proposal_compliance.py \
        --labelstudio-json data/annotations/labelstudio/project-3-at-2026-03-24-23-06-b3b74b08.json \
        --xml-dir data/annotations/pascal_voc_selected \
        --split-dir data/splits
"""

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def read_split_count(path: Path) -> int:
    if not path.exists():
        return 0
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return len(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check compliance against proposal targets")
    parser.add_argument("--labelstudio-json", type=str, required=True, help="Label Studio export JSON path")
    parser.add_argument("--xml-dir", type=str, required=True, help="Directory with converted XML annotations")
    parser.add_argument("--split-dir", type=str, default="data/splits", help="Directory with split txt files")
    parser.add_argument("--strict", action="store_true", help="Return non-zero exit code if non-compliant")
    args = parser.parse_args()

    proposal_targets = {
        "annotated_pages_target": 100,
        "table_boxes_min": 150,
        "table_boxes_max": 200,
        "split_ratio": (0.70, 0.15, 0.15),
    }

    labelstudio_path = Path(args.labelstudio_json)
    xml_dir = Path(args.xml_dir)
    split_dir = Path(args.split_dir)

    tasks = json.loads(labelstudio_path.read_text(encoding="utf-8"))
    total_tasks = len(tasks)
    tasks_with_boxes = 0
    for task in tasks:
        annotations = task.get("annotations", [])
        if not annotations:
            continue
        results = annotations[0].get("result", [])
        if results:
            tasks_with_boxes += 1

    xml_files = sorted(xml_dir.glob("*.xml"))
    box_count = 0
    for xml_file in xml_files:
        root = ET.parse(xml_file).getroot()
        box_count += len(root.findall("object"))

    train_count = read_split_count(split_dir / "train.txt")
    val_count = read_split_count(split_dir / "val.txt")
    test_count = read_split_count(split_dir / "test.txt")
    split_total = train_count + val_count + test_count

    train_ratio = (train_count / split_total) if split_total else 0.0
    val_ratio = (val_count / split_total) if split_total else 0.0
    test_ratio = (test_count / split_total) if split_total else 0.0

    pages_ok = total_tasks >= proposal_targets["annotated_pages_target"]
    boxes_ok = proposal_targets["table_boxes_min"] <= box_count <= proposal_targets["table_boxes_max"]

    # Allow small tolerance due integer rounding on split sizes.
    tol = 0.03
    split_ok = (
        abs(train_ratio - proposal_targets["split_ratio"][0]) <= tol
        and abs(val_ratio - proposal_targets["split_ratio"][1]) <= tol
        and abs(test_ratio - proposal_targets["split_ratio"][2]) <= tol
    )

    print("=" * 60)
    print("WaziGov Proposal Compliance Report")
    print("=" * 60)
    print(f"Annotated tasks (Label Studio): {total_tasks}")
    print(f"Tasks with boxes: {tasks_with_boxes}")
    print(f"Converted XML files: {len(xml_files)}")
    print(f"Total table boxes: {box_count}")
    print(f"Splits -> train: {train_count}, val: {val_count}, test: {test_count}")
    print(f"Split ratios -> train: {train_ratio:.3f}, val: {val_ratio:.3f}, test: {test_ratio:.3f}")
    print()
    print(f"Target check - Annotated pages >= 100: {'PASS' if pages_ok else 'FAIL'}")
    print(f"Target check - Table boxes in [150, 200]: {'PASS' if boxes_ok else 'FAIL'}")
    print(f"Target check - Split ratio approx 70/15/15: {'PASS' if split_ok else 'FAIL'}")

    compliant = pages_ok and boxes_ok and split_ok
    print()
    print(f"Overall proposal compliance: {'COMPLIANT' if compliant else 'PARTIAL / NON-COMPLIANT'}")

    if args.strict and not compliant:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
