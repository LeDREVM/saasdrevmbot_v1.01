<script>
  import Timeline from './Timeline.svelte';
  import { onMount } from 'svelte';
  
  let events = [];
  let loading = true;
  
  const API_URL = 'http://localhost:8000/api';
  
  // Données d'exemple pour la démo
  const mockEvents = [
    {
      timestamp: new Date().toISOString(),
      event_name: 'Non-Farm Payrolls',
      currency: 'USD',
      symbol: 'EURUSD',
      impact_level: 'High',
      movement_pips: 45.5,
      expected_movement_pips: 35.0,
      confidence: 'high',
      risk_level: 'extreme',
      forecast: '200K',
      previous: '180K',
      type: 'alert'
    },
    {
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      event_name: 'Décision de Taux BCE',
      currency: 'EUR',
      symbol: 'EURUSD',
      impact_level: 'High',
      movement_pips: 32.0,
      confidence: 'medium',
      risk_level: 'high',
      type: 'prediction'
    },
    {
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      event_name: 'Ventes au Détail',
      currency: 'GBP',
      symbol: 'GBPUSD',
      impact_level: 'Medium',
      movement_pips: 18.5,
      confidence: 'high',
      risk_level: 'medium',
      forecast: '0.5%',
      previous: '0.3%'
    },
    {
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      event_name: 'Indice PMI Manufacturing',
      currency: 'USD',
      impact_level: 'Medium',
      movement_pips: 12.0,
      confidence: 'medium',
      risk_level: 'low',
      type: 'movement'
    },
    {
      timestamp: new Date(Date.now() - 14400000).toISOString(),
      event_name: 'Discours Powell (Fed)',
      currency: 'USD',
      symbol: 'EURUSD',
      impact_level: 'High',
      movement_pips: 28.5,
      confidence: 'high',
      risk_level: 'high',
      description: 'Discours du président de la Fed sur la politique monétaire'
    }
  ];
  
  async function loadEvents() {
    loading = true;
    try {
      // Essayer de charger depuis l'API
      const response = await fetch(`${API_URL}/calendar/today`);
      if (response.ok) {
        const data = await response.json();
        events = data.events || mockEvents;
      } else {
        // Utiliser les données mock si l'API n'est pas disponible
        events = mockEvents;
      }
    } catch (error) {
      console.error('Erreur chargement événements:', error);
      // Utiliser les données mock en cas d'erreur
      events = mockEvents;
    } finally {
      loading = false;
    }
  }
  
  onMount(() => {
    loadEvents();
  });
</script>

<div class="timeline-example">
  <div class="header">
    <h2>📅 Timeline des Événements</h2>
    <button on:click={loadEvents} class="refresh-btn" disabled={loading}>
      {loading ? '⏳' : '🔄'} Actualiser
    </button>
  </div>
  
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <p>Chargement de la timeline...</p>
    </div>
  {:else}
    <Timeline 
      {events} 
      title="Événements Récents"
      maxItems={10}
    />
  {/if}
  
  <!-- Statistiques -->
  <div class="stats-grid">
    <div class="stat-card">
      <span class="stat-value">{events.length}</span>
      <span class="stat-label">Événements</span>
    </div>
    
    <div class="stat-card">
      <span class="stat-value">
        {events.filter(e => e.impact_level === 'High').length}
      </span>
      <span class="stat-label">Impact Élevé</span>
    </div>
    
    <div class="stat-card">
      <span class="stat-value">
        {Math.round(events.reduce((sum, e) => sum + (e.movement_pips || 0), 0) / events.length || 0)}
      </span>
      <span class="stat-label">Pips Moyen</span>
    </div>
  </div>
</div>

<style>
  .timeline-example {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
  }
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
  }
  
  h2 {
    font-size: 1.75rem;
    color: #1e293b;
    font-weight: 700;
  }
  
  .refresh-btn {
    padding: 0.75rem 1.5rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .refresh-btn:hover:not(:disabled) {
    background: #2563eb;
    transform: translateY(-2px);
  }
  
  .refresh-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }
  
  .loading {
    text-align: center;
    padding: 4rem 2rem;
    color: #64748b;
  }
  
  .spinner {
    width: 50px;
    height: 50px;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-top: 2rem;
  }
  
  .stat-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    text-align: center;
    border-left: 4px solid #3b82f6;
  }
  
  .stat-value {
    display: block;
    font-size: 2rem;
    font-weight: 700;
    color: #3b82f6;
    margin-bottom: 0.5rem;
  }
  
  .stat-label {
    font-size: 0.9rem;
    color: #64748b;
    font-weight: 600;
  }
</style>
