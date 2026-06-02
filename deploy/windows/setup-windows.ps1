# =============================================================================
#  setup-windows.ps1  —  Déploiement VPS Windows (TRADING RÉEL via MetaTrader5)
#
#  Prérequis (à faire AVANT) :
#   1. Installer Python 3.11+ (cocher "Add Python to PATH").
#   2. Installer Git for Windows.
#   3. Installer le terminal MetaTrader 5 de Fusion Markets, s'y connecter,
#      et activer "Algo Trading" (bouton en haut, doit être vert).
#
#  Lancement :  clic droit > "Exécuter avec PowerShell"
#               (ou)  powershell -ExecutionPolicy Bypass -File deploy\windows\setup-windows.ps1
# =============================================================================
$ErrorActionPreference = "Stop"

$Repo   = "https://github.com/LeDREVM/saasdrevmbot_v1.01.git"
$Branch = "claude/trading-session-performance-6Ex86"
$Dir    = Join-Path $env:USERPROFILE "goldyxbotdrevm"

function Step($m) { Write-Host "`n>> $m" -ForegroundColor Cyan }

Step "Vérification de Python et Git"
python --version
git --version

Step "Clone / mise à jour ($Branch)"
if (Test-Path (Join-Path $Dir ".git")) {
    git -C $Dir fetch origin $Branch
    git -C $Dir checkout $Branch
    git -C $Dir pull origin $Branch
} else {
    git clone -b $Branch $Repo $Dir
}

Set-Location (Join-Path $Dir "ny_session_interface")

Step "Création de l'environnement Python"
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pip install MetaTrader5

Write-Host "`n=============================================================" -ForegroundColor Yellow
Write-Host " IMPORTANT avant de trader en reel :" -ForegroundColor Yellow
Write-Host "  - Remplace ny_session_interface\trading_ny_session.py par TA" -ForegroundColor Yellow
Write-Host "    vraie Trading Bible (la version livree est un placeholder)." -ForegroundColor Yellow
Write-Host "  - Le terminal MT5 doit etre ouvert, connecte, Algo Trading ON." -ForegroundColor Yellow
Write-Host "  - DRY_RUN est ACTIF par defaut : aucun ordre reel tant que tu" -ForegroundColor Yellow
Write-Host "    ne le desactives pas depuis la console (avec confirmation)." -ForegroundColor Yellow
Write-Host "=============================================================" -ForegroundColor Yellow

Write-Host "`nLancer la console maintenant ? (O/N) " -NoNewline
if ((Read-Host) -match '^[OoYy]') {
    & .\.venv\Scripts\python.exe api.py
} else {
    Write-Host "Plus tard : double-clique deploy\windows\start-console.bat"
}
