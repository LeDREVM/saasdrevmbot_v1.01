/**
 * Scraper Investing.com — endpoint AJAX + cheerio
 *
 * Remplace l'ancien scraping Puppeteer par une requête HTTP directe sur
 * l'endpoint interne `getCalendarFilteredData`, qui renvoie les lignes du
 * tableau en HTML. On les parse ensuite avec cheerio (sans navigateur).
 *
 * ⚠️ Investing.com est protégé (Cloudflare) : si la requête est bloquée, le
 * scraper renvoie [] proprement et le système bascule sur ForexFactory / l'API
 * saasDrevmbot (sources primaires). C'est un complément, pas une dépendance dure.
 */

const axios = require('axios');
const cheerio = require('cheerio');

const IMPACT_EMOJI = {
  3: '🔴',
  2: '🟠',
  1: '🟡',
  0: '⚪',
};

const INVESTING_AJAX_URL =
  'https://www.investing.com/economic-calendar/Service/getCalendarFilteredData';

/**
 * Scrape le calendrier économique Investing.com (jour courant).
 * @returns {Promise<Array>} Liste d'événements normalisés
 */
async function scrapeInvesting() {
  try {
    // Corps form-urlencoded : calendrier du jour, fuseau GMT, toutes devises.
    const body = new URLSearchParams({
      'country[]': '',
      timeZone: '55', // GMT
      timeFilter: 'timeRemain',
      currentTab: 'today',
      submitFilters: '1',
      limit_from: '0',
    }).toString();

    const { data } = await axios.post(INVESTING_AJAX_URL, body, {
      timeout: 15000,
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9',
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://www.investing.com/economic-calendar/',
        'Origin': 'https://www.investing.com',
      },
    });

    const html = typeof data === 'string' ? data : data?.data;
    if (!html) {
      console.warn('[Investing] Réponse vide ou inattendue');
      return [];
    }

    const $ = cheerio.load(html);
    const results = [];

    $('tr.js-event-item').each((_, el) => {
      const row = $(el);

      const time = row.find('td.first.left.time').text().trim();
      const currency = row.find('td.left.flagCur').text().trim();
      const eventName = row.find('td.left.event a').text().trim();
      if (!eventName) return;

      // Impact = nombre d'icônes « pleines » (grayFullBullishIcon)
      const filled = row.find('td.sentiment i.grayFullBullishIcon').length;
      let impactLevel = 1;
      if (filled >= 3) impactLevel = 3;
      else if (filled === 2) impactLevel = 2;

      const actual = row.find('td.bold.act').text().trim();
      const forecast = row.find('td.fore').text().trim();
      const previous = row.find('td.prev').text().trim();

      const timestamp = row.attr('data-event-datetime') || '';

      results.push({
        source: 'Investing',
        time,
        currency,
        impactLevel,
        impactEmoji: IMPACT_EMOJI[impactLevel] ?? '🟡',
        event: eventName,
        actual: actual || null,
        forecast: forecast || null,
        previous: previous || null,
        id: `INV_${timestamp || time}_${currency}_${eventName}`.replace(/\s+/g, '_'),
      });
    });

    return results.filter((e) => e.event && e.currency);
  } catch (error) {
    console.error('[Investing] Erreur de récupération:', error.message);
    return [];
  }
}

module.exports = { scrapeInvesting };
