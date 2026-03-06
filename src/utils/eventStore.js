/**
 * Store en mémoire pour éviter d'envoyer les mêmes annonces plusieurs fois.
 * À remplacer par une DB (SQLite/Redis) pour la persistance entre redémarrages.
 */

const sentEvents = new Set();
const remindersSent = new Set();
const knownEvents = new Map(); // id -> event

/**
 * Vérifie si un événement a déjà été envoyé
 */
function isEventSent(eventId) {
  return sentEvents.has(eventId);
}

/**
 * Marque un événement comme envoyé
 */
function markEventSent(eventId) {
  sentEvents.add(eventId);
}

/**
 * Vérifie si un rappel a déjà été envoyé pour un événement
 */
function isReminderSent(eventId) {
  return remindersSent.has(eventId);
}

/**
 * Marque un rappel comme envoyé
 */
function markReminderSent(eventId) {
  remindersSent.add(eventId);
}

/**
 * Ajoute ou met à jour un événement connu
 */
function upsertEvent(event) {
  knownEvents.set(event.id, event);
}

/**
 * Récupère tous les événements connus
 */
function getAllEvents() {
  return Array.from(knownEvents.values());
}

/**
 * Vérifie si un événement a un résultat (actual) mis à jour depuis la dernière fois
 */
function hasNewResult(event) {
  const known = knownEvents.get(event.id);
  if (!known) return false;
  return event.actual && event.actual !== known.actual;
}

/**
 * Nettoie les anciens événements (plus vieux que 48h) pour éviter les fuites mémoire
 */
function cleanup() {
  const cutoff = Date.now() - 48 * 60 * 60 * 1000;
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
  }
}

// Nettoyage automatique toutes les 6h
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
};
