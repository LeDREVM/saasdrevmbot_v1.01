export const TIMEFRAMES = ['H4', 'M15', 'M5'];
export function guadeloupeDate(date = new Date()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Guadeloupe', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
}
export function alertInstant(value) {
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value)) throw new Error('Heure Guadeloupe obligatoire.');
  return new Date(`${value}:00-04:00`).toISOString();
}
export function tradePayload(trade) {
  const number = (value) => {
    if (value === '' || value == null) return null;
    const result = Number(value);
    if (!Number.isFinite(result)) throw new Error('Nombre invalide.');
    return result;
  };
  const row = { symbol: trade.symbol.trim().toUpperCase(), direction: trade.direction,
    timeframe: trade.timeframe, trade_date: trade.trade_date, result: trade.result,
    entry: number(trade.entry), sl: number(trade.sl), tp: number(trade.tp),
    r_multiple: number(trade.r_multiple), notes: trade.notes || '' };
  if (!row.symbol || !TIMEFRAMES.includes(row.timeframe) || !['buy', 'sell'].includes(row.direction)
      || !['running', 'win', 'loss', 'breakeven'].includes(row.result)
      || !/^\d{4}-\d{2}-\d{2}$/.test(row.trade_date)) throw new Error('Vérifie le symbole, la date et le timeframe.');
  if ([row.entry, row.sl, row.tp].some(v => v === null || v <= 0)) throw new Error('Entrée, SL et TP doivent être positifs.');
  if (row.direction === 'buy' ? !(row.sl < row.entry && row.tp > row.entry) : !(row.sl > row.entry && row.tp < row.entry))
    throw new Error('SL et TP doivent encadrer l’entrée selon le sens du trade.');
  return row;
}
export function tradesCSV(trades) {
  const fields = ['trade_date', 'symbol', 'timeframe', 'direction', 'entry', 'sl', 'tp', 'result', 'r_multiple', 'notes'];
  const cell = v => '"' + String(v ?? '').replace(/^[=+\-@\t\r]/, "'$&").replaceAll('"', '""') + '"';
  return '\ufeff' + [fields.join(';'), ...trades.map(t => fields.map(f => cell(t[f])).join(';'))].join('\r\n');
}
