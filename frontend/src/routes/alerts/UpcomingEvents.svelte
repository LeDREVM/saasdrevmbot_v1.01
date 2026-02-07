<script>
  import { onMount } from 'svelte';
  
  export let symbols = ['EURUSD'];
  
  let events = [];
  let loading = true;
  
  const API_URL = 'http://localhost:8000/api';
  
  async function fetchUpcomingEvents() {
    loading = true;
    try {
      const response = await fetch(`${API_URL}/calendar/today`);
      const data = await response.json();
      events = data.events || [];
    } catch (error) {
      console.error('Erreur chargement événements:', error);
      events = [];
    } finally {
      loading = false;
    }
  }
  
  onMount(() => {
    fetchUpcomingEvents();
  });
  
  function getImpactColor(impact) {
    switch(impact) {
      case 'High': return '#ef4444';
      case 'Medium': return '#f59e0b';
      case 'Low': return '#10b981';
      default: return '#64748b';
    }
  }
</script>

<div class="upcoming-events">
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <p>Chargement des événements...</p>
    </div>
  {:else if events.length === 0}
    <div class="empty">
      <span class="emoji">📭</span>
      <p>Aucun événement à venir dans les 12h</p>
    </div>
  {:else}
    <div class="events-list">
      {#each events as event}
        <div class="event-item">
          <div class="event-time">
            <span class="time">{event.time}</span>
            <span class="date">{event.date}</span>
          </div>
          
          <div class="event-info">
            <div class="event-header">
              <span class="currency">{event.currency}</span>
              <span class="impact" style="background-color: {getImpactColor(event.impact)}">
                {event.impact}
              </span>
            </div>
            <h4 class="event-name">{event.event}</h4>
            
            {#if event.forecast || event.previous}
              <div class="event-data">
                {#if event.forecast}
                  <span class="data-item">Prév: {event.forecast}</span>
                {/if}
                {#if event.previous}
                  <span class="data-item">Préc: {event.previous}</span>
                {/if}
              </div>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .upcoming-events {
    min-height: 200px;
  }
  
  .loading, .empty {
    text-align: center;
    padding: 3rem 1rem;
    color: #64748b;
  }
  
  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #e5e7eb;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }
  
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
  
  .empty .emoji {
    font-size: 3rem;
    display: block;
    margin-bottom: 1rem;
  }
  
  .events-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .event-item {
    display: flex;
    gap: 1rem;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 8px;
    border-left: 3px solid #3b82f6;
    transition: all 0.2s;
  }
  
  .event-item:hover {
    background: #f1f5f9;
    transform: translateX(4px);
  }
  
  .event-time {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 80px;
    padding: 0.5rem;
    background: white;
    border-radius: 6px;
  }
  
  .time {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1e293b;
  }
  
  .date {
    font-size: 0.75rem;
    color: #64748b;
    margin-top: 0.25rem;
  }
  
  .event-info {
    flex: 1;
  }
  
  .event-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }
  
  .currency {
    font-weight: 700;
    color: #3b82f6;
    font-size: 0.9rem;
  }
  
  .impact {
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
  }
  
  .event-name {
    font-size: 1rem;
    color: #1e293b;
    margin-bottom: 0.5rem;
    font-weight: 600;
  }
  
  .event-data {
    display: flex;
    gap: 1rem;
    font-size: 0.85rem;
    color: #64748b;
  }
  
  .data-item {
    background: white;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
</style>
