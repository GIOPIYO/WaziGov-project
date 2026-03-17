"""
Crop Detected Tables for Structure Annotation
===============================================
After completing Stage 1 (table detection) annotation, this script crops
each annotated table region from the full page images, producing individual
table images for Stage 2 (structure recognition) annotation.

Usage:
    python scripts/crop_tables.py --annotations data/annotations/pubtables1m/
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


def crop_tables_from_annotations(
    annotations_dir: str,
    images_dir: str,
    output_dir: str,
    padding: int = 10,
) -> int:
    """
    Crop table regions from full page images using PASCAL VOC annotations.

    Args:
        annotations_dir: Directory containing PASCAL VOC XML files.
        images_dir: Directory containing source page images.
        output_dir: Directory to save cropped table images.
        padding: Pixel padding around each table crop (default: 10).

    Returns:
        Number of table crops saved.
    """
    annotations_dir = Path(annotations_dir)
    images_dir = Path(images_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    xml_files = sorted(annotations_dir.glob("*.xml"))
    if not xml_files:
        print(f"No XML annotations found in {annotations_dir}")
        return 0

    crop_count = 0
    for xml_path in xml_files:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename = root.find("filename").text
        image_path = images_dir / filename

        if not image_path.exists():
            print(f"  Warning: Image not found: {image_path}")
            continue

        img = Image.open(image_path)
        img_w, img_h = img.size

        table_idx = 0
        for obj in root.findall("object"):
            label = obj.find("name").text
            if label not in ("table", "table_rotated"):
                continue

            bndbox = obj.find("bndbox")
            xmin = max(0, int(bndbox.find("xmin").text) - padding)
            ymin = max(0, int(bndbox.find("ymin").text) - padding)
            xmax = min(img_w, int(bndbox.find("xmax").text) + padding)
            ymax = min(img_h, int(bndbox.find("ymax").text) + padding)

            crop = img.crop((xmin, ymin, xmax, ymax))

            # Naming: <page_stem>_table_<NN>.png
            crop_name = f"{xml_path.stem}_table_{table_idx:02d}.png"
            crop_path = output_dir / crop_name
            crop.save(str(crop_path))

            crop_count += 1
            table_idx += 1
            print(f"  {crop_name}: {crop.width}x{crop.height}px")

        img.close()

    return crop_count


def main():
    parser = argparse.ArgumentParser(
        description="Crop annotated table regions for structure recognition annotation"
    )
    parser.add_argument(
        "--annotations",
        type=str,
        default=None,
        help="Directory with PASCAL VOC XML annotations (default: data/annotations/pubtables1m/)",
    )
    parser.add_argument(
        "--images",
        type=str,
        default=None,
        help="Directory with source page images (default: data/images/pages/)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output directory for cropped tables (default: data/images/table_crops/)",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=10,
        help="Pixel padding around each crop (default: 10)",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    annotations_dir = (
        Path(args.annotations)
        if args.annotations
        else project_root / "data" / "annotations" / "pubtables1m"
    )
    images_dir = (
        Path(args.images) if args.images else project_root / "data" / "images" / "pages"
    )
    output_dir = (
        Path(args.output)
        if args.output
        else project_root / "data" / "images" / "table_crops"
    )

    print(f"Cropping tables from annotations in: {annotations_dir}")
    count = crop_tables_from_annotations(
        str(annotations_dir), str(images_dir), str(output_dir), args.padding
    )
    print(f"\nDone! {count} table crops saved to {output_dir}")
    
    if count > 0:
        print(f"\nNext: Annotate table structure on these crops using Label Studio")
        print(f"  Use config: configs/labelstudio_structure_recognition.xml")


if __name__ == "__main__":
    main()
