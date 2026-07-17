# =====================================================================
# nssm_services.ps1 — Création des services Windows (NSSM) du kit DREVM
# ---------------------------------------------------------------------
# Services créés :
#   DrevmAiAdvisor  → drevm_ai_advisor.py --loop 15  (positions -> Claude -> Telegram)
#
# Prérequis :
#   - NSSM installé et dans le PATH (https://nssm.cc) — déjà utilisé pour saasDrevmBot
#   - Python installé (adapter $PythonExe si besoin)
#   - .env rempli à côté de drevm_ai_advisor.py
#
# Usage : PowerShell ADMIN -> .\nssm_services.ps1
# Gestion : nssm start|stop|restart DrevmAiAdvisor  |  nssm edit DrevmAiAdvisor
# =====================================================================

$ErrorActionPreference = "Stop"

# ── Config (à adapter) ────────────────────────────────────────────────
$PythonExe  = "C:\Python311\python.exe"                 # chemin Python du VPS
$KitRoot    = Split-Path -Parent $PSScriptRoot
$AdvisorPy  = Join-Path $KitRoot "05_Python\drevm_ai_advisor.py"
$LogDir     = Join-Path $KitRoot "logs"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# ── Vérifications ─────────────────────────────────────────────────────
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Host "❌ NSSM introuvable dans le PATH." -ForegroundColor Red; exit 1
}
if (-not (Test-Path $PythonExe)) {
    Write-Host "❌ Python introuvable : $PythonExe (adapter la variable)" -ForegroundColor Red; exit 1
}
if (-not (Test-Path $AdvisorPy)) {
    Write-Host "❌ Script introuvable : $AdvisorPy" -ForegroundColor Red; exit 1
}

# ── Service DrevmAiAdvisor ────────────────────────────────────────────
$svc = "DrevmAiAdvisor"
Write-Host "🔧 Installation du service $svc ..."

nssm stop   $svc 2>$null
nssm remove $svc confirm 2>$null

nssm install $svc $PythonExe "`"$AdvisorPy`" --loop 15"
nssm set $svc AppDirectory   (Split-Path $AdvisorPy)
nssm set $svc AppStdout      (Join-Path $LogDir "advisor_out.log")
nssm set $svc AppStderr      (Join-Path $LogDir "advisor_err.log")
nssm set $svc AppRotateFiles 1
nssm set $svc AppRotateBytes 1048576          # rotation à 1 Mo
nssm set $svc Start          SERVICE_AUTO_START
nssm set $svc AppRestartDelay 30000           # 30s avant redémarrage auto

nssm start $svc
Write-Host "✅ $svc installé et démarré." -ForegroundColor Green
Write-Host "   Logs : $LogDir"
Write-Host "   Gestion : nssm restart $svc | nssm edit $svc"
