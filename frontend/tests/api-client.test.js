import test from 'node:test';
import assert from 'node:assert/strict';
import { requestJSON, guadeloupeTime } from '../src/lib/api-client.js';

test('successful response and HTTP errors', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({ ok: true, json: async () => ({ total: 4 }) });
    assert.deepEqual(await requestJSON('/test'), { total: 4 });
    globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ detail: 'Historique indisponible' }) });
    await assert.rejects(requestJSON('/test'), /Historique indisponible/);
    globalThis.fetch = async () => ({ ok: false, json: async () => { throw new SyntaxError('HTML'); } });
    await assert.rejects(requestJSON('/test'), /réponse illisible/);
  } finally { globalThis.fetch = original; }
});

test('timeout produces a visible message', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = (_url, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    });
    await assert.rejects(requestJSON('/test', {}, 10), /délai de réponse/);
  } finally { globalThis.fetch = original; }
});

test('Guadeloupe timestamps are independent of browser timezone', () => {
  assert.match(guadeloupeTime('2026-09-30T13:30:00+00:00'), /09:30/);
  assert.match(guadeloupeTime('2026-12-30T14:30:00+00:00'), /10:30/);
  assert.equal(guadeloupeTime('invalid'), 'Date indisponible');
  assert.equal(guadeloupeTime(null), '—');
  assert.match(guadeloupeTime('2026-09-30T13:30:00'), /fuseau non précisé/);
});
