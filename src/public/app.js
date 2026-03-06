/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   GoldyXbOT — Dashboard Frontend
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */

// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  events: [],                   // All events from server
  filters: {
    impact: new Set([1, 2, 3]), // Active impact levels
    currency: 'ALL',
    source: 'ALL',
  },
  config: {},
};

// ── Currency flags ─────────────────────────────────────────────────────────────
const FLAGS = {
  USD: '🇺🇸', EUR: '🇪🇺', GBP: '🇬🇧', JPY: '🇯🇵',
  CAD: '🇨🇦', AUD: '🇦🇺', CHF: '🇨🇭', NZD: '🇳🇿',
  CNY: '🇨🇳', CHN: '🇨🇳', KRW: '🇰🇷', SGD: '🇸🇬',
  HKD: '🇭🇰', MXN: '🇲🇽', BRL: '🇧🇷', INR: '🇮🇳',
};

const flag = (cur) => FLAGS[cur?.toUpperCase()] ?? '🏳';

// ── Helpers ───────────────────────────────────────────────────────────────────
function impactClass(lvl) {
  if (lvl >= 3) return 'high';
  if (lvl === 2) return 'med';
  return 'low';
}

function impactLabel(lvl) {
  if (lvl >= 3) return '🔴 FORT';
  if (lvl === 2) return '🟠 MOYEN';
  if (lvl === 1) return '🟡 FAIBLE';
  return '⚪ AUCUN';
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function now() { return new Date(); }

// ── Clock ─────────────────────────────────────────────────────────────────────
function startClock() {
  const el = document.getElementById('clock');
  function tick() {
    el.textContent = now().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
  tick();
  setInterval(tick, 1000);
}

// ── Render Table ──────────────────────────────────────────────────────────────
function getFilteredEvents() {
  return state.events.filter(e => {
    if (!state.filters.impact.has(e.impactLevel)) return false;
    if (state.filters.currency !== 'ALL' && e.currency?.toUpperCase() !== state.filters.currency) return false;
    if (state.filters.source !== 'ALL' && e.source !== state.filters.source) return false;
    return true;
  });
}

function renderTable() {
  const tbody = document.getElementById('ecoTableBody');
  const events = getFilteredEvents();

  document.getElementById('tableCount').textContent = events.length;

  if (events.length === 0) {
    const hasData = state.events.length > 0;
    const msg = hasData
      ? `AUCUNE ANNONCE — ${state.events.length} événement(s) masqué(s) par les filtres`
      : 'AUCUNE ANNONCE — Scan en cours...';
    tbody.innerHTML = `<tr class="empty-row"><td colspan="8">
      <div class="empty-state"><div class="empty-spinner"></div><span>${msg}</span></div>
    </td></tr>`;
    return;
  }

  tbody.innerHTML = events.map(e => `
    <tr class="impact-${impactClass(e.impactLevel)}" data-id="${escHtml(e.id)}">
      <td class="col-time"><span class="time-cell">${escHtml(e.time) || '—'}</span></td>
      <td class="col-currency">
        <span class="currency-cell">
          <span class="flag">${flag(e.currency)}</span>
          <span>${escHtml(e.currency)}</span>
        </span>
      </td>
      <td class="col-event">
        <span class="event-cell">${escHtml(e.event)}</span>
        ${isUS30Relevant(e) ? '<span class="us30-tag">⚡US30</span>' : ''}
      </td>
      <td class="col-impact">
        <span class="impact-badge ${impactClass(e.impactLevel)}">${impactLabel(e.impactLevel)}</span>
      </td>
      <td class="col-forecast"><span class="value-cell">${escHtml(e.forecast) || '—'}</span></td>
      <td class="col-previous"><span class="value-cell">${escHtml(e.previous) || '—'}</span></td>
      <td class="col-actual">
        <span class="value-cell actual-cell ${e.actual ? 'has-result' : ''}">${escHtml(e.actual) || '—'}</span>
      </td>
      <td class="col-source">
        <span class="source-badge ${e.source === 'ForexFactory' ? 'ff' : 'inv'}">
          ${e.source === 'ForexFactory' ? 'FF' : 'INV'}
        </span>
      </td>
    </tr>
  `).join('');
}

// ── Render Stats ───────────────────────────────────────────────────────────────
function renderStats() {
  const all = state.events;
  const high = all.filter(e => e.impactLevel >= 3);
  const med  = all.filter(e => e.impactLevel === 2);
  const low  = all.filter(e => e.impactLevel === 1);

  animateCount('countHigh', high.length);
  animateCount('countMed', med.length);
  animateCount('countLow', low.length);

  document.getElementById('statTotal').textContent = all.length;
  document.getElementById('statWithResult').textContent = all.filter(e => e.actual).length;

  // Next event
  const upcoming = all
    .filter(e => e._parsedTime && new Date(e._parsedTime) > now())
    .sort((a, b) => new Date(a._parsedTime) - new Date(b._parsedTime));

  if (upcoming.length > 0) {
    const next = upcoming[0];
    const diff = Math.round((new Date(next._parsedTime) - now()) / 60000);
    document.getElementById('nextEventTime').textContent = diff <= 60 ? `${diff}min` : next.time || '—';
    document.getElementById('nextEventName').textContent = `${next.currency} ${next.event}`.slice(0, 22);
  } else {
    document.getElementById('nextEventTime').textContent = '—';
    document.getElementById('nextEventName').textContent = 'Prochaine';
  }

  renderCurrencyBars();
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  const current = parseInt(el.textContent) || 0;
  if (current === target) return;
  let step = 0;
  const steps = 12;
  const diff = target - current;
  const timer = setInterval(() => {
    step++;
    el.textContent = Math.round(current + diff * (step / steps));
    if (step >= steps) { el.textContent = target; clearInterval(timer); }
  }, 25);
}

// ── Currency Bars ─────────────────────────────────────────────────────────────
function renderCurrencyBars() {
  const container = document.getElementById('currencyBars');
  const counts = {};
  state.events.forEach(e => {
    if (!e.currency) return;
    counts[e.currency] = (counts[e.currency] || 0) + 1;
  });

  const sorted = Object.entries(counts).sort((a, b) => b[1] - a[1]).slice(0, 8);
  if (sorted.length === 0) { container.innerHTML = ''; return; }

  const max = sorted[0][1];
  container.innerHTML = sorted.map(([cur, cnt]) => `
    <div class="currency-bar-item">
      <span class="currency-bar-label">${flag(cur)} ${escHtml(cur)}</span>
      <div class="currency-bar-track">
        <div class="currency-bar-fill" style="width: ${Math.round((cnt / max) * 100)}%"></div>
      </div>
      <span class="currency-bar-count">${cnt}</span>
    </div>
  `).join('');
}

// ── News Feed ─────────────────────────────────────────────────────────────────
const newsFeedItems = [];

function addToNewsFeed(event) {
  newsFeedItems.unshift(event);
  if (newsFeedItems.length > 20) newsFeedItems.pop();
  renderNewsFeed();
}

function renderNewsFeed() {
  const feed = document.getElementById('newsFeed');
  if (newsFeedItems.length === 0) {
    feed.innerHTML = '<div class="news-empty">En attente de données...</div>';
    return;
  }

  feed.innerHTML = newsFeedItems.map(e => `
    <div class="news-item impact-${e.impactLevel}">
      <div class="news-item-header">
        <span class="news-currency">${flag(e.currency)} ${escHtml(e.currency)}</span>
        <span class="news-time">${escHtml(e.time) || '—'}</span>
      </div>
      <div class="news-event">${escHtml(e.event)}</div>
      ${e.actual ? `<div class="news-result">✅ ${escHtml(e.actual)}</div>` : ''}
    </div>
  `).join('');
}

// ── Toasts ────────────────────────────────────────────────────────────────────
function showToast(event, type = 'new') {
  const container = document.getElementById('toastContainer');
  const id = `toast-${Date.now()}`;
  const duration = 6000;

  const isNew = type === 'new';
  const isUpdate = type === 'update';

  const title = isNew
    ? `Nouvelle annonce — ${event.currency}`
    : isUpdate
    ? `Résultat publié — ${event.currency}`
    : 'Info';

  const msg = isNew
    ? `${event.event}`
    : isUpdate
    ? `${event.event} → ${event.actual}`
    : event.event ?? 'Notification';

  const toast = document.createElement('div');
  toast.id = id;
  toast.className = `toast impact-${event.impactLevel ?? 0}`;
  toast.innerHTML = `
    <span class="toast-icon">${event.impactEmoji ?? '📢'}</span>
    <div class="toast-body">
      <div class="toast-title">${escHtml(title)}</div>
      <div class="toast-msg">${escHtml(msg)}</div>
    </div>
    <button class="toast-close" onclick="dismissToast('${id}')">×</button>
    <div class="toast-progress" style="animation-duration:${duration}ms"></div>
  `;

  container.appendChild(toast);

  setTimeout(() => dismissToast(id), duration);
}

function dismissToast(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add('toast-dismiss');
  setTimeout(() => el.remove(), 250);
}

// ── Highlight row ─────────────────────────────────────────────────────────────
function highlightRow(eventId, cls = 'row-new') {
  const rows = document.querySelectorAll(`[data-id="${CSS.escape(eventId)}"]`);
  rows.forEach(row => {
    row.classList.add(cls);
    setTimeout(() => row.classList.remove(cls), 2000);
  });
}

// ── Scan Status ───────────────────────────────────────────────────────────────
function updateScanStatus({ running, lastScan, error }) {
  const badge = document.getElementById('liveBadge');
  const label = document.getElementById('scanLabel');
  const statusEl = document.getElementById('scanStatus');
  const btn = document.getElementById('btnRefresh');

  if (running) {
    badge.classList.add('scanning');
    statusEl.classList.add('active');
    label.textContent = 'Scan en cours...';
    btn.classList.add('spinning');
  } else {
    badge.classList.remove('scanning');
    statusEl.classList.remove('active');
    if (error) {
      label.textContent = `Erreur: ${error.slice(0, 30)}`;
    } else if (lastScan) {
      const t = new Date(lastScan).toLocaleTimeString('fr-FR');
      label.textContent = `Dernier scan: ${t}`;
      document.getElementById('statLastScan').textContent = t;
    }
    btn.classList.remove('spinning');
  }
}

// ── Filters ───────────────────────────────────────────────────────────────────
function initFilters() {
  // Impact chips
  document.querySelectorAll('#impactFilters .chip').forEach(btn => {
    btn.addEventListener('click', () => {
      const lvl = parseInt(btn.dataset.impact);
      if (state.filters.impact.has(lvl)) {
        state.filters.impact.delete(lvl);
        btn.classList.remove('active');
      } else {
        state.filters.impact.add(lvl);
        btn.classList.add('active');
      }
      renderTable();
    });
  });

  // Currency chips
  document.querySelectorAll('#currencyFilters .chip').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#currencyFilters .chip').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.filters.currency = btn.dataset.currency;
      renderTable();
    });
  });

  // Source chips
  document.querySelectorAll('[data-source]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-source]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.filters.source = btn.dataset.source;
      renderTable();
    });
  });
}

// ── Socket.io ─────────────────────────────────────────────────────────────────
function initSocket() {
  const socket = io({ transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    console.log('[WS] Connecté');
    showToast({ event: 'Connecté au serveur', impactLevel: 0, impactEmoji: '🟢', currency: 'SYSTÈME' }, 'info');
  });

  socket.on('disconnect', () => {
    console.warn('[WS] Déconnecté');
    showToast({ event: 'Connexion perdue — reconnexion...', impactLevel: 0, impactEmoji: '🔴', currency: 'SYSTÈME' }, 'info');
  });

  // Initial load
  socket.on('init', ({ events }) => {
    state.events = events;
    renderTable();
    renderStats();
    // Populate news feed with top recent events
    events.slice(0, 10).forEach(e => newsFeedItems.push(e));
    renderNewsFeed();
  });

  // New event
  socket.on('new_event', (event) => {
    const idx = state.events.findIndex(e => e.id === event.id);
    if (idx === -1) {
      state.events.unshift(event);
    } else {
      state.events[idx] = event;
    }
    renderTable();
    renderStats();
    addToNewsFeed(event);
    showToast(event, 'new');
    setTimeout(() => highlightRow(event.id, 'row-new'), 50);
  });

  // Updated result
  socket.on('update_event', (event) => {
    const idx = state.events.findIndex(e => e.id === event.id);
    if (idx !== -1) state.events[idx] = event;
    renderTable();
    renderStats();
    addToNewsFeed(event);
    showToast(event, 'update');
    setTimeout(() => highlightRow(event.id, 'row-updated'), 50);
  });

  // Scan status
  socket.on('scan_status', updateScanStatus);

  // Données marché US30
  socket.on('market_update', (data) => {
    updateMarketBar(data);
  });

  // Nextcloud sync events
  socket.on('nextcloud_sync', (info) => {
    addSyncEntry(info);
    const typeLabels = { init: '📁 Init', calendar: '📅 Calendrier', results: '✅ Résultats', eod: '📊 Fin journée' };
    showToast({
      event: `${typeLabels[info.type] ?? 'Sync'} — ${info.file}`,
      impactLevel: 0, impactEmoji: '☁', currency: 'NEXTCLOUD',
    }, 'info');
  });
}

// ── Nextcloud sync log ────────────────────────────────────────────────────────
const syncEntries = [];

function addSyncEntry(info) {
  syncEntries.unshift(info);
  if (syncEntries.length > 10) syncEntries.pop();
  renderSyncLog();

  const el = document.getElementById('statNextcloud');
  if (el) {
    const t = new Date(info.time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    el.textContent = `✅ ${t}`;
  }
}

function renderSyncLog() {
  const log = document.getElementById('syncLog');
  if (!log) return;
  if (syncEntries.length === 0) { log.innerHTML = '<div class="news-empty">En attente de sync...</div>'; return; }

  const typeIcons = { init: '📁', calendar: '📅', results: '✅', eod: '📊' };
  log.innerHTML = syncEntries.map(e => {
    const t = new Date(e.time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return `<div class="sync-entry">
      <span class="sync-entry-icon">${typeIcons[e.type] ?? '☁'}</span>
      <span class="sync-entry-file">${escHtml(e.file ?? '')}</span>
      <span class="sync-entry-time">${t}</span>
    </div>`;
  }).join('');
}

// ── HTTP fallback (load config) ───────────────────────────────────────────────
async function loadConfig() {
  try {
    const res = await fetch('/api/config');
    const cfg = await res.json();
    state.config = cfg;

    document.getElementById('statDiscord').textContent  = cfg.discordEnabled  ? '✅ Actif' : '❌ Off';
    document.getElementById('statSaas').textContent     = cfg.sources?.saas   ? '✅ Actif' : '❌ Off';
    document.getElementById('statNextcloud').textContent = cfg.nextcloudEnabled ? '⏳ Prêt'  : '❌ Off';

    // Afficher section Nextcloud si activée
    const ncSection = document.getElementById('nextcloudSection');
    if (ncSection && cfg.nextcloudEnabled) ncSection.style.display = 'block';

    if (!cfg.discordEnabled) {
      document.querySelector('.live-badge span:last-child').textContent = 'LOCAL';
    }
  } catch (e) {
    console.warn('Config non disponible:', e);
  }
}

// ── Export Nextcloud manuel ───────────────────────────────────────────────────
function initExportBtn() {
  const btn = document.getElementById('btnExportNow');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    btn.classList.add('spinning');
    btn.disabled = true;
    try {
      const res = await fetch('/api/nextcloud/export', { method: 'POST' });
      const data = await res.json();
      if (data.success) {
        addSyncEntry({ type: 'manual', file: data.file.split(/[\\/]/).pop(), time: new Date().toISOString() });
        showToast({ event: `Exporté: ${data.file.split(/[\\/]/).pop()}`, impactLevel: 0, impactEmoji: '☁', currency: 'NEXTCLOUD' }, 'info');
      }
    } catch (e) {
      showToast({ event: 'Erreur export Nextcloud', impactLevel: 0, impactEmoji: '⚠️', currency: 'ERR' }, 'info');
    } finally {
      btn.classList.remove('spinning');
      btn.disabled = false;
    }
  });
}

// ── Refresh button ────────────────────────────────────────────────────────────
function initRefreshBtn() {
  document.getElementById('btnRefresh').addEventListener('click', async () => {
    const btn = document.getElementById('btnRefresh');
    btn.classList.add('spinning');
    try {
      const res = await fetch('/api/events');
      const { events } = await res.json();
      state.events = events;
      renderTable();
      renderStats();
    } catch (e) {
      showToast({ event: 'Erreur de chargement', impactLevel: 0, impactEmoji: '⚠️', currency: 'ERR' }, 'info');
    } finally {
      btn.classList.remove('spinning');
    }
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// US30 MARKET PANEL
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// ── Événements qui impactent US30 ─────────────────────────────────────────────
const US30_KEYWORDS = [
  'nfp', 'non-farm', 'payroll', 'unemployment', 'jobless',
  'cpi', 'inflation', 'ppi', 'pce',
  'gdp', 'gross domestic',
  'fomc', 'fed ', 'federal reserve', 'powell', 'interest rate',
  'ism', 'pmi', 'manufacturing',
  'retail sales', 'consumer', 'confidence',
  'treasury', 'debt', 'budget',
  'trade balance', 'current account',
  'durable goods', 'housing', 'existing home',
];

function isUS30Relevant(event) {
  if (event.currency === 'USD') return true;
  const name = (event.event || '').toLowerCase();
  return US30_KEYWORDS.some(k => name.includes(k));
}

// ── Session NYSE (calcul pur JS) ───────────────────────────────────────────────
function getNYSESession() {
  const now   = new Date();
  const etStr = now.toLocaleString('en-US', { timeZone: 'America/New_York' });
  const et    = new Date(etStr);
  const day   = et.getDay();
  const min   = et.getHours() * 60 + et.getMinutes();

  if (day === 0 || day === 6) {
    // Weekend — prochain lundi 9h30 ET
    const toMonday = ((8 - day) % 7) || 7;
    const next = new Date(et);
    next.setDate(next.getDate() + toMonday);
    next.setHours(9, 30, 0, 0);
    return { session: 'closed', label: 'FERMÉ', nextLabel: 'Ouverture lundi', nextTime: next };
  }

  if (min < 240) { // avant 4h ET
    const next = new Date(et); next.setHours(4, 0, 0, 0);
    return { session: 'closed', label: 'FERMÉ', nextLabel: 'Pré-marché à', nextTime: next };
  }
  if (min < 570) { // 4h-9h30 ET → pré-marché
    const next = new Date(et); next.setHours(9, 30, 0, 0);
    return { session: 'pre', label: 'PRÉ-MARCHÉ', nextLabel: 'Ouverture dans', nextTime: next };
  }
  if (min < 960) { // 9h30-16h ET → marché ouvert
    const next = new Date(et); next.setHours(16, 0, 0, 0);
    return { session: 'open', label: 'OUVERT', nextLabel: 'Clôture dans', nextTime: next };
  }
  if (min < 1200) { // 16h-20h ET → after-hours
    const next = new Date(et); next.setHours(20, 0, 0, 0);
    return { session: 'post', label: 'AFTER-HOURS', nextLabel: 'Fermeture dans', nextTime: next };
  }
  // après 20h ET → fermé, prochain jour ouvré
  const nextDay = new Date(et);
  nextDay.setDate(nextDay.getDate() + (day === 5 ? 3 : 1)); // vendredi → lundi
  nextDay.setHours(4, 0, 0, 0);
  return { session: 'closed', label: 'FERMÉ', nextLabel: 'Pré-marché à', nextTime: nextDay };
}

function fmtCountdown(ms) {
  if (ms <= 0) return '';
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  if (h > 0) return `${h}h ${m.toString().padStart(2,'0')}m`;
  return `${m}m ${ss.toString().padStart(2,'0')}s`;
}

function updateSessionPanel() {
  const s = getNYSESession();

  // Badge
  const badge = document.getElementById('sessionBadge');
  badge.textContent = s.label;
  badge.className = 'session-badge ' + s.session;

  // Heures
  const now = new Date();
  document.getElementById('nyTime').textContent =
    now.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour: '2-digit', minute: '2-digit', hour12: false });
  document.getElementById('parisTime').textContent =
    now.toLocaleTimeString('fr-FR', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit' });

  // Countdown
  const countdown = document.getElementById('sessionCountdown');
  if (s.nextTime) {
    const diff = s.nextTime - now;
    if (diff > 0) {
      countdown.textContent = `${s.nextLabel} ${fmtCountdown(diff)}`;
    } else {
      countdown.textContent = '';
    }
  }
}

// ── Trading Window (basé sur le calendrier) ───────────────────────────────────
function updateTradingWindow() {
  const dot    = document.getElementById('twDot');
  const status = document.getElementById('twStatus');
  const detail = document.getElementById('twDetail');

  const now    = new Date();
  const in10   = new Date(now.getTime() + 10 * 60_000);
  const in30   = new Date(now.getTime() + 30 * 60_000);

  // Chercher les événements USD haute/moyenne importance à venir
  const upcoming = state.events.filter(e => {
    if (!e._parsedTime) return false;
    if (e.impactLevel < 2) return false;
    if (!isUS30Relevant(e)) return false;
    const t = new Date(e._parsedTime);
    return t >= now && t <= in30;
  }).sort((a, b) => new Date(a._parsedTime) - new Date(b._parsedTime));

  // Événements dans moins de 10min
  const danger = upcoming.filter(e => new Date(e._parsedTime) <= in10);

  let level, label, desc;

  if (danger.length > 0 && danger[0].impactLevel >= 3) {
    level = 'danger';
    label = '🔴 ÉVITER';
    const t = new Date(danger[0]._parsedTime);
    const diff = Math.max(0, Math.round((t - now) / 60000));
    desc = `${danger[0].currency} ${danger[0].event.slice(0, 28)} dans ${diff}min`;
  } else if (upcoming.length > 0 && upcoming[0].impactLevel >= 3) {
    level = 'caution';
    label = '🟠 ATTENTION';
    const t = new Date(upcoming[0]._parsedTime);
    const diff = Math.round((t - now) / 60000);
    desc = `${upcoming[0].currency} ${upcoming[0].event.slice(0, 28)} dans ${diff}min`;
  } else if (upcoming.length > 0) {
    level = 'watch';
    label = '🟡 SURVEILLER';
    const t = new Date(upcoming[0]._parsedTime);
    const diff = Math.round((t - now) / 60000);
    desc = `${upcoming[0].currency} ${upcoming[0].event.slice(0, 28)} dans ${diff}min`;
  } else {
    level = 'safe';
    label = '🟢 SCALP OK';
    desc = 'Aucun événement US dans 30min';
  }

  dot.className    = 'tw-dot ' + level;
  status.className = 'tw-status ' + level;
  status.textContent = label;
  detail.textContent = desc;
}

// ── Prochain événement USD ─────────────────────────────────────────────────────
function updateNextUsEvent() {
  const now = new Date();
  const next = state.events
    .filter(e => e._parsedTime && isUS30Relevant(e) && new Date(e._parsedTime) > now)
    .sort((a, b) => new Date(a._parsedTime) - new Date(b._parsedTime))[0];

  const timeEl   = document.getElementById('nextUsTime');
  const nameEl   = document.getElementById('nextUsName');
  const impactEl = document.getElementById('nextUsImpact');

  if (next) {
    const diff = Math.round((new Date(next._parsedTime) - now) / 60000);
    timeEl.textContent   = diff <= 60 ? `dans ${diff}min` : next.time || '—';
    nameEl.textContent   = `${next.currency} ${next.event}`;
    impactEl.textContent = next.impactLevel >= 3 ? '🔴 Fort' : next.impactLevel === 2 ? '🟠 Moyen' : '🟡 Faible';
  } else {
    timeEl.textContent   = '—';
    nameEl.textContent   = 'Aucun prévu';
    impactEl.textContent = '';
  }
}

// ── Prix US30 (reçu du serveur via WebSocket) ─────────────────────────────────
function updateMarketBar(data) {
  if (!data) return;

  const priceEl = document.getElementById('us30Price');
  const changeEl = document.getElementById('us30Change');

  if (data.price != null) {
    const prev = parseFloat(priceEl.dataset.price || 0);
    priceEl.textContent = data.price.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    priceEl.dataset.price = data.price;
    priceEl.className = 'mb-price ' + (data.price > prev && prev > 0 ? 'up' : data.price < prev && prev > 0 ? 'down' : '');
  }

  if (data.change != null && data.changePercent != null) {
    const sign = data.change >= 0 ? '+' : '';
    changeEl.textContent = `${sign}${data.change.toFixed(0)} (${sign}${data.changePercent.toFixed(2)}%)`;
    changeEl.className = 'mb-change ' + (data.change >= 0 ? 'up' : 'down');
  }

  if (data.high != null)         document.getElementById('us30High').textContent = data.high.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  if (data.low != null)          document.getElementById('us30Low').textContent  = data.low.toLocaleString('fr-FR', { maximumFractionDigits: 0 });
  if (data.previousClose != null) document.getElementById('us30Prev').textContent = data.previousClose.toLocaleString('fr-FR', { maximumFractionDigits: 0 });

  // VIX
  if (data.vix != null) {
    const vixEl = document.getElementById('vixValue');
    vixEl.textContent = data.vix.toFixed(2);
    vixEl.className = 'mb-vix-val ' + (data.vix < 15 ? 'vix-low' : data.vix < 25 ? 'vix-medium' : data.vix < 35 ? 'vix-high' : 'vix-extreme');
  }
  if (data.vixChange != null) {
    const sign = data.vixChange >= 0 ? '+' : '';
    document.getElementById('vixChange').textContent = `${sign}${data.vixChange.toFixed(1)}%`;
  }
}

// ── US30 tag dans le tableau ──────────────────────────────────────────────────
// (intégré dans renderTable via escHtml event.event)

// ── Init marché ───────────────────────────────────────────────────────────────
async function initMarketPanel() {
  // Charger le prix initial
  try {
    const res  = await fetch('/api/market/us30');
    const data = await res.json();
    updateMarketBar(data);
  } catch {}

  // Mise à jour session + fenêtre toutes les secondes
  setInterval(() => {
    updateSessionPanel();
    updateTradingWindow();
    updateNextUsEvent();
  }, 1000);

  updateSessionPanel();
  updateTradingWindow();
  updateNextUsEvent();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TABS + TRADINGVIEW CHART
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

let tvChartLoaded = false;
let tvWidget      = null;
let tvCurrentInterval = '5';

function loadTradingViewChart(interval) {
  interval = interval || tvCurrentInterval;
  tvCurrentInterval = interval;

  const container = document.getElementById('tradingview_advanced_chart');
  if (!container) return;

  // Show loading indicator while TV loads
  container.innerHTML = '<div class="chart-loading">Chargement du graphique…</div>';

  function createWidget() {
    container.innerHTML = '';
    const inner = document.createElement('div');
    inner.id = 'tv_widget_inner';
    inner.style.cssText = 'width:100%;height:100%';
    container.appendChild(inner);

    // eslint-disable-next-line no-undef
    tvWidget = new TradingView.widget({
      autosize: true,
      symbol: 'FOREXCOM:US30',
      interval: tvCurrentInterval,
      timezone: 'Europe/Paris',
      theme: 'dark',
      style: '1',
      locale: 'fr',
      toolbar_bg: '#0d1117',
      enable_publishing: false,
      allow_symbol_change: false,
      hide_top_toolbar: false,
      hide_legend: false,
      save_image: false,
      studies: ['RSI@tv-basicstudies', 'MACD@tv-basicstudies'],
      container_id: 'tv_widget_inner',
    });
  }

  if (typeof TradingView !== 'undefined') {
    createWidget();
  } else {
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/tv.js';
    script.onload = createWidget;
    script.onerror = () => {
      container.innerHTML = '<div class="chart-loading">Impossible de charger TradingView</div>';
    };
    document.head.appendChild(script);
  }
  tvChartLoaded = true;
}

function initTabs() {
  const tabs   = document.querySelectorAll('.tab-btn');
  const panels = {
    calendar: document.getElementById('panelCalendar'),
    chart:    document.getElementById('panelChart'),
  };

  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.dataset.tab;

      // Update active tab button
      tabs.forEach(b => b.classList.toggle('active', b === btn));

      // Show/hide panels
      Object.entries(panels).forEach(([key, el]) => {
        if (!el) return;
        el.style.display = key === tab ? '' : 'none';
      });

      // Lazy-load TradingView on first open
      if (tab === 'chart' && !tvChartLoaded) {
        loadTradingViewChart();
      }
    });
  });

  // Interval buttons inside chart panel
  document.querySelectorAll('.ci-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.ci-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const interval = btn.dataset.interval;
      // Reload chart with new interval
      tvChartLoaded = false;
      loadTradingViewChart(interval);
    });
  });
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  startClock();
  initFilters();
  initRefreshBtn();
  initExportBtn();
  initSocket();
  loadConfig();
  initMarketPanel();
  initTabs();

  // Initial empty render
  renderTable();
  renderStats();
});
