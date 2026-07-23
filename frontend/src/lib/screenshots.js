/**
 * Helpers Screenshot Manager — DREVM.
 * Encapsule Storage (bucket privé) + table journal_screenshots.
 * Toutes les fonctions supposent une session authentifiée (RLS actives).
 */
import { supabase, SCREENSHOT_BUCKET } from '$lib/supabase';

const sb = /** @type {any} */ (supabase);

/** Cache mémoire des URLs signées (évite de re-signer à chaque render). */
const signedCache = new Map(); // path -> { url, exp }
const SIGN_TTL = 3600; // secondes

/** Nettoie un nom de fichier pour Storage (pas d'espaces/accents). */
function safeName(name) {
  return name.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
             .replace(/[^a-zA-Z0-9._-]/g, '_').slice(-80);
}

/**
 * Upload un fichier + crée la ligne de métadonnées.
 * @param {File} file
 * @param {{symbol?:string, timeframe?:string, grade?:string|null, note?:string,
 *          tags?:string[], trade_id?:string|null, taken_at?:string}} meta
 * @returns {Promise<{data:any, error:string|null}>}
 */
export async function uploadScreenshot(file, meta = {}) {
  const { data: { user } } = await sb.auth.getUser();
  if (!user) return { data: null, error: 'Non connecté' };

  const path = `${user.id}/${crypto.randomUUID()}-${safeName(file.name)}`;
  const { error: upErr } = await sb.storage
    .from(SCREENSHOT_BUCKET)
    .upload(path, file, { contentType: file.type, upsert: false });
  if (upErr) return { data: null, error: 'Upload: ' + upErr.message };

  const row = {
    user_id: user.id,
    storage_path: path,
    symbol: meta.symbol || null,
    timeframe: meta.timeframe || null,
    grade: meta.grade || null,
    note: meta.note || null,
    tags: meta.tags || [],
    trade_id: meta.trade_id || null,
    taken_at: meta.taken_at || new Date().toISOString()
  };
  const { data, error } = await sb.from('journal_screenshots')
    .insert(row).select().single();

  if (error) {
    // rollback storage si l'insert échoue (pas d'orphelin)
    await sb.storage.from(SCREENSHOT_BUCKET).remove([path]);
    return { data: null, error: 'DB: ' + error.message };
  }
  return { data, error: null };
}

/**
 * Liste les captures avec filtres optionnels.
 * @param {{symbol?:string, timeframe?:string, grade?:string, trade_id?:string,
 *          search?:string, limit?:number}} f
 */
export async function listScreenshots(f = {}) {
  let q = sb.from('journal_screenshots').select('*')
    .order('taken_at', { ascending: false })
    .limit(f.limit || 200);
  if (f.symbol)    q = q.eq('symbol', f.symbol);
  if (f.timeframe) q = q.eq('timeframe', f.timeframe);
  if (f.grade)     q = q.eq('grade', f.grade);
  if (f.trade_id)  q = q.eq('trade_id', f.trade_id);
  if (f.search)    q = q.ilike('note', `%${f.search}%`);
  const { data, error } = await q;
  return { data: data || [], error: error?.message || null };
}

/**
 * URLs signées en batch (avec cache). Retourne Map path -> url.
 * @param {string[]} paths
 */
export async function getSignedUrls(paths) {
  const out = new Map();
  const now = Date.now();
  const missing = [];

  for (const p of paths) {
    const c = signedCache.get(p);
    if (c && c.exp > now) out.set(p, c.url);
    else missing.push(p);
  }
  if (missing.length) {
    const { data } = await sb.storage.from(SCREENSHOT_BUCKET)
      .createSignedUrls(missing, SIGN_TTL);
    for (const item of data || []) {
      if (item.signedUrl && !item.error) {
        out.set(item.path, item.signedUrl);
        signedCache.set(item.path, { url: item.signedUrl, exp: now + (SIGN_TTL - 60) * 1000 });
      }
    }
  }
  return out;
}

/** Met à jour les métadonnées d'une capture. */
export async function updateScreenshot(id, patch) {
  const { data, error } = await sb.from('journal_screenshots')
    .update(patch).eq('id', id).select().single();
  return { data, error: error?.message || null };
}

/**
 * Lie / délie une capture à un trade + synchronise journal_trades.screenshots
 * (rétro-compat avec l'affichage existant de la page Journal).
 */
export async function linkToTrade(shot, tradeId /* string|null */) {
  const { error } = await sb.from('journal_screenshots')
    .update({ trade_id: tradeId }).eq('id', shot.id);
  if (error) return { error: error.message };

  // Sync du TEXT[] côté trade (ajout sur le nouveau, retrait sur l'ancien)
  const syncTrade = async (tid, add) => {
    if (!tid) return;
    const { data: t } = await sb.from('journal_trades')
      .select('screenshots').eq('id', tid).single();
    if (!t) return;
    let arr = t.screenshots || [];
    arr = add
      ? (arr.includes(shot.storage_path) ? arr : [...arr, shot.storage_path])
      : arr.filter((p) => p !== shot.storage_path);
    await sb.from('journal_trades').update({ screenshots: arr }).eq('id', tid);
  };
  await syncTrade(shot.trade_id, false); // retire de l'ancien trade
  await syncTrade(tradeId, true);        // ajoute au nouveau
  return { error: null };
}

/** Supprime capture : fichier Storage + ligne DB + référence dans le trade lié. */
export async function deleteScreenshot(shot) {
  const { error: stErr } = await sb.storage
    .from(SCREENSHOT_BUCKET).remove([shot.storage_path]);
  if (stErr) return { error: 'Storage: ' + stErr.message };

  if (shot.trade_id) await linkToTrade(shot, null);

  const { error } = await sb.from('journal_screenshots').delete().eq('id', shot.id);
  signedCache.delete(shot.storage_path);
  return { error: error?.message || null };
}
