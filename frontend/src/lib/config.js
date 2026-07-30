/**
 * Configuration de l'application
 * Gère les variables d'environnement et les configurations par défaut
 */

// URL de l'API backend (FastAPI).
// 3 modes selon VITE_API_URL :
//   - non défini (dev local)        → 'http://localhost:8000' (appel direct FastAPI)
//   - '' (chaîne vide, prod Netlify) → chemins RELATIFS '/api/...' captés par le
//                                       reverse-proxy Netlify (voir netlify.toml)
//   - 'https://api.domaine.com'      → appel absolu (mode CORS)
// On teste `=== undefined` (et non `||`) pour que '' reste relatif au lieu de
// retomber sur localhost.
const _viteApiUrl = import.meta.env.VITE_API_URL;
export const API_URL = _viteApiUrl === undefined ? 'http://localhost:8000' : _viteApiUrl;

// Mode de l'application
export const MODE = import.meta.env.MODE || 'development';
export const IS_DEV = MODE === 'development';
export const IS_PROD = MODE === 'production';

// Configuration des endpoints API
// Source principale : FastAPI (API_URL). Exception : le calendrier public est
// servi par la fonction Netlify via le chemin relatif `/api/calendar` (redirect
// netlify.toml → /.netlify/functions/calendar), donc volontairement SANS API_URL.
export const API_ENDPOINTS = {
	calendar: '/api/calendar', // Fonction Netlify (chemin relatif volontaire)
	calendarToday: `${API_URL}/api/calendar/today`,
	alerts: `${API_URL}/api/alerts`,
	alertConfig: `${API_URL}/api/alert-config`,
	stats: `${API_URL}/api/stats`,
	nextcloud: `${API_URL}/api/nextcloud`,
	scoringHistory: `${API_URL}/api/scoring/history`,
	scoringStats: `${API_URL}/api/scoring/stats`,
	scoringAnalyze: `${API_URL}/api/scoring/analyze`,
	upcoming: `${API_URL}/api/alerts/upcoming`
};

// Configuration du cache
export const CACHE_CONFIG = {
	enabled: IS_PROD,
	ttl: 5 * 60 * 1000, // 5 minutes en millisecondes
	maxSize: 100 // Nombre maximum d'entrées en cache
};

// Configuration des notifications
export const NOTIFICATION_CONFIG = {
	defaultDuration: 5000, // 5 secondes
	position: 'top-right'
};

// Configuration du polling (rafraîchissement automatique)
export const POLLING_CONFIG = {
	enabled: true,
	interval: 60000, // 1 minute
	calendarInterval: 300000, // 5 minutes
	alertsInterval: 30000 // 30 secondes
};

// Devises supportées
export const SUPPORTED_CURRENCIES = [
	'EUR', 'USD', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD'
];

// Niveaux d'impact
export const IMPACT_LEVELS = {
	LOW: { value: 'low', label: 'Faible', color: '#10b981' },
	MEDIUM: { value: 'medium', label: 'Moyen', color: '#f59e0b' },
	HIGH: { value: 'high', label: 'Élevé', color: '#ef4444' }
};

// Configuration des graphiques
export const CHART_CONFIG = {
	responsive: true,
	maintainAspectRatio: false,
	animation: {
		duration: IS_DEV ? 0 : 750
	}
};

// Logs de débogage (uniquement en développement)
if (IS_DEV) {
	console.log('🔧 Configuration chargée:', {
		API_URL,
		MODE,
		ENDPOINTS: API_ENDPOINTS
	});
}

export default {
	API_URL,
	MODE,
	IS_DEV,
	IS_PROD,
	API_ENDPOINTS,
	CACHE_CONFIG,
	NOTIFICATION_CONFIG,
	POLLING_CONFIG,
	SUPPORTED_CURRENCIES,
	IMPACT_LEVELS,
	CHART_CONFIG
};
