#!/usr/bin/env bash
# =============================================================================
#  setup-termux.sh  —  Installation Termux (Android) du projet goldyxbotdrevm
#  Méthode 2A : clone dans le HOME Termux (vrai filesystem) + lien vers la SD.
#
#  Usage :
#     bash setup-termux.sh
#     curl -fsSL <raw-url>/scripts/setup-termux.sh | bash
#  Variables optionnelles :
#     BRANCH=...      branche à utiliser (défaut : main)
#     REPO_DIR=...    dossier cible    (défaut : $HOME/goldyxbotdrevm)
#
#  Guide détaillé + dépannage : docs/guides/INSTALL_TERMUX_ANDROID.md
# =============================================================================
set -e

REPO_URL="https://github.com/LeDREVM/saasdrevmbot_v1.01.git"
BRANCH="${BRANCH:-main}"
REPO_DIR="${REPO_DIR:-$HOME/goldyxbotdrevm}"
SD_LINK="/sdcard/dxpedrevm/goldyxbotdrevm"

log() { printf "\n\033[1;36m▶ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m⚠ %s\033[0m\n" "$1"; }
fail() { printf "\n\033[1;31m✖ %s\033[0m\n" "$1"; exit 1; }

# --- 1. Paquets système ------------------------------------------------------
log "Mise à jour des paquets Termux"
pkg update -y && pkg upgrade -y
pkg install -y git python

# numpy et pandas : TOUJOURS via pkg, jamais via pip. Les wheels PyPI aarch64
# sont manylinux/glibc → incompatibles avec bionic (Termux). pip retomberait sur
# une compilation source très longue, souvent vouée à l'échec faute de
# BLAS/LAPACK.
log "Installation numpy (paquet Termux précompilé)"
pkg install -y python-numpy || warn "python-numpy indisponible → repli pip plus bas"

log "Installation pandas (dépôt TUR — Termux User Repository)"
pkg install -y tur-repo || warn "tur-repo indisponible"
pkg install -y python-pandas || warn "python-pandas indisponible → repli pip plus bas"

# --- 2. Accès au stockage partagé -------------------------------------------
if [ ! -d "$HOME/storage" ]; then
  log "Autorisation d'accès au stockage — ACCEPTE la fenêtre Android"
  termux-setup-storage || warn "termux-setup-storage a échoué (continue quand même)"
  sleep 2
fi

# --- 3. Clone ou mise à jour -------------------------------------------------
if [ -d "$REPO_DIR/.git" ]; then
  log "Dépôt déjà présent → mise à jour sur $BRANCH"
  git -C "$REPO_DIR" fetch origin "$BRANCH"
  git -C "$REPO_DIR" checkout "$BRANCH"
  git -C "$REPO_DIR" pull origin "$BRANCH"
else
  log "Clonage dans $REPO_DIR (token GitHub demandé si dépôt privé)"
  git clone -b "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi

# --- 4. Lien visible depuis l'explorateur Android ---------------------------
# Le repo vit dans $HOME (permissions POSIX complètes) ; /sdcard est monté en
# FUSE sans bit exécutable ni chmod → git et pip y cassent. D'où le symlink.
if [ -d /sdcard ]; then
  log "Lien SD : $SD_LINK → $REPO_DIR"
  mkdir -p "$(dirname "$SD_LINK")"
  ln -sfn "$REPO_DIR" "$SD_LINK"
else
  warn "/sdcard introuvable — lien SD ignoré (relance après termux-setup-storage)"
fi

# --- 5. Dépendances Python de la console NY Session -------------------------
# uvicorn SANS l'extra [standard] : api.py appelle uvicorn.run(app) sans
# reload=True, donc watchfiles (Rust) et uvloop (compilation C) ne servent à
# rien et sont les deux premiers points de friction sur Termux.
log "Dépendances Python (FastAPI + Uvicorn)"
pip install --upgrade pip
if ! pip install fastapi uvicorn; then
  warn "Échec probable de pydantic-core (build Rust) → installation de la toolchain"
  pkg install -y rust binutils
  export CARGO_BUILD_TARGET=aarch64-linux-android
  pip install fastapi uvicorn
fi

python -c "import pandas, numpy" 2>/dev/null || {
  warn "pandas/numpy absents des paquets Termux → repli pip (long, peut échouer)"
  pip install pandas numpy
}

# --- 6. Fichier d'environnement ---------------------------------------------
NY_DIR="$REPO_DIR/ny_session_interface"
if [ -f "$NY_DIR/.env" ]; then
  log ".env déjà présent — conservé tel quel"
elif [ -f "$NY_DIR/env.template" ]; then
  log "Création de $NY_DIR/.env depuis env.template"
  cp "$NY_DIR/env.template" "$NY_DIR/.env"
fi

# --- 7. Vérification réelle avant d'annoncer le succès ----------------------
log "Vérification des imports"
( cd "$NY_DIR" && python -c "import fastapi, uvicorn, pandas, numpy" ) \
  || fail "Imports KO — installation NON terminée. Voir docs/guides/INSTALL_TERMUX_ANDROID.md"

# --- 8. Résumé + lancement optionnel ----------------------------------------
cat <<EOF

✅ Installation vérifiée (fastapi, uvicorn, pandas, numpy importables).
   Repo    : $REPO_DIR
   Lien SD : $SD_LINK
   Branche : $BRANCH

▶ Lancer la console NY Session Bot :
    cd $NY_DIR
    python api.py
  puis ouvre http://127.0.0.1:8800 dans ton navigateur.

ℹ️  MetaTrader5 n'existe pas sur Android → le bot tourne en SIMULATION
   (parfait pour tester l'interface depuis le téléphone).

ℹ️  Pense au wakelock : notification Termux → « Acquire wakelock », sinon
   Android tue le serveur dès que tu quittes l'app.
EOF

# read échouerait sous set -e en exécution non-interactive (curl | bash).
if [ -t 0 ]; then
  printf "\nLancer la console maintenant ? [o/N] "
  read -r ans || ans=""
  case "$ans" in
    o|O|y|Y) cd "$NY_DIR" && exec python api.py ;;
    *) log "Tu peux la lancer plus tard avec les commandes ci-dessus." ;;
  esac
fi
