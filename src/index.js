require('dotenv').config();
const cron = require('node-cron');

const { scrapeForexFactory } = require('./scrapers/forexfactory');
const { scrapeInvesting } = require('./scrapers/investing');
const { scrapeAlphaVantage } = require('./scrapers/alphavantage');
const { sendEvent, sendDailySummary } = require('./utils/discord');
const { logEvent } = require('./services/correlationEngine');
const {
  isEventSent,
  markEventSent,
  isReminderSent,
  markReminderSent,
  upsertEvent,
  hasNewResult,
} = require('./utils/eventStore');
const { parseForexFactoryTime, isWithinMinutes } = require('./utils/timeUtils');

// ─── Configuration ────────────────────────────────────────────────────────────

const WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL;
const WEBHOOK_URLS_RAW = process.env.DISCORD_WEBHOOK_URLS;

// Construire la liste des webhooks
let WEBHOOK_URLS = [];
if (WEBHOOK_URLS_RAW) {
  WEBHOOK_URLS = WEBHOOK_URLS_RAW.split(',').map((u) => u.trim()).filter(Boolean);
}
if (WEBHOOK_URL && !WEBHOOK_URLS.includes(WEBHOOK_URL)) {
  WEBHOOK_URLS.unshift(WEBHOOK_URL);
}

const MIN_IMPACT = parseInt(process.env.MIN_IMPACT ?? '3', 10);
const CURRENCIES_RAW = process.env.CURRENCIES ?? '';
const CURRENCIES = CURRENCIES_RAW
  ? CURRENCIES_RAW.split(',').map((c) => c.trim().toUpperCase())
  : [];

const CHECK_INTERVAL = parseInt(process.env.CHECK_INTERVAL ?? '5', 10);
const REMINDER_MINUTES = parseInt(process.env.REMINDER_MINUTES ?? '15', 10);
const TIMEZONE = process.env.TIMEZONE ?? 'Europe/Paris';

const ENABLE_FF = process.env.ENABLE_FOREXFACTORY !== 'false';
const ENABLE_INV = process.env.ENABLE_INVESTING !== 'false';
const ENABLE_AV  = process.env.ENABLE_ALPHAVANTAGE === 'true';
const AV_API_KEY = process.env.ALPHA_VANTAGE_API_KEY ?? '';
const AV_HORIZON = process.env.ALPHA_VANTAGE_HORIZON ?? '3month';

// ─── Validation de la config ──────────────────────────────────────────────────

function validateConfig() {
  if (WEBHOOK_URLS.length === 0) {
    console.error(
      '❌ ERREUR: Aucun webhook Discord configuré.\n' +
        '   Copiez .env.example en .env et renseignez DISCORD_WEBHOOK_URL'
    );
    process.exit(1);
  }

  console.log('✅ Configuration:');
  console.log(`   Webhooks: ${WEBHOOK_URLS.length} configuré(s)`);
  console.log(`   Impact minimum: ${MIN_IMPACT} (${['', 'Faible', 'Moyen', 'Fort'][MIN_IMPACT]})`);
  console.log(
    `   Devises filtrées: ${CURRENCIES.length > 0 ? CURRENCIES.join(', ') : 'Toutes'}`
  );
  console.log(`   Intervalle: ${CHECK_INTERVAL} minutes`);
  console.log(`   Rappel avant: ${REMINDER_MINUTES > 0 ? `${REMINDER_MINUTES}min` : 'Désactivé'}`);
  console.log(`   Sources: ${[ENABLE_FF && 'ForexFactory', ENABLE_INV && 'Investing', ENABLE_AV && 'AlphaVantage'].filter(Boolean).join(', ')}`);
}

// ─── Filtrage des événements ──────────────────────────────────────────────────

function filterEvents(events) {
  return events.filter((event) => {
    // Filtrer par impact
    if (event.impactLevel < MIN_IMPACT) return false;

    // Filtrer par devise
    if (CURRENCIES.length > 0 && !CURRENCIES.includes(event.currency.toUpperCase())) {
      return false;
    }

    return true;
  });
}

// ─── Logique principale de scraping ──────────────────────────────────────────

let isRunning = false;

async function scrapeAndNotify() {
  if (isRunning) {
    console.log('[Bot] Scan déjà en cours, skip...');
    return;
  }

  isRunning = true;
  console.log(`\n[Bot] Scan en cours... ${new Date().toLocaleString('fr-FR', { timeZone: TIMEZONE })}`);

  try {
    // Scraper les sources activées en parallèle
    const scrapers = [];
    if (ENABLE_FF)  scrapers.push(scrapeForexFactory());
    if (ENABLE_INV) scrapers.push(scrapeInvesting());
    if (ENABLE_AV)  scrapers.push(scrapeAlphaVantage(AV_API_KEY, AV_HORIZON));

    const results = await Promise.allSettled(scrapers);

    let allEvents = [];
    results.forEach((result, i) => {
      const source = i === 0 ? (ENABLE_FF ? 'ForexFactory' : 'Investing') : 'Investing';
      if (result.status === 'fulfilled') {
        console.log(`[Bot] ${source}: ${result.value.length} événements récupérés`);
        allEvents = allEvents.concat(result.value);
      } else {
        console.error(`[Bot] ${source} échoué:`, result.reason?.message ?? result.reason);
      }
    });

    // Filtrer selon la config
    const filtered = filterEvents(allEvents);
    console.log(`[Bot] ${filtered.length} événements après filtrage`);

    // Traiter chaque événement
    for (const event of filtered) {
      // Enrichir avec un timestamp si possible
      const eventTime = parseForexFactoryTime(event.time, event.date);
      const enrichedEvent = { ...event, _parsedTime: eventTime, _addedAt: Date.now() };

      // Mettre à jour le store + persister pour la corrélation historique
      const hadResult = upsertEvent(enrichedEvent);
      logEvent(enrichedEvent);

      // 1. Envoyer le rappel (si activé et dans la fenêtre)
      if (
        REMINDER_MINUTES > 0 &&
        eventTime &&
        isWithinMinutes(eventTime, REMINDER_MINUTES) &&
        !isReminderSent(event.id)
      ) {
        console.log(`[Bot] Rappel: ${event.currency} ${event.event} dans ${REMINDER_MINUTES}min`);
        await sendEvent(WEBHOOK_URLS, { ...enrichedEvent, reminderMinutes: REMINDER_MINUTES }, true);
        markReminderSent(event.id);
      }

      // 2. Envoyer l'annonce initiale (nouvelle annonce non encore envoyée)
      if (!isEventSent(event.id)) {
        console.log(`[Bot] Nouvelle annonce: [${event.source}] ${event.currency} ${event.event}`);
        await sendEvent(WEBHOOK_URLS, enrichedEvent, false);
        markEventSent(event.id);
      }

      // 3. Mettre à jour si résultat disponible (et pas déjà notifié)
      else if (event.actual && hasNewResult(enrichedEvent)) {
        const updateId = `${event.id}_RESULT_${event.actual}`;
        if (!isEventSent(updateId)) {
          console.log(`[Bot] Résultat: ${event.currency} ${event.event} = ${event.actual}`);
          await sendEvent(WEBHOOK_URLS, enrichedEvent, false);
          markEventSent(updateId);
        }
      }

      // Pause entre les envois
      await new Promise((r) => setTimeout(r, 300));
    }
  } catch (error) {
    console.error('[Bot] Erreur globale:', error.message);
  } finally {
    isRunning = false;
  }
}

// ─── Résumé journalier ────────────────────────────────────────────────────────

async function sendMorningBriefing() {
  console.log('[Bot] Envoi du briefing matinal...');
  try {
    const scrapers = [];
    if (ENABLE_FF)  scrapers.push(scrapeForexFactory());
    if (ENABLE_INV) scrapers.push(scrapeInvesting());
    if (ENABLE_AV)  scrapers.push(scrapeAlphaVantage(AV_API_KEY, AV_HORIZON));

    const results = await Promise.allSettled(scrapers);
    let allEvents = [];
    results.forEach((r) => {
      if (r.status === 'fulfilled') allEvents = allEvents.concat(r.value);
    });

    const filtered = filterEvents(allEvents);
    if (filtered.length > 0) {
      await sendDailySummary(WEBHOOK_URLS, filtered);
      console.log(`[Bot] Briefing envoyé: ${filtered.length} événements`);
    } else {
      console.log('[Bot] Aucun événement pour le briefing');
    }
  } catch (error) {
    console.error('[Bot] Erreur briefing:', error.message);
  }
}

// ─── Démarrage ────────────────────────────────────────────────────────────────

async function main() {
  console.log('🤖 GoldyXbOT — Calendrier Économique Discord');
  console.log('='.repeat(50));
  validateConfig();
  console.log('='.repeat(50));

  // Résumé journalier à 8h00 (heure locale du serveur)
  cron.schedule('0 8 * * 1-5', sendMorningBriefing, {
    timezone: TIMEZONE,
  });
  console.log(`[Bot] Briefing matinal programmé à 8h00 (${TIMEZONE})`);

  // Scan périodique
  cron.schedule(`*/${CHECK_INTERVAL} * * * *`, scrapeAndNotify);
  console.log(`[Bot] Scan toutes les ${CHECK_INTERVAL} minutes`);

  // Premier scan immédiat au démarrage
  console.log('[Bot] Premier scan au démarrage...\n');
  await scrapeAndNotify();
}

// Gestion propre de l'arrêt
process.on('SIGINT', () => {
  console.log('\n[Bot] Arrêt propre...');
  process.exit(0);
});

process.on('unhandledRejection', (reason) => {
  console.error('[Bot] Promesse rejetée non gérée:', reason);
});

main().catch((err) => {
  console.error('[Bot] Erreur fatale:', err);
  process.exit(1);
});
