const axios = require('axios');

const IMPACT_COLORS = {
  3: 0xff0000, // Rouge - Impact fort
  2: 0xff8c00, // Orange - Impact moyen
  1: 0xffff00, // Jaune - Impact faible
  0: 0x808080, // Gris - Aucun impact
};

const IMPACT_LABELS = {
  3: 'Fort',
  2: 'Moyen',
  1: 'Faible',
  0: 'Aucun',
};

const SOURCE_COLORS = {
  ForexFactory: 0x1a73e8,
  Investing: 0xff6600,
};

/**
 * Formate un événement en embed Discord
 */
function formatEventEmbed(event, isReminder = false) {
  const color = isReminder ? 0xffd700 : IMPACT_COLORS[event.impactLevel] ?? 0x808080;
  const sourceColor = SOURCE_COLORS[event.source] ?? 0x7289da;

  const fields = [];

  if (event.forecast) {
    fields.push({
      name: '📊 Prévision',
      value: event.forecast,
      inline: true,
    });
  }

  if (event.previous) {
    fields.push({
      name: '📈 Précédent',
      value: event.previous,
      inline: true,
    });
  }

  if (event.actual) {
    fields.push({
      name: '✅ Résultat',
      value: event.actual,
      inline: true,
    });
  }

  const title = isReminder
    ? `⏰ RAPPEL dans ${event.reminderMinutes || 15}min — ${event.event}`
    : `${event.impactEmoji} ${event.event}`;

  const description = [
    `**Devise:** ${event.currency}`,
    `**Impact:** ${IMPACT_LABELS[event.impactLevel] ?? 'Inconnu'} ${event.impactEmoji}`,
    `**Heure:** ${event.time || 'N/A'}`,
    event.date ? `**Date:** ${event.date}` : null,
  ]
    .filter(Boolean)
    .join('\n');

  return {
    title,
    description,
    color: isReminder ? 0xffd700 : color,
    fields,
    footer: {
      text: `Source: ${event.source}`,
    },
    timestamp: new Date().toISOString(),
  };
}

/**
 * Formate un résumé journalier en embed Discord
 */
function formatDailySummaryEmbed(events) {
  const highImpact = events.filter((e) => e.impactLevel >= 3);
  const mediumImpact = events.filter((e) => e.impactLevel === 2);
  const lowImpact = events.filter((e) => e.impactLevel === 1);

  const fields = [];

  if (highImpact.length > 0) {
    fields.push({
      name: '🔴 Impact Fort',
      value: highImpact
        .slice(0, 10)
        .map((e) => `• **${e.time}** ${e.currency} — ${e.event}`)
        .join('\n'),
      inline: false,
    });
  }

  if (mediumImpact.length > 0) {
    fields.push({
      name: '🟠 Impact Moyen',
      value: mediumImpact
        .slice(0, 10)
        .map((e) => `• **${e.time}** ${e.currency} — ${e.event}`)
        .join('\n'),
      inline: false,
    });
  }

  if (lowImpact.length > 0 && lowImpact.length <= 15) {
    fields.push({
      name: '🟡 Impact Faible',
      value: lowImpact
        .slice(0, 10)
        .map((e) => `• **${e.time}** ${e.currency} — ${e.event}`)
        .join('\n'),
      inline: false,
    });
  }

  return {
    title: '📅 Résumé Économique du Jour',
    description: `**${events.length} annonces** au total — ${highImpact.length} fort impact, ${mediumImpact.length} moyen, ${lowImpact.length} faible`,
    color: 0x5865f2,
    fields,
    footer: {
      text: 'GoldyXbOT — Calendrier Économique',
    },
    timestamp: new Date().toISOString(),
  };
}

/**
 * Envoie un message via webhook Discord
 * @param {string} webhookUrl - URL du webhook
 * @param {Object} payload - Payload Discord
 */
async function sendWebhook(webhookUrl, payload) {
  try {
    await axios.post(webhookUrl, payload, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });
  } catch (error) {
    if (error.response) {
      console.error(
        `[Discord] Erreur webhook HTTP ${error.response.status}:`,
        error.response.data
      );
      // Gérer le rate limit Discord
      if (error.response.status === 429) {
        const retryAfter = error.response.data?.retry_after ?? 1;
        console.warn(`[Discord] Rate limité, réessai dans ${retryAfter}s...`);
        await new Promise((r) => setTimeout(r, retryAfter * 1000));
        await sendWebhook(webhookUrl, payload);
      }
    } else {
      console.error('[Discord] Erreur réseau:', error.message);
    }
  }
}

/**
 * Envoie un événement sur Discord
 * @param {string[]} webhookUrls - Liste des webhooks
 * @param {Object} event - Événement économique
 * @param {boolean} isReminder - Est-ce un rappel ?
 */
async function sendEvent(webhookUrls, event, isReminder = false) {
  const embed = formatEventEmbed(event, isReminder);
  const payload = { embeds: [embed] };

  for (const url of webhookUrls) {
    await sendWebhook(url, payload);
    // Petite pause pour éviter le rate limit
    if (webhookUrls.length > 1) {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
}

/**
 * Envoie le résumé journalier sur Discord
 * @param {string[]} webhookUrls - Liste des webhooks
 * @param {Object[]} events - Liste des événements
 */
async function sendDailySummary(webhookUrls, events) {
  const embed = formatDailySummaryEmbed(events);
  const payload = {
    content: '**📊 Calendrier Économique — Résumé du Jour**',
    embeds: [embed],
  };

  for (const url of webhookUrls) {
    await sendWebhook(url, payload);
    if (webhookUrls.length > 1) {
      await new Promise((r) => setTimeout(r, 500));
    }
  }
}

module.exports = {
  sendEvent,
  sendDailySummary,
  sendWebhook,
  formatEventEmbed,
  formatDailySummaryEmbed,
};
