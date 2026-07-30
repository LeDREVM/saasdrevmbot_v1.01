/**
 * Netlify Function — endpoint n8n : calendrier économique du jour
 * Exposé via redirect sur :  /api/n8n/calendar/today
 *
 * Renvoie la MÊME forme que la route FastAPI `/api/n8n/calendar/today`
 * ({ source, date, events, count }) avec impact capitalisé (High/Medium/Low),
 * pour être consommé directement par le workflow n8n.
 *
 * Env vars (Netlify → Site settings → Environment variables) :
 *   TE_API_KEY          — clé Trading Economics
 *   TE_API_SECRET       — secret TE (optionnel si la clé est "KEY:SECRET")
 *   N8N_WEBHOOK_SECRET  — secret partagé ; si défini, l'en-tête X-N8N-Secret est exigé
 */

const TE_BASE = 'https://api.tradingeconomics.com';

function mapImpact(importance) {
  if (importance === 3) return 'High';
  if (importance === 2) return 'Medium';
  return 'Low';
}

// Date du jour (Europe/Paris) au format YYYY-MM-DD
function parisToday() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Paris',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
  return parts; // en-CA → "YYYY-MM-DD"
}

function parisTime(iso) {
  if (!iso) return 'N/A';
  return new Date(iso).toLocaleTimeString('fr-FR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'Europe/Paris',
  });
}

function normalise(e) {
  return {
    source: 'trading-economics',
    date: e.Date ? e.Date.slice(0, 10) : '',
    time: parisTime(e.Date),
    currency: e.Currency || '',
    event: e.Event || '',
    impact: mapImpact(e.Importance),
    actual: e.Actual !== null && e.Actual !== undefined ? String(e.Actual) : null,
    forecast: e.Forecast !== null && e.Forecast !== undefined ? String(e.Forecast) : null,
    previous: e.Previous !== null && e.Previous !== undefined ? String(e.Previous) : null,
  };
}

exports.handler = async (event) => {
  const headers = {
    'Content-Type': 'application/json',
    'Cache-Control': 'public, max-age=300',
  };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }

  // Vérification du secret partagé n8n (si configuré côté serveur)
  const expected = process.env.N8N_WEBHOOK_SECRET;
  if (expected) {
    const got = event.headers['x-n8n-secret'] || event.headers['X-N8N-Secret'];
    if (got !== expected) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Secret n8n invalide ou manquant' }) };
    }
  }

  const apiKey = process.env.TE_API_KEY;
  const apiSecret = process.env.TE_API_SECRET;
  if (!apiKey) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: 'TE_API_KEY manquante (Netlify → Environment variables).' }),
    };
  }

  const auth = apiSecret ? `${apiKey}:${apiSecret}` : apiKey;

  const qs = event.queryStringParameters || {};
  const currencies = qs.currencies
    ? qs.currencies.split(',').map((c) => c.trim().toUpperCase()).filter(Boolean)
    : [];
  const impacts = qs.impact
    ? qs.impact.split(',').map((i) => i.trim().toLowerCase()).filter(Boolean)
    : [];

  const today = parisToday();
  const teUrl = `${TE_BASE}/calendar/country/all?c=${encodeURIComponent(auth)}`;

  let raw;
  try {
    const res = await fetch(teUrl);
    if (!res.ok) {
      const text = await res.text();
      return {
        statusCode: res.status,
        headers,
        body: JSON.stringify({ error: `Trading Economics API: ${res.status}`, detail: text }),
      };
    }
    raw = await res.json();
  } catch (err) {
    return { statusCode: 502, headers, body: JSON.stringify({ error: String(err) }) };
  }

  let events = Array.isArray(raw) ? raw.map(normalise) : [];

  // Aujourd'hui uniquement
  events = events.filter((e) => e.date === today);

  if (currencies.length > 0) {
    events = events.filter((e) => currencies.includes(e.currency.toUpperCase()));
  }
  if (impacts.length > 0) {
    events = events.filter((e) => impacts.includes(e.impact.toLowerCase()));
  }

  events.sort((a, b) => String(a.time).localeCompare(String(b.time)));

  return {
    statusCode: 200,
    headers,
    body: JSON.stringify({
      source: 'trading-economics',
      date: today,
      events,
      count: events.length,
    }),
  };
};
