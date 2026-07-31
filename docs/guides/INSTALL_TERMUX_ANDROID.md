# Installation sur Android avec Termux

Guide d'installation de saasDrevmBot sur un téléphone Android via Termux.

> ⚠️ **Statut de vérification** : les recettes ci-dessous sont la procédure Termux
> standard (paquets `pkg` précompilés plutôt que wheels PyPI incompatibles bionic).
> Elles n'ont pas été exécutées sur un appareil réel depuis l'environnement de dev.
> Signale tout écart — il sera consigné dans `lessons.md`.

---

## Ce qui tourne vraiment sur Android

| Service | Port | Sur Termux ? |
|---|---|---|
| Console NY Session (`ny_session_interface/api.py`) | 8800 | ✅ en **SIMULATION** |
| Dashboard Node / bot Discord (`src/server.js`) | 3000 | ✅ complet |
| Backend FastAPI (`backend/`) | 8000 | ⚠️ déconseillé (ta-lib, psycopg2) |
| Frontend SvelteKit (`frontend/`) | 5173 | ✅ mais build coûteux |
| MetaTrader 5 | — | ❌ inexistant sur Android |

`ny_session_bot.py` tente `import MetaTrader5` et retombe sur `sim_mt5` en cas
d'échec. Sur téléphone, ce fallback est **systématique** : le moteur tourne donc
toujours en mode SIMULATION. C'est idéal pour piloter et tester l'interface,
jamais pour exécuter des ordres réels.

---

## 1. Base Termux

Installe Termux depuis **[F-Droid](https://f-droid.org/packages/com.termux/)**,
pas depuis le Play Store : la version Play est abandonnée et son gestionnaire de
paquets est cassé.

```bash
pkg update -y && pkg upgrade -y
pkg install -y git python nodejs
termux-setup-storage      # accepte la fenêtre de permission Android
```

---

## 2. Option A — Console NY Session (recommandé sur téléphone)

### Script automatique

```bash
curl -fsSL https://raw.githubusercontent.com/LeDREVM/saasdrevmbot_v1.01/main/scripts/setup-termux.sh -o setup-termux.sh
bash setup-termux.sh
```

Variables optionnelles : `BRANCH` (défaut `main`), `REPO_DIR` (défaut
`$HOME/goldyxbotdrevm`).

Le script vérifie que `fastapi`, `uvicorn`, `pandas` et `numpy` sont réellement
importables avant d'annoncer le succès — il sort en erreur sinon.

### Installation manuelle

```bash
git clone -b main https://github.com/LeDREVM/saasdrevmbot_v1.01.git ~/goldyxbotdrevm
cd ~/goldyxbotdrevm/ny_session_interface

pkg install -y python-numpy                              # numpy précompilé
pkg install -y tur-repo && pkg install -y python-pandas   # pandas précompilé

pip install fastapi uvicorn        # ⚠️ PAS uvicorn[standard] — voir plus bas

cp env.template .env
python api.py                      # → http://127.0.0.1:8800
```

Ouvre ensuite `http://127.0.0.1:8800` dans le navigateur du même téléphone.

Les variables d'environnement sont documentées dans
`ny_session_interface/env.template`. Les défauts suffisent pour le mode
simulation.

---

## 3. Option B — Dashboard Node (port 3000)

Aucune dépendance native dans `package.json` (`express`, `socket.io`,
`discord.js`, `axios`, `cheerio` sont du JS pur) → c'est l'installation la plus
propre sur Android.

```bash
cd ~/goldyxbotdrevm
npm install
cp .env.example .env
nano .env                 # renseigne au minimum DISCORD_WEBHOOK_URL
npm start                 # → http://localhost:3000
```

Mode bot seul, sans serveur web : `npm run bot-only`.

---

## 4. Pièges Termux

### Wheels PyPI incompatibles

Les wheels `aarch64` publiées sur PyPI sont `manylinux` → compilées contre
**glibc**. Termux tourne sur **bionic** (la libc d'Android). pip ne peut donc pas
les utiliser et retombe sur une compilation depuis les sources.

Conséquence pratique : pour `numpy` et `pandas`, passe **toujours** par `pkg`
(`python-numpy`, et `python-pandas` via `tur-repo`), jamais par `pip`.

### `uvicorn[standard]` : à éviter

L'extra `[standard]` tire `watchfiles` (build Rust) et `uvloop` (compilation C
longue). Or `api.py` lance `uvicorn.run(app, host=HOST, port=PORT)` **sans**
`reload=True` — ces extras ne servent donc à rien ici. Installe `uvicorn` nu.

### `pydantic-core` bloque à l'installation

FastAPI dépend de pydantic v2, dont le cœur `pydantic-core` est écrit en Rust.
Si aucun binaire compatible n'est disponible, pip compile :

```bash
pkg install -y rust binutils
export CARGO_BUILD_TARGET=aarch64-linux-android
pip install fastapi uvicorn
```

Compte plusieurs dizaines de minutes sur un téléphone. Le script `setup-termux.sh`
applique automatiquement ce repli si le premier `pip install` échoue.

### Ne jamais cloner dans `/sdcard`

`/sdcard` est monté en FUSE : pas de bit exécutable, pas de `chmod`, pas de liens
symboliques. `git` et `pip` y cassent de façon obscure. Clone dans `$HOME` et
utilise un lien symbolique pour la visibilité depuis l'explorateur de fichiers —
ce que fait le script :

```bash
ln -sfn ~/goldyxbotdrevm /sdcard/dxpedrevm/goldyxbotdrevm
```

### Le serveur meurt quand tu quittes Termux

Android tue les process en arrière-plan. Déroule la notification Termux et touche
**« Acquire wakelock »** avant de lancer le serveur.

### `backend/requirements.txt` ne passera pas tel quel

Deux bloqueurs : `ta-lib` (bibliothèque C à compiler séparément) et
`psycopg2-binary` (aucune wheel bionic). Si le backend complet est indispensable
sur le téléphone, il faut `pkg install libpq` puis `psycopg2` depuis les sources,
et retirer `ta-lib`. Déconseillé — préfère l'option A ou B.

---

## 5. Dépannage rapide

| Symptôme | Cause | Fix |
|---|---|---|
| `pkg: command not found` | Termux du Play Store | Réinstaller depuis F-Droid |
| `ModuleNotFoundError: pandas` | `tur-repo` non installé | `pkg install tur-repo && pkg install python-pandas` |
| pip compile indéfiniment sur `pydantic-core` | Pas de binaire Rust | `pkg install rust binutils` + `CARGO_BUILD_TARGET=aarch64-linux-android` |
| `Permission denied` sur git | Clone dans `/sdcard` | Recloner dans `$HOME` |
| Le serveur s'arrête à l'écran verrouillé | Pas de wakelock | Notification Termux → Acquire wakelock |
| Console accessible mais équité figée | Mode SIMULATION (normal) | MT5 n'existe pas sur Android — voir `PRICE_SOURCE=mt5bridge` dans `env.template` pour de vraies bougies |

---

## Voir aussi

- `scripts/setup-termux.sh` — script d'installation
- `ny_session_interface/README.md` — console NY Session en détail
- `ny_session_interface/env.template` — toutes les variables d'environnement
- `docs/guides/DEPENDENCIES.md` — dépendances et troubleshooting général
