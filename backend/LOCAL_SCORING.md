# Dashboard principal et scoring local

Le dashboard principal affiche les marchés, le calendrier et les statistiques réelles de l'historique. La page `/scoring` calcule à la demande un score déterministe, sans envoyer le setup à Anthropic ou OpenRouter. Aucun secret IA n'est nécessaire. Les modules IA existants restent disponibles pour d'autres usages ; cette route ne les importe pas.

Le contexte est saisi manuellement. Le score n'est pas une probabilité de gain et ne valide pas automatiquement les prix, volumes ou annonces.

## Barème /100

| Critère déclaré | Maximum |
| --- | ---: |
| Grade A+/A/B/C : 25/20/12/5 | 25 |
| Phase H4 alignée avec BUY/SELL | 15 |
| Session active | 10 |
| Spread acceptable | 5 |
| Spring/UTAD aligné, sweep + réintégration + confirmation | 15 |
| Divergence RSI alignée | 10 |
| Prix du bon côté de la Kijun | 10 |
| Zone M15 touchée et trigger M5 confirmé | 10 |

TRADE exige au moins 75 points, Wyckoff et M5 confirmés, session/spread favorables, calendrier déclaré vérifié et aucune annonce déclarée dans moins de 30 minutes. WAIT s'applique dès 55 points lorsque ces confirmations manquent ; SKIP sous 55. Aucune exécution de trade ni notification n'est effectuée.

Les routes `/api/scoring/history`, `/stats`, `/analyze` restent disponibles ; `/status` expose le mode local. Les résultats gardent les champs historiques et ajoutent `id`, `provider=local` et `technical_baseline.criteria`. Les anciens avis IA restent dans l'historique ; les métriques agrègent les résultats valides, sans représenter une performance financière.

L'historique conserve son emplacement `SCORING_STORE_PATH` ou `data/scoring_history.json`, avec verrou interprocessus et remplacement atomique. Un fichier corrompu est conservé et produit une erreur explicite. `notify=true` est refusé pour éviter un envoi involontaire.

Les heures utilisent `America/Guadeloupe` ; la plage NY suit `America/New_York` et le changement d'heure. Cette plage indicative exclut les week-ends mais ne consulte pas les jours fériés de marché.

## Vérification

Depuis `backend` : `python -m unittest discover -s tests -p test_local_scoring.py -v`.

Depuis `frontend` : `node --test tests/api-client.test.js`, `npm run check` et `npm run build`.
