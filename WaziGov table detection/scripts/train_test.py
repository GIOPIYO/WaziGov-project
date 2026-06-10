"""
WaziGov train_test.py
=====================
Fine-tune Table Transformer and extract clean County Government info.
Targets: County Names, Budgets, Projects, and OAG Recommendations.

Usage:
    python scripts/train_test.py --train --pdf data/pdfs/report.pdf
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import torch
from PIL import Image
from transformers import DetrImageProcessor, TableTransformerForObjectDetection

# Import domain logic from your existing scripts
import importlib.util

def load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not (spec and spec.loader): return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def strip_unnecessary_data(data):
    """Recursively removes technical CV metadata (bboxes, images, scores)."""
    if isinstance(data, list):
        return [strip_unnecessary_data(item) for item in data]
    if isinstance(data, dict):
        to_remove = {"bbox", "image_b64", "confidence", "_profile", "match_score", "linked_table_id"}
        return {k: strip_unnecessary_data(v) for k, v in data.items() if k not in to_remove}
    return data

def run_training(args, project_root):
    """Triggers the fine-tuning process for the detection model."""
    train_script_path = project_root / "scripts" / "train_table_detection.py"
    train_mod = load_module_from_path("wazi_train", train_script_path)
    
    if not train_mod:
        print("Error: Could not find train_table_detection.py")
        return

    print("Starting Fine-tuning phase...")
    # We repurpose the logic from your training script
    train_mod.train(args)

def run_extraction(pdf_path, model_path, project_root):
    """Runs inference and extracts structured county transparency data."""
    inference_path = project_root / "scripts" / "inference.py"
    extractor_path = project_root.parent / "wazi-ui" / "scripts" / "generate_projects_from_cob_oag.py"
    
    inference = load_module_from_path("wazi_inference", inference_path)
    extractor = load_module_from_path("wazi_extractor", extractor_path)

    if not (inference and extractor):
        print("Error: Missing inference or extractor modules.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, processor = inference.load_model(str(model_path), device)
    
    # Load structure model for cell-level data
    struct_model_name = "microsoft/table-transformer-structure-recognition"
    s_model, s_processor = inference.load_structure_model(struct_model_name, device)

    print(f"Running extraction on: {pdf_path.name}")
    
    # Run detection + structure recognition
    # We use a temp directory for the handoff
    temp_out = project_root / "outputs" / "temp_train_test"
    temp_out.mkdir(parents=True, exist_ok=True)
    cv_json = temp_out / "handoff.json"

    inference.process_pdf(
        pdf_path=pdf_path,
        model=model,
        processor=processor,
        device=device,
        output_dir=str(temp_out),
        threshold=0.5,
        model_version="fine_tuned_wazigov",
        cv_output_path=cv_json,
        structure_model=s_model,
        structure_processor=s_processor,
        use_pdf_table_finder=True
    )

    with open(cv_json, "r", encoding="utf-8") as f:
        handoff_data = json.load(f)

    # Wrap in expected bundle format for the extractor.
    # We include the report under the standard OAG ID so the specialized extractor logic 
    # identifies it as a source of county data during this test run.
    report_entry = {
        "report_id": pdf_path.stem,
        "title": pdf_path.stem,
        "document": handoff_data
    }

    bundle = {
        "fiscal_year": "2023-2024",
        "reports": [
            {**report_entry, "report_id": "Auditor-Generals-summary-Report-on-County-Governments-2023-2024"}
        ]
    }

    print("Filtering for County Accountability Data (Budgets/Projects/OAG Opinions)...")
    structured_data = extractor.extract_all_projects(bundle)
    
    # Clean up unnecessary CV parameters
    clean_data = strip_unnecessary_data(structured_data)
    
    return clean_data

def main():
    parser = argparse.ArgumentParser(description="WaziGov Train & Extract County Info")
    parser.add_argument("--train", action="store_true", help="Run the fine-tuning loop")
    parser.add_argument("--pdf", type=str, help="PDF path to test extraction on")
    parser.add_argument("--data-dir", type=str, default="data/", help="Training data dir")
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--lr", type=float, default=5e-5)
    
    args = parser.parse_args()

    if not args.train and not args.pdf:
        print("\n[WaziGov] No action specified.")
        print("Use --train to fine-tune the model or --pdf <path> to test extraction.")
        parser.print_help()
        return

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    
    # 1. Training Phase
    model_path = project_root / "models" / "table_detection" / "final_model"
    if args.train:
        # Map args to what train_table_detection expects
        train_args = argparse.Namespace(
            data_dir=args.data_dir,
            images_dir=None,
            annotations_dir=None,
            split_dir=None,
            output_dir=project_root / "models" / "table_detection",
            model_name="microsoft/table-transformer-detection",
            epochs=args.epochs,
            batch_size=args.batch_size,
            learning_rate=args.lr,
            weight_decay=0.01,
            val_ratio=0.2,
            freeze_backbone=True,
            num_workers=0,
            use_random_split=True
        )
        run_training(train_args, project_root)
    
    # 2. Test & Extract Phase
    if args.pdf:
        pdf_file = Path(args.pdf)
        if not pdf_file.exists():
            print(f"Error: PDF not found at {pdf_file}")
            return

        if not model_path.exists():
            print("Warning: Fine-tuned model not found. Falling back to pretrained.")
            model_path = "microsoft/table-transformer-detection"

        county_data = run_extraction(pdf_file, model_path, project_root)
        
        # Output only the clean county data
        output_file = project_root / "outputs" / f"{pdf_file.stem}_county_data.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(county_data, f, indent=2)
        
        print(f"\nSUCCESS: County data extracted to {output_file}")
        print("Fields available: Project Implementation, Financial Performance, Audit Quality.")

if __name__ == "__main__":
    main()
