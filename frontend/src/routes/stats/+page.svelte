<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import ImpactChart      from './ImpactChart.svelte';
  import HeatmapView      from './HeatmapView.svelte';
  import CorrelationTable from './CorrelationTable.svelte';
  import PriceTimeline    from './PriceTimeline.svelte';
  import QuickNav         from '$lib/components/QuickNav.svelte';

  $: currentPath = $page.url.pathname;

  // ── State ────────────────────────────────────────────────────────────────────
  let selectedSymbol = 'DJI';
  let daysBack       = 30;
  let stats          = null;
  let loading        = true;
  let error          = null;

  // ── Symboles disponibles (GoldyXbOT Express → yahoo-finance2) ────────────────
  const symbols = [
    { value: 'DJI',    label: 'US30 / DJIA 🇺🇸' },
    { value: 'SPX',    label: 'S&P 500 📈' },
    { value: 'EURUSD', label: 'EUR/USD 💶' },
    { value: 'GBPUSD', label: 'GBP/USD 💷' },
    { value: 'USDJPY', label: 'USD/JPY 💴' },
    { value: 'AUDUSD', label: 'AUD/USD 🦘' },
    { value: 'XAUUSD', label: 'Gold 🥇' },
  ];

  // ── API base URL : Express :3000 (via proxy Vite en dev, ou relatif en prod) ──
  // En dev → '/api/...' passe par le proxy Vite (→ http://localhost:3000)
  // En prod Netlify → variable VITE_API_URL pointe vers le backend déployé
  const API_BASE = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL)
    ? import.meta.env.VITE_API_URL
    : '';

  // ── Fetch principal ───────────────────────────────────────────────────────────
  async function fetchStats(force = false) {
    loading = true;
    error   = null;
    try {
      const url = `${API_BASE}/api/stats/correlations?symbol=${selectedSymbol}&days=${daysBack}${force ? '&force=true' : ''}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      stats = await res.json();
    } catch (err) {
      console.error('[Stats] Erreur fetch:', err.message);
      error = err.message;
      stats = null;
    } finally {
      loading = false;
    }
  }

  async function refreshStats() {
    await fetchStats(true); // force=true contourne le cache 30min
  }

  onMount(() => fetchStats());

  // ── KPIs réactifs ─────────────────────────────────────────────────────────────
  $: impactRate  = stats?.summary?.impact_rate        ?? 0;
  $: avgMovement = stats?.summary?.avg_movement_pips  ?? 0;
  $: totalEvents = stats?.summary?.total_events       ?? 0;
  $: volIncrease = stats?.summary?.volatility_increase ?? 0;
  $: hasData     = stats && (stats.events_analyzed ?? 0) > 0;
</script>

<svelte:head>
  <title>Corrélations — GoldyXbOT</title>
</svelte:head>

<QuickNav currentPath={currentPath} />

<div class="dashboard-container">

  <!-- ── Header ─────────────────────────────────────────────────────────────── -->
  <header class="page-header">
    <div class="page-header-text">
      <h1 class="page-title">📊 Dashboard Corrélation News/Prix</h1>
      <p class="page-description">
        Analyse l'impact réel des événements économiques sur tes actifs
        <span class="data-source">· Source : GoldyXbOT + Yahoo Finance</span>
      </p>
    </div>

    <div class="controls">
      <select bind:value={selectedSymbol} on:change={() => fetchStats()} class="symbol-select">
        {#each symbols as sym}
          <option value={sym.value}>{sym.label}</option>
        {/each}
      </select>

      <select bind:value={daysBack} on:change={() => fetchStats()} class="period-select">
        <option value={7}>7 jours</option>
        <option value={30}>30 jours</option>
        <option value={60}>60 jours</option>
        <option value={90}>90 jours</option>
      </select>

      <button on:click={refreshStats} class="refresh-btn" disabled={loading}>
        {loading ? '⏳' : '🔄'} Actualiser
      </button>
    </div>
  </header>

  <!-- ── Loading ────────────────────────────────────────────────────────────── -->
  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Analyse des {daysBack} derniers jours pour <strong>{selectedSymbol}</strong>…</p>
      <p class="loading-sub">Récupération des données Yahoo Finance en cours</p>
    </div>

  <!-- ── Erreur réseau ──────────────────────────────────────────────────────── -->
  {:else if error}
    <div class="error-state">
      <span class="state-emoji">❌</span>
      <h3>Impossible de contacter GoldyXbOT</h3>
      <p>Vérifiez que le serveur tourne sur le port 3000.</p>
      <p class="error-detail">{error}</p>
      <button on:click={() => fetchStats()} class="retry-btn">Réessayer</button>
    </div>

  <!-- ── Pas encore de données (premier démarrage) ──────────────────────────── -->
  {:else if !hasData}
    <div class="no-data-state">
      <span class="state-emoji">⏳</span>
      <h3>Données en cours d'accumulation</h3>
      <p>{stats?.message ?? "Le moteur enregistre les événements automatiquement à chaque scan."}</p>
      <div class="no-data-tips">
        <div class="tip">
          <span>1️⃣</span>
          <span>Laisse GoldyXbOT tourner quelques heures pour accumuler des événements</span>
        </div>
        <div class="tip">
          <span>2️⃣</span>
          <span>Les données sont enregistrées dans <code>data/events_log.json</code></span>
        </div>
        <div class="tip">
          <span>3️⃣</span>
          <span>La corrélation avec Yahoo Finance se calcule automatiquement</span>
        </div>
      </div>
      <button on:click={refreshStats} class="retry-btn">🔄 Vérifier maintenant</button>
    </div>

  <!-- ── Dashboard complet ──────────────────────────────────────────────────── -->
  {:else}
    <!-- Méta info -->
    <div class="meta-bar">
      <span>📅 Période : {daysBack} jours</span>
      <span>🔍 {stats.events_analyzed} événements analysés</span>
      <span>🕐 Généré : {new Date(stats.generated_at).toLocaleTimeString('fr-FR')}</span>
    </div>

    <!-- KPI Cards -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">📊</div>
        <div class="kpi-content">
          <span class="kpi-value">{totalEvents}</span>
          <span class="kpi-label">Événements analysés</span>
        </div>
      </div>

      <div class="kpi-card highlight">
        <div class="kpi-icon">🎯</div>
        <div class="kpi-content">
          <span class="kpi-value">{impactRate}%</span>
          <span class="kpi-label">Taux d'impact réel</span>
        </div>
      </div>

      <div class="kpi-card">
        <div class="kpi-icon">📏</div>
        <div class="kpi-content">
          <span class="kpi-value">{avgMovement}</span>
          <span class="kpi-label">
            {selectedSymbol === 'DJI' || selectedSymbol === 'SPX' ? 'Points' : 'Pips'} moyens / event
          </span>
        </div>
      </div>

      <div class="kpi-card {volIncrease > 50 ? 'danger' : ''}">
        <div class="kpi-icon">⚡</div>
        <div class="kpi-content">
          <span class="kpi-value">+{volIncrease}%</span>
          <span class="kpi-label">Volatilité post-event</span>
        </div>
      </div>
    </div>

    <!-- Direction Stats -->
    <div class="direction-stats">
      <h3>📈 Direction des mouvements</h3>
      <div class="direction-bars">
        <div class="direction-bar">
          <span class="label">🟢 Haussier</span>
          <div class="bar-container">
            <div class="bar up"
              style="width: {totalEvents > 0 ? (stats.summary.direction_stats?.up / totalEvents * 100) : 0}%">
            </div>
            <span class="value">{stats.summary.direction_stats?.up ?? 0}</span>
          </div>
        </div>

        <div class="direction-bar">
          <span class="label">🔴 Baissier</span>
          <div class="bar-container">
            <div class="bar down"
              style="width: {totalEvents > 0 ? (stats.summary.direction_stats?.down / totalEvents * 100) : 0}%">
            </div>
            <span class="value">{stats.summary.direction_stats?.down ?? 0}</span>
          </div>
        </div>

        <div class="direction-bar">
          <span class="label">⚪ Neutre</span>
          <div class="bar-container">
            <div class="bar neutral"
              style="width: {totalEvents > 0 ? (stats.summary.direction_stats?.neutral / totalEvents * 100) : 0}%">
            </div>
            <span class="value">{stats.summary.direction_stats?.neutral ?? 0}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Main Charts -->
    <div class="charts-grid">
      <div class="chart-section">
        <h3>🚀 Top 10 événements à fort impact</h3>
        <ImpactChart events={stats.top_impact_events} />
      </div>

      <div class="chart-section">
        <h3>🌡️ Heatmap volatilité (Jour × Heure)</h3>
        <HeatmapView data={stats.heatmap_data} />
      </div>
    </div>

    <!-- Correlation Table -->
    <div class="table-section">
      <h3>📋 Événements par type (Top 10)</h3>
      <CorrelationTable data={stats.summary.by_event_type} />
    </div>

    <!-- Timeline -->
    <div class="timeline-section">
      <h3>⏱️ Timeline des événements</h3>
      <PriceTimeline data={stats.timeline} />
    </div>
  {/if}

</div>

<style>
  .dashboard-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    background: #f8fafc;
    min-height: 100vh;
  }

  /* ── Header ──────────────────────────────────────────────────────────────── */
  .page-header {
    background: white;
    padding: 1.5rem 2rem;
    border-radius: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1.5rem;
    flex-wrap: wrap;
  }

  .page-title {
    font-size: 1.75rem;
    color: #1e293b;
    margin: 0 0 0.25rem;
  }

  .page-description {
    color: #64748b;
    font-size: 0.9rem;
    margin: 0;
  }

  .data-source {
    color: #94a3b8;
    font-size: 0.8rem;
  }

  .controls {
    display: flex;
    gap: 0.75rem;
    align-items: center;
    flex-wrap: wrap;
  }

  select {
    padding: 0.6rem 0.9rem;
    border: 2px solid #e2e8f0;
    border-radius: 8px;
    font-size: 0.9rem;
    background: white;
    cursor: pointer;
    transition: border-color 0.2s;
    color: #1e293b;
  }

  select:hover { border-color: #3b82f6; }

  .refresh-btn {
    padding: 0.6rem 1.2rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .refresh-btn:hover:not(:disabled) { background: #2563eb; }
  .refresh-btn:disabled { opacity: 0.6; cursor: not-allowed; }

  /* ── Meta bar ────────────────────────────────────────────────────────────── */
  .meta-bar {
    display: flex;
    gap: 1.5rem;
    color: #64748b;
    font-size: 0.8rem;
    margin-bottom: 1.5rem;
    padding: 0 0.25rem;
    flex-wrap: wrap;
  }

  /* ── States ──────────────────────────────────────────────────────────────── */
  .loading-state,
  .error-state,
  .no-data-state {
    text-align: center;
    padding: 4rem 2rem;
  }

  .state-emoji {
    font-size: 4rem;
    display: block;
    margin-bottom: 1rem;
  }

  .loading-state p,
  .error-state p,
  .no-data-state p {
    color: #64748b;
    margin: 0.5rem 0;
  }

  .loading-sub { font-size: 0.85rem; color: #94a3b8; }
  .error-detail { font-size: 0.8rem; font-family: monospace; color: #ef4444; }

  .no-data-tips {
    display: inline-flex;
    flex-direction: column;
    gap: 0.75rem;
    text-align: left;
    margin: 1.5rem auto;
    max-width: 460px;
    background: #f1f5f9;
    padding: 1.25rem 1.5rem;
    border-radius: 12px;
  }

  .tip {
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
    font-size: 0.9rem;
    color: #475569;
  }

  .tip code {
    background: #e2e8f0;
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  .retry-btn {
    margin-top: 1rem;
    padding: 0.75rem 1.5rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .retry-btn:hover { background: #2563eb; }

  .spinner {
    width: 60px;
    height: 60px;
    border: 5px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1.5rem;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── KPI Cards ───────────────────────────────────────────────────────────── */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1.25rem;
    margin-bottom: 1.5rem;
  }

  .kpi-card {
    background: white;
    padding: 1.25rem 1.5rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: transform 0.2s;
  }

  .kpi-card:hover { transform: translateY(-2px); }

  .kpi-card.highlight {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: white;
  }

  .kpi-card.danger { border-left: 4px solid #ef4444; }

  .kpi-icon { font-size: 2.25rem; }

  .kpi-content {
    display: flex;
    flex-direction: column;
  }

  .kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    line-height: 1;
  }

  .kpi-label {
    font-size: 0.8rem;
    opacity: 0.75;
    margin-top: 0.2rem;
  }

  /* ── Direction Stats ─────────────────────────────────────────────────────── */
  .direction-stats {
    background: white;
    padding: 1.5rem 2rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 1.5rem;
  }

  .direction-stats h3 { margin: 0 0 1.25rem; color: #1e293b; }

  .direction-bars { display: flex; flex-direction: column; gap: 0.75rem; }

  .direction-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .direction-bar .label { width: 120px; font-weight: 600; font-size: 0.9rem; }

  .bar-container {
    flex: 1;
    height: 28px;
    background: #f1f5f9;
    border-radius: 6px;
    position: relative;
    overflow: hidden;
  }

  .bar { height: 100%; transition: width 0.6s ease; }
  .bar.up      { background: #10b981; }
  .bar.down    { background: #ef4444; }
  .bar.neutral { background: #94a3b8; }

  .bar-container .value {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-weight: 600;
    font-size: 0.85rem;
    color: #1e293b;
  }

  /* ── Charts Grid ─────────────────────────────────────────────────────────── */
  .charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(460px, 1fr));
    gap: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .chart-section,
  .table-section,
  .timeline-section {
    background: white;
    padding: 1.5rem 2rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }

  .chart-section h3,
  .table-section h3,
  .timeline-section h3 {
    margin: 0 0 1.25rem;
    color: #1e293b;
    font-size: 1rem;
  }

  .timeline-section { margin-bottom: 2rem; }

  /* ── Responsive ──────────────────────────────────────────────────────────── */
  @media (max-width: 768px) {
    .dashboard-container { padding: 1rem; }
    .page-header { flex-direction: column; }
    .charts-grid { grid-template-columns: 1fr; }
  }
</style>
