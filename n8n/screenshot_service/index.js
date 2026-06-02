const express = require('express');
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(express.json());

const PORT = process.env.SCREENSHOT_PORT || 3001;
const TV_SESSION = process.env.TRADINGVIEW_SESSION_ID || '';

// Map symboles → format TradingView
const SYMBOL_MAP = {
  'XAUUSD': 'OANDA:XAUUSD',
  'EURUSD': 'FX:EURUSD',
  'GBPUSD': 'FX:GBPUSD',
  'USDJPY': 'FX:USDJPY',
  'BTCUSD': 'BITSTAMP:BTCUSD',
};

const TF_MAP = {
  'M1': '1', 'M5': '5', 'M15': '15', 'M30': '30',
  'H1': '60', 'H4': '240', 'D1': 'D', 'W1': 'W',
};

app.post('/screenshot', async (req, res) => {
  const { symbol, timeframe, chart_url } = req.body;

  if (!symbol) {
    return res.status(400).json({ error: 'symbol required' });
  }

  let browser;
  try {
    browser = await puppeteer.launch({
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
      headless: 'new',
    });

    const page = await browser.newPage();
    await page.setViewport({ width: 1920, height: 1080 });

    // Cookie de session TradingView (si compte connecté)
    if (TV_SESSION) {
      await page.setCookie({
        name: 'sessionid',
        value: TV_SESSION,
        domain: '.tradingview.com',
      });
    }

    const tvSymbol = SYMBOL_MAP[symbol] || symbol;
    const tvTF = TF_MAP[timeframe] || '60';
    const url = chart_url || `https://www.tradingview.com/chart/?symbol=${tvSymbol}&interval=${tvTF}`;

    await page.goto(url, { waitUntil: 'networkidle2', timeout: 25000 });

    // Attend que le chart soit chargé
    await page.waitForSelector('.chart-container, canvas', { timeout: 15000 }).catch(() => {});
    await new Promise(r => setTimeout(r, 3000));

    // Cache les popups/overlays
    await page.evaluate(() => {
      const selectors = ['.tv-dialog', '.js-dialog', '.tv-alert-dialog', '[data-name="popup-dialog"]'];
      selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => el.style.display = 'none');
      });
    });

    const screenshotBuffer = await page.screenshot({ type: 'png', fullPage: false });

    res.set('Content-Type', 'image/png');
    res.send(screenshotBuffer);

  } catch (err) {
    console.error('[Screenshot]', err.message);
    res.status(500).json({ error: err.message });
  } finally {
    if (browser) await browser.close();
  }
});

app.get('/health', (_, res) => res.json({ status: 'ok', service: 'screenshot' }));

app.listen(PORT, () => console.log(`[Screenshot Service] Port ${PORT}`));
