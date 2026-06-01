<script>
	import Navigation from '$lib/components/Navigation.svelte';
	import { page } from '$app/stores';

	$: isHomePage = $page.url.pathname === '/';
</script>

<div class="app-layout">
	<Navigation />

	<main class="main-content" class:home-page={isHomePage}>
		<slot />
	</main>
</div>

<style>
	/* ============================================================
	   Design tokens — thème "terminal fintech sombre"
	   ============================================================ */
	:global(:root) {
		--bg: #070b16;
		--bg-grid: rgba(99, 102, 241, 0.06);
		--surface: rgba(255, 255, 255, 0.03);
		--surface-2: rgba(255, 255, 255, 0.05);
		--surface-solid: #0f1626;
		--surface-solid-2: #141d31;
		--border: rgba(148, 163, 184, 0.12);
		--border-strong: rgba(148, 163, 184, 0.22);
		--text: #e8edf6;
		--text-muted: #9aa7bd;
		--text-dim: #64748b;
		--accent: #22d3ee;
		--accent-2: #6366f1;
		--accent-3: #a855f7;
		--accent-grad: linear-gradient(135deg, #6366f1 0%, #22d3ee 100%);
		--accent-grad-soft: linear-gradient(135deg, rgba(99,102,241,0.18) 0%, rgba(34,211,238,0.18) 100%);
		--success: #34d399;
		--warning: #fbbf24;
		--danger: #f87171;
		--radius-sm: 10px;
		--radius: 16px;
		--radius-lg: 22px;
		--shadow: 0 18px 40px rgba(2, 6, 23, 0.55);
		--shadow-sm: 0 6px 18px rgba(2, 6, 23, 0.45);
		--glow: 0 0 0 1px rgba(99, 102, 241, 0.4), 0 8px 30px rgba(34, 211, 238, 0.25);
		--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
		--font-mono: 'JetBrains Mono', 'SF Mono', 'Courier New', monospace;
	}

	:global(body) {
		margin: 0;
		padding: 0;
		font-family: var(--font-sans);
		background: var(--bg);
		background-image:
			radial-gradient(900px circle at 12% -5%, rgba(99, 102, 241, 0.18), transparent 45%),
			radial-gradient(800px circle at 95% 8%, rgba(34, 211, 238, 0.12), transparent 45%),
			linear-gradient(var(--bg-grid) 1px, transparent 1px),
			linear-gradient(90deg, var(--bg-grid) 1px, transparent 1px);
		background-size: 100% 100%, 100% 100%, 44px 44px, 44px 44px;
		background-attachment: fixed;
		color: var(--text);
		-webkit-font-smoothing: antialiased;
	}

	:global(*) {
		box-sizing: border-box;
	}

	:global(::selection) {
		background: rgba(34, 211, 238, 0.3);
		color: #fff;
	}

	:global(::-webkit-scrollbar) { width: 10px; height: 10px; }
	:global(::-webkit-scrollbar-track) { background: transparent; }
	:global(::-webkit-scrollbar-thumb) { background: var(--border-strong); border-radius: 999px; }
	:global(::-webkit-scrollbar-thumb:hover) { background: var(--accent-2); }

	.app-layout {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	.main-content {
		flex: 1;
		padding: 24px;
		max-width: 1400px;
		width: 100%;
		margin: 0 auto;
	}

	.main-content.home-page {
		padding: 0;
		max-width: 100%;
	}

	/* Ajuster le layout avec la sidebar sur desktop */
	@media (min-width: 1024px) {
		.app-layout {
			flex-direction: row;
		}

		.main-content {
			margin-left: 280px;
			padding: 32px;
		}

		.main-content.home-page {
			margin-left: 280px;
			padding: 0;
		}
	}

	/* Responsive */
	@media (max-width: 768px) {
		.main-content {
			padding: 16px;
		}

		.main-content.home-page {
			padding: 0;
		}
	}

	/* ============================================================
	   Composants globaux réutilisables
	   ============================================================ */
	:global(.page-header) {
		margin-bottom: 32px;
	}

	:global(.page-title) {
		font-size: 32px;
		font-weight: 800;
		color: var(--text);
		margin: 0 0 8px 0;
		display: flex;
		align-items: center;
		gap: 12px;
		letter-spacing: -0.02em;
	}

	:global(.page-description) {
		font-size: 16px;
		color: var(--text-muted);
		margin: 0;
	}

	:global(.page-actions) {
		display: flex;
		gap: 12px;
		margin-top: 16px;
		flex-wrap: wrap;
	}

	:global(.btn) {
		display: inline-flex;
		align-items: center;
		gap: 8px;
		padding: 10px 20px;
		border-radius: var(--radius-sm);
		font-weight: 600;
		text-decoration: none;
		transition: transform 0.2s, box-shadow 0.2s, background 0.2s, border-color 0.2s;
		border: 1px solid transparent;
		cursor: pointer;
		font-size: 14px;
	}

	:global(.btn-primary) {
		background: var(--accent-grad);
		color: #fff;
		box-shadow: 0 8px 24px rgba(34, 211, 238, 0.22);
	}

	:global(.btn-primary:hover) {
		transform: translateY(-2px);
		box-shadow: 0 12px 30px rgba(34, 211, 238, 0.4);
	}

	:global(.btn-secondary) {
		background: var(--surface-2);
		color: var(--text);
		border: 1px solid var(--border-strong);
		backdrop-filter: blur(10px);
	}

	:global(.btn-secondary:hover) {
		border-color: var(--accent);
		color: var(--accent);
	}

	:global(.btn-success) {
		background: rgba(52, 211, 153, 0.15);
		color: var(--success);
		border: 1px solid rgba(52, 211, 153, 0.35);
	}

	:global(.btn-success:hover) {
		background: rgba(52, 211, 153, 0.25);
	}

	:global(.btn-danger) {
		background: rgba(248, 113, 113, 0.15);
		color: var(--danger);
		border: 1px solid rgba(248, 113, 113, 0.35);
	}

	:global(.btn-danger:hover) {
		background: rgba(248, 113, 113, 0.25);
	}

	:global(.card) {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 24px;
		box-shadow: var(--shadow-sm);
		margin-bottom: 24px;
		backdrop-filter: blur(12px);
	}

	:global(.card-header) {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--border);
	}

	:global(.card-title) {
		font-size: 20px;
		font-weight: 700;
		color: var(--text);
		margin: 0;
		display: flex;
		align-items: center;
		gap: 8px;
	}

	:global(.grid) {
		display: grid;
		gap: 24px;
	}

	:global(.grid-2) {
		grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
	}

	:global(.grid-3) {
		grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
	}

	:global(.grid-4) {
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
	}

	@media (max-width: 768px) {
		:global(.page-title) {
			font-size: 24px;
		}

		:global(.grid-2),
		:global(.grid-3),
		:global(.grid-4) {
			grid-template-columns: 1fr;
		}
	}
</style>
