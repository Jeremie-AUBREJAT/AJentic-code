import requests
import json
import re

DEFAULT_API = "http://127.0.0.1:5000/v1/chat/completions"


# -------------------------------------------------
# Extract JSON from LLM output
# -------------------------------------------------
def clean_json(text):
    if not text:
        return None

    # remove markdown fences
    text = text.replace("```json", "").replace("```", "").strip()

    # extract first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


# -------------------------------------------------
# Ask LLM with strong anti‑hallucination prompt
# -------------------------------------------------
def ask_llm(code, api_url=DEFAULT_API):

    prompt = f"""
Analyze this WordPress plugin file.

Return STRICT JSON with this schema:

{{
  "llm": {{
    "lang": "",
    "cls": [],
    "fn": [],
    "hk": [],
    "ax": []
  }},
  "doc": {{
    "summary": ""
  }}
}}

Extraction rules (IMPORTANT):

- "cls": ONLY PHP classes defined with "class X" (no CSS classes, no HTML classes, no JS objects)
- "fn": ONLY PHP functions or methods (no JS functions, no jQuery handlers, no callbacks)
- "hk": ONLY WordPress hooks used in add_action() or add_filter()
- "ax": ONLY AJAX endpoints registered via wp_ajax_* or wp_ajax_nopriv_*

IGNORE COMPLETELY:
- CSS classes (e.g. .button-secondary)
- HTML attributes (class="", id="")
- jQuery selectors ($(...))
- DOM manipulation
- JS code blocks
- comments
- UI text
- includes / require
- full lines of code that are not identifiers

Return JSON only.

CODE:
{code}
"""

    payload = {
        "messages": [
            {
                "role": "system",
                "content": "WordPress plugin static analyzer. Output strict JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.0,
        "max_tokens": 4096
    }

    try:
        r = requests.post(api_url, json=payload, timeout=1200)
        r.raise_for_status()
        data = r.json()
        raw = data["choices"][0]["message"]["content"]

    except Exception as e:
        return {
            "error": "api_error",
            "details": str(e)
        }

    cleaned = clean_json(raw)

    try:
        return json.loads(cleaned)
    except Exception:
        return {
            "error": "invalid_json",
            "raw": raw
        }
