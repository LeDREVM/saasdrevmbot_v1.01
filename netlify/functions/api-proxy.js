/**
 * Netlify Function — reverse-proxy vers les backends applicatifs.
 * Exposée via redirects sur :  /api/*  et  /health   (voir netlify.toml)
 *
 * Remplace les redirects `[[redirects]] to = "https://…"` en dur : netlify.toml
 * n'interpole PAS les variables d'environnement, donc une URL backend écrite là
 * est figée dans le repo et impose un redéploiement à chaque changement. Ici
 * l'URL vit dans les env vars Netlify → modifiable depuis l'UI, sans commit.
 *
 * Env vars (Netlify → Site settings → Environment variables) :
 *   BACKEND_API_URL   — base du backend FastAPI, SANS slash final
 *                       (ex. https://drevm-api.onrender.com)
 *   EXPRESS_API_URL   — base du backend Express « GoldyXbOT » (page Stats).
 *                       Optionnel : si absent, on retombe sur BACKEND_API_URL.
 *   PROXY_TIMEOUT_MS  — timeout amont, défaut 9000 (< la limite Netlify de 10 s,
 *                       pour renvoyer un 504 lisible au lieu d'un timeout opaque).
 *
 * Tant qu'une variable est absente, on renvoie un 503 JSON explicite plutôt
 * qu'une erreur de proxy illisible : le front sait alors *pourquoi* l'API ne
 * répond pas (cf. lessons.md L07 — endpoints déployés mais env vars vides).
 */

// Routes servies par le backend Express (GoldyXbOT) et non par FastAPI.
const EXPRESS_PREFIXES = ['/api/stats/correlations'];

const DEFAULT_TIMEOUT_MS = 9000;

// En-têtes qui ne doivent jamais être relayés tels quels (hop-by-hop + réécrits
// par fetch). `host` en particulier casserait le routage côté amont.
const STRIPPED_REQUEST_HEADERS = new Set([
  'host',
  'connection',
  'keep-alive',
  'proxy-authorization',
  'te',
  'trailer',
  'transfer-encoding',
  'upgrade',
  'content-length',
  'accept-encoding', // laisse fetch négocier / décompresser
]);

const STRIPPED_RESPONSE_HEADERS = new Set([
  'connection',
  'keep-alive',
  'transfer-encoding',
  'upgrade',
  'content-encoding', // le corps est déjà décompressé par fetch
  'content-length', // recalculé par Netlify
]);

// Types de contenu renvoyés en texte ; tout le reste part en base64.
const TEXTUAL_CONTENT = /^(text\/|application\/(json|xml|javascript|x-www-form-urlencoded)|application\/[\w.+-]+\+(json|xml))/i;

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-N8N-Secret',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
};

function jsonResponse(statusCode, payload) {
  return {
    statusCode,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', ...CORS_HEADERS },
    body: JSON.stringify(payload),
  };
}

/**
 * Chemin + query réellement demandés par le client.
 * Derrière une réécriture (status 200) Netlify conserve l'URL d'origine dans
 * `rawUrl` ; `event.path` sert de repli, et on retire le préfixe de la fonction
 * au cas où elle serait appelée en direct.
 */
function originalTarget(event) {
  let pathname = event.path || '/';
  let search = '';

  if (event.rawUrl) {
    try {
      const url = new URL(event.rawUrl);
      pathname = url.pathname;
      search = url.search;
    } catch {
      /* rawUrl inexploitable → on garde event.path */
    }
  }

  const prefix = '/.netlify/functions/api-proxy';
  if (pathname.startsWith(prefix)) {
    pathname = pathname.slice(prefix.length) || '/';
  }

  if (!search) {
    const qs = event.rawQuery || '';
    search = qs ? `?${qs}` : '';
  }

  return { pathname, search };
}

function pickUpstream(pathname) {
  const isExpress = EXPRESS_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`)
  );

  // EXPRESS_API_URL est optionnel : mono-backend, tout part sur FastAPI.
  const varName = isExpress && process.env.EXPRESS_API_URL ? 'EXPRESS_API_URL' : 'BACKEND_API_URL';
  const base = (process.env[varName] || '').trim().replace(/\/+$/, '');

  return { varName, base };
}

function forwardedRequestHeaders(event) {
  const out = {};
  for (const [name, value] of Object.entries(event.headers || {})) {
    const lower = name.toLowerCase();
    if (STRIPPED_REQUEST_HEADERS.has(lower)) continue;
    if (lower.startsWith('x-nf-')) continue; // en-têtes internes Netlify
    out[name] = value;
  }
  return out;
}

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 204, headers: CORS_HEADERS, body: '' };
  }

  const { pathname, search } = originalTarget(event);
  const { varName, base } = pickUpstream(pathname);

  if (!base) {
    return jsonResponse(503, {
      error: `${varName} non configurée`,
      detail:
        `Le backend n'est pas câblé : définis ${varName} dans Netlify → Site settings ` +
        `→ Environment variables (URL HTTPS de base, sans slash final), puis redéploie.`,
      path: pathname,
    });
  }

  if (!/^https?:\/\//i.test(base)) {
    return jsonResponse(503, {
      error: `${varName} invalide`,
      detail: `Valeur attendue : une URL absolue commençant par https:// (reçu : "${base}").`,
      path: pathname,
    });
  }

  const target = `${base}${pathname}${search}`;

  const timeoutMs = Number(process.env.PROXY_TIMEOUT_MS) || DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const hasBody = !['GET', 'HEAD'].includes(event.httpMethod);
    const upstream = await fetch(target, {
      method: event.httpMethod,
      headers: forwardedRequestHeaders(event),
      body: hasBody && event.body
        ? (event.isBase64Encoded ? Buffer.from(event.body, 'base64') : event.body)
        : undefined,
      redirect: 'manual',
      signal: controller.signal,
    });

    const headers = { ...CORS_HEADERS };
    upstream.headers.forEach((value, name) => {
      if (!STRIPPED_RESPONSE_HEADERS.has(name.toLowerCase())) headers[name] = value;
    });

    const contentType = upstream.headers.get('content-type') || '';
    const buffer = Buffer.from(await upstream.arrayBuffer());
    const isText = TEXTUAL_CONTENT.test(contentType);

    return {
      statusCode: upstream.status,
      headers,
      body: isText ? buffer.toString('utf8') : buffer.toString('base64'),
      isBase64Encoded: !isText,
    };
  } catch (err) {
    const aborted = err && (err.name === 'AbortError' || err.name === 'TimeoutError');
    return jsonResponse(aborted ? 504 : 502, {
      error: aborted ? 'Backend injoignable (timeout)' : 'Backend injoignable',
      detail: aborted
        ? `Aucune réponse de ${target} en ${timeoutMs} ms.`
        : `Échec de la requête vers ${target} : ${err && err.message ? err.message : String(err)}`,
      hint: `Vérifie que ${varName} pointe sur un backend démarré et accessible en HTTPS.`,
    });
  } finally {
    clearTimeout(timer);
  }
};
