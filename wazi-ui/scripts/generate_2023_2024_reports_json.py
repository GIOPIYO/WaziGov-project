"""Generate a consolidated 2023-2024 COB/OAG JSON bundle.

This script uses the table-detection module to produce document-level JSON
outputs for the relevant PDFs and then combines them into a single bundle that
the specs prototype can consume.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def load_inference_module(inference_path: Path):
    """Load the table-detection inference script as a Python module."""
    spec = importlib.util.spec_from_file_location("wazi_table_inference", inference_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load inference module from {inference_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_title_from_filename(filename: str) -> str:
    """Turn a report filename into a readable fallback title."""
    stem = Path(filename).stem
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem.title()


def classify_report(filename: str) -> dict:
    """Best-effort classification for the citizen-facing bundle."""
    lower_name = filename.lower()
    if "auditor" in lower_name or "oag" in lower_name:
        return {"institution": "OAG", "report_family": "Audit"}
    if "green-book" in lower_name or "budget-implementation" in lower_name or "cob" in lower_name:
        return {"institution": "COB", "report_family": "Budget"}
    return {"institution": "Unknown", "report_family": "Report"}


def build_year_regex(fiscal_year: str) -> re.Pattern[str]:
    """Build a loose regex that matches common year separators."""
    years = re.findall(r"\d{4}", fiscal_year)
    if len(years) >= 2:
        start_year, end_year = years[0], years[1]
        pattern = rf"{start_year}[\W_/-]*{end_year}"
    else:
        pattern = re.escape(fiscal_year)
    return re.compile(pattern, re.IGNORECASE)


def discover_reports(pdf_dir: Path, fiscal_year: str, explicit_pdfs: Iterable[Path] | None = None) -> list[Path]:
    """Discover PDFs that look relevant to the requested fiscal year."""
    if explicit_pdfs:
        return [pdf for pdf in explicit_pdfs if pdf.exists()]

    year_regex = build_year_regex(fiscal_year)
    reports: list[Path] = []

    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        lower_name = pdf_path.name.lower()
        if year_regex.search(lower_name):
            reports.append(pdf_path)
            continue

        if ("auditor" in lower_name or "oag" in lower_name) and any(year in lower_name for year in ("2023", "2024")):
            reports.append(pdf_path)
            continue

        if "green-book" in lower_name and "2024" in lower_name:
            reports.append(pdf_path)

    return reports


def resolve_report_paths(report_paths: list[str], table_detection_root: Path) -> list[Path]:
    """Resolve explicit report paths relative to the repo or table-detection root."""
    resolved_paths: list[Path] = []
    for raw_path in report_paths:
        candidate = Path(raw_path)
        if candidate.is_absolute() and candidate.exists():
            resolved_paths.append(candidate)
            continue

        repo_candidate = (table_detection_root.parent / candidate).resolve()
        if repo_candidate.exists():
            resolved_paths.append(repo_candidate)
            continue

        td_candidate = (table_detection_root / candidate).resolve()
        if td_candidate.exists():
            resolved_paths.append(td_candidate)
            continue

        raise FileNotFoundError(f"Report not found: {raw_path}")

    return resolved_paths


def write_bundle_json(bundle_path: Path, payload: dict) -> None:
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bundle_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a full 2023-2024 COB/OAG JSON bundle using the table detection module"
    )
    parser.add_argument(
        "--fiscal-year",
        default="2023-2024",
        help="Fiscal year token used to discover report PDFs",
    )
    parser.add_argument(
        "--pdf",
        action="append",
        default=[],
        help="Optional explicit PDF path. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--pdf-dir",
        default=None,
        help="Directory containing report PDFs. Defaults to WaziGov table detection/data/pdfs.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path for the consolidated JSON bundle. Defaults to specs/outputs/cob_oag_2023_2024_full.json.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=None,
        help="Directory for per-report detector outputs. Defaults to specs/outputs/cob_oag_2023_2024_artifacts.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Table detection model path or Hugging Face model name.",
    )
    parser.add_argument(
        "--structure-model",
        default="microsoft/table-transformer-structure-recognition",
        help="Structure recognition model path or Hugging Face model name.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Detection confidence threshold.",
    )
    parser.add_argument(
        "--structure-threshold",
        type=float,
        default=0.5,
        help="Structure recognition confidence threshold.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page cap for fast smoke tests.",
    )
    parser.add_argument(
        "--skip-structure",
        action="store_true",
        help="Skip structure recognition and generate table detection only.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Rebuild per-report outputs even when cached JSON already exists.",
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    specs_root = script_path.parents[1]
    repo_root = specs_root.parent
    table_detection_root = repo_root / "WaziGov table detection"

    pdf_dir = Path(args.pdf_dir) if args.pdf_dir else table_detection_root / "data" / "pdfs"
    output_path = Path(args.output) if args.output else specs_root / "outputs" / "cob_oag_2023_2024_full.json"
    artifact_dir = Path(args.artifact_dir) if args.artifact_dir else specs_root / "outputs" / "cob_oag_2023_2024_artifacts"

    if args.pdf:
        report_paths = resolve_report_paths(args.pdf, table_detection_root)
    else:
        report_paths = discover_reports(pdf_dir, args.fiscal_year)

    if not report_paths:
        print(f"No report PDFs found for fiscal year {args.fiscal_year}", file=sys.stderr)
        return 1

    inference_path = table_detection_root / "scripts" / "inference.py"
    inference = load_inference_module(inference_path)

    device = inference.torch.device("cuda" if inference.torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model_path = args.model or str(table_detection_root / "models" / "table_detection" / "final_model")
    model_path_resolved = inference.resolve_path(model_path, table_detection_root)
    if not model_path.startswith("microsoft/") and not Path(model_path_resolved).exists():
        model_path = "microsoft/table-transformer-detection"
        model_path_resolved = model_path

    model, processor = inference.load_model(str(model_path_resolved), device)

    structure_model = None
    structure_processor = None
    if not args.skip_structure:
        structure_model_path = args.structure_model
        if structure_model_path.startswith("microsoft/"):
            structure_model_resolved = structure_model_path
        else:
            structure_model_resolved = inference.resolve_path(structure_model_path, table_detection_root)
            if not Path(structure_model_resolved).exists():
                structure_model_resolved = "microsoft/table-transformer-structure-recognition"
        structure_model, structure_processor = inference.load_structure_model(str(structure_model_resolved), device)

    discovered_reports = []
    for pdf_path in report_paths:
        metadata = classify_report(pdf_path.name)
        report_artifact_dir = artifact_dir / pdf_path.stem
        report_artifact_dir.mkdir(parents=True, exist_ok=True)
        cv_output_path = report_artifact_dir / f"{pdf_path.stem}_cv_handoff.json"

        if args.overwrite or not cv_output_path.exists():
            inference.process_pdf(
                pdf_path=pdf_path,
                model=model,
                processor=processor,
                device=device,
                output_dir=str(report_artifact_dir),
                threshold=args.threshold,
                model_version=str(model_path_resolved),
                cv_output_path=cv_output_path,
                structure_model=structure_model,
                structure_processor=structure_processor,
                structure_threshold=args.structure_threshold,
                max_pages=args.max_pages,
                use_pdf_table_finder=True,
                use_backup_detector=True,
            )
        else:
            print(f"Reusing cached detector output: {cv_output_path}")

        with open(cv_output_path, "r", encoding="utf-8") as handle:
            document_payload = json.load(handle)

        discovered_reports.append(
            {
                "report_id": pdf_path.stem,
                "institution": metadata["institution"],
                "report_family": metadata["report_family"],
                "title": clean_title_from_filename(pdf_path.name),
                "fiscal_year": args.fiscal_year,
                "source_file": str(pdf_path.relative_to(repo_root)),
                "artifact_dir": str(report_artifact_dir.relative_to(repo_root)),
                "cv_output_file": str(cv_output_path.relative_to(repo_root)),
                "page_count": int(document_payload.get("page_count", 0)),
                "table_count": len(document_payload.get("tables", [])),
                "document": document_payload,
            }
        )

    bundle_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fiscal_year": args.fiscal_year,
        "source_directory": str(pdf_dir.relative_to(repo_root)) if pdf_dir.is_relative_to(repo_root) else str(pdf_dir),
        "report_count": len(discovered_reports),
        "selection_mode": "explicit" if args.pdf else "auto",
        "reports": discovered_reports,
    }

    write_bundle_json(output_path, bundle_payload)
    print(f"Bundle saved: {output_path}")
    print(f"Reports included: {len(discovered_reports)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())