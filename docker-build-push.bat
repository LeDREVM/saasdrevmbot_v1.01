@echo off
REM Script de build et push des images Docker vers Docker Hub (Windows)
REM Repository: ledrevm/goldyxrodgersbot

setlocal

REM Variables
set DOCKER_USERNAME=ledrevm
set IMAGE_NAME=goldyxrodgersbot
set VERSION=1.0.0
set LATEST_TAG=latest

echo 🐳 Build et Push Docker Images
echo ================================
echo Repository: %DOCKER_USERNAME%/%IMAGE_NAME%
echo Version: %VERSION%
echo.

REM Vérifier si connecté à Docker Hub
echo 📝 Vérification connexion Docker Hub...
docker info | findstr "Username: %DOCKER_USERNAME%" >nul
if errorlevel 1 (
    echo ⚠️  Non connecté à Docker Hub
    echo Connexion...
    docker login
)

echo ✅ Connecté à Docker Hub
echo.

REM Build Backend
echo 🔨 Build Backend Image...
docker build -t %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%VERSION% ./backend
docker tag %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%VERSION% %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%LATEST_TAG%

echo ✅ Backend image built
echo.

REM Build Frontend
echo 🔨 Build Frontend Image...
docker build -t %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%VERSION% ./frontend
docker tag %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%VERSION% %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%LATEST_TAG%

echo ✅ Frontend image built
echo.

REM Push Backend
echo 📤 Push Backend Image...
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%VERSION%
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%LATEST_TAG%

echo ✅ Backend image pushed
echo.

REM Push Frontend
echo 📤 Push Frontend Image...
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%VERSION%
docker push %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%LATEST_TAG%

echo ✅ Frontend image pushed
echo.

echo.
echo ✅ Toutes les images ont été poussées avec succès !
echo.
echo Images disponibles:
echo   - %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%VERSION%
echo   - %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%LATEST_TAG%
echo   - %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%VERSION%
echo   - %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%LATEST_TAG%
echo.
echo Pour utiliser:
echo   docker pull %DOCKER_USERNAME%/%IMAGE_NAME%:backend-%LATEST_TAG%
echo   docker pull %DOCKER_USERNAME%/%IMAGE_NAME%:frontend-%LATEST_TAG%
echo.

pause
