import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	
	server: {
		port: 5173,
		host: true, // Permet l'accès depuis le réseau local
		strictPort: false,
		proxy: {
			// Corrélations news/prix = feature GoldyXbOT (Express :3000). Règle spécifique
			// listée AVANT '/api' pour être prioritaire.
			'/api/stats/correlations': {
				target: process.env.VITE_EXPRESS_URL || 'http://localhost:3000',
				changeOrigin: true
			},
			// Reste de l'API applicative = FastAPI :8000 (source principale).
			// Note : le calendrier public '/api/calendar' est servi par la fonction
			// Netlify — lance `netlify dev` pour le tester en local.
			'/api': {
				target: process.env.VITE_API_URL || 'http://localhost:8000',
				changeOrigin: true
			}
		}
	},
	
	preview: {
		port: 4173,
		host: true
	},
	
	build: {
		target: 'esnext',
		minify: 'esbuild',
		sourcemap: false,
		chunkSizeWarningLimit: 1000
	},
	
	optimizeDeps: {
		include: ['chart.js', 'date-fns'],
		exclude: ['@sveltejs/kit']
	},
	
	resolve: {
		alias: {
			$lib: '/src/lib',
			$components: '/src/components'
		}
	}
});
