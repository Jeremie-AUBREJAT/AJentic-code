import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime

from core.input_detector import detect_input
from core.extractor import extract_input
from core.scanner import scan_codebase
from core.llm_client import ask_llm
from core.doc_generator import generate_html_doc

WORKSPACE = os.getenv("ANALYZER_WORKSPACE", "workspace")
OUTPUT_DIR = os.getenv("ANALYZER_OUTPUT_DIR", "output")
MAX_FILE_SEND_BYTES = int(os.getenv("ANALYZER_MAX_SEND_BYTES", "80000"))
SAVE_FULL = os.getenv("ANALYZER_SAVE_FULL", "0") in ("1", "true", "yes")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _mask(s):
    if not s:
        return s
    s = re.sub(r"(api[_-]?key|secret|token)[\"'\s:=]+([A-Za-z0-9\-_]{8,})",
               r"\1=[REDACTED]", s, flags=re.I)
    s = re.sub(r"\b[0-9a-fA-F]{32,}\b", "[HEX_REDACTED]", s)
    return s


def _normalize(resp):
    if not isinstance(resp, dict):
        return {"llm": {}, "doc": {"summary": "error"}}

    llm = resp.get("llm", {}) or {}
    return {
        "llm": {
            "lang": llm.get("lang", ""),
            "cls": llm.get("cls", []) or [],
            "fn": llm.get("fn", []) or [],
            "hk": llm.get("hk", []) or [],
            "ax": llm.get("ax", []) or [],
        },
        "doc": {"summary": resp.get("doc", {}).get("summary", "")}
    }


def analyze_file(path: Path):
    try:
        code = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"llm": {}, "doc": {"summary": f"read_error: {e}"}}

    if len(code) > MAX_FILE_SEND_BYTES:
        code = code[:MAX_FILE_SEND_BYTES] + "\n/* TRUNCATED */"

    code = _mask(code)

    prompt = f"""
Analyze this WordPress plugin file.

Return STRICT JSON:
{{
  "llm": {{"lang":"","cls":[],"fn":[],"hk":[],"ax":[]}},
  "doc": {{"summary":""}}
}}

Rules:
- JSON only
- no markdown
- no explanation

CODE:
{code}
"""

    return _normalize(ask_llm(prompt))


def build_global_llm(results):
    g = {"cls": set(), "fn": set(), "hk": set(), "ax": set(), "flow": [], "sink": []}

    for r in results:
        llm = r["analysis"]["llm"]

        g["cls"].update(llm["cls"])
        g["fn"].update(llm["fn"])
        g["hk"].update(llm["hk"])
        g["ax"].update(llm["ax"])
        g["flow"].extend(llm["ax"])

        for label in llm["fn"] + llm["hk"]:
            s = str(label).lower()
            if "cookie" in s:
                g["sink"].append("cookie")
            if "wpdb" in s or "database" in s:
                g["sink"].append("db")

    return {
        "cls": sorted(g["cls"]),
        "fn": sorted(g["fn"]),
        "hk": sorted(g["hk"]),
        "ax": sorted(g["ax"]),
        "flow": g["flow"],
        "sink": list(set(g["sink"])),
    }


def minimize_for_llm(final):
    llm = final["llm"]

    return {
        "t": final["type"],
        "n": final["files"],
        "classes": llm["cls"],
        "functions": llm["fn"],
        "hooks": llm["hk"],
        "ajax": llm["ax"],
        "flow": llm["flow"],
        "sinks": llm["sink"],
        "files": final["files_list"],
        "_meta": {"reduced": True, "generated_at": datetime.utcnow().isoformat() + "Z"}
    }


def save_output(data):
    out = Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    minimized = minimize_for_llm(data)

    (out / "result.min.json").write_text(
        json.dumps(minimized, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8"
    )

    (out / "result.json").write_text(
        json.dumps(minimized, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8"
    )


def run_analysis(input_path):
    input_type = detect_input(input_path)
    project_dir = extract_input(input_path, WORKSPACE)
    files = scan_codebase(project_dir)

    results = []
    for f in files:
        p = Path(f)
        results.append({"file": str(p), "analysis": analyze_file(p)})

    final = {
        "type": input_type,
        "files": len(results),
        "files_list": [str(r["file"]) for r in results],
        "llm": build_global_llm(results),
        "results": results
    }

    save_output(final)
    generate_html_doc(final)
    return final


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python main.py <input_path>")
        exit(2)
    run_analysis(sys.argv[1])
