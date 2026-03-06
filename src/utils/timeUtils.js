/**
 * Utilitaires pour la gestion du temps et des annonces
 */

/**
 * Parse une heure ForexFactory (format "8:30am", "10:00pm", "All Day")
 * en objet Date du jour (UTC ou heure locale selon FF)
 * @param {string} timeStr - Chaîne d'heure
 * @param {string} dateStr - Chaîne de date (optionnel)
 * @returns {Date|null}
 */
function parseForexFactoryTime(timeStr, dateStr) {
  if (!timeStr || timeStr === 'All Day' || timeStr === 'Tentative') return null;

  try {
    const now = new Date();
    const today = dateStr
      ? parseDateString(dateStr, now)
      : new Date(now.getFullYear(), now.getMonth(), now.getDate());

    // Format "8:30am" ou "10:00pm"
    const match = timeStr.match(/^(\d{1,2}):(\d{2})(am|pm)$/i);
    if (!match) return null;

    let hours = parseInt(match[1], 10);
    const minutes = parseInt(match[2], 10);
    const period = match[3].toLowerCase();

    if (period === 'pm' && hours !== 12) hours += 12;
    if (period === 'am' && hours === 12) hours = 0;

    const date = new Date(today);
    date.setHours(hours, minutes, 0, 0);
    return date;
  } catch (e) {
    return null;
  }
}

/**
 * Parse une date ForexFactory (format "Mon Mar 10", "Tue Mar 11", etc.)
 */
function parseDateString(dateStr, reference = new Date()) {
  try {
    // ForexFactory format: "Mon Mar 10" ou "Today" ou "Tomorrow"
    if (dateStr.toLowerCase() === 'today') {
      return new Date(
        reference.getFullYear(),
        reference.getMonth(),
        reference.getDate()
      );
    }
    if (dateStr.toLowerCase() === 'tomorrow') {
      const d = new Date(reference);
      d.setDate(d.getDate() + 1);
      return new Date(d.getFullYear(), d.getMonth(), d.getDate());
    }

    // Essayer de parser directement
    const parsed = new Date(dateStr + ' ' + reference.getFullYear());
    if (!isNaN(parsed.getTime())) return parsed;

    return new Date(
      reference.getFullYear(),
      reference.getMonth(),
      reference.getDate()
    );
  } catch (e) {
    return new Date(
      reference.getFullYear(),
      reference.getMonth(),
      reference.getDate()
    );
  }
}

/**
 * Vérifie si un événement est dans les N prochaines minutes
 * @param {Date} eventTime - Heure de l'événement
 * @param {number} minutes - Nombre de minutes
 * @returns {boolean}
 */
function isWithinMinutes(eventTime, minutes) {
  if (!eventTime || isNaN(eventTime.getTime())) return false;
  const now = Date.now();
  const diff = eventTime.getTime() - now;
  return diff > 0 && diff <= minutes * 60 * 1000;
}

/**
 * Vérifie si un événement vient de se produire (dans les 5 dernières minutes)
 * @param {Date} eventTime
 * @returns {boolean}
 */
function justHappened(eventTime) {
  if (!eventTime || isNaN(eventTime.getTime())) return false;
  const now = Date.now();
  const diff = now - eventTime.getTime();
  return diff >= 0 && diff <= 5 * 60 * 1000;
}

/**
 * Formate une date en heure locale lisible
 * @param {Date} date
 * @param {string} timezone
 * @returns {string}
 */
function formatTime(date, timezone = 'Europe/Paris') {
  if (!date || isNaN(date.getTime())) return 'N/A';
  return date.toLocaleTimeString('fr-FR', {
    timeZone: timezone,
    hour: '2-digit',
    minute: '2-digit',
  });
}

module.exports = {
  parseForexFactoryTime,
  parseDateString,
  isWithinMinutes,
  justHappened,
  formatTime,
};
