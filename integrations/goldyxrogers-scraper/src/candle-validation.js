export function normalizeCandles(data) {
  if (!data || data.status === 'error' || !Array.isArray(data.values) || !data.values.length)
    throw new Error('Twelve Data : données indisponibles.');
  const candles = new Map();
  for (const source of data.values) {
    if (!source || typeof source.datetime !== 'string') continue;
    const datetime = new Date(source.datetime.replace(' ', 'T') + (/(Z|[+-]\d{2}:?\d{2})$/.test(source.datetime) ? '' : 'Z'));
    const numeric = key => source[key] == null || source[key] === '' ? NaN : Number(source[key]);
    const open = numeric('open'), high = numeric('high'), low = numeric('low'), close = numeric('close');
    const volume = source.volume == null ? null : numeric('volume');
    if (!Number.isFinite(datetime.getTime()) || ![open, high, low, close].every(v => Number.isFinite(v) && v > 0)
        || high < Math.max(open, close, low) || low > Math.min(open, close, high)
        || (volume !== null && (!Number.isFinite(volume) || volume < 0))) continue;
    candles.set(datetime.getTime(), { datetime, open, high, low, close, volume });
  }
  if (!candles.size) throw new Error('Twelve Data : aucune bougie valide.');
  return [...candles.values()].sort((a, b) => a.datetime - b.datetime);
}
