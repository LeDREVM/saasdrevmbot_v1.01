@echo off
REM ===========================================================================
REM  install-autostart.bat  -  Lance les backends au demarrage de Windows
REM  Cree un raccourci vers start-all.bat dans le dossier Demarrage de
REM  l'utilisateur courant (shell:startup). Aucun droit admin requis.
REM ===========================================================================
setlocal
set "TARGET=%~dp0start-all.bat"
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LINK=%STARTUP%\saasDrevmBot Backends.lnk"

echo.
echo Installation du demarrage automatique...
echo   Cible   : %TARGET%
echo   Raccourci: %LINK%
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$s = $ws.CreateShortcut('%LINK%');" ^
  "$s.TargetPath = '%TARGET%';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.WindowStyle = 7;" ^
  "$s.Description = 'Demarre les backends saasDrevmBot (Express :3000 + FastAPI :8000)';" ^
  "$s.Save()"

if exist "%LINK%" (
    echo [OK] Demarrage automatique installe.
    echo      Les backends se lanceront a la prochaine ouverture de session Windows.
    echo      Pour desactiver : lance uninstall-autostart.bat
) else (
    echo [ERREUR] Impossible de creer le raccourci.
)
echo.
pause
