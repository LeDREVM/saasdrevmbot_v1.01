@echo off
REM ========================================================
REM  DREVM - Orchestrateur prep session NY (LOCAL, sans n8n)
REM  Declenche tous les jours ouvres a 3h Guadeloupe (07:00 UTC).
REM  Prerequis lances : backend (:8000) + screenshot-service (:3001).
REM ========================================================

cd /d "%~dp0\.."

REM Active le venv backend si present (fournit aussi backend\.env pour le secret)
if exist backend\.venv\Scripts\activate.bat (
    call backend\.venv\Scripts\activate.bat
)

echo Lancement de l'orchestrateur (mode daemon)...
echo Ctrl+C pour arreter.
echo.

python scripts\ny_morning_prep.py --daemon

pause
