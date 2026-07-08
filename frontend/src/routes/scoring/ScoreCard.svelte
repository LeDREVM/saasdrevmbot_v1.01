<script>
  /** @type {any} */
  export let score;

  /** @param {number} s */
  function scoreColor(s) {
    if (s >= 75) return 'var(--success)';
    if (s >= 55) return 'var(--warning)';
    return 'var(--danger)';
  }

  /** @param {string} rec */
  function recBadge(rec) {
    switch (rec) {
      case 'TRADE': return { emoji: '✅', cls: 'rec-trade' };
      case 'WAIT': return { emoji: '⏳', cls: 'rec-wait' };
      case 'SKIP': return { emoji: '❌', cls: 'rec-skip' };
      default: return { emoji: '❓', cls: 'rec-wait' };
    }
  }

  /** @param {string} iso */
  function fmtTime(iso) {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString('fr-FR', {
        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
      });
    } catch { return iso; }
  }

  $: badge = recBadge(score?.recommendation);
  $: pct = Math.max(0, Math.min(100, score?.score ?? 0));
</script>

<div class="score-card">
  <div class="sc-header">
    <div class="sc-symbol">
      <span class="sym">{score.symbol || '?'}</span>
      <span class="grade">Grade {score.setup_grade || '?'}</span>
    </div>
    <span class="rec {badge.cls}">{badge.emoji} {score.recommendation || 'WAIT'}</span>
  </div>

  <div class="sc-gauge">
    <div class="gauge-track">
      <div class="gauge-fill" style="width:{pct}%; background:{scoreColor(pct)}"></div>
    </div>
    <span class="gauge-value" style="color:{scoreColor(pct)}">{pct}<small>/100</small></span>
  </div>

  {#if score.event_context}
    <div class="sc-event">
      📅 {score.event_context.event || score.event_context.event_name || 'Annonce'}
      {#if score.event_context.currency}<span class="cur">{score.event_context.currency}</span>{/if}
    </div>
  {/if}

  {#if score.reasoning}
    <p class="sc-reasoning">{score.reasoning}</p>
  {/if}

  {#if score.risk_factors && score.risk_factors.length}
    <div class="sc-risks">
      {#each score.risk_factors as risk}
        <span class="risk-tag">⚠ {risk}</span>
      {/each}
    </div>
  {/if}

  <div class="sc-footer">
    <span class="ts">{fmtTime(score.generated_at)}</span>
  </div>
</div>

<style>
  .score-card {
    background: var(--surface-solid);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    transition: border-color 0.2s, transform 0.2s;
  }
  .score-card:hover {
    border-color: var(--border-strong);
    transform: translateY(-2px);
  }

  .sc-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .sc-symbol { display: flex; flex-direction: column; gap: 2px; }
  .sym { font-size: 18px; font-weight: 800; font-family: var(--font-mono); }
  .grade { font-size: 12px; color: var(--text-dim); }

  .rec {
    font-size: 13px;
    font-weight: 700;
    padding: 4px 12px;
    border-radius: 999px;
    white-space: nowrap;
  }
  .rec-trade { background: rgba(52,211,153,0.15); color: var(--success); border: 1px solid rgba(52,211,153,0.35); }
  .rec-wait  { background: rgba(251,191,36,0.15); color: var(--warning); border: 1px solid rgba(251,191,36,0.35); }
  .rec-skip  { background: rgba(248,113,113,0.15); color: var(--danger); border: 1px solid rgba(248,113,113,0.35); }

  .sc-gauge { display: flex; align-items: center; gap: 12px; }
  .gauge-track {
    flex: 1;
    height: 10px;
    background: var(--surface-2);
    border-radius: 999px;
    overflow: hidden;
  }
  .gauge-fill { height: 100%; border-radius: 999px; transition: width 0.6s ease; }
  .gauge-value { font-size: 22px; font-weight: 800; font-family: var(--font-mono); min-width: 64px; text-align: right; }
  .gauge-value small { font-size: 12px; opacity: 0.6; }

  .sc-event {
    font-size: 13px;
    color: var(--text-muted);
    background: var(--surface);
    border-radius: var(--radius-sm);
    padding: 8px 12px;
  }
  .cur {
    font-family: var(--font-mono);
    font-size: 11px;
    background: var(--surface-2);
    padding: 1px 6px;
    border-radius: 6px;
    margin-left: 6px;
  }

  .sc-reasoning {
    font-size: 13px;
    line-height: 1.5;
    color: var(--text-muted);
    margin: 0;
    font-style: italic;
  }

  .sc-risks { display: flex; flex-wrap: wrap; gap: 6px; }
  .risk-tag {
    font-size: 11px;
    color: var(--warning);
    background: rgba(251,191,36,0.1);
    padding: 3px 8px;
    border-radius: 6px;
  }

  .sc-footer {
    display: flex;
    justify-content: flex-end;
    border-top: 1px solid var(--border);
    padding-top: 10px;
  }
  .ts { font-size: 11px; color: var(--text-dim); font-family: var(--font-mono); }
</style>
