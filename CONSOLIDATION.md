# Consolidation du SaaS

Le journal, les alertes et le dashboard utilisent les modules du SaaS existant. Le scoring du dashboard reste local, à la demande.

## Configuration avant mise en service

- Appliquer `supabase/migrations/202609300001_journal_timeframes.sql` sur la base du journal. Les trades historiques gardent un timeframe inconnu jusqu'à une saisie explicite.
- Configurer `SUPABASE_URL` et `SUPABASE_ANON_KEY` côté FastAPI pour vérifier les sessions auprès du même projet Supabase que le frontend. Sans configuration, les alertes personnelles refusent l'accès.
- Les préférences et l'historique des alertes nécessitent les tables `UserAlertSettings` et `AlertLog` du backend existant.
- Renseigner les canaux personnels depuis les alertes. Les secrets sont enregistrés côté serveur et ne sont pas renvoyés au navigateur. Les alertes personnelles n'utilisent pas les canaux globaux comme fallback.
- Le worker Celery existant est l'ordonnanceur des alertes personnelles. Ne pas démarrer le bot Telegram Goldy en parallèle pour le même destinataire, afin d'éviter les doubles notifications. Ses commandes sont réservées au chat configuré.

Les dates du journal et heures de silence utilisent America/Guadeloupe. Les crons Goldy utilisent America/New_York pour suivre les changements d'heure. Le calendrier affiche les pannes explicitement. Aucun faux signal ni analyse aléatoire n'est repris.

L'export CSV contient les 200 trades affichés au maximum, et échappe les cellules pour prévenir l'exécution de formules.

Les envois des tests automatisés sont simulés. La migration et les services de production ne sont pas modifiés automatiquement.

## Vérifications locales

Tests hors ligne : journal et erreurs réseau (6), validation bougies et horaire NY (2), accès alertes et masquage secrets (6), livraison par utilisateur (3), scoring local (12), déduplication existante (2). Les composants Svelte modifiés compilent. Les dépendances Python de vérification sont isolées et ignorées par Git ; elles ne remplacent pas les versions de production.

Le build Vite complet reste bloqué par un accès refusé à un dossier parent pendant la résolution de configuration. Migration SQL non exécutée sur Supabase et parcours connecté non vérifié en production.
