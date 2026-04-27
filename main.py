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
You are a WordPress plugin code analyzer.

Analyze the following file.

Return STRICT JSON with this structure:

{{
 "llm": {{
  "lang":"php|js|unknown",
  "cls":[],
  "fn":[],
  "hk":[],
  "ax":[],
  "lg":[]
 }},
 "doc": {{
  "summary":"",
  "features":[],
  "notes":[]
 }}
}}

Rules:
- JSON only
- no explanation
- no markdown
- no invention
- unknown => empty array

CODE:
{code}
"""

    result = ask_llm(prompt)

    if not isinstance(result, dict):

        return {
            "llm": {
                "lang": "unknown",
                "cls": [],
                "fn": [],
                "hk": [],
                "ax": [],
                "lg": []
            },
            "doc": {
                "summary": "analysis_error",
                "features": [],
                "notes": [str(result)]
            }
        }

    return result


# ---------------------------
# BUILD GLOBAL ANALYSIS (LLM)
# ---------------------------
def build_global_llm(results):

    g = {
        "cls": set(),
        "fn": set(),
        "hk": set(),
        "ax": set(),
        "entry": set(),
        "flow": [],
        "sink": []
    }

    for file in results:

        path = file["file"]

        data = file["analysis"].get("llm", {})

        cls = data.get("cls", [])
        fn = data.get("fn", [])
        hk = data.get("hk", [])
        ax = data.get("ax", [])
        lg = data.get("lg", [])

        for c in cls:
            g["cls"].add(c)

        for f in fn:
            g["fn"].add(f)

        for h in hk:
            g["hk"].add(h)
            g["entry"].add(h)

        for a in ax:
            g["ax"].add(str(a))

        # data flow
        for a in ax:
            g["flow"].append({
                "type": "ajax",
                "ep": a,
                "file": path
            })

        # sinks detection
        for l in lg:

            s = l.lower()

            if "wpdb" in s or "database" in s or "table" in s:
                g["sink"].append({
                    "type": "db",
                    "file": path
                })

            if "cookie" in s:
                g["sink"].append({
                    "type": "cookie",
                    "file": path
                })

    return {
        "cls": list(g["cls"]),
        "fn": list(g["fn"]),
        "hk": list(g["hk"]),
        "ax": list(g["ax"]),
        "entry": list(g["entry"]),
        "flow": g["flow"],
        "sink": g["sink"]
    }


# ---------------------------
# BUILD DOC DATA
# ---------------------------
def build_doc(results):

    doc = []

    for r in results:

        f = r["file"]
        d = r["analysis"].get("doc", {})

        doc.append({
            "file": f,
            "summary": d.get("summary", ""),
            "features": d.get("features", []),
            "notes": d.get("notes", [])
        })

    return doc


# ---------------------------
# SAVE JSON (compact)
# ---------------------------
def save_output(data):

    os.makedirs("output", exist_ok=True)

    with open("output/result.json", "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)


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

    llm_global = build_global_llm(results)

    doc_data = build_doc(results)

    final = {
        "type": input_type,
        "files": len(results),
        "llm": llm_global,
        "doc": doc_data
    }

    save_output(final)

    html_path = generate_html_doc(final)

    print("[DONE]", html_path)

    return final