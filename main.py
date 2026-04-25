import os
import json

from core.input_detector import detect_input
from core.extractor import extract_input
from core.scanner import scan_codebase
from core.llm_client import ask_llm
from core.doc_generator import generate_html_doc

WORKSPACE = "workspace"


# ---------------------------
# ANALYSE FICHIER (1 CALL LLM / FICHIER)
# ---------------------------
def analyze_file(file_path):

    print(f"[ANALYZE] {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    prompt = f"""
Tu es un expert en analyse de plugins WordPress (PHP + JavaScript).

Analyse ce fichier COMPLET.

Tu dois extraire uniquement des informations fiables.

Retour JSON STRICT :

{{
  "language": "php|js|unknown",
  "classes": [],
  "functions": [],
  "hooks": [],
  "ajax": [],
  "logic": []
}}

RÈGLES IMPORTANTES:
- aucun texte
- aucun markdown
- JSON valide uniquement
- pas d'invention
- si inconnu => tableau vide

CODE:
{code}
"""

    result = ask_llm(prompt)

    if not isinstance(result, dict):
        return {
            "language": "unknown",
            "classes": [],
            "functions": [],
            "hooks": [],
            "ajax": [],
            "logic": [],
            "raw_error": result
        }

    return result


# ---------------------------
# MERGE GLOBAL PLUGIN
# ---------------------------
def merge_global(results):

    merged = {
        "classes": [],
        "functions": [],
        "hooks": [],
        "ajax": [],
        "logic": []
    }

    for file in results:
        data = file.get("analysis", {})

        for k in merged.keys():
            merged[k] += data.get(k, [])

    return merged


# ---------------------------
# SAVE JSON
# ---------------------------
def save_output(data):

    os.makedirs("output", exist_ok=True)

    with open("output/result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------
# PIPELINE
# ---------------------------
def run_analysis(input_path):

    print("[1] Detect input")
    input_type = detect_input(input_path)

    print("[2] Extract project")
    project_dir = extract_input(input_path, WORKSPACE)

    print("[3] Scan files")
    files = scan_codebase(project_dir)

    print(f"[INFO] Files: {len(files)}")

    results = []

    for file in files[:10]:

        analysis = analyze_file(file)

        results.append({
            "file": str(file),
            "analysis": analysis
        })

    global_analysis = merge_global(results)

    final = {
        "input_type": input_type,
        "files_analyzed": len(results),
        "results": results,
        "global_analysis": global_analysis
    }

    save_output(final)

    html_path = generate_html_doc(final)

    print("[DONE]", html_path)

    return final