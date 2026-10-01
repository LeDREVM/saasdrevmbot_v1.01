import axios from 'axios';
import { normalizeCandles } from './candle-validation.js';
import { config } from './config.js';

const BASE_URL = config.urls.twelveDataBase;

// Mapping instruments → symboles Twelve Data
const SYMBOL_MAP = config.instruments.symbolMap;

let apiKey = null;

export function initPrice(key) {
  apiKey = key;
}

/**
 * Récupère les dernières bougies OHLCV
 * @param {string} instrument - ex: 'XAUUSD'
 * @param {string} interval   - '1min' | '5min' | '1h' | '4h'
 * @param {number} count      - nombre de bougies
 * @returns {Promise<object[]>} bougies [{datetime, open, high, low, close, volume}]
 */
export async function getCandles(instrument, interval = '5min', count = 10) {
  if (!apiKey) throw new Error('TWELVEDATA_API_KEY manquant dans .env');

  interval = ({ H4: '4h', M15: '15min', M5: '5min' })[interval] || interval;
  if (!['1min', '5min', '15min', '1h', '4h'].includes(interval) || !Number.isInteger(count) || count < 1 || count > 5000) throw new Error('Timeframe ou nombre de bougies invalide.');
  const symbol = SYMBOL_MAP[instrument];
  if (!symbol) throw new Error(`Instrument inconnu: ${instrument}`);

  const { data } = await axios.get(`${BASE_URL}/time_series`, {
    params: { symbol, interval, outputsize: count, timezone: 'UTC', apikey: apiKey },
    timeout: 10000,
  });

  return normalizeCandles(data);
}

/**
 * Récupère le prix actuel d'un instrument
 * @param {string} instrument
 * @returns {Promise<number>}
 */
export async function getPrice(instrument) {
  if (!apiKey) throw new Error('TWELVEDATA_API_KEY manquant dans .env');

  const symbol = SYMBOL_MAP[instrument] || instrument;
  const { data } = await axios.get(`${BASE_URL}/price`, {
    params: { symbol, apikey: apiKey },
    timeout: 8000,
  });

  if (data.status === 'error') throw new Error(`Twelve Data: ${data.message}`);
  const price = Number(data?.price);
  if (!Number.isFinite(price) || price <= 0) throw new Error('Twelve Data : prix invalide.');
  return price;
}

/**
 * Récupère le DXY actuel (Dollar Index)
 * @returns {Promise<number>}
 */
export async function getDXY() {
  return getPrice('DXY');
}

/**
 * Récupère les prix de tous les instruments en une requête batch
 * @returns {Promise<object>} { XAUUSD: 2345.5, USDJPY: 150.2, ... }
 */
export async function getAllPrices() {
  if (!apiKey) return {};

  const symbols = Object.values(SYMBOL_MAP).join(',');
  try {
    const { data } = await axios.get(`${BASE_URL}/price`, {
      params: { symbol: symbols, apikey: apiKey },
      timeout: 10000,
    });

    const result = {};
    for (const [inst, sym] of Object.entries(SYMBOL_MAP)) {
      const price = Number(data?.[sym]?.price);
      if (Number.isFinite(price) && price > 0) result[inst] = price;
    }
    return result;
  } catch {
    return {};
  }
}
