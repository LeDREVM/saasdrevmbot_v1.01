<script>
	import HyperliquidChart from '$lib/components/HyperliquidChart.svelte';
</script>

<svelte:head>
	<title>Marchés — saasDrevmBot</title>
</svelte:head>

<div class="page-header">
	<h1 class="page-title">📈 Marchés</h1>
	<p class="page-description">
		Flux de bougies temps réel relayé par le backend — une seule connexion amont partagée par tous
		les clients du dashboard.
	</p>
</div>

<HyperliquidChart />

<style>
	.page-header {
		margin-bottom: 24px;
	}

	.page-title {
		margin: 0 0 8px;
		font-size: 30px;
		font-weight: 800;
		letter-spacing: -0.02em;
		color: var(--text);
	}

	.page-description {
		margin: 0;
		max-width: 70ch;
		font-size: 15px;
		line-height: 1.6;
		color: var(--text-muted);
	}
</style>
