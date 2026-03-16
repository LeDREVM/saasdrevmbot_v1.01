/**
 * Correlation Engine — Analyse l'impact réel des événements économiques sur les prix
 *
 * • Persiste les événements dans data/events_log.json (90 jours)
 * • Récupère les données OHLCV 5m via yahoo-finance2 (déjà installé)
 * • Cache disque des données prix par journée (data/price_cache/)
 * • Cache mémoire des résultats 30 min pour éviter les recalculs
 *
 * Formats retournés compatibles avec les composants SvelteKit :
 *   CorrelationTable → summary.by_event_type (objet keyed)
 *   HeatmapView      → heatmap_data { "Monday": { 9: 80, 12: 40 } }
 *   ImpactChart      → top_impact_events [{ event: {...}, impact: {...} }]
 *   PriceTimeline    → timeline [{ timestamp, currency, event_name, direction, ... }]
 */

const path         = require('path');
const fs           = require('fs');
const YahooFinance = require('yahoo-finance2').default;

const yahooFinance = new YahooFinance({ suppressNotices: ['yahooSurvey'] });

// Retourne n si fini, sinon la valeur de repli (évite Infinity/NaN dans le JSON)
const safeN = (n, fallback = 0) => (Number.isFinite(n) ? n : fallback);

// ─── Chemins ──────────────────────────────────────────────────────────────────

const DATA_DIR  = path.join(__dirname, '../../data');
const LOG_FILE  = path.join(DATA_DIR, 'events_log.json');
const CACHE_DIR = path.join(DATA_DIR, 'price_cache');

// ─── Mappings symboles ────────────────────────────────────────────────────────

/** Conversion symbole GoldyXbOT → Yahoo Finance */
const SYMBOL_MAP = {
  'DJI':    '^DJI',
  'US30':   '^DJI',
  'SPX':    '^GSPC',
  'EURUSD': 'EURUSD=X',
  'GBPUSD': 'GBPUSD=X',
  'USDJPY': 'USDJPY=X',
  'AUDUSD': 'AUDUSD=X',
  'XAUUSD': 'GC=F',
};

/**
 * Facteur pip : nombre de pips pour 1 unité de mouvement du prix
 *   DJI/SPX : 1 point = 1 "pip"
 *   EURUSD  : 1 pip = 0.0001  → ×10 000
 *   USDJPY  : 1 pip = 0.01    → ×100
 *   XAUUSD  : 1 pip = 0.1     → ×10
 */
const PIP_FACTOR = {
  '^DJI':     1,
  '^GSPC':    1,
  'EURUSD=X': 10000,
  'GBPUSD=X': 10000,
  'USDJPY=X': 100,
  'AUDUSD=X': 10000,
  'GC=F':     10,
};

// ─── Cache mémoire résultats (30 min) ─────────────────────────────────────────

const _memCache     = {};
const _memCacheTime = {};
const CACHE_TTL     = 30 * 60 * 1000;

// ─── Utilitaires ──────────────────────────────────────────────────────────────

function ensureDirs() {
  if (!fs.existsSync(DATA_DIR))  fs.mkdirSync(DATA_DIR,  { recursive: true });
  if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });
}

// ─── Persistance des événements ───────────────────────────────────────────────

/**
 * Persiste un événement scraped dans data/events_log.json.
 * Appelé depuis scrapeAndNotify() à chaque upsertEvent().
 * Conserve 90 jours d'historique maximum.
 */
function logEvent(event) {
  if (!event?._parsedTime) return; // Ne logguer que les événements avec un timestamp précis

  try {
    ensureDirs();

    let events = [];
    if (fs.existsSync(LOG_FILE)) {
      try { events = JSON.parse(fs.readFileSync(LOG_FILE, 'utf8')); }
      catch {}
    }

    const idx = events.findIndex(e => e.id === event.id);
    if (idx >= 0) {
      // Mettre à jour le résultat (actual) si disponible
      if (event.actual && event.actual !== events[idx].actual) {
        events[idx] = {
          ...events[idx],
          actual:   event.actual,
          previous: event.previous,
        };
      }
    } else {
      events.push({
        id:          event.id,
        event:       event.event,
        currency:    event.currency,
        time:        event.time,
        date:        event.date,
        impactLevel: event.impactLevel,
        actual:      event.actual   || null,
        forecast:    event.forecast || null,
        previous:    event.previous || null,
        _parsedTime: event._parsedTime,
        _loggedAt:   Date.now(),
      });
    }

    // Garder 90 jours max
    const cutoff = Date.now() - 90 * 24 * 60 * 60 * 1000;
    events = events.filter(e => e._loggedAt > cutoff);

    fs.writeFileSync(LOG_FILE, JSON.stringify(events));
  } catch (err) {
    console.warn('[CorrelEngine] logEvent erreur:', err.message);
  }
}

/**
 * Lit les événements historiques persistés.
 * @param {number} daysBack - Fenêtre temporelle en jours
 */
function getHistoricalEvents(daysBack = 30) {
  if (!fs.existsSync(LOG_FILE)) return [];
  try {
    const events = JSON.parse(fs.readFileSync(LOG_FILE, 'utf8'));
    const cutoff = Date.now() - daysBack * 24 * 60 * 60 * 1000;
    return events.filter(e => e._loggedAt > cutoff && e._parsedTime);
  } catch {
    return [];
  }
}

// ─── Données prix Yahoo Finance ───────────────────────────────────────────────

/**
 * Récupère les barres 5m pour une journée entière (NYSE hours, 12h–22h UTC).
 * Cache disque 25h pour éviter les appels répétés à Yahoo Finance.
 *
 * @param {string} yahooSymbol - ex: '^DJI', 'EURUSD=X'
 * @param {string} dateStr     - format 'YYYY-MM-DD'
 * @returns {Array} Barres OHLCV [{date, open, high, low, close, volume}]
 */
async function fetchDayData(yahooSymbol, dateStr) {
  ensureDirs();

  const safeKey  = yahooSymbol.replace(/[^a-zA-Z0-9]/g, '_');
  const cacheFile = path.join(CACHE_DIR, `${safeKey}_${dateStr}.json`);

  // Cache disque valide 25h
  if (fs.existsSync(cacheFile)) {
    try {
      const cached = JSON.parse(fs.readFileSync(cacheFile, 'utf8'));
      if (Date.now() - cached._cachedAt < 25 * 60 * 60 * 1000) {
        return cached.quotes;
      }
    } catch {}
  }

  // Fenêtre NYSE : 12h00 UTC (8h ET) → 22h00 UTC (18h ET)
  const period1 = new Date(`${dateStr}T12:00:00Z`);
  const period2 = new Date(`${dateStr}T22:00:00Z`);

  try {
    const result = await yahooFinance.chart(yahooSymbol, {
      period1,
      period2,
      interval: '5m',
    }, { validateResult: false });

    const quotes = (result?.quotes ?? []).filter(q => q && q.close != null);

    fs.writeFileSync(cacheFile, JSON.stringify({ _cachedAt: Date.now(), quotes }));
    return quotes;
  } catch (err) {
    console.warn(`[CorrelEngine] fetch ${yahooSymbol} ${dateStr}: ${err.message}`);
    // Écrire cache vide pour éviter de re-requêter le même jour en erreur
    fs.writeFileSync(cacheFile, JSON.stringify({ _cachedAt: Date.now(), quotes: [] }));
    return [];
  }
}

// ─── Calcul impact ────────────────────────────────────────────────────────────

/**
 * Calcule l'impact d'un événement économique sur le prix.
 *
 * Stratégie :
 *   - Prix de référence = dernière barre AVANT l'événement
 *   - Mouvement = max(high, low) dans les 60 minutes APRÈS l'événement
 *   - Pips = mouvement absolu × pipFactor
 *   - Direction = sens net du dernier close vs pré-event
 *   - had_impact = movement > 0.1% du prix
 *
 * @param {Array}  dayQuotes  - Barres 5m de la journée
 * @param {string} eventTime  - ISO timestamp de l'événement
 * @param {number} pipFactor  - Multiplicateur pip
 * @returns {object|null} { movement_pips, direction, pre_price, post_price, had_impact }
 */
function calcEventImpact(dayQuotes, eventTime, pipFactor) {
  if (!dayQuotes || dayQuotes.length < 2) return null;

  const eventTs = new Date(eventTime).getTime();

  // Barres avant l'événement
  const preBars = dayQuotes.filter(q => new Date(q.date).getTime() < eventTs);
  // Barres dans les 60 min après l'événement
  const postBars = dayQuotes.filter(q => {
    const t = new Date(q.date).getTime();
    return t >= eventTs && t <= eventTs + 60 * 60 * 1000;
  });

  if (preBars.length === 0 || postBars.length === 0) return null;

  const prePrice  = preBars[preBars.length - 1].close;
  const maxHigh   = Math.max(...postBars.map(q => q.high ?? q.close));
  const minLow    = Math.min(...postBars.map(q => q.low  ?? q.close));
  const lastClose = postBars[postBars.length - 1].close;

  // Mouvement maximal (haussier ou baissier)
  const upMove   = maxHigh - prePrice;
  const downMove = prePrice - minLow;
  const absMove  = Math.max(upMove, downMove);

  const movement_pips = Math.round(absMove * pipFactor * 10) / 10;

  // Direction nette (seuil 0.05% pour éviter bruit)
  const netMove   = lastClose - prePrice;
  const threshold = prePrice * 0.0005;
  const direction = Math.abs(netMove) < threshold
    ? 'neutral'
    : netMove > 0 ? 'up' : 'down';

  // Considéré comme "impact" si mouvement > 0.1% du prix
  const had_impact = (absMove / prePrice) > 0.001;

  return { movement_pips, direction, pre_price: prePrice, post_price: lastClose, had_impact };
}

// ─── Dashboard principal ──────────────────────────────────────────────────────

/**
 * Construit le dashboard de corrélation complet pour un symbole.
 *
 * Retourne un objet compatible avec tous les composants SvelteKit :
 *   summary.by_event_type  → CorrelationTable
 *   heatmap_data           → HeatmapView
 *   top_impact_events      → ImpactChart
 *   timeline               → PriceTimeline
 *
 * @param {string}  symbol   - 'DJI' | 'US30' | 'SPX' | 'EURUSD' | ...
 * @param {number}  daysBack - Fenêtre temporelle (7, 30, 60, 90)
 * @param {boolean} force    - Ignorer le cache mémoire
 */
async function buildCorrelationDashboard(symbol = 'DJI', daysBack = 30, force = false) {
  const cacheKey = `${symbol}_${daysBack}`;
  const now      = Date.now();

  if (!force && _memCache[cacheKey] && now - _memCacheTime[cacheKey] < CACHE_TTL) {
    return _memCache[cacheKey];
  }

  const yahooSymbol = SYMBOL_MAP[symbol] || `${symbol}=X`;
  const pipFactor   = PIP_FACTOR[yahooSymbol] ?? 1;
  const events      = getHistoricalEvents(daysBack);

  // ── Pas encore de données ─────────────────────────────────────────────────
  const empty = {
    symbol,
    events_analyzed: 0,
    message: "Les données s'accumulent. Le moteur enregistre automatiquement les événements au fil du temps. Revenez après quelques scans.",
    summary: {
      total_events:       0,
      impact_rate:        0,
      avg_movement_pips:  0,
      direction_stats:    { up: 0, down: 0, neutral: 0 },
      volatility_increase: 0,
      by_event_type:      {},
    },
    top_impact_events: [],
    heatmap_data:      {},
    timeline:          [],
  };

  if (events.length === 0) {
    _memCache[cacheKey] = empty;
    _memCacheTime[cacheKey] = now;
    return empty;
  }

  // ── Grouper par date → 1 appel API par jour ───────────────────────────────
  const byDate = {};
  for (const ev of events) {
    const dateStr = new Date(ev._parsedTime).toISOString().slice(0, 10);
    if (!byDate[dateStr]) byDate[dateStr] = [];
    byDate[dateStr].push(ev);
  }

  // Fetcher les données prix (avec délai pour éviter rate-limit Yahoo)
  const dayDataMap = {};
  for (const dateStr of Object.keys(byDate)) {
    dayDataMap[dateStr] = await fetchDayData(yahooSymbol, dateStr);
    await new Promise(r => setTimeout(r, 150));
  }

  // ── Calculer l'impact pour chaque événement ───────────────────────────────
  const results = [];
  for (const ev of events) {
    const dateStr   = new Date(ev._parsedTime).toISOString().slice(0, 10);
    const dayQuotes = dayDataMap[dateStr] || [];
    const impact    = calcEventImpact(dayQuotes, ev._parsedTime, pipFactor);
    if (impact) {
      results.push({ ...ev, ...impact });
    }
  }

  // Si aucune donnée prix disponible
  if (results.length === 0) {
    const noPrice = {
      ...empty,
      events_analyzed: events.length,
      message: `Données prix indisponibles pour ${symbol}. Essayez un autre symbole ou vérifiez votre connexion.`,
    };
    _memCache[cacheKey] = noPrice;
    _memCacheTime[cacheKey] = now;
    return noPrice;
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  const total    = results.length;
  const impacted = results.filter(r => r.had_impact);

  const impact_rate        = safeN(Math.round((impacted.length / total) * 100));
  const avg_movement_pips  = safeN(Math.round(results.reduce((s, r) => s + safeN(r.movement_pips), 0) / total * 10) / 10);
  const direction_stats    = {
    up:      results.filter(r => r.direction === 'up').length,
    down:    results.filter(r => r.direction === 'down').length,
    neutral: results.filter(r => r.direction === 'neutral').length,
  };

  // Volatilité : ratio mouvement events impactés vs events calmes
  const quietResults  = results.filter(r => !r.had_impact);
  const impactedAvg   = impacted.length > 0
    ? safeN(impacted.reduce((s, r) => s + safeN(r.movement_pips), 0) / impacted.length, avg_movement_pips)
    : avg_movement_pips;
  const quietAvg      = quietResults.length > 0
    ? safeN(quietResults.reduce((s, r) => s + safeN(r.movement_pips), 0) / quietResults.length, avg_movement_pips * 0.3)
    : avg_movement_pips * 0.3;
  const volatility_increase = quietAvg > 0
    ? safeN(Math.round(((impactedAvg - quietAvg) / quietAvg) * 100))
    : 0;

  // ── By Event Type → CorrelationTable ─────────────────────────────────────
  const byTypeRaw = {};
  for (const r of results) {
    const key = r.event || 'Inconnu';
    if (!byTypeRaw[key]) {
      byTypeRaw[key] = { count: 0, total_pips: 0, total_impact: 0 };
    }
    byTypeRaw[key].count++;
    byTypeRaw[key].total_pips   += r.movement_pips;
    byTypeRaw[key].total_impact += r.impactLevel || 0;
  }

  // Format compatible CorrelationTable : { "Event Name": { count, avg_pips, avg_impact } }
  const by_event_type = Object.fromEntries(
    Object.entries(byTypeRaw)
      .map(([name, d]) => [
        name,
        {
          count:      d.count,
          avg_pips:   safeN(Math.round(d.total_pips   / d.count * 10) / 10),
          avg_impact: safeN(Math.round(d.total_impact / d.count * 100) / 100),
        },
      ])
      .sort(([, a], [, b]) => b.avg_pips - a.avg_pips)
      .slice(0, 10)
  );

  // ── Top Impact Events → ImpactChart ──────────────────────────────────────
  // Format : [{ event: { event_name, date, time }, impact: { movement_pips, direction } }]
  const top_impact_events = [...results]
    .sort((a, b) => b.movement_pips - a.movement_pips)
    .slice(0, 10)
    .map(r => ({
      event: {
        event_name: r.event || 'Inconnu',
        date:       new Date(r._parsedTime).toLocaleDateString('fr-FR'),
        time:       r.time || '—',
      },
      impact: {
        movement_pips: r.movement_pips,
        direction:     r.direction,
      },
    }));

  // ── Heatmap → HeatmapView ─────────────────────────────────────────────────
  // Format : { "Monday": { 9: 80.5, 12: 40.0 }, ... }
  // Heures regroupées par tranches de 3h : 0, 3, 6, 9, 12, 15, 18, 21
  const DAY_NAMES = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const heatmapRaw = {};

  for (const r of results) {
    const d    = new Date(r._parsedTime);
    const day  = DAY_NAMES[d.getDay()];
    const hour = Math.floor(d.getHours() / 3) * 3; // tranche de 3h

    if (!heatmapRaw[day])       heatmapRaw[day] = {};
    if (!heatmapRaw[day][hour]) heatmapRaw[day][hour] = { total: 0, count: 0 };

    heatmapRaw[day][hour].total += r.movement_pips;
    heatmapRaw[day][hour].count++;
  }

  const heatmap_data = {};
  for (const [day, hours] of Object.entries(heatmapRaw)) {
    heatmap_data[day] = {};
    for (const [hour, { total, count }] of Object.entries(hours)) {
      heatmap_data[day][parseInt(hour)] = Math.round(total / count * 10) / 10;
    }
  }

  // ── Timeline → PriceTimeline ──────────────────────────────────────────────
  // Format : [{ timestamp, currency, event_name, direction, movement_pips, impact_level, had_impact }]
  const IMPACT_LABEL = { 3: 'High', 2: 'Medium', 1: 'Low' };
  const timeline = [...results]
    .sort((a, b) => new Date(a._parsedTime) - new Date(b._parsedTime))
    .map(r => ({
      timestamp:     r._parsedTime,
      currency:      r.currency || '—',
      event_name:    r.event    || 'Inconnu',
      direction:     r.direction,
      movement_pips: r.movement_pips,
      impact_level:  IMPACT_LABEL[r.impactLevel] || 'Low',
      had_impact:    r.had_impact,
    }));

  // ── Résultat final ────────────────────────────────────────────────────────
  const dashboard = {
    symbol,
    generated_at:    new Date().toISOString(),
    events_analyzed: total,
    summary: {
      total_events:        total,
      impact_rate,
      avg_movement_pips,
      direction_stats,
      volatility_increase,
      by_event_type,
    },
    top_impact_events,
    heatmap_data,
    timeline,
  };

  _memCache[cacheKey]     = dashboard;
  _memCacheTime[cacheKey] = now;
  return dashboard;
}

// ─── Exports ──────────────────────────────────────────────────────────────────

module.exports = { logEvent, getHistoricalEvents, buildCorrelationDashboard };
