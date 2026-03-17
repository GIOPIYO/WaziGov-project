"""
Label Studio Setup Script for WaziGov Table Detection
=====================================================
Generates the Label Studio import JSON for page images so you can
immediately start annotating in the browser.

Usage:
    python scripts/setup_labelstudio.py
    python scripts/setup_labelstudio.py --images-dir data/images/pages
"""

import argparse
import json
from pathlib import Path


def generate_import_json(images_dir: str, output_path: str, serve_url: str = "/data/local-files/?d=") -> None:
    """
    Generate a Label Studio-compatible import JSON file.
    
    Each entry maps an image file so Label Studio can load it.
    For local file serving, images are referenced via the local storage path.
    """
    images_dir = Path(images_dir)
    output_path = Path(output_path)

    image_files = sorted(
        list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
    )

    if not image_files:
        print(f"No images found in {images_dir}")
        return

    tasks = []
    for img_path in image_files:
        task = {
            "data": {
                "image": f"{serve_url}{img_path.name}"
            },
            "meta": {
                "source_file": img_path.name,
                "page_number": int(img_path.stem.split("_page_")[-1]) if "_page_" in img_path.stem else 0,
                "pdf_name": img_path.stem.rsplit("_page_", 1)[0] if "_page_" in img_path.stem else img_path.stem,
            }
        }
        tasks.append(task)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(tasks, f, indent=2)

    print(f"Generated {len(tasks)} tasks -> {output_path}")
    print(f"\nNext steps:")
    print(f"  1. Install Label Studio:  pip install label-studio")
    print(f"  2. Start Label Studio:    label-studio start")
    print(f"  3. Create a new project named 'WaziGov Table Detection'")
    print(f"  4. In Settings > Labeling Interface, paste the contents of:")
    print(f"     configs/labelstudio_table_detection.xml")
    print(f"  5. Set up Local Storage in Settings > Cloud Storage:")
    print(f"     - Add Local Storage, set the path to: {images_dir.resolve()}")
    print(f"  6. Import tasks from: {output_path.resolve()}")
    print(f"  7. Start annotating!")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Label Studio import file for WaziGov annotation"
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=None,
        help="Directory containing page images (default: data/images/pages/)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: data/annotations/labelstudio/import_tasks.json)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    images_dir = Path(args.images_dir) if args.images_dir else project_root / "data" / "images" / "pages"
    output_path = (
        Path(args.output)
        if args.output
        else project_root / "data" / "annotations" / "labelstudio" / "import_tasks.json"
    )

    generate_import_json(str(images_dir), str(output_path))


if __name__ == "__main__":
    main()
