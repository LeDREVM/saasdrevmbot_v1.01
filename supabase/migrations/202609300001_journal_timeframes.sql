ALTER TABLE public.journal_trades ADD COLUMN IF NOT EXISTS timeframe TEXT;
-- Existing trades retain an unknown timeframe; never invent historical context.
DO $$ BEGIN
ALTER TABLE public.journal_trades ADD CONSTRAINT journal_timeframe_valid
  CHECK (timeframe IS NULL OR timeframe IN ('H4', 'M15', 'M5'));

EXCEPTION WHEN duplicate_object THEN NULL; END $$;
