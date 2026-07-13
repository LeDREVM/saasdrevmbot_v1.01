-- ============================================================================
--  RLS policies pour les tables "machine" du pipeline (écrites par le bot via
--  service_role, qui contourne la RLS). Sans policy, l'API cliente ne pouvait
--  RIEN lire (RLS activée = tout bloqué). On ouvre la LECTURE aux utilisateurs
--  authentifiés (contexte mono-locataire) ; les ÉCRITURES restent réservées au
--  service_role (aucune policy insert/update/delete → seul service_role écrit).
--  Corrige l'avertissement advisor "rls_enabled_no_policy".
--  Idempotent.
-- ============================================================================

-- trade_signals : signaux du bot — lecture seule pour l'app.
DROP POLICY IF EXISTS "trade_signals_read" ON public.trade_signals;
CREATE POLICY "trade_signals_read" ON public.trade_signals
    FOR SELECT TO authenticated USING (true);

-- chart_snapshots : captures/analyses de graphes — lecture seule.
DROP POLICY IF EXISTS "chart_snapshots_read" ON public.chart_snapshots;
CREATE POLICY "chart_snapshots_read" ON public.chart_snapshots
    FOR SELECT TO authenticated USING (true);

-- mt5_logs : logs d'exécution MT5 — lecture seule (historique).
DROP POLICY IF EXISTS "mt5_logs_read" ON public.mt5_logs;
CREATE POLICY "mt5_logs_read" ON public.mt5_logs
    FOR SELECT TO authenticated USING (true);

-- session_id : mapping session → user, restreint au propriétaire.
DROP POLICY IF EXISTS "session_id_own_select" ON public.session_id;
CREATE POLICY "session_id_own_select" ON public.session_id
    FOR SELECT TO authenticated USING (auth.uid() = user_id);
