"""
extract_projects.py
-------------------
Extracts all project-related data from the COB/OAG 2023-2024 audit JSON file
and writes a clean, website-ready JSON to projects_output.json.

Usage:
    python extract_projects.py [INPUT_FILE] [OUTPUT_FILE]

Defaults:
    INPUT_FILE  = cob_oag_2023_2024_full.json
    OUTPUT_FILE = projects_output.json
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime


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

# ─── helpers ──────────────────────────────────────────────────────────────────

def load_source(path: str) -> dict:
    """Read either a raw JSON file or a markdown wrapper with a JSON code block."""
    source_path = resolve_path(path)
    text = source_path.read_text(encoding="utf-8")
    stripped = text.lstrip()

    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(text)

    m = re.search(r"```\s*json\s*\n(.*?)\n```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))

    raise ValueError(f"Unable to parse JSON from {source_path}.")


def cells_to_grid(cells: list) -> dict:
    """
    Convert a flat list of cell objects into a dict keyed by (row, col),
    keeping the raw_text of the non-empty ones.
    """
    grid = {}
    for c in cells:
        text = (c.get("raw_text") or "").strip()
        if text:
            grid[(c["row_idx"], c["col_idx"])] = text
    return grid


def col_values(grid: dict, col: int, start_row: int = 1) -> list:
    """Return all non-empty values in `col` for rows >= start_row."""
    return [
        grid[k]
        for k in sorted(grid)
        if k[1] == col and k[0] >= start_row and grid[k]
    ]


def parse_kshs(value: str) -> int | None:
    """Parse a Kenyan shilling amount string into an integer, or None."""
    if not value or value.strip().lower() in ("not disclosed", "various", "-", ""):
        return None
    cleaned = re.sub(r"[^\d]", "", value)
    return int(cleaned) if cleaned else None


def parse_count(value: str) -> int | str | None:
    """Parse a project count value: int, 'Various', or None."""
    if not value:
        return None
    stripped = value.strip()
    if stripped.lower() == "various":
        return "Various"
    if stripped.lower() in ("not disclosed", "-", ""):
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def clean_county_name(name: str) -> str:
    """Normalise county names – strip trailing 'County' noise sometimes duplicated."""
    # Remove duplicate 'County County'
    name = re.sub(r"\bCounty\s+County\b", "County", name, flags=re.IGNORECASE)
    return name.strip()


# ─── table-extraction helpers ─────────────────────────────────────────────────

def extract_four_col_county_table(tables: list, table_id: str,
                                   col_labels: tuple) -> list:
    """
    Generic extractor for tables with structure:
        S/No | County Name | col_labels[0] | col_labels[1]
    Returns a list of dicts.
    """
    results = []
    for t in tables:
        if t["table_id"] != table_id:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(1, max_row + 1):
            county = clean_county_name(grid.get((row, 1), ""))
            val_a  = grid.get((row, 2), "")
            val_b  = grid.get((row, 3), "")
            if county:
                results.append({
                    "county": county,
                    col_labels[0]: val_a or None,
                    col_labels[1]: val_b or None,
                })
        break
    return results


def extract_county_project_summary(tables: list,
                                    target_ids: list,
                                    col3_label: str,
                                    col4_label: str) -> list:
    """
    Extract rows from one or more tables that share the schema:
        S/No | County Name | <count> | <amount Kshs>
    Merges data across continuation tables and deduplicates.
    """
    seen_counties = set()
    rows = []
    for t in tables:
        if t["table_id"] not in target_ids:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(0, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw:
                continue
            # column headers may slip into row-0 sometimes – skip pure headers
            if re.search(r"County\s*(Executive|Assembly)?\s*Name", county_raw, re.I):
                continue
            county = clean_county_name(county_raw)
            # Handle OCR artefacts like merged rows
            if " " in county and "\n" not in county and len(county.split()) > 4:
                continue  # skip garbled cells
            count_raw  = grid.get((row, 2), "")
            amount_raw = grid.get((row, 3), "")
            if county and county not in seen_counties:
                seen_counties.add(county)
                rows.append({
                    "county": county,
                    col3_label: parse_count(count_raw),
                    col4_label: parse_kshs(amount_raw),
                    f"{col4_label}_raw": amount_raw or None,
                })
    return rows


def extract_five_col_table(tables: list, target_ids: list,
                            labels: tuple) -> list:
    """
    Extract rows from tables with 5-column schema:
        S/No | County | col1 | col2 | col3
    """
    seen = set()
    rows = []
    for t in tables:
        if t["table_id"] not in target_ids:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(1, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw or re.search(r"Name", county_raw, re.I):
                continue
            county = clean_county_name(county_raw)
            key = (county, t["table_id"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({
                "county": county,
                labels[0]: parse_kshs(grid.get((row, 2), "")),
                labels[1]: parse_kshs(grid.get((row, 3), "")),
                labels[2]: grid.get((row, 4), "") or None,
            })
    return rows


# ─── main extraction ──────────────────────────────────────────────────────────

def extract_all_projects(data: dict) -> dict:
    reports_by_id = {r["report_id"]: r for r in data["reports"]}

    oag_report = reports_by_id.get(
        "Auditor-Generals-summary-Report-on-County-Governments-2023-2024"
    )
    cob_report = reports_by_id.get(
        "GREEN-BOOK-EXECUTIVES-2024-FINAL-5.3.2025-SIGNED"
    )

    oag_tables = oag_report["document"]["tables"] if oag_report else []
    cob_tables = cob_report["document"]["tables"] if cob_report else []

    # ── 1. Delayed Projects – County Executives (Appendix 26) ─────────────────
    # Primary table: page_048_table_00 + continuation page_131_table_00
    delayed_exec = extract_county_project_summary(
        oag_tables,
        target_ids=["page_048_table_00", "page_131_table_00"],
        col3_label="number_of_projects",
        col4_label="amount_kshs",
    )

    # ── 2. Stalled/Abandoned Projects – County Executives (Appendix 27) ───────
    # page_132_table_00 (30 rows), page_133_table_01 (continuation)
    stalled_exec = extract_county_project_summary(
        oag_tables,
        target_ids=["page_132_table_00", "page_133_table_01"],
        col3_label="number_of_projects",
        col4_label="amount_kshs",
    )

    # ── 3. Procurement Irregularities – County Executives (Appendix 24) ───────
    # page_134_table_00 has county + amount (3 cols)
    procurement_irregularities = []
    for t in oag_tables:
        if t["table_id"] == "page_134_table_00":
            grid = cells_to_grid(t["cells"])
            max_row = max(k[0] for k in grid) if grid else 0
            for row in range(0, max_row + 1):
                county_raw = grid.get((row, 1), "")
                if not county_raw or "Name" in county_raw:
                    continue
                # OCR sometimes merges two county names in one cell
                county_parts = re.split(r"\s{2,}|\n", county_raw)
                for part in county_parts:
                    county = clean_county_name(part)
                    if "County" in county and len(county) < 50:
                        amount_raw = grid.get((row, 2), "")
                        procurement_irregularities.append({
                            "county": county,
                            "amount_kshs": parse_kshs(amount_raw),
                            "amount_kshs_raw": amount_raw or None,
                        })
            break

    # ── 4. County Budget Summary (all 47 counties) ────────────────────────────
    # page_087_table_00 + page_088_table_00 – S/No | County | Exec Budget | Assembly Budget | Total
    budget_summary = extract_five_col_table(
        oag_tables,
        ["page_087_table_00", "page_088_table_00"],
        ("executive_budget_kshs", "assembly_budget_kshs", "total_budget_kshs"),
    )

    # ── 5. Actual Revenue (Appendix 3) ────────────────────────────────────────
    # page_089_table_00 + page_090_table_00
    revenue_actual = extract_five_col_table(
        oag_tables,
        ["page_089_table_00", "page_090_table_00"],
        ("executive_revenue_kshs", "assembly_revenue_kshs", "total_revenue_kshs"),
    )

    # ── 6. Own Source Revenue Achievement (Appendix 5) ────────────────────────
    # page_093_table_00 + page_094_table_00  – County | Budgeted | Actual | %age
    own_source_revenue = []
    seen = set()
    for t in oag_tables:
        if t["table_id"] not in ["page_093_table_00", "page_094_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(1, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw or "Name" in county_raw:
                continue
            county = clean_county_name(county_raw)
            if county in seen:
                continue
            seen.add(county)
            own_source_revenue.append({
                "county": county,
                "budgeted_kshs": parse_kshs(grid.get((row, 2), "")),
                "actual_kshs":   parse_kshs(grid.get((row, 3), "")),
                "achievement_pct": grid.get((row, 4), "") or None,
            })

    # ── 7. CRF Exchequer Releases vs Receipts (Appendix 6) ───────────────────
    exchequer = []
    seen_exc = set()
    for t in oag_tables:
        if t["table_id"] not in ["page_095_table_00", "page_096_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(1, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw or "Name" in county_raw:
                continue
            county = clean_county_name(county_raw)
            if county in seen_exc:
                continue
            seen_exc.add(county)
            exchequer.append({
                "county": county,
                "exchequer_releases_kshs": parse_kshs(grid.get((row, 2), "")),
                "receipts_kshs":           parse_kshs(grid.get((row, 3), "")),
                "variance_kshs":           parse_kshs(grid.get((row, 4), "")),
            })

    # ── 8. County Expenditure (Appendix 9) ────────────────────────────────────
    expenditure = extract_five_col_table(
        oag_tables,
        ["page_102_table_00", "page_103_table_00"],
        ("executive_expenditure_kshs", "assembly_expenditure_kshs", "total_expenditure_kshs"),
    )

    # ── 9. Wage Bill Analysis – County Executives (Appendix 10) ───────────────
    wage_bill_exec = []
    seen_wb = set()
    for t in oag_tables:
        if t["table_id"] not in ["page_104_table_00", "page_105_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(1, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw or "Name" in county_raw:
                continue
            county = clean_county_name(county_raw)
            if county in seen_wb:
                continue
            seen_wb.add(county)
            wage_bill_exec.append({
                "county": county,
                "personnel_emoluments_kshs": parse_kshs(grid.get((row, 2), "")),
                "total_revenue_kshs":        parse_kshs(grid.get((row, 3), "")),
                "wage_bill_pct_of_revenue":  grid.get((row, 4), "") or None,
            })

    # ── 10. Voided Transactions – County Executives (Appendix 19) ─────────────
    voided_transactions = []
    seen_vt = set()
    for t in oag_tables:
        if t["table_id"] not in ["page_118_table_00", "page_119_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(0, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw or "Name" in county_raw:
                continue
            county = clean_county_name(county_raw)
            if county in seen_vt:
                continue
            seen_vt.add(county)
            voided_transactions.append({
                "county": county,
                "transaction_count":  parse_count(grid.get((row, 2), "")),
                "amount_kshs":        parse_kshs(grid.get((row, 3), "")),
            })

    # ── 11. CRF Q4 Disbursements – County Executives (Appendix 7) ────────────
    crf_exec_q4 = extract_five_col_table(
        oag_tables,
        ["page_098_table_00", "page_099_table_00"],
        ("q4_disbursement_kshs", "total_disbursed_kshs", "disbursement_pct"),
    )

    # ── 12. CRF Q4 Disbursements – County Assemblies (Appendix 8) ────────────
    crf_assembly_q4 = []
    seen_ca = set()
    for t in oag_tables:
        if t["table_id"] not in ["page_100_table_00", "page_101_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(1, max_row + 1):
            county_raw = grid.get((row, 1), "")
            if not county_raw or "Name" in county_raw:
                continue
            county = clean_county_name(county_raw)
            if county in seen_ca:
                continue
            seen_ca.add(county)
            crf_assembly_q4.append({
                "county": county,
                "q4_disbursement_kshs": parse_kshs(grid.get((row, 2), "")),
                "total_disbursed_kshs": parse_kshs(grid.get((row, 3), "")),
                "disbursement_pct":     grid.get((row, 4), "") or None,
            })

    # ── 13. Delayed Projects – County Assemblies (page_075) ───────────────────
    delayed_assembly = extract_county_project_summary(
        oag_tables,
        target_ids=["page_075_table_00"],
        col3_label="number_of_projects",
        col4_label="amount_kshs",
    )

    # ── 14. Unutilized Assets ─────────────────────────────────────────────────
    unutilized_assets = []
    for t in oag_tables:
        if t["table_id"] not in ["page_051_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        max_row = max(k[0] for k in grid) if grid else 0
        for row in range(0, max_row + 1):
            county_raw = grid.get((row, 0), "")
            description = grid.get((row, 1), "")
            amount_raw  = grid.get((row, 2), "")
            # header row has 'S/No' and 'Executive Name'
            if "Executive Name" in county_raw or not county_raw:
                # Try to pull from header cell which merges first data row
                if "County" in county_raw and description:
                    county = clean_county_name(
                        re.split(r"\s{2,}|\n", county_raw)[0]
                    )
                    unutilized_assets.append({
                        "county": county,
                        "description": description.strip(),
                        "amount_kshs": parse_kshs(amount_raw),
                    })
                continue
            county = clean_county_name(county_raw)
            if "County" in county:
                unutilized_assets.append({
                    "county": county,
                    "description": description.strip(),
                    "amount_kshs": parse_kshs(amount_raw),
                })
        break

    # ── 15. Audit Opinion Summary (Appendix 1a/1b) ────────────────────────────
    audit_opinions = []
    for t in oag_tables:
        if t["table_id"] in ["page_032_table_00"]:
            grid = cells_to_grid(t["cells"])
            max_row = max(k[0] for k in grid) if grid else 0
            for row in range(1, max_row + 1):
                opinion = grid.get((row, 0), "")
                exec_count = grid.get((row, 1), "")
                exec_pct   = grid.get((row, 2), "")
                asm_count  = grid.get((row, 3), "")
                asm_pct    = grid.get((row, 4), "")
                if opinion:
                    audit_opinions.append({
                        "opinion_type": opinion.strip(),
                        "executives_count":    parse_count(exec_count),
                        "executives_pct":      exec_pct or None,
                        "assemblies_count":    parse_count(asm_count),
                        "assemblies_pct":      asm_pct or None,
                    })
            break

    # ── 16. COB Green Book – County Table of Contents (page_005 / page_006) ──
    # These give us the list of all 47 counties covered in the Green Book
    cob_counties = []
    for t in cob_tables:
        if t["table_id"] not in ["page_005_table_00", "page_006_table_00",
                                   "page_007_table_00", "page_008_table_00"]:
            continue
        grid = cells_to_grid(t["cells"])
        for k in sorted(grid):
            text = grid[k]
            # Extract county name (before the dotted leader)
            m = re.match(r"County\s+Executive\s+of\s+([A-Za-z/\- ']+?)(?:\s+\.{3,}|\s+\d)", text)
            if m:
                name = m.group(1).strip()
                cob_counties.append(name)
            elif re.match(r"Executive\s+of\s+([A-Za-z/\- ']+?)(?:\s+\.{3,}|\s+\d)", text):
                m2 = re.match(r"Executive\s+of\s+([A-Za-z/\- ']+?)(?:\s+\.{3,}|\s+\d)", text)
                if m2:
                    cob_counties.append(m2.group(1).strip())

    # Deduplicate preserving order
    seen_cob = set()
    cob_counties_clean = []
    for c in cob_counties:
        if c not in seen_cob:
            seen_cob.add(c)
            cob_counties_clean.append(c)

    # ── Post-processing: remove OCR-corrupted rows ─────────────────────────
    def is_valid_county(county: str) -> bool:
        """True only if the string looks like a real Kenyan county name."""
        if "County" not in county:
            return False
        if len(county) > 60:
            return False
        if re.search(r"\d", county):
            return False
        noise = ["OSR", "Executive Name", "Assembly Name", "Appendix", "S/No", "Expected"]
        if any(n in county for n in noise):
            return False
        return True

    def clean_list(lst: list) -> list:
        return [r for r in lst if is_valid_county(r.get("county", ""))]

    own_source_revenue          = clean_list(own_source_revenue)
    budget_summary              = clean_list(budget_summary)
    revenue_actual              = clean_list(revenue_actual)
    exchequer                   = clean_list(exchequer)
    expenditure                 = clean_list(expenditure)
    wage_bill_exec              = clean_list(wage_bill_exec)
    crf_exec_q4                 = clean_list(crf_exec_q4)
    crf_assembly_q4             = clean_list(crf_assembly_q4)
    voided_transactions         = clean_list(voided_transactions)
    delayed_exec                = clean_list(delayed_exec)
    stalled_exec                = clean_list(stalled_exec)
    delayed_assembly            = clean_list(delayed_assembly)
    procurement_irregularities  = clean_list(procurement_irregularities)
    unutilized_assets           = clean_list(unutilized_assets)

    # ── Build final output ────────────────────────────────────────────────────
    output = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "fiscal_year": data.get("fiscal_year", "2023-2024"),
            "source": {
                "oag_report": oag_report["title"] if oag_report else None,
                "cob_report": cob_report["title"] if cob_report else None,
            },
            "description": (
                "Extracted project and financial performance data from the Kenya "
                "OAG County Governments Audit Summary Report and COB Green Book "
                "for FY 2023-2024."
            ),
        },

        # ── County-level project implementation issues ──────────────────────
        "project_implementation": {
            "_description": "Project status summaries flagged in the OAG audit report.",

            "delayed_projects_county_executives": {
                "_description": (
                    "County Executives with delayed capital projects (Appendix 26). "
                    "amount_kshs is the value of delayed projects."
                ),
                "_columns": ["county", "number_of_projects", "amount_kshs", "amount_kshs_raw"],
                "data": delayed_exec,
                "total_counties": len(delayed_exec),
            },

            "stalled_abandoned_projects_county_executives": {
                "_description": (
                    "County Executives with stalled or abandoned projects (Appendix 27). "
                    "amount_kshs is the cumulative value of stalled/abandoned projects."
                ),
                "_columns": ["county", "number_of_projects", "amount_kshs", "amount_kshs_raw"],
                "data": stalled_exec,
                "total_counties": len(stalled_exec),
            },

            "delayed_projects_county_assemblies": {
                "_description": (
                    "County Assemblies with delayed projects (OAG appendix). "
                    "amount_kshs is the value of delayed projects."
                ),
                "_columns": ["county", "number_of_projects", "amount_kshs", "amount_kshs_raw"],
                "data": delayed_assembly,
                "total_counties": len(delayed_assembly),
            },

            "unutilized_assets": {
                "_description": (
                    "County Executives with significant unutilized/idle assets flagged "
                    "during the audit (Appendix 28 area). "
                    "amount_kshs is the value of the unutilized assets."
                ),
                "_columns": ["county", "description", "amount_kshs"],
                "data": unutilized_assets,
                "total_counties": len(unutilized_assets),
            },

            "procurement_irregularities": {
                "_description": (
                    "County Executives with procurement irregularities (Appendix 24/25). "
                    "amount_kshs is the value of irregular procurement spending."
                ),
                "_columns": ["county", "amount_kshs", "amount_kshs_raw"],
                "data": procurement_irregularities,
                "total_counties": len(procurement_irregularities),
            },
        },

        # ── Financial performance ───────────────────────────────────────────
        "financial_performance": {
            "_description": "County-level financial data from OAG audit appendices.",

            "budget_summary": {
                "_description": (
                    "Approved budget allocation for County Executives and Assemblies "
                    "(Appendix 2, FY 2023-2024)."
                ),
                "_columns": ["county", "executive_budget_kshs", "assembly_budget_kshs", "total_budget_kshs"],
                "data": budget_summary,
                "total_counties": len(budget_summary),
            },

            "actual_revenue": {
                "_description": (
                    "Actual revenue collected by County Executives and Assemblies "
                    "(Appendix 3, FY 2023-2024)."
                ),
                "_columns": ["county", "executive_revenue_kshs", "assembly_revenue_kshs", "total_revenue_kshs"],
                "data": revenue_actual,
                "total_counties": len(revenue_actual),
            },

            "own_source_revenue": {
                "_description": (
                    "Own-source revenue budget vs actual and % achievement "
                    "(Appendix 5, FY 2023-2024)."
                ),
                "_columns": ["county", "budgeted_kshs", "actual_kshs", "achievement_pct"],
                "data": own_source_revenue,
                "total_counties": len(own_source_revenue),
            },

            "exchequer_releases_vs_receipts": {
                "_description": (
                    "National Government exchequer releases versus amounts "
                    "receipted in County Revenue Funds (Appendix 6)."
                ),
                "_columns": ["county", "exchequer_releases_kshs", "receipts_kshs", "variance_kshs"],
                "data": exchequer,
                "total_counties": len(exchequer),
            },

            "county_expenditure": {
                "_description": (
                    "Total expenditure by County Executives and Assemblies "
                    "(Appendix 9, FY 2023-2024)."
                ),
                "_columns": ["county", "executive_expenditure_kshs", "assembly_expenditure_kshs", "total_expenditure_kshs"],
                "data": expenditure,
                "total_counties": len(expenditure),
            },

            "wage_bill_county_executives": {
                "_description": (
                    "Personnel emoluments versus total revenue for County Executives "
                    "(Appendix 10). High values indicate over-spending on salaries."
                ),
                "_columns": ["county", "personnel_emoluments_kshs", "total_revenue_kshs", "wage_bill_pct_of_revenue"],
                "data": wage_bill_exec,
                "total_counties": len(wage_bill_exec),
            },

            "crf_q4_disbursements_executives": {
                "_description": (
                    "Q4 CRF disbursements to County Executives versus total disbursed "
                    "(Appendix 7). High Q4 % indicates last-minute fund releases."
                ),
                "_columns": ["county", "q4_disbursement_kshs", "total_disbursed_kshs", "disbursement_pct"],
                "data": crf_exec_q4,
                "total_counties": len(crf_exec_q4),
            },

            "crf_q4_disbursements_assemblies": {
                "_description": (
                    "Q4 CRF disbursements to County Assemblies versus total disbursed "
                    "(Appendix 8)."
                ),
                "_columns": ["county", "q4_disbursement_kshs", "total_disbursed_kshs", "disbursement_pct"],
                "data": crf_assembly_q4,
                "total_counties": len(crf_assembly_q4),
            },

            "voided_transactions_executives": {
                "_description": (
                    "IFMIS voided transactions in County Executives (Appendix 19). "
                    "High counts may indicate internal control weaknesses."
                ),
                "_columns": ["county", "transaction_count", "amount_kshs"],
                "data": voided_transactions,
                "total_counties": len(voided_transactions),
            },
        },

        # ── Audit quality ───────────────────────────────────────────────────
        "audit_quality": {
            "_description": "OAG audit opinion distribution for FY 2023-2024.",
            "opinion_distribution": {
                "_columns": [
                    "opinion_type",
                    "executives_count", "executives_pct",
                    "assemblies_count", "assemblies_pct",
                ],
                "data": audit_opinions,
            },
        },

        # ── COB Green Book coverage ─────────────────────────────────────────
        "cob_green_book": {
            "_description": (
                "County Executives covered in the COB Green Book "
                "(budget estimates FY 2023-2024)."
            ),
            "counties_covered": cob_counties_clean,
            "total_counties": len(cob_counties_clean),
        },
    }

    return output


# ─── entry point ──────────────────────────────────────────────────────────────

def main():
    input_path = sys.argv[1] if len(sys.argv) > 1 else "outputs/cob_oag_2023_2024_full.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "public/data/projects.json"

    input_path = str(resolve_path(input_path))
    output_path = resolve_path(output_path)

    print(f"[1/3] Loading source: {input_path}")
    data = load_source(input_path)

    print("[2/3] Extracting project data …")
    result = extract_all_projects(data)

    # Compute a quick summary
    pi = result["project_implementation"]
    fp = result["financial_performance"]
    total_delayed  = sum(
        (r.get("number_of_projects") or 0)
        for r in pi["delayed_projects_county_executives"]["data"]
        if isinstance(r.get("number_of_projects"), int)
    )
    total_stalled = sum(
        (r.get("number_of_projects") or 0)
        for r in pi["stalled_abandoned_projects_county_executives"]["data"]
        if isinstance(r.get("number_of_projects"), int)
    )
    result["metadata"]["summary_stats"] = {
        "counties_with_delayed_projects_exec": pi["delayed_projects_county_executives"]["total_counties"],
        "total_delayed_projects_exec": total_delayed,
        "counties_with_stalled_projects_exec": pi["stalled_abandoned_projects_county_executives"]["total_counties"],
        "total_stalled_projects_exec": total_stalled,
        "counties_in_budget_summary": fp["budget_summary"]["total_counties"],
        "counties_in_expenditure": fp["county_expenditure"]["total_counties"],
        "counties_in_own_source_revenue": fp["own_source_revenue"]["total_counties"],
    }

    print(f"[3/3] Writing output: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("\n✅ Done!")
    print(f"   Delayed project counties  (exec): {result['metadata']['summary_stats']['counties_with_delayed_projects_exec']}")
    print(f"   Total delayed projects    (exec): {total_delayed}")
    print(f"   Stalled project counties  (exec): {result['metadata']['summary_stats']['counties_with_stalled_projects_exec']}")
    print(f"   Total stalled projects    (exec): {total_stalled}")
    print(f"   Budget summary counties         : {fp['budget_summary']['total_counties']}")
    print(f"   Expenditure counties            : {fp['county_expenditure']['total_counties']}")
    print(f"   Own source revenue counties     : {fp['own_source_revenue']['total_counties']}")


if __name__ == "__main__":
    main()