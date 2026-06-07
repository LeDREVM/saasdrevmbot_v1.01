<script>
  import { onMount, onDestroy } from 'svelte';
  import { API_ENDPOINTS, POLLING_CONFIG } from '$lib/config.js';
  import ScoreCard from './ScoreCard.svelte';

  /** @type {any[]} */
  let scores = [];
  /** @type {any} */
  let stats = null;
  let loading = true;
  let error = '';

  // Filtre par recommandation
  let filter = 'ALL'; // ALL | TRADE | WAIT | SKIP

  // Formulaire d'analyse manuelle
  let form = {
    symbol: 'US30',
    setup_grade: 'A',
    htf_phase: 'markup',
    direction: 'BUY',
    session_active: true,
    spread_ok: true
  };
  let analyzing = false;
  let analyzeError = '';

  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollTimer;

  async function fetchHistory() {
    const res = await fetch(`${API_ENDPOINTS.scoringHistory}?limit=50`);
    if (!res.ok) throw new Error(`History ${res.status}`);
    const data = await res.json();
    scores = data.scores || [];
  }

  async function fetchStats() {
    const res = await fetch(`${API_ENDPOINTS.scoring.replace('/n8n/scoring', '/scoring/stats')}`);
    if (res.ok) stats = await res.json();
  }

  async function loadAll() {
    loading = true;
    error = '';
    try {
      await Promise.all([fetchHistory(), fetchStats()]);
    } catch (e) {
      error = 'Impossible de charger les scores. Le backend est-il démarré ?';
      console.error(e);
    } finally {
      loading = false;
    }
  }

  async function runAnalysis() {
    analyzing = true;
    analyzeError = '';
    try {
      const url = API_ENDPOINTS.scoring.replace('/n8n/scoring', '/scoring/analyze');
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, notify: false })
      });
      if (!res.ok) throw new Error(`Analyze ${res.status}`);
      await loadAll();
    } catch (e) {
      analyzeError = "Échec de l'analyse (vérifier ANTHROPIC_API_KEY côté backend).";
      console.error(e);
    } finally {
      analyzing = false;
    }
  }

  $: filtered = filter === 'ALL' ? scores : scores.filter((s) => s.recommendation === filter);

  onMount(() => {
    loadAll();
    if (POLLING_CONFIG.enabled) {
      pollTimer = setInterval(fetchHistory, POLLING_CONFIG.interval);
    }
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
  });
</script>

<svelte:head>
  <title>Scoring IA — saasDrevmBot</title>
</svelte:head>

<div class="page-header">
  <h1 class="page-title">🤖 Scoring IA des Setups</h1>
  <p class="page-description">
    Analyse automatique des setups de trading par agent IA — score /100 et recommandation TRADE / WAIT / SKIP.
  </p>
</div>

<!-- Statistiques -->
{#if stats}
  <div class="grid grid-4 stats-row">
    <div class="stat-box">
      <span class="stat-label">Total analyses</span>
      <span class="stat-value">{stats.total}</span>
    </div>
    <div class="stat-box">
      <span class="stat-label">Score moyen</span>
      <span class="stat-value">{stats.avg_score}<small>/100</small></span>
    </div>
    <div class="stat-box">
      <span class="stat-label">✅ TRADE</span>
      <span class="stat-value trade">{stats.by_recommendation.TRADE}</span>
    </div>
    <div class="stat-box">
      <span class="stat-label">❌ SKIP</span>
      <span class="stat-value skip">{stats.by_recommendation.SKIP}</span>
    </div>
  </div>
{/if}

<!-- Analyse manuelle -->
<div class="card">
  <div class="card-header">
    <h2 class="card-title">🎯 Analyser un setup</h2>
  </div>
  <div class="analyze-form">
    <label>
      Symbole
      <input bind:value={form.symbol} placeholder="US30" />
    </label>
    <label>
      Grade
      <select bind:value={form.setup_grade}>
        <option value="A+">A+</option>
        <option value="A">A</option>
        <option value="B">B</option>
        <option value="C">C</option>
      </select>
    </label>
    <label>
      Phase HTF
      <select bind:value={form.htf_phase}>
        <option value="markup">Markup</option>
        <option value="markdown">Markdown</option>
        <option value="accumulation">Accumulation</option>
        <option value="distribution">Distribution</option>
      </select>
    </label>
    <label>
      Direction
      <select bind:value={form.direction}>
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>
    </label>
    <label class="checkbox">
      <input type="checkbox" bind:checked={form.session_active} />
      Session active
    </label>
    <label class="checkbox">
      <input type="checkbox" bind:checked={form.spread_ok} />
      Spread OK
    </label>
    <button class="btn btn-primary" on:click={runAnalysis} disabled={analyzing}>
      {analyzing ? '⏳ Analyse…' : '🚀 Lancer le scoring'}
    </button>
  </div>
  {#if analyzeError}
    <p class="form-error">{analyzeError}</p>
  {/if}
</div>

<!-- Filtres -->
<div class="filters">
  {#each ['ALL', 'TRADE', 'WAIT', 'SKIP'] as f}
    <button class="filter-btn" class:active={filter === f} on:click={() => (filter = f)}>
      {f === 'ALL' ? 'Tout' : f}
    </button>
  {/each}
  <button class="filter-btn refresh" on:click={loadAll} title="Actualiser">🔄</button>
</div>

<!-- Liste des scores -->
{#if loading}
  <div class="state">
    <div class="spinner"></div>
    <p>Chargement des scores…</p>
  </div>
{:else if error}
  <div class="state error">
    <span class="emoji">⚠️</span>
    <p>{error}</p>
    <button class="btn btn-secondary" on:click={loadAll}>Réessayer</button>
  </div>
{:else if filtered.length === 0}
  <div class="state">
    <span class="emoji">📭</span>
    <p>Aucun score à afficher. Lancez une première analyse ci-dessus.</p>
  </div>
{:else}
  <div class="grid grid-2 scores-grid">
    {#each filtered as score (score.generated_at + score.symbol)}
      <ScoreCard {score} />
    {/each}
  </div>
{/if}

<style>
  .stats-row { margin-bottom: 24px; }
  .stat-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .stat-label { font-size: 13px; color: var(--text-muted); }
  .stat-value { font-size: 28px; font-weight: 800; font-family: var(--font-mono); }
  .stat-value small { font-size: 14px; opacity: 0.5; }
  .stat-value.trade { color: var(--success); }
  .stat-value.skip { color: var(--danger); }

  .analyze-form {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    align-items: flex-end;
  }
  .analyze-form label {
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 13px;
    color: var(--text-muted);
  }
  .analyze-form input:not([type]),
  .analyze-form select {
    background: var(--surface-solid);
    border: 1px solid var(--border-strong);
    color: var(--text);
    padding: 9px 12px;
    border-radius: var(--radius-sm);
    font-size: 14px;
    min-width: 130px;
  }
  .analyze-form .checkbox {
    flex-direction: row;
    align-items: center;
    gap: 8px;
    padding-bottom: 9px;
  }
  .form-error { color: var(--danger); font-size: 13px; margin: 12px 0 0; }

  .filters {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }
  .filter-btn {
    background: var(--surface-2);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 8px 18px;
    border-radius: 999px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
  }
  .filter-btn:hover { color: var(--text); border-color: var(--border-strong); }
  .filter-btn.active {
    background: var(--accent-grad-soft);
    color: var(--accent);
    border-color: rgba(34, 211, 238, 0.4);
  }
  .filter-btn.refresh { margin-left: auto; }

  .scores-grid { margin-bottom: 40px; }

  .state {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    padding: 60px 20px;
    color: var(--text-muted);
  }
  .state .emoji { font-size: 44px; }
  .state.error { color: var(--danger); }

  .spinner {
    width: 36px;
    height: 36px;
    border: 3px solid var(--border-strong);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
