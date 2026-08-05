/**
 * Client websocket du feed marché (backend FastAPI → Hyperliquid).
 *
 * Le backend maintient UNE connexion amont vers Hyperliquid ; ce client ne parle
 * qu'au backend. Il reçoit les bougies des 3 actifs sur une seule socket et
 * laisse l'appelant filtrer par `coin`.
 *
 * Reconnexion automatique avec backoff exponentiel — sans ça, un simple
 * redémarrage du backend laisse le chart figé sans aucun signal visible.
 */

import { API_ENDPOINTS, WS_AVAILABLE } from '$lib/config.js';

const BACKOFF_START = 1000;
const BACKOFF_MAX = 30000;

/**
 * Ouvre le flux de bougies.
 *
 * @param {object} handlers
 * @param {(candle: any) => void} handlers.onCandle   - appelé à chaque bougie reçue
 * @param {(open: boolean) => void} [handlers.onStatus] - état de la connexion
 * @returns {() => void} fonction de fermeture — À APPELER dans onDestroy
 */
export function connectMarketFeed({ onCandle, onStatus }) {
	// Aucune URL websocket câblable (MODE A Netlify sans VITE_WS_URL) : on
	// n'ouvre rien. Ouvrir malgré tout ferait boucler la reconnexion à l'infini
	// contre un proxy qui ne sait pas gérer l'upgrade HTTP.
	if (!WS_AVAILABLE) {
		onStatus?.(false);
		return () => {};
	}

	/** @type {WebSocket | null} */
	let socket = null;
	/** @type {ReturnType<typeof setTimeout> | undefined} */
	let retryTimer;
	let backoff = BACKOFF_START;
	let closed = false;

	function open() {
		if (closed) return;

		socket = new WebSocket(API_ENDPOINTS.marketStream);

		socket.onopen = () => {
			backoff = BACKOFF_START;
			onStatus?.(true);
		};

		socket.onmessage = (event) => {
			try {
				onCandle(JSON.parse(event.data));
			} catch (e) {
				console.error('Bougie illisible:', e);
			}
		};

		socket.onerror = () => {
			// onclose suit systématiquement onerror : la reconnexion est gérée là.
			socket?.close();
		};

		socket.onclose = () => {
			onStatus?.(false);
			if (closed) return;
			retryTimer = setTimeout(open, backoff);
			backoff = Math.min(backoff * 2, BACKOFF_MAX);
		};
	}

	open();

	return () => {
		closed = true;
		clearTimeout(retryTimer);
		socket?.close();
	};
}

/**
 * Historique bufferisé côté backend, prêt pour Lightweight Charts.
 * @param {string} coin
 * @returns {Promise<any[]>}
 */
export async function fetchCandles(coin) {
	const res = await fetch(`${API_ENDPOINTS.marketCandles}/${coin}`);
	if (!res.ok) throw new Error(`Historique ${coin}: HTTP ${res.status}`);
	const data = await res.json();
	return data.candles || [];
}
