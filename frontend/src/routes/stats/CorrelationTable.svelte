<script>
  export let data = {};
  
  $: entries = Object.entries(data || {}).slice(0, 10);
</script>

<div class="table-container">
  {#if entries.length > 0}
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>Événement</th>
          <th>Occurrences</th>
          <th>Mouvement Moyen</th>
          <th>Impact Moyen</th>
        </tr>
      </thead>
      <tbody>
        {#each entries as [eventName, eventData], idx}
          <tr>
            <td class="rank">{idx + 1}</td>
            <td class="event-name">{eventName}</td>
            <td class="count">{eventData.count}</td>
            <td class="pips">
              <span class="badge">{eventData.avg_pips} pips</span>
            </td>
            <td class="impact">{eventData.avg_impact.toFixed(4)}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    <div class="empty-state">
      <span class="emoji">📊</span>
      <p>Aucune donnée disponible</p>
    </div>
  {/if}
</div>

<style>
  .table-container {
    overflow-x: auto;
  }
  
  table {
    width: 100%;
    border-collapse: collapse;
  }
  
  thead {
    background: #f8fafc;
  }
  
  th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: #64748b;
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  
  tbody tr {
    border-bottom: 1px solid #e2e8f0;
    transition: background 0.2s;
  }
  
  tbody tr:hover {
    background: #f8fafc;
  }
  
  td {
    padding: 1rem;
    color: #1e293b;
  }
  
  .rank {
    font-weight: 700;
    color: #3b82f6;
    font-size: 1.125rem;
  }
  
  .event-name {
    font-weight: 500;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .count {
    color: #64748b;
  }
  
  .badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: #dbeafe;
    color: #1e40af;
    border-radius: 9999px;
    font-weight: 600;
    font-size: 0.875rem;
  }
  
  .impact {
    font-family: monospace;
    color: #64748b;
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
