<script>
  export let event;
  
  const impactColors = {
    'High': '#ef4444',
    'Medium': '#f59e0b',
    'Low': '#10b981'
  };
  
  const impactEmojis = {
    'High': '🔴',
    'Medium': '🟡',
    'Low': '🟢'
  };
</script>

<div
  class="event-card"
  style="border-left-color: {impactColors[event && (event.impact === 'High' || event.impact === 'Medium' || event.impact === 'Low') ? event.impact : 'Low']}"
>
  <div class="event-header">
    <div class="time-currency">
      <span class="time">🕐 {event?.time}</span>
      <span class="currency">{event?.currency}</span>
    </div>
    <span class="impact" style="background: {impactColors[event.impact]}20; color: {impactColors[event.impact]}">
      {impactEmojis[event.impact]} {event.impact}
    </span>
  </div>
  
  <h3 class="event-name">{event.event}</h3>
  
  {#if event.actual || event.forecast || event.previous}
    <div class="event-data">
      {#if event.actual}
        <div class="data-item actual">
          <span class="label">Actuel</span>
          <span class="value">{event.actual}</span>
        </div>
      {/if}
      {#if event.forecast}
        <div class="data-item">
          <span class="label">Prévu</span>
          <span class="value">{event.forecast}</span>
        </div>
      {/if}
      {#if event.previous}
        <div class="data-item">
          <span class="label">Précédent</span>
          <span class="value">{event.previous}</span>
        </div>
      {/if}
    </div>
  {/if}
  
  <div class="event-footer">
    <span class="source">Source: {event.source}</span>
  </div>
</div>

<style>
  .event-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    border-left: 4px solid;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  
  .event-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }
  
  .event-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
  }
  
  .time-currency {
    display: flex;
    align-items: center;
    gap: 1rem;
  }
  
  .time {
    font-size: 0.9rem;
    color: #64748b;
  }
  
  .currency {
    font-weight: 700;
    font-size: 1.1rem;
    color: #1e293b;
  }
  
  .impact {
    padding: 0.25rem 0.75rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
  }
  
  .event-name {
    font-size: 1.1rem;
    color: #1e293b;
    margin-bottom: 1rem;
    line-height: 1.4;
  }
  
  .event-data {
    display: flex;
    gap: 1.5rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
    margin-bottom: 0.75rem;
  }
  
  .data-item {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }
  
  .data-item.actual {
    font-weight: 700;
  }
  
  .label {
    font-size: 0.75rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .value {
    font-size: 1rem;
    color: #1e293b;
  }
  
  .event-footer {
    font-size: 0.75rem;
    color: #94a3b8;
  }
</style>