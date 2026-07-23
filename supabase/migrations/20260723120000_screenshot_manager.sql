-- ============================================================================
--  Screenshot Manager — DREVM
--  Table de métadonnées pour les captures d'écran stockées dans le bucket
--  "trade-screenshots" (créé par 20260713012222_trade_screenshots_bucket.sql).
--
--  Permet : captures autonomes (hors trade), tags symbole/TF/grade,
--  liaison optionnelle à un journal_trades, recherche/filtre côté front.
--
--  Idempotent (IF NOT EXISTS / DROP POLICY IF EXISTS). RLS par utilisateur.
-- ============================================================================

-- ── journal_screenshots ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journal_screenshots (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL UNIQUE,          -- chemin dans le bucket ({user_id}/...)
    symbol       TEXT,                          -- XAUUSD, US30, USDJPY, CADJPY, USDCAD...
    timeframe    TEXT,                          -- M1..W1 (libre pour rester souple)
    grade        TEXT CHECK (grade IS NULL OR grade IN ('A+','A','B','C','D')),
    tags         TEXT[] NOT NULL DEFAULT '{}',  -- ex: {sweep, mss, fvg, ny-open}
    note         TEXT,
    trade_id     UUID REFERENCES public.journal_trades(id) ON DELETE SET NULL,
    taken_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- moment de la capture
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_journal_screenshots_user
    ON public.journal_screenshots(user_id, taken_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_screenshots_symbol
    ON public.journal_screenshots(symbol, taken_at DESC);
CREATE INDEX IF NOT EXISTS idx_journal_screenshots_trade
    ON public.journal_screenshots(trade_id);

-- updated_at automatique (fonction partagée du schéma journal)
DROP TRIGGER IF EXISTS trg_journal_screenshots_updated ON public.journal_screenshots;
CREATE TRIGGER trg_journal_screenshots_updated
    BEFORE UPDATE ON public.journal_screenshots
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ── RLS ──────────────────────────────────────────────────────────────────────
ALTER TABLE public.journal_screenshots ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "journal_screenshots_select" ON public.journal_screenshots;
CREATE POLICY "journal_screenshots_select" ON public.journal_screenshots
    FOR SELECT TO authenticated USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "journal_screenshots_insert" ON public.journal_screenshots;
CREATE POLICY "journal_screenshots_insert" ON public.journal_screenshots
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "journal_screenshots_update" ON public.journal_screenshots;
CREATE POLICY "journal_screenshots_update" ON public.journal_screenshots
    FOR UPDATE TO authenticated
    USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "journal_screenshots_delete" ON public.journal_screenshots;
CREATE POLICY "journal_screenshots_delete" ON public.journal_screenshots
    FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- ── Rétro-compatibilité ──────────────────────────────────────────────────────
-- Importe dans la table les chemins déjà présents dans journal_trades.screenshots
-- (idempotent grâce à l'UNIQUE sur storage_path + ON CONFLICT DO NOTHING).
INSERT INTO public.journal_screenshots (user_id, storage_path, symbol, trade_id, taken_at)
SELECT t.user_id, s.path, t.symbol, t.id, t.created_at
FROM public.journal_trades t
CROSS JOIN LATERAL unnest(t.screenshots) AS s(path)
WHERE t.screenshots <> '{}'
ON CONFLICT (storage_path) DO NOTHING;
