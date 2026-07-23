@echo off
REM ===========================================================================
REM  uninstall-autostart.bat  -  Retire le demarrage automatique des backends
REM ===========================================================================
setlocal
set "LINK=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\saasDrevmBot Backends.lnk"

if exist "%LINK%" (
    del "%LINK%"
    echo [OK] Demarrage automatique desactive.
) else (
    echo [i] Aucun demarrage automatique installe.
)
echo.
pause
