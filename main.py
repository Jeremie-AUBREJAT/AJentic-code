import os
import json
from pathlib import Path

from core.input_detector import detect_input
from core.extractor import extract_input
from core.scanner import scan_codebase
from core.llm_client import ask_llm
from core.doc_generator import generate_html_doc

WORKSPACE = "workspace"
OUTPUT_DIR = "output"


# ---------------------------
# ANALYSE D'UN FICHIER (1 CALL LLM)
# ---------------------------
def analyze_file(file_path):

    print(f"[ANALYZE] {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception as e:
        return {
            "status": "error",
            "file": str(file_path),
            "message": str(e)
        }

    prompt = f"""
Tu es un expert en analyse de code WordPress (PHP + JavaScript).

Analyse ce fichier COMPLET.

Tu dois détecter :

- classes
- fonctions
- hooks WordPress
- endpoints AJAX
- logique métier

⚠️ IMPORTANT :

- retourne UNIQUEMENT un JSON valide
- aucun texte
- aucun markdown

FORMAT OBLIGATOIRE :

{{
  "language": "php|js|unknown",
  "classes": [],
  "functions": [],
  "hooks": [],
  "ajax": [],
  "logic": []
}}

CODE:
{code}
"""

    result = ask_llm(prompt)

    if not isinstance(result, dict):
        result = {
            "language": "unknown",
            "classes": [],
            "functions": [],
            "hooks": [],
            "ajax": [],
            "logic": [],
            "raw_response": result
        }

    return result


# ---------------------------
# SAVE JSON PAR FICHIER
# ---------------------------
def save_file_json(file_path, analysis, plugin_name):

    plugin_output = Path(OUTPUT_DIR) / plugin_name
    plugin_output.mkdir(parents=True, exist_ok=True)

    file_name = Path(file_path).name + ".json"

    output_path = plugin_output / file_name

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    return output_path


# ---------------------------
# MERGE GLOBAL
# ---------------------------
def merge_results(plugin_name):

    plugin_output = Path(OUTPUT_DIR) / plugin_name

    merged = {
        "plugin": plugin_name,
        "files": [],
        "classes": [],
        "functions": [],
        "hooks": [],
        "ajax": [],
        "logic": []
    }

    for json_file in plugin_output.glob("*.json"):

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        merged["files"].append(json_file.name)

        merged["classes"] += data.get("classes", [])
        merged["functions"] += data.get("functions", [])
        merged["hooks"] += data.get("hooks", [])
        merged["ajax"] += data.get("ajax", [])
        merged["logic"] += data.get("logic", [])

    final_path = Path(OUTPUT_DIR) / f"{plugin_name}_analysis.json"

    with open(final_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    return final_path


# ---------------------------
# PIPELINE PRINCIPAL
# ---------------------------
def run_analysis(input_path):

    print("[1] Detect input...")
    input_type = detect_input(input_path)

    print("[2] Extract project...")
    project_dir = extract_input(input_path, WORKSPACE)

    plugin_name = Path(project_dir).name

    print("[3] Scan codebase...")
    files = scan_codebase(project_dir)

    print(f"[INFO] Files found: {len(files)}")

    results = []

    for file in files:

        analysis = analyze_file(file)

        save_file_json(file, analysis, plugin_name)

        results.append({
            "file": str(file),
            "analysis": analysis
        })

    print("[4] Merge JSON files...")

    merged_json = merge_results(plugin_name)

    print("[DONE] JSON GLOBAL:", merged_json)

    html_path = generate_html_doc({
        "plugin": plugin_name,
        "results": results
    })

    print("[DONE] HTML DOC:", html_path)

    return merged_json