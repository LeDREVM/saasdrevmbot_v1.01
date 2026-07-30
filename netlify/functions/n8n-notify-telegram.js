/**
 * Netlify Function — endpoint n8n : notification Telegram
 * Exposé via redirect sur :  /api/n8n/notify/telegram  (POST)
 *
 * Corps accepté (souple) :
 *   { "date", "events": [...], "count" }  → message formaté ici
 *   { "text": "..." }                     → message HTML déjà prêt
 *   "chat_id" (optionnel)                 → surcharge TELEGRAM_CHAT_ID
 *
 * Env vars :
 *   TELEGRAM_BOT_TOKEN  — token du bot
 *   TELEGRAM_CHAT_ID    — chat/canal par défaut
 *   N8N_WEBHOOK_SECRET  — secret partagé ; si défini, X-N8N-Secret est exigé
 */

function impactEmoji(impact) {
  return { High: '🔴', Medium: '🟠', Low: '🟡' }[impact] || '⚪';
}

/**
 * Échappe &, < et > — obligatoire avant insertion dans un message Telegram
 * envoyé en parse_mode=HTML (un nom d'événement type "M&A Activity" fait
 * échouer l'API Telegram avec un 400 sinon).
 */
function esc(value) {
  return String(value === null || value === undefined ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function formatMessage(date, events) {
  const lines = [`📅 <b>Calendrier économique — ${esc(date)}</b>`, ''];
  if (!events.length) {
    lines.push("✅ Aucun événement à fort impact aujourd'hui.");
    return lines.join('\n');
  }
  const sorted = [...events].sort((a, b) => String(a.time || '').localeCompare(String(b.time || '')));
  for (const e of sorted) {
    let line = `${impactEmoji(e.impact)} <b>${esc(e.time || '--:--')}</b>  ${esc(e.currency || '')} — ${esc(e.event || '')}`;
    const details = [];
    if (e.forecast) details.push(`prév: ${esc(e.forecast)}`);
    if (e.previous) details.push(`préc: ${esc(e.previous)}`);
    if (e.actual) details.push(`réel: ${esc(e.actual)}`);
    if (details.length) line += `\n   <i>${details.join('  |  ')}</i>`;
    lines.push(line);
  }
  lines.push('', `<b>Total:</b> ${sorted.length} événement(s)`);
  return lines.join('\n');
}

exports.handler = async (event) => {
  const headers = { 'Content-Type': 'application/json' };

  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers, body: '' };
  }
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, headers, body: JSON.stringify({ error: 'Méthode non autorisée (POST attendu)' }) };
  }

  const expected = process.env.N8N_WEBHOOK_SECRET;
  if (expected) {
    const got = event.headers['x-n8n-secret'] || event.headers['X-N8N-Secret'];
    if (got !== expected) {
      return { statusCode: 401, headers, body: JSON.stringify({ error: 'Secret n8n invalide ou manquant' }) };
    }
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'TELEGRAM_BOT_TOKEN non configuré' }) };
  }

  let payload = {};
  try {
    payload = event.body ? JSON.parse(event.body) : {};
  } catch (err) {
    return { statusCode: 400, headers, body: JSON.stringify({ error: 'Corps JSON invalide' }) };
  }

  const chatId = payload.chat_id || process.env.TELEGRAM_CHAT_ID;
  if (!chatId) {
    return { statusCode: 500, headers, body: JSON.stringify({ error: 'TELEGRAM_CHAT_ID non configuré' }) };
  }

  let text = payload.text;
  if (!text) {
    const date = payload.date || new Date().toISOString().slice(0, 10);
    const events = Array.isArray(payload.events) ? payload.events : [];
    text = formatMessage(date, events);
  }

  const url = `https://api.telegram.org/bot${token}/sendMessage`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        parse_mode: 'HTML',
        disable_web_page_preview: true,
      }),
    });
    if (!res.ok) {
      const detail = await res.text();
      return { statusCode: 502, headers, body: JSON.stringify({ error: `Echec Telegram: ${res.status}`, detail }) };
    }
  } catch (err) {
    return { statusCode: 502, headers, body: JSON.stringify({ error: String(err) }) };
  }

  return { statusCode: 200, headers, body: JSON.stringify({ status: 'sent', chat_id: String(chatId) }) };
};
