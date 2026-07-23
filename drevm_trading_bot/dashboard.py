# dashboard.py — Dashboard NY Smart Money System
# Lancer :  uvicorn dashboard:app --reload --port 8050
# UI      :  http://localhost:8050

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from db import get_signals, get_stats

app = FastAPI(title="DREVM — NY Smart Money Dashboard")

KILLZONE_START, KILLZONE_END = 13, 16  # heures UTC


# ---------------------------------------------------------------- API JSON

@app.get("/api/status")
def api_status():
    now = datetime.now(timezone.utc)
    in_kz = KILLZONE_START <= now.hour < KILLZONE_END
    return {
        "bot": "running",
        "mode": "NY SMART MONEY SYSTEM",
        "utc_time": now.isoformat(timespec="seconds"),
        "killzone_active": in_kz,
        "killzone_utc": f"{KILLZONE_START}h–{KILLZONE_END}h",
    }


@app.get("/api/signals")
def api_signals(limit: int = 20):
    return {"signals": get_signals(limit)}


@app.get("/api/stats")
def api_stats():
    return get_stats()


@app.get("/api/chart/{pair}")
def api_chart(pair: str):
    """Candlestick + zones supply/demand. Nécessite une clé TwelveData valide."""
    pair = pair.replace("-", "/").upper()
    try:
        from data_engine import get_data, API_KEY
        if API_KEY.startswith("YOUR_"):
            return JSONResponse(
                {"error": "API TwelveData non configurée (data_engine.py)"},
                status_code=503,
            )
        df = get_data(pair)
        for col in ("open", "high", "low"):
            df[col] = df[col].astype(float)
        supply = df["close"].rolling(20).max().iloc[-1]
        demand = df["close"].rolling(20).min().iloc[-1]
        return {
            "pair": pair,
            "datetime": df["datetime"].tolist(),
            "open": df["open"].tolist(),
            "high": df["high"].tolist(),
            "low": df["low"].tolist(),
            "close": df["close"].tolist(),
            "supply": float(supply),
            "demand": float(demand),
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


# ---------------------------------------------------------------- UI

HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DREVM · NY Smart Money</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/plotly.js/2.27.0/plotly.min.js"></script>
<style>
  :root{
    --bg:#0b0e14; --panel:#131722; --panel2:#1a2030; --line:#232a3b;
    --txt:#e6e9f0; --dim:#8a93a8;
    --green:#16c784; --red:#ea3943; --gold:#f0b90b; --blue:#4f8cff;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--txt);font:15px/1.5 -apple-system,'Segoe UI',Roboto,sans-serif;padding:20px;max-width:1200px;margin:auto}
  header{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:20px}
  h1{font-size:1.25rem;letter-spacing:.04em}
  h1 span{color:var(--gold)}
  .pill{padding:6px 14px;border-radius:999px;font-weight:600;font-size:.85rem;border:1px solid var(--line);background:var(--panel)}
  .pill.on{color:var(--green);border-color:var(--green)}
  .pill.off{color:var(--dim)}
  .grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-bottom:20px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px}
  .card .label{color:var(--dim);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}
  .card .value{font-size:1.7rem;font-weight:700}
  .value.gold{color:var(--gold)} .value.green{color:var(--green)} .value.red{color:var(--red)} .value.blue{color:var(--blue)}
  section{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px;margin-bottom:20px}
  section h2{font-size:.95rem;color:var(--dim);text-transform:uppercase;letter-spacing:.08em;margin-bottom:14px}
  table{width:100%;border-collapse:collapse;font-size:.92rem}
  th{color:var(--dim);text-align:left;font-weight:600;padding:8px 10px;border-bottom:1px solid var(--line)}
  td{padding:10px;border-bottom:1px solid var(--line)}
  tr:last-child td{border-bottom:none}
  .badge{display:inline-block;padding:3px 10px;border-radius:6px;font-weight:700;font-size:.8rem}
  .g-Ap{background:rgba(240,185,11,.15);color:var(--gold)}
  .g-A{background:rgba(79,140,255,.15);color:var(--blue)}
  .g-B{background:rgba(138,147,168,.18);color:var(--txt)}
  .g-C{background:rgba(138,147,168,.10);color:var(--dim)}
  .side-BUY{color:var(--green);font-weight:700}
  .side-SELL{color:var(--red);font-weight:700}
  .empty{color:var(--dim);text-align:center;padding:30px 0}
  .chartbar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
  .chartbar button{background:var(--panel2);border:1px solid var(--line);color:var(--txt);padding:7px 14px;border-radius:8px;cursor:pointer;font-weight:600}
  .chartbar button.active{border-color:var(--gold);color:var(--gold)}
  #chart{height:420px}
  footer{color:var(--dim);font-size:.8rem;text-align:center;margin-top:10px}
</style>
</head>
<body>
<header>
  <h1>⚡ DREVM · <span>NY SMART MONEY</span></h1>
  <div>
    <span id="kz" class="pill off">Killzone NY —</span>
    <span id="clock" class="pill">— UTC</span>
  </div>
</header>

<div class="grid">
  <div class="card"><div class="label">Signaux total</div><div id="total" class="value blue">—</div></div>
  <div class="card"><div class="label">Setups A+</div><div id="aplus" class="value gold">—</div></div>
  <div class="card"><div class="label">Buy</div><div id="buys" class="value green">—</div></div>
  <div class="card"><div class="label">Sell</div><div id="sells" class="value red">—</div></div>
</div>

<section>
  <h2>Derniers signaux</h2>
  <div id="signals"><div class="empty">Chargement…</div></div>
</section>

<section>
  <h2>Graphique</h2>
  <div class="chartbar" id="pairs"></div>
  <div id="chart"><div class="empty">Sélectionne une paire</div></div>
</section>

<footer>Auto-refresh 30 s · DREVM saasDrevmBot</footer>

<script>
const PAIRS = ["EUR/USD","GBP/JPY","XAU/USD","USD/CAD"];
let currentPair = null;

function gradeClass(g){ return g==="A+"?"g-Ap":g==="A"?"g-A":g==="B"?"g-B":"g-C"; }
function gradeIcon(g){ return g==="A+"?"🔥 A+":g==="A"?"⚡ A":g||"—"; }

async function refresh(){
  try{
    const [st, sig, stats] = await Promise.all([
      fetch("/api/status").then(r=>r.json()),
      fetch("/api/signals").then(r=>r.json()),
      fetch("/api/stats").then(r=>r.json()),
    ]);
    // statut
    const kz = document.getElementById("kz");
    kz.textContent = "Killzone NY " + st.killzone_utc + (st.killzone_active ? " · ACTIVE" : " · inactive");
    kz.className = "pill " + (st.killzone_active ? "on" : "off");
    document.getElementById("clock").textContent = st.utc_time.slice(11,19) + " UTC";
    // stats
    document.getElementById("total").textContent = stats.total;
    document.getElementById("aplus").textContent = stats.by_grade["A+"] || 0;
    document.getElementById("buys").textContent  = stats.by_side["BUY"] || 0;
    document.getElementById("sells").textContent = stats.by_side["SELL"] || 0;
    // table signaux
    const wrap = document.getElementById("signals");
    if(!sig.signals.length){
      wrap.innerHTML = '<div class="empty">Aucun signal enregistré pour l\\'instant.<br>Le bot alimentera cette liste dès le prochain setup détecté.</div>';
    } else {
      wrap.innerHTML = "<table><tr><th>Heure (UTC)</th><th>Paire</th><th>Sens</th><th>Setup</th><th>Score</th><th>Grade</th><th>Prix</th><th>RSI</th></tr>" +
        sig.signals.map(s=>`<tr>
          <td>${(s.timestamp||"").replace("T"," ").slice(0,16)}</td>
          <td><b>${s.pair}</b></td>
          <td class="side-${s.signal}">${s.signal}</td>
          <td>${s.setup||"—"}</td>
          <td>${s.score??"—"}</td>
          <td><span class="badge ${gradeClass(s.grade)}">${gradeIcon(s.grade)}</span></td>
          <td>${s.price??"—"}</td>
          <td>${s.rsi!=null?Number(s.rsi).toFixed(1):"—"}</td>
        </tr>`).join("") + "</table>";
    }
  }catch(e){ console.error(e); }
}

async function loadChart(pair){
  currentPair = pair;
  document.querySelectorAll("#pairs button").forEach(b=>b.classList.toggle("active", b.dataset.p===pair));
  const el = document.getElementById("chart");
  el.innerHTML = '<div class="empty">Chargement du graphique…</div>';
  const r = await fetch("/api/chart/" + pair.replace("/","-"));
  const d = await r.json();
  if(d.error){ el.innerHTML = '<div class="empty">📡 ' + d.error + '</div>'; return; }
  el.innerHTML = "";
  Plotly.newPlot(el, [{
    type:"candlestick", x:d.datetime, open:d.open, high:d.high, low:d.low, close:d.close,
    increasing:{line:{color:"#16c784"}}, decreasing:{line:{color:"#ea3943"}},
  }],{
    paper_bgcolor:"#131722", plot_bgcolor:"#131722",
    font:{color:"#8a93a8"}, margin:{t:20,r:20,b:40,l:50},
    xaxis:{rangeslider:{visible:false},gridcolor:"#232a3b"},
    yaxis:{gridcolor:"#232a3b"},
    shapes:[
      {type:"line",xref:"paper",x0:0,x1:1,y0:d.supply,y1:d.supply,line:{color:"#ea3943",dash:"dash"}},
      {type:"line",xref:"paper",x0:0,x1:1,y0:d.demand,y1:d.demand,line:{color:"#16c784",dash:"dash"}},
    ],
  },{responsive:true,displayModeBar:false});
}

document.getElementById("pairs").innerHTML =
  PAIRS.map(p=>`<button data-p="${p}" onclick="loadChart('${p}')">${p}</button>`).join("");

refresh();
setInterval(refresh, 30000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML
