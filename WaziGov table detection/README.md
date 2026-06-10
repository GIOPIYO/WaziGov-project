# WaziGov Table Detection - Annotation Guide

## Project Overview

Computer Vision module for extracting table structures from Kenyan government financial documents using a DETR-based Table Transformer. This project follows a **two-stage annotation** approach matching the PubTables-1M standard.

## Project Structure

```
WaziGov table detection/
├── configs/
│   ├── labelstudio_table_detection.xml      # Stage 1: full-page table bboxes
│   └── labelstudio_structure_recognition.xml # Stage 2: row/col/cell structure
├── data/
│   ├── pdfs/                                # Source government PDFs
│   ├── images/
│   │   ├── pages/                           # 300 DPI page images (auto-generated)
│   │   └── table_crops/                     # Cropped tables (after Stage 1)
│   ├── annotations/
│   │   ├── labelstudio/                     # Label Studio import/export JSONs
│   │   └── pubtables1m/                     # PASCAL VOC XMLs (training format)
│   └── splits/
│       ├── train.txt                        # 70% of annotated pages
│       ├── val.txt                          # 15%
│       └── test.txt                         # 15%
├── scripts/
│   ├── pdf_to_images.py                     # Convert PDFs → page images
│   ├── setup_labelstudio.py                 # Generate Label Studio import file
│   ├── convert_annotations.py               # Label Studio → PASCAL VOC XMLs
│   └── crop_tables.py                       # Crop tables for structure annotation
└── requirements.txt
```

## Quick Start

### 1. Convert PDFs to Images

```bash
python scripts/pdf_to_images.py
```

This converts all PDFs in `data/pdfs/` to 300 DPI PNG images in `data/images/pages/`.

### 2. Install & Launch Label Studio

```bash
pip install label-studio
label-studio start
```

Label Studio opens at **http://localhost:8080**. Create an account on first launch.

### 3. Set Up the Annotation Project

1. **Create project** → Name it "WaziGov Table Detection"
2. **Settings → Labeling Interface** → Switch to "Code" view → Paste the contents of `configs/labelstudio_table_detection.xml`
3. **Settings → Cloud Storage → Add Source Storage**:
   - Storage Type: **Local files**
   - Absolute local path: `<full path to>/data/images/pages`
   - Toggle **"Treat every bucket object as a source file"**
   - Click **Sync Storage**
4. The images should now appear as tasks ready for annotation.

*Alternatively*, import the pre-generated task file: **Import → Upload** `data/annotations/labelstudio/import_tasks.json`

---

## Annotation Workflow

### Stage 1: Table Detection (Full Pages)

**Goal**: Draw bounding boxes around every table on each page.

**Labels**:
| Label | Color | Description |
|-------|-------|-------------|
| `table` | Red | Standard table (upright orientation) |
| `table_rotated` | Teal | Table rotated 90° (landscape on portrait page) |

**Guidelines**:
- Draw a **tight rectangle** around the entire table, including all header rows
- **Include**: column headers, row headers, data cells, totals rows
- **Exclude**: page titles above the table, footnotes below, page numbers
- If a table continues from a previous page, still annotate the portion visible on this page as its own table
- Watermarks overlapping with the table should be *inside* the bounding box

**Target**: ~150-200 table bounding boxes across 100 annotated pages.

### Stage 2: Structure Recognition (Table Crops)

**After completing Stage 1**, convert and crop:

```bash
# Convert Label Studio export to PASCAL VOC
python scripts/convert_annotations.py --input <exported_json> --stage detection

# Crop table regions for structure annotation
python scripts/crop_tables.py
```

Then create a **second Label Studio project** for structure annotation using `configs/labelstudio_structure_recognition.xml`.

**Labels**:
| Label | Color | Description |
|-------|-------|-------------|
| `table_row` | Blue | Horizontal strip spanning the full table width for each row |
| `table_column` | Purple | Vertical strip spanning the full table height for each column |
| `table_spanning_cell` | Red | Any cell that spans multiple rows and/or columns (merged cell) |
| `table_column_header` | Yellow | Header row(s) at the top of the table |
| `table_projected_row_header` | Green | Row header column (leftmost column with category names) |

**Annotation order**:
1. Draw all **rows** first (full-width horizontal strips)
2. Draw all **columns** (full-height vertical strips)
3. Mark **spanning/merged cells**
4. Mark **header rows** (`table_column_header`)
5. Mark **row header columns** (`table_projected_row_header`)

**Target**: ~15,000-20,000 cell-level structure labels.

---

## Exporting Annotations

### Export from Label Studio
1. Go to your project → **Export**
2. Choose **JSON** format
3. Save to `data/annotations/labelstudio/`

### Convert to Training Format

```bash
# Table detection annotations
python scripts/convert_annotations.py \
    --input data/annotations/labelstudio/export_detection.json \
    --stage detection \
    --split

# Structure recognition annotations
python scripts/convert_annotations.py \
    --input data/annotations/labelstudio/export_structure.json \
    --stage structure \
    --split
```

The `--split` flag generates 70/15/15 train/val/test splits in `data/splits/`.

---

## Adding More PDFs

1. Place new PDFs in `data/pdfs/`
2. Run `python scripts/pdf_to_images.py`
3. Run `python scripts/setup_labelstudio.py` to regenerate the import file
4. Sync or re-import in Label Studio

## Quality Control

- Double-check 20% of annotated samples (as per proposal)
- Ensure consistent bounding box tightness across annotators
- Verify merged cells are marked wherever rows/columns are combined
- Check that header rows are correctly distinguished from data rows

## Data Targets

| Metric | Target |
|--------|--------|
| Annotated pages | 100 |
| Table bounding boxes | 150-200 |
| Cell-level structure labels | 15,000-20,000 |
| Train/Val/Test split | 70% / 15% / 15% |

## GRiTS Evaluation (Structure)

Use GRiTS-style metrics to compare a predicted CV handoff JSON against a ground-truth handoff JSON:

```bash
python scripts/evaluate_grits.py \
    --gt outputs/cv_handoff_gt.json \
    --pred outputs/cv_handoff_pred.json \
    --mode paper_like \
    --match-by table_id \
    --output outputs/grits_results.json
```

Reported metrics:
- `grits_top` (grid/boundary topology similarity)
- `grits_con` (slot-level content similarity)
- `grits_loc` (cell geometry similarity using bbox IoU)
- `grits` (mean of top, con, loc)

Scoring modes:
- `grits_style` (default): robust practical scoring for current handoff schema.
- `paper_like`: stricter slot-aligned scoring intended to be closer to proposal-style structure evaluation.

For detailed comparison of the two modes and recommendations on when to use each, see [docs/grits_comparison_guide.md](docs/grits_comparison_guide.md).

Generate synthetic test cases to compare modes:
```bash
python scripts/grits_comparison_demo.py
```

## Satellite Change Detection Module

The satellite prototype now lives in the sibling folder [Satellite change detection module](../Satellite%20change%20detection%20module/README.md).

## Phone Image Verification Module

The phone-image verification module lives in the sibling folder [Phone image verification module](../Phone%20image%20verification%20module/README.md).

Verifies phone images for evidence authenticity across three criteria:
- **Geolocation**: Extract GPS from EXIF and validate within site bounds
- **Authenticity & Forensics**: Check metadata integrity and basic deepfake detection
- **Scene Matching**: Compare keypoints against reference satellite/reference images

Quick smoke test:
```bash
cd ../Phone\ image\ verification\ module
python phone_image_verifier.py --smoke-test
```

Verify a batch of photos:
```bash
python phone_image_verifier.py \
    --image-dir ./photos \
    --lat-min -1.3 --lon-min 36.7 --lat-max -1.2 --lon-max 36.8 \
    --reference-image satellite_reference.jpg
```
