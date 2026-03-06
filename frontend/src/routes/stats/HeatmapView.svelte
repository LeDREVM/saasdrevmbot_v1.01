<script>
  export let data = {};
  
  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
  const hours = [0, 3, 6, 9, 12, 15, 18, 21];
  
  // Fonction pour obtenir la couleur selon la valeur
  function getColor(value) {
    if (value === 0) return '#f1f5f9';
    if (value < 5) return '#dbeafe';
    if (value < 10) return '#93c5fd';
    if (value < 20) return '#3b82f6';
    if (value < 30) return '#1d4ed8';
    return '#1e3a8a';
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
      <div class="legend-item" style="background: #f1f5f9">0</div>
      <div class="legend-item" style="background: #dbeafe">5</div>
      <div class="legend-item" style="background: #93c5fd">10</div>
      <div class="legend-item" style="background: #3b82f6">20</div>
      <div class="legend-item" style="background: #1d4ed8">30+</div>
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
    color: #64748b;
    background: transparent;
  }
  
  .cell.day-label {
    font-weight: 600;
    color: #1e293b;
    background: #f8fafc;
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding-left: 1rem;
  }
  
  .cell.data-cell {
    cursor: pointer;
    transition: transform 0.2s;
    color: white;
    font-weight: 600;
  }
  
  .cell.data-cell:hover {
    transform: scale(1.1);
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  }
  
  .legend {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
  }
  
  .legend-label {
    font-weight: 600;
    color: #64748b;
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
    color: #1e293b;
  }
</style>
