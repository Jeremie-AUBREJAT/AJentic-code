import requests
import json
import re

OOBABOOGA_API = "http://127.0.0.1:5000/v1/chat/completions"


def clean_json(text):

    if not text:
        return None

    text = text.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if match:
        return match.group(0)

    return text


def ask_llm(prompt):

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es un analyseur de code WordPress expert. "
                    "Tu dois répondre UNIQUEMENT en JSON valide strict."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "mode": "instruct",
        "temperature": 0.2,
        "max_tokens": 8192
    }

    r = requests.post(OOBABOOGA_API, json=payload, timeout=1200)

    try:
        data = r.json()
        raw = data["choices"][0]["message"]["content"]
    except:
        return {"error": "api_error"}

    cleaned = clean_json(raw)

    try:
        return json.loads(cleaned)
    except:
        return {
            "error": "invalid_json",
            "raw_response": raw
        }