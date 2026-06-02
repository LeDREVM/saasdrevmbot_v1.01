# Déploiement VPS

Deux cibles, deux rôles complémentaires :

| VPS | Rôle | Trading réel ? |
|---|---|---|
| **Windows** | Bot NY Session + console, connecté à MetaTrader 5 | ✅ Oui (MT5) |
| **Linux** | Plateforme web : dashboard GoldyXbOT + console (simulation) | ❌ Non (pas de MT5) |

> ⚠️ `MetaTrader5` est **Windows uniquement**. Les vrais ordres ne peuvent
> partir que du VPS Windows. Le VPS Linux sert au monitoring, au calendrier
> économique et à tester l'interface (mode SIMULATION).

---

## 🪟 VPS Windows — trading réel (MT5)

### Prérequis
1. **Python 3.11+** (cocher « Add Python to PATH »).
2. **Git for Windows**.
3. **Terminal MetaTrader 5** de Fusion Markets : installé, connecté à ton
   compte, et **« Algo Trading » activé** (bouton vert dans la barre du haut).

### Installation
```powershell
git clone -b claude/trading-session-performance-6Ex86 https://github.com/LeDREVM/saasdrevmbot_v1.01.git %USERPROFILE%\goldyxbotdrevm
cd %USERPROFILE%\goldyxbotdrevm
powershell -ExecutionPolicy Bypass -File deploy\windows\setup-windows.ps1
```
Le script crée un venv, installe `requirements.txt` + `MetaTrader5`, et propose
de lancer la console (**http://127.0.0.1:8800**).

### Avant le live
- **Remplace `ny_session_interface\trading_ny_session.py`** par ta vraie Trading
  Bible (la version livrée est un placeholder).
- `DRY_RUN` est **actif par défaut** → aucun ordre réel tant que tu ne le coupes
  pas depuis la console (avec confirmation). Teste d'abord sur **compte démo**.

### Tourner 24/7
- Simple : `deploy\windows\start-console.bat` (laisse la fenêtre ouverte), ou
  Planificateur de tâches « au démarrage de session ».
- Service : [NSSM](https://nssm.cc) →
  `nssm install NYConsole "%USERPROFILE%\goldyxbotdrevm\ny_session_interface\.venv\Scripts\python.exe" api.py`
  (définir le dossier de travail sur `...\ny_session_interface`).

---

## 🐧 VPS Linux — plateforme web + console (simulation)

### Installation
```bash
git clone -b claude/trading-session-performance-6Ex86 https://github.com/LeDREVM/saasdrevmbot_v1.01.git
cd saasdrevmbot_v1.01
sudo bash deploy/setup-vps-linux.sh
```
Le script installe Node 20 + Python, clone dans `/opt/goldyxbotdrevm`, et crée
deux services systemd :

| Service | Port | Description |
|---|---|---|
| `goldyxbot` | 3000 | Dashboard GoldyXbOT (calendrier éco, Discord, US30/VIX) |
| `ny-console` | 8800 | Console NY Session Bot (SIMULATION) |

### Exploitation
```bash
systemctl status goldyxbot ny-console
journalctl -u ny-console -f          # logs en direct
systemctl restart ny-console         # après un git pull
```

### Accès & sécurité
- **Dashboard** : `http://<IP_VPS>:3000` (ouvre le port 3000 au pare-feu).
- **Console** : reste en **localhost**. Depuis ton PC :
  ```bash
  ssh -L 8800:127.0.0.1:8800 user@<IP_VPS>
  # puis http://127.0.0.1:8800
  ```
- Pour exposer la console publiquement : mets un **reverse-proxy HTTPS**
  (nginx/Caddy) devant + active un **token** (`API_TOKEN` dans
  `ny-console.service`). Sur Linux il n'y a pas de MT5 → aucun ordre réel
  possible, mais garde quand même l'accès protégé.

### Plateforme complète (API FastAPI + PostgreSQL + frontend)
Pour le backend `saasDrevmBot` (port 8000) + Postgres/Redis + frontend (5173),
utilise plutôt Docker (déjà fourni à la racine) :
```bash
docker compose up -d           # voir docker-compose.yml / DOCKER_DEPLOYMENT.md
```

---

## Mettre à jour (les deux OS)
```bash
# Linux
cd /opt/goldyxbotdrevm && git pull && sudo systemctl restart goldyxbot ny-console
```
```powershell
# Windows
cd %USERPROFILE%\goldyxbotdrevm; git pull
```
