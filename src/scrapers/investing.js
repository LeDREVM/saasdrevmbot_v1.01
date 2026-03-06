const puppeteer = require('puppeteer');

const IMPACT_MAP = {
  5: 3, // Volatilité très haute -> impact 3
  4: 3, // Volatilité haute -> impact 3
  3: 2, // Volatilité moyenne -> impact 2
  2: 1, // Volatilité faible -> impact 1
  1: 1, // Volatilité très faible -> impact 1
};

const IMPACT_EMOJI = {
  3: '🔴',
  2: '🟠',
  1: '🟡',
  0: '⚪',
};

/**
 * Scrape le calendrier économique Investing.com
 * @returns {Promise<Array>} Liste d'événements
 */
async function scrapeInvesting() {
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
      ],
    });

    const page = await browser.newPage();

    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );

    await page.setExtraHTTPHeaders({
      'Accept-Language': 'en-US,en;q=0.9',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    });

    // Charger le calendrier économique d'Investing
    await page.goto('https://www.investing.com/economic-calendar/', {
      waitUntil: 'networkidle2',
      timeout: 30000,
    });

    // Gérer le bandeau de cookies si présent
    await page.evaluate(() => {
      const acceptBtn = document.querySelector('#onetrust-accept-btn-handler');
      if (acceptBtn) acceptBtn.click();
    }).catch(() => {});

    // Attendre le tableau
    await page.waitForSelector('#economicCalendarData', { timeout: 15000 }).catch(() => {
      console.warn('[Investing] Tableau non trouvé, tentative de scraping quand même...');
    });

    const events = await page.evaluate(() => {
      const rows = document.querySelectorAll('#economicCalendarData tr.js-event-item');
      const results = [];

      rows.forEach((row) => {
        try {
          const timeEl = row.querySelector('td.first.left.time');
          const currencyEl = row.querySelector('td.left.flagCur.noWrap');
          const impactEl = row.querySelector('td.left.textNum.sentiment');
          const eventEl = row.querySelector('td.left.event a');
          const actualEl = row.querySelector('td.bold.act');
          const forecastEl = row.querySelector('td.fore');
          const previousEl = row.querySelector('td.prev');

          if (!eventEl) return;

          const time = timeEl ? timeEl.textContent.trim() : '';
          const currency = currencyEl ? currencyEl.textContent.trim() : '';
          const eventName = eventEl.textContent.trim();

          // Compter le nombre d'étoiles/icônes pour l'impact
          let impactLevel = 1;
          if (impactEl) {
            const icons = impactEl.querySelectorAll('i');
            const filled = Array.from(icons).filter(
              (i) => !i.classList.contains('empty')
            ).length;
            if (filled >= 4) impactLevel = 3;
            else if (filled >= 2) impactLevel = 2;
            else impactLevel = 1;
          }

          const actual = actualEl ? actualEl.textContent.trim() : '';
          const forecast = forecastEl ? forecastEl.textContent.trim() : '';
          const previous = previousEl ? previousEl.textContent.trim() : '';

          const eventId = row.getAttribute('event_attr_id') || '';
          const timestamp = row.getAttribute('data-event-datetime') || '';

          results.push({
            source: 'Investing',
            time,
            currency,
            impactLevel,
            event: eventName,
            actual: actual || null,
            forecast: forecast || null,
            previous: previous || null,
            eventId,
            timestamp,
          });
        } catch (e) {
          // Ignorer les lignes malformées
        }
      });

      return results;
    });

    await browser.close();

    return events
      .filter((e) => e.event && e.currency)
      .map((e) => ({
        ...e,
        impactEmoji: IMPACT_EMOJI[e.impactLevel] ?? '🟡',
        id: `INV_${e.timestamp || e.time}_${e.currency}_${e.event}`.replace(/\s+/g, '_'),
      }));
  } catch (error) {
    console.error('[Investing] Erreur de scraping:', error.message);
    if (browser) await browser.close().catch(() => {});
    return [];
  }
}

module.exports = { scrapeInvesting };
