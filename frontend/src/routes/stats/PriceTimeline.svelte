<script>
  export let data = [];
  
  $: sortedData = (data || []).slice(0, 20); // Limiter à 20 événements
  
  function formatDate(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: 'short',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  function getDirectionIcon(direction) {
    if (direction === 'up') return '📈';
    if (direction === 'down') return '📉';
    return '↔️';
  }
  
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
    background: #e2e8f0;
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
    border: 3px solid white;
    box-shadow: 0 0 0 2px #e2e8f0;
  }
  
  .timeline-content {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid #e2e8f0;
    transition: all 0.2s;
  }
  
  .timeline-content:hover {
    border-color: #3b82f6;
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1);
  }
  
  .timeline-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }
  
  .time {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 500;
  }
  
  .currency {
    font-size: 0.75rem;
    font-weight: 700;
    color: #3b82f6;
    background: #dbeafe;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
  
  .event-name {
    font-weight: 600;
    color: #1e293b;
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
    color: #1e293b;
    font-size: 0.875rem;
  }
  
  .impact-badge {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    background: #f1f5f9;
    color: #64748b;
  }
  
  .impact-badge.had-impact {
    background: #dcfce7;
    color: #166534;
    font-weight: 600;
  }
  
  .empty-state {
    text-align: center;
    padding: 3rem;
    color: #94a3b8;
  }
  
  .empty-state .emoji {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
  }
</style>
