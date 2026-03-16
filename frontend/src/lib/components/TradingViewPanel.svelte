<script>
  const symbols = [
    { id: 'EURUSD', label: 'EUR/USD',        tvSymbol: 'FX:EURUSD' },
    { id: 'XAUUSD', label: 'Gold',           tvSymbol: 'TVC:GOLD' },
    { id: 'GBPUSD', label: 'GBP/USD',        tvSymbol: 'FX:GBPUSD' },
    { id: 'USDJPY', label: 'USD/JPY',        tvSymbol: 'FX:USDJPY' },
    { id: 'US30',   label: 'US30',           tvSymbol: 'DJ:DJI' },
    { id: 'SPX',    label: 'S&P 500',        tvSymbol: 'SP:SPX' },
    { id: 'WTI',    label: 'WTI',            tvSymbol: 'TVC:USOIL' },
    { id: 'BTCUSD', label: 'Bitcoin',        tvSymbol: 'BITSTAMP:BTCUSD' },
  ];

  let selected = symbols[0];
  let loading = true;

  $: iframeSrc =
    `https://www.tradingview.com/widgetembed/?frameElementId=tv_${selected.id}` +
    `&symbol=${encodeURIComponent(selected.tvSymbol)}` +
    `&interval=60` +
    `&hidesidetoolbar=0` +
    `&hidetoptoolbar=0` +
    `&saveimage=0` +
    `&toolbarbg=131722` +
    `&theme=dark` +
    `&style=1` +
    `&timezone=Europe%2FParis` +
    `&locale=fr` +
    `&hideideas=1` +
    `&studies=%5B%5D` +
    `&utm_source=localhost`;

  function selectSymbol(sym) {
    loading = true;
    selected = sym;
  }
</script>

<div class="tv-panel">
  <div class="tv-header">
    <div class="tv-title-block">
      <h2>📈 Vue Marché Temps Réel</h2>
      <p>Graphique TradingView interactif — outils de dessin & multi-timeframe disponibles.</p>
    </div>
    <div class="tv-tabs" aria-label="Sélection de l'actif">
      {#each symbols as sym}
        <button
          type="button"
          class="tv-tab"
          class:active={sym.id === selected.id}
          on:click={() => selectSymbol(sym)}
        >
          {sym.label}
        </button>
      {/each}
    </div>
  </div>

  <div class="tv-frame-wrapper">
    {#if loading}
      <div class="tv-loader" aria-label="Chargement du graphique">
        <div class="tv-spinner"></div>
        <span>{selected.label}</span>
      </div>
    {/if}
    <iframe
      id="tv_{selected.id}"
      title={`TradingView — ${selected.label}`}
      src={iframeSrc}
      frameborder="0"
      scrolling="no"
      allow="fullscreen"
      allowfullscreen
      class:hidden={loading}
      on:load={() => (loading = false)}
    ></iframe>
  </div>
</div>

<style>
  .tv-panel {
    background: #020617;
    border-radius: 20px;
    padding: 1.5rem;
    box-shadow: 0 16px 40px rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(148, 163, 184, 0.3);
    color: #e5e7eb;
  }

  .tv-header {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    flex-wrap: wrap;
    margin-bottom: 1rem;
    align-items: flex-end;
  }

  .tv-title-block h2 {
    margin: 0 0 0.25rem;
    font-size: 1.25rem;
  }

  .tv-title-block p {
    margin: 0;
    font-size: 0.85rem;
    color: #9ca3af;
  }

  .tv-tabs {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .tv-tab {
    border-radius: 999px;
    border: 1px solid rgba(148, 163, 184, 0.5);
    padding: 0.35rem 0.9rem;
    font-size: 0.8rem;
    background: transparent;
    color: #e5e7eb;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }

  .tv-tab:hover {
    border-color: #38bdf8;
    background: rgba(15, 23, 42, 0.9);
  }

  .tv-tab.active {
    background: linear-gradient(135deg, #0ea5e9, #6366f1);
    border-color: transparent;
    color: white;
    box-shadow: 0 0 0 1px rgba(15, 23, 42, 0.8);
  }

  .tv-frame-wrapper {
    margin-top: 0.75rem;
    border-radius: 16px;
    overflow: hidden;
    border: 1px solid rgba(15, 23, 42, 0.9);
    background: #020617;
    min-height: 460px;
    position: relative;
  }

  .tv-loader {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: #020617;
    color: #9ca3af;
    font-size: 0.9rem;
    z-index: 1;
  }

  .tv-spinner {
    width: 32px;
    height: 32px;
    border: 3px solid rgba(148, 163, 184, 0.2);
    border-top-color: #38bdf8;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .tv-frame-wrapper iframe {
    width: 100%;
    height: 460px;
    display: block;
  }

  .tv-frame-wrapper iframe.hidden {
    opacity: 0;
    pointer-events: none;
  }

  @media (max-width: 768px) {
    .tv-panel {
      padding: 1rem;
    }

    .tv-frame-wrapper {
      min-height: 380px;
    }

    .tv-frame-wrapper iframe {
      height: 380px;
    }
  }
</style>
