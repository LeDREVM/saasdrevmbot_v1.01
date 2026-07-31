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

## 3. Option B — Dashboards Node (port 3000)

Aucune dépendance native dans `package.json` (`express`, `socket.io`,
`discord.js`, `axios`, `cheerio` sont du JS pur) → c'est l'installation la plus
propre sur Android.

```bash
cd ~/goldyxbotdrevm
npm install
cp .env.example .env
npm start                 # → http://localhost:3000
```

Un seul serveur expose trois pages :

| Page | URL | Fichier |
|---|---|---|
| Centre de Contrôle | `http://localhost:3000/` | `src/public/home.html` |
| Calendrier Économique | `http://localhost:3000/dashboard` | `src/public/index.html` |
| Corrélations Prix ↔ News | `http://localhost:3000/correlations` | `src/public/correlations.html` |

**Discord n'est pas obligatoire.** `src/server.js` démarre le serveur quoi qu'il
arrive ; sans `DISCORD_WEBHOOK_URL` il affiche simplement `Discord: ❌` au
démarrage et les dashboards fonctionnent normalement. Ne renseigne le webhook
dans `.env` que si tu veux les alertes.

Le temps réel marche sans configuration : `src/public/app.js` appelle
`io({ transports: [...] })` sans URL, donc Socket.io se connecte à l'origine
servie — y compris via une IP de réseau local.

Mode bot seul, sans serveur web : `npm run bot-only`.

> **Et l'Analytics SvelteKit (port 5173) ?** Déconseillé sur téléphone : `vite dev`
> tourne, mais le build est long et gourmand en RAM. Les pages Node ci-dessus
> couvrent déjà calendrier et corrélations.

---

## 4. Accéder aux dashboards depuis un autre appareil

Le serveur Node écoute déjà sur toutes les interfaces (`server.listen(PORT)` sans
hôte → `0.0.0.0`). Il suffit de connaître l'IP du téléphone :

```bash
pkg install -y net-tools
ifconfig wlan0 | grep 'inet '
```

Puis depuis un autre appareil du même Wi-Fi : `http://192.168.x.x:3000`.

**La console Python, elle, écoute sur `127.0.0.1` par défaut** (`api.py`) — c'est
volontaire, elle peut envoyer des ordres. Pour l'exposer au réseau local :

```bash
NY_BOT_HOST=0.0.0.0 API_TOKEN="<token-long-et-aleatoire>" REQUIRE_TOKEN=1 python api.py
```

Ne l'expose jamais sans `REQUIRE_TOKEN=1` (cf. §6.3). Sur Android le moteur est en
SIMULATION, donc le risque réel est nul — mais prends l'habitude tout de suite.

---

## 5. Garder le serveur vivant

Android tue les process en arrière-plan. Trois niveaux, du plus simple au plus
durable :

```bash
# 1. Wakelock — indispensable
termux-wake-lock          # ou : notification Termux → « Acquire wakelock »

# 2. Survivre à la fermeture de la session shell
cd ~/goldyxbotdrevm
nohup npm start > ~/dashboard.log 2>&1 &
tail -f ~/dashboard.log

# 3. Démarrage automatique au boot du téléphone
#    installe l'app Termux:Boot depuis F-Droid et ouvre-la une fois, puis :
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/dashboard <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd ~/goldyxbotdrevm && npm start
EOF
chmod +x ~/.termux/boot/dashboard
```

Le wakelock ne suffit pas seul : il faut aussi lever la restriction batterie
côté Android (cf. §6.1).

---

## 6. Permissions

Trois couches indépendantes. C'est en général la deuxième qui coince.

### 6.1 Permissions Android

**Stockage** — accès à `/sdcard` :

```bash
termux-setup-storage      # accepte la fenêtre Android
```

Crée `~/storage/` (raccourcis vers `shared`, `downloads`, `dcim`…). Si la fenêtre
a été refusée : Paramètres → Applications → Termux → Autorisations → Fichiers →
Autoriser, puis relancer la commande.

**Batterie** — *la* permission qui fait mourir le dashboard. Sans elle, Android
tue le process dès que tu quittes l'app :

- Paramètres → Applications → Termux → Batterie → **« Sans restriction »**
- Le chemin varie selon la marque (Samsung : « Autoriser l'activité en
  arrière-plan » ; Xiaomi : Sécurité → Démarrage automatique + Économiseur →
  Sans restriction)

**Notifications** (Android 13+) — nécessaire pour voir la notification
persistante de Termux, donc le bouton wakelock : Paramètres → Applications →
Termux → Notifications → Autoriser.

**Démarrage au boot** — installer l'app **Termux:Boot** (F-Droid) et l'ouvrir une
fois ; elle n'affiche rien, c'est normal. Les scripts de `~/.termux/boot/`
s'exécuteront alors au redémarrage.

### 6.2 Permissions de fichiers (`chmod`)

Les scripts `.sh` du repo sont committés en **644**, sans bit exécutable :

```
100644  scripts/setup-termux.sh
100644  scripts/deploy-netlify.sh
```

D'où le `bash setup-termux.sh` de ce guide plutôt que `./setup-termux.sh`. Pour
les invoquer directement :

```bash
chmod +x ~/goldyxbotdrevm/scripts/*.sh
```

**Le `.env` contient des secrets** (`API_TOKEN`, `TELEGRAM_BOT_TOKEN`,
`SUPABASE_SERVICE_KEY`, `MT5_PASSWORD`). Restreins-le :

```bash
chmod 600 ~/goldyxbotdrevm/.env
chmod 600 ~/goldyxbotdrevm/ny_session_interface/.env
```

Il est déjà couvert par `.gitignore` — aucun risque de commit accidentel.

Le script de boot doit être exécutable, sinon Termux:Boot l'ignore
silencieusement : `chmod +x ~/.termux/boot/dashboard`.

⚠️ **`chmod` n'a aucun effet dans `/sdcard`** (montage FUSE sans permissions
POSIX). Si un script refuse de tourner malgré `chmod +x`, vérifie que tu es bien
dans `$HOME` et non dans `/sdcard`.

### 6.3 Permissions applicatives (accès à la console)

La console NY Session a son propre contrôle d'accès, indépendant d'Android. Dans
`ny_session_interface/.env` :

```bash
API_TOKEN=<chaine-longue-et-aleatoire>
REQUIRE_TOKEN=1      # exige le token sur TOUTES les routes /api/*, GET compris
```

Avec `REQUIRE_TOKEN=0` (le défaut), seules les routes POST sont protégées — les
GET (équité, positions, logs) restent ouverts. Passe-le à `1` dès que le port
sort de `127.0.0.1`.

Générer un token correct :

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 7. Pièges Termux

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

Android tue les process en arrière-plan. Wakelock **et** restriction batterie
levée — les deux sont nécessaires, voir §5 et §6.1.

### `backend/requirements.txt` ne passera pas tel quel

Deux bloqueurs : `ta-lib` (bibliothèque C à compiler séparément) et
`psycopg2-binary` (aucune wheel bionic). Si le backend complet est indispensable
sur le téléphone, il faut `pkg install libpq` puis `psycopg2` depuis les sources,
et retirer `ta-lib`. Déconseillé — préfère l'option A ou B.

---

## 8. Dépannage rapide

| Symptôme | Cause | Fix |
|---|---|---|
| `pkg: command not found` | Termux du Play Store | Réinstaller depuis F-Droid |
| `ModuleNotFoundError: pandas` | `tur-repo` non installé | `pkg install tur-repo && pkg install python-pandas` |
| pip compile indéfiniment sur `pydantic-core` | Pas de binaire Rust | `pkg install rust binutils` + `CARGO_BUILD_TARGET=aarch64-linux-android` |
| `Permission denied` sur git | Clone dans `/sdcard` | Recloner dans `$HOME` (§6.2) |
| `./script.sh: Permission denied` | Scripts committés en 644 | `chmod +x scripts/*.sh`, ou lancer via `bash script.sh` (§6.2) |
| `chmod +x` sans effet | Fichier dans `/sdcard` (FUSE) | Déplacer dans `$HOME` (§6.2) |
| Le serveur s'arrête à l'écran verrouillé | Pas de wakelock, ou restriction batterie | §5 et §6.1 — les deux sont nécessaires |
| `termux-setup-storage` ne fait rien | Permission Fichiers refusée | Paramètres → Termux → Autorisations → Fichiers (§6.1) |
| Script `~/.termux/boot/` jamais exécuté | Pas exécutable, ou Termux:Boot jamais ouverte | `chmod +x` + ouvrir l'app une fois (§6.1) |
| Dashboard inaccessible depuis le PC | Mauvaise IP, ou pare-feu Wi-Fi | `ifconfig wlan0` (§4) ; le Node écoute déjà sur `0.0.0.0` |
| Console 8800 inaccessible depuis le PC | `NY_BOT_HOST` reste sur `127.0.0.1` | `NY_BOT_HOST=0.0.0.0` + `REQUIRE_TOKEN=1` (§4) |
| Console accessible mais équité figée | Mode SIMULATION (normal) | MT5 n'existe pas sur Android — voir `PRICE_SOURCE=mt5bridge` dans `env.template` pour de vraies bougies |

---

## Voir aussi

- `scripts/setup-termux.sh` — script d'installation
- `ny_session_interface/README.md` — console NY Session en détail
- `ny_session_interface/env.template` — toutes les variables d'environnement
- `docs/guides/DEPENDENCIES.md` — dépendances et troubleshooting général
