/**
 * Client pour saasDrevmbot FastAPI (http://localhost:8000)
 * Utilisé comme source principale de données.
 * Si l'API est indisponible, le caller doit fallback sur les scrapers directs.
 */

const axios = require('axios');

const SAAS_API_URL = process.env.SAAS_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: SAAS_API_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// ─── Ping ─────────────────────────────────────────────────────────────────────

let _available = null;
let _lastCheck  = 0;

async function isAvailable() {
  const now = Date.now();
  if (now - _lastCheck < 30_000) return _available; // Cache 30s
  _lastCheck = now;
  try {
    await client.get('/api/docs', { timeout: 3000 });
    if (!_available) console.log('[SaasAPI] ✅ saasDrevmbot connecté sur', SAAS_API_URL);
    _available = true;
  } catch {
    if (_available !== false) console.warn('[SaasAPI] ⚠️ saasDrevmbot non disponible — fallback scrapers');
    _available = false;
  }
  return _available;
}

// ─── Normalisation événement saasDrevmbot → GoldyXbOT ────────────────────────

const IMPACT_MAP_SAAS = {
  'High':   3,
  'Medium': 2,
  'Low':    1,
  'None':   0,
};

const IMPACT_EMOJI = { 3: '🔴', 2: '🟠', 1: '🟡', 0: '⚪' };

function normalizeEvent(e) {
  const impactLevel = IMPACT_MAP_SAAS[e.impact] ?? IMPACT_MAP_SAAS[e.impact_level] ?? 1;
  return {
    id:           `SAAS_${e.date || ''}_${e.time || ''}_${e.currency}_${e.event_name || e.event}`.replace(/\s+/g, '_'),
    source:       'SaasDrevmbot',
    date:         e.date     || '',
    time:         e.time     || '',
    currency:     e.currency || '',
    event:        e.event_name || e.event || '',
    impact:       e.impact   || 'Low',
    impactLevel,
    impactEmoji:  IMPACT_EMOJI[impactLevel],
    forecast:     e.forecast || null,
    previous:     e.previous || null,
    actual:       e.actual   || null,
  };
}

// ─── Endpoints ────────────────────────────────────────────────────────────────

/**
 * GET /api/calendar/today
 * Retourne les événements du jour filtrés.
 * @param {string[]} currencies  ex. ['USD','EUR']
 * @param {string[]} impacts     ex. ['High','Medium']
 * @returns {Promise<Object[]>}  événements normalisés GoldyXbOT
 */
async function getTodayEvents(currencies = [], impacts = []) {
  const params = {};
  if (currencies.length) params.currencies = currencies.join(',');
  if (impacts.length)    params.impact     = impacts.join(',');

  const { data } = await client.get('/api/calendar/today', { params });
  const events = data.events ?? [];
  console.log(`[SaasAPI] /calendar/today → ${events.length} événements (source: ${data.source})`);
  return events.map(normalizeEvent);
}

/**
 * GET /api/calendar/week
 * @returns {Promise<Object[]>}
 */
async function getWeekEvents(currencies = []) {
  const params = {};
  if (currencies.length) params.currencies = currencies.join(',');
  const { data } = await client.get('/api/calendar/week', { params });
  return (data.events ?? []).map(normalizeEvent);
}

/**
 * GET /api/calendar/upcoming
 * @returns {Promise<Object[]>}
 */
async function getUpcomingEvents() {
  const { data } = await client.get('/api/calendar/upcoming');
  return (data.events ?? []).map(normalizeEvent);
}

/**
 * GET /api/stats/dashboard/{symbol}
 * @param {string} symbol  ex. 'EURUSD'
 */
async function getStatsDashboard(symbol = 'EURUSD') {
  const { data } = await client.get(`/api/stats/dashboard/${symbol}`);
  return data;
}

/**
 * GET /api/stats/correlation-score
 */
async function getCorrelationScore() {
  const { data } = await client.get('/api/stats/correlation-score');
  return data;
}

module.exports = {
  isAvailable,
  getTodayEvents,
  getWeekEvents,
  getUpcomingEvents,
  getStatsDashboard,
  getCorrelationScore,
};
