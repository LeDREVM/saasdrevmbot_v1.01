import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tradePayload, tradesCSV, guadeloupeDate, alertInstant } from '../src/lib/journal.js';
const trade = { symbol: ' xauusd ', timeframe: 'M5', trade_date: '2026-09-30', direction: 'buy', entry: 2000, sl: 1990, tp: 2020, result: 'running', r_multiple: '', notes: '' };
test('journal prices and long/short boundaries', () => {
  assert.equal(tradePayload(trade).symbol, 'XAUUSD');
  for (const entry of [NaN, Infinity, '', -2]) assert.throws(() => tradePayload({ ...trade, entry }));
  assert.throws(() => tradePayload({ ...trade, sl: 2010 }));
  assert.throws(() => tradePayload({ ...trade, timeframe: 'H1' }));
  assert.equal(tradePayload({ ...trade, direction: 'sell', sl: 2010, tp: 1980 }).entry, 2000);
});
test('Guadeloupe date and alert timezone are explicit', () => {
  assert.equal(guadeloupeDate(new Date('2026-10-01T02:00:00Z')), '2026-09-30');
  assert.equal(alertInstant('2026-09-30T09:30'), '2026-09-30T13:30:00.000Z');
});
test('CSV quotes multiline notes and prevents formula execution', () => {
  const csv = tradesCSV([{ ...trade, notes: '=HYPERLINK("x")\nline' }]);
  assert.match(csv, /"'=HYPERLINK\(""x""\)/);
  assert.match(csv, /timeframe/);
});
