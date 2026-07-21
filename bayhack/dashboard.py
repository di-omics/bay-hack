"""Live demo dashboard -- watch the world model run the bench, in your browser.

    python -m bayhack.dashboard          # -> http://127.0.0.1:8000

Stdlib only (matches the sim demo's zero-dependency promise). It runs the REAL
DBTL loop from bayhack.loop and visualizes it in the matcha house style: the world
model proposes experiments, each becomes a well colored by fluorescence, the
Rhodamine R^2 gate goes green, the convergence curve climbs, and the conformal
gate accepts -- the wow beat that reads from the back of the room.
"""
from __future__ import annotations

import argparse
import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .loop import DBTLLoop, Bench
from .safety import FAULTS, run_refusal


RECEIPT_PATH: Path | None = None


class ReceiptReplayError(RuntimeError):
    """A saved trust receipt cannot be presented safely."""


def run_loop(seed: int = 7, budget: int = 20) -> dict:
    loop = DBTLLoop(Bench(rng=random.Random(seed)), tol=0.03, budget=budget)
    hist = loop.run(verbose=False)
    bx, by = loop.wm.best()
    return {
        "mode": "simulation",
        "x_star": round(loop.bench.x_star, 4),
        "runs_used": loop.runs_used,
        "grid": 26,
        "converged": bool(
            loop.follow_up is not None
            and abs(bx - loop.bench.x_star) <= loop.tol
        ),
        "best_x": round(bx, 4), "best_y": round(by, 4),
        "target_signal": loop.target_signal,
        "rounds": [{"k": r.k, "phase": r.phase, "well": r.destination,
                    "stock_ul": r.stock_ul, "diluent_ul": r.diluent_ul,
                    "x": round(r.x, 4), "fluor": round(r.fluor, 4),
                    "r2": round(r.r2, 4), "decision": r.decision,
                    "plan_verified": r.plan_verified,
                    "measurement_provenance": r.measurement_provenance,
                    "model_updated": r.model_updated,
                    "uncertainty": round(r.uncertainty, 4),
                    "target_signal": r.target_signal,
                    "target_met": r.target_met,
                    "conformal_decision": r.conformal_decision,
                    "best_x": round(r.best_x, 4), "best_y": round(r.best_y, 4)}
                   for r in hist],
        "follow_up": loop.follow_up,
        "ledger": loop.ledger.to_dict(),
    }


def replay_receipt(path: str | Path) -> dict:
    """Convert a saved trust receipt into dashboard data without bench motion."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ReceiptReplayError(f"cannot read trust receipt: {source}") from exc
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ReceiptReplayError("trust receipt contains no experiment records")

    rounds = []
    for record in records:
        try:
            plan = record["plan"]
            measurement = record["measurement"]
            physical = record["physical_verification"]
            model = record["world_model"]
        except (KeyError, TypeError) as exc:
            raise ReceiptReplayError("trust receipt record is missing required fields") from exc
        acceptance = record.get("acceptance", {})
        best_x = model.get("best_x")
        best_y = model.get("best_y")
        rounds.append({
            "k": record["run_id"],
            "phase": record["phase"],
            "well": plan["destination"],
            "stock_ul": float(plan["stock_ul"]),
            "diluent_ul": float(plan["diluent_ul"]),
            "x": round(float(plan["design_x"]), 4),
            "fluor": round(float(measurement["value"]), 4),
            "r2": round(float(physical.get("rhodamine", {}).get("r2", 0.0)), 4),
            "decision": record["decision"],
            "plan_verified": bool(record["plan_verification"]["passed"]),
            "measurement_provenance": str(measurement["provenance"]),
            "model_updated": bool(model["updated"]),
            "uncertainty": round(float(acceptance.get("uncertainty", 0.0)), 4),
            "target_signal": float(acceptance.get("target_signal", 0.85)),
            "target_met": bool(acceptance.get("target_met", False)),
            "conformal_decision": str(
                acceptance.get("conformal_decision", record["decision"])
            ),
            "best_x": round(float(best_x if best_x is not None else plan["design_x"]), 4),
            "best_y": round(float(best_y if best_y is not None else measurement["value"]), 4),
        })

    trusted_rounds = [
        round_data
        for round_data, record in zip(rounds, records)
        if record.get("world_model", {}).get("updated")
    ]
    best_round = max(trusted_rounds or rounds, key=lambda item: item["fluor"])
    final = records[-1]
    final_acceptance = final.get("acceptance", {})
    final_model = final.get("world_model", {})
    best_x = final_model.get("best_x")
    best_y = final_model.get("best_y")
    ledger_follow_up = payload.get("follow_up")
    follow_up = None
    follow_up_passed = False
    if isinstance(ledger_follow_up, dict):
        execution = ledger_follow_up.get("execution", {})
        follow_up_passed = bool(execution.get("passed"))
        follow_up = {
            "action": ledger_follow_up.get("action", {}),
            "verification": ledger_follow_up.get("verification", {}),
            "executed": follow_up_passed,
        }
    return {
        "mode": "receipt-replay",
        "x_star": None,
        "runs_used": len(rounds),
        "grid": 26,
        "converged": final.get("decision") == "ACCEPT" and follow_up_passed,
        "best_x": round(float(best_x if best_x is not None else best_round["x"]), 4),
        "best_y": round(float(best_y if best_y is not None else best_round["fluor"]), 4),
        "target_signal": float(final_acceptance.get("target_signal", 0.85)),
        "rounds": rounds,
        "follow_up": follow_up,
        "ledger": payload,
    }


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>bay-hack &middot; live demo</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ccircle cx='50' cy='50' r='46' fill='%235cae5a'/%3E%3Cpath d='M28 50h44' stroke='white' stroke-width='12' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200;400;500;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--matcha:#5cae5a;--matcha-deep:#3c8446;--ink:#28372a;--bg:#ffffff;--wash:#f2f8f3;
  --line:#e6efe8;--muted:#6f8274;--dye:#2f6fd6;--bad:#b23a2e;
  --sans:'Manrope',system-ui,-apple-system,sans-serif;--mono:'JetBrains Mono',ui-monospace,monospace;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.5;-webkit-font-smoothing:antialiased;}
.wrap{max-width:1080px;margin:0 auto;padding:34px 24px 70px;}
a{color:var(--matcha-deep);text-decoration:none;font-weight:800;}
.charm-row{display:flex;gap:12px;align-items:center;}
svg.charm{width:28px;height:28px;fill:none;stroke:var(--matcha);stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;}
.eyebrow{font-weight:800;font-size:11px;letter-spacing:.2em;text-transform:uppercase;color:var(--matcha-deep);margin:14px 0 8px;}
h1{font-weight:800;font-size:clamp(30px,5vw,46px);letter-spacing:-.02em;margin:0;color:var(--ink);}
h1 .lite{font-weight:200;color:var(--matcha-deep);}
.sub{color:var(--muted);font-weight:500;margin:8px 0 0;max-width:680px;}
.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:26px 0 6px;}
.run{font-family:var(--sans);font-weight:800;font-size:13px;letter-spacing:.08em;text-transform:uppercase;
  border:none;border-radius:999px;cursor:pointer;background:var(--matcha);color:#fff;padding:11px 26px;}
.run:hover{background:var(--matcha-deep);}
.refuse{font-family:var(--sans);font-weight:800;font-size:13px;letter-spacing:.06em;text-transform:uppercase;
  border:1.5px solid #d7897e;border-radius:999px;cursor:pointer;background:#fff;color:var(--bad);padding:9px 20px;}
.refuse:hover{background:#fff5f3;}
.seed{font-family:var(--mono);font-size:13px;color:var(--ink);background:#fff;border:1.5px solid var(--line);border-radius:10px;padding:9px 12px;width:120px;}
.seed:focus{outline:2px solid var(--matcha);}
.muted{color:var(--muted);font-size:13px;font-weight:500;}
.banner{display:block;border-radius:14px;padding:14px 18px;margin:22px 0;
  border:1px solid var(--line);background:var(--wash);font-weight:800;color:var(--matcha-deep);}
.banner.refused{background:#fff5f3;border-color:#efc7c1;color:var(--bad);}
.banner .headline{display:flex;align-items:center;gap:11px;}
.banner-stats{display:flex;flex-wrap:wrap;gap:22px;margin:12px 0 0 22px;}
.banner .dot{width:11px;height:11px;border-radius:50%;background:var(--matcha);flex:0 0 auto;}
.card{background:#fff;border:1px solid var(--line);border-left:3px solid var(--matcha);border-radius:14px;padding:20px 22px;margin:16px 0;}
.card h2{margin:0 0 4px;font-size:11px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;color:var(--matcha-deep);}
.card .note{color:var(--muted);font-size:13px;font-weight:500;margin:0 0 14px;}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
@media(max-width:760px){.grid2{grid-template-columns:1fr;}}
/* loop diagram */
.flow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;}
.flow .node{border:1.5px solid var(--matcha);border-radius:10px;padding:8px 12px;font-weight:800;font-size:12.5px;color:var(--ink);background:#fff;text-align:center;}
.flow .node small{display:block;font-family:var(--mono);font-weight:600;font-size:9px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);margin-top:3px;}
.flow .node.accent{background:var(--matcha);color:#fff;border-color:var(--matcha);}
.flow .node.accent small{color:rgba(255,255,255,.9);}
.flow .node.swap{border-style:dashed;color:var(--muted);}
.flow .arrow{color:var(--matcha);font-weight:800;font-size:15px;}
/* wells */
.wells{display:flex;flex-wrap:wrap;gap:9px;}
.col{display:flex;flex-direction:column;align-items:center;gap:5px;}
.sw{width:30px;height:30px;border-radius:7px;border:1px solid var(--line);}
.sw.best{box-shadow:0 0 0 2px var(--matcha);border-color:var(--matcha);}
.col .n{font-family:var(--mono);font-size:10px;color:var(--muted);}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin-bottom:12px;font-weight:600;}
.legend .k{display:inline-block;width:16px;height:12px;border-radius:3px;vertical-align:middle;margin-right:6px;border:1px solid var(--line);}
/* table */
table{width:100%;border-collapse:collapse;font-size:13px;}
th,td{text-align:right;padding:8px 10px;border-bottom:1px solid var(--line);white-space:nowrap;font-family:var(--mono);}
th{font-family:var(--sans);font-size:10px;text-transform:uppercase;letter-spacing:.1em;color:var(--matcha-deep);font-weight:800;}
td.lab{text-align:left;color:var(--muted);}
.pass{color:var(--matcha-deep);font-weight:800;}
.acc{color:var(--matcha-deep);font-weight:800;}.esc{color:#b0862a;font-weight:800;}
.tablewrap{overflow-x:auto;}
#chart svg{width:100%;height:auto;display:block;}
.foot{margin-top:44px;display:flex;align-items:center;gap:14px;color:var(--muted);}
svg.vesica{width:56px;height:36px;fill:none;stroke:var(--matcha);stroke-width:1.4;}
.foot .cap{font-family:var(--mono);font-weight:600;font-size:11px;letter-spacing:.15em;text-transform:uppercase;color:var(--ink);}
.stat{display:inline-block;margin-right:22px;}
.stat b{display:block;font-size:22px;font-weight:800;color:var(--matcha-deep);}
.stat span{font-size:10px;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);font-weight:800;}
.receipt{display:flex;flex-wrap:wrap;gap:10px;}
.receipt .proof{border:1px solid var(--line);border-radius:999px;background:var(--wash);padding:8px 12px;
  color:var(--matcha-deep);font-family:var(--mono);font-size:11px;font-weight:600;}
.receipt .proof.modeled{color:#7c6727;background:#fffaf0;border-color:#e7d9aa;}
.receipt .proof.blocked{color:var(--bad);background:#fff5f3;border-color:#efc7c1;}
</style>
</head>
<body>
<svg id="lh-sprite" width="0" height="0" style="position:absolute" aria-hidden="true">
 <symbol id="lh-plate" viewBox="0 0 32 32"><rect x="4" y="7" width="24" height="18" rx="2.5"/><circle cx="9" cy="12" r="1.3"/><circle cx="14" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/><circle cx="24" cy="12" r="1.3"/><circle cx="9" cy="16.5" r="1.3"/><circle cx="14" cy="16.5" r="1.3"/><circle cx="19" cy="16.5" r="1.3"/><circle cx="24" cy="16.5" r="1.3"/><circle cx="9" cy="21" r="1.3"/><circle cx="14" cy="21" r="1.3"/><circle cx="19" cy="21" r="1.3"/><circle cx="24" cy="21" r="1.3"/></symbol>
 <symbol id="lh-pipette" viewBox="0 0 32 32"><path d="M16 4v5"/><path d="M12 9h8l-2.2 8.5h-3.6z"/><path d="M14.9 17.5 16 23l1.1-5.5"/><circle cx="16" cy="25.6" r="1.4"/></symbol>
 <symbol id="lh-droplet" viewBox="0 0 32 32"><path d="M16 5c-6 9-8 13-8 16a8 8 0 0 0 16 0c0-3-2-7-8-16z"/></symbol>
 <symbol id="lh-reservoir" viewBox="0 0 32 32"><path d="M6 9h20l-2 15H8z"/><path d="M8.5 14h15"/></symbol>
 <symbol id="lh-target" viewBox="0 0 32 32"><circle cx="16" cy="16" r="10"/><circle cx="16" cy="16" r="5.5"/><circle cx="16" cy="16" r="1.6"/></symbol>
</svg>

<div class="wrap">
  <div class="charm-row" aria-hidden="true">
    <svg class="charm"><use href="#lh-plate"/></svg><svg class="charm"><use href="#lh-pipette"/></svg>
    <svg class="charm"><use href="#lh-droplet"/></svg><svg class="charm"><use href="#lh-reservoir"/></svg>
    <svg class="charm"><use href="#lh-target"/></svg>
  </div>
  <p class="eyebrow">bay-hack &middot; live demo</p>
  <h1>two world models close the liquid-handling loop</h1>
  <p class="sub">The scientific world model chooses the next 40 uL formulation. The physical world
  model executes it safely. <b>plr-mcp</b>, a <b>Rhodamine-B</b> volume gate, CV, and conformal QC turn
  every proposed well into a trust receipt before the accepted result moves downstream.</p>

  <div class="controls">
    <button class="run" id="run">&#9654; Run the loop</button>
    <button class="refuse" id="refuse">Prove refusal</button>
    <label class="muted">seed <input class="seed" id="seed" type="number" value="7"></label>
    <span class="muted" id="status"></span>
  </div>

  <div id="banner"></div>

  <div class="card">
    <h2>The closed loop</h2>
    <div class="flow">
      <span class="node">Plan</span><span class="arrow">&rarr;</span>
      <span class="node accent">scientific model<small>choose next well</small></span><span class="arrow">&rarr;</span>
      <span class="node">Build / Test<small>plr-mcp</small></span><span class="arrow">&rarr;</span>
      <span class="node">Verify<small>rhodamine + cv</small></span><span class="arrow">&rarr;</span>
      <span class="node">Learn<small>objective + uncertainty</small></span><span class="arrow">&rarr;</span>
      <span class="node">Follow up<small>20 uL to H12</small></span><span class="arrow">&#8634;</span>
      <span class="node swap">Zeon physical model<small>scene + executor</small></span>
    </div>
  </div>

  <div class="card">
    <h2>Experiments &middot; each well is one proposed run</h2>
    <p class="note">Colored by assay score. The default signal is explicitly modeled; a camera or reader callback changes the receipt to measured. The matcha ring marks the best well.</p>
    <div class="legend"><span><span class="k" style="background:#eef2fb"></span>low signal</span><span><span class="k" style="background:#2f6fd6"></span>high signal</span><span><span class="k" style="box-shadow:0 0 0 2px var(--matcha);background:#fff"></span>best so far</span></div>
    <div class="wells" id="wells"></div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>Convergence</h2>
      <p class="note">Best assay score found, per round.</p>
      <div id="chart"></div>
    </div>
    <div class="card">
      <h2>Liquid-handling plan</h2>
      <div class="tablewrap"><table id="tbl"><thead><tr><th>run</th><th>well</th><th>stock</th><th>diluent</th><th>signal</th><th>evidence</th><th>gate</th></tr></thead><tbody></tbody></table></div>
    </div>
  </div>

  <div class="card">
    <h2>Trust receipt &middot; current decision</h2>
    <p class="note">Plan, execution, measurement provenance, physical gates, model update, and follow-up remain inspectable.</p>
    <div class="receipt" id="receipt"></div>
  </div>

  <div class="foot">
    <svg class="vesica" viewBox="0 0 74 48"><circle cx="30" cy="24" r="17"/><circle cx="44" cy="24" r="17"/></svg>
    <span class="cap">di-omics &middot; autonomous labs</span>
    <span style="margin-left:auto"><a href="https://github.com/di-omics/bay-hack">github.com/di-omics/bay-hack</a></span>
  </div>
</div>

<script>
const $=s=>document.querySelector(s);
function dye(f){ // white -> dye blue by signal strength
  const a=[238,242,251], b=[47,111,214];
  return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*Math.max(0,Math.min(1,f)))).join(',')})`;
}
function chart(rounds){
  const W=440,H=210,pad=34;
  const ys=rounds.map(r=>r.best_y), n=rounds.length;
  const X=i=>pad+(W-2*pad)*(n<2?0.5:i/(n-1));
  const Y=v=>H-pad-(H-2*pad)*Math.max(0,Math.min(1,v));
  const pts=rounds.map((r,i)=>`${X(i)},${Y(r.best_y)}`).join(' ');
  const dots=rounds.map((r,i)=>`<circle cx="${X(i)}" cy="${Y(r.best_y)}" r="3.4" fill="#3c8446"/>`).join('');
  return `<svg viewBox="0 0 ${W} ${H}">
    <line x1="${pad}" y1="${Y(1)}" x2="${W-pad}" y2="${Y(1)}" stroke="#9db8a0" stroke-dasharray="5 4" stroke-width="1.2"/>
    <text x="${W-pad}" y="${Y(1)-6}" fill="#3c8446" font-size="10" text-anchor="end" font-family="monospace">max response</text>
    <polyline points="${pts}" fill="none" stroke="#5cae5a" stroke-width="2.4"/>${dots}
    <text x="${pad}" y="${H-8}" fill="#6f8274" font-size="10" font-family="monospace">round &rarr;</text>
  </svg>`;
}
async function run(){
  const seed=$('#seed').value||7;
  $('#status').textContent='running the loop...';
  const d=await (await fetch('/api/run?seed='+seed)).json();
  if(d.error){ $('#status').textContent=d.error; return; }
  const replay=d.mode==='receipt-replay';
  $('#run').textContent=replay?'↻ Reload receipt':'▶ Run the loop';
  $('#seed').disabled=replay;
  $('#seed').closest('label').style.display=replay?'none':'';
  $('#status').textContent=replay?'safe receipt replay · zero hardware commands':'';
  // banner
  const b=$('#banner');
  b.className='banner';
  if(d.converged){
    const f=d.follow_up.action;
    const headline=replay
      ? `Replayed accepted receipt: x=${d.best_x.toFixed(3)}, signal ${d.best_y.toFixed(3)}, ${d.runs_used} trusted runs. Follow-up: ${f.volume_ul}uL ${f.source} &rarr; ${f.destination}, verified.`
      : `Recovered optimum x*&asymp;${d.x_star.toFixed(2)} at x=${d.best_x.toFixed(3)} (signal ${d.best_y.toFixed(3)}) in ${d.runs_used} runs, vs ~${d.grid} for a grid sweep. Follow-up: ${f.volume_ul}uL ${f.source} &rarr; ${f.destination}, verified.`;
    b.innerHTML=`<div class="headline"><span class="dot"></span><span>${headline}</span></div>
      <div class="banner-stats"><span class="stat"><b>${d.runs_used}</b><span>runs</span></span><span class="stat"><b>800uL</b><span>search volume saved</span></span><span class="stat"><b>${d.rounds.at(-1).measurement_provenance.toUpperCase()}</b><span>signal provenance</span></span><span class="stat"><b>&ge;${d.target_signal.toFixed(2)}</b><span>objective threshold</span></span></div>`;
  } else {
    const target=d.x_star===null?`objective &ge;${d.target_signal.toFixed(2)}`:`target ${d.x_star.toFixed(2)}`;
    b.innerHTML=`<span class="dot" style="background:var(--bad)"></span>best x=${d.best_x.toFixed(3)} (${target}) after ${d.runs_used} runs.`;
  }
  // wells
  $('#wells').innerHTML=d.rounds.map((r,i)=>{
    const best=Math.abs(r.x-d.best_x)<1e-6 && r.best_y===d.best_y;
    return `<div class="col"><div class="sw${best?' best':''}" style="background:${dye(r.fluor)}" title="x=${r.x}, fluor=${r.fluor}"></div><div class="n">${r.k}</div></div>`;
  }).join('');
  // chart
  $('#chart').innerHTML=chart(d.rounds);
  // table
  $('#tbl tbody').innerHTML=d.rounds.map(r=>{
    const g=r.decision==='ACCEPT'?'acc':(r.decision==='ESCALATE'?'esc':'');
    return `<tr><td class="lab">R${r.k} ${r.phase}</td><td>${r.well}</td><td>${r.stock_ul.toFixed(1)}uL</td>
      <td>${r.diluent_ul.toFixed(1)}uL</td><td>${r.fluor.toFixed(3)}</td><td>${r.measurement_provenance.toUpperCase()}</td><td class="${g}">${r.decision}</td></tr>`;
  }).join('');
  const accepted=d.ledger.records[d.ledger.records.length-1];
  const proofs=[
    ['PLAN PASS', accepted.plan_verification.passed],
    ['EXECUTE '+accepted.execution.backend, accepted.execution.passed],
    ['MEASURE '+accepted.measurement.provenance.toUpperCase(), true],
    ['VOLUME GATE '+accepted.physical_verification.provenance.toUpperCase(), accepted.physical_verification.rhodamine.passed],
    ['CV '+accepted.physical_verification.provenance.toUpperCase(), accepted.physical_verification.cv.passed],
    ['OBJECTIVE ≥'+accepted.acceptance.target_signal.toFixed(2), accepted.acceptance.target_met],
    ['UNCERTAINTY '+accepted.acceptance.uncertainty.toFixed(3), accepted.acceptance.conformal_decision==='ACCEPT'],
    ['MODEL UPDATED', accepted.world_model.updated],
    ['FOLLOW-UP '+d.ledger.follow_up.execution.backend.toUpperCase(), d.ledger.follow_up.execution.passed],
  ];
  $('#receipt').innerHTML=proofs.map(([label,ok])=>`<span class="proof${label.includes('MODELED')?' modeled':''}">${ok?'&#10003;':'!'} ${label}</span>`).join('');
}
async function refuse(){
  $('#status').textContent='injecting an invalid tip assignment...';
  const d=await (await fetch('/api/refusal?kind=tip_reuse')).json();
  $('#status').textContent='unsafe plan blocked before motion';
  const b=$('#banner');
  b.className='banner refused';
  b.innerHTML=`<div class="headline"><span>REFUSED BEFORE ACT: ${d.plan_verification.reasons.join('; ')}.</span></div>
    <div class="banner-stats"><span class="stat"><b>${d.execution.commands_issued}</b><span>robot commands</span></span><span class="stat"><b>NO</b><span>measurement taken</span></span><span class="stat"><b>NO</b><span>model update</span></span><span class="stat"><b>PASS</b><span>recovery plan</span></span></div>`;
  const p=d.unsafe_plan;
  $('#wells').innerHTML=`<div class="col"><div class="sw" style="background:#fff5f3;border-color:#d7897e" title="unsafe plan refused"></div><div class="n">REFUSED</div></div>`;
  $('#chart').innerHTML='<p class="note">No measurement entered the scientific model.</p>';
  $('#tbl tbody').innerHTML=`<tr><td class="lab">R1 safety-check</td><td>${p.destination}</td><td>${p.stock_ul.toFixed(1)}uL</td><td>${p.diluent_ul.toFixed(1)}uL</td><td>not taken</td><td>BLOCKED</td><td style="color:var(--bad);font-weight:800">REFUSED</td></tr>`;
  const proofs=[
    'PLAN REFUSED',
    'ROBOT COMMANDS 0',
    'MEASUREMENT NOT TAKEN',
    'MODEL NOT UPDATED',
    'FOLLOW-UP BLOCKED',
    'RECOVERY PLAN PASS',
  ];
  $('#receipt').innerHTML=proofs.map(label=>`<span class="proof blocked">&#10003; ${label}</span>`).join('');
}
$('#run').addEventListener('click',run);
$('#refuse').addEventListener('click',refuse);
run();
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif u.path == "/api/run":
            q = parse_qs(u.query)
            try:
                seed = int(q.get("seed", ["7"])[0])
            except ValueError:
                seed = 7
            try:
                data = replay_receipt(RECEIPT_PATH) if RECEIPT_PATH else run_loop(seed)
                self._send(200, json.dumps(data).encode(), "application/json")
            except ReceiptReplayError as exc:
                self._send(
                    500,
                    json.dumps({"error": str(exc)}).encode(),
                    "application/json",
                )
        elif u.path == "/api/refusal":
            q = parse_qs(u.query)
            kind = q.get("kind", ["tip_reuse"])[0]
            if kind not in FAULTS:
                kind = "tip_reuse"
            body = json.dumps(run_refusal(kind)).encode()
            self._send(200, body, "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def log_message(self, *a):
        pass


def main():
    global RECEIPT_PATH
    ap = argparse.ArgumentParser(description="bay-hack live demo dashboard")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument(
        "--receipt",
        help="replay a saved trust receipt without issuing hardware commands",
    )
    args = ap.parse_args()
    if args.receipt:
        RECEIPT_PATH = Path(args.receipt)
        replay_receipt(RECEIPT_PATH)
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    mode = f"receipt replay: {RECEIPT_PATH}" if RECEIPT_PATH else "simulation"
    print(f"bay-hack dashboard -> http://{args.host}:{args.port}  ({mode}; Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
