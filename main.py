import os
import json

from core.input_detector import detect_input
from core.extractor import extract_input
from core.scanner import scan_codebase
from core.chunker import chunk_text
from core.llm_client import ask_llm
from core.doc_generator import generate_html_doc

WORKSPACE = "workspace"


# ---------------------------
# ANALYSE D'UN FICHIER (1 SEUL CALL LLM)
# ---------------------------
def analyze_file(file_path):

    print(f"[ANALYZE] {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    # chunking uniquement pour sécurité mémoire
    chunks = chunk_text(code)

    # IMPORTANT : fusion AVANT LLM
    full_code = "\n\n/* ===== FILE CHUNK ===== */\n\n".join(chunks)

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
- fusion complète du fichier (pas chunk)

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
{full_code}
"""

    result = ask_llm(prompt)

    # sécurité fallback
    if not isinstance(result, dict):
        return {
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
# FUSION GLOBALE DU PLUGIN
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
        data = file["analysis"]

        for key in merged.keys():
            merged[key] += data.get(key, [])

    return merged


# ---------------------------
# SAVE JSON
# ---------------------------
def save_output(data):

    os.makedirs("output", exist_ok=True)

    with open("output/result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------
# PIPELINE PRINCIPAL
# ---------------------------
def run_analysis(input_path):

    print("[1] Detect input...")
    input_type = detect_input(input_path)

    print("[2] Extract project...")
    project_dir = extract_input(input_path, WORKSPACE)

    print("[3] Scan codebase...")
    files = scan_codebase(project_dir)

    print(f"[INFO] Files found: {len(files)}")

    results = []

    # LIMIT pour tests
    for file in files[:10]:

        analysis = analyze_file(file)

        results.append({
            "file": str(file),
            "analysis": analysis
        })

    # fusion globale
    global_analysis = merge_global(results)

    final_result = {
        "input_type": input_type,
        "files_analyzed": len(results),
        "results": results,
        "global_analysis": global_analysis
    }

    # save JSON
    save_output(final_result)

    # generate HTML doc
    html_path = generate_html_doc(final_result)

    print("[DONE] HTML DOC:", html_path)

    return final_result