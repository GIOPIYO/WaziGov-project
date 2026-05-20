import os
import pypdf  # Use 'pip install pypdf' if not installed yet
import pytesseract
from PIL import Image
from pdf2image import convert_from_path  # Use 'pip install pdf2image'
from docling.document_converter import DocumentConverter

def is_scanned_pdf(pdf_path):
    """Detects if a PDF is a scanned image or contains digital text."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages[:3]:  # Sample first 3 pages
                if page.extract_text().strip():
                    return False  # Born-digital text found
    except Exception:
        pass
    return True  # No text extracted; treat as scanned raster image

def process_digital(pdf_path, output_dir):
    """Routes born-digital documents through the Docling structural parser."""
    print(f"[DIGITAL PATH] Processing via Docling structural parser...")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    markdown_content = result.document.export_to_markdown()
    return markdown_content

def process_scanned(pdf_path):
    """Routes legacy scanned documents through a Tesseract OCR pipeline with filters."""
    print(f"[SCANNED PATH] PDF contains raster images. Executing Tesseract v5 OCR...")
    # Convert PDF pages to images for OCR processing
    pages = convert_from_path(pdf_path, dpi=300)
    ocr_text = []
    
    for i, page_img in enumerate(pages):
        # Apply standard contrast enhancement filters if needed via PIL here
        text = pytesseract.image_to_string(page_img)
        ocr_text.append(f"## PAGE {i+1}\n\n{text}")
        
    return "\n\n".join(ocr_text)

def run_ingestion_pipeline(pdf_path, output_dir):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.md")
    
    # Dual-Path Routing Logic (Step 1)
    if is_scanned_pdf(pdf_path):
        markdown_content = process_scanned(pdf_path)
    else:
        markdown_content = process_digital(pdf_path, output_dir)
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"Ingestion successful! Structural representation stored at: {output_path}\n")
    return output_path

if __name__ == "__main__":
    RAW_DIR = "data/raw"
    PROCESSED_DIR = "data/processed"
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    pdfs = [f for f in os.listdir(RAW_DIR) if f.endswith('.pdf')]
    if not pdfs:
        print(f"Error: Drop your OAG/CoB files into '{RAW_DIR}' before running.")
    else:
        for pdf in pdfs:
            print(f"Starting pipeline processing for: {pdf}")
            run_ingestion_pipeline(os.path.join(RAW_DIR, pdf), PROCESSED_DIR)