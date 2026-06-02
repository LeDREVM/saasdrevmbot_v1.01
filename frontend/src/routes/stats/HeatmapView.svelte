<script>
  /** @type {Record<string, Record<string, number>>} */
  export let data = {};

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const hours = [0, 3, 6, 9, 12, 15, 18, 21];

  // Fonction pour obtenir la couleur selon la valeur
  /** @param {any} value */
  function getColor(value) {
    if (value === 0) return 'rgba(255,255,255,0.04)';
    if (value < 5) return 'rgba(34,211,238,0.18)';
    if (value < 10) return 'rgba(34,211,238,0.38)';
    if (value < 20) return 'rgba(34,211,238,0.6)';
    if (value < 30) return 'rgba(99,102,241,0.75)';
    return 'rgba(99,102,241,0.95)';
  }
</script>

<div class="heatmap">
  <div class="heatmap-grid">
    <!-- Header avec les heures -->
    <div class="cell header"></div>
    {#each hours as hour}
      <div class="cell header">{hour}h</div>
    {/each}
    
    <!-- Lignes par jour -->
    {#each days as day}
      <div class="cell day-label">{day.slice(0, 3)}</div>
      {#each hours as hour}
        {@const value = data[day]?.[hour] || 0}
        <div 
          class="cell data-cell" 
          style="background-color: {getColor(value)}"
          title="{day} {hour}h: {value} pips">
          {value > 0 ? value.toFixed(1) : ''}
        </div>
      {/each}
    {/each}
  </div>
  
  <!-- Légende -->
  <div class="legend">
    <span class="legend-label">Volatilité (pips):</span>
    <div class="legend-scale">
      <div class="legend-item" style="background: rgba(255,255,255,0.04)">0</div>
      <div class="legend-item" style="background: rgba(34,211,238,0.18)">5</div>
      <div class="legend-item" style="background: rgba(34,211,238,0.38)">10</div>
      <div class="legend-item" style="background: rgba(34,211,238,0.6)">20</div>
      <div class="legend-item" style="background: rgba(99,102,241,0.75)">30+</div>
    </div>
  </div>
</div>

<style>
  .heatmap {
    padding: 1rem;
  }
  
  .heatmap-grid {
    display: grid;
    grid-template-columns: 100px repeat(8, 1fr);
    gap: 4px;
    margin-bottom: 1rem;
  }
  
  .cell {
    padding: 0.75rem;
    text-align: center;
    border-radius: 4px;
    font-size: 0.875rem;
  }
  
  .cell.header {
    font-weight: 600;
    color: var(--text-muted);
    background: transparent;
    font-family: var(--font-mono);
  }

  .cell.day-label {
    font-weight: 600;
    color: var(--text);
    background: var(--surface-2);
    border: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding-left: 1rem;
  }

  .cell.data-cell {
    cursor: pointer;
    transition: transform 0.2s;
    color: var(--text);
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .cell.data-cell:hover {
    transform: scale(1.1);
    box-shadow: var(--shadow-sm);
  }

  .legend {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  .legend-label {
    font-weight: 600;
    color: var(--text-muted);
  }

  .legend-scale {
    display: flex;
    gap: 0.5rem;
  }

  .legend-item {
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--text);
  }
</style>
