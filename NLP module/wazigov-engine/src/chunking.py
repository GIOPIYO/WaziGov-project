import os

def sliding_window_chunking(text, chunk_size=512, overlap=51):
    """
    Partitions raw text layouts into overlapping token arrays.
    Enforces a strict chunk size with an overlap buffer.
    """
    tokens = text.split()  # Base tokenization by whitespace
    chunks = []
    
    start = 0
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = " ".join(chunk_tokens)
        chunks.append(chunk_text)
        
        # Move forward by chunk_size minus the overlapping token count
        start += (chunk_size - overlap)
        
    return chunks

def process_processed_markdowns(processed_dir):
    """Reads transformed layout files and outputs structured matrix windows."""
    md_files = [f for f in os.listdir(processed_dir) if f.endswith('.md')]
    
    for md_file in md_files:
        file_path = os.path.join(processed_dir, md_file)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        print(f"Slicing {md_file} into 512-token segments...")
        chunks = sliding_window_chunking(content)
        print(f"Generated {len(chunks)} overlapping layout chunks.")
        
        # In a later step, these chunks are mapped directly to vectors: 
        # X_i = [w_start, ..., w_end, x0, y0, x1, y1] for LayoutLMv3 processing
        
    print("Chunking sequence complete.")

if __name__ == "__main__":
    PROCESSED_DIR = "data/processed"
    process_processed_markdowns(PROCESSED_DIR)