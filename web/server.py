from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
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
progress_state = {"current": 0, "total": 1, "zip_path": ""}


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
def background_analysis(input_path, provider, model, api_key, endpoint, agent):
    zip_path = run_analysis(
        input_path,
        provider=provider,
        model=model,
        api_key=api_key,
        endpoint=endpoint,
        agent=agent,
        progress_state=progress_state
    )
    progress_state["zip_path"] = zip_path


# ---------------------------------------------------------
# UPLOAD (LANCE L'ANALYSE ET RÉPOND IMMÉDIATEMENT)
# ---------------------------------------------------------
@app.post("/upload")
async def upload(
    file: UploadFile | None = File(None),
    url: str | None = Form(None),
    provider: str = Form(...),
    model: str = Form(None),
    api_key: str = Form(None),
    endpoint: str = Form(None),
    agent: str = Form("default")
):

    # MODE WEB_AUDIT → pas de fichier, seulement une URL
    if agent == "web_audit":
        if not url:
            return {"status": "error", "message": "URL manquante pour web_audit"}
        input_path = url

    else:
        # MODE NORMAL → fichier obligatoire
        if not file or not file.filename:
            return {"status": "error", "message": "Aucun fichier uploadé"}

        filepath = os.path.join(UPLOAD_DIR, file.filename)

        try:
            with open(filepath, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            return {"status": "error", "message": f"Erreur sauvegarde fichier: {e}"}

        input_path = filepath

    # Reset progression
    progress_state["current"] = 0
    progress_state["total"] = 1
    progress_state["zip_path"] = ""

    # Lancer l'analyse en thread
    t = threading.Thread(
        target=background_analysis,
        args=(input_path, provider, model, api_key, endpoint, agent),
        daemon=True
    )
    t.start()

    return {"status": "started"}


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


# ---------------------------------------------------------
# DOWNLOAD DU ZIP
# ---------------------------------------------------------
@app.get("/download")
def download(zip_path: str):
    if not os.path.exists(zip_path):
        return {"status": "error", "message": "ZIP not found"}

    return FileResponse(
        zip_path,
        filename=os.path.basename(zip_path),
        media_type="application/zip"
    )
