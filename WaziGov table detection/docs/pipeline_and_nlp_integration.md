# WaziGov CV Module — Pipeline Architecture & NLP Integration Guide

## 1. HOW THE PIPELINE WORKS

The CV module is a **5-stage sequential pipeline** that converts a raw government PDF into structured JSON with cell-level data.

```
 ┌─────────────┐     ┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌──────────────┐
 │  STAGE 1    │     │   STAGE 2    │     │    STAGE 3       │     │    STAGE 4        │     │   STAGE 5    │
 │ Preprocess  │────▶│   Table      │────▶│   Structure      │────▶│  Post-Processing  │────▶│  JSON Output │
 │ PDF → Image │     │  Detection   │     │  Recognition     │     │  & Validation     │     │  (for NLP)   │
 └─────────────┘     └──────────────┘     └──────────────────┘     └───────────────────┘     └──────────────┘
     300 DPI             DETR model            DETR model           Merged cells,              Structured
   page images        finds table bbox      finds rows/cols        headers, multi-page       cell-level JSON
```

### Stage 1: Document Preprocessing
- **Input**: Raw PDF file
- **Process**: Convert each page to a 300 DPI RGB image using PyMuPDF
- **Output**: List of PIL Image objects (one per page)
- **Script**: `scripts/pdf_to_images.py`

### Stage 2: Table Detection
- **Input**: Full-page image (e.g., 6888 × 9742 px at 300 DPI)
- **Process**: The Table Transformer detection model scans the entire page and predicts bounding boxes around every table
- **Output**: List of bounding boxes `[xmin, ymin, xmax, ymax]` with confidence scores
- **Script**: `scripts/inference.py`
- **Current performance**: F1 = 0.963 (pretrained, no fine-tuning)

### Stage 3: Structure Recognition (TODO)
- **Input**: Cropped table image (one per detected table)
- **Process**: A second Table Transformer model predicts rows, columns, spanning cells, and header regions within the table
- **Output**: Raw grid structure `G(R, C, S)` — rows, columns, spanning cells

### Stage 4: Post-Processing (TODO)
Three parallel algorithms:
1. **Merged Cell Resolver** — resolves overlapping spanning cell predictions
2. **Hierarchical Header Detector** — assigns depth levels (1-5) to header cells based on text indentation
3. **Multi-Page Continuity Stitcher** — detects when a table continues across pages using column-width cosine similarity

### Stage 5: JSON Serialisation (TODO)
- Assembles validated cells into the output JSON schema
- Extracts cell images as base64-encoded PNGs
- Extracts raw text using PyMuPDF (digital) or EasyOCR (scanned)
- Runs arithmetic validation (column sums, row totals)

---

## 2. HOW TABLE TRANSFORMER WORKS

### Architecture: DETR (DEtection TRansformer)

The Table Transformer is built on Facebook's DETR architecture. It works fundamentally differently from traditional object detectors — it treats detection as a **set prediction problem**.

```
 INPUT IMAGE                    CNN BACKBONE                TRANSFORMER                 OUTPUT
 ┌──────────┐    ┌─────────────────────────┐    ┌──────────────────────────┐    ┌──────────────┐
 │          │    │      ResNet-18          │    │  Encoder (6 layers)      │    │ Object 1:    │
 │  Page    │───▶│  Extracts visual        │───▶│  Self-attention across   │───▶│  class: table │
 │  Image   │    │  features from image    │    │  ALL image regions       │    │  bbox: [x,y, │
 │ H×W×3    │    │  Output: feature map    │    │                          │    │    w,h]      │
 │          │    │  C × H/32 × W/32       │    │  Decoder (6 layers)      │    │  score: 0.98 │
 │          │    │                         │    │  100 learnable queries   │    │              │
 │          │    │  + 1×1 conv → 256 dim   │    │  each "looks for" a     │    │ Object 2:    │
 │          │    │  + positional encoding  │    │  potential table         │    │  class: table │
 │          │    │                         │    │  via cross-attention     │    │  bbox: [...]  │
 └──────────┘    └─────────────────────────┘    └──────────────────────────┘    └──────────────┘
```

### Key concepts:

**1. CNN Backbone (ResNet-18)**
Converts the image into a grid of feature vectors. A 6888×9742 image becomes roughly a 215×304 grid of 2048-dimensional feature vectors, then projected to 256 dimensions.

**2. Transformer Encoder (6 layers, 8 attention heads)**
Each feature vector attends to ALL other feature vectors via self-attention. This is why it works well for tables — it can understand that a header row at the top of the page belongs to the same table as data rows 5000 pixels below.

**3. Transformer Decoder + Object Queries**
100 learnable query vectors (think of them as "table detectors") each attend to the encoder output. Each query learns to specialise in detecting tables in different positions/sizes. Most queries output "no object" — only the ones that find a table produce a prediction.

**4. Bipartite Matching Loss (Hungarian Algorithm)**
During training, predicted tables are matched 1-to-1 with ground truth tables using the Hungarian algorithm. This eliminates the need for Non-Maximum Suppression (NMS) — the model inherently avoids duplicate predictions.

### Two models, same architecture:

| Model | Input | Predicts | HuggingFace ID |
|-------|-------|----------|----------------|
| **Detection** | Full page image | Table bounding boxes | `microsoft/table-transformer-detection` |
| **Structure** | Cropped table image | Rows, columns, headers, spanning cells | `microsoft/table-transformer-structure-recognition` |

### Why it works well for government documents:
- **No anchors needed** — handles tables at any size/position
- **Self-attention** — captures long-range dependencies (large multi-page tables)
- **Pretrained on 947K tables** — strong starting point, fine-tune with as few as 50-100 domain examples

---

## 3. OUTPUT FORMAT FOR NLP INTEGRATION

### Schema Overview

The CV module produces **one JSON file per PDF document**. The NLP module consumes this JSON — it never needs to touch the original PDF.

```
{
  "document_id": string,          // Unique hash of PDF + timestamp
  "source_file": string,          // Original PDF filename
  "page_count": int,              // Total pages in document
  "processed_at": string,         // ISO 8601 timestamp
  "model_version": string,        // Which model produced this
  "tables": [                     // Array of ALL tables in the document
    {
      "table_id": string,         // "page_003_table_00"
      "page_number": int,         // 1-indexed page number
      "bbox": {xmin, ymin, xmax, ymax},  // Pixel coordinates on page
      "confidence": float,        // 0.0 - 1.0
      "label": string,            // "table" or "table_rotated"
      "grid": {rows, cols},       // Grid dimensions
      "continuation": {...},      // Multi-page linking info
      "cells": [...],             // Array of Cell objects (see below)
      "validation": {...}         // Arithmetic check results
    }
  ]
}
```

### Cell Object — what the NLP module receives per cell:

```
{
  "cell_id": "page_003_table_00_r2_c1",   // Unique, deterministic ID
  "row_idx": 2,                            // 0-based row position
  "col_idx": 1,                            // 0-based column position
  "row_span": 1,                           // 1 = normal, >1 = merged vertically
  "col_span": 1,                           // 1 = normal, >1 = merged horizontally
  "cell_type": "data",                     // "column_header" | "header" | "data"
  "hierarchy_level": 2,                    // null for data cells, 1-5 for headers
  "bbox": {xmin, ymin, xmax, ymax},        // Pixel coordinates within page
  "raw_text": "Property Rates",            // Text extracted by CV module (for reference)
  "image_b64": "/9j/4AAQSkZ...",           // Base64-encoded PNG of this cell at 300 DPI
  "confidence": 0.94                       // How confident the model is about this cell's boundary
}
```

### What each field means for the NLP module:

| Field | NLP Usage |
|-------|-----------|
| `cell_id` | Unique key — use this to reference specific cells |
| `row_idx` / `col_idx` | Reconstruct the table grid: cells at row 0 are headers, row N are data |
| `row_span` / `col_span` | If >1, this cell is merged across multiple rows/columns |
| `cell_type` | `"column_header"` = column name, `"header"` = section header (e.g., "A. County Own Revenue"), `"data"` = regular cell |
| `hierarchy_level` | 1 = top-level category (e.g., "Development Budget"), 5 = most nested. Used to build parent-child relationships between budget items |
| `raw_text` | **Reference only** — the NLP module should do its own extraction from `image_b64` for accuracy |
| `image_b64` | **Primary input for NLP** — decode to get a crisp 300 DPI image of exactly this cell. Feed to LayoutLMv3 or OCR |
| `confidence` | Filter out low-confidence cells (< 0.7) or flag for manual review |

### How to read `image_b64` in Python:

```python
import base64
from io import BytesIO
from PIL import Image

cell_image = Image.open(BytesIO(base64.b64decode(cell["image_b64"])))
# cell_image is now a PIL Image of just this one cell at 300 DPI
```

### Multi-page table linking:

```python
# Find all parts of a multi-page table
for table in data["tables"]:
    if table["continuation"]["is_continuation"]:
        parent_id = table["continuation"]["continues_from"]
        # Merge this table's cells with the parent table
        # Skip repeated header rows (row_idx 0 if cell_type == "column_header")
```

### Sample template file:
See `outputs/sample_cv_output.json` for a complete working example with realistic data from your Migori County revenue table.

---

## 4. CURRENT STATUS & WHAT REMAINS

| Component | Status | Notes |
|-----------|--------|-------|
| PDF → Images | ✅ Done | 300 DPI conversion working |
| Table Detection Annotation | ✅ Done | 14 tables annotated via Label Studio |
| Table Detection Model | ✅ Working | Pretrained model: F1 = 0.963 |
| Table Detection Fine-tuning | ⬜ Optional | Only needed if pretrained drops on edge cases |
| Structure Recognition | ⬜ TODO | Need Stage 2 annotation + inference script |
| Post-Processing | ⬜ TODO | Merged cells, headers, multi-page stitching |
| Full JSON Output Pipeline | ⬜ TODO | Assembling all stages into final output |
| More document annotation | ⬜ In progress | Need 100+ pages for robust evaluation |
