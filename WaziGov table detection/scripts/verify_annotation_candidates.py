"""
Verify candidate pages with Table Transformer and produce final annotation shortlist.

Inputs:
- outputs/page_selection/heuristic_top40_per_pdf.json

Outputs:
- outputs/page_selection/model_verified_scores.json
- outputs/page_selection/final_recommended_pages.json
"""

import json
from pathlib import Path

import fitz
import torch
from PIL import Image
from transformers import DetrImageProcessor, TableTransformerForObjectDetection

PDF_DIR = Path("data/pdfs")
OUT_DIR = Path("outputs/page_selection")
HEURISTIC_TOP40 = OUT_DIR / "heuristic_top40_per_pdf.json"

MODEL_NAME = "microsoft/table-transformer-detection"
THRESHOLD = 0.7
DPI = 150  # Faster than 300; enough for page-level ranking.
TOP_K_PER_PDF = 18


def render_page(doc: fitz.Document, page_num_1based: int, dpi: int = DPI) -> Image.Image:
    page = doc.load_page(page_num_1based - 1)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def detect_tables(image: Image.Image, model, processor, device, threshold: float = THRESHOLD):
    inputs = processor(images=image, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)

    target_sizes = torch.tensor([image.size[::-1]], device=device)
    results = processor.post_process_object_detection(
        outputs, target_sizes=target_sizes, threshold=threshold
    )[0]

    detections = []
    for score, label, box in zip(
        results["scores"].cpu().tolist(),
        results["labels"].cpu().tolist(),
        results["boxes"].cpu().tolist(),
    ):
        detections.append(
            {
                "label": model.config.id2label.get(label, f"class_{label}"),
                "score": float(score),
                "box": [float(v) for v in box],
            }
        )

    return detections


def page_quality_score(detections, image_size):
    w, h = image_size
    page_area = max(1.0, float(w * h))

    table_dets = [d for d in detections if d["label"] in {"table", "table_rotated"}]
    n_tables = len(table_dets)
    conf_sum = sum(d["score"] for d in table_dets)

    area_ratio_sum = 0.0
    for d in table_dets:
        x1, y1, x2, y2 = d["box"]
        bw = max(0.0, x2 - x1)
        bh = max(0.0, y2 - y1)
        area_ratio_sum += (bw * bh) / page_area

    # Prefer pages with at least one confident table and substantial table area.
    score = (n_tables * 12.0) + (conf_sum * 8.0) + (area_ratio_sum * 30.0)

    return {
        "n_tables": n_tables,
        "confidence_sum": round(conf_sum, 4),
        "table_area_ratio_sum": round(area_ratio_sum, 4),
        "model_score": round(score, 4),
    }


def main():
    if not HEURISTIC_TOP40.exists():
        raise FileNotFoundError(
            f"Missing {HEURISTIC_TOP40}. Run scripts/rank_annotation_pages.py first."
        )

    candidates = json.loads(HEURISTIC_TOP40.read_text(encoding="utf-8"))

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    print(f"Loading model: {MODEL_NAME}")
    processor = DetrImageProcessor.from_pretrained(MODEL_NAME)
    model = TableTransformerForObjectDetection.from_pretrained(MODEL_NAME).to(device)
    model.eval()

    verified = {}

    for pdf_name, pages in candidates.items():
        pdf_path = PDF_DIR / pdf_name
        if not pdf_path.exists():
            continue

        print(f"\nScoring {pdf_name}")
        doc = fitz.open(pdf_path)
        page_count = len(doc)

        # Candidate pages from heuristic pass.
        candidate_pages = sorted({int(p["page"]) for p in pages})

        # For short PDFs, evaluate all pages (helps image-only/scanned docs).
        if page_count <= 40:
            candidate_pages = list(range(1, page_count + 1))

        results = []
        for p in candidate_pages:
            image = render_page(doc, p, DPI)
            dets = detect_tables(image, model, processor, device, THRESHOLD)
            metrics = page_quality_score(dets, image.size)
            results.append(
                {
                    "page": p,
                    **metrics,
                }
            )

        doc.close()

        results.sort(key=lambda x: x["model_score"], reverse=True)
        verified[pdf_name] = results

        preview = results[:5]
        for row in preview:
            print(
                f"  page {row['page']:>4} score={row['model_score']:.2f} "
                f"tables={row['n_tables']} area={row['table_area_ratio_sum']:.3f}"
            )

    recommended = {}
    for pdf_name, rows in verified.items():
        recommended[pdf_name] = [
            {
                "page": r["page"],
                "model_score": r["model_score"],
                "n_tables": r["n_tables"],
                "table_area_ratio_sum": r["table_area_ratio_sum"],
            }
            for r in rows[:TOP_K_PER_PDF]
            if r["n_tables"] > 0
        ]

    (OUT_DIR / "model_verified_scores.json").write_text(
        json.dumps(verified, indent=2), encoding="utf-8"
    )
    (OUT_DIR / "final_recommended_pages.json").write_text(
        json.dumps(recommended, indent=2), encoding="utf-8"
    )

    print(f"\nSaved: {OUT_DIR / 'model_verified_scores.json'}")
    print(f"Saved: {OUT_DIR / 'final_recommended_pages.json'}")


if __name__ == "__main__":
    main()
