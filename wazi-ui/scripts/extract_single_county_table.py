from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PREFERRED_TABLE_IDS = [
    "page_030_table_00",
    "page_087_table_00",
    "page_088_table_00",
    "page_089_table_00",
    "page_090_table_00",
    "page_095_table_00",
    "page_096_table_00",
    "page_102_table_00",
    "page_103_table_00",
]

COUNTIES = [
    "Baringo", "Bomet", "Bungoma", "Busia", "Elgeyo-Marakwet", "Embu", "Garissa",
    "Homa Bay", "Isiolo", "Kajiado", "Kakamega", "Kericho", "Kiambu", "Kilifi",
    "Kirinyaga", "Kisii", "Kisumu", "Kitui", "Kwale", "Laikipia", "Lamu", "Machakos",
    "Makueni", "Mandera", "Marsabit", "Meru", "Migori", "Mombasa", "Murang'a",
    "Nairobi", "Nakuru", "Nandi", "Narok", "Nyamira", "Nyandarua", "Nyeri", "Samburu",
    "Siaya", "Taita-Taveta", "Tana River", "Tharaka-Nithi", "Trans Nzoia", "Turkana",
    "Uasin Gishu", "Vihiga", "Wajir", "West Pokot",
]

COUNTY_NORMALIZED = {re.sub(r"[^a-z0-9]", "", county.lower()): county for county in COUNTIES}
FINANCIAL_KEYWORDS = (
    "budget",
    "allocation",
    "actual",
    "variance",
    "revenue",
    "expenditure",
    "receipt",
    "approved",
    "estimate",
    "fund",
)


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parents[1] / candidate


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


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


def table_text(table: dict[str, Any]) -> str:
    snippets = [table.get("title") or "", table.get("raw_text") or ""]
    for cell in table.get("cells", [])[:250]:
        snippets.append(cell.get("raw_text") or "")
    return normalize_text(" ".join(snippets))


def score_table(table: dict[str, Any]) -> tuple[int, int, int]:
    text = table_text(table)
    county_hits = 0
    compact = re.sub(r"[^a-z0-9]", "", text)
    for county in COUNTIES:
        if re.sub(r"[^a-z0-9]", "", county.lower()) in compact:
            county_hits += 1

    financial_hits = sum(1 for keyword in FINANCIAL_KEYWORDS if keyword in text)
    cell_count = len(table.get("cells", []))
    return county_hits, financial_hits, cell_count


def iter_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def find_table(bundle: dict[str, Any], preferred_ids: list[str]) -> dict[str, Any]:
    for item in iter_dicts(bundle):
        if item.get("table_id") in preferred_ids:
            return item

    scored: list[tuple[tuple[int, int, int], dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for item in iter_dicts(bundle):
        if item.get("table_id"):
            score = score_table(item)
            if score[0] > 0 and score[1] > 0:
                scored.append((score, {}, {}, item))

    if scored:
        scored.sort(key=lambda item: (-item[0][0], -item[0][1], -item[0][2], str(item[3].get("table_id") or "")))
        _, _, _, table = scored[0]
        return table

    debug_path = Path(__file__).resolve().parents[1] / "outputs" / "county_table_candidates.txt"
    candidates: list[str] = []
    for table in iter_dicts(bundle):
        if table.get("table_id"):
            score = score_table(table)
            if score[0] > 0 or score[1] > 0:
                candidates.append(
                    f"score={score[0]}/{score[1]}/{score[2]} | table={table.get('table_id')} | title={table.get('title')!r} | raw={(table.get('raw_text') or '')[:180].replace(chr(10), ' ')}"
                )

    candidates.sort(reverse=True)
    debug_path.write_text("\n".join(candidates[:40]) + ("\n" if candidates else ""), encoding="utf-8")

    raise ValueError(f"No county/financial table found in bundle and preferred ids were not present: {preferred_ids}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract a single county financial table from the COB/OAG bundle.")
    parser.add_argument("--input", default="outputs/cob_oag_2023_2024_full.json", help="Source JSON bundle path")
    parser.add_argument("--output", default="outputs/county_financial_table.json", help="Output JSON path")
    args = parser.parse_args()

    input_path = resolve_path(args.input)
    output_path = resolve_path(args.output)

    bundle = load_json(input_path)
    table = find_table(bundle, PREFERRED_TABLE_IDS)

    table_payload = {
        "table_id": table.get("table_id"),
        "title": table.get("title"),
        "raw_text": table.get("raw_text"),
        "cells": table.get("cells", []),
    }

    payload = {
        "source_file": str(input_path.relative_to(Path(__file__).resolve().parents[1])) if input_path.is_relative_to(Path(__file__).resolve().parents[1]) else str(input_path),
        "table": table_payload,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(f"Wrote {output_path}")
    print(f"Selected table id: {table.get('table_id')}")


if __name__ == "__main__":
    main()
