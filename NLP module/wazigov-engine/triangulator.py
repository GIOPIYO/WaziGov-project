import os
import json
import re
from pathlib import Path
from rapidfuzz import fuzz, process
from collections import Counter
from datetime import datetime
import nltk

# You may need to run this once if you haven't downloaded the sentence splitter
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

# ==========================================
# 1. SETUP & MODEL LOADING
# ==========================================
MODEL_PATH = "GIOPIYO/Deberta-WaziGov" 
HF_TOKEN = os.environ.get("HF_TOKEN")

print(f"Loading NER model from Hugging Face: {MODEL_PATH}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, token=HF_TOKEN)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH, token=HF_TOKEN)

ner_pipeline = pipeline(
    "token-classification", 
    model=model, 
    tokenizer=tokenizer, 
    aggregation_strategy="simple"
)

# ==========================================
# 2. FILE PARSING HELPER FUNCTIONS
# ==========================================
# ==========================================
# 2. FILE PARSING HELPER FUNCTIONS
# ==========================================
def normalise(name):
    return re.sub(r"[\s'\-/]+", " ", name.lower().strip())

def parse_cob(filepaths):
    sections = []
    for filepath in filepaths:
        try:
            text = Path(filepath).read_text(encoding="utf-8")
            pattern = re.compile(
                r'3\.\d+\.\s+(?:County Government of\s+([^\.\n\r\t]+)|(Nairobi City) County Government)',
                re.MULTILINE
            )
            positions = []
            for m in pattern.finditer(text):
                name = m.group(1) if m.group(1) else m.group(2)
                positions.append((m.start(), name.strip()))

            for i, (start, name) in enumerate(positions):
                end = positions[i+1][0] if i+1 < len(positions) else len(text)
                sections.append({"county": name, "source": "COB", "text": text[start:end]})
            print(f"CoB: Successfully loaded '{filepath}'")
        except FileNotFoundError:
            print(f"ERROR: Could not find COB file -> {filepath}")
    
    return sections

def parse_oag(filepaths):
    sections = []
    for filepath in filepaths:
        try:
            text = Path(filepath).read_text(encoding="utf-8")
            pattern = re.compile(
                r'(?=(?:County\s+Executive\s+o\s*f|COUNTY\s+EXECUTIVE\s+OF)\s+([^\.\n\r\t\-–]+)(?:\s*[-–]|\s*\.\.\.))',
                re.MULTILINE | re.IGNORECASE
            )
            positions = [(m.start(), m.group(1).strip().title()) for m in pattern.finditer(text)]

            for i, (start, name) in enumerate(positions):
                end = positions[i+1][0] if i+1 < len(positions) else len(text)
                sections.append({"county": name, "source": "OAG", "text": text[start:end]})
            print(f"OAG: Successfully loaded '{filepath}'")
        except FileNotFoundError:
             print(f"ERROR: Could not find OAG file -> {filepath}")
             
    return sections

# ==========================================
# 3. EXTRACTION LOGIC
# ==========================================
def extract_projects(text, county):
    """Extracts planned projects and amounts from COB text using Regex."""
    projects = []
    table_m = re.search(r'[Ll]ist of [Dd]evelopment [Pp]rojects.{0,100}Highest Expenditure(.*?)(?:3\.\d+\.\d+\s+[A-Z]|\Z)', text, re.DOTALL)
    if not table_m:
        return projects

    table_text = table_m.group(1)
    lines = [l.strip() for l in table_text.split('\n') if l.strip()]

    for line in lines:
        if re.match(r'^(Sector|Project|Location|Contract|Amount|No\.|S/N|Budget)', line, re.IGNORECASE): continue
        line_clean = re.sub(r'(?<=\d),\s+(?=\d)', ',', line)
        amounts = re.findall(r'[\d,]{5,}(?:\.\d+)?', line_clean)
        if len(amounts) < 2: continue

        pct_m = re.search(r'(\d{1,3}(?:\.\d+)?)\s*$', line_clean)
        pct = float(pct_m.group(1)) if pct_m and float(pct_m.group(1)) <= 250 else None

        def to_f(s):
            try: return float(s.replace(",",""))
            except: return None

        c_sum = to_f(amounts[0])
        a_paid = to_f(amounts[-1])

        projects.append({
            "county": county,
            "project_name": re.sub(r'[\d,]{5,}(?:\.\d+)?', '', line_clean).strip()[:150],
            "contract_sum_kshs": c_sum,
            "amount_paid_kshs": a_paid,
            "implementation_pct": pct,
            "source_cob": True,
            "source_oag": False,
            "absorption_flag": "LOW" if pct and pct < 30 else "NORMAL" if pct else "UNKNOWN"
        })
    return projects

def extract_dev_signal(text, county):
    """Mock/Placeholder for development expenditure signal. Replace with your actual regex if needed."""
    # Assuming baseline 30% rule for now
    return {"status": "OK", "dev_pct": 35.0, "metric": "Dev spend > 30%"}

def extract_oag_entities(text, county):
    """Uses DeBERTa AI model to extract audit findings from OAG text."""
    findings = []
    sentences = nltk.sent_tokenize(text)
    
    # Process sentence by sentence to avoid model max-length limits
    for sent in sentences:
        if len(sent) < 40: continue
        
        raw_entities = ner_pipeline(sent)
        if not raw_entities: continue
        
        current_finding = {"sentence": sent.strip(), "project_name_extracted": "", "amounts_kshs": [], "risk_type": "GENERAL_FINDING"}
        has_relevant_entity = False
        
        for ent in raw_entities:
            group = ent['entity_group']
            word = ent['word'].strip()
            
            if group == 'PROJECT_NAME':
                current_finding["project_name_extracted"] = word
                has_relevant_entity = True
            elif group == 'KSH_AMOUNT':
                amount_str = re.sub(r'[^\d.]', '', word)
                if amount_str:
                    current_finding["amounts_kshs"].append(float(amount_str))
            elif group == 'RISK_FINDING':
                current_finding["risk_type"] = "FLAGGED_BY_MODEL"
                has_relevant_entity = True
                
        # Only append if the model actually found a project name or risk finding
        if has_relevant_entity:
            findings.append(current_finding)
            
    return findings

# ==========================================
# 4. TRIANGULATION LOGIC
# ==========================================
def link(cob_projects, oag_findings, county, dev_signal, threshold=65):
    """Fuzzy matches COB projects to OAG DeBERTa findings."""
    linked = []
    matched_oag = set()

    for proj in cob_projects:
        name = proj["project_name"]
        matches = []
        for i, finding in enumerate(oag_findings):
            extracted = finding.get("project_name_extracted") or ""
            score = (
                max(fuzz.token_sort_ratio(name.lower(), extracted.lower()),
                    fuzz.partial_ratio(name.lower(), extracted.lower()))
                if extracted else
                fuzz.partial_ratio(name.lower()[:60], finding["sentence"].lower())
            )
            if score >= threshold:
                matches.append({**finding, "match_score": score})
                matched_oag.add(i)

        risk_types = {m["risk_type"] for m in matches}
        severe = {"FLAGGED_BY_MODEL", "INCOMPLETE_PROJECT", "UNSUPPORTED_PAYMENT", "PROCUREMENT_BREACH", "DUPLICATE_PAYMENT"}
        
        verdict = (
            "CORROBORATED_PROJECT_RISK" if matches and risk_types & severe else
            "OAG_NOTED"                 if matches else
            "COB_LOW_ABSORPTION"        if proj.get("absorption_flag") in ("LOW","VERY_LOW") else
            "COB_LISTED_CLEAN"
        )

        linked.append({
            "project_id": f"{county[:4].lower()}-{re.sub(r'[^a-z0-9]','',name.lower())[:10]}",
            "county": county,
            "financial_year": "2023/2024",
            "project_name": name,
            "contract_sum_kshs": proj.get("contract_sum_kshs"),
            "amount_paid_kshs": proj.get("amount_paid_kshs"),
            "implementation_pct": proj.get("implementation_pct"),
            "source_cob": True,
            "source_oag": bool(matches),
            "dev_threshold_breach": dev_signal.get("status") == "FLAGGED",
            "cob_signal": {
                "status": proj.get("absorption_flag"),
                "dev_pct": dev_signal.get("dev_pct"),
                "metric": dev_signal.get("metric")
            },
            "oag_forensics": {
                "status": "FLAGGED" if matches else "NOT_SAMPLED",
                "findings": [m["sentence"] for m in matches],
                "risk_types": list(risk_types),
                "match_confidence": matches[0]["match_score"] if matches else None
            },
            "triangulation_verdict": verdict
        })

    # Add OAG-only records (Projects the AI found that weren't in COB Highest Expenditure table)
    for i, finding in enumerate(oag_findings):
        if i in matched_oag or not finding.get("project_name_extracted"):
            continue
        linked.append({
            "project_id": f"{county[:4].lower()}-oagonly-{i}",
            "county": county,
            "financial_year": "2023/2024",
            "project_name": finding["project_name_extracted"],
            "contract_sum_kshs": finding["amounts_kshs"][0] if finding["amounts_kshs"] else None,
            "amount_paid_kshs": None,
            "implementation_pct": None,
            "source_cob": False,
            "source_oag": True,
            "dev_threshold_breach": dev_signal.get("status") == "FLAGGED",
            "cob_signal": None,
            "oag_forensics": {
                "status": "FLAGGED",
                "findings": [finding["sentence"]],
                "risk_types": [finding["risk_type"]],
                "match_confidence": None
            },
            "triangulation_verdict": "OAG_ONLY_PROJECT_FLAG"
        })

    return linked

# ==========================================
# 5. MAIN ORCHESTRATION PIPELINE
# ==========================================
def run_pipeline():
    print("Starting Triangulation Pipeline...")
    
    # --- UPDATE THESE PATHS TO YOUR ACTUAL MD FILES ---
    COB_FILES = [
        "data/processed/County report September 2024 copy.md",
        "data/processed/CGBIRR August 2025.md"
    ]
    OAG_FILES = [
        "data/processed/GREEN-BOOK-EXECUTIVES-2024-FINAL-5.3.2025-SIGNED.md",
        "data/processed/OAG-2024-2025.md"
    ]
    
    COB_PATH = COB_FILES
    OAG_PATH = OAG_FILES
    
    cob_sections = parse_cob(COB_PATH)
    oag_sections = parse_oag(OAG_PATH)

    if not cob_sections or not oag_sections:
        print("CRITICAL ERROR: Failed to load files. Check your file paths.")
        return

    # Create a lookup dictionary for OAG to easily match with COB counties
    oag_lookup = {}
    for s in oag_sections:
        c_name = normalise(s["county"])
        if c_name not in oag_lookup:
            oag_lookup[c_name] = []
        oag_lookup[c_name].append(s)

    all_output = {
        "pipeline": "WaziGov_Hybrid_Extraction",
        "financial_year": "2023/2024",
        "generated_at": datetime.now().isoformat(),
        "counties": [],
        "summary": {}
    }

    verdict_totals = {}
    flagged_counties = []

    for cob_sec in cob_sections:
        county = cob_sec["county"]
        print(f"\nProcessing {county}...")
        
        oag_sec = oag_lookup.get(normalise(county))
        
        # 1. COB Extraction
        dev_sig = extract_dev_signal(cob_sec["text"], county)
        cob_proj = extract_projects(cob_sec["text"], county)
        print(f"  - COB: Found {len(cob_proj)} projects in Highest Expenditure list.")
        
        # 2. OAG AI Extraction
        oag_find = []
        if oag_sec:
            oag_find = extract_oag_entities(oag_sec["text"], county)
            print(f"  - OAG: DeBERTa model extracted {len(oag_find)} potential flagged entities/projects.")
        else:
            print("  - OAG: No matching county section found in OAG report.")

        # 3. Triangulation
        linked = link(cob_proj, oag_find, county, dev_sig)
        
        # Compile Stats
        for r in linked:
            v = r["triangulation_verdict"]
            verdict_totals[v] = verdict_totals.get(v, 0) + 1

        if dev_sig.get("status") == "FLAGGED":
            flagged_counties.append(county)

        all_output["counties"].append({
            "county": county,
            "oag_matched": oag_sec is not None,
            "dev_signal": dev_sig,
            "stats": {
                "cob_projects": sum(1 for r in linked if r["source_cob"]),
                "oag_findings": len(oag_find),
                "total_records": len(linked),
                "verdicts": dict(Counter(r["triangulation_verdict"] for r in linked))
            },
            "projects": linked
        })

    all_output["summary"] = {
        "total_counties": len(all_output["counties"]),
        "counties_below_dev_threshold": flagged_counties,
        "verdict_totals": verdict_totals
    }

    output_file = "final_master_audit_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_output, f, indent=2, ensure_ascii=False)

    print("\n" + "="*40)
    print("=== PIPELINE COMPLETE ===")
    print("="*40)
    print(f"Total Counties Processed: {all_output['summary']['total_counties']}")
    print("Verdict Breakdown:")
    for verdict, count in verdict_totals.items():
        print(f"  - {verdict}: {count}")
    print(f"\nSaved comprehensive JSON database to: {output_file}")

if __name__ == "__main__":
    run_pipeline()