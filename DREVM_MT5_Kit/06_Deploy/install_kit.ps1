# =====================================================================
# install_kit.ps1 — Installation du DREVM MT5 Kit dans le dossier MQL5
# ---------------------------------------------------------------------
# Détecte le dossier de données MT5 (Fusion Markets) et copie :
#   01_Experts/*.mq5     -> MQL5\Experts\DREVM\
#   02_Indicators/*.mq5  -> MQL5\Indicators\DREVM\
#   03_Include/*.mqh     -> MQL5\Experts\DREVM\  (même dossier que les EAs)
#   04_Presets/*.set     -> MQL5\Presets\
# Puis rappelle les étapes manuelles (compilation, WebRequest).
#
# Usage : clic droit -> Exécuter avec PowerShell (sur le VPS Windows)
# =====================================================================

$ErrorActionPreference = "Stop"
$KitRoot = Split-Path -Parent $PSScriptRoot   # racine du kit (parent de 06_Deploy)

Write-Host "🎯 DREVM MT5 Kit — Installation" -ForegroundColor Cyan
Write-Host "Kit: $KitRoot`n"

# ── 1. Localiser le dossier de données MT5 ────────────────────────────
$terminalRoot = Join-Path $env:APPDATA "MetaQuotes\Terminal"
if (-not (Test-Path $terminalRoot)) {
    Write-Host "❌ Dossier MetaQuotes introuvable : $terminalRoot" -ForegroundColor Red
    Write-Host "   Lance MT5 au moins une fois, puis relance ce script."
    exit 1
}

# Prend l'instance la plus récemment modifiée contenant un dossier MQL5
$instance = Get-ChildItem $terminalRoot -Directory |
    Where-Object { Test-Path (Join-Path $_.FullName "MQL5") } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $instance) {
    Write-Host "❌ Aucune instance MT5 avec dossier MQL5 trouvée." -ForegroundColor Red
    exit 1
}

$MQL5 = Join-Path $instance.FullName "MQL5"
Write-Host "✅ Instance MT5 : $($instance.Name)"
Write-Host "   MQL5 : $MQL5`n"

# ── 2. Créer les dossiers cibles ──────────────────────────────────────
$expDir = Join-Path $MQL5 "Experts\DREVM"
$indDir = Join-Path $MQL5 "Indicators\DREVM"
$preDir = Join-Path $MQL5 "Presets"
foreach ($d in @($expDir, $indDir, $preDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

# ── 3. Copier les fichiers ────────────────────────────────────────────
function Copy-Kit($pattern, $dest, $label) {
    $files = Get-ChildItem $pattern -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        Copy-Item $f.FullName $dest -Force
        Write-Host "  📄 $($f.Name) -> $label"
    }
}

Write-Host "Copie des fichiers :"
Copy-Kit (Join-Path $KitRoot "01_Experts\*.mq5")    $expDir "Experts\DREVM"
Copy-Kit (Join-Path $KitRoot "03_Include\*.mqh")    $expDir "Experts\DREVM"
Copy-Kit (Join-Path $KitRoot "02_Indicators\*.mq5") $indDir "Indicators\DREVM"
Copy-Kit (Join-Path $KitRoot "04_Presets\*.set")    $preDir "Presets"

# ── 4. Rappels manuels ────────────────────────────────────────────────
Write-Host "`n✅ Fichiers installés." -ForegroundColor Green
Write-Host @"

📋 ÉTAPES MANUELLES RESTANTES :
  1. MT5 -> F4 (MetaEditor) -> ouvrir chaque .mq5 dans Experts\DREVM et Indicators\DREVM -> F7 (compiler)
  2. MT5 -> Outils -> Options -> Expert Advisors :
       ✅ Autoriser le trading algorithmique
       ✅ Autoriser WebRequest pour : https://api.telegram.org
  3. MT5 -> Outils -> Options -> Notifications : MetaQuotes ID du téléphone + Test
  4. Attacher l'INDICATEUR sur les charts d'analyse
  5. Attacher l'EA sur le chart d'exécution (magic UNIQUE par instrument)
  6. Vérifier MODE_ALERT_ONLY avant tout passage MODE_MARKET

"@ -ForegroundColor Yellow
