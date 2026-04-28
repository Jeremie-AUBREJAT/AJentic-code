import os
import re
import json
import logging
from pathlib import Path
from datetime import datetime
from collections import Counter

from core.input_detector import detect_input
from core.extractor import extract_input
from core.scanner import scan_codebase
from core.llm_client import ask_llm
from core.doc_generator import generate_html_doc

# ---------------------------
# Configuration (env override)
# ---------------------------
WORKSPACE = os.getenv("ANALYZER_WORKSPACE", "workspace")
OUTPUT_DIR = os.getenv("ANALYZER_OUTPUT_DIR", "output")
MAX_FILE_SEND_BYTES = int(os.getenv("ANALYZER_MAX_SEND_BYTES", "100000"))  # bytes sent to LLM per file
MAX_SAMPLE = int(os.getenv("ANALYZER_MAX_SAMPLE", "5"))  # items per sample
MIN_SUMMARY_LEN = int(os.getenv("ANALYZER_MIN_SUMMARY_LEN", "80"))
SAVE_FULL = os.getenv("ANALYZER_SAVE_FULL", "1").lower() in ("1", "true", "yes")

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------
# Utilities
# ---------------------------
def _truncate(s, max_len=200):
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def _sample_list(lst, n=MAX_SAMPLE):
    if not lst:
        return []
    seen = []
    for x in lst:
        if x not in seen:
            seen.append(x)
        if len(seen) >= n:
            break
    return seen


def _top_keywords(texts, n=6):
    cnt = Counter()
    for t in texts:
        if not t:
            continue
        s = re.sub(r"[^\w\s]", " ", str(t).lower())
        words = [w for w in s.split() if len(w) > 3]
        cnt.update(words)
    return [w for w, _ in cnt.most_common(n)]


def _mask_secrets_in_text(s):
    """
    Basic masking for obvious secrets (API keys, tokens, long hex strings).
    This is intentionally conservative and not a replacement for a full secret scanner.
    """
    if not s:
        return s
    # mask long hex-like strings and common key patterns
    s = re.sub(r"(?:api[_-]?key|secret|token)[\"'\s:=]+([A-Za-z0-9\-_]{8,})", r"\1[REDACTED]", s, flags=re.I)
    s = re.sub(r"\b[0-9a-fA-F]{32,}\b", "[REDACTED_HEX]", s)
    return s


# ---------------------------
# LLM response normalization
# ---------------------------
def _normalize_llm_response(resp):
    if not isinstance(resp, dict):
        return {
            "llm": {"lang": "unknown", "cls": [], "fn": [], "hk": [], "ax": [], "lg": []},
            "doc": {"summary": "error", "features": [], "notes": [str(resp)]}
        }

    llm = resp.get("llm", {}) or {}
    doc = resp.get("doc", {}) or {}

    return {
        "llm": {
            "lang": llm.get("lang", "") or "",
            "cls": llm.get("cls", []) if isinstance(llm.get("cls", []), list) else [],
            "fn": llm.get("fn", []) if isinstance(llm.get("fn", []), list) else [],
            "hk": llm.get("hk", []) if isinstance(llm.get("hk", []), list) else [],
            "ax": llm.get("ax", []) if isinstance(llm.get("ax", []), list) else [],
            "lg": llm.get("lg", []) if isinstance(llm.get("lg", []), list) else []
        },
        "doc": {
            "summary": doc.get("summary", "") or "",
            "features": doc.get("features", []) if isinstance(doc.get("features", []), list) else [],
            "notes": doc.get("notes", []) if isinstance(doc.get("notes", []), list) else []
        }
    }


# ---------------------------
# File analysis
# ---------------------------
def analyze_file(file_path: Path):
    logging.info("ANALYZE %s", file_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception as e:
        logging.exception("read error")
        return {
            "llm": {"lang": "unknown", "cls": [], "fn": [], "hk": [], "ax": [], "lg": []},
            "doc": {"summary": "read_error", "features": [], "notes": [str(e)]}
        }

    # truncate code sent to LLM
    if len(code) > MAX_FILE_SEND_BYTES:
        logging.info("Truncating %s bytes -> %s bytes for LLM", len(code), MAX_FILE_SEND_BYTES)
        code_to_send = code[:MAX_FILE_SEND_BYTES] + f"\n/* TRUNCATED to {MAX_FILE_SEND_BYTES} bytes */\n"
    else:
        code_to_send = code

    # mask obvious secrets before sending to LLM
    code_to_send = _mask_secrets_in_text(code_to_send)

    prompt = f"""
Analyze this WordPress plugin file.

Return STRICT JSON:

{{
  "llm": {{
    "lang": "",
    "cls": [],
    "fn": [],
    "hk": [],
    "ax": [],
    "lg": []
  }},
  "doc": {{
    "summary": "",
    "features": [],
    "notes": []
  }}
}}

Rules:
- JSON only
- no markdown
- no explanation
- no hallucination

CODE:
{code_to_send}
"""

    result = ask_llm(prompt)
    normalized = _normalize_llm_response(result)
    return normalized


# ---------------------------
# Aggregation helpers
# ---------------------------
def build_global_llm(results):
    g = {"cls": set(), "fn": set(), "hk": set(), "ax": set(), "entry": set(), "flow": [], "sink": []}

    for file in results:
        path = file.get("file", "")
        data = file.get("analysis", {}).get("llm", {})

        for c in data.get("cls", []):
            g["cls"].add(c)
        for f in data.get("fn", []):
            g["fn"].add(f)
        for h in data.get("hk", []):
            g["hk"].add(h)
            g["entry"].add(h)
        for a in data.get("ax", []):
            g["ax"].add(str(a))
            g["flow"].append({"type": "ajax", "ep": a, "file": path})
        for l in data.get("lg", []):
            s = str(l).lower()
            if "wpdb" in s or "database" in s:
                g["sink"].append({"type": "db", "file": path})
            if "cookie" in s:
                g["sink"].append({"type": "cookie", "file": path})

    return {
        "cls": sorted(list(g["cls"])),
        "fn": sorted(list(g["fn"])),
        "hk": sorted(list(g["hk"])),
        "ax": sorted(list(g["ax"])),
        "entry": sorted(list(g["entry"])),
        "flow": g["flow"],
        "sink": g["sink"],
    }


def build_doc(results):
    doc = []
    for r in results:
        d = r.get("analysis", {}).get("doc", {})
        llm = r.get("analysis", {}).get("llm", {})
        doc.append({
            "file": r.get("file", ""),
            "summary": d.get("summary", ""),
            "features": d.get("features", []),
            "notes": d.get("notes", []),
            "hooks": llm.get("hk", []),
            "functions": llm.get("fn", []),
            "ajax": llm.get("ax", []),
        })
    return doc


# ---------------------------
# Ultra-minimization for LLM
# ---------------------------
def _min_file_ultra(entry):
    file = entry.get("file", "")
    analysis = entry.get("analysis", {}) or {}
    llm = analysis.get("llm", {}) or {}
    doc = analysis.get("doc", {}) or {}

    summary = (doc.get("summary") or "").strip()
    if len(summary) > MIN_SUMMARY_LEN:
        summary = summary.split(".")[0][:MIN_SUMMARY_LEN] + "..."

    keywords = _top_keywords([summary] + (doc.get("features") or []) + llm.get("lg", []), n=6)

    return {
        "f": file,
        "s": _truncate(_mask_secrets_in_text(summary), MIN_SUMMARY_LEN),
        "k": keywords,
        "fn": _sample_list(llm.get("fn", []), MAX_SAMPLE),
        "hk": _sample_list(llm.get("hk", []), MAX_SAMPLE),
        "ax": _sample_list(llm.get("ax", []), MAX_SAMPLE),
    }


def minimize_for_llm(final):
    llm = final.get("llm", {}) or {}
    doc = final.get("doc", []) or []
    results = final.get("results", []) or []

    out = {
        "t": final.get("type", ""),
        "n": final.get("files", 0),
        "c": {
            "classes": len(llm.get("cls", []) or []),
            "functions": len(llm.get("fn", []) or []),
            "hooks": len(llm.get("hk", []) or []),
            "ajax": len(llm.get("ax", []) or []),
        },
        "samples": {
            "fn": _sample_list(llm.get("fn", []), MAX_SAMPLE),
            "hk": _sample_list(llm.get("hk", []), MAX_SAMPLE),
            "ax": _sample_list(llm.get("ax", []), MAX_SAMPLE),
        },
        "flow": [f.get("ep") for f in (llm.get("flow") or [])[:MAX_SAMPLE]],
        "sinks": list({s.get("type") for s in (llm.get("sink") or []) if s.get("type")})[:MAX_SAMPLE],
        "docs": [{"f": d.get("file", ""), "s": _truncate((d.get("summary") or "").split(".")[0], MIN_SUMMARY_LEN)} for d in doc[:MAX_SAMPLE]],
        "files": [_min_file_ultra(r) for r in results[: MAX_SAMPLE * 10]]  # cap number of detailed file entries
    }
    out["_meta"] = {"reduced": True, "generated_at": datetime.utcnow().isoformat() + "Z", "original_files": len(results)}
    return out


# ---------------------------
# Save outputs
# ---------------------------
def save_output(data):
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save full (optional)
    if SAVE_FULL:
        try:
            full_path = out_dir / "result_full.json"
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logging.info("Saved full result to %s", full_path)
        except Exception:
            logging.exception("Failed to save full result")

    # Save reduced (backwards compatible)
    try:
        reduced = minimize_for_llm(data)
        reduced_path = out_dir / "result.min.json"
        with open(reduced_path, "w", encoding="utf-8") as f:
            json.dump(reduced, f, separators=(",", ":"), ensure_ascii=False)
        # also write a 'result.json' for compatibility (same as min)
        compat_path = out_dir / "result.json"
        with open(compat_path, "w", encoding="utf-8") as f:
            json.dump(reduced, f, separators=(",", ":"), ensure_ascii=False)
        logging.info("Saved minimized result to %s and %s", reduced_path, compat_path)
    except Exception:
        logging.exception("Failed to save minimized result")


# ---------------------------
# Pipeline
# ---------------------------
def run_analysis(input_path):
    logging.info("1) Detect input")
    input_type = detect_input(input_path)

    logging.info("2) Extract")
    project_dir = extract_input(input_path, WORKSPACE)

    logging.info("3) Scan")
    files = scan_codebase(project_dir)
    logging.info("Found %d files", len(files))

    results = []
    for f in files:
        p = Path(f)
        analysis = analyze_file(p)
        results.append({"file": str(p), "analysis": analysis})

    final = {
        "type": input_type,
        "files": len(results),
        "llm": build_global_llm(results),
        "doc": build_doc(results),
        "results": results
    }

    save_output(final)

    try:
        html_path = generate_html_doc(final)
        logging.info("Documentation generated: %s", html_path)
    except Exception:
        logging.exception("Failed to generate HTML documentation")

    return final


# ---------------------------
# CLI
# ---------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logging.error("Usage: python main.py <input_path>")
        sys.exit(2)

    run_analysis(sys.argv[1])
