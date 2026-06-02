<script>
	import { onMount, onDestroy } from 'svelte';
	import { API_ENDPOINTS } from '$lib/config';

	/** @type {any[]} */
	let events = [];
	/** @type {any} */
	let stats = null;
	let loading = true;
	/** @type {any} */
	let error = null;
	let selectedImpact = 'all';
	let selectedCurrency = 'all';
	let autoRefresh = true;
	/** @type {any} */
	let refreshInterval = null;

	// Filtrer les événements
	$: filteredEvents = events.filter(event => {
		if (selectedImpact !== 'all' && event.impact !== selectedImpact) return false;
		if (selectedCurrency !== 'all' && event.currency !== selectedCurrency) return false;
		return true;
	});

	// Obtenir les devises uniques
	$: currencies = [...new Set(events.map(e => e.currency))].sort();

	async function fetchEvents() {
		try {
			loading = true;
			error = null;

			const response = await fetch(`${API_ENDPOINTS.calendar || 'http://localhost:8000/api'}/trading-economics/today`);
			
			if (!response.ok) {
				throw new Error(`Erreur HTTP: ${response.status}`);
			}

			const data = await response.json();
			
			if (data.success) {
				events = data.events || [];
			} else {
				throw new Error('Erreur lors de la récupération des données');
			}

		} catch (err) {
			console.error('Erreur:', err);
			error = err instanceof Error ? err.message : String(err);
		} finally {
			loading = false;
		}
	}

	async function fetchStats() {
		try {
			const response = await fetch(`${API_ENDPOINTS.calendar || 'http://localhost:8000/api'}/trading-economics/stats`);
			const data = await response.json();
			
			if (data.success) {
				stats = data;
			}
		} catch (err) {
			console.error('Erreur stats:', err);
		}
	}

	/** @param {any} impact */
	function getImpactColor(impact) {
		switch(impact) {
			case 'high': return '#ef4444';
			case 'medium': return '#f59e0b';
			case 'low': return '#10b981';
			default: return '#6b7280';
		}
	}

	/** @param {any} impact */
	function getImpactEmoji(impact) {
		switch(impact) {
			case 'high': return '🔴';
			case 'medium': return '🟡';
			case 'low': return '🟢';
			default: return '⚪';
		}
	}

	/** @param {any} timeStr */
	function formatTime(timeStr) {
		if (!timeStr) return 'N/A';
		return timeStr;
	}

	async function handleRefresh() {
		await fetchEvents();
		await fetchStats();
	}

	onMount(async () => {
		await fetchEvents();
		await fetchStats();

		// Auto-refresh toutes les 5 minutes
		if (autoRefresh) {
			refreshInterval = setInterval(async () => {
				await fetchEvents();
				await fetchStats();
			}, 5 * 60 * 1000);
		}
	});

	onDestroy(() => {
		if (refreshInterval) {
			clearInterval(refreshInterval);
		}
	});
</script>

<div class="trading-economics-widget">
	<div class="widget-header">
		<div class="header-left">
			<h2>📊 Calendrier Économique</h2>
			<span class="source">Trading Economics</span>
		</div>
		<button class="refresh-btn" on:click={handleRefresh} disabled={loading}>
			{loading ? '⏳' : '🔄'} Actualiser
		</button>
	</div>

	{#if stats}
		<div class="stats-summary">
			<div class="stat-card">
				<div class="stat-value">{stats.total_events}</div>
				<div class="stat-label">Événements</div>
			</div>
			<div class="stat-card high">
				<div class="stat-value">🔴 {stats.by_impact.high}</div>
				<div class="stat-label">Fort Impact</div>
			</div>
			<div class="stat-card medium">
				<div class="stat-value">🟡 {stats.by_impact.medium}</div>
				<div class="stat-label">Impact Moyen</div>
			</div>
			<div class="stat-card low">
				<div class="stat-value">🟢 {stats.by_impact.low}</div>
				<div class="stat-label">Faible Impact</div>
			</div>
		</div>
	{/if}

	<div class="filters">
		<div class="filter-group">
			<label for="impact-filter">Impact:</label>
			<select id="impact-filter" bind:value={selectedImpact}>
				<option value="all">Tous</option>
				<option value="high">🔴 Fort</option>
				<option value="medium">🟡 Moyen</option>
				<option value="low">🟢 Faible</option>
			</select>
		</div>

		<div class="filter-group">
			<label for="currency-filter">Devise:</label>
			<select id="currency-filter" bind:value={selectedCurrency}>
				<option value="all">Toutes</option>
				{#each currencies as currency}
					<option value={currency}>{currency}</option>
				{/each}
			</select>
		</div>

		<div class="results-count">
			{filteredEvents.length} événement{filteredEvents.length > 1 ? 's' : ''}
		</div>
	</div>

	{#if loading}
		<div class="loading">
			<div class="spinner"></div>
			<p>Chargement des événements...</p>
		</div>
	{:else if error}
		<div class="error">
			<p>❌ {error}</p>
			<button on:click={handleRefresh}>Réessayer</button>
		</div>
	{:else if filteredEvents.length === 0}
		<div class="no-events">
			<p>Aucun événement trouvé</p>
		</div>
	{:else}
		<div class="events-list">
			{#each filteredEvents as event}
				<div class="event-card" style="border-left-color: {getImpactColor(event.impact)}">
					<div class="event-time">
						<span class="time">{formatTime(event.time)}</span>
						<span class="impact-badge" style="background-color: {getImpactColor(event.impact)}">
							{getImpactEmoji(event.impact)} {event.impact}
						</span>
					</div>

					<div class="event-info">
						<div class="event-header">
							<span class="currency">{event.currency}</span>
							<span class="country">{event.country}</span>
						</div>
						<div class="event-name">{event.event}</div>
					</div>

					<div class="event-data">
						{#if event.forecast}
							<div class="data-item">
								<span class="label">Prévision:</span>
								<span class="value">{event.forecast}</span>
							</div>
						{/if}
						{#if event.previous}
							<div class="data-item">
								<span class="label">Précédent:</span>
								<span class="value">{event.previous}</span>
							</div>
						{/if}
						{#if event.actual}
							<div class="data-item">
								<span class="label">Actuel:</span>
								<span class="value actual">{event.actual}</span>
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.trading-economics-widget {
		background: var(--surface);
		border: 1px solid var(--border);
		backdrop-filter: blur(12px);
		border-radius: var(--radius);
		padding: 24px;
		box-shadow: var(--shadow-sm);
		color: var(--text);
	}

	.widget-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--border);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.widget-header h2 {
		margin: 0;
		font-size: 24px;
		color: var(--text);
	}

	.source {
		background: var(--accent-grad-soft);
		color: var(--accent);
		padding: 4px 12px;
		border-radius: 12px;
		font-size: 12px;
		font-weight: 600;
		box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
	}

	.refresh-btn {
		background: var(--accent-grad);
		color: #fff;
		border: none;
		padding: 8px 16px;
		border-radius: var(--radius-sm);
		cursor: pointer;
		font-size: 14px;
		transition: all 0.2s;
	}

	.refresh-btn:hover:not(:disabled) {
		transform: translateY(-1px);
		box-shadow: var(--shadow-sm);
	}

	.refresh-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.stats-summary {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
		gap: 16px;
		margin-bottom: 24px;
	}

	.stat-card {
		background: var(--accent-grad-soft);
		border: 1px solid var(--border);
		box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.2);
		padding: 16px;
		border-radius: var(--radius);
		text-align: center;
		color: var(--text);
	}

	.stat-card.high {
		background: rgba(248, 113, 113, 0.12);
		box-shadow: inset 0 0 0 1px rgba(248, 113, 113, 0.3);
	}

	.stat-card.medium {
		background: rgba(251, 191, 36, 0.12);
		box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.3);
	}

	.stat-card.low {
		background: rgba(52, 211, 153, 0.12);
		box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.3);
	}

	.stat-value {
		font-size: 28px;
		font-weight: bold;
		margin-bottom: 4px;
		font-family: var(--font-mono);
	}

	.stat-label {
		font-size: 12px;
		color: var(--text-muted);
	}

	.filters {
		display: flex;
		gap: 16px;
		align-items: center;
		margin-bottom: 20px;
		padding: 16px;
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		flex-wrap: wrap;
	}

	.filter-group {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.filter-group label {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-muted);
	}

	.filter-group select {
		padding: 6px 12px;
		border: 1px solid var(--border);
		border-radius: 6px;
		font-size: 14px;
		background: var(--surface-solid-2);
		color: var(--text);
		cursor: pointer;
	}

	.filter-group select:focus {
		border-color: var(--accent);
		outline: none;
		box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.15);
	}

	.results-count {
		margin-left: auto;
		font-size: 14px;
		color: var(--text-muted);
		font-weight: 600;
	}

	.events-list {
		display: flex;
		flex-direction: column;
		gap: 12px;
		max-height: 600px;
		overflow-y: auto;
	}

	.event-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-left: 4px solid;
		border-radius: var(--radius-sm);
		padding: 16px;
		transition: all 0.2s;
	}

	.event-card:hover {
		box-shadow: var(--shadow-sm);
		border-color: var(--border-strong);
		transform: translateY(-2px);
	}

	.event-time {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 12px;
	}

	.time {
		font-size: 18px;
		font-weight: bold;
		color: var(--text);
		font-family: var(--font-mono);
	}

	.impact-badge {
		padding: 4px 12px;
		border-radius: 12px;
		font-size: 11px;
		font-weight: 600;
		color: white;
		text-transform: uppercase;
	}

	.event-info {
		margin-bottom: 12px;
	}

	.event-header {
		display: flex;
		gap: 12px;
		margin-bottom: 8px;
	}

	.currency {
		background: var(--accent-grad-soft);
		color: var(--accent);
		padding: 4px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 700;
		box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
	}

	.country {
		color: var(--text-muted);
		font-size: 12px;
	}

	.event-name {
		font-size: 16px;
		font-weight: 600;
		color: var(--text);
	}

	.event-data {
		display: flex;
		gap: 16px;
		flex-wrap: wrap;
	}

	.data-item {
		display: flex;
		gap: 6px;
		font-size: 14px;
	}

	.data-item .label {
		color: var(--text-muted);
	}

	.data-item .value {
		font-weight: 600;
		color: var(--text);
		font-family: var(--font-mono);
	}

	.data-item .value.actual {
		color: var(--success);
	}

	.loading, .error, .no-events {
		text-align: center;
		padding: 40px;
		color: var(--text-muted);
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 4px solid var(--surface-2);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 16px;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error button {
		margin-top: 16px;
		background: var(--danger);
		color: #fff;
		border: none;
		padding: 8px 16px;
		border-radius: 6px;
		cursor: pointer;
	}

	@media (max-width: 768px) {
		.trading-economics-widget {
			padding: 16px;
		}

		.stats-summary {
			grid-template-columns: repeat(2, 1fr);
		}

		.filters {
			flex-direction: column;
			align-items: stretch;
		}

		.results-count {
			margin-left: 0;
			text-align: center;
		}
	}
</style>
