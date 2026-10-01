import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeCandles } from './src/candle-validation.js';
import { config } from './src/config.js';
const candle = { datetime: '2026-09-30 13:30:00', open: '10', high: '12', low: '9', close: '11' };
test('sort, deduplicate and reject invalid candles', () => {
  const values = [candle, { ...candle, datetime: '2026-09-30 13:25:00' }, candle, { ...candle, close: 'NaN' }];
  const result = normalizeCandles({ values });
  assert.equal(result.length, 2);
  assert.equal(result[0].datetime.toISOString(), '2026-09-30T13:25:00.000Z');
  assert.equal(result[0].volume, null);
  assert.throws(() => normalizeCandles({ values: [{ ...candle, high: '8' }] }));
  assert.throws(() => normalizeCandles({ status: 'error' }));
});
test('NY scheduling follows DST', () => {
  assert.equal(config.timing.timezone, 'America/New_York');
  const hour = instant => new Intl.DateTimeFormat('en-US', { timeZone: config.timing.timezone, hour: '2-digit', hourCycle: 'h23' }).format(new Date(instant));
  assert.equal(hour('2026-07-01T13:25:00Z'), '09');
  assert.equal(hour('2026-12-01T14:25:00Z'), '09');
});
