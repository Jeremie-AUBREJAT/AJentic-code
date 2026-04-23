@echo off

set VENV_DIR=.venv

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    python -m venv %VENV_DIR%
)

call %VENV_DIR%\Scripts\activate

pip install -r requirements.txt

echo Lancement serveur...

uvicorn web.server:app --reload --port 9000

pause