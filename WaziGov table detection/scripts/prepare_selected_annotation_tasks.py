"""
Prepare selected pages for Label Studio annotation.

This script:
1. Reads outputs/page_selection/final_recommended_pages.json
2. Renders only those pages to data/images/pages_selected/ at 300 DPI
3. Writes Label Studio import JSON to data/annotations/labelstudio/import_tasks_selected.json
"""

import argparse
import json
from pathlib import Path

import fitz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
IMAGES_DIR = PROJECT_ROOT / "data" / "images" / "pages_selected"
TASKS_PATH = PROJECT_ROOT / "data" / "annotations" / "labelstudio" / "import_tasks_selected.json"
RECOMMENDED_PATH = PROJECT_ROOT / "outputs" / "page_selection" / "final_recommended_pages.json"

DPI = 300
SERVE_URL = "/data/local-files/?d="


def render_page(pdf_path: Path, page_num_1based: int, output_path: Path, dpi: int = DPI) -> None:
    doc = fitz.open(pdf_path)
    try:
        page = doc.load_page(page_num_1based - 1)
        zoom = dpi / 72
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), colorspace=fitz.csRGB)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(output_path))
    finally:
        doc.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare selected Label Studio tasks")
    parser.add_argument(
        "--limit-per-pdf",
        type=int,
        default=15,
        help="Maximum pages per PDF from recommendations (default: 15)",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Include all recommended pages without per-PDF limiting",
    )
    args = parser.parse_args()

    if not RECOMMENDED_PATH.exists():
        raise FileNotFoundError(f"Missing recommended pages file: {RECOMMENDED_PATH}")

    recommendations = json.loads(RECOMMENDED_PATH.read_text(encoding="utf-8"))

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_PATH.parent.mkdir(parents=True, exist_ok=True)

    tasks = []
    created = 0
    reused = 0

    for pdf_name, page_entries in recommendations.items():
        selected_entries = page_entries if args.include_all else page_entries[: args.limit_per_pdf]
        pdf_path = PDF_DIR / pdf_name
        if not pdf_path.exists():
            print(f"Skipping missing PDF: {pdf_name}")
            continue

        for entry in selected_entries:
            page_num = int(entry["page"])
            out_name = f"{pdf_path.stem}_page_{page_num:03d}.png"
            out_path = IMAGES_DIR / out_name

            if out_path.exists():
                reused += 1
            else:
                render_page(pdf_path, page_num, out_path, DPI)
                created += 1

            tasks.append(
                {
                    "data": {
                        "image": f"{SERVE_URL}{out_name}",
                    },
                    "meta": {
                        "source_file": out_name,
                        "page_number": page_num,
                        "pdf_name": pdf_name,
                        "recommended": True,
                        "selection_method": "heuristic_plus_model_verification",
                    },
                }
            )

    TASKS_PATH.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

    print(f"Created images: {created}")
    print(f"Reused images: {reused}")
    print(f"Total tasks: {len(tasks)}")
    print(f"Images dir: {IMAGES_DIR}")
    print(f"Tasks file: {TASKS_PATH}")


if __name__ == "__main__":
    main()
