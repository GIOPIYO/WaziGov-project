"""
WaziGov CV->NLP Handoff QA Checker
==================================
Validate a generated cv_handoff JSON file and report readiness for NLP integration.

Usage:
    python scripts/qa_handoff.py --input outputs/cv_handoff.json
"""

import argparse
import json
from pathlib import Path


def run_checks(payload):
    report = {
        "totals": {},
        "warnings": [],
        "errors": [],
        "checks": {},
    }

    tables = payload.get("tables", [])
    report["totals"]["tables"] = len(tables)

    total_cells = 0
    empty_text_cells = 0
    ocr_cells = 0
    continuation_tables = 0
    merged_cells = 0
    low_conf_cells = 0

    required_root = ["document_id", "source_file", "page_count", "processed_at", "model_version", "tables"]
    for key in required_root:
        if key not in payload:
            report["errors"].append(f"missing_root_field:{key}")

    for table in tables:
        required_table = ["table_id", "page_number", "bbox", "grid", "continuation", "cells", "validation"]
        for key in required_table:
            if key not in table:
                report["errors"].append(f"{table.get('table_id', 'unknown')}:missing_table_field:{key}")

        continuation = table.get("continuation", {})
        if continuation.get("is_continuation") or continuation.get("continues_on_next_page"):
            continuation_tables += 1

        cells = table.get("cells", [])
        total_cells += len(cells)
        for cell in cells:
            if not cell.get("raw_text", "").strip():
                empty_text_cells += 1
            if cell.get("text_source") == "ocr":
                ocr_cells += 1
            if cell.get("row_span", 1) > 1 or cell.get("col_span", 1) > 1:
                merged_cells += 1
            if float(cell.get("confidence", 1.0)) < 0.5:
                low_conf_cells += 1

    report["totals"]["cells"] = total_cells
    report["totals"]["empty_text_cells"] = empty_text_cells
    report["totals"]["ocr_cells"] = ocr_cells
    report["totals"]["continuation_tables"] = continuation_tables
    report["totals"]["merged_cells"] = merged_cells
    report["totals"]["low_conf_cells"] = low_conf_cells

    if total_cells == 0:
        report["errors"].append("no_cells_found")

    if total_cells > 0 and empty_text_cells / total_cells > 0.4:
        report["warnings"].append("high_empty_text_ratio")

    if total_cells > 0 and low_conf_cells / total_cells > 0.3:
        report["warnings"].append("high_low_confidence_cell_ratio")

    report["checks"]["has_root_fields"] = len([e for e in report["errors"] if e.startswith("missing_root_field")]) == 0
    report["checks"]["has_cells"] = total_cells > 0
    report["checks"]["text_coverage_ok"] = not (total_cells > 0 and empty_text_cells / total_cells > 0.4)
    report["checks"]["confidence_coverage_ok"] = not (total_cells > 0 and low_conf_cells / total_cells > 0.3)

    report["ready_for_nlp"] = len(report["errors"]) == 0 and report["checks"]["has_cells"]
    return report


def main():
    parser = argparse.ArgumentParser(description="Validate cv_handoff JSON for NLP integration")
    parser.add_argument("--input", required=True, help="Path to cv_handoff JSON")
    parser.add_argument("--output", default=None, help="Optional path to save QA report JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    report = run_checks(payload)

    print("=" * 60)
    print("WaziGov CV->NLP Handoff QA")
    print("=" * 60)
    print(f"Input: {input_path}")
    print(f"Tables: {report['totals']['tables']}")
    print(f"Cells: {report['totals']['cells']}")
    print(f"Empty text cells: {report['totals']['empty_text_cells']}")
    print(f"OCR cells: {report['totals']['ocr_cells']}")
    print(f"Merged cells: {report['totals']['merged_cells']}")
    print(f"Continuation tables: {report['totals']['continuation_tables']}")
    print(f"Ready for NLP: {report['ready_for_nlp']}")

    if report["warnings"]:
        print("Warnings:")
        for warning in report["warnings"]:
            print(f"  - {warning}")

    if report["errors"]:
        print("Errors:")
        for error in report["errors"]:
            print(f"  - {error}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"QA report saved: {output_path}")


if __name__ == "__main__":
    main()
