from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import shutil
import os
import webbrowser
import threading
import json
import time

from main import run_analysis

app = FastAPI()

UPLOAD_DIR = "workspace/upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# État global de progression
progress_state = {"current": 0, "total": 1}


# ---------------------------------------------------------
# OUVERTURE AUTOMATIQUE DU NAVIGATEUR
# ---------------------------------------------------------
def open_browser():
    webbrowser.open("http://127.0.0.1:9000")


@app.on_event("startup")
def startup_event():
    threading.Timer(1.5, open_browser).start()


# ---------------------------------------------------------
# PAGE HTML
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    with open("web/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------
# THREAD D'ANALYSE
# ---------------------------------------------------------
def background_analysis(filepath, provider, model, api_key, endpoint):
    # run_analysis mettra à jour progress_state
    run_analysis(
        filepath,
        provider=provider,
        model=model,
        api_key=api_key,
        endpoint=endpoint,
        progress_state=progress_state
    )


# ---------------------------------------------------------
# UPLOAD (LANCE L'ANALYSE ET RÉPOND IMMÉDIATEMENT)
# ---------------------------------------------------------
@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    provider: str = Form(...),
    model: str = Form(None),
    api_key: str = Form(None),
    endpoint: str = Form(None)
):

    if not file.filename:
        return {"status": "error", "message": "No file uploaded"}

    filepath = os.path.join(UPLOAD_DIR, file.filename)

    try:
        # Sauvegarde du fichier uploadé
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Reset de la progression
        progress_state["current"] = 0
        progress_state["total"] = 1  # sera mis à jour dans run_analysis

        # Lancer l'analyse en thread
        t = threading.Thread(
            target=background_analysis,
            args=(filepath, provider, model, api_key, endpoint),
            daemon=True
        )
        t.start()

        # Réponse immédiate
        return {
            "status": "started",
            "file": file.filename
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ---------------------------------------------------------
# SSE : STREAM DE PROGRESSION
# ---------------------------------------------------------
@app.get("/progress")
def progress_stream():

    def event_stream():
        last_sent = ""
        while True:
            data = json.dumps(progress_state)
            if data != last_sent:
                yield f"data: {data}\n\n"
                last_sent = data
            time.sleep(0.3)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
