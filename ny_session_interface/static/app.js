"use strict";

// ── Helpers ──────────────────────────────────────────────────────────────────
const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem("ny_token") || "";

async function api(path, method = "GET", body = null) {
  const opts = { method, headers: {} };
  if (body) { opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
  if (method !== "GET") opts.headers["X-Api-Token"] = token();
  const r = await fetch(path, opts);
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

// ── State suppression flags (évite que le polling écrase une action en cours) ─
let suppressUntil = 0;
const suppress = () => { suppressUntil = Date.now() + 1200; };
const suppressed = () => Date.now() < suppressUntil;

// ── Rendu de l'état ───────────────────────────────────────────────────────────
let profilesLoaded = false;

function renderState(s) {
  // badges
  const run = $("badge-run");
  run.textContent = s.running ? "EN MARCHE" : "ARRÊTÉ";
  run.className = "pill " + (s.running ? "pill-on" : "pill-off");

  const conn = $("badge-conn");
  conn.textContent = s.connected ? "connecté" : "déconnecté";
  conn.className = "badge " + (s.connected ? "badge-on" : "");

  const mode = $("badge-mode");
  mode.textContent = s.simulate ? "SIMULATION" : "LIVE MT5";
  mode.className = "badge " + (s.simulate ? "badge-sim" : "badge-live");

  const dry = $("badge-dry");
  dry.textContent = s.dry_run ? "DRY RUN" : "ORDRES RÉELS";
  dry.className = "badge " + (s.dry_run ? "badge-on" : "badge-live");

  const tg = $("badge-tg");
  tg.textContent = s.telegram ? "Telegram ✓" : "Telegram off";
  tg.className = "badge " + (s.telegram ? "badge-on" : "");

  const sess = $("badge-session");
  sess.textContent = s.session_open ? "session NY ouverte" : "hors session";
  sess.className = "badge " + (s.session_open ? "badge-on" : "");

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

  // compte
  const a = s.account;
  $("v-balance").textContent = a ? fmt(a.balance) + " " + a.currency : "—";
  $("v-equity").textContent = a ? fmt(a.equity) + " " + a.currency : "—";
  $("v-starteq").textContent = a ? fmt(a.start_equity) : "—";
  $("v-leverage").textContent = a ? "1:" + a.leverage : "—";

  const dd = a ? Math.max(0, a.dd_pct) : 0;
  const ddmax = s.max_daily_dd_pct || 1;
  $("v-dd").textContent = dd.toFixed(2) + "%";
  $("v-ddmax").textContent = ddmax + "%";
  const fill = $("dd-fill");
  fill.style.width = Math.min(100, (dd / ddmax) * 100) + "%";
  fill.style.background = dd >= ddmax ? "var(--red)" : dd >= ddmax * 0.6 ? "var(--amber)" : "var(--green)";

  // profil/session
  const c = s.profile_config || {};
  $("v-risk").textContent = c.risk_pct != null ? c.risk_pct + " %" : "—";
  $("v-grade").textContent = c.min_grade || "—";
  $("v-rr").textContent = c.rr_target != null ? c.rr_target : "—";
  $("v-maxtrades").textContent = c.max_trades_per_symbol != null ? c.max_trades_per_symbol : "—";
  $("v-trades").textContent = s.daily_trades
    ? Object.entries(s.daily_trades).map(([k, v]) => `${k}:${v}`).join("  ") : "—";
  $("v-halted").textContent = s.halted ? "⛔ stoppées (DD)" : (s.kill_switch ? "⛔ kill switch" : "actives");

  if (s.last_error) flash("Erreur moteur : " + s.last_error, "err");
}

function renderPositions(list) {
  $("pos-count").textContent = list.length;
  const body = $("pos-body");
  if (!list.length) {
    body.innerHTML = '<tr class="empty"><td colspan="10">Aucune position</td></tr>';
    return;
  }
  body.innerHTML = list.map((p) => {
    const dirCls = p.type === "BUY" ? "dir-buy" : "dir-sell";
    const pnlCls = p.pnl >= 0 ? "pnl-pos" : "pnl-neg";
    return `<tr>
      <td>${p.ticket}</td><td>${p.symbol}</td>
      <td class="${dirCls}">${p.type}</td><td>${fmt(p.volume)}</td>
      <td>${p.price_open}</td><td>${p.price_now}</td>
      <td>${p.sl}</td><td>${p.tp}</td>
      <td class="${pnlCls}">${fmt(p.pnl)}</td>
      <td><button class="btn-close-pos" data-ticket="${p.ticket}">✕</button></td>
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

// ── Stats P&L + courbe d'équité ────────────────────────────────────────────--
function setSigned(id, v, cur) {
  const el = $(id);
  el.textContent = (v >= 0 ? "+" : "") + fmt(v) + (cur ? " " + cur : "");
  el.className = v >= 0 ? "pnl-pos" : "pnl-neg";
}

function renderStats(s) {
  const cur = s.currency || "";
  setSigned("s-realized", s.realized_pnl, cur);
  setSigned("s-floating", s.floating_pnl, cur);
  setSigned("s-total", s.total_pnl, cur);
  const r = $("s-return");
  r.textContent = (s.return_pct >= 0 ? "+" : "") + s.return_pct + "%";
  r.className = s.return_pct >= 0 ? "pnl-pos" : "pnl-neg";
  $("s-closed").textContent = `${s.closed_count} (${s.wins}W/${s.losses}L)`;
  $("s-winrate").textContent = s.closed_count ? s.winrate + "%" : "—";
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
      <td>${time}</td><td>${t.symbol}</td>
      <td class="${dirCls}">${t.type}</td><td>${fmt(t.volume)}</td>
      <td>${t.entry}</td><td>${t.exit}</td>
      <td class="${pnlCls}">${(t.pnl >= 0 ? "+" : "") + fmt(t.pnl)}</td>
      <td>${t.reason || ""}</td>
    </tr>`;
  }).join("");
}

let lastEqPoints = [];
function drawEquity(points) {
  lastEqPoints = points;
  const c = $("eq-chart");
  const ctx = c.getContext("2d");
  const w = c.clientWidth || (c.parentElement.clientWidth - 32);
  c.width = w;
  const h = c.height;
  ctx.clearRect(0, 0, w, h);
  if (!points || points.length < 2) {
    ctx.fillStyle = "#8b949e"; ctx.font = "12px sans-serif";
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
  const col = up ? "#2ea043" : "#da3633";

  // ligne de base (équité de départ)
  ctx.strokeStyle = "#2a313c"; ctx.setLineDash([4, 4]);
  ctx.beginPath(); ctx.moveTo(0, Y(base)); ctx.lineTo(w, Y(base)); ctx.stroke();
  ctx.setLineDash([]);

  // courbe
  ctx.beginPath(); ctx.moveTo(X(0), Y(eq[0]));
  for (let i = 1; i < eq.length; i++) ctx.lineTo(X(i), Y(eq[i]));
  ctx.strokeStyle = col; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.stroke();

  // remplissage
  ctx.lineTo(X(eq.length - 1), h); ctx.lineTo(X(0), h); ctx.closePath();
  ctx.fillStyle = up ? "rgba(46,160,67,.12)" : "rgba(218,54,51,.12)";
  ctx.fill();
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
function escapeHtml(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

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
    renderPositions(pos.positions);
    renderSignals(sig.signals);
    appendLogs(logs.logs);
    renderStats(stats);
    drawEquity(eq.points);
  } catch (e) {
    $("badge-conn").textContent = "API injoignable";
    $("badge-conn").className = "badge badge-warn";
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
  $("btn-clearlog").onclick = () => { $("logs").innerHTML = ""; };
}

wire();
poll();
setInterval(poll, 2000);
