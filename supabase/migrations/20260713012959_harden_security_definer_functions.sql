-- ============================================================================
--  Durcissement des fonctions SECURITY DEFINER exposées (advisor 0011/0028/0029).
--
--  rls_auto_enable() : event trigger interne (auto-active la RLS). Ne doit JAMAIS
--    être appelable via l'API REST → révoqué de PUBLIC/anon/authenticated.
--  session_id(text,uuid) : upsert session→user, SECURITY DEFINER sans search_path.
--    On fixe search_path='' et on le réserve au service_role. Table vide
--    (scaffolding) ; si le front doit l'appeler, refaire :
--      GRANT EXECUTE ON FUNCTION public.session_id(text, uuid) TO authenticated;
--  Idempotent.
-- ============================================================================

REVOKE ALL ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.rls_auto_enable() TO service_role;

ALTER FUNCTION public.session_id(text, uuid) SET search_path = '';
REVOKE ALL ON FUNCTION public.session_id(text, uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.session_id(text, uuid) TO service_role;
