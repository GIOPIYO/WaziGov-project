"""
Generate direct budget analytics from canonical COB/OAG bundles (no NLP required).

Outputs:
- county_trends.json
- validation_integrity_panels.json
- transparency_scorecard.json

Usage:
    python scripts/generate_budget_analytics.py \
      --input outputs/cob_oag_2023_2024_full.json

You can pass multiple --input files (for multiple fiscal years).
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
    "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
    "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos",
    "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a",
    "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu",
    "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
]

COUNTY_NORMALIZED = {re.sub(r"[^a-z0-9]", "", c.lower()): c for c in COUNTIES}

ALLOCATION_KEYWORDS = ("approved", "budget", "estimate", "allocation")
ACTUAL_KEYWORDS = ("actual", "receipt", "receipts", "revenue", "expenditure", "spent", "utilized")
VARIANCE_KEYWORDS = ("variance", "deviation", "difference", "shortfall")
COUNTY_KEYWORDS = ("county", "executive name", "assembly name", "county name", "name")

# Sanity check: Discard any single value exceeding 100 Billion KSh (typical max for a county is ~40B)
MAX_PLAUSIBLE_AMOUNT = 100_000_000_000.0


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate

    script_root = Path(__file__).resolve().parents[1]
    script_candidate = script_root / candidate
    if script_candidate.exists():
        return script_candidate

    cwd_candidate = Path.cwd() / candidate
    if cwd_candidate.exists():
        return cwd_candidate

    return script_candidate


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_numeric(value: str | None) -> float | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    lowered = text.lower()
    if lowered in {"-", "n/a", "na", "not disclosed", "various"}:
        return None

    # Heuristic: If it contains a slash or colon, it's likely a date or reference, not a budget
    # Example: "2023/24" should not be parsed as 202324
    if "/" in text or ":" in text:
        return None

    is_percent = "%" in text
    negative = "(" in text and ")" in text

    cleaned = re.sub(r"[^0-9.\-]", "", text)
    if cleaned in {"", ".", "-", "-."}:
        return None

    try:
        number = float(cleaned)
    except ValueError:
        return None

    if negative:
        number = -abs(number)

    if is_percent:
        return number

    return number


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def match_county(text: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]", "", text.lower())
    if not normalized:
        return None

    for key, county in COUNTY_NORMALIZED.items():
        if key and key in normalized:
            return county
    return None


def extract_table_headers(cells: list[dict[str, Any]]) -> dict[int, str]:
    headers: dict[int, list[str]] = defaultdict(list)
    for cell in cells:
        row_idx = int(cell.get("row_idx", 0))
        if row_idx > 3:
            continue
        cell_type = (cell.get("cell_type") or "").lower()
        if cell_type not in {"column_header", "header"}:
            continue
        col_idx = int(cell.get("col_idx", -1))
        if col_idx < 0:
            continue
        raw_text = (cell.get("raw_text") or "").strip()
        if raw_text:
            headers[col_idx].append(raw_text)

    merged: dict[int, str] = {}
    for col_idx, parts in headers.items():
        merged[col_idx] = normalize_text(" ".join(parts))
    return merged


def pick_columns(headers: dict[int, str], keywords: tuple[str, ...]) -> list[int]:
    out: list[int] = []
    for col_idx, header in headers.items():
        if any(keyword in header for keyword in keywords):
            out.append(col_idx)
    return sorted(out)


def infer_counties_from_cells(cells: list[dict[str, Any]], max_cells: int = 500) -> set[str]:
    counties: set[str] = set()
    for cell in cells[:max_cells]:
        text = (cell.get("raw_text") or "").strip()
        if not text:
            continue
        county = match_county(text)
        if county:
            counties.add(county)
            if len(counties) >= 10:
                break
    return counties


def to_sorted_counter_items(counter: Counter) -> list[dict[str, Any]]:
    return [{"warning": warning, "count": int(count)} for warning, count in sorted(counter.items(), key=lambda x: (-x[1], x[0]))]


def build_analytics(bundles: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    trend_map: dict[tuple[str, str], dict[str, Any]] = {}

    integrity_family_year: dict[tuple[str, str], dict[str, Any]] = {}
    integrity_county_year: dict[tuple[str, str], dict[str, Any]] = {}

    document_scorecard: dict[str, dict[str, Any]] = {}
    county_scorecard: dict[str, dict[str, Any]] = {}

    all_years: set[str] = set()
    source_files: list[str] = []

    for bundle in bundles:
        bundle_fiscal_year = str(bundle.get("fiscal_year") or "unknown")
        reports = bundle.get("reports", [])

        for report in reports:
            report_id = str(report.get("report_id") or "unknown_report")
            report_family = str(report.get("report_family") or "Unknown")
            fiscal_year = str(report.get("fiscal_year") or bundle_fiscal_year)
            all_years.add(fiscal_year)

            document = report.get("document") or {}
            source_file = str(report.get("source_file") or document.get("source_file") or "")
            if source_file:
                source_files.append(source_file)

            tables = document.get("tables") or []
            doc_key = f"{report_id}:{fiscal_year}"
            doc_entry = document_scorecard.setdefault(
                doc_key,
                {
                    "report_id": report_id,
                    "report_family": report_family,
                    "fiscal_year": fiscal_year,
                    "source_file": source_file,
                    "table_count": 0,
                    "warning_table_count": 0,
                    "warnings_total": 0,
                    "warning_type_counts": Counter(),
                    "counties_covered": set(),
                },
            )

            fam_year_key = (report_family, fiscal_year)
            fam_entry = integrity_family_year.setdefault(
                fam_year_key,
                {
                    "report_family": report_family,
                    "fiscal_year": fiscal_year,
                    "table_count": 0,
                    "warning_table_count": 0,
                    "warnings_total": 0,
                    "warning_type_counts": Counter(),
                },
            )

            for table in tables:
                table_id = str(table.get("table_id") or "unknown_table")
                cells = table.get("cells") or []
                validation = table.get("validation") or {}
                warnings = validation.get("warnings") or []

                headers = extract_table_headers(cells)
                county_cols = pick_columns(headers, COUNTY_KEYWORDS)
                allocation_cols = pick_columns(headers, ALLOCATION_KEYWORDS)
                actual_cols = pick_columns(headers, ACTUAL_KEYWORDS)
                variance_cols = pick_columns(headers, VARIANCE_KEYWORDS)

                row_map: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
                for cell in cells:
                    row_idx = int(cell.get("row_idx", -1))
                    col_idx = int(cell.get("col_idx", -1))
                    if row_idx < 0 or col_idx < 0:
                        continue
                    row_map[row_idx][col_idx] = cell

                table_counties_from_rows: set[str] = set()

                for row_idx, row_cells in row_map.items():
                    if row_idx == 0:
                        continue

                    county_candidates: list[str] = []
                    if county_cols:
                        for cidx in county_cols:
                            text = (row_cells.get(cidx, {}).get("raw_text") or "").strip()
                            if text:
                                county_candidates.append(text)
                    else:
                        for cidx in sorted(row_cells):
                            text = (row_cells[cidx].get("raw_text") or "").strip()
                            if text:
                                county_candidates.append(text)
                            if len(county_candidates) >= 2:
                                break

                    matched_county = None
                    for candidate in county_candidates:
                        matched_county = match_county(candidate)
                        if matched_county:
                            break

                    if not matched_county:
                        continue

                    table_counties_from_rows.add(matched_county)

                    allocation_value = None
                    for cidx in allocation_cols:
                        allocation_value = parse_numeric(row_cells.get(cidx, {}).get("raw_text"))
                        if allocation_value is not None and abs(allocation_value) > MAX_PLAUSIBLE_AMOUNT:
                            allocation_value = None
                        if allocation_value is not None:
                            break

                    actual_value = None
                    for cidx in actual_cols:
                        actual_value = parse_numeric(row_cells.get(cidx, {}).get("raw_text"))
                        if actual_value is not None and abs(actual_value) > MAX_PLAUSIBLE_AMOUNT:
                            actual_value = None
                        if actual_value is not None:
                            break

                    variance_value = None
                    for cidx in variance_cols:
                        variance_value = parse_numeric(row_cells.get(cidx, {}).get("raw_text"))
                        if variance_value is not None and abs(variance_value) > MAX_PLAUSIBLE_AMOUNT:
                            variance_value = None
                        if variance_value is not None:
                            break

                    if variance_value is None and allocation_value is not None and actual_value is not None:
                        variance_value = actual_value - allocation_value

                    if allocation_value is None and actual_value is None and variance_value is None:
                        continue

                    trend_key = (matched_county, fiscal_year)
                    if trend_key not in trend_map:
                        trend_map[trend_key] = {
                            "county": matched_county,
                            "fiscal_year": fiscal_year,
                            "allocation_kshs": 0.0,
                            "actual_kshs": 0.0,
                            "variance_kshs": 0.0,
                            "rows_used": 0,
                            "tables_used": set(),
                            "source_reports": set(),
                        }

                    trend = trend_map[trend_key]
                    if allocation_value is not None:
                        trend["allocation_kshs"] += allocation_value
                    if actual_value is not None:
                        trend["actual_kshs"] += actual_value
                    if variance_value is not None:
                        trend["variance_kshs"] += variance_value
                    trend["rows_used"] += 1
                    trend["tables_used"].add(table_id)
                    trend["source_reports"].add(report_id)

                # Validation/integrity aggregation
                table_counties = set(table_counties_from_rows)
                if not table_counties:
                    table_counties = infer_counties_from_cells(cells)

                doc_entry["table_count"] += 1
                fam_entry["table_count"] += 1

                if warnings:
                    doc_entry["warning_table_count"] += 1
                    fam_entry["warning_table_count"] += 1

                    warning_count = len(warnings)
                    doc_entry["warnings_total"] += warning_count
                    fam_entry["warnings_total"] += warning_count

                    doc_entry["warning_type_counts"].update(warnings)
                    fam_entry["warning_type_counts"].update(warnings)

                for county in table_counties:
                    doc_entry["counties_covered"].add(county)

                    ckey = (county, fiscal_year)
                    centry = integrity_county_year.setdefault(
                        ckey,
                        {
                            "county": county,
                            "fiscal_year": fiscal_year,
                            "table_mentions": 0,
                            "warning_table_mentions": 0,
                            "warnings_total": 0,
                            "warning_type_counts": Counter(),
                        },
                    )
                    centry["table_mentions"] += 1
                    if warnings:
                        centry["warning_table_mentions"] += 1
                        centry["warnings_total"] += len(warnings)
                        centry["warning_type_counts"].update(warnings)

    # Finalize county trends
    county_trends = []
    for _, row in sorted(trend_map.items(), key=lambda item: (item[0][0], item[0][1])):
        allocation = row["allocation_kshs"]
        actual = row["actual_kshs"]
        absorption_ratio = None
        if allocation not in (None, 0):
            absorption_ratio = actual / allocation

        county_trends.append(
            {
                "county": row["county"],
                "fiscal_year": row["fiscal_year"],
                "allocation_kshs": round(allocation, 2),
                "actual_kshs": round(actual, 2),
                "variance_kshs": round(row["variance_kshs"], 2),
                "absorption_ratio": round(absorption_ratio, 6) if absorption_ratio is not None else None,
                "rows_used": int(row["rows_used"]),
                "tables_used": int(len(row["tables_used"])),
                "source_reports": sorted(row["source_reports"]),
            }
        )

    # Calculate overall budget ranking across all fiscal years
    overall_county_allocations: dict[str, float] = defaultdict(float)
    for trend_item in county_trends:
        county = trend_item["county"]
        allocation = trend_item["allocation_kshs"]
        if allocation is not None:
            overall_county_allocations[county] += allocation

    budget_ranking = []
    for rank, (county, total_allocation) in enumerate(
        sorted(overall_county_allocations.items(), key=lambda item: item[1], reverse=True)
    ):
        budget_ranking.append(
            {
                "rank": rank + 1,
                "county": county,
                "total_allocation_kshs": round(total_allocation, 2),
            }
        )

    # Finalize integrity panels
    family_panel = []
    for _, row in sorted(integrity_family_year.items(), key=lambda item: (item[0][1], item[0][0])):
        table_count = max(1, int(row["table_count"]))
        family_panel.append(
            {
                "report_family": row["report_family"],
                "fiscal_year": row["fiscal_year"],
                "table_count": int(row["table_count"]),
                "warning_table_count": int(row["warning_table_count"]),
                "warnings_total": int(row["warnings_total"]),
                "warning_table_rate": round(row["warning_table_count"] / table_count, 6),
                "warnings_per_table": round(row["warnings_total"] / table_count, 6),
                "warning_type_counts": to_sorted_counter_items(row["warning_type_counts"]),
            }
        )

    county_panel = []
    for _, row in sorted(integrity_county_year.items(), key=lambda item: (item[0][1], item[0][0])):
        mentions = max(1, int(row["table_mentions"]))
        county_panel.append(
            {
                "county": row["county"],
                "fiscal_year": row["fiscal_year"],
                "table_mentions": int(row["table_mentions"]),
                "warning_table_mentions": int(row["warning_table_mentions"]),
                "warnings_total": int(row["warnings_total"]),
                "warning_table_rate": round(row["warning_table_mentions"] / mentions, 6),
                "warnings_per_table_mention": round(row["warnings_total"] / mentions, 6),
                "warning_type_counts": to_sorted_counter_items(row["warning_type_counts"]),
            }
        )

    # Finalize scorecards
    document_rows = []
    for _, row in sorted(document_scorecard.items(), key=lambda item: (item[1]["fiscal_year"], item[1]["report_id"])):
        table_count = max(1, int(row["table_count"]))
        document_rows.append(
            {
                "report_id": row["report_id"],
                "report_family": row["report_family"],
                "fiscal_year": row["fiscal_year"],
                "source_file": row["source_file"],
                "table_count": int(row["table_count"]),
                "warning_table_count": int(row["warning_table_count"]),
                "warnings_total": int(row["warnings_total"]),
                "warning_table_rate": round(row["warning_table_count"] / table_count, 6),
                "warnings_per_table": round(row["warnings_total"] / table_count, 6),
                "counties_covered": sorted(row["counties_covered"]),
                "warning_type_counts": to_sorted_counter_items(row["warning_type_counts"]),
            }
        )

    for row in county_panel:
        county = row["county"]
        score_entry = county_scorecard.setdefault(
            county,
            {
                "county": county,
                "table_mentions": 0,
                "warning_table_mentions": 0,
                "warnings_total": 0,
                "warning_type_counts": Counter(),
                "fiscal_years": set(),
            },
        )
        score_entry["table_mentions"] += row["table_mentions"]
        score_entry["warning_table_mentions"] += row["warning_table_mentions"]
        score_entry["warnings_total"] += row["warnings_total"]
        score_entry["fiscal_years"].add(row["fiscal_year"])
        score_entry["warning_type_counts"].update({item["warning"]: item["count"] for item in row["warning_type_counts"]})

    county_rows = []
    for county, row in sorted(county_scorecard.items(), key=lambda item: item[0]):
        mentions = max(1, int(row["table_mentions"]))
        county_rows.append(
            {
                "county": county,
                "fiscal_years": sorted(row["fiscal_years"]),
                "table_mentions": int(row["table_mentions"]),
                "warning_table_mentions": int(row["warning_table_mentions"]),
                "warnings_total": int(row["warnings_total"]),
                "warning_table_rate": round(row["warning_table_mentions"] / mentions, 6),
                "warnings_per_table_mention": round(row["warnings_total"] / mentions, 6),
                "warning_type_counts": to_sorted_counter_items(row["warning_type_counts"]),
            }
        )

    generated_at = datetime.now(timezone.utc).isoformat()

    trends_payload = {
        "metadata": {
            "generated_at": generated_at,
            "source_files": sorted(set(source_files)),
            "fiscal_years": sorted(all_years),
            "description": "County trend metrics from canonical table cells (no NLP).",
            "notes": [
                "allocation_kshs and actual_kshs are aggregated from detected county rows and budget-like columns.",
                "absorption_ratio = actual_kshs / allocation_kshs when allocation is available.",
            ],
        },
        "county_trends": county_trends,
    }

    integrity_payload = {
        "metadata": {
            "generated_at": generated_at,
            "fiscal_years": sorted(all_years),
            "description": "Validation warning consistency/integrity panels by report family and county.",
            "notes": [
                "County linkage is heuristic and based on county mentions in table cells.",
                "Use table_mentions coverage to interpret county warning rates.",
            ],
        },
        "by_report_family_year": family_panel,
        "by_county_year": county_panel,
    }

    scorecard_payload = {
        "metadata": {
            "generated_at": generated_at,
            "fiscal_years": sorted(all_years),
            "description": "Public transparency scorecards from validation warning burden.",
        },
        "documents": document_rows,
        "counties": county_rows,
    }
    
    budget_ranking_payload = {
        "metadata": {
            "generated_at": generated_at,
            "source_files": sorted(set(source_files)),
            "fiscal_years": sorted(all_years),
            "description": "Overall budget ranking by county, aggregated across all processed fiscal years.",
            "notes": [
                "total_allocation_kshs is the sum of allocation_kshs from all county trends for a given county.",
            ],
        },
        "budget_ranking": budget_ranking,
    }

    return trends_payload, integrity_payload, scorecard_payload, budget_ranking_payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate county trends + integrity + transparency analytics from COB/OAG bundles.")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="Input bundle JSON path. Repeat for multiple fiscal years.",
    )
    parser.add_argument(
        "--output-dir",
        default="public/data/analytics",
        help="Output directory for generated analytics JSON files.",
    )

    args = parser.parse_args()

    input_paths = args.input or ["outputs/cob_oag_2023_2024_full.json"]
    resolved_inputs = [resolve_path(p) for p in input_paths]

    for path in resolved_inputs:
        if not path.exists():
            raise FileNotFoundError(f"Input bundle not found: {path}")

    bundles = [load_json(path) for path in resolved_inputs] # type: ignore
    trends_payload, integrity_payload, scorecard_payload, budget_ranking_payload = build_analytics(bundles)

    output_dir = resolve_path(args.output_dir)
    write_json(output_dir / "county_trends.json", trends_payload)
    write_json(output_dir / "validation_integrity_panels.json", integrity_payload)
    write_json(output_dir / "transparency_scorecard.json", scorecard_payload)
    write_json(output_dir / "county_budget_ranking.json", budget_ranking_payload)

    print("Generated analytics files:")
    print(f"- {output_dir / 'county_trends.json'}")
    print(f"- {output_dir / 'validation_integrity_panels.json'}")
    print(f"- {output_dir / 'transparency_scorecard.json'}")
    print(f"- {output_dir / 'county_budget_ranking.json'}")


    print(f"County trend rows: {len(trends_payload.get('county_trends', []))}")
    print(f"Integrity rows (family/year): {len(integrity_payload.get('by_report_family_year', []))}")
    print(f"Integrity rows (county/year): {len(integrity_payload.get('by_county_year', []))}")
    print(f"Document scorecard rows: {len(scorecard_payload.get('documents', []))}")
    print(f"County scorecard rows: {len(scorecard_payload.get('counties', []))}")

    print(f"Budget ranking rows: {len(budget_ranking_payload.get('budget_ranking', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
