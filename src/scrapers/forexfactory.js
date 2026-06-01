/**
 * Scraper ForexFactory — flux JSON officiel (faireconomy)
 *
 * Remplace l'ancien scraping Puppeteer (Chromium headless relancé à chaque scan,
 * ~300-500 Mo de RAM) par une simple requête HTTP sur le flux JSON public de la
 * semaine. Plus rapide, sans navigateur, et insensible aux changements de CSS.
 *
 * Flux : https://nfs.faireconomy.media/ff_calendar_thisweek.json
 * Format d'un item : { title, country, date (ISO+offset), impact, forecast, previous }
 * Remarque : ce flux ne fournit PAS le résultat "actual" en direct. Les résultats
 * temps réel proviennent d'Investing.com et/ou de l'API saasDrevmbot.
 */

const axios = require('axios');

const IMPACT_MAP = {
  'High': 3,
  'Medium': 2,
  'Low': 1,
  'Non-Economic': 0,
  'Holiday': 0,
};

const IMPACT_EMOJI = {
  3: '🔴',
  2: '🟠',
  1: '🟡',
  0: '⚪',
};

const FF_FEED_URL = 'https://nfs.faireconomy.media/ff_calendar_thisweek.json';

// Formate une Date en heure ForexFactory ("8:30am", "10:00pm") en heure locale
// du serveur, pour rester compatible avec parseForexFactoryTime().
function formatTime(date) {
  let hours = date.getHours();
  const minutes = date.getMinutes();
  const period = hours >= 12 ? 'pm' : 'am';
  hours = hours % 12;
  if (hours === 0) hours = 12;
  return `${hours}:${String(minutes).padStart(2, '0')}${period}`;
}

// Formate une Date en "Mon Mar 10" (sans année) pour parseDateString().
function formatDate(date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Récupère le calendrier économique ForexFactory de la semaine.
 * @returns {Promise<Array>} Liste d'événements normalisés
 */
async function scrapeForexFactory() {
  try {
    const { data } = await axios.get(FF_FEED_URL, {
      timeout: 15000,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
      },
    });

    if (!Array.isArray(data)) {
      console.warn('[ForexFactory] Réponse inattendue (pas un tableau)');
      return [];
    }

    return data
      .filter((item) => item && item.title && item.country)
      .map((item) => {
        const dt = item.date ? new Date(item.date) : null;
        const valid = dt && !isNaN(dt.getTime());

        const impact = item.impact || 'Low';
        const impactLevel = IMPACT_MAP[impact] ?? 1;

        // Les jours fériés / événements « All Day » n'ont pas d'heure précise
        const isAllDay = impact === 'Holiday' || !valid;
        const time = isAllDay ? 'All Day' : formatTime(dt);
        const date = valid ? formatDate(dt) : '';

        return {
          source: 'ForexFactory',
          date,
          time,
          currency: item.country,
          impact,
          event: item.title,
          actual: item.actual || null,
          forecast: item.forecast || null,
          previous: item.previous || null,
          impactLevel,
          impactEmoji: IMPACT_EMOJI[impactLevel],
          id: `FF_${date}_${time}_${item.country}_${item.title}`.replace(/\s+/g, '_'),
        };
      });
  } catch (error) {
    console.error('[ForexFactory] Erreur de récupération:', error.message);
    return [];
  }
}

module.exports = { scrapeForexFactory };
