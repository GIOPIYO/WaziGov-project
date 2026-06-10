"""
Aggregate budgets and produce analytics artifacts for the frontend.

This script is more robust than the original quick-scan: it accepts an input
directory (which may contain bundles from the CV pipeline or per-table JSONs),
walks expected JSON shapes, extracts county-linked numeric rows, aggregates by
county and fiscal year, runs simple validation checks, and emits JSON/CSV
artifacts under an output directory for the frontend to consume.

Usage:
  python aggregate_budgets.py --input-dir "WaziGov table detection/outputs" \
      --output-dir "wazi-ui/public/data/analytics"
"""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import importlib.util

# Minimal canonical list of Kenyan counties for normalization
COUNTIES = [
    "Baringo","Bomet","Bungoma","Busia","Elgeyo-Marakwet","Embu","Garissa",
    "Homa Bay","Isiolo","Kajiado","Kakamega","Kericho","Kiambu","Kilifi",
    "Kirinyaga","Kisii","Kisumu","Kitui","Kwale","Laikipia","Lamu","Machakos",
    "Makueni","Mandera","Marsabit","Meru","Migori","Mombasa","Murang'a",
    "Nairobi","Nakuru","Nandi","Narok","Nyamira","Nyandarua","Nyeri","Samburu",
    "Siaya","Taita-Taveta","Tana River","Tharaka-Nithi","Trans Nzoia","Turkana",
    "Uasin Gishu","Vihiga","Wajir","West Pokot"
]

IGNORED_WARNING_PREFIXES = (
    "no_cell_text_extracted",
    "no_header_hierarchy_detected",
)

# Keywords indicating numeric/arithmetic validation problems we want to surface
ARITHMETIC_WARNING_KEYWORDS = (
    "numeric_ratio_mismatch",
    "numeric_sum_mismatch",
    "sum_mismatch",
    "ratio_mismatch",
    "numeric",
    "variance",
    "deviation",
)


def normalize_county(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    def county_key(value: str) -> str:
        cleaned = value.lower().replace("/", " ").replace("-", " ")
        cleaned = re.sub(r"[^a-z0-9 ]", " ", cleaned)
        tokens = [token for token in cleaned.split() if token not in {"county"}]
        return " ".join(tokens)

    raw_key = county_key(raw)
    for c in COUNTIES:
        if county_key(c) == raw_key:
            return c
    # try variations using the first token for abbreviated or noisy names
    for c in COUNTIES:
        if county_key(c).split()[0] in raw_key:
            return c
    return raw.strip()


def filter_validation_warnings(warnings: List[str]) -> List[str]:
    return [w for w in warnings if not any(w == prefix or w.startswith(prefix + ":") for prefix in IGNORED_WARNING_PREFIXES)]


def filter_to_arithmetic(warnings: List[str]) -> List[str]:
    """Return only arithmetic/financial validation warnings after applying basic ignores."""
    if not warnings:
        return []
    filtered = filter_validation_warnings(warnings)
    arith = [w for w in filtered if any(k in w for k in ARITHMETIC_WARNING_KEYWORDS)]
    return arith


def parse_currency(value_str: Optional[str]) -> Optional[float]:
    if value_str is None:
        return None
    if not isinstance(value_str, str):
        value_str = str(value_str)
    txt = value_str.strip()
    if txt == "":
        return None
    lowered = txt.lower()
    if lowered in {"-", "n/a", "na", "not disclosed", "various"}:
        return None

    # remove common non-number tokens but keep '.' and '-'
    cleaned = re.sub(r"[^0-9.\-]", "", txt)
    # guard against lone '-' or '.'
    if cleaned in {"", "-", ".", "-."}:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def resolve_json_tables(payload: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """Return list of (source_label, table_dict) pairs for a given JSON payload.

    Supports several shapes produced by your pipeline:
      - Bundle files: { 'reports': [ { 'report_id', 'document': { 'tables': [...] } } ] }
      - Per-document CV output: { 'tables': [...] }
      - Per-table JSON with top-level 'cells'
    """
    tables_out: List[Tuple[str, Dict[str, Any]]] = []

    if isinstance(payload.get("reports"), list):
        for rpt in payload.get("reports", []):
            rid = rpt.get("report_id") or rpt.get("title") or "report"
            doc = rpt.get("document") or {}
            for t in doc.get("tables", []):
                tables_out.append((f"{rid}", t))
    elif isinstance(payload.get("tables"), list):
        doc_id = payload.get("document_id") or payload.get("source_file") or "doc"
        for t in payload.get("tables", []):
            tables_out.append((f"{doc_id}", t))
    elif isinstance(payload.get("cells"), list):
        # This JSON is a single table representation
        tbl_id = payload.get("table_id") or payload.get("source_file") or "table"
        tables_out.append((tbl_id, payload))

    return tables_out


def extract_rows_from_table(table: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract rows with potential county and numeric columns from a table dict.

    Returns list of dicts: {row_idx, county (maybe), allocation, actual, variance, raw_cells}
    """
    cells = table.get("cells", []) or []
    # Build grid map
    grid = defaultdict(dict)
    for c in cells:
        r = int(c.get("row_idx", -1))
        col = int(c.get("col_idx", -1))
        if r >= 0 and col >= 0:
            grid[r][col] = c

    # try to detect header columns by inspecting row 0..2
    header_texts = {}
    for r in range(0, 4):
        for col, cell in grid.get(r, {}).items():
            txt = (cell.get("raw_text") or "").strip()
            if not txt:
                continue
            header_texts.setdefault(col, []).append(txt.lower())

    # heuristics: identify county column (contains 'county' or matches common county names)
    county_col = None
    amount_col = None
    actual_col = None
    variance_col = None

    # flatten header samples
    header_samples = {col: " ".join(vals) for col, vals in header_texts.items()}
    for col, txt in header_samples.items():
        if "county" in txt or "name" in txt or "executive" in txt:
            county_col = col
        if any(k in txt for k in ("approved", "budget", "estimate", "allocation")) and amount_col is None:
            amount_col = col
        if any(k in txt for k in ("actual", "receipts", "receipt", "revenue", "spent", "utilized")) and actual_col is None:
            actual_col = col
        if any(k in txt for k in ("variance", "deviation", "difference")) and variance_col is None:
            variance_col = col

    rows_out: List[Dict[str, Any]] = []
    for r, cols in grid.items():
        if r == 0:
            continue
        # try county detection
        county = None
        if county_col is not None and county_col in cols:
            county = (cols[county_col].get("raw_text") or "").strip()
        else:
            # fallback: look for a cell that contains 'County' word
            for c in cols.values():
                t = (c.get("raw_text") or "").strip()
                if "county" in t.lower():
                    county = t
                    break

        # pick allocation/amount/actual cells
        allocation = None
        actual = None
        variance = None

        if amount_col is not None and amount_col in cols:
            allocation = parse_currency(cols[amount_col].get("raw_text"))
        if actual_col is not None and actual_col in cols:
            actual = parse_currency(cols[actual_col].get("raw_text"))
        if variance_col is not None and variance_col in cols:
            variance = parse_currency(cols[variance_col].get("raw_text"))

        # fallback strategies if not found
        if allocation is None:
            # try common numeric columns (col index >0)
            for col_idx in sorted(cols.keys()):
                if col_idx == county_col:
                    continue
                v = parse_currency(cols[col_idx].get("raw_text"))
                if v is not None:
                    allocation = v
                    break

        if actual is None:
            for col_idx in sorted(cols.keys(), reverse=True):
                v = parse_currency(cols[col_idx].get("raw_text"))
                if v is not None and v != allocation:
                    actual = v
                    break

        if variance is None and allocation is not None and actual is not None:
            variance = actual - allocation

        rows_out.append({
            "row_idx": r,
            "county": county,
            "allocation": allocation,
            "actual": actual,
            "variance": variance,
            "raw_cells": {col: cols[col].get("raw_text") for col in cols},
            "confidence": max((cols[col].get("confidence") or 0) for col in cols) if cols else 0,
        })

    return rows_out


def aggregate_directory(input_dir: str) -> Tuple[Dict[str, float], List[Dict[str, Any]], List[Dict[str, Any]]]:
    input_path = Path(input_dir)
    json_files = list(input_path.glob("**/*.json"))
    if not json_files:
        raise FileNotFoundError(f"No JSON files found under {input_dir}")

    county_totals: Dict[str, float] = defaultdict(float)
    raw_rows: List[Dict[str, Any]] = []
    alerts: List[Dict[str, Any]] = []

    for jf in json_files:
        try:
            payload = json.loads(jf.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"Skipping {jf} (invalid JSON): {e}")
            continue

        tables = resolve_json_tables(payload)
        for source_label, table in tables:
            report_id = source_label
            table_id = table.get("table_id") or f"table_{hash(json.dumps(table) )}"
            rows = extract_rows_from_table(table)
            for r in rows:
                county = (r.get("county") or "").strip()
                allocation = r.get("allocation")
                actual = r.get("actual")
                variance = r.get("variance")
                try:
                    src_file = str(jf.relative_to(Path.cwd()))
                except Exception:
                    src_file = str(jf)
                raw_rows.append({
                    "source_file": src_file,
                    "report_id": report_id,
                    "table_id": table_id,
                    **r,
                })
                if county:
                    if allocation is not None:
                        county_totals[county] += allocation

            # collect validation warnings if present (keep only arithmetic/financial warnings)
            validation = table.get("validation") or {}
            warnings = filter_to_arithmetic(validation.get("warnings") or [])
            if warnings:
                try:
                    src_file = str(jf.relative_to(Path.cwd()))
                except Exception:
                    src_file = str(jf)
                alerts.append({
                    "source_file": src_file,
                    "report_id": report_id,
                    "table_id": table_id,
                    "warnings": warnings,
                })

    return county_totals, raw_rows, alerts


def save_outputs(output_dir: str, county_totals: Dict[str, float], raw_rows: List[Dict[str, Any]], alerts: List[Dict[str, Any]]):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Ranking
    ranking = sorted(county_totals.items(), key=lambda x: x[1], reverse=True)
    ranking_rows = [{"rank": i+1, "county": c, "total_ksh": int(v)} for i, (c, v) in enumerate(ranking)]
    with open(out / "county_budget_ranking.json", "w", encoding="utf-8") as fh:
        json.dump({"generated_at": Path.cwd().as_posix(), "ranking": ranking_rows}, fh, indent=2)

    with open(out / "county_budget_ranking.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["Rank", "County", "Total Budget (KSh)"])
        for row in ranking_rows:
            writer.writerow([row["rank"], row["county"], row["total_ksh"]])

    # raw rows and alerts
    with open(out / "raw_extracted_rows.json", "w", encoding="utf-8") as fh:
        json.dump({"rows": raw_rows}, fh, indent=2, ensure_ascii=False)

    with open(out / "validation_alerts.json", "w", encoding="utf-8") as fh:
        json.dump({"alerts": alerts}, fh, indent=2, ensure_ascii=False)

    print(f"Wrote: {out / 'county_budget_ranking.json'}")
    print(f"Wrote: {out / 'county_budget_ranking.csv'}")
    print(f"Wrote: {out / 'raw_extracted_rows.json'}")
    print(f"Wrote: {out / 'validation_alerts.json'}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="outputs", help="Directory to search for CV JSON outputs")
    parser.add_argument("--input-file", default=None, help="Single bundle JSON file to process (overrides --input-dir)")
    parser.add_argument("--output-dir", default="public/data/analytics", help="Directory to write analytics JSON/CSV")
    args = parser.parse_args()

    if args.input_file:
        # process single file
        input_path = Path(args.input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        try:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"Unable to read JSON from {input_path}: {e}")

        # If this is a bundle (has 'reports'), prefer using the project's
        # structured extractor to get clean county-level fields.
        county_totals = defaultdict(float)
        raw_rows = []
        alerts = []
        if isinstance(payload.get("reports"), list):
            # Try to load the existing extractor script for robust parsing
            extractor_path = Path(__file__).resolve().parents[1] / "scripts" / "generate_projects_from_cob_oag.py"
            if extractor_path.exists():
                spec = importlib.util.spec_from_file_location("generate_projects_from_cob_oag", str(extractor_path))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore
                # mod.extract_all_projects expects the raw bundle dict
                extracted = mod.extract_all_projects(payload)
                # 'financial_performance' contains budget_summary and others
                fp = extracted.get("financial_performance", {})
                # budget_summary -> data: list of {county, executive_budget_kshs, assembly_budget_kshs, total_budget_kshs}
                # Use budget_summary as the authoritative source for approved allocations
                section = fp.get("budget_summary", {})
                for row in section.get("data", []):
                    county = row.get("county")
                    total_field = row.get("total_budget_kshs")
                    parsed_total = None
                    # Prefer parsing the human-readable total string (with commas)
                    if isinstance(total_field, str) and total_field.strip():
                        parsed_total = parse_currency(total_field)
                    # fallback: parse executive/assembly fields (they may be numeric or strings)
                    if parsed_total is None:
                        a = row.get("executive_budget_kshs")
                        b = row.get("assembly_budget_kshs")
                        pa = parse_currency(a) if isinstance(a, str) else (float(a) if a not in (None, "") else None)
                        pb = parse_currency(b) if isinstance(b, str) else (float(b) if b not in (None, "") else None)
                        vals = [v for v in (pa, pb) if v is not None]
                        if vals:
                            parsed_total = sum(vals)

                    # normalize county and apply a sanity cap to avoid corrupted huge numbers
                    if county and parsed_total is not None:
                        county_norm = normalize_county(county)
                        # ignore implausibly large values (> 10 trillion)
                        if parsed_total > 1e13:
                            # skip as likely extraction corruption
                            # record the raw row for manual inspection (already in raw_rows)
                            parsed_total = None
                        else:
                            county_totals[county_norm] += parsed_total
                    raw_rows.append({"source_file": str(input_path), "report_id": "bundle", "table_id": "budget_summary", **row})
                # collect validation alerts from original bundle reports
                for rpt in payload.get("reports", []):
                    doc = rpt.get("document") or {}
                    for t in doc.get("tables", []):
                        validation = t.get("validation") or {}
                        warnings = filter_to_arithmetic(validation.get("warnings") or [])
                        if warnings:
                            alerts.append({
                                "source_file": str(input_path),
                                "report_id": rpt.get("report_id"),
                                "table_id": t.get("table_id"),
                                "warnings": warnings,
                            })
            else:
                # fallback to table-level scanning
                tables = resolve_json_tables(payload)
                for source_label, table in tables:
                    report_id = source_label
                    table_id = table.get("table_id") or f"table_{hash(json.dumps(table))}"
                    rows = extract_rows_from_table(table)
                    for r in rows:
                        county = (r.get("county") or "").strip()
                        allocation = r.get("allocation")
                        raw_rows.append({
                            "source_file": str(input_path),
                            "report_id": report_id,
                            "table_id": table_id,
                            **r,
                        })
                        if county and allocation is not None:
                            county_totals[county] += allocation
                    validation = table.get("validation") or {}
                    warnings = filter_to_arithmetic(validation.get("warnings") or [])
                    if warnings:
                        alerts.append({
                            "source_file": str(input_path),
                            "report_id": report_id,
                            "table_id": table_id,
                            "warnings": warnings,
                        })
    else:
        county_totals, raw_rows, alerts = aggregate_directory(args.input_dir)

    # basic duplicate check
    file_county = Counter((r["source_file"], r["county"]) for r in raw_rows if r.get("county"))
    duplicates = [(f, c, cnt) for (f, c), cnt in file_county.items() if cnt > 1]
    if duplicates:
        print("\n⚠️  Duplicate county entries detected:")
        for f, c, cnt in duplicates:
            print(f" - {c} appears {cnt} times in {f}")
    else:
        print("\n✓ No duplicate county entries found across rows (good).")

    save_outputs(args.output_dir, county_totals, raw_rows, alerts)


if __name__ == "__main__":
    main()