const axios = require('axios');

const IMPACT_MAP = {
  High: 3,
  Medium: 2,
  Low: 1,
};

const IMPACT_EMOJI = {
  3: '🔴',
  2: '🟠',
  1: '🟡',
  0: '⚪',
};

// Alpha Vantage utilise des pays, pas des devises — on mappe ici
const COUNTRY_TO_CURRENCY = {
  'United States': 'USD',
  'Euro Zone': 'EUR',
  'United Kingdom': 'GBP',
  Japan: 'JPY',
  Canada: 'CAD',
  Australia: 'AUD',
  Switzerland: 'CHF',
  'New Zealand': 'NZD',
  China: 'CNY',
  Germany: 'EUR',
  France: 'EUR',
  Italy: 'EUR',
  Spain: 'EUR',
  'South Korea': 'KRW',
  Brazil: 'BRL',
  India: 'INR',
  Mexico: 'MXN',
  'South Africa': 'ZAR',
  Norway: 'NOK',
  Sweden: 'SEK',
  Denmark: 'DKK',
  Singapore: 'SGD',
  'Hong Kong': 'HKD',
};

/**
 * Découpe une ligne CSV en tenant compte des guillemets
 */
function parseCSVLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      inQuotes = !inQuotes;
    } else if (ch === ',' && !inQuotes) {
      fields.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  fields.push(current.trim());
  return fields;
}

/**
 * Récupère le calendrier économique via l'API Alpha Vantage
 * @param {string} apiKey  Clé API Alpha Vantage
 * @param {string} horizon '3month' | '6month' | '12month'
 * @returns {Promise<Array>}
 */
async function scrapeAlphaVantage(apiKey, horizon = '3month') {
  if (!apiKey) {
    console.warn('[AlphaVantage] Clé API manquante, scraper ignoré.');
    return [];
  }

  try {
    const url = `https://www.alphavantage.co/query?function=ECONOMIC_CALENDAR&horizon=${horizon}&apikey=${apiKey}`;
    const response = await axios.get(url, { timeout: 15000, responseType: 'text' });

    const text = response.data;
    if (!text || typeof text !== 'string') {
      console.warn('[AlphaVantage] Réponse vide ou inattendue.');
      return [];
    }

    // Détecter une erreur JSON renvoyée par l'API (ex: quota dépassé)
    if (text.trim().startsWith('{')) {
      const json = JSON.parse(text);
      const msg = json['Note'] || json['Information'] || json['Error Message'] || 'Erreur inconnue';
      console.error('[AlphaVantage] Erreur API:', msg);
      return [];
    }

    const lines = text.split('\n').filter((l) => l.trim());
    if (lines.length < 2) {
      console.warn('[AlphaVantage] Aucune donnée dans la réponse.');
      return [];
    }

    // Première ligne = en-têtes : title,country,date,time,impact,forecast,previous
    const headers = parseCSVLine(lines[0]).map((h) => h.toLowerCase());
    const idx = {
      title: headers.indexOf('title'),
      country: headers.indexOf('country'),
      date: headers.indexOf('date'),
      time: headers.indexOf('time'),
      impact: headers.indexOf('impact'),
      forecast: headers.indexOf('forecast'),
      previous: headers.indexOf('previous'),
    };

    const events = [];
    const today = new Date().toISOString().slice(0, 10);

    for (let i = 1; i < lines.length; i++) {
      const cols = parseCSVLine(lines[i]);
      if (cols.length < 4) continue;

      const date = cols[idx.date] || '';
      // Garder uniquement aujourd'hui et les événements futurs
      if (date < today) continue;

      const country = cols[idx.country] || '';
      const currency = COUNTRY_TO_CURRENCY[country] || country;
      const title = cols[idx.title] || '';
      const time = cols[idx.time] || '';
      const impactStr = cols[idx.impact] || 'Low';
      const forecast = cols[idx.forecast] || null;
      const previous = cols[idx.previous] || null;

      const impactLevel = IMPACT_MAP[impactStr] ?? 1;

      events.push({
        source: 'AlphaVantage',
        date,
        time,
        currency,
        country,
        impact: impactStr,
        impactLevel,
        impactEmoji: IMPACT_EMOJI[impactLevel],
        event: title,
        actual: null, // Alpha Vantage ne publie pas l'actual en temps réel
        forecast: forecast || null,
        previous: previous || null,
        id: `AV_${date}_${time}_${currency}_${title}`.replace(/\s+/g, '_'),
      });
    }

    console.log(`[AlphaVantage] ${events.length} événements récupérés.`);
    return events;
  } catch (error) {
    console.error('[AlphaVantage] Erreur:', error.message);
    return [];
  }
}

module.exports = { scrapeAlphaVantage };
