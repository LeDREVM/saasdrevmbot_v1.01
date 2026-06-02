@echo off
REM ===========================================================================
REM  start-console.bat  -  Lance la console NY Session Bot (Windows + MT5)
REM  Le terminal MT5 doit etre ouvert/connecte avec Algo Trading active.
REM ===========================================================================

cd /d "%USERPROFILE%\goldyxbotdrevm\ny_session_interface"

REM --- Alertes Telegram (optionnel) : decommente et renseigne ---
REM set TELEGRAM_BOT_TOKEN=123456:ABC...
REM set TELEGRAM_CHAT_ID=987654321

REM --- Protection des commandes par token (optionnel) ---
REM set API_TOKEN=change-me

if exist ".venv\Scripts\python.exe" (
    .venv\Scripts\python.exe api.py
) else (
    python api.py
)

pause
