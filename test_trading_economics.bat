@echo off
echo ========================================
echo Test du systeme Trading Economics
echo ========================================
echo.

REM Activer l'environnement virtuel si disponible
if exist .venv\Scripts\activate.bat (
    echo Activation de l'environnement virtuel...
    call .venv\Scripts\activate.bat
)

REM Installer les dependances si necessaire
echo Verification des dependances...
pip install -q requests beautifulsoup4 lxml schedule python-dotenv

echo.
echo Execution des tests...
echo.
python test_trading_economics.py

echo.
echo ========================================
echo Tests termines
echo ========================================
pause
