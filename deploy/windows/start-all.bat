@echo off
REM ===========================================================================
REM  start-all.bat  -  Demarre les 2 backends de saasDrevmBot
REM    - Express "GoldyXbOT"  -> http://localhost:3000  (dashboard correlation)
REM    - FastAPI "saasDrevmbot" -> http://localhost:8000 (alertes, scoring, config)
REM  A lancer AVANT d'ouvrir l'application desktop.
REM ===========================================================================
setlocal
cd /d "%~dp0\..\.."

echo.
echo ===========================================================
echo   saasDrevmBot - Demarrage des backends
echo ===========================================================
echo.

REM --- 1) Backend Express (port 3000) ---------------------------------------
echo [1/2] Backend Express GoldyXbOT (port 3000)...
if not exist "node_modules" (
    echo      Installation des dependances npm...
    call npm install --no-audit --no-fund
)
start "GoldyXbOT :3000" cmd /k "npm start"

REM --- 2) Backend FastAPI (port 8000) ---------------------------------------
echo [2/2] Backend FastAPI saasDrevmbot (port 8000)...
cd backend
if not exist ".venv\Scripts\python.exe" (
    echo      Creation de l'environnement virtuel Python...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    echo      Installation des dependances (peut prendre 1-2 min)...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)
start "saasDrevmbot API :8000" cmd /k ".venv\Scripts\uvicorn.exe main:app --host 0.0.0.0 --port 8000 --reload"
cd ..

echo.
echo ===========================================================
echo   Les 2 backends demarrent dans des fenetres separees.
echo   - Dashboard Express : http://localhost:3000
echo   - API FastAPI       : http://localhost:8000/api/docs
echo.
echo   Laisse ces fenetres OUVERTES puis lance l'app desktop.
echo   Pour arreter : ferme les deux fenetres.
echo ===========================================================
echo.
pause
