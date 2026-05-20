import os
import pypdf
import pytesseract
from pdf2image import convert_from_path
import fitz


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
    return True

def process_digital(pdf_path):
    """Extracts text cleanly from digital PDFs using pypdf."""
    print("[DIGITAL PATH] Extracting text layout via pypdf...")
    text_content = []
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        for i, page in enumerate(reader.pages):
            text_content.append(f"## PAGE {i+1}\n\n{page.extract_text()}")
    return "\n\n".join(text_content)

def process_scanned(pdf_path):
    """
    Fault-tolerant OCR ingestion pathway. 
    Bypasses broken PDF page catalogs and uses PyMuPDF to hunt for raw 
    embedded image objects if the standard page count returns 0.
    """
    print("[SCANNED PATH] Initializing PyMuPDF low-level stream...")
    ocr_text = []
    
    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        
        # --- IF STANDARD PAGE COUNT WORKS ---
        if page_count > 0:
            print(f"[INGESTION GATE] Standard page tree found. Total pages: {page_count}")
            for page_num in range(page_count):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=150)
                img_data = pix.tobytes("png")
                
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(img)
                ocr_text.append(f"## PAGE {page_num + 1}\n\n{text}")
                print(f"Processed Page {page_num + 1}/{page_count} successfully.")
            doc.close()
            return "\n\n".join(ocr_text)
        
        # --- FALLBACK SEQUENCE: NATIVE XREF IMAGE EXTRACTION ---
        print("[INGESTION GATE] Standard page count is 0. Executing PyMuPDF native xref hunt...")
        virtual_page_num = 1
        
        # Iterate through every single raw object in the PDF container
        for xref in range(1, doc.xref_length()):
            if doc.xref_is_image(xref):
                print(f"Found embedded image asset at xref index {xref}. Running OCR...")
                try:
                    # Use Pixmap to automatically decode weird scanner formats (JBIG2, etc.)
                    pix = fitz.Pixmap(doc, xref)
                    
                    # Force conversion to standard RGB if the scanner used CMYK or an alpha mask
                    if pix.n >= 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                        
                    # Convert the clean pixel map to standard PNG bytes
                    image_bytes = pix.tobytes("png")
                    
                    from PIL import Image
                    import io
                    img = Image.open(io.BytesIO(image_bytes))
                    
                    text = pytesseract.image_to_string(img)
                    if text.strip(): 
                        ocr_text.append(f"## EXTRACTED ASSET {virtual_page_num}\n\n{text}")
                        print(f"Processed Asset block {virtual_page_num} successfully.")
                        virtual_page_num += 1
                        
                    # Free up memory inside the loop to protect your Cloud Shell limits
                    pix = None
                    
                except Exception as e:
                    print(f"Skipping damaged image asset at {xref}: {e}")
                    continue  
                    
        # Close the document after the xref loop finishes
        doc.close()
        
    # --- MISSING EXCEPT
    except Exception as e:
        print(f"[CRITICAL FAILURE] Document completely unreadable: {e}")
        return f"# ERROR: Document structure corrupted\n\nFile path: {pdf_path}"
        
    if not ocr_text:
        print("[WARNING] Deep scan recovered zero text characters. File may be encrypted or blank.")
        return "# WARNING: Empty document layout extracted."
        
    return "\n\n".join(ocr_text)
    
def run_ingestion_pipeline(pdf_path, output_dir):
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}.md")
    
    if is_scanned_pdf(pdf_path):
        markdown_content = process_scanned(pdf_path)
    else:
        markdown_content = process_digital(pdf_path)
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
        
    print(f"Ingestion successful! Stored at: {output_path}\n")
    return output_path

if __name__ == "__main__":
    RAW_DIR = "data/raw"
    PROCESSED_DIR = "data/processed"
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    
    pdfs = [f for f in os.listdir(RAW_DIR) if f.endswith('.pdf')]
    if not pdfs:
        print(f"Please drop your OAG/CoB files into '{RAW_DIR}' first.")
    else:
        for pdf in pdfs:
            print(f"Starting processing for: {pdf}")
            run_ingestion_pipeline(os.path.join(RAW_DIR, pdf), PROCESSED_DIR)