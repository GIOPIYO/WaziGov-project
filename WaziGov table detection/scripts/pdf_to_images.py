"""
PDF to Page Image Converter for WaziGov Table Detection
========================================================
Converts PDF documents to 300 DPI page images for annotation and model input.

Usage:
    python scripts/pdf_to_images.py                          # Process all PDFs in data/pdfs/
    python scripts/pdf_to_images.py --input path/to/file.pdf # Process a single PDF
    python scripts/pdf_to_images.py --dpi 300 --format png   # Custom DPI and format
"""

import argparse
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF


def pdf_to_images(
    pdf_path: str,
    output_dir: str,
    dpi: int = 300,
    image_format: str = "png",
    page_range: tuple = None,
) -> list[str]:
    """
    Convert a PDF to per-page images at the specified DPI.

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Directory to save the page images.
        dpi: Resolution in dots per inch (default: 300 as per proposal).
        image_format: Output format - 'png' or 'jpg'.
        page_range: Optional (start, end) tuple for specific pages (1-indexed).

    Returns:
        List of output image file paths.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    pdf_stem = pdf_path.stem

    # Determine page range
    start = (page_range[0] - 1) if page_range else 0
    end = page_range[1] if page_range else len(doc)

    zoom = dpi / 72  # PyMuPDF default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    output_paths = []
    for page_num in range(start, end):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)

        # Naming: <pdf_stem>_page_<NNN>.<ext>
        filename = f"{pdf_stem}_page_{page_num + 1:03d}.{image_format}"
        output_path = output_dir / filename

        if image_format == "png":
            pix.save(str(output_path))
        elif image_format in ("jpg", "jpeg"):
            pix.save(str(output_path), jpg_quality=95)

        output_paths.append(str(output_path))
        print(f"  Page {page_num + 1}/{end}: {filename} ({pix.width}x{pix.height}px)")

    doc.close()
    return output_paths


def process_all_pdfs(
    input_dir: str, output_dir: str, dpi: int = 300, image_format: str = "png"
) -> dict:
    """Process all PDFs in the input directory."""
    input_dir = Path(input_dir)
    results = {}

    pdf_files = sorted(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return results

    for pdf_path in pdf_files:
        print(f"\nProcessing: {pdf_path.name}")
        paths = pdf_to_images(pdf_path, output_dir, dpi, image_format)
        results[pdf_path.name] = paths
        print(f"  -> {len(paths)} pages extracted")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Convert government PDF documents to page images for annotation"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to a single PDF file. If not provided, processes all PDFs in data/pdfs/",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory (default: data/images/pages/)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Resolution in DPI (default: 300)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="png",
        choices=["png", "jpg"],
        help="Image format (default: png)",
    )
    parser.add_argument(
        "--pages",
        type=str,
        default=None,
        help="Page range to extract, e.g. '1-10' (1-indexed, inclusive)",
    )

    args = parser.parse_args()

    # Resolve project root (two levels up from scripts/)
    project_root = Path(__file__).resolve().parent.parent
    output_dir = Path(args.output) if args.output else project_root / "data" / "images" / "pages"

    page_range = None
    if args.pages:
        parts = args.pages.split("-")
        page_range = (int(parts[0]), int(parts[1]))

    if args.input:
        print(f"Converting: {args.input}")
        print(f"DPI: {args.dpi}, Format: {args.format}")
        paths = pdf_to_images(args.input, str(output_dir), args.dpi, args.format, page_range)
        print(f"\nDone! {len(paths)} page images saved to {output_dir}")
    else:
        input_dir = project_root / "data" / "pdfs"
        print(f"Processing all PDFs in: {input_dir}")
        print(f"DPI: {args.dpi}, Format: {args.format}")
        results = process_all_pdfs(str(input_dir), str(output_dir), args.dpi, args.format)
        total = sum(len(v) for v in results.values())
        print(f"\nDone! {total} total page images from {len(results)} PDF(s) saved to {output_dir}")


if __name__ == "__main__":
    main()
