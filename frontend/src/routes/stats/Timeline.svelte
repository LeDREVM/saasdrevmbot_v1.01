<script>
  /**
   * Timeline Component - Affiche une timeline verticale d'événements
   * @prop {Array} events - Liste des événements à afficher
   * @prop {string} title - Titre de la timeline (optionnel)
   * @prop {number} maxItems - Nombre maximum d'items à afficher (défaut: 20)
   */
  /** @type {any[]} */
  export let events = [];
  export let title = '';
  export let maxItems = 20;

  // Trier et limiter les événements
  $: displayEvents = (events || [])
    .sort((/** @type {any} */ a, /** @type {any} */ b) => new Date(b.timestamp || b.date).getTime() - new Date(a.timestamp || a.date).getTime())
    .slice(0, maxItems);

  /**
   * Formate une date/timestamp
   * @param {any} dateStr
   */
  function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  /**
   * Formate une date courte (juste jour et mois)
   * @param {any} dateStr
   */
  function formatShortDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short'
    });
  }
  
  /**
   * Obtient la couleur selon le niveau d'impact
   * @param {any} impact
   */
  function getImpactColor(impact) {
    const impactStr = String(impact).toLowerCase();
    if (impactStr === 'high' || impactStr === 'extreme') return '#ef4444';
    if (impactStr === 'medium') return '#f59e0b';
    if (impactStr === 'low') return '#10b981';
    return '#64748b';
  }
  
  /**
   * Obtient l'icône selon le type d'événement
   * @param {any} event
   */
  function getEventIcon(event) {
    if (event.type === 'alert') return '🔔';
    if (event.type === 'prediction') return '🎯';
    if (event.type === 'movement') return '📊';
    if (event.impact_level === 'High') return '🔴';
    if (event.impact_level === 'Medium') return '🟡';
    if (event.impact_level === 'Low') return '🟢';
    return '📌';
  }
  
  /**
   * Vérifie si c'est aujourd'hui
   * @param {any} dateStr
   */
  function isToday(dateStr) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }
</script>

<div class="timeline-container">
  {#if title}
    <h3 class="timeline-title">{title}</h3>
  {/if}
  
  {#if displayEvents.length === 0}
    <div class="empty-state">
      <span class="empty-icon">📭</span>
      <p>Aucun événement à afficher</p>
    </div>
  {:else}
    <div class="timeline">
      {#each displayEvents as event, index}
        <div class="timeline-item" class:first={index === 0}>
          <!-- Marker (point sur la ligne) -->
          <div 
            class="timeline-marker" 
            style="background-color: {getImpactColor(event.impact_level || event.impact || 'low')}"
            title={event.impact_level || event.impact || 'Info'}
          >
            <span class="marker-icon">{getEventIcon(event)}</span>
          </div>
          
          <!-- Ligne verticale -->
          {#if index < displayEvents.length - 1}
            <div class="timeline-line"></div>
          {/if}
          
          <!-- Contenu de l'événement -->
          <div class="timeline-content">
            <!-- Header avec date et badges -->
            <div class="timeline-header">
              <span class="timeline-date" class:today={isToday(event.timestamp || event.date)}>
                {formatDate(event.timestamp || event.date)}
              </span>
              
              {#if event.currency}
                <span class="currency-badge">{event.currency}</span>
              {/if}
              
              {#if event.symbol}
                <span class="symbol-badge">{event.symbol}</span>
              {/if}
            </div>
            
            <!-- Nom de l'événement -->
            <div class="event-title">
              {event.event_name || event.name || event.title || 'Événement'}
            </div>
            
            <!-- Description ou détails -->
            {#if event.description}
              <p class="event-description">{event.description}</p>
            {/if}
            
            <!-- Statistiques/Métriques -->
            <div class="event-metrics">
              {#if event.movement_pips !== undefined}
                <span class="metric">
                  📊 {event.movement_pips} pips
                </span>
              {/if}
              
              {#if event.expected_movement_pips !== undefined}
                <span class="metric">
                  🎯 {event.expected_movement_pips} pips prévu
                </span>
              {/if}
              
              {#if event.confidence}
                <span class="metric confidence-{event.confidence}">
                  💪 {event.confidence}
                </span>
              {/if}
              
              {#if event.risk_level}
                <span class="metric risk-{event.risk_level}">
                  ⚠️ {event.risk_level}
                </span>
              {/if}
              
              {#if event.forecast}
                <span class="metric">
                  📈 Prév: {event.forecast}
                </span>
              {/if}
              
              {#if event.previous}
                <span class="metric">
                  📉 Préc: {event.previous}
                </span>
              {/if}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .timeline-container {
    width: 100%;
  }
  
  .timeline-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 1.5rem;
  }

  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--text-muted);
  }
  
  .empty-icon {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
  }
  
  .timeline {
    position: relative;
    padding-left: 2rem;
  }
  
  .timeline-item {
    position: relative;
    padding-bottom: 2rem;
  }
  
  .timeline-item.first .timeline-marker {
    animation: pulse 2s ease-in-out infinite;
  }
  
  @keyframes pulse {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(34, 211, 238, 0.7);
    }
    50% {
      transform: scale(1.05);
      box-shadow: 0 0 0 10px rgba(34, 211, 238, 0);
    }
  }

  .timeline-marker {
    position: absolute;
    left: -2rem;
    top: 0;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--accent);
    border: 4px solid var(--surface-solid);
    box-shadow: var(--shadow-sm);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2;
    transition: all 0.3s ease;
  }

  .timeline-marker:hover {
    transform: scale(1.1);
    box-shadow: var(--shadow);
  }
  
  .marker-icon {
    font-size: 1.2rem;
  }
  
  .timeline-line {
    position: absolute;
    left: -1.25rem;
    top: 40px;
    width: 2px;
    height: calc(100% - 40px);
    background: linear-gradient(to bottom, var(--border-strong), transparent);
    z-index: 1;
  }

  .timeline-content {
    background: var(--surface);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    padding: 1.25rem;
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease;
    border-left: 3px solid var(--border-strong);
  }

  .timeline-content:hover {
    box-shadow: var(--shadow);
    transform: translateX(4px);
    border-left-color: var(--accent);
  }
  
  .timeline-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
  }
  
  .timeline-date {
    font-size: 0.85rem;
    color: var(--text-muted);
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .timeline-date.today {
    color: var(--accent);
    font-weight: 700;
  }

  .currency-badge,
  .symbol-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
  }

  .currency-badge {
    background: var(--accent-grad-soft);
    color: var(--accent);
    box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
  }

  .symbol-badge {
    background: rgba(251, 191, 36, 0.12);
    color: var(--warning);
    box-shadow: inset 0 0 0 1px rgba(251, 191, 36, 0.3);
  }

  .event-title {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.5rem;
    line-height: 1.4;
  }

  .event-description {
    font-size: 0.9rem;
    color: var(--text-muted);
    margin-bottom: 0.75rem;
    line-height: 1.5;
  }
  
  .event-metrics {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  
  .metric {
    padding: 0.35rem 0.75rem;
    background: var(--surface-2);
    border-radius: 6px;
    font-size: 0.8rem;
    color: var(--text-muted);
    font-weight: 600;
    border: 1px solid var(--border);
    transition: all 0.2s;
  }

  .metric:hover {
    border-color: var(--border-strong);
  }

  .metric.confidence-high {
    background: rgba(52, 211, 153, 0.12);
    color: var(--success);
    border-color: rgba(52, 211, 153, 0.4);
  }

  .metric.confidence-medium {
    background: rgba(251, 191, 36, 0.12);
    color: var(--warning);
    border-color: rgba(251, 191, 36, 0.4);
  }

  .metric.confidence-low {
    background: rgba(248, 113, 113, 0.12);
    color: var(--danger);
    border-color: rgba(248, 113, 113, 0.4);
  }

  .metric.risk-extreme {
    background: rgba(248, 113, 113, 0.12);
    color: var(--danger);
    border-color: rgba(248, 113, 113, 0.4);
    font-weight: 700;
  }

  .metric.risk-high {
    background: rgba(251, 146, 60, 0.12);
    color: #fb923c;
    border-color: rgba(251, 146, 60, 0.4);
  }

  .metric.risk-medium {
    background: rgba(251, 191, 36, 0.12);
    color: var(--warning);
    border-color: rgba(251, 191, 36, 0.4);
  }

  .metric.risk-low {
    background: rgba(52, 211, 153, 0.12);
    color: var(--success);
    border-color: rgba(52, 211, 153, 0.4);
  }
  
  /* Responsive */
  @media (max-width: 640px) {
    .timeline {
      padding-left: 1.5rem;
    }
    
    .timeline-marker {
      left: -1.5rem;
      width: 32px;
      height: 32px;
    }
    
    .marker-icon {
      font-size: 1rem;
    }
    
    .timeline-line {
      left: -0.9375rem;
    }
    
    .timeline-content {
      padding: 1rem;
    }
    
    .event-title {
      font-size: 0.95rem;
    }
  }
</style>
