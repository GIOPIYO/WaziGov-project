"""
WaziGov Generate Citizen Data
=============================
Produces a clean, County-centric JSON file for website use.
Uses the fine-tuned model to extract transparency data and strips all technical noise.

Output format: { "counties": { "Nairobi": { "budget": ..., "projects": [...] }, ... } }

Changes from original:
  - CV noise (bbox, image_b64, confidence, cell metadata) is stripped from each
    document BEFORE it reaches the extractor, so the extractor only ever sees
    clean text-only table data.
  - `strip_document` replaces the old end-of-pipeline `strip_metadata` for the
    document payloads; the final `strip_metadata` pass is kept as a safety net.
  - `_raw` amount fields (e.g. amount_kshs_raw) are removed from the citizen
    bundle since the website only needs the parsed integer.
  - County keys are normalised (trailing "County" removed) so lookups are simple:
    data.counties["Nairobi"] not data.counties["Nairobi County"].
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
import importlib.util
import re
import torch
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*pin_memory.*")


# ─── module loader ────────────────────────────────────────────────────────────

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not (spec and spec.loader):
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ─── stripping helpers ────────────────────────────────────────────────────────

# Fields that are purely CV/ML artefacts with no citizen value
_CV_FIELDS = {
    "bbox", "image_b64", "confidence", "match_score", "linked_table_id",
    "_profile", "text_source", "cell_type", "hierarchy_level",
    "row_span", "col_span", "cell_id",
}

# Fields that duplicate the parsed integer (website uses amount_kshs, not the raw string)
_RAW_FIELDS = {k for k in dir(str) if k.endswith("_raw")} | {
    "amount_kshs_raw", "total_budget_kshs_raw",
    "executive_budget_kshs_raw", "assembly_budget_kshs_raw",
}


def strip_document(doc: dict) -> dict:
    """
    Strip a single document payload (the value of report["document"]) down to
    text-only table data.  Mutates and returns a NEW dict.

    Before:
        table -> cells -> [{ cell_id, row_idx, col_idx, row_span, col_span,
                              cell_type, hierarchy_level, bbox, raw_text,
                              text_source, image_b64, confidence }]

    After:
        table -> cells -> [{ row_idx, col_idx, raw_text }]

    All table-level CV fields (bbox, confidence, label, continuation, validation,
    grid) are also removed; only table_id, page_number, and cells survive.
    """
    clean_doc = {
        "document_id": doc.get("document_id"),
        "source_file": doc.get("source_file"),
        "page_count":  doc.get("page_count"),
        "processed_at": doc.get("processed_at"),
        "tables": [],
    }

    for table in doc.get("tables", []):
        clean_cells = []
        for cell in table.get("cells", []):
            text = (cell.get("raw_text") or "").strip()
            if text:  # skip empty cells entirely
                clean_cells.append({
                    "row_idx": cell["row_idx"],
                    "col_idx": cell["col_idx"],
                    "raw_text": text,
                })

        # Only keep the table if it has at least one non-empty cell
        if clean_cells:
            clean_doc["tables"].append({
                "table_id":    table["table_id"],
                "page_number": table["page_number"],
                "cells":       clean_cells,
            })

    return clean_doc


def strip_metadata(data):
    """
    Recursive safety-net pass: remove any remaining CV fields and _raw strings
    that may have slipped through (e.g. from the extractor output itself).
    """
    if isinstance(data, list):
        return [strip_metadata(item) for item in data]
    if isinstance(data, dict):
        remove = _CV_FIELDS | _RAW_FIELDS
        return {k: strip_metadata(v) for k, v in data.items() if k not in remove}
    return data


def strip_internal_descriptions(data):
    """
    Remove _description and _columns keys that are useful for developers
    but add noise to a citizen-facing payload.
    """
    if isinstance(data, list):
        return [strip_internal_descriptions(item) for item in data]
    if isinstance(data, dict):
        return {
            k: strip_internal_descriptions(v)
            for k, v in data.items()
            if not k.startswith("_")
        }
    return data


# ─── county key normalisation ─────────────────────────────────────────────────

def normalise_county_key(name: str) -> str:
    """
    'Nairobi County' -> 'Nairobi'
    'Trans Nzoia County' -> 'Trans Nzoia'
    Already-clean names are returned as-is.
    """
    return re.sub(r"\s+County\s*$", "", name.strip(), flags=re.IGNORECASE).strip()


def rekey_counties(sections: dict) -> dict:
    """
    Walk the extracted data and re-key any list whose items have a 'county'
    field so each county's data is directly addressable by name.
    """
    result = {}
    for section_name, section in sections.items():
        if not isinstance(section, dict):
            result[section_name] = section
            continue

        data_list = section.get("data")
        if not isinstance(data_list, list):
            result[section_name] = section
            continue

        # Turn list into a county-keyed dict
        keyed = {}
        for row in data_list:
            county_raw = row.get("county", "")
            key = normalise_county_key(county_raw)
            if not key:
                continue
            # Drop the now-redundant 'county' field from the row values
            entry = {k: v for k, v in row.items() if k != "county"}
            keyed[key] = entry

        result[section_name] = {
            k: v for k, v in section.items()
            if k not in ("data", "total_counties")
        }
        result[section_name]["by_county"] = keyed
        result[section_name]["total_counties"] = len(keyed)

    return result


# ─── report classification ────────────────────────────────────────────────────

def classify_report(filename: str) -> dict:
    lower = filename.lower()
    if "auditor" in lower or "oag" in lower:
        return {
            "institution": "Office of the Auditor General (OAG)",
            "report_family": "Audit",
            "data_context": "Financial integrity, project status, and audit opinions",
        }
    if "green-book" in lower or "budget-implementation" in lower or "cob" in lower:
        return {
            "institution": "Controller of Budget (COB)",
            "report_family": "Budget",
            "data_context": "County budget allocations and actual expenditure",
        }
    return {"institution": "Unknown", "report_family": "Report"}


def is_relevant_report(pdf_path: Path, fiscal_year: str) -> bool:
    lower = pdf_path.name.lower()
    is_type = any(k in lower for k in ("auditor", "oag", "cob",
                                        "budget-implementation", "green-book"))
    is_year = fiscal_year in lower or "2023" in lower or "2024" in lower
    return is_type and is_year


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate web-ready County data bundle")
    parser.add_argument("--pdf-dir",    default="data/pdfs")
    parser.add_argument("--model",      default="models/table_detection/final_model")
    parser.add_argument("--input-pdfs", nargs="*")
    parser.add_argument("--output",     default="outputs/wazigov_citizen_bundle.json")
    parser.add_argument("--max-pages",  type=int, default=None)
    parser.add_argument("--keep-descriptions", action="store_true",
                        help="Keep _description/_columns fields (useful for debugging)")
    args = parser.parse_args()

    project_root  = Path(__file__).resolve().parent.parent
    pdf_dir       = project_root / args.pdf_dir
    model_path    = project_root / args.model
    output_path   = project_root / args.output

    # Load WaziGov modules
    inference = load_module("inference",
                            project_root / "scripts" / "inference.py")
    extractor_path = project_root.parent / "wazi-ui" / "scripts" / \
                     "generate_projects_from_cob_oag.py"
    extractor = load_module("extractor", extractor_path)

    if not inference or not extractor:
        print("Critical Error: Inference or Extractor scripts missing.")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, processor = inference.load_model(
        str(model_path if model_path.exists() else
            "microsoft/table-transformer-detection"), device)
    s_model, s_processor = inference.load_structure_model(
        "microsoft/table-transformer-structure-recognition", device)

    # ── PDF processing ────────────────────────────────────────────────────────
    pdfs = ([Path(p) for p in args.input_pdfs] if args.input_pdfs
            else [p for p in pdf_dir.glob("*.pdf")
                  if is_relevant_report(p, "2023-2024")])

    print(f"Processing {len(pdfs)} reports for WaziGov citizen bundle...")

    all_reports = []
    for pdf in pdfs:
        print(f"  Analysing: {pdf.name}")
        art_dir = project_root / "outputs" / "artifacts" / pdf.stem
        art_dir.mkdir(parents=True, exist_ok=True)
        cv_json = art_dir / "handoff.json"

        inference.process_pdf(
            pdf_path=pdf,
            model=model,
            processor=processor,
            device=device,
            output_dir=str(art_dir),
            threshold=0.5,
            model_version="fine_tuned_wazigov",
            cv_output_path=cv_json,
            structure_model=s_model,
            structure_processor=s_processor,
            use_pdf_table_finder=True,
            max_pages=args.max_pages,
        )

        with open(cv_json, encoding="utf-8") as f:
            doc_payload = json.load(f)

        # ✅ Strip CV noise HERE — before the extractor ever sees the document.
        # This means bbox, image_b64, confidence, cell_type, etc. are gone
        # from memory before any extraction logic runs.
        clean_doc = strip_document(doc_payload)

        report_id = pdf.stem
        if "auditor" in pdf.name.lower() or "oag" in pdf.name.lower():
            report_id = "Auditor-Generals-summary-Report-on-County-Governments-2023-2024"

        all_reports.append({
            "report_id": report_id,
            "title":     pdf.stem.replace("-", " ").title(),
            "document":  clean_doc,          # ← clean, not raw
            **classify_report(pdf.name),
        })

    # ── Extraction ────────────────────────────────────────────────────────────
    raw_bundle = {"fiscal_year": "2023-2024", "reports": all_reports}

    print("Extracting structured County data...")
    structured = extractor.extract_all_projects(raw_bundle)

    # ── Reshape into county-indexed citizen bundle ────────────────────────────
    # Re-key the project_implementation and financial_performance sections so
    # the website can do: data.project_implementation.stalled["Nakuru"]
    # instead of scanning a flat list.
    if isinstance(structured, dict):
        pi = rekey_counties(structured.get("project_implementation", {}))
        fp = rekey_counties(structured.get("financial_performance", {}))
    else:
        # Extractor returned a flat list — convert to simple county lookup
        pi, fp = {}, {}
        for item in (structured if isinstance(structured, list) else []):
            key = normalise_county_key(item.get("county_name", "Unknown"))
            fp[key] = {k: v for k, v in item.items() if k != "county_name"}

    citizen_data = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "fiscal_year": "2023-2024",
            "version": "2.0-citizen",
            "county_key_format": "County name without trailing 'County' — e.g. 'Nairobi', 'Trans Nzoia'",
        },
        "project_implementation": pi,
        "financial_performance":  fp,
        "audit_quality":  structured.get("audit_quality", {})  if isinstance(structured, dict) else {},
        "cob_green_book": structured.get("cob_green_book", {}) if isinstance(structured, dict) else {},
    }

    # ── Final clean pass ──────────────────────────────────────────────────────
    print("Finalizing web bundle...")

    # Remove any remaining CV fields that slipped through
    clean_bundle = strip_metadata(citizen_data)

    # Optionally remove developer-facing _description / _columns fields
    if not args.keep_descriptions:
        clean_bundle = strip_internal_descriptions(clean_bundle)

    # ── Write output ──────────────────────────────────────────────────────────
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(clean_bundle, f, indent=2, ensure_ascii=False)

    total_counties = max(
        len(pi.get("stalled_abandoned_projects_county_executives", {})
              .get("by_county", {})),
        len(fp.get("budget_summary", {}).get("by_county", {})),
        1,
    )

    print(f"\nSUCCESS: Web-ready data saved to {output_path}")
    print(f"Total Counties in Bundle: {total_counties}")
    print("Usage hint: data.financial_performance.budget_summary.by_county['Nairobi']")


if __name__ == "__main__":
    main()