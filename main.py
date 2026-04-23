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
# Analyse fichier (OPTIMISÉ)
# ---------------------------
def analyze_file(file_path):

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    chunks = chunk_text(code)

    merged_result = {
        "classes": [],
        "functions": [],
        "hooks": [],
        "ajax": [],
        "logic": []
    }

    for chunk in chunks:

        prompt = f"""
Analyse ce code WordPress.

Retourne UNIQUEMENT JSON:

{{
  "classes": [],
  "functions": [],
  "hooks": [],
  "ajax": [],
  "logic": []
}}

CODE:
{chunk}
"""

        result = ask_llm(prompt)

        if isinstance(result, dict):

            merged_result["classes"] += result.get("classes", [])
            merged_result["functions"] += result.get("functions", [])
            merged_result["hooks"] += result.get("hooks", [])
            merged_result["ajax"] += result.get("ajax", [])
            merged_result["logic"] += result.get("logic", [])

    return merged_result


# ---------------------------
# FUSION GLOBALE PLUGIN
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

        merged["classes"] += data.get("classes", [])
        merged["functions"] += data.get("functions", [])
        merged["hooks"] += data.get("hooks", [])
        merged["ajax"] += data.get("ajax", [])
        merged["logic"] += data.get("logic", [])

    return merged


# ---------------------------
# SAVE
# ---------------------------
def save_output(data):

    os.makedirs("output", exist_ok=True)

    with open("output/result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ---------------------------
# PIPELINE PRINCIPAL
# ---------------------------
def run_analysis(input_path):

    print("Detecting input type...")
    input_type = detect_input(input_path)

    print("Type:", input_type)

    print("Extracting project...")
    project_dir = extract_input(input_path, WORKSPACE)

    print("Scanning codebase...")
    files = scan_codebase(project_dir)

    print(f"Files found: {len(files)}")

    results = []

    # LIMIT pour perf
    for file in files[:10]:

        print("Analyzing:", file)

        analysis = analyze_file(file)

        results.append({
            "file": str(file),
            "analysis": analysis
        })

    # 🔥 FUSION GLOBALE
    global_analysis = merge_global(results)

    final_result = {
        "input_type": input_type,
        "files_analyzed": len(results),
        "results": results,
        "global_analysis": global_analysis
    }

    # SAVE JSON
    save_output(final_result)

    # HTML DOC (Doxygen-like)
    html_path = generate_html_doc(final_result)

    print("DOC GENERATED:", html_path)

    return final_result