"""
Swarm Observability Dashboard — FastAPI + Server-Sent Events

Real-time view of the FlashForge multi-agent swarm.
Bridges FoxMQ MQTT messages → SSE → browser.

Features:
  - Live peer registry (online/stale status)
  - Multi-critic EVAL_VOTE table (shows BFT consensus in action)
  - Job pipeline tracker (TASK_AVAILABLE → BID → COMMIT → CONSENSUS → DONE)
  - Scrolling event stream (all MQTT messages)

Run:
    python swarm/dashboard_server.py

Open: http://localhost:5050

Environment variables:
  FOXMQ_HOST       default "127.0.0.1"
  FOXMQ_PORT       default 1883
  DASHBOARD_PORT   default 5050
"""
import asyncio
import json
import os
import sys

import paho.mqtt.client as mqtt
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FOXMQ_HOST     = os.getenv("FOXMQ_HOST",   "127.0.0.1")
FOXMQ_PORT     = int(os.getenv("FOXMQ_PORT",   "1883"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5050"))

# ── Event bus: paho thread → asyncio broadcast ─────────────────────────────────
_recent_events: list    = []          # last 200 events (for replay on connect)
_client_queues: set     = set()       # one asyncio.Queue per SSE client
_loop: asyncio.AbstractEventLoop | None = None


def _paho_on_message(client, userdata, msg) -> None:
    try:
        data = json.loads(msg.payload)
    except Exception:
        return
    _recent_events.append(data)
    if len(_recent_events) > 200:
        _recent_events.pop(0)
    if _loop:
        asyncio.run_coroutine_threadsafe(_broadcast(data), _loop)


async def _broadcast(msg: dict) -> None:
    for q in list(_client_queues):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            pass


def _start_mqtt() -> None:
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id="dashboard-observer",
        protocol=mqtt.MQTTv5,
    )
    client.on_message = _paho_on_message
    try:
        client.connect(FOXMQ_HOST, FOXMQ_PORT, keepalive=60)
        client.subscribe("swarm/#", qos=1)
        client.loop_start()
        print(f"[dashboard] ✓ MQTT → FoxMQ {FOXMQ_HOST}:{FOXMQ_PORT}")
    except Exception as e:
        print(f"[dashboard] ⚠ Cannot connect to FoxMQ: {e} — dashboard will show live events once broker starts")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(title="FlashForge Swarm Dashboard")


@app.on_event("startup")
async def startup() -> None:
    global _loop
    _loop = asyncio.get_event_loop()
    _start_mqtt()


# ── SSE endpoint ───────────────────────────────────────────────────────────────
@app.get("/events")
async def sse(request: Request):
    q: asyncio.Queue = asyncio.Queue(maxsize=300)
    _client_queues.add(q)

    async def gen():
        try:
            # Replay up to 50 recent events on fresh connect
            for evt in _recent_events[-50:]:
                yield f"data: {json.dumps(evt)}\n\n"
            # Stream new events
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"data: {json.dumps(msg)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"  # prevent browser SSE timeout
        finally:
            _client_queues.discard(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/events")
async def api_events():
    return {"events": _recent_events[-100:], "total": len(_recent_events)}


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(DASHBOARD_HTML)


# ── Embedded dashboard HTML ────────────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FlashForge — Swarm Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0d1117;color:#e6edf3;font-family:'Courier New',monospace;padding:20px;font-size:13px}
h1{color:#58a6ff;font-size:18px;margin-bottom:2px}
.sub{color:#8b949e;margin-bottom:20px;font-size:12px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px}
.card h2{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;margin-bottom:14px}
.stat{text-align:center;padding:12px 8px;border-right:1px solid #30363d}
.stat:last-child{border-right:none}
.stat-n{font-size:26px;color:#58a6ff;font-weight:700;line-height:1}
.stat-l{font-size:10px;color:#8b949e;margin-top:4px;text-transform:uppercase}
.peer{display:inline-flex;align-items:center;gap:6px;background:#21262d;border-radius:4px;padding:3px 9px;margin:3px;font-size:11px}
.dot{width:7px;height:7px;border-radius:50%;flex-shrink:0}
.online .dot{background:#3fb950}
.stale  .dot{background:#f85149}
table{width:100%;border-collapse:collapse}
th{color:#8b949e;font-weight:400;text-align:left;padding:4px 8px;border-bottom:1px solid #30363d;font-size:10px;text-transform:uppercase;letter-spacing:1px}
td{padding:5px 8px;border-bottom:1px solid #1c2128;font-size:12px}
tr:hover td{background:#1c2128}
.pass{background:#1a4731;color:#3fb950}
.fail{background:#3d1a1a;color:#f85149}
.consensus{background:#1d3557;color:#79c0ff}
.badge{display:inline-block;border-radius:3px;padding:0 6px;font-size:11px;font-weight:600}
#stream-box{height:260px;overflow-y:auto}
.evt{display:flex;gap:8px;padding:2px 0;border-bottom:1px solid #1c2128}
.t{color:#8b949e;min-width:70px;font-size:11px}
.ty{min-width:160px;font-weight:600;font-size:11px}
.ty-EVAL_VOTE{color:#e3b341}
.ty-EVAL_CONSENSUS{color:#79c0ff}
.ty-COMMIT{color:#3fb950}
.ty-BID{color:#8b949e}
.ty-PEER_ANNOUNCE{color:#58a6ff}
.ty-HEARTBEAT{color:#30363d}
.ty-TASK_AVAILABLE{color:#ff7b72}
.ty-COORDINATION_COMPLETE{color:#3fb950}
.eb{color:#484f58;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;font-size:11px}
</style>
</head>
<body>
<h1>⚡ FlashForge Swarm</h1>
<p class="sub">Vertex Swarm Challenge 2026 — Track 3 · Multi-Critic BFT Agent Economy ·
  <span id="cs" style="color:#f85149">connecting…</span></p>

<div class="stats">
  <div class="stat"><div class="stat-n" id="s0">0</div><div class="stat-l">Peers Online</div></div>
  <div class="stat"><div class="stat-n" id="s1">0</div><div class="stat-l">Jobs</div></div>
  <div class="stat"><div class="stat-n" id="s2">0</div><div class="stat-l">Votes Cast</div></div>
  <div class="stat"><div class="stat-n" id="s3">0</div><div class="stat-l">Consensus</div></div>
</div>

<div class="grid2">
  <div class="card">
    <h2>🟢 Swarm Peers</h2>
    <div id="peers">no peers yet</div>
  </div>
  <div class="card">
    <h2>⚖️ Multi-Critic BFT Votes &amp; Consensus</h2>
    <table>
      <thead><tr><th>Job</th><th>Critic</th><th>Score</th><th>Verdict</th></tr></thead>
      <tbody id="vtb"></tbody>
    </table>
  </div>
</div>

<div class="card">
  <h2>📡 Live MQTT Event Stream <span id="ec" style="color:#484f58"></span></h2>
  <div id="stream-box"></div>
</div>

<script>
const peers={},jobs=new Set(),vdata={};
let tv=0,tc=0,ec=0;

const es=new EventSource('/events');
es.onopen=()=>{const el=document.getElementById('cs');el.textContent='connected';el.style.color='#3fb950'};
es.onerror=()=>{const el=document.getElementById('cs');el.textContent='reconnecting…';el.style.color='#f85149'};
es.onmessage=e=>{const m=JSON.parse(e.data);handle(m);appendEvt(m);stats()};

function handle(m){
  const{type:t,sender_id:sid,sender_role:role,payload:p={}}=m;
  if(t==='PEER_ANNOUNCE'||t==='HEARTBEAT'){
    peers[sid]={role,status:'online',seen:Date.now()};
    renderPeers();
  }
  if(p.job_id) jobs.add(p.job_id.split(':')[0]);
  if(t==='EVAL_VOTE'){
    const k=(p.job_id||'').slice(0,8);
    (vdata[k]=vdata[k]||[]).push({
      critic:(p.critic_id||sid||'').slice(0,8),
      score:p.score,passed:p.passed
    });
    tv++;renderVotes();
  }
  if(t==='EVAL_CONSENSUS'){
    const k=(p.job_id||'').slice(0,8);
    (vdata[k]=vdata[k]||[]).push({
      critic:'⚖ CONSENSUS',score:p.avg_score,
      passed:p.verdict==='PASS',isC:true
    });
    tc++;renderVotes();
  }
}

function renderPeers(){
  const now=Date.now();
  const h=Object.entries(peers).map(([id,p])=>{
    if((now-p.seen)/1e3>12)p.status='stale';
    return `<span class="peer ${p.status}"><span class="dot"></span>${p.role} <span style="color:#484f58">${id.slice(0,8)}</span></span>`;
  }).join('');
  document.getElementById('peers').innerHTML=h||'no peers yet';
}

function renderVotes(){
  const rows=[];
  for(const[j,vs] of Object.entries(vdata)){
    for(const v of vs){
      const cls=v.isC?'consensus':v.passed?'pass':'fail';
      const lbl=v.isC?'⚖ CONSENSUS':v.passed?'PASS':'FAIL';
      rows.push(`<tr>
        <td style="color:#484f58">${j}</td>
        <td>${v.critic}</td>
        <td>${v.score!=null?v.score.toFixed(1):'—'}</td>
        <td><span class="badge ${cls}">${lbl}</span></td>
      </tr>`);
    }
  }
  document.getElementById('vtb').innerHTML=rows.join('')||
    '<tr><td colspan="4" style="color:#484f58;padding:10px">Waiting for evaluation task…</td></tr>';
}

function appendEvt(m){
  ec++;
  const box=document.getElementById('stream-box');
  const d=document.createElement('div');d.className='evt';
  const now=new Date().toLocaleTimeString('en',{hour12:false});
  const body=JSON.stringify(m.payload||{}).slice(0,100);
  d.innerHTML=`<span class="t">${now}</span><span class="ty ty-${m.type}">${m.type}</span><span class="eb">${m.sender_role||''}:${(m.sender_id||'').slice(0,8)} ${body}</span>`;
  box.appendChild(d);
  box.scrollTop=box.scrollHeight;
  if(box.children.length>300)box.removeChild(box.firstChild);
  document.getElementById('ec').textContent=`(${ec} events)`;
}

function stats(){
  const on=Object.values(peers).filter(p=>p.status==='online').length;
  document.getElementById('s0').textContent=on;
  document.getElementById('s1').textContent=jobs.size;
  document.getElementById('s2').textContent=tv;
  document.getElementById('s3').textContent=tc;
}

setInterval(()=>{
  const now=Date.now();let ch=false;
  for(const p of Object.values(peers)){
    if(p.status==='online'&&(now-p.seen)/1e3>12){p.status='stale';ch=true;}
  }
  if(ch){renderPeers();stats();}
},2000);
</script>
</body>
</html>"""


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=DASHBOARD_PORT, log_level="warning")
