/**
 * Client front — Bot analyse intégrale DREVM.
 * Envoie des captures (URLs signées) au backend FastAPI /api/vision/analyze
 * et persiste l'historique dans Supabase (screenshot_analyses, RLS).
 */
import { API_URL } from '$lib/config';
import { supabase } from '$lib/supabase';
import { getSignedUrls } from '$lib/screenshots';

const sb = /** @type {any} */ (supabase);

/**
 * Lance l'analyse intégrale sur une sélection de captures (même symbole).
 * @param {any[]} shots  lignes journal_screenshots sélectionnées
 * @param {string} [context]  contexte libre optionnel
 * @returns {Promise<{data:any|null, error:string|null}>}
 */
export async function runFullAnalysis(shots, context = '') {
  if (!shots.length) return { data: null, error: 'Aucune capture sélectionnée' };

  const symbols = [...new Set(shots.map((s) => s.symbol).filter(Boolean))];
  if (symbols.length > 1) {
    return { data: null, error: `Un seul symbole à la fois (sélection : ${symbols.join(', ')})` };
  }
  const symbol = symbols[0] || 'XAUUSD';

  const urls = await getSignedUrls(shots.map((s) => s.storage_path));
  const images = shots
    .map((s) => ({ url: urls.get(s.storage_path), timeframe: s.timeframe || null }))
    .filter((i) => i.url);
  if (!images.length) return { data: null, error: 'URLs signées indisponibles' };

  let resp;
  try {
    resp = await fetch(`${API_URL}/api/vision/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol, images, context: context || null })
    });
  } catch (e) {
    return { data: null, error: 'Backend injoignable — FastAPI démarré ?' };
  }
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    return { data: null, error: body.detail || `Erreur ${resp.status}` };
  }
  const data = await resp.json();

  // Persistance historique (best-effort, n'échoue pas l'analyse)
  try {
    const { data: { user } } = await sb.auth.getUser();
    if (user) {
      await sb.from('screenshot_analyses').insert({
        user_id: user.id,
        symbol,
        screenshot_ids: shots.map((s) => s.id),
        timeframes: data._meta?.timeframes || [],
        grade: data.grade || null,
        action: data.action || null,
        bias_direction: data.bias?.direction || null,
        bias_score: data.bias?.score ?? null,
        result: data,
        model: data._meta?.model || null
      });
    }
  } catch (e) {
    console.warn('Historique analyse non sauvegardé :', e);
  }
  return { data, error: null };
}

/** Charge l'historique des analyses. */
export async function listAnalyses(limit = 30) {
  const { data, error } = await sb.from('screenshot_analyses')
    .select('*').order('created_at', { ascending: false }).limit(limit);
  return { data: data || [], error: error?.message || null };
}

/** Supprime une analyse de l'historique. */
export async function deleteAnalysis(id) {
  const { error } = await sb.from('screenshot_analyses').delete().eq('id', id);
  return { error: error?.message || null };
}
