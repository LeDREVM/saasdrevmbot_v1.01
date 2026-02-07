<script>
    import { onMount } from 'svelte';
    import ImpactChart from './ImpactChart.svelte';
    import HeatmapView from './HeatmapView.svelte';
    import CorrelationTable from './CorrelationTable.svelte';
    import PriceTimeline from './PriceTimeline.svelte';
    
    let selectedSymbol = 'EURUSD';
    let daysBack = 30;
    let stats = null;
    let loading = true;

    const symbols = [
      { value: 'EURUSD', label: 'EUR/USD 💶' },
      { value: 'GBPUSD', label: 'GBP/USD 💷' },
      { value: 'USDJPY', label: 'USD/JPY 💴' },
      { value: 'AUDUSD', label: 'AUD/USD 🦘' },
      { value: 'XAUUSD', label: 'Gold 🥇' },
      { value: 'SPX', label: 'S&P 500 📈' },
    ];
    
    async function fetchStats() {
      loading = true;
      try {
        const response = await fetch(
          `http://localhost:8000/api/stats/dashboard/${selectedSymbol}?days_back=${daysBack}`
        );
        stats = await response.json();
      } catch (error) {
        console.error('Erreur fetch stats:', error);
      } finally {
        loading = false;
      }
    }
    
    async function refreshStats() {
      await fetch(`http://localhost:8000/api/stats/refresh/${selectedSymbol}`, {
        method: 'POST'
      });
      await fetchStats();
    }
    
    onMount(fetchStats);
    
    // KPI formattés
    $: impactRate = stats?.summary?.impact_rate || 0;
    $: avgMovement = stats?.summary?.avg_movement_pips || 0;
    $: totalEvents = stats?.summary?.total_events || 0;
    $: volIncrease = stats?.summary?.volatility_increase || 0;
  </script>
  
  <div class="dashboard-container">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="title-section">
        <h1>📊 Dashboard Corrélation News/Prix</h1>
        <p class="subtitle">Analyse l'impact réel des événements économiques sur tes actifs</p>
      </div>
      
      <div class="controls">
        <select bind:value={selectedSymbol} on:change={fetchStats} class="symbol-select">
          {#each symbols as sym}
            <option value={sym.value}>{sym.label}</option>
          {/each}
        </select>
        
        <select bind:value={daysBack} on:change={fetchStats} class="period-select">
          <option value={7}>7 jours</option>
          <option value={30}>30 jours</option>
          <option value={60}>60 jours</option>
          <option value={90}>90 jours</option>
        </select>
        
        <button on:click={refreshStats} class="refresh-btn">
          🔄 Actualiser
        </button>
      </div>
    </header>
    
    {#if loading}
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Analyse des {daysBack} derniers jours...</p>
      </div>
    {:else if stats}
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
            <span class="kpi-label">Pips moyens / event</span>
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
              <div 
                class="bar up" 
                style="width: {(stats.summary.direction_stats?.up / totalEvents * 100)}%">
              </div>
              <span class="value">{stats.summary.direction_stats?.up}</span>
            </div>
          </div>
          
          <div class="direction-bar">
            <span class="label">🔴 Baissier</span>
            <div class="bar-container">
              <div 
                class="bar down" 
                style="width: {(stats.summary.direction_stats?.down / totalEvents * 100)}%">
              </div>
              <span class="value">{stats.summary.direction_stats?.down}</span>
            </div>
          </div>
          
          <div class="direction-bar">
            <span class="label">⚪ Neutre</span>
            <div class="bar-container">
              <div 
                class="bar neutral" 
                style="width: {(stats.summary.direction_stats?.neutral / totalEvents * 100)}%">
              </div>
              <span class="value">{stats.summary.direction_stats?.neutral}</span>
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
        <h3>⏱️ Timeline événements</h3>
        <PriceTimeline data={stats.timeline} />
      </div>
    {:else}
      <div class="error-state">
        <span class="emoji">❌</span>
        <p>Impossible de charger les statistiques</p>
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
    
    .dashboard-header {
      background: white;
      padding: 2rem;
      border-radius: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      margin-bottom: 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    h1 {
      font-size: 2rem;
      color: #1e293b;
      margin-bottom: 0.5rem;
    }
    
    .subtitle {
      color: #64748b;
      font-size: 1rem;
    }
    
    .controls {
      display: flex;
      gap: 1rem;
      align-items: center;
    }
    
    select {
      padding: 0.75rem 1rem;
      border: 2px solid #e2e8f0;
      border-radius: 8px;
      font-size: 1rem;
      background: white;
      cursor: pointer;
      transition: border-color 0.2s;
    }
    
    select:hover {
      border-color: #3b82f6;
    }
    
    .refresh-btn {
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
    
    .refresh-btn:hover {
      background: #2563eb;
    }
    
    /* KPI Cards */
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2rem;
    }
    
    .kpi-card {
      background: white;
      padding: 1.5rem;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      display: flex;
      align-items: center;
      gap: 1rem;
      transition: transform 0.2s;
    }
    
    .kpi-card:hover {
      transform: translateY(-2px);
    }
    
    .kpi-card.highlight {
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      color: white;
    }
    
    .kpi-card.danger {
      border-left: 4px solid #ef4444;
    }
    
    .kpi-icon {
      font-size: 2.5rem;
    }
    
    .kpi-content {
      display: flex;
      flex-direction: column;
    }
    
    .kpi-value {
      font-size: 2rem;
      font-weight: 700;
      line-height: 1;
    }
    
    .kpi-label {
      font-size: 0.85rem;
      opacity: 0.8;
      margin-top: 0.25rem;
    }
    
    /* Direction Stats */
    .direction-stats {
      background: white;
      padding: 2rem;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
      margin-bottom: 2rem;
    }
    
    .direction-stats h3 {
      margin-bottom: 1.5rem;
    }
    
    .direction-bars {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    
    .direction-bar {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    
    .direction-bar .label {
      width: 120px;
      font-weight: 600;
    }
    
    .bar-container {
      flex: 1;
      height: 30px;
      background: #f1f5f9;
      border-radius: 8px;
      position: relative;
      overflow: hidden;
    }
    
    .bar {
      height: 100%;
      transition: width 0.5s ease;
    }
    
    .bar.up { background: #10b981; }
    .bar.down { background: #ef4444; }
    .bar.neutral { background: #94a3b8; }
    
    .bar-container .value {
      position: absolute;
      right: 10px;
      top: 50%;
      transform: translateY(-50%);
      font-weight: 600;
      color: #1e293b;
    }
    
    /* Charts Grid */
    .charts-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
      gap: 2rem;
      margin-bottom: 2rem;
    }
    
    .chart-section, .table-section, .timeline-section {
      background: white;
      padding: 2rem;
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .chart-section h3, .table-section h3, .timeline-section h3 {
      margin-bottom: 1.5rem;
      color: #1e293b;
    }
    
    .timeline-section {
      margin-bottom: 2rem;
    }
    
    /* Loading & Error */
    .loading-state, .error-state {
      text-align: center;
      padding: 4rem 2rem;
    }
    
    .spinner {
      width: 60px;
      height: 60px;
      border: 5px solid #e5e7eb;
      border-top-color: #3b82f6;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 1rem;
    }
    
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    
    .error-state .emoji {
      font-size: 4rem;
      display: block;
      margin-bottom: 1rem;
    }
  </style>