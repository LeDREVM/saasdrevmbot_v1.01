/**
 * Netlify Function — calendrier économique via le flux public ForexFactory
 * (https://nfs.faireconomy.media/ff_calendar_thisweek.json + nextweek).
 *
 * Aucune clé API requise. Même contrat de sortie que l'ancienne version
 * Trading Economics : { success, source, fetched_at, total, by_impact, events[] }
 * avec impact en minuscules (high|medium|low) — les événements "Holiday" sont
 * ignorés, comme dans ny_session_interface/news.py.
 */

const FF_BASE = 'https://nfs.faireconomy.media';
const FF_FEEDS = ['ff_calendar_thisweek.json', 'ff_calendar_nextweek.json'];

// Normalise un événement ForexFactory vers le format interne.
// FF : { title, country (= devise), date (ISO avec fuseau), impact, forecast, previous }
function normalise(e) {
  const impact = String(e.impact || '').toLowerCase();
  if (impact !== 'high' && impact !== 'medium' && impact !== 'low') return null; // Holiday…
  const date = e.date || '';
  return {
    id: `${date}-${e.country}-${e.title}`,
    date,
    time: date
      ? new Date(date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' })
      : 'N/A',
    currency: e.country || '',
    country: e.country || '',
    event: e.title || '',
    impact,
    actual: null, // non fourni par le flux FF hebdo
    forecast: e.forecast ? String(e.forecast) : null,
    previous: e.previous ? String(e.previous) : null,
    revised: null,
    url: null,
  };
}

exports.handler = async (event) => {
  const headers = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Cache-Control': 'public, max-age=300', // 5 min cache
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }

  // Filtres transmis par le frontend
  const qs = event.queryStringParameters || {};
  const currencies = qs.currencies ? qs.currencies.split(',').map(c => c.trim().toUpperCase()).filter(Boolean) : [];
  const impacts = qs.impact ? qs.impact.split(',').map(i => i.trim().toLowerCase()).filter(Boolean) : [];

  // this week + next week ; un flux en échec n'invalide pas l'autre
  const results = await Promise.allSettled(
    FF_FEEDS.map(async (feed) => {
      const res = await fetch(`${FF_BASE}/${feed}`);
      if (!res.ok) throw new Error(`ForexFactory ${feed}: HTTP ${res.status}`);
      return res.json();
    })
  );

  const raw = [];
  const errors = [];
  for (const r of results) {
    if (r.status === 'fulfilled' && Array.isArray(r.value)) raw.push(...r.value);
    else if (r.status === 'rejected') errors.push(String(r.reason));
  }

  if (raw.length === 0) {
    console.error('ForexFactory fetch errors:', errors);
    return {
      statusCode: 502,
      headers,
      body: JSON.stringify({ success: false, error: 'Flux ForexFactory injoignable', detail: errors.join('; ') }),
    };
  }

  let events = raw.map(normalise).filter(Boolean);

  if (currencies.length > 0) {
    events = events.filter(e => currencies.includes(e.currency.toUpperCase()));
  }
  if (impacts.length > 0) {
    events = events.filter(e => impacts.includes(e.impact));
  }

  events.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

  const byImpact = { high: 0, medium: 0, low: 0 };
  events.forEach(e => { byImpact[e.impact] = (byImpact[e.impact] || 0) + 1; });

  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({
      success: true,
      source: 'forexfactory',
      fetched_at: new Date().toISOString(),
      total: events.length,
      by_impact: byImpact,
      events,
    }),
  };
};
