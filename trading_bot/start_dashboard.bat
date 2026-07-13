@echo off
REM Lance le dashboard NY Smart Money — http://localhost:8050
cd /d "%~dp0"
python -m uvicorn dashboard:app --port 8050
pause
