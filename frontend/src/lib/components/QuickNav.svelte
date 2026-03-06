<script>
	export let currentPage = '';
	
	const pages = [
		{ path: '/', icon: '🏠', label: 'Accueil', color: '#667eea' },
		{ path: '/calendar', icon: '📅', label: 'Calendrier', color: '#4facfe' },
		{ path: '/alerts', icon: '🔔', label: 'Alertes', color: '#f093fb' },
		{ path: '/stats', icon: '📊', label: 'Stats', color: '#43e97b' }
	];
	
	function isActive(path) {
		if (path === '/') {
			return currentPage === '/';
		}
		return currentPage.startsWith(path);
	}
</script>

<div class="quick-nav">
	{#each pages as page}
		<a 
			href={page.path} 
			class="quick-nav-btn"
			class:active={isActive(page.path)}
			style="--btn-color: {page.color}"
		>
			<span class="btn-icon">{page.icon}</span>
			<span class="btn-label">{page.label}</span>
		</a>
	{/each}
</div>

<style>
	.quick-nav {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
		margin-bottom: 24px;
	}
	
	.quick-nav-btn {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 12px 20px;
		background: white;
		border: 2px solid #e5e7eb;
		border-radius: 12px;
		text-decoration: none;
		color: #6b7280;
		font-weight: 600;
		transition: all 0.2s;
		cursor: pointer;
	}
	
	.quick-nav-btn:hover {
		border-color: var(--btn-color);
		color: var(--btn-color);
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}
	
	.quick-nav-btn.active {
		background: var(--btn-color);
		border-color: var(--btn-color);
		color: white;
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
	}
	
	.btn-icon {
		font-size: 20px;
	}
	
	.btn-label {
		font-size: 14px;
	}
	
	@media (max-width: 768px) {
		.quick-nav {
			gap: 8px;
		}
		
		.quick-nav-btn {
			padding: 10px 16px;
			flex: 1;
			min-width: calc(50% - 4px);
			justify-content: center;
		}
		
		.btn-label {
			font-size: 13px;
		}
	}
</style>
