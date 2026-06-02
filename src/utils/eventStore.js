/**
 * Store des événements connus + déduplication des notifications.
 *
 * Persisté sur disque (data/event_store.json) afin que l'état de déduplication
 * survive aux redémarrages : sans ça, un restart en début de session relance un
 * spam de notifications Discord pour des événements déjà annoncés.
 *
 * Les écritures sont coalescées (debounce) pour ne pas toucher le disque à
 * chaque marquage pendant un scan.
 */

const path = require('path');
const fs   = require('fs');

const DATA_DIR   = path.join(__dirname, '../../data');
const STORE_FILE = path.join(DATA_DIR, 'event_store.json');

const RETENTION_MS    = 48 * 60 * 60 * 1000; // 48h
const SAVE_DEBOUNCE_MS = 3000;

const sentEvents    = new Set();
const remindersSent = new Set();
const knownEvents   = new Map(); // id -> event

let _dirty     = false;
let _saveTimer = null;

// ─── Persistance ────────────────────────────────────────────────────────────

function load() {
  try {
    if (!fs.existsSync(STORE_FILE)) return;
    const data = JSON.parse(fs.readFileSync(STORE_FILE, 'utf8'));
    const cutoff = Date.now() - RETENTION_MS;

    if (Array.isArray(data.knownEvents)) {
      for (const [id, event] of data.knownEvents) {
        if (event && (!event._addedAt || event._addedAt > cutoff)) knownEvents.set(id, event);
      }
    }
    if (Array.isArray(data.sentEvents))    for (const id of data.sentEvents)    sentEvents.add(id);
    if (Array.isArray(data.remindersSent)) for (const id of data.remindersSent) remindersSent.add(id);

    console.log(`[EventStore] Restauré: ${knownEvents.size} événements, ${sentEvents.size} notifiés`);
  } catch (err) {
    console.warn('[EventStore] Chargement échoué:', err.message);
  }
}

function scheduleSave() {
  _dirty = true;
  if (_saveTimer) return;
  _saveTimer = setTimeout(() => { _saveTimer = null; flushStore(); }, SAVE_DEBOUNCE_MS);
  if (_saveTimer.unref) _saveTimer.unref();
}

/** Écrit l'état sur disque s'il a changé. À appeler en fin de scan / à l'arrêt. */
function flushStore() {
  if (!_dirty) return;
  try {
    if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
    const payload = {
      sentEvents:    Array.from(sentEvents),
      remindersSent: Array.from(remindersSent),
      knownEvents:   Array.from(knownEvents.entries()),
      _savedAt:      Date.now(),
    };
    fs.writeFileSync(STORE_FILE, JSON.stringify(payload));
    _dirty = false;
  } catch (err) {
    console.warn('[EventStore] Sauvegarde échouée:', err.message);
  }
}

// ─── API ────────────────────────────────────────────────────────────────────

function isEventSent(eventId)    { return sentEvents.has(eventId); }
function markEventSent(eventId)  { sentEvents.add(eventId); scheduleSave(); }

function isReminderSent(eventId)   { return remindersSent.has(eventId); }
function markReminderSent(eventId) { remindersSent.add(eventId); scheduleSave(); }

function upsertEvent(event) { knownEvents.set(event.id, event); scheduleSave(); }

function getAllEvents() { return Array.from(knownEvents.values()); }

function hasNewResult(event) {
  const known = knownEvents.get(event.id);
  if (!known) return false;
  return event.actual && event.actual !== known.actual;
}

/** Nettoie les événements de plus de 48h (anti-fuite mémoire). */
function cleanup() {
  const cutoff = Date.now() - RETENTION_MS;
  let removed = 0;

  for (const [id, event] of knownEvents.entries()) {
    if (event._addedAt && event._addedAt < cutoff) {
      knownEvents.delete(id);
      sentEvents.delete(id);
      remindersSent.delete(id);
      removed++;
    }
  }

  if (removed > 0) {
    console.log(`[EventStore] Nettoyage: ${removed} événements supprimés`);
    scheduleSave();
  }
}

// Restauration au démarrage + nettoyage périodique
load();
setInterval(cleanup, 6 * 60 * 60 * 1000);

module.exports = {
  isEventSent,
  markEventSent,
  isReminderSent,
  markReminderSent,
  upsertEvent,
  getAllEvents,
  hasNewResult,
  cleanup,
  flushStore,
};
