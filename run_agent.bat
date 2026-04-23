@echo off
set VENV_DIR=.venv

echo ===========================
echo  Agent LLM - Bootstrap
echo ===========================

:: 1. Create venv if not exists
IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Creation environnement virtuel...

    python -m venv %VENV_DIR%

    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Python venv creation failed
        pause
        exit /b
    )
)

:: 2. Activate venv
call %VENV_DIR%\Scripts\activate

:: 3. Upgrade pip (important)
python -m pip install --upgrade pip

:: 4. Install dependencies
IF EXIST requirements.txt (
    echo [INFO] Installation dependances...
    pip install -r requirements.txt
) ELSE (
    echo [WARN] requirements.txt introuvable
)

:: 5. Launch agent
echo [INFO] Lancement agent...
python main.py %*

pause