# MQL5 — EA, indicateur & pont calendrier (DREVM)

| Fichier | Type | Rôle |
|---|---|---|
| `SmartMoneyNYSession.mq5` | **Expert Advisor** (algo de trading) | Trade la session NY (US30/USDJPY) : EMA/RSI/ATR/Kijun + Wyckoff, profils de risque. |
| `NY_Wyckoff_FVG_OB_Fib.mq5` | Indicateur (visuel) | Order Blocks, FVG, Wyckoff, Fibonacci + panneau de score. |
| `CalendarExporter.mq5` | EA (pont) | Exporte le calendrier éco MT5 (`CalendarValueHistory`) en JSON pour le pipeline Python. |
| `SmartMoneyNYSession.set` | Preset | Configuration de l'EA alignée sur le pipeline. |

## Configurer l'algo (`SmartMoneyNYSession.mq5`)

1. Copier `SmartMoneyNYSession.mq5` dans `MQL5/Experts/` du terminal, compiler (F7 dans MetaEditor).
2. Glisser l'EA sur un graphique **US30** (ou USDJPY), autoriser l'AutoTrading.
3. Dans la fenêtre de paramètres → **Charger** → `SmartMoneyNYSession.set`.

### Paramètres (preset fourni)

| Groupe | Input | Valeur | Correspondance Python |
|---|---|---|---|
| Profil | `InpProfile` | `SCALPING` | `PROFILES` / `DEFAULT_PROFILE` |
| Session | `InpSessStartH/M`–`InpSessEndH/M` | 9:30 → 16:00 (NY) | `NY_SESSION_START/END` |
| | `InpCloseAtEnd` | `true` | `CLOSE_AT_SESSION_END` |
| Symboles | `InpSym1/2` | US30 / USDJPY | `SYMBOLS` |
| | `InpSpread1/2` | 50 / 20 | `max_spread_points` |
| Indicateurs | `InpKijunPeriod` | 26 | `price_above_kijun` |
| | `InpWyckLookback` | 20 | `detect_wyckoff` (swing 20) |
| | `InpRSIPeriod` / `InpATRPeriod` | 14 / 14 | `rsi` / `atr` |
| | `InpEMA21` / `InpEMA50` | 21 / 50 | `detect_h4` (EMA 21/50) |

> Change `InpProfile` pour ajuster le risque : `CONSERVATIVE` (grade A+, R:R 3, 1 trade/sym),
> `BALANCED`, `AGGRESSIVE` (grade B, R:R 2). Les valeurs des profils sont définies côté
> console (`ny_session_interface/ny_session_bot.py`) — garde les deux côtés cohérents.

## Pont calendrier (`CalendarExporter.mq5`)

1. Copier dans `MQL5/Experts/`, compiler, glisser sur un graphique (autoriser l'AutoTrading).
2. Inputs : `HoursAhead` (fenêtre), `RefreshSec` (rafraîchissement), `OutFile`
   (défaut `calendar_export.json` dans `MQL5/Files/`), `HighOnly`.
3. Côté console, pointer `MT5_CALENDAR_FILE` sur ce fichier et mettre `NEWS_SOURCE=mt5`
   pour que le filtre news du validator utilise le calendrier MT5 natif.

> ⚠️ Le terminal doit avoir le **calendrier économique activé** et une connexion.
> Le paquet Python `MetaTrader5` n'expose pas le calendrier — d'où ce pont MQL5.
