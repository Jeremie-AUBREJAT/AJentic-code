import requests
import json
import re

DEFAULT_API = "http://127.0.0.1:5000/v1/chat/completions"


def clean_json(text):
    if not text:
        return None

    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


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

Extraction rules (CRITICAL — FOLLOW EXACTLY):

1) "cls": ONLY PHP classes defined with:
   - class X
   - class X extends Y
   - abstract class X
   - final class X
   DO NOT include:
   - CSS classes
   - HTML classes
   - JS objects (e.g. dtx)
   - DOM classes
   - strings
   - variables

2) "fn": ONLY PHP functions or methods:
   - function x()
   - public function x()
   - private function x()
   - protected function x()
   - static function x()
   DO NOT include:
   - ANY JavaScript functions
   - ANY jQuery handlers
   - ANY callbacks
   - ANY arrow functions
   - ANY DOM events
   - ANY HTML attributes
   - ANY JS object methods (e.g. dtx.init, dtx.get, dtx.set, dtx.guid, dtx.obfuscate)
   - ANY generic names like current_url, get, set, guid, referrer, obfuscate, replaceAll, updateOption, validKey
   - ANY strings

3) "hk": ALL WordPress hooks used in:
   - add_action("hook_name", ...)
   - add_filter("hook_name", ...)
   - remove_action(...)
   - remove_filter(...)
   - apply_filters("hook_name", ...)
   - do_action("hook_name", ...)
   - add_shortcode("shortcode_name", ...)
   Extract ONLY the hook/shortcode name.
   DO NOT include:
   - comments
   - sentences
   - UI labels
   - JS strings
   - HTML
   - DOM events like change, click, keyup, input
   - ANY pattern with "*" (e.g. wpcf7_validate_dynamic_*)

4) "ax": ALL AJAX endpoints:
   - wp_ajax_*
   - wp_ajax_nopriv_*
   DO NOT include:
   - jQuery AJAX calls
   - DOM manipulation
   - JS code
   - includes
   - strings
   - plain "wpcf7dtx" (this is NOT an AJAX endpoint)

5) IGNORE COMPLETELY:
   - CSS
   - HTML
   - JS DOM manipulation
   - jQuery selectors ($(...))
   - JS code blocks
   - comments
   - UI text
   - includes / require
   - full lines of code that are not identifiers
   - any non‑PHP syntax

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
