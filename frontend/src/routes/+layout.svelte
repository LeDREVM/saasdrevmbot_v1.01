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
	:global(body) {
		margin: 0;
		padding: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
		background: #f9fafb;
		color: #1f2937;
	}
	
	:global(*) {
		box-sizing: border-box;
	}
	
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
	
	/* Styles globaux pour les pages */
	:global(.page-header) {
		margin-bottom: 32px;
	}
	
	:global(.page-title) {
		font-size: 32px;
		font-weight: 700;
		color: #1f2937;
		margin: 0 0 8px 0;
		display: flex;
		align-items: center;
		gap: 12px;
	}
	
	:global(.page-description) {
		font-size: 16px;
		color: #6b7280;
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
		border-radius: 8px;
		font-weight: 600;
		text-decoration: none;
		transition: all 0.2s;
		border: none;
		cursor: pointer;
		font-size: 14px;
	}
	
	:global(.btn-primary) {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}
	
	:global(.btn-primary:hover) {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
	}
	
	:global(.btn-secondary) {
		background: white;
		color: #667eea;
		border: 2px solid #667eea;
	}
	
	:global(.btn-secondary:hover) {
		background: #667eea;
		color: white;
	}
	
	:global(.btn-success) {
		background: #10b981;
		color: white;
	}
	
	:global(.btn-success:hover) {
		background: #059669;
	}
	
	:global(.btn-danger) {
		background: #ef4444;
		color: white;
	}
	
	:global(.btn-danger:hover) {
		background: #dc2626;
	}
	
	:global(.card) {
		background: white;
		border-radius: 12px;
		padding: 24px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
		margin-bottom: 24px;
	}
	
	:global(.card-header) {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 2px solid #f0f0f0;
	}
	
	:global(.card-title) {
		font-size: 20px;
		font-weight: 700;
		color: #1f2937;
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
