# TradingView → AI Score → MetaTrader (Guide complet)

## Architecture globale

```
TradingView Alert
      │  (webhook POST)
      ▼
  n8n (VPS:5678)
      │
      ├─ Screenshot Service (Puppeteer :3001)
      │        └── capture chart PNG
      │
      ├─ Supabase Storage (screenshot PNG)
      ├─ Supabase DB (chart_snapshots)
      │
      ├─ Claude AI (Vision + Analyse ICT/Wyckoff)
      │        └── score 0–10 + direction + SL/TP
      │
      ├─ Supabase DB (trade_signals)
      │
      └─ Signal Server Python (VPS:5000)
               │  si score ≥ 7
               ▼
         MT5 EA (socket TCP :5001)
               └── OrderSend()
```

## 1. Installation VPS Hostinger

### Prérequis
- VPS Hostinger Ubuntu 22.04 minimum (2 vCPU / 4 Go RAM recommandé)
- Accès SSH root

```bash
ssh root@VOTRE_IP_VPS
curl -O https://raw.githubusercontent.com/ledrevm/saasdrevmbot_v1.01/main/vps/setup_vps.sh
bash setup_vps.sh
```

### Configuration `.env`
```bash
nano /opt/saasdrevmbot/vps/.env
```
Remplir :
- `VPS_IP` = IP publique de ton VPS
- `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` = dans Supabase → Settings → API
- `ANTHROPIC_API_KEY` = dans console.anthropic.com
- `N8N_PASSWORD` = mot de passe fort pour l'interface n8n

Redémarrer :
```bash
cd /opt/saasdrevmbot/vps && docker-compose restart
```

## 2. Supabase — Initialiser la base de données

1. Aller sur **supabase.com** → ton projet → **SQL Editor**
2. Coller le contenu de `supabase/migrations/001_trade_signals.sql`
3. Exécuter
4. Aller dans **Storage** → **New Bucket**
   - Nom : `chart-screenshots`
   - Public : ✅ oui (pour que Claude puisse accéder aux images)

## 3. n8n — Importer le workflow

1. Ouvrir `http://VOTRE_IP:5678`
2. Se connecter (user/password du `.env`)
3. **Workflows** → **Import from file**
4. Sélectionner `n8n/tradingview_ai_workflow.json`

### Configurer les credentials dans n8n

**Supabase** (`Settings → Credentials → New → Supabase`):
- Host : `XXXX.supabase.co`
- Service Role Key : `eyJ...`

**Anthropic** (`Settings → Credentials → New → Header Auth`):
- Name : `Anthropic API Key`
- Header Name : `x-api-key`
- Header Value : `sk-ant-api03-...`

## 4. TradingView — Créer l'alerte webhook

Dans TradingView, sur ton indicateur/stratégie :
1. **Alerte** → **Créer**
2. Condition : ton signal (ex. RSI croise, OB touché, etc.)
3. **Notifications** → **Webhook URL** :
   ```
   http://VOTRE_IP:5678/webhook/tradingview-alert
   ```
4. **Message** (JSON) :
   ```json
   {
     "symbol": "{{ticker}}",
     "timeframe": "{{interval}}",
     "close": "{{close}}",
     "open": "{{open}}",
     "high": "{{high}}",
     "low": "{{low}}",
     "volume": "{{volume}}",
     "time": "{{time}}"
   }
   ```

## 5. MetaTrader 5 — Installer l'EA

1. Dans MT5 : **Fichier → Ouvrir le dossier des données → MQL5/Experts**
2. Copier `metatrader/ea/AISignalReceiver.mq5`
3. Recompiler dans MetaEditor (F7)
4. Glisser l'EA sur n'importe quel chart (il s'exécute indépendamment)
5. Paramètres :
   - `VPS_IP` : IP de ton VPS Hostinger
   - `BRIDGE_PORT` : 5001
   - `POLL_SECONDS` : 5 (poll toutes les 5 secondes)
   - `DEFAULT_LOT` : 0.01 (à ajuster selon ta gestion du risque)

⚠️ **Dans MT5 → Options → Expert Advisors** :
- ☑ Autoriser le trading automatique
- ☑ Autoriser les connexions WebRequest pour : `VOTRE_IP`

## 6. Flux complet — Test

1. Activer le workflow dans n8n (bouton en haut à droite)
2. Tester manuellement via n8n ou attendre une alerte TradingView
3. Vérifier dans Supabase :
   - Table `chart_snapshots` : screenshot uploadé
   - Table `trade_signals` : score AI + direction
4. Si score ≥ 7 : vérifier MT5 → **Historique des transactions**

## 7. Scoring IA (Claude Vision)

| Score | Signification                        | Action        |
|-------|--------------------------------------|---------------|
| 8–10  | Setup parfait (OB+FVG+Fib+Session)  | Trade envoyé  |
| 7     | Bon setup, 2–3 confluences           | Trade envoyé  |
| 5–6   | Setup moyen, incertitude             | Log seulement |
| 0–4   | Pas de setup / contre-tendance       | Ignoré        |

Pour changer le seuil : modifier `score >= 7` dans le node **🎯 Score >= 7 ?** dans n8n.

## 8. Sécurité (VPS)

```bash
# Limiter l'accès au bridge MT5 à l'IP de ta machine MT5
ufw allow from VOTRE_IP_MT5 to any port 5001
ufw delete allow 5001    # retirer la règle ouverte précédente

# HTTPS pour n8n (optionnel, via Nginx reverse proxy)
apt install nginx certbot python3-certbot-nginx
```

## 9. Monitoring

```bash
# Logs n8n
docker logs n8n -f

# Logs signal server
docker logs signal-server -f

# Logs screenshot service
docker logs screenshot-service -f

# Vérifier la queue de signaux
curl http://localhost:5000/health
```
