/**
 * Netlify Function — proxy Trading Economics Calendar Snapshot
 * https://api.tradingeconomics.com/calendar/country/all?c=KEY:SECRET
 *
 * Env vars required in Netlify dashboard:
 *   TE_API_KEY    — Trading Economics API key
 *   TE_API_SECRET — Trading Economics API secret (optional if key is "KEY:SECRET" format)
 */

const TE_BASE = 'https://api.tradingeconomics.com';

// Map TE importance (number) → label
function mapImpact(importance) {
  if (importance === 3) return 'high';
  if (importance === 2) return 'medium';
  return 'low';
}

// Normalise a TE calendar event to our internal shape
function normalise(e) {
  return {
    id: e.CalendarId || `${e.Date}-${e.Currency}-${e.Event}`,
    date: e.Date || '',
    time: e.Date ? new Date(e.Date).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Paris' }) : 'N/A',
    currency: e.Currency || '',
    country: e.Country || '',
    event: e.Event || '',
    impact: mapImpact(e.Importance),
    actual: e.Actual !== null && e.Actual !== undefined ? String(e.Actual) : null,
    forecast: e.Forecast !== null && e.Forecast !== undefined ? String(e.Forecast) : null,
    previous: e.Previous !== null && e.Previous !== undefined ? String(e.Previous) : null,
    revised: e.Revised !== null && e.Revised !== undefined ? String(e.Revised) : null,
    url: e.URL || null,
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

  const apiKey = process.env.TE_API_KEY;
  const apiSecret = process.env.TE_API_SECRET;

  if (!apiKey) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ success: false, error: 'TE_API_KEY manquante. Configurez-la dans Netlify → Site settings → Environment variables.' }),
    };
  }

  // Build auth param: "KEY:SECRET" or just "KEY" if no secret
  const auth = apiSecret ? `${apiKey}:${apiSecret}` : apiKey;

  // Parse query params forwarded from frontend
  const qs = event.queryStringParameters || {};
  const currencies = qs.currencies ? qs.currencies.split(',').map(c => c.trim().toUpperCase()).filter(Boolean) : [];
  const impacts = qs.impact ? qs.impact.split(',').map(i => i.trim().toLowerCase()).filter(Boolean) : [];

  // Build TE URL — /calendar/country/all gives today's snapshot
  const teUrl = `${TE_BASE}/calendar/country/all?c=${encodeURIComponent(auth)}`;

  let raw;
  try {
    const res = await fetch(teUrl);
    if (!res.ok) {
      const text = await res.text();
      console.error('TE API error:', res.status, text);
      return {
        statusCode: res.status,
        headers,
        body: JSON.stringify({ success: false, error: `Trading Economics API: ${res.status}`, detail: text }),
      };
    }
    raw = await res.json();
  } catch (err) {
    console.error('Fetch error:', err);
    return {
      statusCode: 502,
      headers,
      body: JSON.stringify({ success: false, error: String(err) }),
    };
  }

  let events = Array.isArray(raw) ? raw.map(normalise) : [];

  // Filter by currencies if requested
  if (currencies.length > 0) {
    events = events.filter(e => currencies.includes(e.currency.toUpperCase()));
  }

  // Filter by impact if requested
  if (impacts.length > 0) {
    events = events.filter(e => impacts.includes(e.impact));
  }

  // Sort by date/time
  events.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));

  const byImpact = { high: 0, medium: 0, low: 0 };
  events.forEach(e => { byImpact[e.impact] = (byImpact[e.impact] || 0) + 1; });

  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({
      success: true,
      source: 'trading-economics',
      fetched_at: new Date().toISOString(),
      total: events.length,
      by_impact: byImpact,
      events,
    }),
  };
};
