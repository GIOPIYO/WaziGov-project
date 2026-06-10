# CV to NLP Integration Workflow

## Purpose
This guide defines what CV exports, what NLP consumes, and the minimum QA gate before handoff.

## 1. Generate CV Handoff
Run inference on a PDF with structure enabled:

```powershell
python scripts/inference.py \
  --pdf data/pdfs/YOUR_FILE.pdf \
  --output-dir outputs/detections \
  --cv-output outputs/cv_handoff.json
```

## 2. Validate Handoff Quality
Run the QA checker:

```powershell
python scripts/qa_handoff.py --input outputs/cv_handoff.json --output outputs/cv_handoff_qa.json
```

Minimum pass criteria:
- No `errors`
- `ready_for_nlp = true`
- Empty text ratio under 40%

## 3. Required Fields for NLP
At document level:
- `document_id`
- `source_file`
- `page_count`
- `processed_at`
- `model_version`
- `tables[]`

At table level:
- `table_id`, `page_number`, `bbox`, `confidence`, `label`
- `grid` (`rows`, `cols`)
- `continuation` (`is_continuation`, `continues_from`, `continues_on_next_page`, `linked_table_id`, `match_score`)
- `cells[]`
- `validation`

At cell level:
- `cell_id`, `row_idx`, `col_idx`, `row_span`, `col_span`
- `cell_type`, `hierarchy_level`
- `bbox`
- `raw_text`
- `text_source` (`pdf_text`, `ocr`, `none`)
- `image_b64`
- `confidence`

## 4. Integration Contract Notes
- NLP should treat `image_b64` as primary input for extraction/interpretation.
- `raw_text` is a reference signal; quality depends on PDF text layer and OCR fallback.
- If `text_source = none`, NLP should use `image_b64` only.
- Use continuation metadata to merge multi-page tables before downstream aggregation.

## 5. What CV Needs From NLP Team
- Confidence threshold policy (drop, keep, or flag low-confidence cells).
- Merge policy for continuation tables (automatic vs human review).
- Whether OCR-derived text is acceptable in production or only as fallback.
- Preferred output granularity (document-level only or document + per-table views).

## 6. Known Pending Item
- Table geometry stabilization for challenging layouts is deferred and should be revisited.
