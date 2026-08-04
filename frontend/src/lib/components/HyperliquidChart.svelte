<script>
	import { onMount, onDestroy } from 'svelte';
	import { createChart, CandlestickSeries, ColorType } from 'lightweight-charts';
	import { connectMarketFeed, fetchCandles } from '$lib/services/marketFeed.js';

	/** Actifs suivis par le backend (voir COINS dans hyperliquid_feed.py). */
	const coins = [
		{ id: 'BTC', label: 'Bitcoin' },
		{ id: 'ETH', label: 'Ethereum' },
		{ id: 'SOL', label: 'Solana' }
	];

	let selected = 'BTC';
	let connected = false;
	let loading = true;
	let error = '';
	/** @type {any} */
	let lastCandle = null;

	/** @type {HTMLDivElement} */
	let container;
	/** @type {any} */
	let chart;
	/** @type {any} */
	let series;
	/** @type {ResizeObserver | undefined} */
	let observer;
	/** @type {(() => void) | undefined} */
	let disconnect;

	// Jeton anti-course : si l'utilisateur change d'actif pendant le chargement de
	// l'historique, la réponse tardive de l'ancien actif ne doit pas écraser le chart.
	let loadToken = 0;

	const palette = {
		up: '#34d399', // --success
		down: '#f87171', // --danger
		text: '#9aa7bd', // --text-muted
		grid: 'rgba(148, 163, 184, 0.12)' // --border
	};

	function buildChart() {
		chart = createChart(container, {
			layout: {
				background: { type: ColorType.Solid, color: 'transparent' },
				textColor: palette.text,
				fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
			},
			grid: {
				vertLines: { color: palette.grid },
				horzLines: { color: palette.grid }
			},
			rightPriceScale: { borderColor: palette.grid },
			timeScale: { borderColor: palette.grid, timeVisible: true, secondsVisible: false },
			crosshair: { mode: 0 },
			autoSize: false,
			height: 480
		});

		series = chart.addSeries(CandlestickSeries, {
			upColor: palette.up,
			downColor: palette.down,
			borderUpColor: palette.up,
			borderDownColor: palette.down,
			wickUpColor: palette.up,
			wickDownColor: palette.down
		});

		observer = new ResizeObserver(() => {
			chart?.applyOptions({ width: container.clientWidth });
		});
		observer.observe(container);
		chart.applyOptions({ width: container.clientWidth });
	}

	/** @param {string} coin */
	async function loadHistory(coin) {
		const token = ++loadToken;
		loading = true;
		error = '';
		try {
			const candles = await fetchCandles(coin);
			if (token !== loadToken) return; // l'utilisateur a changé d'actif entre-temps
			series.setData(
				candles.map((c) => ({
					time: c.time,
					open: c.open,
					high: c.high,
					low: c.low,
					close: c.close
				}))
			);
			lastCandle = candles.at(-1) || null;
			chart.timeScale().fitContent();
		} catch (e) {
			if (token !== loadToken) return;
			error = "Historique indisponible. Le backend FastAPI est-il démarré ?";
			console.error(e);
		} finally {
			if (token === loadToken) loading = false;
		}
	}

	/** @param {any} candle */
	function onCandle(candle) {
		if (candle.coin !== selected || !series) return;
		series.update({
			time: candle.time,
			open: candle.open,
			high: candle.high,
			low: candle.low,
			close: candle.close
		});
		lastCandle = candle;
	}

	/** @param {string} coin */
	function selectCoin(coin) {
		if (coin === selected) return;
		selected = coin;
		lastCandle = null;
		loadHistory(coin);
	}

	onMount(async () => {
		buildChart();
		await loadHistory(selected);
		disconnect = connectMarketFeed({
			onCandle,
			onStatus: (open) => (connected = open)
		});
	});

	onDestroy(() => {
		disconnect?.();
		observer?.disconnect();
		chart?.remove();
	});

	$: currentLabel = coins.find((c) => c.id === selected)?.label ?? selected;
	$: priceLabel = lastCandle ? lastCandle.close.toLocaleString('fr-FR') : '—';
	$: direction = lastCandle ? (lastCandle.close >= lastCandle.open ? 'up' : 'down') : 'flat';
</script>

<section class="hl-panel">
	<header class="hl-header">
		<div class="hl-title-block">
			<h2>Marché crypto temps réel</h2>
			<p>Hyperliquid — bougies 5 minutes, relayées par le backend FastAPI.</p>
		</div>

		<div class="hl-status" role="status">
			<span class="hl-dot" class:online={connected} aria-hidden="true"></span>
			<span>{connected ? 'Flux connecté' : 'Flux interrompu'}</span>
		</div>
	</header>

	<div class="hl-toolbar">
		<div class="hl-tabs" role="group" aria-label="Sélection de l'actif">
			{#each coins as coin}
				<button
					type="button"
					class="hl-tab"
					class:active={coin.id === selected}
					aria-pressed={coin.id === selected}
					on:click={() => selectCoin(coin.id)}
				>
					{coin.label}
				</button>
			{/each}
		</div>

		<p class="hl-price" class:up={direction === 'up'} class:down={direction === 'down'}>
			<span class="hl-price-label">{selected}</span>
			<span class="hl-price-value">{priceLabel}</span>
		</p>
	</div>

	<div class="hl-chart-wrapper">
		<div
			class="hl-chart"
			bind:this={container}
			role="img"
			aria-label={`Graphique en chandeliers ${currentLabel}, unité de temps 5 minutes`}
		></div>

		{#if loading}
			<p class="hl-overlay">Chargement de l'historique {currentLabel}…</p>
		{:else if error}
			<p class="hl-overlay hl-error" role="alert">{error}</p>
		{/if}
	</div>

	<p class="hl-note">
		Données de marché publiques, en lecture seule — aucun ordre n'est transmis depuis cette page.
	</p>
</section>

<style>
	.hl-panel {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 24px;
		box-shadow: var(--shadow-sm);
	}

	.hl-header {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		align-items: flex-start;
		justify-content: space-between;
		margin-bottom: 20px;
	}

	.hl-title-block h2 {
		margin: 0 0 4px;
		font-size: 22px;
		font-weight: 700;
		color: var(--text);
	}

	.hl-title-block p {
		margin: 0;
		font-size: 14px;
		color: var(--text-muted);
	}

	.hl-status {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 13px;
		color: var(--text-muted);
		background: var(--surface-2);
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 8px 14px;
	}

	.hl-dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: var(--text-dim);
	}

	.hl-dot.online {
		background: var(--success);
	}

	.hl-toolbar {
		display: flex;
		flex-wrap: wrap;
		gap: 16px;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 16px;
	}

	.hl-tabs {
		display: flex;
		gap: 8px;
		flex-wrap: wrap;
	}

	.hl-tab {
		min-height: 44px;
		padding: 10px 20px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--surface-2);
		color: var(--text-muted);
		font-family: inherit;
		font-size: 15px;
		font-weight: 600;
		cursor: pointer;
		transition: color 0.2s, border-color 0.2s;
	}

	.hl-tab:hover {
		color: var(--text);
		border-color: var(--border-strong);
	}

	.hl-tab:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	.hl-tab.active {
		background: var(--surface-solid-2);
		border-color: var(--accent);
		color: var(--text);
	}

	.hl-price {
		display: flex;
		align-items: baseline;
		gap: 10px;
		margin: 0;
		font-family: var(--font-mono);
	}

	.hl-price-label {
		font-size: 13px;
		color: var(--text-muted);
	}

	.hl-price-value {
		font-size: 26px;
		font-weight: 700;
		color: var(--text);
	}

	.hl-price.up .hl-price-value {
		color: var(--success);
	}

	.hl-price.down .hl-price-value {
		color: var(--danger);
	}

	.hl-chart-wrapper {
		position: relative;
		min-height: 480px;
	}

	.hl-chart {
		width: 100%;
	}

	.hl-overlay {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		margin: 0;
		background: var(--surface-solid);
		border-radius: var(--radius-sm);
		color: var(--text-muted);
		font-size: 15px;
		text-align: center;
		padding: 24px;
	}

	.hl-overlay.hl-error {
		color: var(--danger);
	}

	.hl-note {
		margin: 16px 0 0;
		font-size: 13px;
		color: var(--text-dim);
	}

	@media (max-width: 600px) {
		.hl-panel {
			padding: 16px;
		}

		.hl-price-value {
			font-size: 22px;
		}
	}
</style>
