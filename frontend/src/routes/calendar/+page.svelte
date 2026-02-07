<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import EventCard from './EventCard.svelte';
  import Timeline from '../stats/Timeline.svelte';
  import QuickNav from '$lib/components/QuickNav.svelte';
  
  $: currentPath = $page.url.pathname;
  
  let events = [];
  let loading = true;
  let selectedCurrencies = ['USD', 'EUR', 'JPY', 'GBP'];
  let selectedImpact = ['High', 'Medium'];
  let viewMode = 'list'; // 'list' ou 'timeline'
  
  const currencies = ['USD', 'EUR', 'JPY', 'GBP', 'CHF', 'CAD', 'AUD', 'NZD'];
  const impacts = ['High', 'Medium', 'Low'];
  
  async function fetchCalendar() {
    loading = true;
    
    const params = new URLSearchParams({
      currencies: selectedCurrencies.join(','),
      impact: selectedImpact.join(',')
    });
    
    try {
      const response = await fetch(`http://localhost:8000/api/calendar/today?${params}`);
      const data = await response.json();
      events = data.events;
    } catch (error) {
      console.error('Erreur fetch calendrier:', error);
    } finally {
      loading = false;
    }
  }
  
  async function forceSync() {
    await fetch('http://localhost:8000/api/calendar/sync', { method: 'POST' });
    await fetchCalendar();
  }
  
  onMount(fetchCalendar);
  
  // Stats rapides
  $: highImpactCount = events.filter(e => e.impact === 'High').length;
  $: mediumImpactCount = events.filter(e => e.impact === 'Medium').length;
</script>

<svelte:head>
  <title>Calendrier Économique - DrevmBot</title>
</svelte:head>

<QuickNav currentPage={currentPath} />

<div class="calendar-container">
  <!-- Header -->
  <header class="page-header">
    <h1 class="page-title">📅 Calendrier Économique</h1>
    <p class="page-description">{new Date().toLocaleDateString('fr-FR', {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'})}</p>
    
    <div class="stats">
      <span class="stat high">🔴 {highImpactCount} High</span>
      <span class="stat medium">🟡 {mediumImpactCount} Medium</span>
      <span class="stat total">📊 {events.length} Total</span>
    </div>
  </header>
  
  <!-- Filtres -->
  <div class="filters">
    <div class="filter-group">
      <label>💱 Devises:</label>
      <div class="checkbox-group">
        {#each currencies as currency}
          <label class="checkbox-label">
            <input 
              type="checkbox" 
              value={currency}
              bind:group={selectedCurrencies}
              on:change={fetchCalendar}
            />
            {currency}
          </label>
        {/each}
      </div>
    </div>
    
    <div class="filter-group">
      <label>⚡ Impact:</label>
      <div class="checkbox-group">
        {#each impacts as impact}
          <label class="checkbox-label">
            <input 
              type="checkbox" 
              value={impact}
              bind:group={selectedImpact}
              on:change={fetchCalendar}
            />
            {impact}
          </label>
        {/each}
      </div>
    </div>
    
    <button class="sync-btn" on:click={forceSync}>
      🔄 Actualiser
    </button>
    
    <div class="view-toggle">
      <button 
        class:active={viewMode === 'list'} 
        on:click={() => viewMode = 'list'}>
        📋 Liste
      </button>
      <button 
        class:active={viewMode === 'timeline'} 
        on:click={() => viewMode = 'timeline'}>
        ⏱️ Timeline
      </button>
    </div>
  </div>
  
  <!-- Contenu -->
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <p>Récupération du calendrier...</p>
    </div>
  {:else if events.length === 0}
    <div class="empty">
      <span class="emoji">🌴</span>
      <p>Aucun événement économique aujourd'hui</p>
    </div>
  {:else}
    {#if viewMode === 'list'}
      <div class="events-list">
        {#each events as event (event.time + event.currency + event.event)}
          <EventCard {event} />
        {/each}
      </div>
    {:else}
      <Timeline {events} />
    {/if}
  {/if}
</div>

<style>
  .calendar-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
  }
  
  header {
    text-align: center;
    margin-bottom: 2rem;
  }
  
  h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    color: #1e293b;
  }
  
  .date {
    color: #64748b;
    font-size: 1.1rem;
  }
  
  .stats {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-top: 1rem;
  }
  
  .stat {
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-weight: 600;
    font-size: 0.9rem;
  }
  
  .stat.high { background: #fee2e2; color: #991b1b; }
  .stat.medium { background: #fef3c7; color: #92400e; }
  .stat.total { background: #dbeafe; color: #1e40af; }
  
  .filters {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .filter-group label {
    font-weight: 600;
    display: block;
    margin-bottom: 0.5rem;
  }
  
  .checkbox-group {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
  }
  
  .checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-weight: normal;
  }
  
  .sync-btn {
    padding: 0.75rem 1.5rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
    align-self: flex-start;
  }
  
  .sync-btn:hover {
    background: #2563eb;
  }
  
  .view-toggle {
    display: flex;
    gap: 0.5rem;
  }
  
  .view-toggle button {
    padding: 0.5rem 1rem;
    background: #f1f5f9;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }
  
  .view-toggle button.active {
    background: #3b82f6;
    color: white;
  }
  
  .loading, .empty {
    text-align: center;
    padding: 4rem 2rem;
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
  
  .empty .emoji {
    font-size: 4rem;
    display: block;
    margin-bottom: 1rem;
  }
  
  .events-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
</style>