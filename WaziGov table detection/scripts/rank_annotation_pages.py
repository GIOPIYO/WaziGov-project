"""
Rank PDF pages by likely table richness for annotation prioritization.

This uses fast text heuristics so we can score large PDFs quickly.
Output files are written to outputs/page_selection/.
"""

import json
import re
from pathlib import Path

import fitz

PDF_DIR = Path("data/pdfs")
OUT_DIR = Path("outputs/page_selection")
OUT_DIR.mkdir(parents=True, exist_ok=True)

NUM_PAT = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+\b|\b\d+%\b")
KW_PAT = re.compile(
    r"budget|actual|variance|total|expenditure|revenue|county|ksh|audit|statement|summary|amount|approved|collection",
    re.I,
)


def page_score(text: str):
    if not text:
        return 0.0, {
            "line_count": 0,
            "num_hits": 0,
            "keyword_hits": 0,
            "dense_numeric_lines": 0,
            "long_lines": 0,
        }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    nums = len(NUM_PAT.findall(text))
    kws = len(KW_PAT.findall(text))
    dense_lines = sum(1 for ln in lines if len(NUM_PAT.findall(ln)) >= 3)
    long_lines = sum(1 for ln in lines if len(ln) > 80)

    # Favor pages that look like financial tables:
    # lots of numeric tokens + finance keywords + row-like dense lines.
    score = (nums * 1.2) + (kws * 0.8) + (dense_lines * 5.0) + (long_lines * 0.2)

    return score, {
        "line_count": len(lines),
        "num_hits": nums,
        "keyword_hits": kws,
        "dense_numeric_lines": dense_lines,
        "long_lines": long_lines,
    }


def main():
    all_ranked = {}

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        doc = fitz.open(pdf_path)
        ranked = []

        for idx in range(len(doc)):
            txt = doc.load_page(idx).get_text("text")
            score, feats = page_score(txt)
            ranked.append({
                "page": idx + 1,
                "score": round(score, 3),
                **feats,
            })

        doc.close()
        ranked.sort(key=lambda x: x["score"], reverse=True)
        all_ranked[pdf_path.name] = ranked

    top40 = {pdf: pages[:40] for pdf, pages in all_ranked.items()}
    top20 = {pdf: pages[:20] for pdf, pages in all_ranked.items()}

    (OUT_DIR / "heuristic_rankings_all.json").write_text(
        json.dumps(all_ranked, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "heuristic_top40_per_pdf.json").write_text(
        json.dumps(top40, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "heuristic_top20_per_pdf.json").write_text(
        json.dumps(top20, indent=2), encoding="utf-8"
    )

    print(f"Saved: {OUT_DIR / 'heuristic_rankings_all.json'}")
    print(f"Saved: {OUT_DIR / 'heuristic_top40_per_pdf.json'}")
    print(f"Saved: {OUT_DIR / 'heuristic_top20_per_pdf.json'}")

    for pdf, pages in top20.items():
        print(f"\n{pdf}")
        for p in pages[:5]:
            print(
                f"  page {p['page']:>4} score={p['score']:.1f} "
                f"nums={p['num_hits']} dense={p['dense_numeric_lines']}"
            )


if __name__ == "__main__":
    main()
