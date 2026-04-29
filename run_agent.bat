@echo off

set VENV_DIR=.venv

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    python -m venv %VENV_DIR%
)

call %VENV_DIR%\Scripts\activate

pip install -r requirements.txt

echo Lancement serveur...


uvicorn web.server:app --host 127.0.0.1 --port 9000 --workers 1

pause