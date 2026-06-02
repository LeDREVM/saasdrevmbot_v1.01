<script>
  /** @type {any[]} */
  export let data = [];

  $: sortedData = (data || []).slice(0, 20); // Limiter à 20 événements

  /** @param {any} timestamp */
  function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  /** @param {any} direction */
  function getDirectionIcon(direction) {
    if (direction === 'up') return '📈';
    if (direction === 'down') return '📉';
    return '↔️';
  }
  
  /** @param {any} impactLevel */
  function getImpactColor(impactLevel) {
    if (impactLevel === 'High') return '#ef4444';
    if (impactLevel === 'Medium') return '#f59e0b';
    return '#94a3b8';
  }
</script>

<div class="timeline">
  {#if sortedData.length > 0}
    {#each sortedData as event}
      <div class="timeline-item">
        <div class="timeline-marker" style="background: {getImpactColor(event.impact_level)}"></div>
        <div class="timeline-content">
          <div class="timeline-header">
            <span class="time">{formatDate(event.timestamp)}</span>
            <span class="currency">{event.currency}</span>
          </div>
          <div class="event-name">{event.event_name}</div>
          <div class="timeline-stats">
            <span class="movement">
              {getDirectionIcon(event.direction)} {event.movement_pips} pips
            </span>
            <span class="impact-badge" class:had-impact={event.had_impact}>
              {event.had_impact ? '✓ Impact' : '○ Faible'}
            </span>
          </div>
        </div>
      </div>
    {/each}
  {:else}
    <div class="empty-state">
      <span class="emoji">⏱️</span>
      <p>Aucun événement dans la timeline</p>
    </div>
  {/if}
</div>

<style>
  .timeline {
    position: relative;
    padding-left: 2rem;
    max-height: 600px;
    overflow-y: auto;
  }
  
  .timeline::before {
    content: '';
    position: absolute;
    left: 0.5rem;
    top: 0;
    bottom: 0;
    width: 2px;
    background: var(--border-strong);
  }

  .timeline-item {
    position: relative;
    padding-bottom: 2rem;
    padding-left: 2rem;
  }

  .timeline-marker {
    position: absolute;
    left: 0;
    top: 0.25rem;
    width: 1rem;
    height: 1rem;
    border-radius: 50%;
    border: 3px solid var(--surface-solid);
    box-shadow: 0 0 0 2px var(--border-strong);
  }

  .timeline-content {
    background: var(--surface);
    padding: 1rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border);
    backdrop-filter: blur(12px);
    transition: all 0.2s;
  }

  .timeline-content:hover {
    border-color: var(--accent);
    box-shadow: var(--shadow-sm);
  }
  
  .timeline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }
  
  .time {
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 500;
    font-family: var(--font-mono);
  }

  .currency {
    font-size: 0.75rem;
    font-weight: 700;
    color: var(--accent);
    background: var(--accent-grad-soft);
    box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }

  .event-name {
    font-weight: 600;
    color: var(--text);
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
  }

  .timeline-stats {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .movement {
    font-weight: 600;
    color: var(--text);
    font-size: 0.875rem;
    font-family: var(--font-mono);
  }

  .impact-badge {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    background: var(--surface-2);
    color: var(--text-muted);
  }

  .impact-badge.had-impact {
    background: rgba(52, 211, 153, 0.12);
    color: var(--success);
    box-shadow: inset 0 0 0 1px rgba(52, 211, 153, 0.3);
    font-weight: 600;
  }

  .empty-state {
    text-align: center;
    padding: 3rem;
    color: var(--text-dim);
  }
  
  .empty-state .emoji {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
  }
</style>
