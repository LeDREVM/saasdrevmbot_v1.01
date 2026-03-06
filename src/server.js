require('dotenv').config();
const express = require('express');
const http    = require('http');
const { Server } = require('socket.io');
const path    = require('path');
const cron    = require('node-cron');

const { scrapeForexFactory }  = require('./scrapers/forexfactory');
const { scrapeInvesting }     = require('./scrapers/investing');
const { sendEvent, sendDailySummary } = require('./utils/discord');
const {
  isEventSent, markEventSent,
  isReminderSent, markReminderSent,
  upsertEvent, getAllEvents, hasNewResult,
} = require('./utils/eventStore');
const { parseForexFactoryTime, isWithinMinutes } = require('./utils/timeUtils');

// ── Nouveaux services ─────────────────────────────────────────────────────────
const saasApi        = require('./services/saasApi');
const { exportDailyCalendar, updateDailyResults, updateIndex, REPORTS_DIR } = require('./services/nextcloudExport');
const marketData     = require('./services/marketData');

// ─── Config ───────────────────────────────────────────────────────────────────

const PORT = parseInt(process.env.PORT ?? '3000', 10);

const WEBHOOK_URL      = process.env.DISCORD_WEBHOOK_URL;
const WEBHOOK_URLS_RAW = process.env.DISCORD_WEBHOOK_URLS;
let WEBHOOK_URLS = WEBHOOK_URLS_RAW
  ? WEBHOOK_URLS_RAW.split(',').map(u => u.trim()).filter(Boolean)
  : [];
if (WEBHOOK_URL && !WEBHOOK_URLS.includes(WEBHOOK_URL)) WEBHOOK_URLS.unshift(WEBHOOK_URL);

const MIN_IMPACT       = parseInt(process.env.MIN_IMPACT      ?? '3',  10);
const CURRENCIES_RAW   = process.env.CURRENCIES               ?? '';
const CURRENCIES       = CURRENCIES_RAW ? CURRENCIES_RAW.split(',').map(c => c.trim().toUpperCase()) : [];
const CHECK_INTERVAL   = parseInt(process.env.CHECK_INTERVAL  ?? '5',  10);
const REMINDER_MINUTES = parseInt(process.env.REMINDER_MINUTES ?? '15', 10);
const TIMEZONE         = process.env.TIMEZONE                 ?? 'Europe/Paris';
const ENABLE_FF        = process.env.ENABLE_FOREXFACTORY      !== 'false';
const ENABLE_INV       = process.env.ENABLE_INVESTING         !== 'false';
const ENABLE_SAAS      = process.env.ENABLE_SAAS_API          !== 'false';
const ENABLE_NEXTCLOUD = process.env.ENABLE_NEXTCLOUD         !== 'false';

// ─── Express + Socket.io ──────────────────────────────────────────────────────

const app    = express();
const server = http.createServer(app);
const io     = new Server(server, { cors: { origin: '*' } });

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ─── REST API ─────────────────────────────────────────────────────────────────

app.get('/api/events', (_req, res) => {
  const events = getAllEvents().sort((a, b) => {
    if (b.impactLevel !== a.impactLevel) return b.impactLevel - a.impactLevel;
    return (a.time || '').localeCompare(b.time || '');
  });
  res.json({ events, config: { minImpact: MIN_IMPACT, currencies: CURRENCIES, timezone: TIMEZONE } });
});

app.get('/api/config', (_req, res) => {
  res.json({
    minImpact:       MIN_IMPACT,
    currencies:      CURRENCIES,
    checkInterval:   CHECK_INTERVAL,
    reminderMinutes: REMINDER_MINUTES,
    timezone:        TIMEZONE,
    sources:         { forexfactory: ENABLE_FF, investing: ENABLE_INV, saas: ENABLE_SAAS },
    discordEnabled:  WEBHOOK_URLS.length > 0,
    nextcloudEnabled: ENABLE_NEXTCLOUD,
    nextcloudDir:    ENABLE_NEXTCLOUD ? REPORTS_DIR : null,
    saasApiUrl:      ENABLE_SAAS ? (process.env.SAAS_API_URL || 'http://localhost:8000') : null,
  });
});

// Proxy vers les stats saasDrevmbot
app.get('/api/saas/stats/:symbol', async (req, res) => {
  try {
    if (!ENABLE_SAAS || !(await saasApi.isAvailable())) {
      return res.status(503).json({ error: 'saasDrevmbot non disponible' });
    }
    const stats = await saasApi.getStatsDashboard(req.params.symbol);
    res.json(stats);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/api/saas/correlation', async (_req, res) => {
  try {
    if (!ENABLE_SAAS || !(await saasApi.isAvailable())) {
      return res.status(503).json({ error: 'saasDrevmbot non disponible' });
    }
    const data = await saasApi.getCorrelationScore();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Forcer un export Nextcloud manuel
app.post('/api/nextcloud/export', async (_req, res) => {
  try {
    if (!ENABLE_NEXTCLOUD) return res.status(503).json({ error: 'Nextcloud désactivé' });
    const events = getAllEvents();
    const filepath = exportDailyCalendar(events);
    updateIndex();
    res.json({ success: true, file: filepath, count: events.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Données marché US30 / DJIA
app.get('/api/market/us30', async (_req, res) => {
  try {
    const data = await marketData.getUS30();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ─── WebSocket ────────────────────────────────────────────────────────────────

io.on('connection', async (socket) => {
  console.log(`[WS] Client connecté: ${socket.id}`);
  socket.emit('init', { events: getAllEvents() });
  // Envoyer les données marché au nouveau client
  try {
    const market = await marketData.getUS30();
    socket.emit('market_update', market);
  } catch {}
  socket.on('disconnect', () => console.log(`[WS] Client déconnecté: ${socket.id}`));
});

function broadcastNewEvent(event)    { io.emit('new_event', event); }
function broadcastUpdateEvent(event) { io.emit('update_event', event); }
function broadcastScanStatus(status) { io.emit('scan_status', status); }
function broadcastNextcloud(info)    { io.emit('nextcloud_sync', info); }

// ─── Filtrage ─────────────────────────────────────────────────────────────────

// Filtre affichage : par devise uniquement (tous niveaux d'impact stockés)
function filterByCurrency(events) {
  if (CURRENCIES.length === 0) return events;
  return events.filter(e => CURRENCIES.includes(e.currency?.toUpperCase()));
}

// Filtre notifications Discord : devise + impact minimum
function filterForNotify(events) {
  return events.filter(e => e.impactLevel >= MIN_IMPACT);
}

// ─── Source de données : saasDrevmbot OU scrapers directs ─────────────────────

async function fetchEvents() {
  // Essayer saasDrevmbot en premier
  if (ENABLE_SAAS && await saasApi.isAvailable()) {
    try {
      // Toujours récupérer tous les niveaux pour l'affichage
      const impactLabels = ['High', 'Medium', 'Low'];

      const events = await saasApi.getTodayEvents(CURRENCIES, impactLabels);
      if (events.length > 0) {
        console.log(`[Bot] Source: saasDrevmbot (${events.length} événements)`);
        return events;
      }
    } catch (err) {
      console.warn('[Bot] saasDrevmbot fetch échoué:', err.message, '— fallback scrapers');
    }
  }

  // Fallback : scrapers directs
  console.log('[Bot] Source: scrapers directs (FF + Investing)');
  const scrapers = [];
  if (ENABLE_FF)  scrapers.push(scrapeForexFactory());
  if (ENABLE_INV) scrapers.push(scrapeInvesting());

  const results = await Promise.allSettled(scrapers);
  let allEvents = [];
  results.forEach(r => {
    if (r.status === 'fulfilled') allEvents = allEvents.concat(r.value);
    else console.error('[Bot] Scraper échoué:', r.reason?.message);
  });
  return allEvents;
}

// ─── Scan principal ───────────────────────────────────────────────────────────

let isRunning    = false;
let lastScanTime = null;
let resultsDirty = false; // Flag pour export Nextcloud résultats

async function scrapeAndNotify() {
  if (isRunning) return;
  isRunning = true;

  const startTime = Date.now();
  broadcastScanStatus({ running: true, startedAt: startTime });
  console.log(`\n[Bot] Scan... ${new Date().toLocaleTimeString('fr-FR', { timeZone: TIMEZONE })}`);

  try {
    const allEvents   = await fetchEvents();
    const forDisplay  = filterByCurrency(allEvents);   // Tous niveaux → dashboard
    const forDiscord  = filterForNotify(forDisplay);   // MIN_IMPACT → Discord/reminders
    console.log(`[Bot] ${forDisplay.length} événements (${forDiscord.length} notifiables) sur ${allEvents.length} total`);

    for (const event of forDisplay) {
      const eventTime = parseForexFactoryTime(event.time, event.date);
      const enriched  = { ...event, _parsedTime: eventTime?.toISOString() ?? null, _addedAt: Date.now() };
      const notify    = event.impactLevel >= MIN_IMPACT;

      upsertEvent(enriched);

      // Rappel (seulement pour les événements MIN_IMPACT)
      if (notify && REMINDER_MINUTES > 0 && eventTime && isWithinMinutes(eventTime, REMINDER_MINUTES) && !isReminderSent(event.id)) {
        if (WEBHOOK_URLS.length > 0) await sendEvent(WEBHOOK_URLS, { ...enriched, reminderMinutes: REMINDER_MINUTES }, true);
        markReminderSent(event.id);
      }

      // Nouvelle annonce
      if (!isEventSent(event.id)) {
        if (notify) {
          console.log(`[Bot] Nouvelle (Discord): [${event.source}] ${event.currency} ${event.event}`);
          if (WEBHOOK_URLS.length > 0) await sendEvent(WEBHOOK_URLS, enriched, false);
          await new Promise(r => setTimeout(r, 200));
        }
        markEventSent(event.id);
        broadcastNewEvent(enriched);
      }
      // Résultat mis à jour
      else if (event.actual && hasNewResult(enriched)) {
        const uid = `${event.id}_RESULT_${event.actual}`;
        if (!isEventSent(uid)) {
          if (notify && WEBHOOK_URLS.length > 0) await sendEvent(WEBHOOK_URLS, enriched, false);
          markEventSent(uid);
          broadcastUpdateEvent(enriched);
          resultsDirty = true;
        }
      }
    }

    lastScanTime = Date.now();
    broadcastScanStatus({ running: false, lastScan: lastScanTime, duration: Date.now() - startTime, count: forDisplay.length });

    // Exporter vers Nextcloud si résultats mis à jour
    if (ENABLE_NEXTCLOUD && resultsDirty) {
      try {
        const filepath = updateDailyResults(getAllEvents());
        if (filepath) {
          broadcastNextcloud({ type: 'results', file: path.basename(filepath), time: new Date().toISOString() });
        }
        resultsDirty = false;
      } catch (err) {
        console.error('[Nextcloud] Erreur export résultats:', err.message);
      }
    }

  } catch (err) {
    console.error('[Bot] Erreur globale:', err.message);
    broadcastScanStatus({ running: false, error: err.message });
  } finally {
    isRunning = false;
  }
}

// ─── Briefing matinal + export Nextcloud ──────────────────────────────────────

async function sendMorningBriefing() {
  console.log('[Bot] Briefing matinal...');
  try {
    const allEvents = await fetchEvents();
    const filtered  = filterEvents(allEvents);

    if (filtered.length > 0 && WEBHOOK_URLS.length > 0) {
      await sendDailySummary(WEBHOOK_URLS, filtered);
    }

    // Export Nextcloud calendrier du jour
    if (ENABLE_NEXTCLOUD) {
      try {
        // On exporte TOUS les événements du jour (sans filtre d'impact strict)
        const allFiltered = allEvents.filter(e => e.impactLevel >= 1);
        const filepath    = exportDailyCalendar(allFiltered);
        updateIndex();
        console.log(`[Nextcloud] ✅ Calendrier exporté: ${path.basename(filepath)}`);
        broadcastNextcloud({ type: 'calendar', file: path.basename(filepath), count: allFiltered.length, time: new Date().toISOString() });
      } catch (err) {
        console.error('[Nextcloud] Erreur export calendrier:', err.message);
      }
    }
  } catch (err) {
    console.error('[Bot] Erreur briefing:', err.message);
  }
}

// ─── Démarrage ────────────────────────────────────────────────────────────────

async function main() {
  console.log('🤖 GoldyXbOT — Dashboard + Bot Discord + Nextcloud');
  console.log('='.repeat(50));
  console.log(`   Port:        ${PORT}`);
  console.log(`   Impact min:  ${MIN_IMPACT}`);
  console.log(`   Devises:     ${CURRENCIES.length > 0 ? CURRENCIES.join(', ') : 'Toutes'}`);
  console.log(`   Discord:     ${WEBHOOK_URLS.length > 0 ? '✅' : '❌'}`);
  console.log(`   saasDrevmbot:${ENABLE_SAAS ? ' ✅ ' + (process.env.SAAS_API_URL || 'http://localhost:8000') : ' ❌'}`);
  console.log(`   Nextcloud:   ${ENABLE_NEXTCLOUD ? '✅ ' + REPORTS_DIR : '❌'}`);
  console.log('='.repeat(50));

  server.listen(PORT, () => console.log(`\n🌐 Dashboard: http://localhost:${PORT}\n`));

  // Briefing 9h tous les jours (inclut export Nextcloud)
  cron.schedule('0 9 * * *', sendMorningBriefing, { timezone: TIMEZONE });

  // Export Nextcloud résumé de fin de journée 18h
  if (ENABLE_NEXTCLOUD) {
    cron.schedule('0 18 * * 1-5', () => {
      try {
        const events   = getAllEvents();
        const filepath = exportDailyCalendar(events);
        updateIndex();
        broadcastNextcloud({ type: 'eod', file: path.basename(filepath), time: new Date().toISOString() });
        console.log(`[Nextcloud] ✅ Export fin de journée: ${path.basename(filepath)}`);
      } catch (err) {
        console.error('[Nextcloud] Erreur export 18h:', err.message);
      }
    }, { timezone: TIMEZONE });
  }

  // Scan périodique
  cron.schedule(`*/${CHECK_INTERVAL} * * * *`, scrapeAndNotify);

  // Mise à jour marché US30 toutes les 30s (broadcast WebSocket)
  setInterval(async () => {
    try {
      const data = await marketData.getUS30();
      io.emit('market_update', data);
    } catch {}
  }, 30_000);

  // Premier scan + export initial
  await scrapeAndNotify();

  // Export Nextcloud initial (si pas encore fait aujourd'hui)
  if (ENABLE_NEXTCLOUD) {
    setTimeout(async () => {
      try {
        const allEvents = await fetchEvents();
        const filepath  = exportDailyCalendar(allEvents.filter(e => e.impactLevel >= 1));
        updateIndex();
        console.log(`[Nextcloud] ✅ Export initial: ${path.basename(filepath)}`);
        broadcastNextcloud({ type: 'init', file: path.basename(filepath), time: new Date().toISOString() });
      } catch (err) {
        console.error('[Nextcloud] Erreur export initial:', err.message);
      }
    }, 5000); // Après le premier scan
  }
}

process.on('SIGINT', () => { console.log('\n[Bot] Arrêt...'); process.exit(0); });
process.on('unhandledRejection', r => console.error('[Bot] Rejet non géré:', r));

main().catch(err => { console.error('[Bot] Erreur fatale:', err); process.exit(1); });
