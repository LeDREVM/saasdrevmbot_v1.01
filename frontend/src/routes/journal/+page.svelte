<script>
  import { onMount } from 'svelte';
  import { supabase, supabaseEnabled, SCREENSHOT_BUCKET } from '$lib/supabase';

  // Réf castée : les appels sont gardés par supabaseEnabled/session.
  const sb = /** @type {any} */ (supabase);

  /** @type {any} */ let session = null;
  let email = '';
  let authMsg = '';
  let tab = 'trades';
  let err = '';

  /** @type {any} */ let stats = null;
  /** @type {any[]} */ let trades = [];
  /** @type {any[]} */ let sessions = [];
  /** @type {any} */ let rules = null;
  /** @type {any[]} */ let alerts = [];

  const RULES_DEFAULT = {
    risk_per_day_pct: 3, max_trades_per_day: 3,
    drawdown_lock_pct: 4, drawdown_locked: false, risk_per_trade_pct: 1
  };

  const today = () => new Date().toISOString().slice(0, 10);
  let nt = blankTrade();
  /** @type {any} */ let ntFile = null;
  let ns = { session_date: today(), bias: '', news: '', comment: '' };
  let na = { event: '', impact: 'medium', alert_time: '', currency: '', note: '' };

  function blankTrade() {
    return { symbol: 'XAUUSD', direction: 'buy', entry: '', sl: '', tp: '',
             result: 'running', r_multiple: '', notes: '' };
  }
  const num = (/** @type {any} */ v) => (v === '' || v === null || v === undefined ? null : Number(v));

  onMount(async () => {
    if (!supabaseEnabled) return;
    const { data } = await sb.auth.getSession();
    session = data.session;
    sb.auth.onAuthStateChange((/** @type {any} */ _e, /** @type {any} */ s) => { session = s; if (s) loadAll(); });
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
  async function signOut() {
    await sb.auth.signOut();
    trades = []; sessions = []; alerts = []; rules = null; stats = null;
  }

  async function loadAll() {
    await Promise.all([loadStats(), loadTrades(), loadSessions(), loadRules(), loadAlerts()]);
  }
  async function loadStats() {
    const { data } = await sb.from('journal_stats').select('*').maybeSingle();
    stats = data;
  }
  async function loadTrades() {
    const { data, error } = await sb.from('journal_trades').select('*')
      .order('trade_date', { ascending: false }).limit(200);
    if (error) err = error.message;
    trades = data || [];
  }
  async function loadSessions() {
    const { data } = await sb.from('journal_sessions').select('*')
      .order('session_date', { ascending: false }).limit(100);
    sessions = data || [];
  }
  async function loadRules() {
    const { data } = await sb.from('journal_rules').select('*').maybeSingle();
    rules = data || { ...RULES_DEFAULT };
  }
  async function loadAlerts() {
    const { data } = await sb.from('journal_alerts').select('*')
      .order('alert_time', { ascending: false }).limit(100);
    alerts = data || [];
  }

  async function addTrade() {
    err = '';
    const uid = session.user.id;
    /** @type {string[]} */ let screenshots = [];
    if (ntFile) {
      const path = `${uid}/${crypto.randomUUID()}-${ntFile.name}`;
      const { error: upErr } = await sb.storage.from(SCREENSHOT_BUCKET).upload(path, ntFile);
      if (upErr) { err = 'Upload : ' + upErr.message; return; }
      screenshots = [path];
    }
    const row = {
      user_id: uid, symbol: nt.symbol, direction: nt.direction,
      entry: num(nt.entry), sl: num(nt.sl), tp: num(nt.tp),
      result: nt.result, r_multiple: num(nt.r_multiple), notes: nt.notes, screenshots
    };
    const { error } = await sb.from('journal_trades').insert(row);
    if (error) { err = error.message; return; }
    nt = blankTrade(); ntFile = null;
    await Promise.all([loadTrades(), loadStats()]);
  }

  async function addSession() {
    const { error } = await sb.from('journal_sessions')
      .insert({ user_id: session.user.id, ...ns });
    if (error) { err = error.message; return; }
    ns = { session_date: today(), bias: '', news: '', comment: '' };
    loadSessions();
  }
  async function addAlert() {
    const { error } = await sb.from('journal_alerts').insert({
      user_id: session.user.id, event: na.event, impact: na.impact,
      alert_time: na.alert_time, currency: na.currency, note: na.note
    });
    if (error) { err = error.message; return; }
    na = { event: '', impact: 'medium', alert_time: '', currency: '', note: '' };
    loadAlerts();
  }
  async function saveRules() {
    const { error } = await sb.from('journal_rules').upsert({
      user_id: session.user.id,
      risk_per_day_pct: num(rules.risk_per_day_pct),
      max_trades_per_day: num(rules.max_trades_per_day),
      drawdown_lock_pct: num(rules.drawdown_lock_pct),
      drawdown_locked: rules.drawdown_locked,
      risk_per_trade_pct: num(rules.risk_per_trade_pct)
    }, { onConflict: 'user_id' });
    if (error) { err = error.message; return; }
    loadRules();
  }

  async function openShot(/** @type {string} */ path) {
    const { data } = await sb.storage.from(SCREENSHOT_BUCKET).createSignedUrl(path, 3600);
    if (data?.signedUrl) window.open(data.signedUrl, '_blank');
  }
</script>

<svelte:head><title>Journal — DREVM</title></svelte:head>

<main class="wrap">
  <h1>📓 Journal de trading</h1>

  {#if !supabaseEnabled}
    <p class="notice">Supabase non configuré. Définis <code>VITE_SUPABASE_URL</code> et
      <code>VITE_SUPABASE_ANON_KEY</code> (voir <code>frontend/env.template</code>).</p>
  {:else if !session}
    <section class="card auth">
      <h2>Connexion</h2>
      <p>Reçois un lien magique par e-mail pour accéder à ton journal.</p>
      <div class="row">
        <input type="email" placeholder="ton@email.com" bind:value={email} />
        <button class="btn" on:click={signIn} disabled={!email}>Recevoir le lien</button>
      </div>
      {#if authMsg}<p class="msg">{authMsg}</p>{/if}
    </section>
  {:else}
    <div class="topbar">
      {#if stats}
        <div class="stats">
          <span><b>{stats.trades ?? 0}</b> trades</span>
          <span>Winrate <b>{stats.winrate_pct ?? '—'}%</b></span>
          <span>R total <b class:pos={(stats.total_r ?? 0) >= 0} class:neg={(stats.total_r ?? 0) < 0}>{stats.total_r ?? 0}</b></span>
          <span>PF <b>{stats.profit_factor ?? '—'}</b></span>
        </div>
      {/if}
      <button class="btn ghost" on:click={signOut}>Déconnexion</button>
    </div>

    <nav class="tabs">
      {#each [['trades','Trades'],['sessions','Sessions'],['rules','Règles'],['alerts','Alertes']] as [k, label]}
        <button class:active={tab === k} on:click={() => (tab = k)}>{label}</button>
      {/each}
    </nav>

    {#if err}<p class="notice err">{err}</p>{/if}

    {#if tab === 'trades'}
      <section class="card">
        <h2>Nouveau trade</h2>
        <div class="grid">
          <label>Symbole <input bind:value={nt.symbol} /></label>
          <label>Sens
            <select bind:value={nt.direction}><option value="buy">BUY</option><option value="sell">SELL</option></select>
          </label>
          <label>Entrée <input type="number" step="any" bind:value={nt.entry} /></label>
          <label>SL <input type="number" step="any" bind:value={nt.sl} /></label>
          <label>TP <input type="number" step="any" bind:value={nt.tp} /></label>
          <label>Résultat
            <select bind:value={nt.result}>
              <option value="running">running</option><option value="win">win</option>
              <option value="loss">loss</option><option value="breakeven">breakeven</option>
            </select>
          </label>
          <label>R <input type="number" step="any" bind:value={nt.r_multiple} /></label>
          <label>Capture <input type="file" accept="image/*" on:change={(e) => (ntFile = (/** @type {HTMLInputElement} */ (e.currentTarget)).files?.[0])} /></label>
          <label class="wide">Notes <input bind:value={nt.notes} /></label>
        </div>
        <button class="btn" on:click={addTrade}>Ajouter</button>
      </section>

      <section class="card">
        <h2>Trades ({trades.length})</h2>
        <div class="tblwrap">
          <table>
            <thead><tr><th>Date</th><th>Symbole</th><th>Sens</th><th>Entrée</th><th>SL</th><th>TP</th><th>Résultat</th><th>R</th><th>📷</th></tr></thead>
            <tbody>
              {#each trades as t}
                <tr>
                  <td>{t.trade_date}</td><td>{t.symbol}</td>
                  <td class:pos={t.direction === 'buy'} class:neg={t.direction === 'sell'}>{t.direction}</td>
                  <td>{t.entry ?? ''}</td><td>{t.sl ?? ''}</td><td>{t.tp ?? ''}</td>
                  <td>{t.result}</td>
                  <td class:pos={(t.r_multiple ?? 0) > 0} class:neg={(t.r_multiple ?? 0) < 0}>{t.r_multiple ?? ''}</td>
                  <td>{#if t.screenshots?.length}<button class="mini" on:click={() => openShot(t.screenshots[0])}>voir</button>{/if}</td>
                </tr>
              {:else}
                <tr><td colspan="9" class="empty">Aucun trade</td></tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>

    {:else if tab === 'sessions'}
      <section class="card">
        <h2>Nouvelle session</h2>
        <div class="grid">
          <label>Date <input type="date" bind:value={ns.session_date} /></label>
          <label>Biais <input bind:value={ns.bias} placeholder="bullish / bearish / neutral" /></label>
          <label class="wide">News <input bind:value={ns.news} /></label>
          <label class="wide">Commentaire <input bind:value={ns.comment} /></label>
        </div>
        <button class="btn" on:click={addSession}>Ajouter</button>
      </section>
      <section class="card">
        <h2>Sessions ({sessions.length})</h2>
        <div class="tblwrap"><table>
          <thead><tr><th>Date</th><th>Biais</th><th>News</th><th>Commentaire</th></tr></thead>
          <tbody>
            {#each sessions as s}
              <tr><td>{s.session_date}</td><td>{s.bias ?? ''}</td><td>{s.news ?? ''}</td><td>{s.comment ?? ''}</td></tr>
            {:else}<tr><td colspan="4" class="empty">Aucune session</td></tr>{/each}
          </tbody>
        </table></div>
      </section>

    {:else if tab === 'rules'}
      <section class="card">
        <h2>Règles de risque</h2>
        {#if rules}
          <div class="grid">
            <label>Risque / jour (%) <input type="number" step="any" bind:value={rules.risk_per_day_pct} /></label>
            <label>Risque / trade (%) <input type="number" step="any" bind:value={rules.risk_per_trade_pct} /></label>
            <label>Max trades / jour <input type="number" bind:value={rules.max_trades_per_day} /></label>
            <label>Drawdown lock (%) <input type="number" step="any" bind:value={rules.drawdown_lock_pct} /></label>
            <label class="chk"><input type="checkbox" bind:checked={rules.drawdown_locked} /> Verrouillé (DD atteint)</label>
          </div>
          <button class="btn" on:click={saveRules}>Enregistrer</button>
        {/if}
      </section>

    {:else if tab === 'alerts'}
      <section class="card">
        <h2>Nouvelle alerte</h2>
        <div class="grid">
          <label>Événement <input bind:value={na.event} /></label>
          <label>Impact
            <select bind:value={na.impact}><option value="low">low</option><option value="medium">medium</option><option value="high">high</option></select>
          </label>
          <label>Heure <input type="datetime-local" bind:value={na.alert_time} /></label>
          <label>Devise <input bind:value={na.currency} placeholder="USD" /></label>
          <label class="wide">Note <input bind:value={na.note} /></label>
        </div>
        <button class="btn" on:click={addAlert} disabled={!na.event || !na.alert_time}>Ajouter</button>
      </section>
      <section class="card">
        <h2>Alertes ({alerts.length})</h2>
        <div class="tblwrap"><table>
          <thead><tr><th>Heure</th><th>Événement</th><th>Impact</th><th>Devise</th><th>Note</th></tr></thead>
          <tbody>
            {#each alerts as a}
              <tr><td>{a.alert_time}</td><td>{a.event}</td>
                <td class:high={a.impact === 'high'}>{a.impact}</td><td>{a.currency ?? ''}</td><td>{a.note ?? ''}</td></tr>
            {:else}<tr><td colspan="5" class="empty">Aucune alerte</td></tr>{/each}
          </tbody>
        </table></div>
      </section>
    {/if}
  {/if}
</main>

<style>
  .wrap { max-width: 1000px; margin: 0 auto; padding: 20px; color: #e6edf3; }
  h1 { font-size: 22px; margin-bottom: 16px; }
  h2 { font-size: 15px; margin: 0 0 12px; }
  .card { background: #161b22; border: 1px solid #2a313c; border-radius: 10px; padding: 16px; margin-bottom: 16px; }
  .notice { background: #1c232c; border: 1px solid #2a313c; border-radius: 8px; padding: 12px; }
  .notice.err { border-color: #da3633; color: #ff8a80; }
  .row { display: flex; gap: 8px; }
  input, select { background: #0d1117; border: 1px solid #2a313c; color: #e6edf3; border-radius: 6px; padding: 8px 10px; font: inherit; }
  label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: #8b949e; }
  label.chk { flex-direction: row; align-items: center; gap: 6px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 12px; }
  .grid label.wide { grid-column: 1 / -1; }
  .btn { background: #2ea043; border: none; color: #fff; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; }
  .btn.ghost { background: transparent; border: 1px solid #2a313c; color: #8b949e; }
  .btn:disabled { opacity: .5; cursor: default; }
  .mini { background: #1c232c; border: 1px solid #2a313c; color: #2f81f7; border-radius: 5px; padding: 2px 8px; cursor: pointer; }
  .topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .stats { display: flex; gap: 16px; font-size: 13px; color: #8b949e; }
  .stats b { color: #e6edf3; }
  .tabs { display: flex; gap: 6px; margin-bottom: 16px; }
  .tabs button { background: #1c232c; border: 1px solid #2a313c; color: #8b949e; padding: 6px 14px; border-radius: 7px; cursor: pointer; }
  .tabs button.active { background: #1a7f37; border-color: #2ea043; color: #fff; }
  .tblwrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; color: #8b949e; font-weight: 500; padding: 6px 8px; border-bottom: 1px solid #2a313c; }
  td { padding: 7px 8px; border-bottom: 1px solid #2a313c; font-variant-numeric: tabular-nums; }
  td.empty { text-align: center; color: #8b949e; padding: 16px; }
  .pos { color: #2ea043; } .neg { color: #da3633; } .high { color: #da3633; font-weight: 600; }
  .msg { color: #2ea043; font-size: 13px; margin-top: 8px; }
</style>
