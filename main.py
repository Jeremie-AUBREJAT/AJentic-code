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


# ---------------------------------------------------------
# MASKING
# ---------------------------------------------------------
def _mask(s):
    if not s:
        return s
    s = re.sub(
        r"(api[_-]?key|secret|token)[\"'\s:=]+([A-Za-z0-9\-_]{8,})",
        r"\1=[REDACTED]",
        s,
        flags=re.I,
    )
    s = re.sub(r"\b[0-9a-fA-F]{32,}\b", "[HEX_REDACTED]", s)
    return s


# ---------------------------------------------------------
# NORMALISATION DU JSON LLM
# ---------------------------------------------------------
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
        "doc": {
            "summary": resp.get("doc", {}).get("summary", "")
        }
    }


# ---------------------------------------------------------
# ANALYSE D’UN FICHIER
# ---------------------------------------------------------
def analyze_file(path: Path, provider=None, model=None, api_key=None, endpoint=None):

    try:
        code = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"llm": {}, "doc": {"summary": f"read_error: {e}"}}

    if len(code) > MAX_FILE_SEND_BYTES:
        code = code[:MAX_FILE_SEND_BYTES] + "\n/* TRUNCATED */"

    code = _mask(code)

    resp = ask_llm(code, provider, model, api_key, endpoint)
    return _normalize(resp)


# ---------------------------------------------------------
# POST-PROCESSING GLOBAL
# ---------------------------------------------------------
def _postprocess_llm_aggregates(g):

    blacklist_classes = {"dtx", "wpcf7dtx_taggen"}

    blacklist_fn_prefix = ("dtx.",)
    blacklist_fn_exact = {"setTimeout"}

    blacklist_wp_generic = {
        "array_merge", "count", "empty", "implode", "in_array",
        "sanitize_text_field", "sanitize_textarea_field",
        "str_replace", "strval", "shortcode_parse_atts", "prop",
    }

    blacklist_cf7_generic = {
        "wpcf7_is_email", "wpcf7_is_number", "wpcf7_is_tel",
        "wpcf7_is_date", "wpcf7_count_code_units",
        "wpcf7_get_message", "wpcf7_get_hangover",
    }

    blacklist_hooks_prefix = ("document.",)
    blacklist_hooks_exact = {
        "post_meta_access", "post_meta_allow_all", "post_meta_allow_keys",
        "user_data_access", "user_data_allow_all", "user_data_allow_keys",
    }

    blacklist_ajax_prefix = ("wpcf7dtx_",)

    g["cls"] = {c for c in g["cls"] if c not in blacklist_classes}

    cleaned_fn = set()
    for f in g["fn"]:
        if f in blacklist_fn_exact:
            continue
        if any(f.startswith(p) for p in blacklist_fn_prefix):
            continue
        if f in blacklist_wp_generic:
            continue
        if f in blacklist_cf7_generic:
            continue
        cleaned_fn.add(f)
    g["fn"] = cleaned_fn

    cleaned_hooks = set()
    for h in g["hk"]:
        if h in blacklist_hooks_exact:
            continue
        if any(h.startswith(p) for p in blacklist_hooks_prefix):
            continue
        if "*" in h:
            continue
        cleaned_hooks.add(h)
    g["hk"] = cleaned_hooks

    cleaned_ax = set()
    for a in g["ax"]:
        if any(a.startswith(p) for p in blacklist_ajax_prefix):
            continue
        cleaned_ax.add(a)
    g["ax"] = cleaned_ax

    g["flow"] = [a for a in g["flow"] if a in g["ax"]]

    g["sink"] = list(set(g["sink"]))

    return g


# ---------------------------------------------------------
# AGRÉGATION GLOBALE
# ---------------------------------------------------------
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
            if (
                "wpdb" in s or "database" in s or "get_post_meta" in s or
                "get_user_meta" in s or "get_option" in s or "update_option" in s
            ):
                g["sink"].append("db")

    g = _postprocess_llm_aggregates(g)

    return {
        "cls": sorted(g["cls"]),
        "fn": sorted(g["fn"]),
        "hk": sorted(g["hk"]),
        "ax": sorted(g["ax"]),
        "flow": g["flow"],
        "sink": g["sink"],
    }


# ---------------------------------------------------------
# MINIMISATION POUR LLM
# ---------------------------------------------------------
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
        "_meta": {
            "reduced": True,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
    }


# ---------------------------------------------------------
# SAUVEGARDE
# ---------------------------------------------------------
def save_output(data):
    out = Path(OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)

    minimized = minimize_for_llm(data)

    (out / "result.min.json").write_text(
        json.dumps(minimized, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )

    (out / "result.json").write_text(
        json.dumps(minimized, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------
# PIPELINE PRINCIPAL (AVEC PROGRESS_STATE)
# ---------------------------------------------------------
def run_analysis(input_path, provider, model=None, api_key=None, endpoint=None, progress_state=None):

    input_type = detect_input(input_path)
    project_dir = extract_input(input_path, WORKSPACE)
    files = scan_codebase(project_dir)

    # Initialisation de la progression
    if progress_state is not None:
        progress_state["current"] = 0
        progress_state["total"] = len(files)

    results = []

    for f in files:
        p = Path(f)

        # Mise à jour de la progression
        if progress_state is not None:
            progress_state["current"] += 1

        results.append({
            "file": str(p),
            "analysis": analyze_file(
                p,
                provider=provider,
                model=model,
                api_key=api_key,
                endpoint=endpoint
            )
        })

    final = {
        "type": input_type,
        "files": len(results),
        "files_list": [str(r["file"]) for r in results],
        "llm": build_global_llm(results),
        "results": results,
    }

    save_output(final)
    generate_html_doc(final)

    return final


# ---------------------------------------------------------
# MODE CLI
# ---------------------------------------------------------
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python main.py <input_path>")
        exit(2)

    run_analysis(sys.argv[1], provider="local", progress_state={"current": 0, "total": 1})
