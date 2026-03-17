"""
Convert Label Studio Annotations to PubTables-1M Format
=========================================================
Converts Label Studio JSON export to the PASCAL VOC XML format used by
PubTables-1M, which is what the Table Transformer expects for training.

PubTables-1M format per image:
  <annotation>
    <folder>...</folder>
    <filename>image.png</filename>
    <size><width>W</width><height>H</height><depth>3</depth></size>
    <object>
      <name>table</name>
      <bndbox><xmin>x1</xmin><ymin>y1</ymin><xmax>x2</xmax><ymax>y2</ymax></bndbox>
    </object>
    ...
  </annotation>

Usage:
    python scripts/convert_annotations.py --input export.json --stage detection
    python scripts/convert_annotations.py --input export.json --stage structure
"""

import argparse
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from PIL import Image


def labelstudio_to_pascal_voc(
    input_path: str,
    images_dir: str,
    output_dir: str,
    stage: str = "detection",
) -> int:
    """
    Convert Label Studio JSON export to PASCAL VOC XML annotations.

    Args:
        input_path: Path to the Label Studio JSON export file.
        images_dir: Directory containing the source images.
        output_dir: Directory to save the XML annotation files.
        stage: 'detection' or 'structure' (determines valid label set).

    Returns:
        Number of annotation files created.
    """
    valid_labels = {
        "detection": {"table", "table_rotated"},
        "structure": {
            "table_row",
            "table_column",
            "table_spanning_cell",
            "table_projected_row_header",
            "table_column_header",
        },
    }

    if stage not in valid_labels:
        raise ValueError(f"Stage must be 'detection' or 'structure', got '{stage}'")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, "r") as f:
        tasks = json.load(f)

    count = 0
    for task in tasks:
        annotations = task.get("annotations", [])

        # Skip tasks with no annotations (pages with no tables)
        if not annotations or not annotations[0].get("result", []):
            print(f"  Skipping task {task.get('id', '?')} - no annotations")
            continue

        results = annotations[0]["result"]

        # Get image dimensions from the first result
        img_width = results[0].get("original_width", 0)
        img_height = results[0].get("original_height", 0)

        # If dimensions not in annotation, try reading from the actual image
        if img_width == 0 or img_height == 0:
            from PIL import Image as PILImage
            img_filename = task["data"]["image"].split("/")[-1].split("?d=")[-1]
            img_path = os.path.join(images_dir, img_filename)
            if os.path.exists(img_path):
                with PILImage.open(img_path) as img:
                    img_width, img_height = img.size
            else:
                print(f"  Skipping - image not found: {img_path}")
                continue

        # Get the image filename
        img_filename = task["data"]["image"].split("/")[-1].split("?d=")[-1]

        # Build XML annotation
        annotation = ET.Element("annotation")
        ET.SubElement(annotation, "folder").text = str(output_dir.name)
        ET.SubElement(annotation, "filename").text = img_filename

        size = ET.SubElement(annotation, "size")
        ET.SubElement(size, "width").text = str(img_width)
        ET.SubElement(size, "height").text = str(img_height)
        ET.SubElement(size, "depth").text = "3"

        # Process annotations
        has_objects = False

        for ann in annotations:
            results = ann.get("result", [])
            for result in results:
                if result.get("type") != "rectanglelabels":
                    continue

                value = result.get("value", {})
                labels = value.get("rectanglelabels", [])

                for label in labels:
                    if label not in valid_labels[stage]:
                        print(f"  Warning: Skipping unknown label '{label}' in {img_filename}")
                        continue

                    # Label Studio stores as percentages (0-100)
                    x_pct = value.get("x", 0)
                    y_pct = value.get("y", 0)
                    w_pct = value.get("width", 0)
                    h_pct = value.get("height", 0)

                    # Convert to pixel coordinates
                    xmin = int(x_pct / 100.0 * img_width)
                    ymin = int(y_pct / 100.0 * img_height)
                    xmax = int((x_pct + w_pct) / 100.0 * img_width)
                    ymax = int((y_pct + h_pct) / 100.0 * img_height)

                    # Clamp to image bounds
                    xmin = max(0, min(xmin, img_width))
                    ymin = max(0, min(ymin, img_height))
                    xmax = max(0, min(xmax, img_width))
                    ymax = max(0, min(ymax, img_height))

                    obj = ET.SubElement(annotation, "object")
                    ET.SubElement(obj, "name").text = label
                    ET.SubElement(obj, "pose").text = "Unspecified"
                    ET.SubElement(obj, "truncated").text = "0"
                    ET.SubElement(obj, "difficult").text = "0"

                    bndbox = ET.SubElement(obj, "bndbox")
                    ET.SubElement(bndbox, "xmin").text = str(xmin)
                    ET.SubElement(bndbox, "ymin").text = str(ymin)
                    ET.SubElement(bndbox, "xmax").text = str(xmax)
                    ET.SubElement(bndbox, "ymax").text = str(ymax)

                    has_objects = True

        if has_objects:
            # Pretty-print XML
            xml_str = minidom.parseString(ET.tostring(annotation)).toprettyxml(indent="  ")
            # Remove the XML declaration added by minidom
            xml_str = "\n".join(xml_str.split("\n")[1:])

            xml_filename = Path(img_filename).stem + ".xml"
            xml_path = output_dir / xml_filename
            with open(xml_path, "w") as f:
                f.write(xml_str)

            count += 1
            print(f"  {xml_filename}: {len(annotation.findall('object'))} objects")

    return count


def generate_split_files(
    annotations_dir: str,
    splits_dir: str,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> None:
    """
    Generate train/val/test split text files.
    Each file lists the image stems (without extension) for that split.
    70/15/15 split as specified in the proposal.
    """
    import random

    annotations_dir = Path(annotations_dir)
    splits_dir = Path(splits_dir)
    splits_dir.mkdir(parents=True, exist_ok=True)

    xml_files = sorted(annotations_dir.glob("*.xml"))
    stems = [f.stem for f in xml_files]

    random.seed(42)  # Reproducibility
    random.shuffle(stems)

    n = len(stems)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_stems = stems[:n_train]
    val_stems = stems[n_train : n_train + n_val]
    test_stems = stems[n_train + n_val :]

    for split_name, split_stems in [
        ("train", train_stems),
        ("val", val_stems),
        ("test", test_stems),
    ]:
        split_path = splits_dir / f"{split_name}.txt"
        with open(split_path, "w") as f:
            f.write("\n".join(split_stems) + "\n")
        print(f"  {split_name}: {len(split_stems)} images -> {split_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Label Studio annotations to PubTables-1M (PASCAL VOC) format"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to Label Studio JSON export file",
    )
    parser.add_argument(
        "--stage",
        type=str,
        required=True,
        choices=["detection", "structure"],
        help="Annotation stage: 'detection' (full page) or 'structure' (table crops)",
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default=None,
        help="Directory with source images (default: data/images/pages/)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for XMLs (default: data/annotations/pubtables1m/)",
    )
    parser.add_argument(
        "--split",
        action="store_true",
        help="Also generate train/val/test split files",
    )

    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    images_dir = (
        Path(args.images_dir)
        if args.images_dir
        else project_root / "data" / "images" / "pages"
    )
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else project_root / "data" / "annotations" / "pubtables1m"
    )

    print(f"Converting: {args.input}")
    print(f"Stage: {args.stage}")
    print(f"Images: {images_dir}")
    print(f"Output: {output_dir}")

    count = labelstudio_to_pascal_voc(args.input, str(images_dir), str(output_dir), args.stage)
    print(f"\nConverted {count} annotations to PASCAL VOC format")

    if args.split and count > 0:
        print("\nGenerating train/val/test splits (70/15/15):")
        splits_dir = project_root / "data" / "splits"
        generate_split_files(str(output_dir), str(splits_dir))


if __name__ == "__main__":
    main()
