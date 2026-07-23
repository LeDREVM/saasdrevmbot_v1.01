# trading_bot — NY Smart Money System

Bot de trading (SMC/ICT + Wyckoff + RSI) avec dashboard web dark et notifications Telegram.

## 🚀 Démarrage rapide

```bash
cd trading_bot

# 1. Dépendances
pip install -r requirements.txt

# 2. Configuration
cp env.template .env
# → remplir TWELVEDATA_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 3. Dashboard
uvicorn dashboard:app --port 8050
# → http://localhost:8050

# 4. Bot (boucle de détection des signaux)
python main.py
```

Sous Windows : double-clique `start_dashboard.bat`.

## 📁 Fichiers

| Fichier | Rôle |
|---------|------|
| `main.py` | Boucle principale : détection + scoring + Telegram + enregistrement en base |
| `dashboard.py` | Dashboard web (FastAPI) : statut, killzone NY, signaux, stats, candlesticks |
| `db.py` | Persistance SQLite des signaux (`db.sqlite`, non versionné) |
| `data_engine.py` | Données de marché via TwelveData (`TWELVEDATA_API_KEY`) |
| `telegram.py` | Notifications Telegram (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`) |
| `scoring_engine.py` | Score et grade des setups (A+ / A / B / C) |
| `smart_money_engine.py` | Ichimoku, divergences RSI, signaux smart money |
| `strategy_engine.py` · `wyckoff_engine.py` · `divergence_engine.py` · `mtf_engine.py` | Moteurs d'analyse |
| `mt5_execution.py` | Exécution des ordres MetaTrader 5 (Windows) |
| `backtest.py` | Backtests |

## 🌐 API du dashboard

| Endpoint | Description |
|----------|-------------|
| `GET /` | Interface web |
| `GET /api/status` | Statut bot + killzone NY (13h–16h UTC) |
| `GET /api/signals?limit=20` | Derniers signaux |
| `GET /api/stats` | Stats par grade, paire, sens |
| `GET /api/chart/{pair}` | OHLC + zones supply/demand (ex : `XAU-USD`) |

## ⚠️ Notes

- Sans `.env`, le dashboard fonctionne mais les graphiques affichent « API non configurée ».
- `db.sqlite` est créée automatiquement au premier signal.
