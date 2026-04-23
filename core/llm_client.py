import requests
import json
import re

OOBABOOGA_API = "http://127.0.0.1:5000/v1/chat/completions"


def clean_json(text):
    """
    Extrait uniquement JSON valide depuis réponse LLM
    """

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
                    "Tu es un analyseur de code WordPress. "
                    "Tu réponds UNIQUEMENT en JSON valide. "
                    "Aucun texte, aucun markdown."
                )
            },
            {"role": "user", "content": prompt}
        ],
        "mode": "instruct",
        "temperature": 0.2,
        "max_tokens": 2000
    }

    r = requests.post(OOBABOOGA_API, json=payload)
    data = r.json()

    raw = data["choices"][0]["message"]["content"]

    cleaned = clean_json(raw)

    try:
        return json.loads(cleaned)
    except:
        return {
            "error": "invalid_json",
            "raw_response": raw
        }