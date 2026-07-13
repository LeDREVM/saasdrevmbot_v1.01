# Calendrier économique — fichiers JSON hebdomadaires (ForexFactory)

Dépose ici **un fichier JSON par semaine** au format ForexFactory ; le pipeline
les charge quand `NEWS_SOURCE=file` (voir `ny_session_interface/news.py`).

## Convention de nommage

```
data/calendar/ff_calendar_<AAAA-MM-JJ>.json
```
où `<AAAA-MM-JJ>` est le **début de semaine (dimanche)** couvert par le fichier.
Exemple fourni : `ff_calendar_2026-07-12.json` (semaine du 12 au 18 juillet 2026).

Tous les `*.json` du dossier sont chargés et fusionnés ; le filtre news ne retient
que les annonces **à venir dans la fenêtre** `NEWS_WINDOW_HOURS`. Tu peux donc
laisser plusieurs semaines côte à côte — les anciennes sont ignorées
automatiquement (événements passés).

## Format attendu (ForexFactory)

Tableau d'objets :
```json
[
  {
    "title": "Core CPI m/m",
    "country": "USD",                       // = devise
    "date": "2026-07-14T08:30:00-04:00",    // ISO avec fuseau
    "impact": "High",                        // High | Medium | Low | Holiday
    "forecast": "0.2%",
    "previous": "0.2%"
  }
]
```
Normalisation interne : `title→event`, `country→currency`, `impact` en minuscules
(`Holiday` ignoré), `date` conservée (fuseau géré). Où récupérer les exports :
`https://nfs.faireconomy.media/ff_calendar_thisweek.json` (et `...nextweek.json`).

## Activer

```bash
# ny_session_interface/.env
NEWS_SOURCE=file
# CALENDAR_DIR=  (optionnel ; défaut = ce dossier)
```
