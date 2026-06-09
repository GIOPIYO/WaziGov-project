from transformers import pipeline
import warnings

# Suppress minor huggingface warnings for a cleaner terminal
warnings.filterwarnings("ignore")

# 1. Point this to the folder you just unzipped!
LOCAL_MODEL_PATH = "./wazigov-bert-v1"

print(f"Loading WaziGov Engine from: {LOCAL_MODEL_PATH}...")

# 2. Load the pipeline using local files (No internet required!)
ner_pipeline = pipeline(
    "token-classification",
    model=LOCAL_MODEL_PATH,
    tokenizer=LOCAL_MODEL_PATH,
    aggregation_strategy="simple" # This tells the pipeline to auto-merge B and I tags
)

def extract_entities(text):
    """Runs the model and cleans up the outputs."""
    raw_results = ner_pipeline(text)
    clean_entities = []
    
    # Label mapping dictionary (in case the pipeline returns raw strings)
    id2label = {0: "O", 1: "B-COUNTY", 2: "I-COUNTY", 3: "B-AMOUNT", 4: "I-AMOUNT"}

    for entity in raw_results:
        # Ignore 'Outside' tokens
        if entity['entity_group'] == '0' or entity['entity_group'] == 'LABEL_0':
            continue
            
        # Map the label ID to the human-readable tag
        raw_label = str(entity['entity_group']).replace('LABEL_', '')
        try:
            mapped_label = id2label[int(raw_label)]
        except:
            mapped_label = raw_label
            
        # Clean up WordPiece artifacts (e.g., merging "##basa" into "Mom")
        clean_word = entity['word'].replace(' ##', '').replace('##', '')

        if "AMOUNT" in mapped_label:
            clean_word = clean_word.replace(" ", "")
        
        clean_entities.append({
            "entity": clean_word.strip(),
            "label": mapped_label,
            "confidence": round(entity['score'] * 100, 2)
        })
        
    return clean_entities

# --- TEST THE LOCAL ENGINE ---
if __name__ == "__main__":
    print("\nModel loaded successfully. Running test...")
    
    test_text = "During the review, the County Assembly of Mombasa reported pending bills totaling 233,512,403.10 and requested additional funding."
    
    print(f"\nInput Document: '{test_text}'")
    print("-" * 50)
    
    extracted_data = extract_entities(test_text)
    
    for item in extracted_data:
        print(f"Found: {item['entity']:<20} | Tag: {item['label']:<10} | Confidence: {item['confidence']}%")