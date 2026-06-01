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
    background: var(--surface-2);
  }

  th {
    padding: 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--text-muted);
    font-size: 0.875rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  tbody tr {
    border-bottom: 1px solid var(--border);
    transition: background 0.2s;
  }

  tbody tr:hover {
    background: var(--surface-2);
  }

  td {
    padding: 1rem;
    color: var(--text);
  }

  .rank {
    font-weight: 700;
    color: var(--accent);
    font-size: 1.125rem;
    font-family: var(--font-mono);
  }

  .event-name {
    font-weight: 500;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .count {
    color: var(--text-muted);
    font-family: var(--font-mono);
  }

  .badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: var(--accent-grad-soft);
    color: var(--accent);
    box-shadow: inset 0 0 0 1px rgba(34, 211, 238, 0.3);
    border-radius: 9999px;
    font-weight: 600;
    font-size: 0.875rem;
    font-family: var(--font-mono);
  }

  .impact {
    font-family: var(--font-mono);
    color: var(--text-muted);
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
