-- ============================================================================
--  Trading Journal (style FTMO) — DREVM
--  Tables de journalisation MANUELLE, distinctes des tables automatiques du
--  pipeline (trade_signals / positions / trading_sessions / alert_logs).
--
--    journal_trades   : date, symbole, sens, entry, sl, tp, résultat, R, screenshots
--    journal_sessions : date, biais, news, commentaire
--    journal_rules    : risk/jour, max trades/jour, drawdown lock (1 ligne / user)
--    journal_alerts   : événement, impact, heure, devise, note
--
--  Idempotent (IF NOT EXISTS / DROP POLICY IF EXISTS). RLS par utilisateur.
-- ============================================================================

-- ── Enums ────────────────────────────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE trade_direction AS ENUM ('buy', 'sell');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE trade_result AS ENUM ('win', 'loss', 'breakeven', 'running');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- event_impact peut déjà exister (schéma de base) ; sinon on le crée.
DO $$ BEGIN
    CREATE TYPE event_impact AS ENUM ('low', 'medium', 'high');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Fonction updated_at (réutilise celle du schéma de base ; recréée pour être autonome)
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SET search_path = '';

-- ── journal_trades ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journal_trades (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trade_date   DATE NOT NULL DEFAULT CURRENT_DATE,
    symbol       TEXT NOT NULL,
    direction    trade_direction NOT NULL,
    entry        NUMERIC(18, 5),
    sl           NUMERIC(18, 5),
    tp           NUMERIC(18, 5),
    result       trade_result NOT NULL DEFAULT 'running',
    r_multiple   NUMERIC(8, 2),                 -- résultat en R (ex: +2.00, -1.00)
    screenshots  TEXT[] NOT NULL DEFAULT '{}',  -- URLs/paths Supabase Storage
    notes        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_journal_trades_user ON public.journal_trades(user_id, trade_date DESC);
CREATE INDEX IF NOT EXISTS idx_journal_trades_symbol ON public.journal_trades(symbol, trade_date DESC);

-- ── journal_sessions ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journal_sessions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    session_date DATE NOT NULL DEFAULT CURRENT_DATE,
    bias         TEXT,           -- biais du jour (ex: bullish / bearish / neutral)
    news         TEXT,           -- news / événements à surveiller
    comment      TEXT,           -- commentaire libre
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, session_date)
);
CREATE INDEX IF NOT EXISTS idx_journal_sessions_user ON public.journal_sessions(user_id, session_date DESC);

-- ── journal_rules (1 ligne par utilisateur) ─────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journal_rules (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    risk_per_day_pct      NUMERIC(5, 2) NOT NULL DEFAULT 3.00,   -- risque max / jour (%)
    max_trades_per_day    INTEGER NOT NULL DEFAULT 3,
    drawdown_lock_pct     NUMERIC(5, 2) NOT NULL DEFAULT 4.00,   -- DD journalier qui verrouille
    drawdown_locked       BOOLEAN NOT NULL DEFAULT FALSE,         -- état de verrouillage courant
    risk_per_trade_pct    NUMERIC(5, 2) NOT NULL DEFAULT 1.00,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── journal_alerts ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.journal_alerts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    event        TEXT NOT NULL,          -- nom de l'événement
    impact       event_impact NOT NULL DEFAULT 'medium',
    alert_time   TIMESTAMPTZ NOT NULL,   -- heure de l'événement
    currency     TEXT,                   -- devise concernée (USD, EUR, ...)
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_journal_alerts_user ON public.journal_alerts(user_id, alert_time DESC);
CREATE INDEX IF NOT EXISTS idx_journal_alerts_currency ON public.journal_alerts(currency, alert_time DESC);

-- ── Triggers updated_at ──────────────────────────────────────────────────────
DROP TRIGGER IF EXISTS update_journal_trades_updated_at ON public.journal_trades;
CREATE TRIGGER update_journal_trades_updated_at
    BEFORE UPDATE ON public.journal_trades
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_journal_sessions_updated_at ON public.journal_sessions;
CREATE TRIGGER update_journal_sessions_updated_at
    BEFORE UPDATE ON public.journal_sessions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_journal_rules_updated_at ON public.journal_rules;
CREATE TRIGGER update_journal_rules_updated_at
    BEFORE UPDATE ON public.journal_rules
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_journal_alerts_updated_at ON public.journal_alerts;
CREATE TRIGGER update_journal_alerts_updated_at
    BEFORE UPDATE ON public.journal_alerts
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ── Row Level Security : chaque utilisateur ne voit/écrit que ses lignes ──────
ALTER TABLE public.journal_trades   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journal_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journal_rules    ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.journal_alerts   ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['journal_trades', 'journal_sessions', 'journal_rules', 'journal_alerts']
    LOOP
        EXECUTE format('DROP POLICY IF EXISTS "own_select" ON public.%I;', t);
        EXECUTE format('CREATE POLICY "own_select" ON public.%I FOR SELECT USING (auth.uid() = user_id);', t);
        EXECUTE format('DROP POLICY IF EXISTS "own_insert" ON public.%I;', t);
        EXECUTE format('CREATE POLICY "own_insert" ON public.%I FOR INSERT WITH CHECK (auth.uid() = user_id);', t);
        EXECUTE format('DROP POLICY IF EXISTS "own_update" ON public.%I;', t);
        EXECUTE format('CREATE POLICY "own_update" ON public.%I FOR UPDATE USING (auth.uid() = user_id);', t);
        EXECUTE format('DROP POLICY IF EXISTS "own_delete" ON public.%I;', t);
        EXECUTE format('CREATE POLICY "own_delete" ON public.%I FOR DELETE USING (auth.uid() = user_id);', t);
    END LOOP;
END $$;
