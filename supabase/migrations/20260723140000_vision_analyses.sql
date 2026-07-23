-- ============================================================================
--  Vision Analyses — DREVM
--  Historique des analyses intégrales IA (multi-captures / multi-timeframes).
--  Idempotent. RLS par utilisateur.
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.screenshot_analyses (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol         TEXT NOT NULL,
    screenshot_ids UUID[] NOT NULL DEFAULT '{}',   -- captures utilisées
    timeframes     TEXT[] NOT NULL DEFAULT '{}',
    grade          TEXT CHECK (grade IN ('A+','A','B','C','D')),
    action         TEXT CHECK (action IN ('LONG','SHORT','WAIT','SKIP')),
    bias_direction TEXT,
    bias_score     NUMERIC(4, 1),
    result         JSONB NOT NULL,                 -- analyse complète structurée
    model          TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_screenshot_analyses_user
    ON public.screenshot_analyses(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_screenshot_analyses_symbol
    ON public.screenshot_analyses(symbol, created_at DESC);

ALTER TABLE public.screenshot_analyses ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "screenshot_analyses_select" ON public.screenshot_analyses;
CREATE POLICY "screenshot_analyses_select" ON public.screenshot_analyses
    FOR SELECT TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "screenshot_analyses_insert" ON public.screenshot_analyses;
CREATE POLICY "screenshot_analyses_insert" ON public.screenshot_analyses
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "screenshot_analyses_delete" ON public.screenshot_analyses;
CREATE POLICY "screenshot_analyses_delete" ON public.screenshot_analyses
    FOR DELETE TO authenticated USING (auth.uid() = user_id);
