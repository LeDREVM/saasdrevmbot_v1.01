/**
 * Market data service — US30 (DJIA) + VIX via Yahoo Finance
 * Données retardées ~15min (gratuit, sans clé API)
 */

const YahooFinance = require('yahoo-finance2').default;
const yahooFinance = new YahooFinance({ suppressNotices: ['yahooSurvey'] });


let _cache    = null;
let _cacheTime = 0;
const CACHE_MS = 30_000; // 30s

// ─── Quote US30 + VIX ─────────────────────────────────────────────────────────

async function getUS30() {
  const now = Date.now();
  if (_cache && now - _cacheTime < CACHE_MS) return _cache;

  try {
    const [djiResult, vixResult] = await Promise.allSettled([
      yahooFinance.quote('^DJI', {}, { validateResult: false }),
      yahooFinance.quote('^VIX', {}, { validateResult: false }),
    ]);

    const dji = djiResult.status === 'fulfilled' ? djiResult.value : null;
    const vix = vixResult.status === 'fulfilled' ? vixResult.value : null;

    _cache = {
      price:          dji?.regularMarketPrice          ?? null,
      change:         dji?.regularMarketChange          ?? null,
      changePercent:  dji?.regularMarketChangePercent   ?? null,
      high:           dji?.regularMarketDayHigh         ?? null,
      low:            dji?.regularMarketDayLow          ?? null,
      previousClose:  dji?.regularMarketPreviousClose   ?? null,
      open:           dji?.regularMarketOpen            ?? null,
      preMarketPrice: dji?.preMarketPrice               ?? null,
      preMarketChange:dji?.preMarketChange              ?? null,
      postMarketPrice:dji?.postMarketPrice              ?? null,
      marketState:    dji?.marketState                  ?? 'CLOSED', // REGULAR | PRE | POST | CLOSED
      vix:            vix?.regularMarketPrice           ?? null,
      vixChange:      vix?.regularMarketChangePercent   ?? null,
      timestamp:      new Date().toISOString(),
    };

    _cacheTime = now;
    return _cache;

  } catch (err) {
    console.error('[MarketData] Yahoo Finance erreur:', err.message);
    return _cache ?? {
      price: null, change: null, changePercent: null,
      high: null, low: null, previousClose: null,
      marketState: 'UNKNOWN', vix: null,
      timestamp: new Date().toISOString(),
    };
  }
}

module.exports = { getUS30 };
