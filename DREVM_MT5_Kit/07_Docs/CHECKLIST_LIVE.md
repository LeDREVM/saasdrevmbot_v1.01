# ✅ CHECKLIST — Passage en réel (MODE_MARKET)

À valider **dans l'ordre**, case par case. Un seul ❌ = on reste en ALERT_ONLY.

## Phase 1 — Backtest (Strategy Tester)

- [ ] Optimisation génétique lancée avec `DREVM_Martingale_Optim.set` (ticks réels, forward 1/3)
- [ ] Set retenu : bon en backtest **ET** en forward (pas un pic isolé, un plateau de voisins similaires)
- [ ] Drawdown max < 25 %
- [ ] Série de pertes consécutives max ≤ 4
- [ ] ≥ 100 trades dans le test
- [ ] Re-test du set sur USDJPY : ne s'effondre pas totalement (sinon = overfit or)
- [ ] Rapport XML exporté et archivé dans Notion (DREVM Performance System)

## Phase 2 — Validation live en ALERT_ONLY (2 semaines minimum)

- [ ] EA attaché avec le set gagnant, `MODE_ALERT_ONLY`
- [ ] Alertes Telegram reçues et lisibles (E/SL/TP corrects)
- [ ] Compter les signaux : fréquence cohérente avec le backtest (± 30 %)
- [ ] Compter les séries de pertes virtuelles consécutives : **≤ 3**
- [ ] Aucun signal pendant les fenêtres news (blackout `InpNewsTimes` à jour via ff_to_newstimes.py)
- [ ] `drevm_ai_advisor.py` opérationnel (analyses Telegram reçues)

## Phase 3 — MODE_MARKET progressif

- [ ] Semaine 1-2 : lot **fixe 0.01, martingale désactivée** (`InpMaxSteps=0`)
- [ ] Slippage et spread réels acceptables vs backtest
- [ ] Disjoncteurs testés au moins une fois (stop jour OU limite 4 trades déclenché proprement)
- [ ] Compteur `tradesToday` persiste après un restart VPS (vérifier GlobalVariables)
- [ ] Semaine 3+ : martingale réactivée (`InpMaxSteps=3`) SEULEMENT si séries ≤ 3 confirmées en réel

## Phase 4 — Multi-instruments (optionnel)

- [ ] CorrelationGuard actif (`CorrGuard_Report()` vérifié dans les logs)
- [ ] Magic numbers uniques par chart (tableau INSTALLATION.md)
- [ ] Exposition devise surveillée sur le dashboard `/stats` (ExposureView)
- [ ] Jamais plus de 2 instruments corrélés (|r| ≥ 0.7) en même sens simultanément

## Rappels permanents

- 🛑 Le hard stop equity (140$) est **définitif** — s'il se déclenche : retirer l'EA, analyser, ne pas relancer le jour même
- 🛑 Ne JAMAIS élargir les disjoncteurs après une perte ("juste cette fois")
- 📓 Chaque trade → journal (Supabase trading_journal) avec grade et screenshot
- 📰 Mettre à jour `InpNewsTimes` chaque dimanche (CSV Forex Factory, UTC → GMT+3)
