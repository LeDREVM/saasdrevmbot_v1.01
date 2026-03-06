<script>
	import { page } from '$app/stores';
	
	let mobileMenuOpen = false;
	
	const navItems = [
		{ path: '/', icon: '🏠', label: 'Accueil', description: 'Dashboard principal' },
		{ path: '/calendar', icon: '📅', label: 'Calendrier', description: 'Événements économiques' },
		{ path: '/alerts', icon: '🔔', label: 'Alertes', description: 'Notifications et config' },
		{ path: '/stats', icon: '📊', label: 'Statistiques', description: 'Analyses et corrélations' }
	];
	
	$: currentPath = $page.url.pathname;
	
	function toggleMobileMenu() {
		mobileMenuOpen = !mobileMenuOpen;
	}
	
	function closeMobileMenu() {
		mobileMenuOpen = false;
	}
	
	function isActive(path) {
		if (path === '/') {
			return currentPath === '/';
		}
		return currentPath.startsWith(path);
	}
</script>

<!-- Navigation Desktop -->
<nav class="desktop-nav">
	<div class="nav-container">
		<div class="nav-brand">
			<a href="/">
				<span class="brand-icon">🤖</span>
				<span class="brand-name">DrevmBot</span>
			</a>
		</div>
		
		<div class="nav-links">
			{#each navItems as item}
				<a 
					href={item.path} 
					class="nav-link"
					class:active={isActive(item.path)}
					title={item.description}
				>
					<span class="nav-icon">{item.icon}</span>
					<span class="nav-label">{item.label}</span>
				</a>
			{/each}
		</div>
		
		<div class="nav-actions">
			<button class="btn-refresh" title="Actualiser les données">
				🔄
			</button>
			<div class="status-indicator" title="Système en ligne">
				<span class="status-dot"></span>
			</div>
		</div>
	</div>
</nav>

<!-- Navigation Mobile -->
<nav class="mobile-nav">
	<div class="mobile-header">
		<a href="/" class="mobile-brand">
			<span class="brand-icon">🤖</span>
			<span class="brand-name">DrevmBot</span>
		</a>
		
		<button 
			class="hamburger" 
			class:active={mobileMenuOpen}
			on:click={toggleMobileMenu}
			aria-label="Menu"
		>
			<span></span>
			<span></span>
			<span></span>
		</button>
	</div>
	
	{#if mobileMenuOpen}
		<div class="mobile-menu" on:click={closeMobileMenu}>
			<div class="mobile-menu-content" on:click|stopPropagation>
				{#each navItems as item}
					<a 
						href={item.path} 
						class="mobile-link"
						class:active={isActive(item.path)}
						on:click={closeMobileMenu}
					>
						<span class="mobile-icon">{item.icon}</span>
						<div class="mobile-text">
							<span class="mobile-label">{item.label}</span>
							<span class="mobile-description">{item.description}</span>
						</div>
					</a>
				{/each}
			</div>
		</div>
	{/if}
</nav>

<!-- Sidebar Navigation (pour desktop) -->
<aside class="sidebar">
	<div class="sidebar-header">
		<a href="/" class="sidebar-brand">
			<span class="brand-icon-large">🤖</span>
			<div class="brand-info">
				<span class="brand-name">DrevmBot</span>
				<span class="brand-tagline">Trading Assistant</span>
			</div>
		</a>
	</div>
	
	<div class="sidebar-nav">
		{#each navItems as item}
			<a 
				href={item.path} 
				class="sidebar-link"
				class:active={isActive(item.path)}
			>
				<span class="sidebar-icon">{item.icon}</span>
				<div class="sidebar-text">
					<span class="sidebar-label">{item.label}</span>
					<span class="sidebar-description">{item.description}</span>
				</div>
				{#if isActive(item.path)}
					<span class="active-indicator">●</span>
				{/if}
			</a>
		{/each}
	</div>
	
	<div class="sidebar-footer">
		<div class="status-card">
			<div class="status-header">
				<span class="status-icon">✅</span>
				<span class="status-text">Système en ligne</span>
			</div>
			<div class="status-details">
				<div class="status-item">
					<span>API</span>
					<span class="status-value online">●</span>
				</div>
				<div class="status-item">
					<span>Worker</span>
					<span class="status-value online">●</span>
				</div>
			</div>
		</div>
	</div>
</aside>

<style>
	/* Desktop Navigation (Top Bar) */
	.desktop-nav {
		display: none;
		background: white;
		border-bottom: 1px solid #e5e7eb;
		position: sticky;
		top: 0;
		z-index: 100;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}
	
	.nav-container {
		max-width: 1400px;
		margin: 0 auto;
		padding: 0 24px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 64px;
	}
	
	.nav-brand a {
		display: flex;
		align-items: center;
		gap: 12px;
		text-decoration: none;
		color: #1f2937;
		font-weight: 700;
		font-size: 20px;
	}
	
	.brand-icon {
		font-size: 28px;
	}
	
	.nav-links {
		display: flex;
		gap: 8px;
	}
	
	.nav-link {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 8px 16px;
		border-radius: 8px;
		text-decoration: none;
		color: #6b7280;
		font-weight: 500;
		transition: all 0.2s;
	}
	
	.nav-link:hover {
		background: #f3f4f6;
		color: #1f2937;
	}
	
	.nav-link.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}
	
	.nav-icon {
		font-size: 20px;
	}
	
	.nav-actions {
		display: flex;
		align-items: center;
		gap: 16px;
	}
	
	.btn-refresh {
		background: #f3f4f6;
		border: none;
		width: 40px;
		height: 40px;
		border-radius: 8px;
		cursor: pointer;
		font-size: 18px;
		transition: all 0.2s;
	}
	
	.btn-refresh:hover {
		background: #e5e7eb;
		transform: rotate(90deg);
	}
	
	.status-indicator {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	
	.status-dot {
		width: 8px;
		height: 8px;
		background: #10b981;
		border-radius: 50%;
		animation: pulse 2s infinite;
	}
	
	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}
	
	/* Mobile Navigation */
	.mobile-nav {
		display: block;
		background: white;
		border-bottom: 1px solid #e5e7eb;
		position: sticky;
		top: 0;
		z-index: 100;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
	}
	
	.mobile-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px;
		height: 64px;
	}
	
	.mobile-brand {
		display: flex;
		align-items: center;
		gap: 12px;
		text-decoration: none;
		color: #1f2937;
		font-weight: 700;
		font-size: 18px;
	}
	
	.hamburger {
		width: 40px;
		height: 40px;
		background: transparent;
		border: none;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		justify-content: center;
		align-items: center;
		gap: 6px;
		padding: 0;
	}
	
	.hamburger span {
		width: 24px;
		height: 2px;
		background: #1f2937;
		transition: all 0.3s;
		border-radius: 2px;
	}
	
	.hamburger.active span:nth-child(1) {
		transform: rotate(45deg) translate(7px, 7px);
	}
	
	.hamburger.active span:nth-child(2) {
		opacity: 0;
	}
	
	.hamburger.active span:nth-child(3) {
		transform: rotate(-45deg) translate(7px, -7px);
	}
	
	.mobile-menu {
		position: fixed;
		top: 64px;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		z-index: 99;
		animation: fadeIn 0.2s;
	}
	
	@keyframes fadeIn {
		from { opacity: 0; }
		to { opacity: 1; }
	}
	
	.mobile-menu-content {
		background: white;
		padding: 16px;
		animation: slideDown 0.3s;
	}
	
	@keyframes slideDown {
		from { transform: translateY(-20px); opacity: 0; }
		to { transform: translateY(0); opacity: 1; }
	}
	
	.mobile-link {
		display: flex;
		align-items: center;
		gap: 16px;
		padding: 16px;
		border-radius: 12px;
		text-decoration: none;
		color: #1f2937;
		margin-bottom: 8px;
		transition: all 0.2s;
	}
	
	.mobile-link:hover {
		background: #f3f4f6;
	}
	
	.mobile-link.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}
	
	.mobile-icon {
		font-size: 28px;
	}
	
	.mobile-text {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}
	
	.mobile-label {
		font-weight: 600;
		font-size: 16px;
	}
	
	.mobile-description {
		font-size: 13px;
		opacity: 0.8;
	}
	
	/* Sidebar Navigation */
	.sidebar {
		display: none;
		position: fixed;
		left: 0;
		top: 0;
		bottom: 0;
		width: 280px;
		background: white;
		border-right: 1px solid #e5e7eb;
		flex-direction: column;
		z-index: 50;
		overflow-y: auto;
	}
	
	.sidebar-header {
		padding: 24px;
		border-bottom: 1px solid #e5e7eb;
	}
	
	.sidebar-brand {
		display: flex;
		align-items: center;
		gap: 16px;
		text-decoration: none;
		color: #1f2937;
	}
	
	.brand-icon-large {
		font-size: 48px;
	}
	
	.brand-info {
		display: flex;
		flex-direction: column;
	}
	
	.brand-name {
		font-weight: 700;
		font-size: 20px;
	}
	
	.brand-tagline {
		font-size: 12px;
		color: #6b7280;
	}
	
	.sidebar-nav {
		flex: 1;
		padding: 16px;
	}
	
	.sidebar-link {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 16px;
		border-radius: 12px;
		text-decoration: none;
		color: #6b7280;
		margin-bottom: 8px;
		transition: all 0.2s;
		position: relative;
	}
	
	.sidebar-link:hover {
		background: #f3f4f6;
		color: #1f2937;
	}
	
	.sidebar-link.active {
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		color: white;
	}
	
	.sidebar-icon {
		font-size: 24px;
	}
	
	.sidebar-text {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
	}
	
	.sidebar-label {
		font-weight: 600;
		font-size: 15px;
	}
	
	.sidebar-description {
		font-size: 12px;
		opacity: 0.8;
	}
	
	.active-indicator {
		color: white;
		font-size: 8px;
	}
	
	.sidebar-footer {
		padding: 16px;
		border-top: 1px solid #e5e7eb;
	}
	
	.status-card {
		background: #f9fafb;
		border-radius: 12px;
		padding: 16px;
	}
	
	.status-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 12px;
		font-weight: 600;
		font-size: 14px;
	}
	
	.status-icon {
		font-size: 18px;
	}
	
	.status-details {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	
	.status-item {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 13px;
		color: #6b7280;
	}
	
	.status-value {
		font-size: 10px;
	}
	
	.status-value.online {
		color: #10b981;
	}
	
	/* Responsive */
	@media (min-width: 768px) {
		.mobile-nav {
			display: none;
		}
		
		.desktop-nav {
			display: block;
		}
	}
	
	@media (min-width: 1024px) {
		.desktop-nav {
			display: none;
		}
		
		.sidebar {
			display: flex;
		}
	}
</style>
