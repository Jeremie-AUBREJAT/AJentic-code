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


def ask_llm(prompt, api_url=DEFAULT_API):

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
        "temperature": 0.1,
        "max_tokens": 8192
    }

    try:

        r = requests.post(
            api_url,
            json=payload,
            timeout=1200
        )

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