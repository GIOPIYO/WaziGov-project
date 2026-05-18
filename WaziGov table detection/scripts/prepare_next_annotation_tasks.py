"""
Prepare a next batch of Label Studio tasks without reusing already-annotated pages.

This script:
1. Reads model-verified candidates from outputs/page_selection/model_verified_scores.json
2. Excludes pages already present in a prior Label Studio export
3. Renders only new pages to an output image directory
4. Writes a new Label Studio import JSON for round-2 annotation
"""

import argparse
import json
from pathlib import Path
from urllib.parse import unquote

import fitz

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = PROJECT_ROOT / "data" / "pdfs"
DEFAULT_RECOMMENDATIONS = PROJECT_ROOT / "outputs" / "page_selection" / "model_verified_scores.json"
DEFAULT_USED_EXPORT = PROJECT_ROOT / "data" / "annotations" / "labelstudio" / "project-3-at-2026-03-24-23-06-b3b74b08.json"
DEFAULT_IMAGES_DIR = PROJECT_ROOT / "data" / "images" / "pages_selected_round2"
DEFAULT_TASKS_PATH = PROJECT_ROOT / "data" / "annotations" / "labelstudio" / "import_tasks_selected_round2.json"
SERVE_URL = "/data/local-files/?d="


def extract_image_filename(image_value: str) -> str:
    raw = image_value or ""
    if "?d=" in raw:
        raw = raw.split("?d=", 1)[1]
    raw = unquote(raw).replace("\\", "/")
    return Path(raw).name


def load_used_image_filenames(used_export_json: Path) -> set[str]:
    if not used_export_json.exists():
        return set()

    tasks = json.loads(used_export_json.read_text(encoding="utf-8"))
    used = set()
    for task in tasks:
        image_value = task.get("data", {}).get("image", "")
        image_name = extract_image_filename(image_value)
        if image_name:
            used.add(image_name)
    return used


def render_page(pdf_path: Path, page_num_1based: int, output_path: Path, dpi: int) -> None:
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
    parser = argparse.ArgumentParser(description="Prepare next annotation tasks excluding used pages")
    parser.add_argument("--recommendations-path", type=str, default=str(DEFAULT_RECOMMENDATIONS))
    parser.add_argument("--used-export-json", type=str, default=str(DEFAULT_USED_EXPORT))
    parser.add_argument("--images-dir", type=str, default=str(DEFAULT_IMAGES_DIR))
    parser.add_argument("--tasks-path", type=str, default=str(DEFAULT_TASKS_PATH))
    parser.add_argument("--limit-per-pdf", type=int, default=10)
    parser.add_argument("--min-tables", type=int, default=1)
    parser.add_argument("--min-model-score", type=float, default=0.0)
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    recommendations_path = Path(args.recommendations_path)
    used_export_json = Path(args.used_export_json)
    images_dir = Path(args.images_dir)
    tasks_path = Path(args.tasks_path)

    if not recommendations_path.exists():
        raise FileNotFoundError(f"Missing recommendations file: {recommendations_path}")

    recommendations = json.loads(recommendations_path.read_text(encoding="utf-8"))
    used_images = load_used_image_filenames(used_export_json)

    images_dir.mkdir(parents=True, exist_ok=True)
    tasks_path.parent.mkdir(parents=True, exist_ok=True)

    tasks = []
    created = 0
    reused = 0

    for pdf_name, entries in recommendations.items():
        pdf_path = PDF_DIR / pdf_name
        if not pdf_path.exists():
            print(f"Skipping missing PDF: {pdf_name}")
            continue

        selected_for_pdf = 0
        for entry in entries:
            if selected_for_pdf >= args.limit_per_pdf:
                break

            n_tables = int(entry.get("n_tables", 0))
            model_score = float(entry.get("model_score", 0.0))
            if n_tables < args.min_tables or model_score < args.min_model_score:
                continue

            page_num = int(entry["page"])
            out_name = f"{pdf_path.stem}_page_{page_num:03d}.png"

            if out_name in used_images:
                continue

            out_path = images_dir / out_name
            if out_path.exists():
                reused += 1
            else:
                render_page(pdf_path, page_num, out_path, args.dpi)
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
                        "selection_method": "model_verified_excluding_used",
                        "model_score": model_score,
                        "n_tables": n_tables,
                    },
                }
            )
            selected_for_pdf += 1

        print(f"{pdf_name}: selected {selected_for_pdf} new pages")

    tasks_path.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

    print(f"Used pages excluded: {len(used_images)}")
    print(f"Created images: {created}")
    print(f"Reused images: {reused}")
    print(f"Total new tasks: {len(tasks)}")
    print(f"Images dir: {images_dir}")
    print(f"Tasks file: {tasks_path}")


if __name__ == "__main__":
    main()
