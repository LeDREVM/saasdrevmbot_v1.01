-- ============================================================================
-- DREVM Trading Sessions - Schema Complet Supabase (IDEMPOTENT)
-- ============================================================================
-- Migration idempotente: peut être exécutée plusieurs fois sans erreur
-- ============================================================================

-- ============================================================================
-- 1. TYPES ENUMS
-- ============================================================================

DO $$ BEGIN
    CREATE TYPE session_type AS ENUM ('tokyo', 'london', 'ny', 'manual');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE session_status AS ENUM ('scheduled', 'active', 'closed', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE htf_phase AS ENUM ('accumulation', 'markup', 'distribution', 'markdown');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE fib_zone AS ENUM ('shallow', 'equilibrium', 'sniper', 'deep');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE setup_type AS ENUM ('none', 'continuation', 'reversal', 'range_buy', 'range_sell');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE setup_grade AS ENUM ('C', 'B', 'A', 'A+');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE signal_status AS ENUM ('pending', 'executed', 'expired', 'cancelled');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE position_status AS ENUM ('open', 'partial_close', 'closed');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE exit_reason AS ENUM ('tp1', 'tp2', 'sl', 'breakeven', 'manual', 'timeout');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE metric_period AS ENUM ('daily', 'weekly', 'monthly', 'all_time');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE event_impact AS ENUM ('low', 'medium', 'high');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_channel AS ENUM ('discord', 'telegram');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_type AS ENUM ('signal', 'session_start', 'session_end', 'economic_event', 'position_update');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- ============================================================================
-- 2. TABLES
-- ============================================================================

-- User Profiles
CREATE TABLE IF NOT EXISTS public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT,
    broker_account_id TEXT,
    risk_percentage DECIMAL(5,2) DEFAULT 1.0 CHECK (risk_percentage > 0 AND risk_percentage <= 5),
    max_daily_drawdown DECIMAL(10,2) DEFAULT 500.00,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_username ON public.user_profiles(username);

-- Trading Sessions
CREATE TABLE IF NOT EXISTS public.trading_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    session_type session_type NOT NULL,
    session_date DATE NOT NULL,
    scheduled_start TIMESTAMPTZ NOT NULL,
    scheduled_end TIMESTAMPTZ NOT NULL,
    actual_start TIMESTAMPTZ,
    actual_end TIMESTAMPTZ,
    status session_status DEFAULT 'scheduled',
    
    symbol TEXT NOT NULL DEFAULT 'EURUSD',
    initial_balance DECIMAL(12,2),
    final_balance DECIMAL(12,2),
    
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    breakeven_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0,
    max_drawdown DECIMAL(12,2) DEFAULT 0,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trading_sessions_user ON public.trading_sessions(user_id, session_date DESC);
CREATE INDEX IF NOT EXISTS idx_trading_sessions_status ON public.trading_sessions(status);

-- Market Contexts
CREATE TABLE IF NOT EXISTS public.market_contexts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.trading_sessions(id) ON DELETE CASCADE,
    
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol TEXT NOT NULL DEFAULT 'EURUSD',
    
    h4_phase htf_phase,
    h4_trend TEXT CHECK (h4_trend IN ('up', 'down', 'range')),
    h4_bias TEXT CHECK (h4_bias IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    
    m15_fib_zone fib_zone,
    m15_is_logical_zone BOOLEAN DEFAULT FALSE,
    m15_zone_touched BOOLEAN DEFAULT FALSE,
    
    m5_trigger TEXT CHECK (m5_trigger IN ('BUY_TRIGGER', 'SELL_TRIGGER')),
    m5_bos_direction TEXT CHECK (m5_bos_direction IN ('up', 'down')),
    swept_liquidity_side_m5 TEXT CHECK (swept_liquidity_side_m5 IN ('high', 'low')),
    
    rsi_divergence TEXT CHECK (rsi_divergence IN ('BULLISH', 'BEARISH')),
    wyckoff_pattern TEXT CHECK (wyckoff_pattern IN ('SPRING', 'UTAD')),
    price_above_kijun BOOLEAN DEFAULT FALSE,
    
    current_price DECIMAL(10,5),
    current_atr DECIMAL(10,5),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_market_contexts_session ON public.market_contexts(session_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_contexts_symbol ON public.market_contexts(symbol, captured_at DESC);

-- Trade Signals
CREATE TABLE IF NOT EXISTS public.trade_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES public.trading_sessions(id) ON DELETE CASCADE,
    context_id UUID REFERENCES public.market_contexts(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol TEXT NOT NULL DEFAULT 'EURUSD',
    direction TEXT NOT NULL CHECK (direction IN ('up', 'down')),
    setup_type setup_type NOT NULL,
    grade setup_grade NOT NULL,
    status signal_status DEFAULT 'pending',
    
    entry_price DECIMAL(10,5),
    stop_loss DECIMAL(10,5),
    take_profit_1 DECIMAL(10,5),
    take_profit_2 DECIMAL(10,5),
    
    risk_amount DECIMAL(10,2),
    position_size DECIMAL(10,4),
    rr_ratio DECIMAL(5,2),
    
    h4_ok BOOLEAN DEFAULT FALSE,
    m15_zone_ok BOOLEAN DEFAULT FALSE,
    fib_ok BOOLEAN DEFAULT FALSE,
    liquidity_ok BOOLEAN DEFAULT FALSE,
    trigger_ok BOOLEAN DEFAULT FALSE,
    rr_ok BOOLEAN DEFAULT FALSE,
    
    confluence_score INTEGER,
    reasons JSONB,
    
    expires_at TIMESTAMPTZ,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trade_signals_session ON public.trade_signals(session_id, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_signals_user ON public.trade_signals(user_id, status);
CREATE INDEX IF NOT EXISTS idx_trade_signals_grade ON public.trade_signals(grade, status);

-- Positions
CREATE TABLE IF NOT EXISTS public.positions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID REFERENCES public.trade_signals(id) ON DELETE SET NULL,
    session_id UUID REFERENCES public.trading_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    broker_order_id TEXT,
    symbol TEXT NOT NULL DEFAULT 'EURUSD',
    direction TEXT NOT NULL CHECK (direction IN ('up', 'down')),
    
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    entry_price DECIMAL(10,5) NOT NULL,
    position_size DECIMAL(10,4) NOT NULL,
    stop_loss DECIMAL(10,5) NOT NULL,
    take_profit DECIMAL(10,5),
    
    status position_status DEFAULT 'open',
    closed_at TIMESTAMPTZ,
    exit_price DECIMAL(10,5),
    exit_reason exit_reason,
    
    pnl DECIMAL(12,2) DEFAULT 0,
    pnl_pips DECIMAL(10,2) DEFAULT 0,
    r_multiple DECIMAL(5,2),
    
    partial_close_at TIMESTAMPTZ,
    partial_close_size DECIMAL(10,4),
    remaining_size DECIMAL(10,4),
    breakeven_moved BOOLEAN DEFAULT FALSE,
    
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_positions_session ON public.positions(session_id, opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_positions_user ON public.positions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_positions_signal ON public.positions(signal_id);

-- Performance Metrics
CREATE TABLE IF NOT EXISTS public.performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    
    period_type metric_period NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    total_sessions INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    breakeven_trades INTEGER DEFAULT 0,
    
    total_pnl DECIMAL(12,2) DEFAULT 0,
    win_rate DECIMAL(5,2),
    avg_win DECIMAL(10,2),
    avg_loss DECIMAL(10,2),
    profit_factor DECIMAL(6,2),
    expectancy DECIMAL(10,2),
    
    max_drawdown DECIMAL(12,2),
    max_consecutive_wins INTEGER DEFAULT 0,
    max_consecutive_losses INTEGER DEFAULT 0,
    sharpe_ratio DECIMAL(6,2),
    
    a_plus_trades INTEGER DEFAULT 0,
    a_plus_win_rate DECIMAL(5,2),
    a_trades INTEGER DEFAULT 0,
    a_win_rate DECIMAL(5,2),
    b_trades INTEGER DEFAULT 0,
    b_win_rate DECIMAL(5,2),
    c_trades INTEGER DEFAULT 0,
    c_win_rate DECIMAL(5,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, period_type, period_start)
);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_user ON public.performance_metrics(user_id, period_start DESC);

-- Economic Events
CREATE TABLE IF NOT EXISTS public.economic_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source TEXT NOT NULL,
    event_date DATE NOT NULL,
    event_time TIME NOT NULL,
    currency TEXT NOT NULL,
    event_name TEXT NOT NULL,
    impact event_impact NOT NULL,
    
    actual TEXT,
    forecast TEXT,
    previous TEXT,
    
    price_move_5min DECIMAL(10,5),
    price_move_15min DECIMAL(10,5),
    price_move_1h DECIMAL(10,5),
    volatility_spike BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_economic_events_date ON public.economic_events(event_date DESC, event_time);
CREATE INDEX IF NOT EXISTS idx_economic_events_currency ON public.economic_events(currency, event_date DESC);
CREATE INDEX IF NOT EXISTS idx_economic_events_impact ON public.economic_events(impact, event_date DESC);

-- Alert Logs
CREATE TABLE IF NOT EXISTS public.alert_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.user_profiles(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES public.trade_signals(id) ON DELETE SET NULL,
    position_id UUID REFERENCES public.positions(id) ON DELETE SET NULL,
    
    alert_type alert_type NOT NULL,
    channel alert_channel NOT NULL,
    
    message TEXT NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_logs_user ON public.alert_logs(user_id, sent_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_logs_signal ON public.alert_logs(signal_id);

-- ============================================================================
-- 3. ROW LEVEL SECURITY
-- ============================================================================

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trading_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.market_contexts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.performance_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alert_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.economic_events ENABLE ROW LEVEL SECURITY;

-- Policies user_profiles
DROP POLICY IF EXISTS "Users can view own profile" ON public.user_profiles;
CREATE POLICY "Users can view own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.user_profiles;
CREATE POLICY "Users can update own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- Policies trading_sessions
DROP POLICY IF EXISTS "Users can view own sessions" ON public.trading_sessions;
CREATE POLICY "Users can view own sessions"
    ON public.trading_sessions FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own sessions" ON public.trading_sessions;
CREATE POLICY "Users can insert own sessions"
    ON public.trading_sessions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own sessions" ON public.trading_sessions;
CREATE POLICY "Users can update own sessions"
    ON public.trading_sessions FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies market_contexts
DROP POLICY IF EXISTS "Users can view contexts of own sessions" ON public.market_contexts;
CREATE POLICY "Users can view contexts of own sessions"
    ON public.market_contexts FOR SELECT
    USING (
        session_id IN (
            SELECT id FROM public.trading_sessions WHERE user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert contexts for own sessions" ON public.market_contexts;
CREATE POLICY "Users can insert contexts for own sessions"
    ON public.market_contexts FOR INSERT
    WITH CHECK (
        session_id IN (
            SELECT id FROM public.trading_sessions WHERE user_id = auth.uid()
        )
    );

-- Policies trade_signals
DROP POLICY IF EXISTS "Users can view own signals" ON public.trade_signals;
CREATE POLICY "Users can view own signals"
    ON public.trade_signals FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own signals" ON public.trade_signals;
CREATE POLICY "Users can insert own signals"
    ON public.trade_signals FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own signals" ON public.trade_signals;
CREATE POLICY "Users can update own signals"
    ON public.trade_signals FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies positions
DROP POLICY IF EXISTS "Users can view own positions" ON public.positions;
CREATE POLICY "Users can view own positions"
    ON public.positions FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own positions" ON public.positions;
CREATE POLICY "Users can insert own positions"
    ON public.positions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own positions" ON public.positions;
CREATE POLICY "Users can update own positions"
    ON public.positions FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies performance_metrics
DROP POLICY IF EXISTS "Users can view own metrics" ON public.performance_metrics;
CREATE POLICY "Users can view own metrics"
    ON public.performance_metrics FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own metrics" ON public.performance_metrics;
CREATE POLICY "Users can insert own metrics"
    ON public.performance_metrics FOR INSERT
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update own metrics" ON public.performance_metrics;
CREATE POLICY "Users can update own metrics"
    ON public.performance_metrics FOR UPDATE
    USING (auth.uid() = user_id);

-- Policies alert_logs
DROP POLICY IF EXISTS "Users can view own alerts" ON public.alert_logs;
CREATE POLICY "Users can view own alerts"
    ON public.alert_logs FOR SELECT
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert own alerts" ON public.alert_logs;
CREATE POLICY "Users can insert own alerts"
    ON public.alert_logs FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Economic events: visible par tous
DROP POLICY IF EXISTS "Anyone can view economic events" ON public.economic_events;
CREATE POLICY "Anyone can view economic events"
    ON public.economic_events FOR SELECT
    USING (true);

DROP POLICY IF EXISTS "Service role can manage economic events" ON public.economic_events;
CREATE POLICY "Service role can manage economic events"
    ON public.economic_events FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ============================================================================
-- 4. FUNCTIONS & TRIGGERS
-- ============================================================================

-- Fonction update_updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers updated_at (DROP IF EXISTS pour éviter erreurs)
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON public.user_profiles;
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_trading_sessions_updated_at ON public.trading_sessions;
CREATE TRIGGER update_trading_sessions_updated_at
    BEFORE UPDATE ON public.trading_sessions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_trade_signals_updated_at ON public.trade_signals;
CREATE TRIGGER update_trade_signals_updated_at
    BEFORE UPDATE ON public.trade_signals
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_positions_updated_at ON public.positions;
CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON public.positions
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_performance_metrics_updated_at ON public.performance_metrics;
CREATE TRIGGER update_performance_metrics_updated_at
    BEFORE UPDATE ON public.performance_metrics
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_economic_events_updated_at ON public.economic_events;
CREATE TRIGGER update_economic_events_updated_at
    BEFORE UPDATE ON public.economic_events
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- Fonction calcul R-multiple
CREATE OR REPLACE FUNCTION public.calculate_r_multiple()
RETURNS TRIGGER AS $$
DECLARE
    risk_amount DECIMAL(10,5);
    pnl_amount DECIMAL(10,5);
BEGIN
    IF NEW.exit_price IS NOT NULL AND NEW.status IN ('partial_close', 'closed') THEN
        IF NEW.direction = 'up' THEN
            risk_amount := NEW.entry_price - NEW.stop_loss;
            pnl_amount := NEW.exit_price - NEW.entry_price;
        ELSE
            risk_amount := NEW.stop_loss - NEW.entry_price;
            pnl_amount := NEW.entry_price - NEW.exit_price;
        END IF;
        
        IF risk_amount > 0 THEN
            NEW.r_multiple := pnl_amount / risk_amount;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS calculate_position_r_multiple ON public.positions;
CREATE TRIGGER calculate_position_r_multiple
    BEFORE UPDATE ON public.positions
    FOR EACH ROW
    WHEN (NEW.exit_price IS NOT NULL)
    EXECUTE FUNCTION public.calculate_r_multiple();

-- ============================================================================
-- 5. VUES
-- ============================================================================

DROP VIEW IF EXISTS public.active_signals CASCADE;
CREATE OR REPLACE VIEW public.active_signals AS
SELECT 
    s.*,
    mc.h4_phase,
    mc.h4_bias,
    mc.m15_fib_zone,
    mc.rsi_divergence,
    mc.wyckoff_pattern,
    ts.session_type,
    ts.session_date
FROM public.trade_signals s
LEFT JOIN public.market_contexts mc ON s.context_id = mc.id
LEFT JOIN public.trading_sessions ts ON s.session_id = ts.id
WHERE s.status = 'pending'
AND (s.expires_at IS NULL OR s.expires_at > NOW());

DROP VIEW IF EXISTS public.open_positions_summary CASCADE;
CREATE OR REPLACE VIEW public.open_positions_summary AS
SELECT 
    p.*,
    s.grade AS signal_grade,
    s.setup_type,
    ts.session_type,
    ts.session_date,
    EXTRACT(EPOCH FROM (NOW() - p.opened_at))/60 AS duration_minutes
FROM public.positions p
LEFT JOIN public.trade_signals s ON p.signal_id = s.id
LEFT JOIN public.trading_sessions ts ON p.session_id = ts.id
WHERE p.status IN ('open', 'partial_close');

DROP VIEW IF EXISTS public.performance_by_grade CASCADE;
CREATE OR REPLACE VIEW public.performance_by_grade AS
SELECT 
    s.user_id,
    s.grade,
    COUNT(*) AS total_signals,
    COUNT(p.id) AS executed_trades,
    SUM(CASE WHEN p.pnl > 0 THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN p.pnl < 0 THEN 1 ELSE 0 END) AS losses,
    ROUND(AVG(p.pnl), 2) AS avg_pnl,
    ROUND(AVG(p.r_multiple), 2) AS avg_r_multiple,
    ROUND(
        100.0 * SUM(CASE WHEN p.pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(p.id), 0),
        2
    ) AS win_rate
FROM public.trade_signals s
LEFT JOIN public.positions p ON s.id = p.signal_id
WHERE p.status = 'closed'
GROUP BY s.user_id, s.grade;

-- ============================================================================
-- COMMENTAIRES
-- ============================================================================

COMMENT ON TABLE public.trading_sessions IS 'Sessions de trading actives et historiques (Tokyo, Londres, NY)';
COMMENT ON TABLE public.market_contexts IS 'Snapshots du contexte de marché multi-timeframe (H4/M15/M5)';
COMMENT ON TABLE public.trade_signals IS 'Signaux de trading générés avec scoring A+/A/B/C';
COMMENT ON TABLE public.positions IS 'Positions ouvertes/fermées avec gestion partielle (TP1 50% → breakeven → trailing)';
COMMENT ON TABLE public.performance_metrics IS 'Métriques de performance agrégées par période';
COMMENT ON TABLE public.economic_events IS 'Calendrier économique (ForexFactory, Investing, Trading Economics)';
