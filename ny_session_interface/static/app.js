"use strict";

// ── Helpers ──────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem("ny_token") || "";

// Base d'URL : "/" en direct (:8800), "/bot/" derrière le proxy Netlify.
// Rend tous les appels /api/* relatifs au chemin où la console est servie.
const API_BASE = location.pathname.endsWith("/")
  ? location.pathname
  : location.pathname.replace(/[^/]*$/, "");

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  // Token sur TOUTES les requêtes : en mode REQUIRE_TOKEN (exposition publique
  // via Netlify/tunnel), les GET aussi sont protégés.
  if (token()) opts.headers["X-Api-Token"] = token();
  const r = await fetch(API_BASE + path.replace(/^\//, ""), opts);
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}));
    throw new Error(detail.detail || `HTTP ${r.status}`);
  }
  return r.json();
}

function flash(text, kind = "") {
  const m = $("msg");
  m.textContent = text;
  m.className = "msg " + kind;
  if (text) setTimeout(() => { if (m.textContent === text) { m.textContent = ""; m.className = "msg"; } }, 4000);
}

const fmt = (n, d = 2) => (n === null || n === undefined ? "—" : Number(n).toLocaleString("fr-FR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const signed = (n, d = 2) => (n >= 0 ? "+" : "") + fmt(n, d);
function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// ── State suppression flags (évite que le polling écrase une action en cours) ─
let suppressUntil = 0;
const suppress = () => { suppressUntil = Date.now() + 1200; };
const suppressed = () => Date.now() < suppressUntil;

// ── Horloges : prochaine éval M5 (gating new-bar) + temps de session restant ──
function nextBarLabel() {
  const now = new Date();
  const next = new Date(now);
  next.setSeconds(0, 0);
  next.setMinutes(now.getMinutes() + (5 - (now.getMinutes() % 5)));
  return next.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}
function nyRemaining() {
  // Minutes restantes avant 16:00 heure de New York (fin de session).
  try {
    const parts = new Intl.DateTimeFormat("fr-FR", {
      timeZone: "America/New_York", hour: "2-digit", minute: "2-digit", hour12: false,
    }).formatToParts(new Date());
    const h = +parts.find((p) => p.type === "hour").value;
    const m = +parts.find((p) => p.type === "minute").value;
    const left = 16 * 60 - (h * 60 + m);
    if (left <= 0) return null;
    return `${Math.floor(left / 60)} h ${String(left % 60).padStart(2, "0")}`;
  } catch (e) { return null; }
}
function tickClocks() { $("v-nextbar").textContent = nextBarLabel(); }

// ── Rendu de l'état ───────────────────────────────────────────────────────────
let profilesLoaded = false;

function setBadge(id, on, text) {
  const el = $(id);
  el.className = "badge " + (on ? "on" : "off");
  el.querySelector("em").textContent = text;
}

function renderState(s) {
  // Bandeau de mode — l'info la plus importante de la page.
  const mode = $("badge-mode");
  mode.textContent = s.simulate ? "SIMULATION" : "LIVE MT5";
  mode.className = s.simulate ? "mode-sim" : "mode-live";
  const dry = $("badge-dry");
  dry.textContent = s.dry_run ? "DRY RUN — AUCUN ORDRE RÉEL" : "⚠ ORDRES RÉELS ARMÉS";
  dry.className = s.dry_run ? "dry-on" : "dry-off";

  const run = $("badge-run");
  run.textContent = s.running ? `▶ MOTEUR ACTIF · ${s.profile}` : "⏸ MOTEUR ARRÊTÉ";
  run.className = "badge " + (s.running ? "run-on" : "run-off");

  // Compte/positions poussés par le pont MT5 (VPS Windows) → données RÉELLES
  // même quand le moteur cloud tourne en SIMULATION pour l'exécution.
  const bridged = s.account_source === "mt5bridge";
  const connLabel = bridged ? "MT5 (pont)" : s.simulate ? "MT5 (sim)" : "MT5";
  setBadge("badge-conn", s.connected || bridged, connLabel);
  const rem = s.session_open ? nyRemaining() : null;
  setBadge("badge-session", s.session_open,
    s.session_open ? (rem ? `Session NY · reste ${rem}` : "Session NY ouverte") : "Hors session NY");
  setBadge("badge-tg", s.telegram, "Telegram");

  // contrôles
  $("btn-start").disabled = s.running;
  $("btn-stop").disabled = !s.running;
  if (!suppressed()) {
    $("tg-dry").checked = s.dry_run;
    $("tg-kill").checked = s.kill_switch;
  }

  // profils
  if (!profilesLoaded && s.profiles) {
    const sel = $("sel-profile");
    sel.innerHTML = "";
    for (const p of s.profiles) {
      const o = document.createElement("option");
      o.value = p; o.textContent = p;
      sel.appendChild(o);
    }
    profilesLoaded = true;
  }
  if (!suppressed()) $("sel-profile").value = s.profile;

  // tuiles compte
  const a = s.account;
  $("v-equity").textContent = a ? fmt(a.equity) + " " + a.currency : "—";
  $("v-starteq").textContent = a ? fmt(a.start_equity) : "—";
  $("v-balance").textContent = a ? fmt(a.balance) : "—";
  $("v-leverage").textContent = a ? "1:" + a.leverage : "—";

  const dd = a ? Math.max(0, a.dd_pct) : 0;
  const ddmax = s.max_daily_dd_pct || 1;
  $("v-dd").textContent = dd.toFixed(2) + " %";
  $("v-ddmax").textContent = ddmax + " %";
  const fill = $("dd-fill");
  fill.style.width = Math.min(100, (dd / ddmax) * 100) + "%";
  fill.style.background = dd >= ddmax ? "var(--danger)" : dd >= ddmax * 0.6 ? "var(--warn)" : "var(--ok)";

  // trades du jour + statut entrées
  $("v-trades").textContent = s.daily_trades
    ? Object.entries(s.daily_trades).map(([k, v]) => `${k}:${v}`).join(" ") : "—";
  const halted = $("v-halted");
  if (s.halted) { halted.textContent = "⛔ entrées stoppées (drawdown)"; halted.style.color = "var(--danger)"; }
  else if (s.kill_switch) { halted.textContent = "🛑 kill switch actif"; halted.style.color = "var(--danger)"; }
  else { halted.textContent = "entrées actives"; halted.style.color = ""; }

  // récap du profil (bandeau de la carte équité)
  const c = s.profile_config || {};
  $("v-profcfg").textContent =
    `${s.profile} · risque ${c.risk_pct ?? "—"} %/trade · grade ≥ ${c.min_grade ?? "—"} · ` +
    `R:R ${c.rr_target ?? "—"} · max ${c.max_trades_per_symbol ?? "—"}/sym`;

  if (s.last_error) flash("Erreur moteur : " + s.last_error, "err");
}

// ── Positions (R multiple + badge SL→BE calculés côté client) ────────────────
function computeR(p) {
  const risk = p.type === "BUY" ? p.price_open - p.sl : p.sl - p.price_open;
  if (!risk || risk <= 0) return null;
  const gain = p.type === "BUY" ? p.price_now - p.price_open : p.price_open - p.price_now;
  return gain / risk;
}
function isBreakeven(p) {
  return p.type === "BUY" ? p.sl >= p.price_open : (p.sl > 0 && p.sl <= p.price_open);
}

function renderPositions(list, source) {
  $("pos-count").textContent = list.length;
  const body = $("pos-body");
  // Positions poussées par le pont MT5 = lecture seule ici (l'exécution reste
  // côté terminal Windows) → on désactive le bouton « Fermer » du cloud.
  const readonly = source === "mt5bridge";
  if (!list.length) {
    body.innerHTML = '<tr class="empty"><td colspan="11">Aucune position</td></tr>';
    return;
  }
  body.innerHTML = list.map((p) => {
    const dirCls = p.type === "BUY" ? "dir-buy" : "dir-sell";
    const pnlCls = p.pnl >= 0 ? "pnl-pos" : "pnl-neg";
    const r = computeR(p);
    const rTxt = r === null ? "—" : signed(r, 1) + " R";
    const be = isBreakeven(p) ? '<span class="badge-be">SL→BE</span>' : "";
    const closeCell = readonly
      ? '<span class="pos-readonly" title="Fermeture depuis le terminal MT5 Windows">🔒 pont</span>'
      : `<button class="btn-close-pos" data-ticket="${p.ticket}">✕ Fermer</button>`;
    return `<tr>
      <td>${p.ticket}</td><td><b>${p.symbol}</b></td>
      <td class="${dirCls}">${p.type}</td><td>${fmt(p.volume)}</td>
      <td>${p.price_open}</td><td>${p.price_now}</td>
      <td>${p.sl}</td><td>${p.tp}</td>
      <td class="${r >= 0 ? "pnl-pos" : "pnl-neg"}">${rTxt}${be}</td>
      <td class="${pnlCls}"><b>${signed(p.pnl)}</b></td>
      <td>${closeCell}</td>
    </tr>`;
  }).join("");
  body.querySelectorAll(".btn-close-pos").forEach((b) => {
    b.onclick = async () => {
      if (!confirm(`Fermer la position ${b.dataset.ticket} ?`)) return;
      try { await api(`/api/control/close/${b.dataset.ticket}`, "POST"); flash("Position fermée", "ok"); }
      catch (e) { flash(e.message, "err"); }
    };
  });
}

function renderSignals(list) {
  const box = $("signals");
  if (!list.length) { box.innerHTML = '<div class="empty-feed">En attente…</div>'; return; }
  box.innerHTML = list.map((s) => {
    const gradeCls = s.grade === "A+" ? "grade-Aplus" : s.grade === "A" ? "grade-A" : "grade-B";
    const dirCls = s.direction === "up" ? "dir-buy" : "dir-sell";
    const t = (s.ts || "").replace("T", " ").replace("+00:00", "");
    return `<div class="sig">
      <div class="sig-top">
        <span><b class="${dirCls}">${s.symbol} ${s.direction === "up" ? "▲" : "▼"}</b>
        <span class="grade ${gradeCls}">${s.grade}</span> ${s.setup_type}</span>
        <span>${s.demo ? "DEMO · " : ""}${s.dry_run ? "DRY" : "LIVE"} ${fmt(s.lots)} lot</span>
      </div>
      <div class="sig-meta">${t} · entrée ${s.entry} · SL ${s.sl} · TP ${s.tp}</div>
    </div>`;
  }).join("");
}

// ── Navigation entre dashboards ─────────────────────────────────────────────--
function renderDashboards(list) {
  const nav = $("dash-nav");
  if (!nav) return;
  if (!list || !list.length) { nav.innerHTML = ""; return; }
  nav.innerHTML = list.map((d) => {
    if (d.current) {
      return `<span class="dash-link current">${d.icon || "•"} ${d.label}</span>`;
    }
    return `<a class="dash-link" href="${d.url}" title="${d.url}">${d.icon || "•"} ${d.label}</a>`;
  }).join("");
}

async function loadDashboards() {
  try {
    const r = await api("/api/dashboards");
    renderDashboards(r.dashboards);
  } catch (e) { /* silencieux : la nav est secondaire */ }
}

// ── Scan des setups (Wyckoff · FVG · Ichimoku) ──────────────────────────────--
const PILLARS = [
  { key: "wyckoff", label: "Wyckoff", cls: "" },
  { key: "fvg", label: "FVG", cls: "fvg" },
  { key: "ichimoku", label: "Ichimoku", cls: "" },
];
const EXTRA_CONF = [
  { key: "fvg_mitigation", label: "Mitig. FVG" },
  { key: "divergence", label: "Diverg. RSI" },
  { key: "bias", label: "Biais H4" },
];

function gradeChipClass(g) {
  return g === "A+" ? "g-Aplus" : g === "A" ? "g-A" : g === "B" ? "g-B" : g === "C" ? "g-C" : "g-D";
}

// Résultats IA persistés par symbole (le panneau est re-rendu toutes les 5 s).
const aiResults = {};
const aiPending = {};
let lastScanList = [];

function aiBlock(symbol) {
  if (aiPending[symbol]) return '<div class="ai-line">⏳ Analyse IA en cours…</div>';
  const stored = aiResults[symbol];
  if (!stored) return "";
  if (stored.error) return `<div class="ai-line ai-err">⚠️ IA indisponible : ${escapeHtml(stored.error)}</div>`;
  const ai = stored.ai || {};
  const setup = stored.setup || {};
  const rec = (ai.recommendation || "").toUpperCase();
  const recCls = rec === "TRADE" ? "ai-trade" : rec === "WAIT" ? "ai-wait2" : "ai-skip";
  const risks = (ai.risk_factors || []).map((x) => `<span class="chip">${escapeHtml(x)}</span>`).join("");
  const analysed = setup.grade
    ? `<span class="ai-analysed">analysé : ${setup.grade} ${setup.direction === "up" ? "BUY" : setup.direction === "down" ? "SELL" : ""}</span>`
    : "";
  return `<div class="ai-result">
    <div class="ai-top">
      <span class="ai-badge ${recCls}">${rec || "?"}</span>
      <span class="ai-score">${ai.score != null ? ai.score + "/100" : "—"}</span>
      ${analysed}
    </div>
    <div class="ai-reason">${escapeHtml(ai.reasoning || "")}</div>
    ${risks ? `<div class="scan-chips">${risks}</div>` : ""}
  </div>`;
}

function renderScanCached() { renderScan(lastScanList); }

function renderScan(list) {
  lastScanList = list || [];
  const box = $("scan");
  if (!list || !list.length) { box.innerHTML = '<div class="empty-feed">En attente du moteur…</div>'; return; }

  // Badge « source de prix » de la barre de commande (cascade PRICE_SOURCE).
  const sources = [...new Set(list.map((r) => r.price_source).filter(Boolean))];
  const srcBadge = $("badge-src");
  if (sources.length) {
    srcBadge.hidden = false;
    srcBadge.querySelector("em").textContent = "Prix : " + sources.join(" + ");
  }

  box.innerHTML = list.map((r) => {
    if (!r.available) {
      return `<article class="setup scan-na">
        <div class="gradechip"><b>?</b><span>N/A</span></div>
        <div class="body"><div class="top"><span class="sym">${r.symbol}</span>
        <span class="decision d-wait">DONNÉES INDISPO</span></div>
        <div class="meta">Pas de données de marché pour ce symbole.</div></div>
      </article>`;
    }
    const c = r.confluence || {};
    const up = r.direction === "up";
    const dirCls = up ? "dir-buy" : r.direction === "down" ? "dir-sell" : "";
    const dirTxt = up ? "▲ BUY" : r.direction === "down" ? "▼ SELL" : "—";
    const pct = Math.round((r.confluence_points / r.confluence_max) * 100);
    const barCol = pct >= 82 ? "var(--gA)" : pct >= 55 ? "var(--gB)" : "var(--faint)";

    const decision = r.passes_profile
      ? '<span class="decision d-exec">ENTRÉE POSSIBLE</span>'
      : r.is_valid
        ? '<span class="decision d-valid">VALIDE · GRADE &lt; PROFIL</span>'
        : '<span class="decision d-wait">EN ATTENTE</span>';

    const pillars = PILLARS.map((p) => {
      const ok = !!c[p.key];
      return `<span class="pill ${ok ? (p.cls || "ok") : "no"}">${ok ? "✓" : "—"} ${p.label}</span>`;
    }).join("");

    // Structure de marché : CHoCH (retournement) ou BOS (continuation).
    const st = r.structure || {};
    let structBadge = "";
    if (st.event) {
      const arrow = st.direction === "up" ? "▲" : st.direction === "down" ? "▼" : "";
      const cls = st.event === "CHOCH" ? "choch" : "bos";
      const label = st.event === "CHOCH" ? "CHoCH" : "BOS";
      const title = st.event === "CHOCH"
        ? "Change of Character — 1er break contre-tendance (retournement possible)"
        : "Break of Structure — cassure dans le sens de la tendance (continuation)";
      structBadge = `<span class="struct ${cls}" title="${title}">${label} ${arrow}</span>`;
    }
    const extras = EXTRA_CONF.map((p) => {
      const ok = !!c[p.key];
      return `<span class="chip ${ok ? "chip-on" : ""}">${p.label}</span>`;
    }).join("");

    const ctx = r.context || {};
    const fvg = r.fvg || {};
    const fvgTxt = fvg.direction
      ? `${fvg.direction === "BULLISH" ? "haussier" : "baissier"} [${fmt(fvg.bottom, 2)}–${fmt(fvg.top, 2)}]${fvg.price_in_gap ? " · mitigation" : ""}`
      : "aucun";

    return `<article class="setup ${r.pillars_aligned ? "aligned" : ""}">
      <div class="gradechip ${gradeChipClass(r.grade)}"><b>${r.grade}</b><span>GRADE</span></div>
      <div class="body">
        <div class="top">
          <span class="sym">${r.symbol}</span>
          <span class="${dirCls}">${dirTxt}</span>
          ${structBadge}
          ${decision}
          <span class="score"><b class="num">${r.confluence_points}</b>/${r.confluence_max}
            ${r.price_source ? `<span style="color:var(--faint)">· ${r.price_source}</span>` : ""}</span>
        </div>
        <div class="confl">
          <div class="bar"><div class="fill" style="width:${pct}%;background:${barCol}"></div></div>
          <span class="num">${pct} %</span>
        </div>
        <div class="pillars">${pillars}</div>
        <div class="scan-chips">${extras}</div>
        <div class="meta">
          prix ${fmt(r.last_price, 2)} · ${ctx.price_above_kijun ? "prix &gt; Kijun" : "prix &lt; Kijun"} ·
          H4 ${ctx.h4_phase || "—"} · FVG ${fvgTxt}
        </div>
        <div class="verdict ${r.passes_profile ? "ok" : r.is_valid ? "wait" : "idle"}">
          ${r.passes_profile ? "✅ passe le profil (entrée possible)" : r.is_valid ? "⚠️ valide mais grade < profil" : "⏳ pas de smart signal"}
        </div>
        <div class="scan-ai">
          <button class="btn-ai" data-symbol="${r.symbol}" ${r.direction ? "" : "disabled"}
            ${aiPending[r.symbol] ? "disabled" : ""}>🤖 Analyser (IA)</button>
          ${aiBlock(r.symbol)}
        </div>
      </div>
    </article>`;
  }).join("");
  $("scan-updated").textContent = new Date().toLocaleTimeString("fr-FR");
}

async function runAi(symbol) {
  if (aiPending[symbol]) return;
  aiPending[symbol] = true; renderScanCached();
  try {
    const r = await api("/api/scan/ai", "POST", { symbol });
    aiResults[symbol] = { ai: r.ai || {}, setup: r.setup || {} };
  } catch (e) {
    aiResults[symbol] = { error: e.message };
  } finally {
    aiPending[symbol] = false; renderScanCached();
  }
}

// ── Stats P&L ────────────────────────────────────────────────────────────────
function setSigned(id, v, cur) {
  const el = $(id);
  el.textContent = signed(v) + (cur ? " " + cur : "");
  el.className = el.className.replace(/pnl-(pos|neg)/g, "").trim() + (v >= 0 ? " pnl-pos" : " pnl-neg");
}

function renderStats(s) {
  const cur = s.currency || "";
  setSigned("s-realized", s.realized_pnl, cur);
  setSigned("s-floating", s.floating_pnl, cur);
  setSigned("s-total", s.total_pnl, "");
  const r = $("s-return");
  r.textContent = (s.return_pct >= 0 ? "+" : "") + s.return_pct + " %";
  r.className = s.return_pct >= 0 ? "pnl-pos" : "pnl-neg";
  $("s-closed").textContent = `${s.closed_count} fermé(s) · ${s.wins}W/${s.losses}L`;
  $("s-winrate").textContent = s.closed_count ? s.winrate + " %" : "—";
  renderClosed(s.recent_closed || []);
}

function renderClosed(list) {
  $("closed-count").textContent = list.length;
  const body = $("closed-body");
  if (!list.length) {
    body.innerHTML = '<tr class="empty"><td colspan="8">Aucun trade fermé</td></tr>';
    return;
  }
  body.innerHTML = list.map((t) => {
    const dirCls = t.type === "BUY" ? "dir-buy" : "dir-sell";
    const pnlCls = t.pnl >= 0 ? "pnl-pos" : "pnl-neg";
    const time = (t.ts || "").replace("T", " ").replace("+00:00", "");
    return `<tr>
      <td>${time}</td><td><b>${t.symbol}</b></td>
      <td class="${dirCls}">${t.type}</td><td>${fmt(t.volume)}</td>
      <td>${t.entry}</td><td>${t.exit}</td>
      <td class="${pnlCls}">${signed(t.pnl)}</td>
      <td>${t.reason || ""}</td>
    </tr>`;
  }).join("");
}

// ── Courbe d'équité (couleurs thème via tokens CSS) ──────────────────────────
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

let lastEqPoints = [];
function drawEquity(points) {
  lastEqPoints = points;
  const c = $("eq-chart");
  const ctx = c.getContext("2d");
  const w = c.clientWidth || (c.parentElement.clientWidth - 28);
  c.width = w;
  const h = c.height;
  ctx.clearRect(0, 0, w, h);
  if (!points || points.length < 2) {
    ctx.fillStyle = cssVar("--faint") || "#8b949e"; ctx.font = "12px sans-serif";
    ctx.fillText("En attente de données d'équité (moteur en marche)…", 10, h / 2);
    return;
  }
  const eq = points.map((p) => p.equity);
  let min = Math.min(...eq), max = Math.max(...eq);
  if (min === max) { min -= 1; max += 1; }
  const padv = (max - min) * 0.12; min -= padv; max += padv;
  const X = (i) => 4 + (i / (eq.length - 1)) * (w - 8);
  const Y = (v) => h - 8 - ((v - min) / (max - min)) * (h - 16);
  const base = eq[0];
  const up = eq[eq.length - 1] >= base;
  const col = up ? (cssVar("--chart-up") || "#22c55e") : (cssVar("--chart-dn") || "#ef4444");

  // ligne de base (équité de départ)
  ctx.strokeStyle = cssVar("--chart-grid") || "#232D40"; ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(0, Y(base)); ctx.lineTo(w, Y(base)); ctx.stroke();
  ctx.setLineDash([]);

  // courbe
  ctx.beginPath(); ctx.moveTo(X(0), Y(eq[0]));
  for (let i = 1; i < eq.length; i++) ctx.lineTo(X(i), Y(eq[i]));
  ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.stroke();

  // point terminal (valeur courante mise en évidence)
  ctx.beginPath(); ctx.arc(X(eq.length - 1), Y(eq[eq.length - 1]), 3.5, 0, Math.PI * 2);
  ctx.fillStyle = col; ctx.fill();

  // remplissage
  ctx.beginPath(); ctx.moveTo(X(0), Y(eq[0]));
  for (let i = 1; i < eq.length; i++) ctx.lineTo(X(i), Y(eq[i]));
  ctx.lineTo(X(eq.length - 1), h); ctx.lineTo(X(0), h); ctx.closePath();
  ctx.globalAlpha = 0.12; ctx.fillStyle = col; ctx.fill(); ctx.globalAlpha = 1;
}
window.addEventListener("resize", () => drawEquity(lastEqPoints));

// ── Logs (incrémental) ─────────────────────────────────────────────────────---
let lastLogIdx = -1;
function appendLogs(list) {
  if (!list.length) return;
  const box = $("logs");
  const atBottom = box.scrollHeight - box.scrollTop - box.clientHeight < 40;
  for (const r of list) {
    lastLogIdx = Math.max(lastLogIdx, r.i);
    const div = document.createElement("div");
    div.className = "logline lvl-" + r.level;
    div.innerHTML = `<span class="t">${(r.ts || "").replace("T", " ")}</span>${escapeHtml(r.msg)}`;
    box.appendChild(div);
  }
  while (box.childElementCount > 400) box.removeChild(box.firstChild);
  if (atBottom) box.scrollTop = box.scrollHeight;
}

// ── Boucle de polling ──────────────────────────────────────────────────────---
async function poll() {
  try {
    const [state, pos, sig, logs, eq, stats] = await Promise.all([
      api("/api/state"),
      api("/api/positions"),
      api("/api/signals"),
      api(`/api/logs?after=${lastLogIdx}`),
      api("/api/equity"),
      api("/api/stats"),
    ]);
    renderState(state);
    renderPositions(pos.positions, pos.source);
    renderSignals(sig.signals);
    appendLogs(logs.logs);
    renderStats(stats);
    drawEquity(eq.points);
  } catch (e) {
    const conn = $("badge-conn");
    conn.className = "badge warn";
    conn.querySelector("em").textContent = "API injoignable";
  }
}

// ── Câblage des contrôles ────────────────────────────────────────────────────
function wire() {
  $("inp-token").value = token();
  $("inp-token").onchange = (e) => localStorage.setItem("ny_token", e.target.value.trim());

  $("btn-start").onclick = async () => {
    try { await api("/api/control/start", "POST"); flash("Moteur démarré", "ok"); poll(); }
    catch (e) { flash(e.message, "err"); }
  };
  $("btn-stop").onclick = async () => {
    if (!confirm("Arrêter le moteur ?")) return;
    try { await api("/api/control/stop", "POST"); flash("Moteur arrêté", "ok"); poll(); }
    catch (e) { flash(e.message, "err"); }
  };
  $("sel-profile").onchange = async (e) => {
    suppress();
    try { await api("/api/control/profile", "POST", { profile: e.target.value }); flash("Profil → " + e.target.value, "ok"); }
    catch (err) { flash(err.message, "err"); }
  };
  $("tg-dry").onchange = async (e) => {
    if (!e.target.checked && !confirm("⚠️ Désactiver DRY RUN = ORDRES RÉELS. Confirmer ?")) {
      e.target.checked = true; return;
    }
    suppress();
    try { await api("/api/control/dry-run", "POST", { enabled: e.target.checked }); flash("DRY RUN " + (e.target.checked ? "ON" : "OFF"), e.target.checked ? "ok" : "err"); }
    catch (err) { flash(err.message, "err"); e.target.checked = !e.target.checked; }
  };
  $("tg-kill").onchange = async (e) => {
    suppress();
    try { await api("/api/control/kill-switch", "POST", { enabled: e.target.checked }); flash("Kill switch " + (e.target.checked ? "ACTIVÉ" : "désactivé"), e.target.checked ? "err" : "ok"); }
    catch (err) { flash(err.message, "err"); e.target.checked = !e.target.checked; }
  };
  $("btn-closeall").onclick = async () => {
    if (!confirm("Fermer TOUTES les positions du bot ?")) return;
    try { const r = await api("/api/control/close-all", "POST"); flash(`${r.closed} position(s) fermée(s)`, "ok"); poll(); }
    catch (e) { flash(e.message, "err"); }
  };
  $("btn-clearlog").onclick = (e) => { e.preventDefault(); $("logs").innerHTML = ""; };

  // Bouton « Analyser (IA) » — délégué car #scan est re-rendu périodiquement.
  $("scan").addEventListener("click", (e) => {
    const btn = e.target.closest(".btn-ai");
    if (btn && btn.dataset.symbol) runAi(btn.dataset.symbol);
  });
}

// ── Scan (plus lent : 3 timeframes × symboles à chaque appel) ────────────────
async function scanPoll() {
  try {
    const r = await api("/api/scan");
    renderScan(r.scan);
  } catch (e) { /* l'indicateur de connexion est géré par poll() */ }
}

wire();
loadDashboards();
tickClocks();
poll();
scanPoll();
setInterval(poll, 2000);
setInterval(scanPoll, 5000);
setInterval(tickClocks, 10000);
