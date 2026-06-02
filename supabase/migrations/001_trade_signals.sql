-- ============================================================
-- SCHEMA : TradingView AI Signal Pipeline
-- ============================================================

-- Snapshots de charts TradingView
CREATE TABLE IF NOT EXISTS chart_snapshots (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol        TEXT NOT NULL,           -- ex: "EURUSD", "XAUUSD"
  timeframe     TEXT NOT NULL,           -- ex: "H1", "H4", "D1"
  source_url    TEXT,                    -- URL TradingView originale
  screenshot_url TEXT,                  -- URL public dans Supabase Storage
  raw_payload   JSONB,                  -- payload complet de l'alerte TradingView
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Signaux IA analysés à partir des snapshots
CREATE TABLE IF NOT EXISTS trade_signals (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  snapshot_id     UUID REFERENCES chart_snapshots(id) ON DELETE CASCADE,
  symbol          TEXT NOT NULL,
  timeframe       TEXT NOT NULL,
  direction       TEXT CHECK (direction IN ('BUY','SELL','NEUTRAL')),
  score           NUMERIC(4,2),          -- 0.00 à 10.00
  confidence      NUMERIC(4,2),          -- 0.00 à 1.00 (probabilité)
  entry_price     NUMERIC(12,5),
  stop_loss       NUMERIC(12,5),
  take_profit_1   NUMERIC(12,5),
  take_profit_2   NUMERIC(12,5),
  risk_reward     NUMERIC(6,2),
  ai_analysis     TEXT,                 -- analyse complète retournée par l'IA
  ai_model        TEXT DEFAULT 'claude-sonnet-4-6',
  status          TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING','SENT','EXECUTED','CANCELLED')),
  mt5_ticket      BIGINT,               -- ticket MetaTrader une fois exécuté
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  sent_at         TIMESTAMPTZ
);

-- Logs d'envoi vers MetaTrader
CREATE TABLE IF NOT EXISTS mt5_logs (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id     UUID REFERENCES trade_signals(id) ON DELETE CASCADE,
  action        TEXT,                   -- "SEND", "ACK", "ERROR"
  payload       JSONB,
  response      JSONB,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Index performance
CREATE INDEX idx_signals_symbol    ON trade_signals(symbol);
CREATE INDEX idx_signals_status    ON trade_signals(status);
CREATE INDEX idx_signals_score     ON trade_signals(score DESC);
CREATE INDEX idx_snapshots_created ON chart_snapshots(created_at DESC);

-- Bucket Supabase Storage pour les screenshots
-- (à exécuter manuellement dans Storage > New Bucket)
-- Nom: "chart-screenshots", Public: true
