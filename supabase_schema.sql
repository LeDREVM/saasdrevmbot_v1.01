-- ============================================================
--  DreVM Trading — Schéma Supabase
--  Coller dans : Supabase Dashboard → SQL Editor → Run
-- ============================================================

-- Extension pour UUID
create extension if not exists "pgcrypto";

-- ============================================================
--  TABLE : mt5_signals
--  Reçoit chaque signal envoyé par DreVM_Bridge.mq5
-- ============================================================
create table if not exists public.mt5_signals (
    id              uuid        primary key default gen_random_uuid(),
    created_at      timestamptz default now(),

    -- Identification
    symbol          text        not null,
    timeframe       text        not null,
    bar_time        timestamptz not null,

    -- OHLCV
    open            numeric(18,8) not null,
    high            numeric(18,8) not null,
    low             numeric(18,8) not null,
    close           numeric(18,8) not null,
    volume          bigint       default 0,
    spread          integer      default 0,

    -- Indicateurs
    rsi             numeric(6,2),
    wyckoff_event   text,        -- SC, BC, Spring, UT, SOS, SOW, NONE
    score           integer,     -- -10 à +10
    bias            text,        -- BULL_FORT, BULL, NEUTRE, BEAR, BEAR_FORT
    session         text,        -- NY, LDN_OPEN, LDN_CLOSE, ASIAN, AUTRE

    -- Fibonacci
    fib_618         numeric(18,8),
    fib_786         numeric(18,8)
);

-- Index pour requêtes fréquentes
create index if not exists idx_signals_symbol_time  on public.mt5_signals (symbol, bar_time desc);
create index if not exists idx_signals_bias         on public.mt5_signals (bias);
create index if not exists idx_signals_session      on public.mt5_signals (session);
create index if not exists idx_signals_wyckoff      on public.mt5_signals (wyckoff_event);
create index if not exists idx_signals_score        on public.mt5_signals (score desc);

-- ============================================================
--  TABLE : mt5_events
--  Événements intra-bar (FVG, OB cassé, etc.)
-- ============================================================
create table if not exists public.mt5_events (
    id          uuid        primary key default gen_random_uuid(),
    created_at  timestamptz default now(),
    symbol      text        not null,
    event_type  text        not null,  -- FVG_BULL, FVG_BEAR, OB_BULL, OB_BEAR
    price       numeric(18,8),
    event_time  timestamptz
);

create index if not exists idx_events_symbol on public.mt5_events (symbol, created_at desc);

-- ============================================================
--  TABLE : journal_entries
--  Journal de trading enrichi (auto + manuel)
-- ============================================================
create table if not exists public.journal_entries (
    id              uuid        primary key default gen_random_uuid(),
    created_at      timestamptz default now(),

    -- Signal source
    symbol          text        not null,
    timeframe       text,
    bar_time        timestamptz,
    session         text,

    -- Analyse
    bias            text,
    score           integer,
    wyckoff_event   text,
    rsi             numeric(6,2),
    close_price     numeric(18,8),
    fib_618         numeric(18,8),
    fib_786         numeric(18,8),

    -- Trade réel (rempli manuellement ou via EA)
    entry_price     numeric(18,8),
    sl_price        numeric(18,8),
    tp_price        numeric(18,8),
    lot_size        numeric(10,4),
    pnl_pips        numeric(10,2),
    pnl_usd         numeric(12,2),
    trade_result    text,   -- WIN, LOSS, BREAKEVEN, OPEN

    -- Notes
    notes           text,
    screenshot_url  text,
    tags            text[]   -- ex: ['FVG', 'OB', 'NY_session']
);

create index if not exists idx_journal_symbol on public.journal_entries (symbol, bar_time desc);
create index if not exists idx_journal_result on public.journal_entries (trade_result);

-- ============================================================
--  TABLE : performance_stats
--  Vue agrégée auto-rafraîchie
-- ============================================================
create or replace view public.performance_stats as
select
    symbol,
    session,
    bias,
    wyckoff_event,
    count(*)                                          as total_signals,
    round(avg(score)::numeric, 2)                     as avg_score,
    count(*) filter (where trade_result = 'WIN')      as wins,
    count(*) filter (where trade_result = 'LOSS')     as losses,
    count(*) filter (where trade_result = 'BREAKEVEN') as breakevens,
    round(
        100.0 * count(*) filter (where trade_result = 'WIN') /
        nullif(count(*) filter (where trade_result in ('WIN','LOSS')), 0),
    2)                                                as winrate_pct,
    round(sum(pnl_usd)::numeric, 2)                  as total_pnl_usd,
    round(avg(pnl_pips)::numeric, 2)                 as avg_pnl_pips
from public.journal_entries
group by symbol, session, bias, wyckoff_event
order by total_pnl_usd desc;

-- ============================================================
--  ROW LEVEL SECURITY (optionnel mais recommandé)
-- ============================================================
alter table public.mt5_signals    enable row level security;
alter table public.mt5_events     enable row level security;
alter table public.journal_entries enable row level security;

-- Politique : accès total pour le service role (utilisé par n8n)
create policy "service_role_all_signals"
    on public.mt5_signals for all
    using (auth.role() = 'service_role');

create policy "service_role_all_events"
    on public.mt5_events for all
    using (auth.role() = 'service_role');

create policy "service_role_all_journal"
    on public.journal_entries for all
    using (auth.role() = 'service_role');

-- Politique : lecture pour utilisateurs authentifiés
create policy "authenticated_read_signals"
    on public.mt5_signals for select
    using (auth.role() = 'authenticated');

create policy "authenticated_read_journal"
    on public.journal_entries for select
    using (auth.role() = 'authenticated');

-- ============================================================
--  REALTIME (pour dashboard live)
--  Supabase Dashboard → Database → Replication → mt5_signals
-- ============================================================
-- alter publication supabase_realtime add table public.mt5_signals;
-- alter publication supabase_realtime add table public.mt5_events;

-- ============================================================
--  DONNÉES DE TEST
-- ============================================================
/*
insert into public.mt5_signals (symbol, timeframe, bar_time, open, high, low, close, volume, rsi, wyckoff_event, score, bias, session, fib_618, fib_786)
values ('EURUSD', 'PERIOD_M15', now(), 1.08450, 1.08490, 1.08420, 1.08480, 1234, 42.5, 'Spring', 6, 'BULL_FORT', 'NY', 1.08350, 1.08400);
*/
