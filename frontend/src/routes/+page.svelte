<script>
  import { onMount } from 'svelte';
  import TradingEconomicsWidget from './TradingEconomicsWidget.svelte';
  import TradingViewPanel from '$lib/components/TradingViewPanel.svelte';
  import { API_URL, API_ENDPOINTS } from '$lib/config.js';
  import { requestJSON, guadeloupeTime } from '$lib/api-client.js';
  let backend = 'Vérification';
  let sync = 'Vérification';
  let ai = 'Vérification';
  /** @type {any} */ let scores = null;
  /** @type {any} */ let latest = null;
  let error = '';
  let updated = '';
  let refreshing = false;
  let now = new Date();
  $: localClock = now.toLocaleTimeString('fr-FR', { timeZone: 'America/Guadeloupe' });
  $: ny = new Intl.DateTimeFormat('en-US', { timeZone: 'America/New_York',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23', weekday: 'short' }).formatToParts(now);
  $: nyHour = Number(ny.find(p => p.type === 'hour')?.value || 0);
  $: nyMinute = Number(ny.find(p => p.type === 'minute')?.value || 0);
  $: weekday = ny.find(p => p.type === 'weekday')?.value || '';
  $: session = !['Sat', 'Sun'].includes(weekday) && nyHour * 60 + nyMinute >= 570 && nyHour < 16;
  // Convert NY opening to Guadeloupe using today's actual offset (DST-aware).
  $: localHour = Number(new Intl.DateTimeFormat('en-US', { timeZone: 'America/Guadeloupe', hour: '2-digit', hourCycle: 'h23' }).format(now));
  $: offset = (localHour - nyHour + 24) % 24;
  $: openHour = (9 + offset) % 24;
  $: closeHour = (16 + offset) % 24;

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    error = '';
    const results = await Promise.allSettled([
      requestJSON(`${API_URL}/health`), requestJSON(`${API_URL}/api/nextcloud/status`),
      requestJSON(API_ENDPOINTS.scoringStats), requestJSON(`${API_ENDPOINTS.scoringHistory}?limit=1`),
      requestJSON(`${API_URL}/api/scoring/status`)
    ]);
    backend = results[0].status === 'fulfilled' ? 'En ligne' : 'Indisponible';
    sync = results[1].status === 'fulfilled' ? (results[1].value.connected ? 'Connectée' : 'Non connectée') : 'Indisponible';
    if (results[2].status === 'fulfilled') { scores = results[2].value; updated = new Date().toISOString(); }
    else error = 'Statistiques indisponibles. Les dernières données restent affichées.';
    if (results[3].status === 'fulfilled') latest = results[3].value.scores?.[0] || null;
    ai = results[4].status === 'fulfilled' ? (results[4].value.configured ? 'Local · à la demande' : 'Non configuré') : 'Indisponible';
    refreshing = false;
  }
  onMount(() => {
    refresh();
    const clock = setInterval(() => { now = new Date(); }, 1000);
    const poll = setInterval(refresh, 60000);
    return () => { clearInterval(clock); clearInterval(poll); };
  });
</script>

<svelte:head><title>DREVM — Tableau de bord NY</title><meta name="description" content="Tableau de bord de trading New York : marchés, calendrier et scoring IA à la demande." /></svelte:head>

<div class="dashboard">
  <header>
    <div><p class="eyebrow">DREVM / SESSION NEW YORK</p><h1>Ton espace de décision.</h1><p class="muted">H4 pour le biais · M15 pour la zone · M5 pour la confirmation</p></div>
    <div class="clock"><strong>{localClock}</strong><span>Guadeloupe · UTC−4</span></div>
  </header>
  <section class="session" aria-label="Horaires de la session">
    <div><span class="dot" class:active={session}></span><strong>{session ? 'Plage NY ouverte' : 'Hors plage NY'}</strong><span class="muted">{openHour}h30–{closeHour}h00 en Guadeloupe · hors jours fériés</span></div>
    <a href="/scoring" class="primary">Analyser un setup →</a>
  </section>
  <div class="metrics">
    <article><span>Analyses enregistrées</span><strong>{scores?.total ?? '—'}</strong></article>
    <article><span>Score moyen enregistré</span><strong>{scores?.total ? `${scores.avg_score}/100` : '—'}</strong></article>
    <article><span>Avis WAIT</span><strong>{scores?.by_recommendation?.WAIT ?? '—'}</strong></article>
    <article><span>Dernière analyse</span><strong class="small">{latest?.symbol || 'Aucune'}</strong><span>{latest ? guadeloupeTime(latest.generated_at) : 'Lance une analyse à la demande'}</span></article>
  </div>
  <div class="refresh"><p class="muted" role="status">{error || `Actualisé ${guadeloupeTime(updated)} · scoring local à la demande`}</p><button on:click={refresh} disabled={refreshing}>{refreshing ? 'Actualisation…' : 'Actualiser'}</button></div>
  <section class="workspace" aria-label="Marchés et calendrier"><TradingViewPanel /><TradingEconomicsWidget /></section>
  <section class="bottom" aria-label="Espace de trading">
    <article><p class="eyebrow">JOURNAL PERSONNEL</p><h2>Suivre tes décisions</h2><p class="muted">Trades H4 / M15 / M5, résultats en R et export CSV.</p><nav><a href="/journal">Ouvrir le journal</a></nav></article>
    <article><p class="eyebrow">ALERTES PERSONNELLES</p><h2>Préparer la session NY</h2><p class="muted">Calendrier économique et préférences réservées à ton compte.</p><nav><a href="/alerts">Mes alertes</a><a href="/calendar">Voir le calendrier</a></nav></article>
  </section>
  <section class="bottom">
    <article class="checklist"><p class="eyebrow">AVANT LA DÉCISION</p><h2>Trois confirmations</h2><ol><li>Biais et structure H4</li><li>Zone M15 et liquidité</li><li>Sweep, réintégration et confirmation M5</li></ol><p class="muted">Le scoring local repose sur le contexte que tu renseignes.</p></article>
    <article><p class="eyebrow">SERVICES</p><dl><div><dt>Backend</dt><dd>{backend}</dd></div><div><dt>Scoring</dt><dd>{ai}</dd></div><div><dt>Synchronisation</dt><dd>{sync}</dd></div></dl><nav><a href="/calendar">Calendrier</a><a href="/scoring">Historique des scores</a><a href="/alerts">Alertes</a></nav></article>
  </section>
</div>

<style>
  .dashboard{max-width:1440px;margin:auto;padding:28px;display:grid;gap:22px}header{display:flex;justify-content:space-between;align-items:center;gap:20px}h1{font-size:clamp(1.8rem,3vw,2.8rem);letter-spacing:-.04em;margin:8px 0}h2{font-size:1.2rem;margin:12px 0}.eyebrow{font-size:11px;letter-spacing:.16em;color:var(--accent);font-weight:700}.muted{color:var(--text-muted);font-size:13px}.clock{display:grid;text-align:right;gap:4px}.clock strong{font:700 26px var(--font-mono)}.clock span{font-size:12px;color:var(--text-muted)}.session{padding:18px 22px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface);display:flex;justify-content:space-between;align-items:center;gap:20px}.session>div{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.dot{width:8px;height:8px;border-radius:50%;background:var(--text-muted)}.dot.active{background:var(--success)}.primary{background:var(--accent-grad);color:white;border-radius:8px;padding:11px 18px;text-decoration:none;font-weight:700;white-space:nowrap}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}article{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:22px}.metrics article{display:grid;gap:8px}.metrics span{font-size:12px;color:var(--text-muted)}.metrics strong{font:700 30px var(--font-mono)}.metrics strong.small{font-size:21px}.refresh{display:flex;justify-content:space-between;align-items:center;gap:12px}.refresh button{padding:8px 14px;background:var(--surface);border:1px solid var(--border);border-radius:8px;color:var(--text);cursor:pointer}.workspace{display:grid;grid-template-columns:1.2fr 1fr;gap:20px;align-items:start;min-width:0}.workspace :global(>*){min-width:0}.bottom{display:grid;grid-template-columns:1fr 1fr;gap:20px}ol{padding-left:20px;color:var(--text-muted);font-size:14px;line-height:2}dl>div{display:flex;justify-content:space-between;border-bottom:1px solid var(--border);padding:12px 0;font-size:13px}dt{color:var(--text-muted)}dd{margin:0}nav{display:flex;gap:18px;margin-top:18px}nav a{color:var(--accent);font-size:13px}@media(max-width:900px){.workspace,.bottom{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.dashboard{padding:16px}header{align-items:flex-start}.clock strong{font-size:18px}.session{align-items:flex-start;flex-direction:column}.metrics article{padding:16px}.metrics strong{font-size:24px}.refresh{align-items:flex-start}}
</style>
