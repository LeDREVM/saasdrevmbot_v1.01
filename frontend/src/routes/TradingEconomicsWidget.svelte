<script>
	import { onMount } from 'svelte';
	import { API_ENDPOINTS } from '$lib/config';

	let events = [];
	let stats = null;
	let loading = true;
	let error = null;
	let selectedImpact = 'all';
	let selectedCurrency = 'all';
	let autoRefresh = true;
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
			error = err.message;
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

	function getImpactColor(impact) {
		switch(impact) {
			case 'high': return '#ef4444';
			case 'medium': return '#f59e0b';
			case 'low': return '#10b981';
			default: return '#6b7280';
		}
	}

	function getImpactEmoji(impact) {
		switch(impact) {
			case 'high': return '🔴';
			case 'medium': return '🟡';
			case 'low': return '🟢';
			default: return '⚪';
		}
	}

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

		return () => {
			if (refreshInterval) {
				clearInterval(refreshInterval);
			}
		};
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
		background: white;
		border-radius: 12px;
		padding: 24px;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.widget-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 20px;
		padding-bottom: 16px;
		border-bottom: 2px solid #f0f0f0;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.widget-header h2 {
		margin: 0;
		font-size: 24px;
		color: #1f2937;
	}

	.source {
		background: #e0e7ff;
		color: #4f46e5;
		padding: 4px 12px;
		border-radius: 12px;
		font-size: 12px;
		font-weight: 600;
	}

	.refresh-btn {
		background: #4f46e5;
		color: white;
		border: none;
		padding: 8px 16px;
		border-radius: 8px;
		cursor: pointer;
		font-size: 14px;
		transition: all 0.2s;
	}

	.refresh-btn:hover:not(:disabled) {
		background: #4338ca;
		transform: translateY(-1px);
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
		background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
		padding: 16px;
		border-radius: 12px;
		text-align: center;
		color: white;
	}

	.stat-card.high {
		background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
	}

	.stat-card.medium {
		background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
	}

	.stat-card.low {
		background: linear-gradient(135deg, #10b981 0%, #059669 100%);
	}

	.stat-value {
		font-size: 28px;
		font-weight: bold;
		margin-bottom: 4px;
	}

	.stat-label {
		font-size: 12px;
		opacity: 0.9;
	}

	.filters {
		display: flex;
		gap: 16px;
		align-items: center;
		margin-bottom: 20px;
		padding: 16px;
		background: #f9fafb;
		border-radius: 8px;
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
		color: #374151;
	}

	.filter-group select {
		padding: 6px 12px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 14px;
		background: white;
		cursor: pointer;
	}

	.results-count {
		margin-left: auto;
		font-size: 14px;
		color: #6b7280;
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
		background: white;
		border: 1px solid #e5e7eb;
		border-left: 4px solid;
		border-radius: 8px;
		padding: 16px;
		transition: all 0.2s;
	}

	.event-card:hover {
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
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
		color: #1f2937;
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
		background: #dbeafe;
		color: #1e40af;
		padding: 4px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 700;
	}

	.country {
		color: #6b7280;
		font-size: 12px;
	}

	.event-name {
		font-size: 16px;
		font-weight: 600;
		color: #111827;
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
		color: #6b7280;
	}

	.data-item .value {
		font-weight: 600;
		color: #111827;
	}

	.data-item .value.actual {
		color: #059669;
	}

	.loading, .error, .no-events {
		text-align: center;
		padding: 40px;
		color: #6b7280;
	}

	.spinner {
		width: 40px;
		height: 40px;
		border: 4px solid #f3f4f6;
		border-top-color: #4f46e5;
		border-radius: 50%;
		animation: spin 1s linear infinite;
		margin: 0 auto 16px;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.error button {
		margin-top: 16px;
		background: #ef4444;
		color: white;
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
