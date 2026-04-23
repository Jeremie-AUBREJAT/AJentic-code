from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
import shutil
import os
import webbrowser
import threading

from main import run_analysis

app = FastAPI()

UPLOAD_DIR = "workspace/upload"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ouvrir navigateur automatiquement
def open_browser():
    webbrowser.open("http://127.0.0.1:9000")


@app.on_event("startup")
def startup_event():
    threading.Timer(1.5, open_browser).start()


@app.get("/", response_class=HTMLResponse)
def index():
    with open("web/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/upload")
async def upload(file: UploadFile = File(...)):

    if not file.filename:
        return {"error": "No file uploaded"}

    filepath = os.path.join(UPLOAD_DIR, file.filename)

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        result = run_analysis(filepath)

        return {
            "status": "success",
            "file": file.filename,
            "analysis": result
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }