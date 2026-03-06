const puppeteer = require('puppeteer');

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

/**
 * Scrape le calendrier économique ForexFactory
 * @returns {Promise<Array>} Liste d'événements
 */
async function scrapeForexFactory() {
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
    });

    // Charger la page du calendrier du jour
    await page.goto('https://www.forexfactory.com/calendar', {
      waitUntil: 'networkidle2',
      timeout: 30000,
    });

    // Attendre le tableau du calendrier
    await page.waitForSelector('.calendar__table', { timeout: 15000 }).catch(() => {
      console.warn('[ForexFactory] Tableau non trouvé, tentative de scraping quand même...');
    });

    const events = await page.evaluate(() => {
      const rows = document.querySelectorAll('.calendar__row');
      const results = [];
      let currentDate = '';
      let currentTime = '';

      rows.forEach((row) => {
        // Détecter les lignes de date
        const dateCell = row.querySelector('.calendar__cell.calendar__date span');
        if (dateCell && dateCell.textContent.trim()) {
          currentDate = dateCell.textContent.trim();
        }

        // Détecter les lignes d'heure
        const timeCell = row.querySelector('.calendar__cell.calendar__time');
        if (timeCell && timeCell.textContent.trim()) {
          const timeText = timeCell.textContent.trim();
          if (timeText && timeText !== 'All Day') {
            currentTime = timeText;
          }
        }

        // Extraire les données de l'événement
        const currencyCell = row.querySelector('.calendar__cell.calendar__currency');
        const impactCell = row.querySelector('.calendar__cell.calendar__impact span');
        const eventCell = row.querySelector('.calendar__cell.calendar__event span');
        const actualCell = row.querySelector('.calendar__cell.calendar__actual');
        const forecastCell = row.querySelector('.calendar__cell.calendar__forecast');
        const previousCell = row.querySelector('.calendar__cell.calendar__previous');

        if (!currencyCell || !eventCell) return;

        const currency = currencyCell.textContent.trim();
        const eventName = eventCell.textContent.trim();

        if (!currency || !eventName) return;

        // Déterminer l'impact
        let impact = 'Low';
        if (impactCell) {
          const impactClass = impactCell.className;
          if (impactClass.includes('high')) impact = 'High';
          else if (impactClass.includes('medium')) impact = 'Medium';
          else if (impactClass.includes('low')) impact = 'Low';
          else if (impactClass.includes('holiday')) impact = 'Holiday';
          else if (impactClass.includes('nonecon')) impact = 'Non-Economic';
        }

        const actual = actualCell ? actualCell.textContent.trim() : '';
        const forecast = forecastCell ? forecastCell.textContent.trim() : '';
        const previous = previousCell ? previousCell.textContent.trim() : '';

        results.push({
          source: 'ForexFactory',
          date: currentDate,
          time: currentTime,
          currency,
          impact,
          event: eventName,
          actual: actual || null,
          forecast: forecast || null,
          previous: previous || null,
        });
      });

      return results;
    });

    await browser.close();

    // Post-traitement: normaliser les données
    return events
      .filter((e) => e.event && e.currency)
      .map((e) => ({
        ...e,
        impactLevel: IMPACT_MAP[e.impact] ?? 1,
        impactEmoji: IMPACT_EMOJI[IMPACT_MAP[e.impact] ?? 1],
        id: `FF_${e.date}_${e.time}_${e.currency}_${e.event}`.replace(/\s+/g, '_'),
      }));
  } catch (error) {
    console.error('[ForexFactory] Erreur de scraping:', error.message);
    if (browser) await browser.close().catch(() => {});
    return [];
  }
}

module.exports = { scrapeForexFactory };
