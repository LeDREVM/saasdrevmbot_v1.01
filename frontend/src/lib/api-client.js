/**
 * Bounded requests, with timers cleaned on every exit.
 * @param {string} url
 * @param {RequestInit} options
 * @param {number} timeout
 */
export async function requestJSON(url, options = {}, timeout = 8000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    let data;
    try { data = await response.json(); }
    catch { throw new Error('Le service a renvoyé une réponse illisible.'); }
    if (!response.ok) {
      const detail = typeof data.detail === 'string' ? data.detail : `Service indisponible (${response.status})`;
      throw new Error(detail);
    }
    return data;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw new Error('Le délai de réponse est dépassé. Réessaie.');
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

/** @param {string | null | undefined} iso */
export function guadeloupeTime(iso) {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Date indisponible';
  // Legacy scores had naive server dates: do not silently invent a timezone.
  if (!/(Z|[+-]\d{2}:?\d{2})$/i.test(iso)) return `${iso.replace('T', ' ').slice(0, 16)} · fuseau non précisé`;
  return date.toLocaleString('fr-FR', { timeZone: 'America/Guadeloupe',
    day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}
