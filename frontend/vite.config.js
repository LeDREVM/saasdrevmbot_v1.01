import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	
	server: {
		port: 5173,
		host: true, // Permet l'accès depuis le réseau local
		strictPort: false,
		proxy: {
			'/api': {
				target: process.env.VITE_API_URL || 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api/, '')
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
