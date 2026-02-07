@echo off
echo ========================================
echo Demarrage du Worker Calendrier Quotidien
echo ========================================
echo.

REM Activer l'environnement virtuel si disponible
if exist .venv\Scripts\activate.bat (
    echo Activation de l'environnement virtuel...
    call .venv\Scripts\activate.bat
)

echo.
echo Configuration:
echo - Envoi quotidien: 7h00 du matin
echo - Alertes: Toutes les 15 minutes
echo.
echo Appuyez sur Ctrl+C pour arreter le worker
echo.

python start_daily_worker.py

pause
