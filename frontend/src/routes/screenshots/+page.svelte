<script>
  import { onMount } from 'svelte';
  import { supabase, supabaseEnabled } from '$lib/supabase';
  import {
    uploadScreenshot, listScreenshots, getSignedUrls,
    updateScreenshot, linkToTrade, deleteScreenshot
  } from '$lib/screenshots';
  import { runFullAnalysis, listAnalyses, deleteAnalysis } from '$lib/visionApi';

  const sb = /** @type {any} */ (supabase);

  /** @type {any} */ let session = null;
  let email = '';
  let authMsg = '';
  let err = '';
  let busy = false;

  const SYMBOLS = ['XAUUSD', 'US30', 'USDJPY', 'CADJPY', 'USDCAD', 'GBPJPY', 'XTIUSD'];
  const TFS = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'];
  const GRADES = ['A+', 'A', 'B', 'C', 'D'];

  // ── Upload ─────────────────────────────────────────────────────────────
  /** @type {File[]} */ let queue = [];
  let dragOver = false;
  let up = { symbol: 'XAUUSD', timeframe: 'M5', grade: '', note: '', tags: '' };
  let progress = '';

  // ── Galerie ────────────────────────────────────────────────────────────
  /** @type {any[]} */ let shots = [];
  /** @type {Map<string,string>} */ let urls = new Map();
  let filters = { symbol: '', timeframe: '', grade: '', search: '' };
  /** @type {any[]} */ let recentTrades = [];
  /** @type {string|null} */ let linkingId = null;
  /** @type {any} */ let lightbox = null;

  // ── Bot analyse intégrale ──────────────────────────────────────────────
  /** @type {Set<string>} */ let selected = new Set();
  let analyzing = false;
  let analysisContext = '';
  /** @type {any} */ let report = null;        // analyse affichée
  /** @type {any[]} */ let history = [];
  let showHistory = false;

  onMount(async () => {
    if (!supabaseEnabled) return;
    const { data } = await sb.auth.getSession();
    session = data.session;
    sb.auth.onAuthStateChange((/** @type {any} */ _e, /** @type {any} */ s) => {
      session = s; if (s) loadAll();
    });
    if (session) loadAll();
  });

  async function signIn() {
    authMsg = '';
    const { error } = await sb.auth.signInWithOtp({
      email, options: { emailRedirectTo: window.location.href }
    });
    authMsg = error ? 'Erreur : ' + error.message
                    : 'Lien de connexion envoyé — vérifie ta boîte mail.';
  }

  async function loadAll() {
    await Promise.all([loadShots(), loadTrades(), loadHistory()]);
  }

  async function loadShots() {
    err = '';
    const { data, error } = await listScreenshots({
      symbol: filters.symbol || undefined,
      timeframe: filters.timeframe || undefined,
      grade: filters.grade || undefined,
      search: filters.search || undefined
    });
    if (error) { err = error; return; }
    shots = data;
    urls = await getSignedUrls(shots.map((s) => s.storage_path));
  }

  async function loadTrades() {
    const { data } = await sb.from('journal_trades')
      .select('id, trade_date, symbol, direction, result')
      .order('trade_date', { ascending: false }).limit(50);
    recentTrades = data || [];
  }

  async function loadHistory() {
    const { data } = await listAnalyses(30);
    history = data;
  }

  // ── Handlers upload ────────────────────────────────────────────────────
  function pickFiles(/** @type {any} */ e) {
    queue = [...queue, ...Array.from(e.target.files || [])];
    e.target.value = '';
  }
  function onDrop(/** @type {DragEvent} */ e) {
    e.preventDefault(); dragOver = false;
    const files = Array.from(e.dataTransfer?.files || [])
      .filter((f) => f.type.startsWith('image/'));
    queue = [...queue, ...files];
  }
  function removeFromQueue(/** @type {number} */ i) {
    queue = queue.filter((_, idx) => idx !== i);
  }

  async function uploadAll() {
    if (!queue.length) return;
    busy = true; err = ''; progress = '';
    const tags = up.tags.split(',').map((t) => t.trim()).filter(Boolean);
    let ok = 0;
    for (let i = 0; i < queue.length; i++) {
      progress = `Upload ${i + 1}/${queue.length}…`;
      const { error } = await uploadScreenshot(queue[i], {
        symbol: up.symbol, timeframe: up.timeframe,
        grade: up.grade || null, note: up.note || null, tags
      });
      if (error) { err = error; break; }
      ok++;
    }
    progress = ok ? `✅ ${ok} capture(s) ajoutée(s)` : '';
    queue = queue.slice(ok);
    if (!err) up.note = '';
    busy = false;
    await loadShots();
  }

  // ── Handlers galerie ───────────────────────────────────────────────────
  async function doLink(/** @type {any} */ shot, /** @type {string} */ tradeId) {
    const { error } = await linkToTrade(shot, tradeId || null);
    if (error) { err = error; return; }
    linkingId = null;
    await loadShots();
  }

  async function doDelete(/** @type {any} */ shot) {
    if (!confirm('Supprimer définitivement cette capture ?')) return;
    const { error } = await deleteScreenshot(shot);
    if (error) { err = error; return; }
    if (lightbox?.id === shot.id) lightbox = null;
    selected.delete(shot.id); selected = selected;
    await loadShots();
  }

  async function setGrade(/** @type {any} */ shot, /** @type {string} */ g) {
    const grade = shot.grade === g ? null : g;
    const { error } = await updateScreenshot(shot.id, { grade });
    if (error) { err = error; return; }
    shot.grade = grade; shots = shots;
  }

  // ── Handlers bot ───────────────────────────────────────────────────────
  function toggleSelect(/** @type {string} */ id) {
    if (selected.has(id)) selected.delete(id); else selected.add(id);
    selected = selected;
  }

  async function analyze() {
    const picked = shots.filter((s) => selected.has(s.id));
    analyzing = true; err = ''; report = null;
    const { data, error } = await runFullAnalysis(picked, analysisContext);
    analyzing = false;
    if (error) { err = '🤖 ' + error; return; }
    report = data;
    analysisContext = '';
    selected = new Set();
    await loadHistory();
  }

  async function removeAnalysis(/** @type {string} */ id) {
    await deleteAnalysis(id);
    if (report && history.find((h) => h.id === id)?.result === report) report = null;
    await loadHistory();
  }

  const tradeLabel = (/** @type {string} */ id) => {
    const t = recentTrades.find((t) => t.id === id);
    return t ? `${t.trade_date} ${t.symbol} ${t.direction}` : '🔗 lié';
  };
  const fmtDate = (/** @type {string} */ d) =>
    new Date(d).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' });
  const gradeClass = (/** @type {string} */ g) =>
    g ? 'g' + g.replace('+', 'p') : '';
  const actionEmoji = { LONG: '🟢', SHORT: '🔴', WAIT: '⏳', SKIP: '⛔' };
</script>

<svelte:head><title>Captures — DREVM</title></svelte:head>

<main class="wrap">
  <h1>📸 Gestionnaire de captures</h1>

  {#if !supabaseEnabled}
    <p class="notice">Supabase non configuré. Définis <code>VITE_SUPABASE_URL</code> et
      <code>VITE_SUPABASE_ANON_KEY</code> (voir <code>frontend/env.template</code>).</p>
  {:else if !session}
    <section class="card auth">
      <h2>Connexion</h2>
      <p>Reçois un lien magique par e-mail pour accéder à tes captures.</p>
      <div class="row">
        <input type="email" placeholder="ton@email.com" bind:value={email} />
        <button class="btn" on:click={signIn} disabled={!email}>Recevoir le lien</button>
      </div>
      {#if authMsg}<p class="msg">{authMsg}</p>{/if}
    </section>
  {:else}

    {#if err}<p class="notice err">{err}</p>{/if}

    <!-- ── BARRE BOT (visible dès qu'une capture est cochée) ──────────── -->
    {#if selected.size}
      <section class="card botbar">
        <div class="botrow">
          <span class="botcount">🤖 {selected.size} capture(s) sélectionnée(s)</span>
          <input class="ctx" bind:value={analysisContext}
                 placeholder="Contexte optionnel : news du jour, position ouverte…" />
          <button class="btn" on:click={analyze} disabled={analyzing}>
            {analyzing ? '⏳ Analyse en cours…' : '🚀 Analyse intégrale'}
          </button>
          <button class="btn ghost" on:click={() => (selected = new Set())}>✕</button>
        </div>
        <p class="hint">Coche les TF d'un même symbole (ex: D1 + H4 + M5) → rapport DREVM top-down.</p>
      </section>
    {/if}

    <!-- ── RAPPORT ────────────────────────────────────────────────────── -->
    {#if report}
      <section class="card reportcard">
        <div class="rephead">
          <h2>📊 {report._meta?.symbol} — {(report._meta?.timeframes || []).join(' → ')}</h2>
          <div class="repbadges">
            <span class="badge grade {gradeClass(report.grade)}">Grade {report.grade}</span>
            <span class="badge act">{actionEmoji[report.action] || ''} {report.action}</span>
            <span class="badge">{report.bias?.direction} {report.bias?.score}/10</span>
          </div>
          <button class="mini" on:click={() => (report = null)}>✕ Fermer</button>
        </div>

        <p class="repsummary">{report.bias?.summary}</p>

        <div class="repgrid">
          <div class="repblock">
            <h3>🔵 Wyckoff</h3>
            <p><b>{report.wyckoff?.phase}</b>
              {#if report.wyckoff?.events?.length} · {report.wyckoff.events.join(', ')}{/if}
              · aligné : {report.wyckoff?.aligned_with_bias ? '✅' : '❌'}</p>
          </div>
          <div class="repblock">
            <h3>🔴 Structure</h3>
            <p>{report.structure?.trend} · MSS confirmé : {report.structure?.mss_confirmed ? '✅' : '❌'}
              {#if report.structure?.counter_trend} · ⚠️ contre-tendance{/if}</p>
            {#if report.structure?.key_levels?.length}
              <p class="lvls">{report.structure.key_levels.join(' · ')}</p>{/if}
          </div>
          <div class="repblock">
            <h3>🟡 ICT/SMC</h3>
            <p>{report.ict_smc?.fvg || ''} {report.ict_smc?.order_blocks || ''}</p>
            <p>{report.ict_smc?.liquidity || ''} · prix en zone : {report.ict_smc?.price_in_zone ? '✅' : '❌'}</p>
          </div>
          <div class="repblock">
            <h3>🎯 Fibonacci sniper</h3>
            <p>{report.fibonacci?.swing || ''} · {report.fibonacci?.sniper_zone || ''}
              · en zone : {report.fibonacci?.in_sniper_zone ? '✅' : '❌'}</p>
          </div>
        </div>

        {#if report.per_timeframe?.length}
          <div class="repblock">
            <h3>🔭 Lecture par timeframe</h3>
            {#each report.per_timeframe as tf}
              <p><b>{tf.timeframe}</b> — {tf.read}</p>
            {/each}
          </div>
        {/if}

        {#if report.confluences?.length}
          <div class="repblock">
            <h3>✅ Confluences validées</h3>
            <p>{report.confluences.join(' · ')}</p>
          </div>
        {/if}

        {#if report.trade_plan?.entry}
          <div class="repblock plan">
            <h3>📋 Plan</h3>
            <p><b>Entry</b> {report.trade_plan.entry} · <b>SL</b> {report.trade_plan.sl}
               · <b>TP1</b> {report.trade_plan.tp1} ({report.trade_plan.rr1}R)
               {#if report.trade_plan.tp2}· <b>TP2</b> {report.trade_plan.tp2} ({report.trade_plan.rr2}R){/if}</p>
            {#if report.trade_plan.trigger}<p>🎬 Trigger : {report.trade_plan.trigger}</p>{/if}
          </div>
        {/if}

        <div class="repblock">
          <h3>⚠️ Invalidation</h3>
          <p>{report.invalidation}</p>
          {#if report.news_risk}<p>📅 News : {report.news_risk}</p>{/if}
        </div>

        {#if report.warnings?.length}
          <div class="repblock warn">
            {#each report.warnings as w}<p>🚨 {w}</p>{/each}
          </div>
        {/if}
      </section>
    {/if}

    <!-- ── UPLOAD ─────────────────────────────────────────────────────── -->
    <section class="card">
      <h2>Ajouter des captures</h2>
      <div
        class="dropzone" class:over={dragOver}
        role="button" tabindex="0"
        on:dragover|preventDefault={() => (dragOver = true)}
        on:dragleave={() => (dragOver = false)}
        on:drop={onDrop}
      >
        <p>🖼️ Glisse tes captures ici, ou</p>
        <label class="btn ghost filepick">
          Choisir des fichiers
          <input type="file" accept="image/*" multiple on:change={pickFiles} hidden />
        </label>
        {#if queue.length}
          <ul class="queue">
            {#each queue as f, i}
              <li>{f.name} <span class="sz">({Math.round(f.size / 1024)} Ko)</span>
                <button class="mini" on:click={() => removeFromQueue(i)}>✕</button></li>
            {/each}
          </ul>
        {/if}
      </div>

      <div class="grid">
        <label>Symbole
          <select bind:value={up.symbol}>
            {#each SYMBOLS as s}<option value={s}>{s}</option>{/each}
          </select>
        </label>
        <label>Timeframe
          <select bind:value={up.timeframe}>
            {#each TFS as t}<option value={t}>{t}</option>{/each}
          </select>
        </label>
        <label>Grade
          <select bind:value={up.grade}>
            <option value="">—</option>
            {#each GRADES as g}<option value={g}>{g}</option>{/each}
          </select>
        </label>
        <label>Tags (virgules)
          <input bind:value={up.tags} placeholder="sweep, mss, ny-open" />
        </label>
        <label class="wide">Note
          <input bind:value={up.note} placeholder="Contexte, setup, remarque…" />
        </label>
      </div>
      <div class="row">
        <button class="btn" on:click={uploadAll} disabled={busy || !queue.length}>
          {busy ? '⏳ Upload…' : `Uploader ${queue.length || ''} capture(s)`}
        </button>
        {#if progress}<span class="msg">{progress}</span>{/if}
      </div>
    </section>

    <!-- ── FILTRES + HISTORIQUE ───────────────────────────────────────── -->
    <section class="card">
      <div class="grid filters">
        <label>Symbole
          <select bind:value={filters.symbol} on:change={loadShots}>
            <option value="">Tous</option>
            {#each SYMBOLS as s}<option value={s}>{s}</option>{/each}
          </select>
        </label>
        <label>Timeframe
          <select bind:value={filters.timeframe} on:change={loadShots}>
            <option value="">Tous</option>
            {#each TFS as t}<option value={t}>{t}</option>{/each}
          </select>
        </label>
        <label>Grade
          <select bind:value={filters.grade} on:change={loadShots}>
            <option value="">Tous</option>
            {#each GRADES as g}<option value={g}>{g}</option>{/each}
          </select>
        </label>
        <label>Recherche note
          <input bind:value={filters.search} on:change={loadShots} placeholder="mot-clé…" />
        </label>
      </div>
      <button class="mini" on:click={() => (showHistory = !showHistory)}>
        🕘 Historique analyses ({history.length}) {showHistory ? '▲' : '▼'}
      </button>
      {#if showHistory}
        <div class="tblwrap">
          <table>
            <thead><tr><th>Date</th><th>Symbole</th><th>TF</th><th>Grade</th><th>Action</th><th>Biais</th><th></th></tr></thead>
            <tbody>
              {#each history as h}
                <tr>
                  <td>{fmtDate(h.created_at)}</td>
                  <td>{h.symbol}</td>
                  <td>{(h.timeframes || []).join('→')}</td>
                  <td><span class="badge grade {gradeClass(h.grade)}">{h.grade}</span></td>
                  <td>{actionEmoji[h.action] || ''} {h.action}</td>
                  <td>{h.bias_direction} {h.bias_score}/10</td>
                  <td class="rowactions">
                    <button class="mini" on:click={() => (report = h.result)}>👁</button>
                    <button class="mini danger" on:click={() => removeAnalysis(h.id)}>🗑</button>
                  </td>
                </tr>
              {:else}
                <tr><td colspan="7" class="empty">Aucune analyse</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <!-- ── GALERIE ────────────────────────────────────────────────────── -->
    <section class="gallery">
      {#each shots as s (s.id)}
        <article class="shot card" class:sel={selected.has(s.id)}>
          <label class="selbox">
            <input type="checkbox" checked={selected.has(s.id)}
                   on:change={() => toggleSelect(s.id)} /> 🤖
          </label>
          <button class="thumbwrap" on:click={() => (lightbox = s)}>
            {#if urls.get(s.storage_path)}
              <img src={urls.get(s.storage_path)} alt={s.note || s.symbol || 'capture'} loading="lazy" />
            {:else}
              <div class="thumb-missing">🖼️</div>
            {/if}
          </button>
          <div class="meta">
            <div class="badges">
              {#if s.symbol}<span class="badge sym">{s.symbol}</span>{/if}
              {#if s.timeframe}<span class="badge tf">{s.timeframe}</span>{/if}
              {#if s.grade}<span class="badge grade {gradeClass(s.grade)}">{s.grade}</span>{/if}
              {#if s.trade_id}<span class="badge linked" title={tradeLabel(s.trade_id)}>🔗</span>{/if}
            </div>
            <p class="date">{fmtDate(s.taken_at)}</p>
            {#if s.note}<p class="note">{s.note}</p>{/if}
            {#if s.tags?.length}
              <p class="tags">{#each s.tags as t}<span>#{t}</span>{/each}</p>
            {/if}
            <div class="grades">
              {#each GRADES as g}
                <button class="gbtn {gradeClass(g)}" class:on={s.grade === g}
                        on:click={() => setGrade(s, g)}>{g}</button>
              {/each}
            </div>
            <div class="actions">
              {#if linkingId === s.id}
                <select on:change={(e) => doLink(s, /** @type {any} */ (e.target).value)}>
                  <option value="">— délier —</option>
                  {#each recentTrades as t}
                    <option value={t.id} selected={t.id === s.trade_id}>
                      {t.trade_date} {t.symbol} {t.direction} ({t.result})
                    </option>
                  {/each}
                </select>
                <button class="mini" on:click={() => (linkingId = null)}>✕</button>
              {:else}
                <button class="mini" on:click={() => (linkingId = s.id)}>🔗 Trade</button>
                <button class="mini danger" on:click={() => doDelete(s)}>🗑</button>
              {/if}
            </div>
          </div>
        </article>
      {:else}
        <p class="notice">Aucune capture{filters.symbol || filters.grade ? ' avec ces filtres' : ''}. 📭</p>
      {/each}
    </section>

    <!-- ── LIGHTBOX ───────────────────────────────────────────────────── -->
    {#if lightbox}
      <button class="lightbox" on:click={() => (lightbox = null)} aria-label="Fermer">
        <img src={urls.get(lightbox.storage_path)} alt={lightbox.note || 'capture'} />
        <p>{lightbox.symbol || ''} {lightbox.timeframe || ''}
           {lightbox.grade ? '· Grade ' + lightbox.grade : ''} · {fmtDate(lightbox.taken_at)}</p>
      </button>
    {/if}
  {/if}
</main>

<style>
  .wrap { max-width: 1100px; margin: 0 auto; padding: 20px; color: #e6edf3; }
  h1 { font-size: 22px; margin-bottom: 16px; }
  h2 { font-size: 15px; margin: 0 0 12px; }
  h3 { font-size: 13px; margin: 0 0 6px; color: #8b949e; }
  .card { background: #161b22; border: 1px solid #2a313c; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
  .notice { background: #1c232c; border: 1px solid #2a313c; border-radius: 8px; padding: 12px; }
  .notice.err { border-color: #da3633; color: #ff8a80; }
  .row { display: flex; gap: 8px; align-items: center; }
  input, select { background: #0d1117; border: 1px solid #2a313c; color: #e6edf3; border-radius: 6px; padding: 8px 10px; font: inherit; }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #8b949e; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 12px; }
  .grid label.wide { grid-column: 1 / -1; }
  .btn { background: #2ea043; border: none; color: #fff; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; }
  .btn.ghost { background: transparent; border: 1px solid #2a313c; color: #8b949e; }
  .btn:disabled { opacity: .5; cursor: default; }
  .mini { background: #1c232c; border: 1px solid #2a313c; color: #2f81f7; border-radius: 5px; padding: 2px 8px; cursor: pointer; }
  .mini.danger { color: #ff8a80; }
  .msg { color: #2ea043; font-size: 13px; }
  .tblwrap { overflow-x: auto; margin-top: 10px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: #8b949e; font-weight: 500; padding: 6px 8px; border-bottom: 1px solid #2a313c; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a313c; }
  td.empty { text-align: center; color: #8b949e; padding: 16px; }
  .rowactions { display: flex; gap: 4px; }

  /* Bot bar */
  .botbar { position: sticky; top: 8px; z-index: 20; border-color: #2f81f7; }
  .botrow { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .botcount { font-weight: 700; color: #2f81f7; }
  .ctx { flex: 1; min-width: 200px; }
  .hint { font-size: 11px; color: #8b949e; margin: 8px 0 0; }

  /* Rapport */
  .reportcard { border-color: #2f81f7; }
  .rephead { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 8px; }
  .rephead h2 { margin: 0; flex: 1; }
  .repbadges { display: flex; gap: 6px; }
  .badge.act { color: #e6edf3; font-weight: 700; }
  .repsummary { font-size: 14px; margin: 4px 0 12px; }
  .repgrid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px; margin-bottom: 10px; }
  .repblock { background: #0d1117; border: 1px solid #2a313c; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; font-size: 13px; }
  .repblock p { margin: 3px 0; }
  .repblock.plan { border-color: #2ea043; }
  .repblock.warn { border-color: #da3633; color: #ff8a80; }
  .lvls { color: #8b949e; }

  .dropzone { border: 2px dashed #2a313c; border-radius: 10px; padding: 20px; text-align: center; margin-bottom: 12px; transition: border-color .15s; }
  .dropzone.over { border-color: #2ea043; background: #14201a; }
  .filepick { display: inline-block; margin-top: 6px; }
  .queue { list-style: none; padding: 0; margin: 12px 0 0; font-size: 13px; text-align: left; }
  .queue li { display: flex; gap: 8px; align-items: center; padding: 3px 0; }
  .sz { color: #8b949e; }

  .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px; }
  .shot { padding: 0; overflow: hidden; margin-bottom: 0; position: relative; }
  .shot.sel { border-color: #2f81f7; box-shadow: 0 0 0 1px #2f81f7; }
  .selbox { position: absolute; top: 8px; left: 8px; z-index: 2; flex-direction: row; align-items: center; gap: 4px;
            background: rgba(13,17,23,.85); border: 1px solid #2a313c; border-radius: 6px; padding: 3px 7px; cursor: pointer; }
  .thumbwrap { display: block; width: 100%; aspect-ratio: 16/9; background: #0d1117; border: none; padding: 0; cursor: zoom-in; }
  .thumbwrap img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .thumb-missing { display: grid; place-items: center; height: 100%; font-size: 28px; }
  .meta { padding: 10px 12px 12px; }
  .badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 4px; }
  .badge { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: #1c232c; border: 1px solid #2a313c; }
  .badge.sym { color: #2f81f7; }
  .badge.tf  { color: #8b949e; }
  .badge.linked { color: #d2a8ff; }
  .badge.grade.gAp { background: #3d2f00; color: #ffd700; border-color: #ffd700; }
  .badge.grade.gA  { background: #14301c; color: #2ea043; border-color: #2ea043; }
  .badge.grade.gB  { background: #33300f; color: #d4c220; border-color: #d4c220; }
  .badge.grade.gC  { background: #35230d; color: #f0883e; border-color: #f0883e; }
  .badge.grade.gD  { background: #33110f; color: #da3633; border-color: #da3633; }
  .date { font-size: 11px; color: #8b949e; margin: 2px 0; }
  .note { font-size: 13px; margin: 4px 0; }
  .tags { display: flex; gap: 6px; flex-wrap: wrap; font-size: 11px; color: #2f81f7; margin: 2px 0 6px; }
  .grades { display: flex; gap: 4px; margin: 6px 0; }
  .gbtn { font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 5px; background: #0d1117; border: 1px solid #2a313c; color: #8b949e; cursor: pointer; }
  .gbtn.on.gAp { color: #ffd700; border-color: #ffd700; }
  .gbtn.on.gA  { color: #2ea043; border-color: #2ea043; }
  .gbtn.on.gB  { color: #d4c220; border-color: #d4c220; }
  .gbtn.on.gC  { color: #f0883e; border-color: #f0883e; }
  .gbtn.on.gD  { color: #da3633; border-color: #da3633; }
  .actions { display: flex; gap: 6px; align-items: center; }
  .actions select { font-size: 12px; padding: 4px 6px; max-width: 200px; }

  .lightbox { position: fixed; inset: 0; background: rgba(0,0,0,.88); border: none; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; cursor: zoom-out; z-index: 50; padding: 20px; }
  .lightbox img { max-width: 95vw; max-height: 85vh; border-radius: 8px; }
  .lightbox p { color: #e6edf3; font-size: 13px; }
</style>
