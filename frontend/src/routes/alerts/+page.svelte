<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import AlertCard from './AlertCard.svelte';
  import ConfigPanel from './ConfigPanel.svelte';
  import UpcomingEvents from './UpcomingEvents.svelte';
  import AlertHistory from './AlertHistory.svelte';
  import TestNotification from './TestNotification.svelte';
  import QuickNav from '$lib/components/QuickNav.svelte';
  
  $: currentPath = $page.url.pathname;
  
  // User ID (hardcoded pour l'instant, à remplacer par auth)
  const userId = 'negus_dja';
  
  // State
  /** @type {any} */
  let settings = null;
  /** @type {any[]} */
  let activeAlerts = [];
  /** @type {any[]} */
  let history = [];
  /** @type {any} */
  let stats = null;
  /** @type {any} */
  let syncStatus = null;
  let loading = true;
  let activeTab = 'overview'; // overview, config, history

  // API Base URL
  const API_URL = 'http://localhost:8000/api';
  
  // Fetch functions
  async function fetchSettings() {
    const response = await fetch(`${API_URL}/alert-config/settings/${userId}`);
    settings = await response.json();
  }
  
  async function fetchActiveAlerts() {
    const response = await fetch(`${API_URL}/alert-config/active-alerts/${userId}`);
    const data = await response.json();
    activeAlerts = data.alerts || [];
  }
  
  async function fetchHistory() {
    const response = await fetch(`${API_URL}/alert-config/history/${userId}?limit=20`);
    const data = await response.json();
    history = data.alerts || [];
  }
  
  async function fetchStats() {
    const response = await fetch(`${API_URL}/alert-config/stats/${userId}?days_back=30`);
    stats = await response.json();
  }
  
  async function loadAll() {
    loading = true;
    try {
      await Promise.all([
        fetchSettings(),
        fetchActiveAlerts(),
        fetchHistory(),
        fetchStats()
      ]);
    } catch (error) {
      console.error('Erreur chargement:', error);
    } finally {
      loading = false;
    }
  }
  
  /** @param {any} newSettings */
  async function updateSettings(newSettings) {
    const response = await fetch(`${API_URL}/alert-config/settings/${userId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newSettings)
    });
    
    if (response.ok) {
      await fetchSettings();
      alert('✅ Paramètres mis à jour !');
    }
  }
  
  // Nextcloud sync functions
  async function syncToNextcloud() {
    try {
      const response = await fetch(`${API_URL}/nextcloud/sync/all`, {
        method: 'POST'
      });
      const data = await response.json();
      alert('✅ Synchronisation lancée !');
      await checkSyncStatus();
    } catch (error) {
      alert('❌ Erreur sync: ' + (error instanceof Error ? error.message : String(error)));
    }
  }
  
  async function checkSyncStatus() {
    try {
      const response = await fetch(`${API_URL}/nextcloud/status`);
      syncStatus = await response.json();
    } catch (error) {
      console.error('Erreur statut sync:', error);
    }
  }
  
  // Lifecycle
  onMount(() => {
    loadAll();
    checkSyncStatus();
  });
  
  // Auto-refresh toutes les 5 minutes
  setInterval(() => {
    fetchActiveAlerts();
    fetchHistory();
  }, 5 * 60 * 1000);
  
  // KPIs calculés
  $: alertCount = activeAlerts.length;
  $: extremeCount = activeAlerts.filter(a => a.prediction?.risk_level === 'extreme').length;
  $: accuracyRate = stats?.summary?.accuracy_rate || 0;
  $: totalSent = stats?.summary?.total_alerts_sent || 0;
</script>

<svelte:head>
  <title>Alertes - DrevmBot</title>
</svelte:head>

<QuickNav currentPage={currentPath} />

<div class="dashboard-container">
  <!-- Header -->
  <header class="page-header">
    <h1 class="page-title">🔔 Dashboard Alertes</h1>
    <p class="page-description">Gestion intelligente des notifications d'événements économiques</p>
    
    <div class="header-actions">
      <button on:click={loadAll} class="refresh-btn">
        🔄 Actualiser
      </button>
      <div class="user-badge">
        👤 {userId}
      </div>
    </div>
  </header>
  
  <!-- Navigation Tabs -->
  <nav class="tabs">
    <button 
      class:active={activeTab === 'overview'} 
      on:click={() => activeTab = 'overview'}>
      📊 Vue d'ensemble
    </button>
    <button 
      class:active={activeTab === 'config'} 
      on:click={() => activeTab = 'config'}>
      ⚙️ Configuration
    </button>
    <button 
      class:active={activeTab === 'history'} 
      on:click={() => activeTab = 'history'}>
      📜 Historique
    </button>
  </nav>
  
  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Chargement du dashboard...</p>
    </div>
  {:else}
    <!-- Vue d'ensemble -->
    {#if activeTab === 'overview'}
      <div class="overview-section">
        <!-- KPI Cards -->
        <div class="kpi-grid">
          <div class="kpi-card primary">
            <div class="kpi-icon">🔔</div>
            <div class="kpi-content">
              <span class="kpi-value">{alertCount}</span>
              <span class="kpi-label">Alertes actives</span>
            </div>
          </div>
          
          <div class="kpi-card {extremeCount > 0 ? 'danger' : ''}">
            <div class="kpi-icon">🔴</div>
            <div class="kpi-content">
              <span class="kpi-value">{extremeCount}</span>
              <span class="kpi-label">Risque EXTRÊME</span>
            </div>
          </div>
          
          <div class="kpi-card success">
            <div class="kpi-icon">🎯</div>
            <div class="kpi-content">
              <span class="kpi-value">{accuracyRate}%</span>
              <span class="kpi-label">Précision</span>
            </div>
          </div>
          
          <div class="kpi-card">
            <div class="kpi-icon">📨</div>
            <div class="kpi-content">
              <span class="kpi-value">{totalSent}</span>
              <span class="kpi-label">Total envoyées (30j)</span>
            </div>
          </div>
        </div>
        
        <!-- Alertes Actives -->
        <section class="section">
          <div class="section-header">
            <h2>🔔 Alertes Actives ({alertCount})</h2>
            <p class="section-desc">Événements à venir dans les {settings?.advanced?.advance_notice_hours || 2}h</p>
          </div>
          
          {#if alertCount === 0}
            <div class="empty-state">
              <span class="emoji">🌴</span>
              <p>Aucune alerte active</p>
              <p class="sub">Profite du calme avant la tempête !</p>
            </div>
          {:else}
            <div class="alerts-grid">
              {#each activeAlerts as alert (alert.event.event_name + alert.symbol)}
                <AlertCard {alert} />
              {/each}
            </div>
          {/if}
        </section>
        
        <!-- Synchronisation Nextcloud -->
        <section class="section sync-section">
          <div class="section-header">
            <h2>☁️ Synchronisation Nextcloud</h2>
            <p class="section-desc">Sauvegarde automatique sur ledream.kflw.io</p>
          </div>
          
          <div class="sync-actions">
            <button on:click={syncToNextcloud} class="sync-btn">
              📤 Sync Maintenant
            </button>
            
            <button on:click={checkSyncStatus} class="status-btn">
              ℹ️ Vérifier Statut
            </button>
          </div>
          
          {#if syncStatus}
            <div class="sync-status" class:success={syncStatus.connected}>
              {#if syncStatus.connected}
                <span class="status-icon">✅</span>
                <div class="status-content">
                  <strong>Connecté à Nextcloud</strong>
                  <p class="sync-url">{syncStatus.nextcloud_url}</p>
                  {#if syncStatus.last_sync}
                    <p class="sync-time">Dernière sync: {new Date(syncStatus.last_sync).toLocaleString('fr-FR')}</p>
                  {/if}
                </div>
              {:else}
                <span class="status-icon">❌</span>
                <div class="status-content">
                  <strong>Déconnecté</strong>
                  <p class="sync-url">Vérifier la configuration dans .env</p>
                </div>
              {/if}
            </div>
          {/if}
        </section>
        
        <!-- Prochains événements (12h) -->
        <section class="section">
          <div class="section-header">
            <h2>📅 Prochains Événements (12h)</h2>
            <p class="section-desc">Tous les événements à venir, même non-alarmants</p>
          </div>
          
          <UpcomingEvents symbols={settings?.watched_symbols || []} />
        </section>
        
        <!-- Test Panel -->
        <section class="section">
          <div class="section-header">
            <h2>🧪 Test Notifications</h2>
            <p class="section-desc">Teste tes canaux de notification</p>
          </div>
          
          <TestNotification {userId} {settings} />
        </section>
      </div>
    {/if}
    
    <!-- Configuration -->
    {#if activeTab === 'config'}
      <ConfigPanel {settings} on:update={(e) => updateSettings(e.detail)} />
    {/if}
    
    <!-- Historique -->
    {#if activeTab === 'history'}
      <AlertHistory {history} {stats} />
    {/if}
  {/if}
</div>

<style>
  .dashboard-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
  }

  .dashboard-header {
    background: var(--surface);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    padding: 2rem;
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    margin-bottom: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  h1 {
    font-size: 2rem;
    color: var(--text);
    margin-bottom: 0.5rem;
  }

  .subtitle {
    color: var(--text-muted);
    font-size: 1rem;
  }

  .header-actions {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .refresh-btn {
    padding: 0.75rem 1.5rem;
    background: var(--accent-grad);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .refresh-btn:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
  }

  .user-badge {
    padding: 0.5rem 1rem;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  /* Tabs */
  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 2rem;
    background: var(--surface);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    padding: 0.5rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
  }

  .tabs button {
    flex: 1;
    padding: 1rem;
    background: transparent;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    color: var(--text-muted);
  }

  .tabs button:hover {
    background: var(--surface-2);
    color: var(--text);
  }

  .tabs button.active {
    background: var(--accent-grad-soft);
    color: var(--accent);
    box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
  }
  
  /* KPI Grid */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }
  
  .kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    padding: 1.5rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    display: flex;
    align-items: center;
    gap: 1rem;
    transition: transform 0.2s, border-color 0.2s;
    color: var(--text);
  }

  .kpi-card:hover {
    transform: translateY(-2px);
    border-color: var(--border-strong);
  }

  .kpi-card.primary {
    background: var(--accent-grad);
    border: none;
    color: #fff;
  }

  .kpi-card.danger {
    border-left: 4px solid var(--danger);
  }

  .kpi-card.success {
    border-left: 4px solid var(--success);
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
    font-family: var(--font-mono);
  }
  
  .kpi-label {
    font-size: 0.85rem;
    opacity: 0.8;
    margin-top: 0.25rem;
  }
  
  /* Sections */
  .section {
    background: var(--surface);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    padding: 2rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    margin-bottom: 2rem;
  }

  .section-header {
    margin-bottom: 1.5rem;
  }

  .section-header h2 {
    font-size: 1.5rem;
    color: var(--text);
    margin-bottom: 0.5rem;
  }

  .section-desc {
    color: var(--text-muted);
    font-size: 0.9rem;
  }
  
  /* Alerts Grid */
  .alerts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
  }
  
  /* Nextcloud Sync Section */
  .sync-section {
    border-left: 4px solid var(--accent);
  }

  .sync-actions {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
  }

  .sync-btn {
    padding: 1rem 2rem;
    background: var(--accent-grad);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .sync-btn:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-sm);
  }

  .status-btn {
    padding: 1rem 2rem;
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .status-btn:hover {
    border-color: var(--accent);
  }

  .sync-status {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem;
    border-radius: 8px;
    background: rgba(248, 113, 113, 0.12);
    color: var(--danger);
    box-shadow: inset 0 0 0 1px rgba(248, 113, 113, 0.3);
  }

  .sync-status.success {
    background: rgba(52, 211, 153, 0.12);
    color: var(--success);
    box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.3);
  }
  
  .status-icon {
    font-size: 1.5rem;
  }
  
  .status-content {
    flex: 1;
  }
  
  .status-content strong {
    display: block;
    margin-bottom: 0.5rem;
  }
  
  .sync-url {
    font-size: 0.85rem;
    opacity: 0.8;
    margin-top: 0.25rem;
  }
  
  .sync-time {
    font-size: 0.75rem;
    opacity: 0.7;
    margin-top: 0.5rem;
  }
  
  /* Empty State */
  .empty-state {
    text-align: center;
    padding: 4rem 2rem;
  }
  
  .empty-state .emoji {
    font-size: 4rem;
    display: block;
    margin-bottom: 1rem;
  }
  
  .empty-state p {
    color: var(--text-muted);
    font-size: 1.1rem;
  }
  
  .empty-state .sub {
    font-size: 0.9rem;
    margin-top: 0.5rem;
  }
  
  /* Loading */
  .loading-state {
    text-align: center;
    padding: 4rem 2rem;
  }
  
  .spinner {
    width: 60px;
    height: 60px;
    border: 5px solid var(--surface-2);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
