@echo off
REM Script de déploiement Netlify pour SaaS DrevmBot (Windows)
REM Usage: deploy-netlify.bat

setlocal enabledelayedexpansion

echo ╔════════════════════════════════════════════════════════╗
echo ║   🚀 DÉPLOIEMENT NETLIFY - SaaS DrevmBot 🚀           ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Vérifier si on est dans le bon répertoire
if not exist "frontend" (
    echo ❌ Le dossier 'frontend' n'existe pas. Êtes-vous dans le bon répertoire ?
    exit /b 1
)

echo ✅ Répertoire du projet trouvé

REM Vérifier si Node.js est installé
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Node.js n'est pas installé. Installez-le depuis https://nodejs.org/
    exit /b 1
)

for /f "tokens=*" %%i in ('node -v') do set NODE_VERSION=%%i
echo ✅ Node.js !NODE_VERSION! détecté

REM Vérifier si npm est installé
where npm >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ npm n'est pas installé
    exit /b 1
)

for /f "tokens=*" %%i in ('npm -v') do set NPM_VERSION=%%i
echo ✅ npm !NPM_VERSION! détecté

REM Se déplacer dans le dossier frontend
cd frontend

REM Vérifier si package.json existe
if not exist "package.json" (
    echo ❌ package.json n'existe pas dans le dossier frontend
    cd ..
    exit /b 1
)

echo ✅ package.json trouvé

REM Installer les dépendances
echo.
echo ▶ Installation des dépendances...
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo ❌ L'installation des dépendances a échoué
    cd ..
    exit /b 1
)
echo ✅ Dépendances installées

REM Vérifier si .env existe
if not exist ".env" (
    if exist "env.template" (
        echo ⚠️  .env n'existe pas, création depuis env.template...
        copy env.template .env >nul
        echo ✅ .env créé depuis env.template
        echo ⚠️  N'oubliez pas de configurer VITE_API_URL dans .env ou dans Netlify !
    ) else (
        echo ⚠️  .env n'existe pas. Les variables d'environnement doivent être configurées dans Netlify.
    )
)

REM Build de production
echo.
echo ▶ Build de production...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Le build a échoué
    cd ..
    exit /b 1
)

echo ✅ Build réussi !

REM Vérifier si le dossier build existe
if not exist "build" (
    echo ❌ Le dossier 'build' n'a pas été créé
    cd ..
    exit /b 1
)

echo ✅ Dossier build créé

REM Vérifier si Netlify CLI est installé
where netlify >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ⚠️  Netlify CLI n'est pas installé
    echo.
    echo Pour déployer, vous avez 3 options :
    echo.
    echo 1️⃣  Installer Netlify CLI et déployer :
    echo    npm install -g netlify-cli
    echo    netlify login
    echo    netlify deploy --prod
    echo.
    echo 2️⃣  Déployer manuellement :
    echo    - Aller sur https://app.netlify.com/
    echo    - Glisser-déposer le dossier 'frontend\build'
    echo.
    echo 3️⃣  Déployer via Git (Recommandé) :
    echo    - Pusher le code sur GitHub/GitLab
    echo    - Connecter le repo à Netlify
    echo    - Netlify déploiera automatiquement
    echo.
    cd ..
    exit /b 0
)

echo ✅ Netlify CLI détecté

REM Demander confirmation pour le déploiement
echo.
echo ═══════════════════════════════════════════════════════
echo 🚀 Prêt à déployer sur Netlify !
echo ═══════════════════════════════════════════════════════
echo.
set /p DEPLOY="Voulez-vous déployer maintenant ? (o/N) "

if /i "!DEPLOY!"=="o" (
    echo.
    echo ▶ Déploiement en cours...
    
    call netlify deploy --prod
    
    if !ERRORLEVEL! EQU 0 (
        echo.
        echo ╔════════════════════════════════════════════════════════╗
        echo ║   ✅ DÉPLOIEMENT RÉUSSI ! ✅                          ║
        echo ╚════════════════════════════════════════════════════════╝
        echo.
        echo ✅ Site déployé sur : https://saasdrevmbot.netlify.app/
        echo.
        echo 📋 Prochaines étapes :
        echo   1. Vérifier le site en production
        echo   2. Configurer VITE_API_URL dans Netlify (si pas fait^)
        echo   3. Déployer le backend
        echo   4. Tester les fonctionnalités
        echo.
    ) else (
        echo ❌ Le déploiement a échoué
        cd ..
        exit /b 1
    )
) else (
    echo.
    echo ⚠️  Déploiement annulé
    echo.
    echo Pour déployer plus tard, exécutez :
    echo   cd frontend
    echo   netlify deploy --prod
    echo.
)

cd ..

echo ═══════════════════════════════════════════════════════
echo ✨ Script terminé avec succès !
echo ═══════════════════════════════════════════════════════

endlocal
