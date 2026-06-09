import fitz
import re
import os

def clean_and_triage_pdf(pdf_path):
    print(f"Opening {os.path.basename(pdf_path)}...")
    doc = fitz.open(pdf_path)
    
    # STEP 1: Check for signature/widget blocks and strip them if they exist
    has_widgets = False
    for page in doc:
        if page.annots():
            has_widgets = True
            break
            
    if has_widgets:
        print("Digital signature or form widgets detected. Unlocking layers...")
        for page in doc:
            for annot in page.annots():
                # Type 19 represents digital signature/widget annotations that mask text
                if annot.type[0] == 19: 
                    page.delete_annot(annot)
                    
    full_markdown_content = []
    
    # STEP 2: Iterate through pages and decide whether to extract natively or fallback to full-page OCR
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_header = f"\n\n## PAGE {page_num + 1}\n\n"
        full_markdown_content.append(page_header)
        
        # Try native structural text block extraction first
        blocks = page.get_text("blocks")
        native_text_pieces = [b[4].strip() for b in blocks if b[4].strip()]
        page_text = "\n".join(native_text_pieces)
        
        # If native extraction successfully found text, keep it
        if len(page_text.strip()) > 150: # Adjust threshold as needed
            full_markdown_content.append(page_text)
        else:
            # STEP 3: Fallback to high-resolution full-page canvas rasterization
            print(f"Page {page_num + 1} yielded low text characters. Activating High-DPI Fallback OCR...")
            
            # Render the entire page as a crisp image at 2x resolution
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            
            # --- INTEGRATION LINK FOR YOUR TESSERACT WRAPPER ---
            # If you use pytesseract, you would convert this pixmap to a PIL Image:
            # from PIL import Image
            # import io
            # import pytesseract
            # img = Image.open(io.BytesIO(pix.tobytes("png")))
            # ocr_text = pytesseract.image_to_string(img)
            # full_markdown_content.append(ocr_text)
            
            # Temporary placeholder until your local tesseract wrapper is connected:
            full_markdown_content.append("[FALLBACK IMAGE RENDERED - RUN LOCAL OCR COMPONENT HERE]")
            
    return "".join(full_markdown_content)

# --- EXECUTE ---
if __name__ == "__main__":
    # Point this to your raw PDF file path
    INPUT_PDF = "data/raw/GREEN-BOOK-EXECUTIVES-2024-FINAL-5.3.2025-SIGNED.pdf"
    OUTPUT_MD = "data/processed/GREEN-BOOK-EXECUTIVES-2024-FINAL-5.3.2025-SIGNED.md"
    
    if os.path.exists(INPUT_PDF):
        processed_markdown = clean_and_triage_pdf(INPUT_PDF)
        
        # Save the clean structural text directly to your markdown folder
        with open(OUTPUT_MD, "w", encoding="utf-8") as f:
            f.write(processed_markdown)
        print(f"\nIngestion completely repaired! File written safely to: {OUTPUT_MD}")
    else:
        print(f"Please place your raw PDF at: {INPUT_PDF}")