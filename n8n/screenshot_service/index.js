/**
 * Screenshot Service v2 — DREVM
 * - /screenshot   : capture unique (PNG binaire, ou JSON base64 avec ?b64=1)
 * - /capture-set  : capture MULTI-TIMEFRAMES en une seule session navigateur
 *                   → [{timeframe, data(base64)}] prêt pour /api/vision/analyze-raw
 * - SYMBOL_MAP complet (5 instruments DREVM + extras)
 */
require('dotenv').config(); // charge n8n/screenshot_service/.env en run natif (no-op si absent)
const express = require('express');
const puppeteer = require('puppeteer');

const app = express();
app.use(express.json({ limit: '2mb' }));

const PORT = process.env.SCREENSHOT_PORT || 3001;
const TV_SESSION = process.env.TRADINGVIEW_SESSION_ID || '';

// Map symboles → format TradingView (instruments DREVM en tête)
const SYMBOL_MAP = {
  'XAUUSD': 'OANDA:XAUUSD',
  'US30':   'OANDA:US30USD',
  'USDJPY': 'FX:USDJPY',
  'CADJPY': 'FX:CADJPY',
  'USDCAD': 'FX:USDCAD',
  'GBPJPY': 'FX:GBPJPY',
  'XTIUSD': 'TVC:USOIL',
  'EURUSD': 'FX:EURUSD',
  'GBPUSD': 'FX:GBPUSD',
  'BTCUSD': 'BITSTAMP:BTCUSD',
};

const TF_MAP = {
  'M1': '1', 'M5': '5', 'M15': '15', 'M30': '30',
  'H1': '60', 'H4': '240', 'D1': 'D', 'W1': 'W',
};

async function launchBrowser() {
  return puppeteer.launch({
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    headless: 'new',
  });
}

async function preparePage(browser) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  if (TV_SESSION) {
    await page.setCookie({ name: 'sessionid', value: TV_SESSION, domain: '.tradingview.com' });
  }
  return page;
}

async function captureChart(page, symbol, timeframe, chartUrl) {
  const tvSymbol = SYMBOL_MAP[symbol] || symbol;
  const tvTF = TF_MAP[timeframe] || '60';
  const url = chartUrl || `https://www.tradingview.com/chart/?symbol=${tvSymbol}&interval=${tvTF}`;

  await page.goto(url, { waitUntil: 'networkidle2', timeout: 25000 });
  await page.waitForSelector('.chart-container, canvas', { timeout: 15000 }).catch(() => {});
  await new Promise((r) => setTimeout(r, 3000));

  // Cache les popups/overlays
  await page.evaluate(() => {
    const selectors = ['.tv-dialog', '.js-dialog', '.tv-alert-dialog', '[data-name="popup-dialog"]'];
    selectors.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => (el.style.display = 'none'));
    });
  });

  return page.screenshot({ type: 'png', fullPage: false });
}

// ── Capture unique ───────────────────────────────────────────────────────────
app.post('/screenshot', async (req, res) => {
  const { symbol, timeframe, chart_url } = req.body;
  if (!symbol) return res.status(400).json({ error: 'symbol required' });

  let browser;
  try {
    browser = await launchBrowser();
    const page = await preparePage(browser);
    const buf = await captureChart(page, symbol, timeframe, chart_url);

    if (req.query.b64 === '1') {
      return res.json({
        symbol, timeframe: timeframe || 'H1',
        media_type: 'image/png', data: buf.toString('base64'),
      });
    }
    res.set('Content-Type', 'image/png');
    res.send(buf);
  } catch (err) {
    console.error('[Screenshot]', err.message);
    res.status(500).json({ error: err.message });
  } finally {
    if (browser) await browser.close();
  }
});

// ── Capture multi-TF (une session navigateur, séquentiel) ────────────────────
// Body : { symbol: "XAUUSD", timeframes: ["D1","H4","M15","M5"] }
// → { symbol, images: [{timeframe, media_type, data}] }  (base64)
app.post('/capture-set', async (req, res) => {
  const { symbol, timeframes } = req.body;
  if (!symbol) return res.status(400).json({ error: 'symbol required' });
  const tfs = (Array.isArray(timeframes) && timeframes.length ? timeframes : ['D1', 'H4', 'M15', 'M5'])
    .slice(0, 6);

  let browser;
  const images = [];
  const errors = [];
  try {
    browser = await launchBrowser();
    const page = await preparePage(browser);

    for (const tf of tfs) {
      try {
        const buf = await captureChart(page, symbol, tf);
        images.push({ timeframe: tf, media_type: 'image/png', data: buf.toString('base64') });
        console.log(`[CaptureSet] ${symbol} ${tf} ✅ (${Math.round(buf.length / 1024)} Ko)`);
      } catch (e) {
        console.error(`[CaptureSet] ${symbol} ${tf} ❌`, e.message);
        errors.push({ timeframe: tf, error: e.message });
      }
    }

    if (!images.length) {
      return res.status(500).json({ error: 'Aucune capture réussie', details: errors });
    }
    res.json({ symbol, images, errors });
  } catch (err) {
    console.error('[CaptureSet]', err.message);
    res.status(500).json({ error: err.message });
  } finally {
    if (browser) await browser.close();
  }
});

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'screenshot', version: 2 }));

app.listen(PORT, () => console.log(`[Screenshot Service v2] Port ${PORT}`));
