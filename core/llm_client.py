import requests
import json
import re


def clean_json(text):
    if not text:
        return None

    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


# ---------------------------------------------------------
#  UNIVERSAL RESPONSE EXTRACTOR
# ---------------------------------------------------------
def extract_content(provider, data):
    """
    Normalise la réponse selon le provider.
    Retourne toujours du texte brut.
    """

    try:
        if provider == "openai" or provider == "mistral" or provider == "local-openai":
            return data["choices"][0]["message"]["content"]

        if provider == "anthropic":
            return data["content"][0]["text"]

        if provider == "google":
            return data["candidates"][0]["content"][0]["text"]

        if provider == "ollama":
            return data["message"]["content"]

        if provider == "kobold" or provider == "oobabooga":
            return data["choices"][0]["message"]["content"]

    except Exception:
        return None

    return None


# ---------------------------------------------------------
#  UNIVERSAL LLM CLIENT
# ---------------------------------------------------------
def ask_llm(code, provider, model=None, api_key=None, endpoint=None):

    # -----------------------------------------------------
    # 1) Construire le prompt
    # -----------------------------------------------------
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
   DO NOT include ANY JavaScript functions, jQuery handlers, callbacks, arrow functions, DOM events, HTML attributes, JS object methods, generic names, or strings.

3) "hk": ALL WordPress hooks used in:
   - add_action("hook_name", ...)
   - add_filter("hook_name", ...)
   - remove_action(...)
   - remove_filter(...)
   - apply_filters("hook_name", ...)
   - do_action("hook_name", ...)
   - add_shortcode("shortcode_name", ...)
   Extract ONLY the hook/shortcode name.

4) "ax": ALL AJAX endpoints:
   - wp_ajax_*
   - wp_ajax_nopriv_*

5) IGNORE COMPLETELY:
   - CSS, HTML, JS DOM manipulation, jQuery, comments, UI text, includes, non‑PHP syntax.

Return JSON only.

CODE:
{code}
"""

    # -----------------------------------------------------
    # 2) Construire le payload universel
    # -----------------------------------------------------
    messages = [
        {"role": "system", "content": "WordPress plugin static analyzer. Output strict JSON only."},
        {"role": "user", "content": prompt}
    ]

    payload = {}
    headers = {}

    # -----------------------------------------------------
    # 3) ROUTING CLOUD PROVIDERS
    # -----------------------------------------------------

    # ---------- OPENAI ----------
    if provider == "openai":
        endpoint = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": 4096
        }

    # ---------- ANTHROPIC ----------
    elif provider == "anthropic":
        endpoint = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096
        }

    # ---------- GOOGLE ----------
    elif provider == "google":
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}]
        }

    # ---------- MISTRAL ----------
    elif provider == "mistral":
        endpoint = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": messages
        }

    # -----------------------------------------------------
    # 4) ROUTING LOCAL PROVIDERS
    # -----------------------------------------------------
    elif provider == "local":

        # Détection automatique du backend selon l’URL
        url = endpoint.lower()

        # ----- OOBABOOGA -----
        if "oobabooga" in url or "text-generation-webui" in url:
            provider = "oobabooga"
            payload = {"messages": messages}

        # ----- KOBOLDCPP -----
        elif "kobold" in url:
            provider = "kobold"
            payload = {"messages": messages}

        # ----- OLLAMA -----
        elif "ollama" in url:
            provider = "ollama"
            payload = {
                "model": model,
                "messages": messages
            }

        # ----- LM STUDIO / GPT4ALL / OPENAI-LIKE -----
        else:
            provider = "local-openai"
            payload = {
                "model": model,
                "messages": messages
            }

    # -----------------------------------------------------
    # 5) APPEL API
    # -----------------------------------------------------
    try:
        r = requests.post(endpoint, json=payload, headers=headers, timeout=1200)
        r.raise_for_status()
        data = r.json()

    except Exception as e:
        return {"error": "api_error", "details": str(e)}

    # -----------------------------------------------------
    # 6) EXTRACTION DU TEXTE
    # -----------------------------------------------------
    raw = extract_content(provider, data)

    if not raw:
        return {"error": "empty_response", "raw": data}

    # -----------------------------------------------------
    # 7) CLEAN JSON
    # -----------------------------------------------------
    cleaned = clean_json(raw)

    try:
        return json.loads(cleaned)
    except Exception:
        return {"error": "invalid_json", "raw": raw}
