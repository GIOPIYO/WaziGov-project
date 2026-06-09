import os
import csv
from transformers import pipeline
import warnings

# Suppress warnings for a clean terminal
warnings.filterwarnings("ignore")

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_MODEL_PATH = os.path.join(SCRIPT_DIR, "wazigov-bert-v1")
DATA_DIRECTORY = os.path.join(SCRIPT_DIR, "wazigov-engine", "data", "processed")  # Ensure this points to your .md files
OUTPUT_CSV = os.path.join(SCRIPT_DIR, "wazigov_extracted_budgets.csv")


print(f"Loading WaziGov Engine from {LOCAL_MODEL_PATH}...")
ner_pipeline = pipeline(
    "token-classification",
    model=LOCAL_MODEL_PATH,
    tokenizer=LOCAL_MODEL_PATH,
    aggregation_strategy="simple"
)

def extract_entities(text):
    """Runs the model and cleans up the outputs."""
    raw_results = ner_pipeline(text)
    clean_entities = []
    id2label = {0: "O", 1: "B-COUNTY", 2: "I-COUNTY", 3: "B-AMOUNT", 4: "I-AMOUNT"}

    for entity in raw_results:
        raw_label = str(entity['entity_group']).replace('LABEL_', '')
        
        # Skip 'Outside' tokens immediately
        if raw_label == '0':
            continue
            
        try:
            mapped_label = id2label[int(raw_label)]
        except:
            mapped_label = raw_label
            
        clean_word = entity['word'].replace(' ##', '').replace('##', '')
        
        # Remove spaces from numbers
        if "AMOUNT" in mapped_label:
            clean_word = clean_word.replace(" ", "")
            
        clean_entities.append({
            "entity": clean_word.strip(),
            "label": mapped_label.replace("B-", "").replace("I-", ""), 
            "confidence": round(entity['score'] * 100, 2)
        })
        
    return clean_entities

def process_all_documents():
    print(f"Scanning directory: {DATA_DIRECTORY}...")
    
    # Check if directory exists
    if not os.path.exists(DATA_DIRECTORY):
        print(f"Error: Could not find the folder '{DATA_DIRECTORY}'. Please check your path.")
        return

    files_to_process = [f for f in os.listdir(DATA_DIRECTORY) if f.endswith(".md")]
    print(f"Found {len(files_to_process)} markdown documents to process.\n")
    
    # Prepare the CSV file
    with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        # Write the header row
        writer.writerow(["Source_File", "Entity_Type", "Extracted_Value", "Confidence_Score"])
        
        # Loop through every file
        for filename in files_to_process:
            file_path = os.path.join(DATA_DIRECTORY, filename)
            print(f"Mining data from: {filename}...")
            
            with open(file_path, 'r', encoding='utf-8') as md_file:
                # Read line by line/paragraph by paragraph
                for line in md_file:
                    clean_line = line.strip()
                    if len(clean_line) > 10:  # Skip empty lines or tiny headers
                        
                        # Run the model on the paragraph
                        extracted_data = extract_entities(clean_line)
                        
                        # If the model found something, write it to the CSV
                        for item in extracted_data:
                            writer.writerow([
                                filename, 
                                item['label'], 
                                item['entity'], 
                                f"{item['confidence']}%"
                            ])
                            
    print(f"\nExtraction Complete! All data saved to: {OUTPUT_CSV}")

if __name__ == "__main__":
    process_all_documents()