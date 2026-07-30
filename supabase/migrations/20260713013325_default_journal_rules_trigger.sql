-- ============================================================================
--  À chaque inscription (auth.users insert), crée une ligne journal_rules par
--  défaut pour le nouvel utilisateur. SECURITY DEFINER (écrit dans public depuis
--  le contexte auth) + search_path='' (advisor). Idempotent.
-- ============================================================================

CREATE OR REPLACE FUNCTION public.create_default_journal_rules()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
BEGIN
    INSERT INTO public.journal_rules (user_id)
    VALUES (NEW.id)
    ON CONFLICT (user_id) DO NOTHING;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created_journal_rules ON auth.users;
CREATE TRIGGER on_auth_user_created_journal_rules
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.create_default_journal_rules();
