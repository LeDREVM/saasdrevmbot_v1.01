#!/usr/bin/env bash
# =============================================================================
#  setup-termux.sh  —  Installation Termux (Android) du projet goldyxbotdrevm
#  Méthode 2A : clone dans le HOME Termux (vrai filesystem) + lien vers la SD.
#
#  Usage :
#     bash setup-termux.sh
#  Variables optionnelles :
#     BRANCH=...      branche à utiliser (défaut : branche de dev ci-dessous)
#     REPO_DIR=...    dossier cible    (défaut : $HOME/goldyxbotdrevm)
# =============================================================================
set -e

REPO_URL="https://github.com/LeDREVM/saasdrevmbot_v1.01.git"
BRANCH="${BRANCH:-claude/trading-session-performance-6Ex86}"
REPO_DIR="${REPO_DIR:-$HOME/goldyxbotdrevm}"
SD_LINK="/sdcard/dxpedrevm/goldyxbotdrevm"

log() { printf "\n\033[1;36m▶ %s\033[0m\n" "$1"; }
warn() { printf "\033[1;33m⚠ %s\033[0m\n" "$1"; }

# --- 1. Paquets système ------------------------------------------------------
log "Mise à jour des paquets Termux"
pkg update -y && pkg upgrade -y
pkg install -y git python

log "Installation numpy/pandas (versions précompilées si dispo)"
pkg install -y python-numpy || true
pkg install -y python-pandas || true

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
if [ -d /sdcard ]; then
  log "Lien SD : $SD_LINK → $REPO_DIR"
  mkdir -p "$(dirname "$SD_LINK")"
  ln -sfn "$REPO_DIR" "$SD_LINK"
else
  warn "/sdcard introuvable — lien SD ignoré (relance après termux-setup-storage)"
fi

# --- 5. Dépendances Python de la console NY Session -------------------------
log "Dépendances Python (FastAPI + Uvicorn)"
pip install --upgrade pip
pip install fastapi "uvicorn[standard]"
python -c "import pandas, numpy" 2>/dev/null || {
  warn "pandas/numpy absents → installation pip (peut être longue à compiler)"
  pip install pandas numpy
}

# --- 6. Résumé + lancement optionnel ----------------------------------------
cat <<EOF

✅ Installation terminée.
   Repo    : $REPO_DIR
   Lien SD : $SD_LINK
   Branche : $BRANCH

▶ Lancer la console NY Session Bot :
    cd $REPO_DIR/ny_session_interface
    python api.py
  puis ouvre http://127.0.0.1:8800 dans ton navigateur.

ℹ️  MetaTrader5 n'existe pas sur Android → le bot tourne en SIMULATION
   (parfait pour tester l'interface depuis le téléphone).
EOF

printf "\nLancer la console maintenant ? [o/N] "
read -r ans
case "$ans" in
  o|O|y|Y) cd "$REPO_DIR/ny_session_interface" && exec python api.py ;;
  *) log "Tu peux la lancer plus tard avec les commandes ci-dessus." ;;
esac
