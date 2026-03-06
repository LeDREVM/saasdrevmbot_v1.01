/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   saasDrevmBot — Home Page Logic
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

// ── Clock ─────────────────────────────────────────────────────────────────────
function startClock() {
  function tick() {
    const now  = new Date();
    const time = now.toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const date = now.toLocaleDateString('fr-FR', { timeZone: 'Europe/Paris', weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' });
    const clockEl = document.getElementById('hubClock');
    const dateEl  = document.getElementById('hubDate');
    if (clockEl) clockEl.textContent = time;
    if (dateEl)  dateEl.textContent  = date.charAt(0).toUpperCase() + date.slice(1);
  }
  tick();
  setInterval(tick, 1000);
}

// ── NYSE Session ──────────────────────────────────────────────────────────────
function getNYSESession() {
  const etStr = new Date().toLocaleString('en-US', { timeZone: 'America/New_York' });
  const et    = new Date(etStr);
  const day   = et.getDay();
  const min   = et.getHours() * 60 + et.getMinutes();
  if (day === 0 || day === 6) return { session: 'closed', label: 'FERMÉ' };
  if (min < 240)  return { session: 'closed', label: 'FERMÉ' };
  if (min < 570)  return { session: 'pre',    label: 'PRÉ-MARCHÉ' };
  if (min < 960)  return { session: 'open',   label: 'OUVERT' };
  if (min < 1200) return { session: 'post',   label: 'AFTER-HOURS' };
  return { session: 'closed', label: 'FERMÉ' };
}

// ── Format helpers ─────────────────────────────────────────────────────────────
function fmt(n, dec = 0) {
  if (n == null) return '——';
  return n.toLocaleString('fr-FR', { minimumFractionDigits: dec, maximumFractionDigits: dec });
}
function sign(n) { return n >= 0 ? '+' : ''; }
function upDown(n) { return n >= 0 ? 'up' : 'down'; }

// ── Update Market ─────────────────────────────────────────────────────────────
function updateMarket(data) {
  if (!data) return;

  // Ticker
  if (data.price != null) {
    document.getElementById('tickerUs30').textContent = fmt(data.price);
  }
  if (data.changePercent != null) {
    const el = document.getElementById('tickerUs30Chg');
    el.textContent = `${sign(data.changePercent)}${data.changePercent.toFixed(2)}%`;
    el.className = `ticker-change ${upDown(data.changePercent)}`;
  }
  if (data.vix != null) {
    document.getElementById('tickerVix').textContent = data.vix.toFixed(2);
  }
  if (data.vixChange != null) {
    const el = document.getElementById('tickerVixChg');
    el.textContent = `${sign(data.vixChange)}${data.vixChange.toFixed(1)}%`;
    el.className = `ticker-change ${upDown(data.vixChange)}`;
  }

  // Bottom panel
  if (data.price != null) {
    const el = document.getElementById('hpUs30');
    el.textContent  = fmt(data.price);
    el.className    = `market-price ${upDown(data.change)}`;
  }
  if (data.change != null && data.changePercent != null) {
    const el = document.getElementById('hpUs30Chg');
    el.textContent = `${sign(data.change)}${fmt(data.change)} (${sign(data.changePercent)}${data.changePercent.toFixed(2)}%)`;
    el.className   = `market-change ${upDown(data.change)}`;
  }
  if (data.high != null && data.low != null && data.previousClose != null) {
    document.getElementById('hpUs30HL').textContent =
      `H ${fmt(data.high)} / L ${fmt(data.low)} / Veille ${fmt(data.previousClose)}`;
  }
  if (data.vix != null) {
    document.getElementById('hpVix').textContent = data.vix.toFixed(2);
  }
  if (data.vixChange != null) {
    const el = document.getElementById('hpVixChg');
    el.textContent = `${sign(data.vixChange)}${data.vixChange.toFixed(1)}%`;
    el.className   = `market-change ${upDown(data.vixChange)}`;
  }

  // GoldyXbOT card metric
  if (data.price != null) {
    const m = document.querySelector('#card-goldyxbot .metric-val.cyan:first-of-type');
    // update via ID to be safe
  }
}

// ── Update Session ─────────────────────────────────────────────────────────────
function updateSession() {
  const s = getNYSESession();
  const badge = document.getElementById('hpSession');
  if (badge) {
    badge.textContent = s.label;
    badge.className   = `session-badge-home ${s.session}`;
  }
  const now = new Date();
  const nyTime  = now.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false });
  const frTime  = now.toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris',     hour: '2-digit', minute: '2-digit' });
  const nyEl  = document.getElementById('hpNyTime');
  const frEl  = document.getElementById('hpParisTime');
  if (nyEl)  nyEl.textContent  = nyTime;
  if (frEl)  frEl.textContent  = frTime;
}

// ── Update System Status ──────────────────────────────────────────────────────
function updateSystemStatus(status) {
  if (!status) return;

  const goldyOnline   = status.goldyxbot?.status === 'online';
  const apiOnline     = status.saasApi?.status   === 'online';
  const analyticsOn   = false; // SvelteKit checked separately

  // Global badge
  const dot   = document.getElementById('systemDot');
  const label = document.getElementById('systemLabel');
  if (goldyOnline && apiOnline) {
    dot.className   = 'system-dot online';
    label.textContent = 'SYSTÈME EN LIGNE';
  } else if (goldyOnline) {
    dot.className   = 'system-dot partial';
    label.textContent = 'PARTIEL — API hors ligne';
  } else {
    dot.className   = 'system-dot offline';
    label.textContent = 'SYSTÈME HORS LIGNE';
  }

  // GoldyXbOT card
  setCardStatus('goldyxbot', true); // always online (we're running inside it)
  const evts = status.goldyxbot?.events;
  if (evts) {
    document.getElementById('m-events').textContent = evts.total ?? '—';
    const highEl = document.getElementById('m-high');
    highEl.textContent = evts.high ?? '—';
    highEl.className   = `metric-val ${evts.high > 0 ? 'red' : 'cyan'}`;
  }

  // FastAPI card
  setCardStatus('api', apiOnline);

  // Integrations
  const cfg = status.config || {};
  setInteg('discord',     status.goldyxbot?.discordEnabled   ?? cfg.discordEnabled);
  setInteg('nextcloud',   status.goldyxbot?.nextcloudEnabled ?? cfg.nextcloudEnabled);
  setInteg('forexfactory',status.sources?.forexfactory);
  setInteg('investing',   status.sources?.investing);
  setInteg('saas',        apiOnline);
  setInteg('yahoo',       status.market?.price != null);

  // Events ticker
  if (evts) {
    const high = evts.high ?? 0;
    document.getElementById('tickerEvents').textContent = `${evts.total ?? '—'} total`;
    document.getElementById('tickerHigh').textContent   = `${high} 🔴 fort`;
  }

  // Footer
  const footerEl = document.getElementById('footerLastUpdate');
  if (footerEl && status.timestamp) {
    const t = new Date(status.timestamp).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    footerEl.textContent = `Dernière sync : ${t}`;
  }
}

function setCardStatus(id, online) {
  const dot   = document.getElementById(`dot-${id}`);
  const label = document.getElementById(`label-${id}`);
  if (!dot || !label) return;
  dot.className = `card-dot ${online ? 'online' : 'offline'}`;
  label.textContent  = online ? 'EN LIGNE' : 'HORS LIGNE';
  label.className    = `card-status-label ${online ? 'online' : 'offline'}`;
}

function setInteg(id, enabled) {
  const el = document.getElementById(`istat-${id}`);
  if (!el) return;
  if (enabled == null) {
    el.textContent = '—';
    el.className   = 'integ-status na';
  } else if (enabled) {
    el.textContent = '✅ ACTIF';
    el.className   = 'integ-status on';
  } else {
    el.textContent = '❌ OFF';
    el.className   = 'integ-status off';
  }
}

// ── Update Events ─────────────────────────────────────────────────────────────
const US30_KEYWORDS = [
  'nfp','non-farm','payroll','unemployment','jobless',
  'cpi','inflation','ppi','pce','gdp','gross domestic',
  'fomc','fed ','federal reserve','powell','interest rate',
  'ism','pmi','manufacturing','retail sales','consumer','confidence',
  'treasury','debt','budget','trade balance','durable goods','housing',
];
function isUS30Relevant(e) {
  if (e.currency === 'USD') return true;
  const n = (e.event || '').toLowerCase();
  return US30_KEYWORDS.some(k => n.includes(k));
}

function updateEventList(events) {
  const list = document.getElementById('homeEventList');
  if (!list) return;

  const now     = new Date();
  const upcoming = events
    .filter(e => e._parsedTime && new Date(e._parsedTime) > now && isUS30Relevant(e))
    .sort((a, b) => new Date(a._parsedTime) - new Date(b._parsedTime))
    .slice(0, 8);

  // Update ticker next event
  if (upcoming.length > 0) {
    const next = upcoming[0];
    const diff = Math.round((new Date(next._parsedTime) - now) / 60000);
    document.getElementById('tickerNextTime').textContent = diff <= 60 ? `dans ${diff}min` : next.time || '—';
    document.getElementById('tickerNextName').textContent = `${next.currency} ${next.event}`;
  } else {
    document.getElementById('tickerNextTime').textContent = '—';
    document.getElementById('tickerNextName').textContent = 'Aucun prévu';
  }

  if (upcoming.length === 0) {
    list.innerHTML = '<div class="home-event-empty">Aucun événement USD à venir</div>';
    return;
  }

  const impactClass = lvl => lvl >= 3 ? 'high' : lvl === 2 ? 'medium' : 'low';
  const impactEmoji = lvl => lvl >= 3 ? '🔴' : lvl === 2 ? '🟠' : '🟡';

  list.innerHTML = upcoming.map(e => {
    const cls  = impactClass(e.impactLevel);
    const emoji = impactEmoji(e.impactLevel);
    const name = (e.event || '').slice(0, 32) + ((e.event || '').length > 32 ? '…' : '');
    return `<div class="home-event-item ${cls}">
      <span class="hev-time">${e.time || '—'}</span>
      <span class="hev-cur">${e.currency || '—'}</span>
      <span class="hev-name" title="${e.event || ''}">${name}</span>
      <span class="hev-impact">${emoji}</span>
    </div>`;
  }).join('');
}

// ── Check Analytics Status (SvelteKit :5173) ──────────────────────────────────
async function checkAnalyticsStatus() {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 2500);
    const res = await fetch('http://localhost:5173', { signal: ctrl.signal, mode: 'no-cors' });
    // no-cors = opaque response, but if it resolves the server is up
    setCardStatus('analytics', true);
  } catch {
    setCardStatus('analytics', false);
  }
}

// ── Main fetch loop ───────────────────────────────────────────────────────────
async function fetchAll() {
  try {
    // System status (aggregated from Express)
    const [statusRes, eventsRes] = await Promise.allSettled([
      fetch('/api/system/status'),
      fetch('/api/events'),
    ]);

    if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
      const status = await statusRes.value.json();
      updateSystemStatus(status);
      if (status.market) updateMarket(status.market);
    }

    if (eventsRes.status === 'fulfilled' && eventsRes.value.ok) {
      const data = await eventsRes.value.json();
      updateEventList(data.events || []);
    }

    // Market data (separate, more frequent)
    try {
      const mRes = await fetch('/api/market/us30');
      if (mRes.ok) updateMarket(await mRes.json());
    } catch {}

  } catch (err) {
    console.warn('[Home] Fetch error:', err.message);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startClock();

  // Initial session
  updateSession();
  setInterval(updateSession, 30_000);

  // Check analytics (SvelteKit)
  checkAnalyticsStatus();
  setInterval(checkAnalyticsStatus, 30_000);

  // Fetch data
  fetchAll();
  setInterval(fetchAll, 15_000);

  // GoldyXbOT is always online (home is served by it)
  setCardStatus('goldyxbot', true);
  setInteg('ff', null);
});
