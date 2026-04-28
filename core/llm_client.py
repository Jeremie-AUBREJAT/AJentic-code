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

Extraction rules (CRITICAL — FOLLOW EXACTLY):

1) "cls": ONLY PHP classes defined with:
   - class X
   - class X extends Y
   - abstract class X
   - final class X
   DO NOT include:
   - CSS classes
   - HTML classes
   - JS objects
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
   - JavaScript functions
   - jQuery handlers
   - callbacks
   - arrow functions
   - DOM events
   - HTML attributes
   - strings
   - JS object methods (e.g. dtx.init)

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

4) "ax": ALL AJAX endpoints:
   - wp_ajax_*
   - wp_ajax_nopriv_*
   DO NOT include:
   - jQuery AJAX calls
   - DOM manipulation
   - JS code
   - includes
   - strings

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
