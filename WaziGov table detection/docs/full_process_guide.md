# WaziGov Table Detection — Complete Process Guide

> **End-to-end guide**: from raw government PDFs to detected tables with bounding boxes.  
> Project: SCT212-0147/2022 | Model: `microsoft/table-transformer-detection`

---

## Table of Contents

1. [Prerequisites & Setup](#1-prerequisites--setup)
2. [Step 1 — Collect PDF Documents](#2-step-1--collect-pdf-documents)
3. [Step 2 — Convert PDFs to Page Images](#3-step-2--convert-pdfs-to-page-images)
4. [Step 3 — Set Up Label Studio for Annotation](#4-step-3--set-up-label-studio-for-annotation)
5. [Step 4 — Annotate Tables (Stage 1 — Detection)](#5-step-4--annotate-tables-stage-1--detection)
6. [Step 5 — Export & Convert Annotations](#6-step-5--export--convert-annotations)
7. [Step 6 — Evaluate Pretrained Model (Baseline)](#7-step-6--evaluate-pretrained-model-baseline)
8. [Step 7 — Fine-Tune on Your Data](#8-step-7--fine-tune-on-your-data)
9. [Step 8 — Evaluate Fine-Tuned Model](#9-step-8--evaluate-fine-tuned-model)
10. [Step 9 — Run Inference on New Documents](#10-step-9--run-inference-on-new-documents)
11. [Step 10 — Stage 2: Structure Recognition (Rows/Columns/Cells)](#11-step-10--stage-2-structure-recognition-rowscolumnscells)
12. [Folder Structure Reference](#12-folder-structure-reference)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites & Setup

### 1.1 System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.10+ | 3.10.11 |
| RAM | 8 GB | 16 GB |
| GPU | Not required (CPU works) | NVIDIA GPU with CUDA |
| Disk | 5 GB | 20 GB (for images + models) |

### 1.2 Clone / Open the Project

Open the project folder in VS Code:

```
WaziGov table detection/
```

### 1.3 Create Virtual Environment & Install Dependencies

```powershell
# Create virtual environment
python -m venv .venv

# Activate it (PowerShell)
.\.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt

# Also install timm (required by Table Transformer's ResNet backbone)
pip install timm
```

**Contents of `requirements.txt`:**
- `PyMuPDF` — PDF processing
- `Pillow` — Image processing
- `torch`, `torchvision` — Deep learning framework
- `transformers` — HuggingFace (loads Table Transformer)
- `label-studio` — Annotation tool
- `tqdm` — Progress bars

---

## 2. Step 1 — Collect PDF Documents

### What You Need

Kenyan government financial PDFs containing tables. Sources:

| Source | URL |
|---|---|
| Controller of Budget | https://cob.go.ke/reports/ |
| National Treasury | https://www.treasury.go.ke/ |
| County Government portals | e.g., Nairobi, Migori, Kisumu |
| Parliament Budget Office | https://www.parliament.go.ke/ |

### Where to Put Them

Place all PDF files in:

```
data/pdfs/
```

**Target**: At least 100 pages across multiple PDFs for robust training.

### Example

```
data/pdfs/
├── COUNTY-GOVERNMENTS-BUDGET-IMPLEMENTATION-REVIEW-REPORT-FY-2024.2025.pdf
├── nairobi-revenue-report-2023.pdf
├── national-budget-estimates-2024.pdf
└── ...
```

---

## 3. Step 2 — Convert PDFs to Page Images

Each PDF page becomes a high-resolution PNG image (300 DPI) that both Label Studio and the model consume.

### Run the Conversion

```powershell
# Convert ALL PDFs in data/pdfs/
python scripts/pdf_to_images.py

# Or convert a single PDF
python scripts/pdf_to_images.py --input data/pdfs/YOUR_FILE.pdf

# Custom DPI (default is 300)
python scripts/pdf_to_images.py --dpi 300

# Convert specific pages only (e.g., pages 3-8)
python scripts/pdf_to_images.py --input data/pdfs/YOUR_FILE.pdf --pages 3 8
```

### Output

Images are saved to:

```
data/images/pages/
├── COUNTY-GOVERNMENTS-BUDGET_page_01.png
├── COUNTY-GOVERNMENTS-BUDGET_page_02.png
├── ...
```

Each image will be approximately **6888 × 9742 px** at 300 DPI for A4-sized pages.

### Verify

Open a few output images to confirm they look correct — sharp text, full page visible.

---

## 4. Step 3 — Set Up Label Studio for Annotation

### 4.1 Generate Import Tasks

This creates a JSON file that tells Label Studio about your images:

```powershell
python scripts/setup_labelstudio.py
```

Output: `data/annotations/labelstudio/import_tasks.json`

### 4.2 Start Label Studio

```powershell
label-studio start
```

This opens Label Studio in your browser at **http://localhost:8080**.

### 4.3 Create a New Project

1. Click **"Create"** in Label Studio
2. Name it: **`WaziGov Table Detection`**
3. Skip the data import for now

### 4.4 Configure the Labeling Interface

1. Go to **Settings → Labeling Interface**
2. Switch to **"Code"** tab
3. Paste the contents of `configs/labelstudio_table_detection.xml`:

```xml
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="table" background="red"/>
    <Label value="table_rotated" background="teal"/>
  </RectangleLabels>
</View>
```

4. Click **Save**

### 4.5 Set Up Local File Storage

1. Go to **Settings → Cloud Storage → Add Source Storage**
2. Storage Type: **Local files**
3. Absolute local path: the full path to your images folder, e.g.:
   ```
   C:\Users\joeki\Documents\Notes\4th YEAR PROJECT\WaziGov table detection\data\images\pages
   ```
4. Toggle **"Treat every bucket object as a source file"** ON
5. Click **Add Storage**, then **Sync Storage**

### 4.6 Import Tasks

1. Go to your project's main page
2. Click **Import**
3. Upload `data/annotations/labelstudio/import_tasks.json`
4. Your images should appear as tasks

---

## 5. Step 4 — Annotate Tables (Stage 1 — Detection)

### What to Annotate

Draw **bounding boxes** around every table on each page.

### Annotation Rules

| Rule | Details |
|---|---|
| **Label** | Use `table` for normal tables, `table_rotated` for rotated/landscape tables |
| **Bounding box** | Draw a tight rectangle around the table body |
| **Include** | All data rows, column headers that are part of the table grid |
| **Exclude** | Table titles/captions above the table, footnotes below, page headers/footers |
| **Multiple tables** | If a page has 2+ tables, draw a separate box for each |
| **No tables** | If a page has no tables, skip it (click Submit with no annotations) |
| **Tight fit** | The box should hug the table borders closely — don't leave large margins |
| **Multi-page tables** | Annotate the portion visible on each page separately |

### Visual Example

```
┌─────────────────────────────────┐
│  PAGE HEADER                    │  ← DO NOT include
│                                 │
│  Table 4.1: Revenue Summary     │  ← DO NOT include (title)
│  ┌───────────────────────────┐  │
│  │ County  │ Budget │ Actual │  │  ← START of bounding box
│  │─────────│────────│────────│  │
│  │ Nairobi │ 50,000 │ 45,200│  │
│  │ Mombasa │ 30,000 │ 28,100│  │
│  │ Kisumu  │ 20,000 │ 18,900│  │
│  └───────────────────────────┘  │  ← END of bounding box
│                                 │
│  Source: National Treasury       │  ← DO NOT include (footnote)
│  PAGE 12                        │  ← DO NOT include
└─────────────────────────────────┘
```

### Workflow

1. Open each task in Label Studio
2. Select the **`table`** label (or `table_rotated`)
3. Click and drag to draw a rectangle around each table
4. Click **Submit** to save and move to the next page
5. Repeat for all pages

### Tips

- Use keyboard shortcuts: press `1` for `table`, `2` for `table_rotated`
- Zoom in with scroll wheel to get precise boundaries
- If you make a mistake, click the annotation and press **Delete**
- Pages with no tables: just click **Submit** with no annotations

---

## 6. Step 5 — Export & Convert Annotations

### 6.1 Export from Label Studio

1. Go to your project in Label Studio
2. Click **Export**
3. Select format: **JSON** ← Important: use JSON, not COCO or any other format
4. Download the file
5. Save it to: `data/annotations/labelstudio/export.json`

### 6.2 Convert to PASCAL VOC XML (PubTables-1M Format)

The model expects annotations in PASCAL VOC format. This script converts the Label Studio JSON:

```powershell
python scripts/convert_annotations.py --input data/annotations/labelstudio/export.json --images-dir data/images/pages/ --output-dir data/annotations/pascal_voc/ --stage detection
```

### What It Does

For each annotated page, it creates an XML file like:

```xml
<annotation>
  <filename>COUNTY-GOVERNMENTS-BUDGET_page_03.png</filename>
  <size>
    <width>6888</width>
    <height>9742</height>
    <depth>3</depth>
  </size>
  <object>
    <name>table</name>
    <bndbox>
      <xmin>412</xmin>
      <ymin>1530</ymin>
      <xmax>6476</xmax>
      <ymax>8210</ymax>
    </bndbox>
  </object>
</annotation>
```

### Verify

Check that XML files exist in `data/annotations/pascal_voc/`:

```powershell
Get-ChildItem data/annotations/pascal_voc/ -Filter *.xml | Measure-Object
```

You should see one XML per annotated page (pages with no tables are skipped).

---

## 7. Step 6 — Evaluate Pretrained Model (Baseline)

Before fine-tuning, evaluate the pretrained model on your annotated data to establish a baseline.

### Run Evaluation

```powershell
python scripts/evaluate.py --model microsoft/table-transformer-detection --data-dir data/
```

### What It Does

1. Loads the pretrained `microsoft/table-transformer-detection` model
2. Runs detection on each annotated page image
3. Compares predicted bounding boxes against your ground truth annotations
4. Computes precision, recall, and F1 score at IoU ≥ 0.5

### Output

Results saved to `outputs/evaluation_results.json`.

Console output example:

```
OVERALL RESULTS (IoU threshold: 0.5)
============================================================
  Total GT tables:   14
  Total predictions: 13
  True positives:    13
  False positives:   0
  False negatives:   1
  Precision:         1.0000
  Recall:            0.9286
  F1 Score:          0.9630
```

### Interpret Results

| Metric | Meaning |
|---|---|
| **Precision** | Of all tables the model predicted, what % were real tables? |
| **Recall** | Of all real tables, what % did the model find? |
| **F1** | Harmonic mean of precision and recall (balanced score) |
| **TP** | Correctly detected tables |
| **FP** | False alarms (predicted a table where there wasn't one) |
| **FN** | Missed tables (real table the model didn't find) |

**If F1 ≥ 0.95**: The pretrained model already works well; fine-tuning will polish edge cases.  
**If F1 < 0.80**: Significant fine-tuning needed; collect more annotations.

---

## 8. Step 7 — Fine-Tune on Your Data

### When to Fine-Tune

- You have **≥ 20 annotated pages** (more is better; target 100+)
- The pretrained model misses certain table layouts common in your documents
- You want to improve recall on specific document types

### Run Training

```powershell
# Basic training (recommended for small datasets)
python scripts/train_table_detection.py --data-dir data/ --epochs 50 --batch-size 2 --freeze-backbone

# Full training (if you have ≥ 100 annotated pages)
python scripts/train_table_detection.py --data-dir data/ --epochs 100 --batch-size 4

# Custom learning rate
python scripts/train_table_detection.py --data-dir data/ --epochs 50 --batch-size 2 --learning-rate 5e-5 --freeze-backbone
```

### CLI Options

| Flag | Default | Description |
|---|---|---|
| `--data-dir` | `data/` | Root data directory |
| `--output-dir` | `models/table_detection/` | Where to save the trained model |
| `--model-name` | `microsoft/table-transformer-detection` | Base pretrained model |
| `--epochs` | `50` | Number of training epochs |
| `--batch-size` | `2` | Batch size (lower = less VRAM needed) |
| `--learning-rate` | `5e-5` | Learning rate |
| `--weight-decay` | `0.01` | Weight decay (regularisation) |
| `--val-ratio` | `0.2` | Fraction of data used for validation |
| `--freeze-backbone` | off | Freeze ResNet-18 backbone (use for small datasets) |
| `--num-workers` | `0` | DataLoader workers (keep 0 on Windows) |

### What Happens Internally

1. **Data split**: 80% train / 20% validation (configurable with `--val-ratio`)
2. **Image preprocessing**: Resize, normalize, pad to uniform size via `DetrImageProcessor`
3. **Frozen backbone** (if `--freeze-backbone`): Only the transformer head is trained initially
4. **Loss function**: DETR's Hungarian matching loss (classification + box regression + GIoU)
5. **Checkpoints**: Saved every 10 epochs to `models/table_detection/`
6. **Final model**: Saved to `models/table_detection/final_model/`

### Training Duration Estimates

| Data Size | GPU | Estimated Time |
|---|---|---|
| 20 pages, 50 epochs | CPU | ~2-4 hours |
| 20 pages, 50 epochs | NVIDIA GPU | ~15-30 min |
| 100 pages, 100 epochs | CPU | ~12-20 hours |
| 100 pages, 100 epochs | NVIDIA GPU | ~1-2 hours |

---

## 9. Step 8 — Evaluate Fine-Tuned Model

After training, evaluate the fine-tuned model to measure improvement:

```powershell
python scripts/evaluate.py --model models/table_detection/final_model --data-dir data/
```

### Compare With Baseline

| Metric | Pretrained (Baseline) | Fine-Tuned |
|---|---|---|
| Precision | 1.000 | ? |
| Recall | 0.929 | ? |
| F1 | 0.963 | ? |

You should see an improvement, especially in recall (fewer missed tables).

---

## 10. Step 9 — Run Inference on New Documents

### On a Single Image

```powershell
python scripts/inference.py --image path/to/page.png
```

### On a Folder of Images

```powershell
python scripts/inference.py --image-dir data/images/pages/
```

### On a PDF (Converts + Detects automatically)

```powershell
python scripts/inference.py --pdf path/to/document.pdf
```

### Using the Pretrained Model (Skip Fine-Tuning)

```powershell
python scripts/inference.py --pdf path/to/document.pdf --model microsoft/table-transformer-detection
```

### Using the Fine-Tuned Model

```powershell
python scripts/inference.py --pdf path/to/document.pdf --model models/table_detection/final_model
```

### Adjusting Confidence Threshold

```powershell
# Lower threshold = more detections (may include false positives)
python scripts/inference.py --pdf path/to/document.pdf --threshold 0.3

# Higher threshold = fewer detections (higher confidence only)
python scripts/inference.py --pdf path/to/document.pdf --threshold 0.8
```

### CLI Options

| Flag | Default | Description |
|---|---|---|
| `--image` | — | Path to a single image |
| `--image-dir` | — | Path to a folder of images |
| `--pdf` | — | Path to a PDF file |
| `--model` | `models/table_detection/final_model` | Model path or HuggingFace name |
| `--output-dir` | `outputs/detections/` | Where to save results |
| `--threshold` | `0.5` | Detection confidence threshold |

### Output

For each processed image, you get:

1. **Annotated image** — original image with coloured bounding boxes overlaid  
   → saved to `outputs/detections/<image_name>_detected.png`

2. **JSON results** — machine-readable detection data  
   → saved to `outputs/detections/<image_name>_detections.json`

Example JSON output:
```json
[
  {
    "label": "table",
    "score": 0.998,
    "bbox": {
      "xmin": 412,
      "ymin": 1530,
      "xmax": 6476,
      "ymax": 8210
    }
  }
]
```

---

## 11. Step 10 — Stage 2: Structure Recognition (Rows/Columns/Cells)

> **Note**: This is the next phase after table detection is working well.

Stage 2 identifies the internal structure of each detected table — rows, columns, headers, and cells.

### 10.1 Crop Detected Tables

First, extract individual table images from the annotated pages:

```powershell
python scripts/crop_tables.py
```

Or with explicit paths:

```powershell
python scripts/crop_tables.py --annotations data/annotations/pascal_voc/ --images data/images/pages/ --output data/images/table_crops/
```

Output: individual table images in `data/images/table_crops/`

### 10.2 Set Up a New Label Studio Project for Structure

1. Create a new project in Label Studio: **`WaziGov Structure Recognition`**
2. In **Settings → Labeling Interface → Code**, paste `configs/labelstudio_structure_recognition.xml`:

```xml
<View>
  <Image name="image" value="$image"/>
  <RectangleLabels name="label" toName="image">
    <Label value="table_row" background="#FF6B6B"/>
    <Label value="table_column" background="#4ECDC4"/>
    <Label value="table_spanning_cell" background="#45B7D1"/>
    <Label value="table_projected_row_header" background="#FFA07A"/>
    <Label value="table_column_header" background="#98D8C8"/>
  </RectangleLabels>
</View>
```

3. Set up Local Storage pointing to `data/images/table_crops/`
4. Generate new import tasks for the crops (update `setup_labelstudio.py --images-dir data/images/table_crops`)

### 10.3 Annotate Structure

For each cropped table image, draw bounding boxes for:

| Label | What to Annotate |
|---|---|
| `table_row` | Each horizontal row |
| `table_column` | Each vertical column |
| `table_column_header` | Header row(s) at the top |
| `table_spanning_cell` | Any cell that spans multiple columns or rows |
| `table_projected_row_header` | Row labels on the left side (hierarchical headers) |

### 10.4 Export & Convert

Same process as Stage 1:

```powershell
# Export from Label Studio as JSON
# Then convert:
python scripts/convert_annotations.py --input data/annotations/labelstudio/structure_export.json --images-dir data/images/table_crops/ --output-dir data/annotations/pascal_voc_structure/ --stage structure
```

### 10.5 Use Structure Recognition Model

Microsoft also provides `microsoft/table-transformer-structure-recognition` for this stage.  
Fine-tuning and inference follow the same pattern as the detection model.

---

## 12. Folder Structure Reference

After completing all steps, your project will look like this:

```
WaziGov table detection/
│
├── .venv/                                  # Python virtual environment
├── requirements.txt                        # Dependencies
├── README.md                               # Project overview
├── .gitignore                              # Git ignore rules
│
├── configs/
│   ├── labelstudio_table_detection.xml     # Stage 1 annotation config
│   └── labelstudio_structure_recognition.xml # Stage 2 annotation config
│
├── scripts/
│   ├── pdf_to_images.py                    # Step 2: PDF → 300 DPI images
│   ├── setup_labelstudio.py                # Step 3: Generate Label Studio tasks
│   ├── convert_annotations.py              # Step 5: Label Studio JSON → PASCAL VOC XML
│   ├── crop_tables.py                      # Step 10: Crop tables for Stage 2
│   ├── train_table_detection.py            # Step 7: Fine-tune Table Transformer
│   ├── evaluate.py                         # Steps 6 & 8: Compute metrics
│   └── inference.py                        # Step 9: Run detection on new docs
│
├── data/
│   ├── pdfs/                               # Raw government PDF documents
│   ├── images/
│   │   ├── pages/                          # Full page images (300 DPI PNGs)
│   │   └── table_crops/                    # Cropped table images (Stage 2)
│   ├── annotations/
│   │   ├── labelstudio/                    # Label Studio exports (JSON)
│   │   ├── pascal_voc/                     # Converted annotations (XML)
│   │   └── pubtables1m/                    # Alternative annotation location
│   └── splits/                             # Train/val splits
│
├── models/
│   └── table_detection/
│       ├── checkpoint-*/                   # Training checkpoints
│       └── final_model/                    # Final fine-tuned model
│
├── outputs/
│   ├── detections/                         # Inference results (images + JSON)
│   ├── evaluation_results.json             # Evaluation metrics
│   └── sample_cv_output.json              # Sample output for NLP integration
│
└── docs/
    ├── pipeline_and_nlp_integration.md     # Pipeline docs for NLP teammate
    └── full_process_guide.md               # This file
```

---

## 13. Troubleshooting

### Common Issues

| Problem | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'timm'` | Missing dependency | `pip install timm` |
| `IndexError` in `convert_annotations.py` | Pages with no annotations | Already fixed — script skips them |
| PowerShell `^` error | Using CMD syntax in PowerShell | Use backtick `` ` `` or put command on one line |
| Label Studio images not loading | Local storage path wrong | Check absolute path in Cloud Storage settings |
| `CUDA out of memory` during training | Batch size too large | Reduce `--batch-size` to 1 |
| Poor recall after fine-tuning | Too few annotations | Annotate more pages (target 100+) |
| Fine-tuned model not found | Model not yet trained | Script auto-falls back to pretrained model |
| Slow training on CPU | No GPU available | Use `--freeze-backbone` and lower `--epochs` |

### Quick Health Check

Run these commands to verify everything is set up:

```powershell
# 1. Check Python and venv
python --version
# → Python 3.10.11

# 2. Check key packages
python -c "import torch; print(f'PyTorch {torch.__version__}, CUDA: {torch.cuda.is_available()}')"
python -c "import transformers; print(f'Transformers {transformers.__version__}')"
python -c "import fitz; print(f'PyMuPDF {fitz.version}')"

# 3. Check data
Get-ChildItem data/pdfs/ -Filter *.pdf | Measure-Object
Get-ChildItem data/images/pages/ -Filter *.png | Measure-Object
Get-ChildItem data/annotations/pascal_voc/ -Filter *.xml | Measure-Object

# 4. Quick pretrained model test (detects tables on first page)
python scripts/inference.py --image data/images/pages/ --model microsoft/table-transformer-detection --threshold 0.5
```

---

## Quick Reference — Command Cheat Sheet

```powershell
# ── SETUP ──────────────────────────────────────────────────
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install timm

# ── STEP 2: PDF → IMAGES ──────────────────────────────────
python scripts/pdf_to_images.py

# ── STEP 3: GENERATE LABEL STUDIO TASKS ───────────────────
python scripts/setup_labelstudio.py
label-studio start

# ── STEP 5: CONVERT ANNOTATIONS ───────────────────────────
python scripts/convert_annotations.py --input data/annotations/labelstudio/export.json --images-dir data/images/pages/ --output-dir data/annotations/pascal_voc/ --stage detection

# ── STEP 6: EVALUATE PRETRAINED (BASELINE) ────────────────
python scripts/evaluate.py --model microsoft/table-transformer-detection --data-dir data/

# ── STEP 7: FINE-TUNE ─────────────────────────────────────
python scripts/train_table_detection.py --data-dir data/ --epochs 50 --batch-size 2 --freeze-backbone

# ── STEP 8: EVALUATE FINE-TUNED ───────────────────────────
python scripts/evaluate.py --model models/table_detection/final_model --data-dir data/

# ── STEP 9: INFERENCE ─────────────────────────────────────
python scripts/inference.py --pdf path/to/document.pdf
python scripts/inference.py --image-dir data/images/pages/

# ── STEP 10: CROP TABLES FOR STAGE 2 ─────────────────────
python scripts/crop_tables.py
```

---

*Last updated: March 2026 | WaziGov CV Module | JKUAT BSc CT Final Year Project*
