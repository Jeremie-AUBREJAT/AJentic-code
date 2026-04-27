import os
import json

from core.input_detector import detect_input
from core.extractor import extract_input
from core.scanner import scan_codebase
from core.llm_client import ask_llm
from core.doc_generator import generate_html_doc

WORKSPACE = "workspace"


# ---------------------------
# ANALYSE FICHIER (1 CALL LLM)
# ---------------------------
def analyze_file(file_path):

    print(f"[ANALYZE] {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        code = f.read()

    prompt = f"""
Tu es un expert en analyse de plugins WordPress (PHP + JavaScript).

Analyse ce fichier COMPLET.

Retourne STRICTEMENT un JSON valide avec cette structure :

{{
  "language": "php|js|unknown",
  "classes": [],
  "functions": [],
  "hooks": [],
  "ajax": [],
  "logic": []
}}

RÈGLES :
- JSON strict uniquement
- aucun markdown
- aucune explication
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
# BUILD GLOBAL ANALYSIS
# ---------------------------
def build_global_analysis(results):

    global_analysis = {
        "classes": [],
        "functions": [],
        "hooks": [],
        "ajax": [],
        "logic": [],
        "entrypoints": [],
        "hook_map": [],
        "execution_graph": [],
        "data_flow": [],
        "state_model": [],
        "data_sinks": []
    }

    for file in results:

        path = file["file"]
        data = file.get("analysis", {})

        classes = data.get("classes", [])
        functions = data.get("functions", [])
        hooks = data.get("hooks", [])
        ajax = data.get("ajax", [])
        logic = data.get("logic", [])

        global_analysis["classes"] += classes
        global_analysis["functions"] += functions
        global_analysis["hooks"] += hooks
        global_analysis["ajax"] += ajax
        global_analysis["logic"] += logic

        # ENTRYPOINTS
        for h in hooks:
            global_analysis["entrypoints"].append(h)

        # HOOK MAP
        for h in hooks:
            for f in functions:
                global_analysis["hook_map"].append({
                    "hook": h,
                    "function": f,
                    "file": path
                })

        # EXECUTION GRAPH
        for h in hooks:
            for f in functions:
                global_analysis["execution_graph"].append({
                    "entrypoint": h,
                    "function": f,
                    "file": path
                })

        # DATA FLOW (AJAX)
        for a in ajax:
            global_analysis["data_flow"].append({
                "type": "ajax",
                "endpoint": a,
                "file": path
            })

        # DATA SINKS
        for l in logic:

            lower = l.lower()

            if "wpdb" in lower or "database" in lower or "table" in lower:
                global_analysis["data_sinks"].append({
                    "type": "database",
                    "description": l,
                    "file": path
                })

            if "cookie" in lower:
                global_analysis["data_sinks"].append({
                    "type": "cookie",
                    "description": l,
                    "file": path
                })

            if "ajax" in lower:
                global_analysis["data_sinks"].append({
                    "type": "ajax",
                    "description": l,
                    "file": path
                })

            if "post" in lower or "get" in lower:
                global_analysis["state_model"].append({
                    "type": "request_state",
                    "description": l,
                    "file": path
                })

    return global_analysis


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

    for file in files:

        analysis = analyze_file(file)

        results.append({
            "file": str(file),
            "analysis": analysis
        })

    global_analysis = build_global_analysis(results)

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