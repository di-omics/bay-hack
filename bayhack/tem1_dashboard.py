"""Matcha dashboard for the announced Track A TEM-1 inhibitor challenge."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .tem1 import (
    ExpressionEvidence,
    TEM1AssaySpec,
    TEM1Error,
    confirm_expression,
    run_simulated_closed_loop,
    verify_receipt_integrity,
)


RECEIPT_PATH: Path | None = None


class TEM1ReceiptError(RuntimeError):
    """A TEM-1 receipt cannot be safely replayed."""


def replay_tem1_receipt(path: str | Path) -> dict:
    source = Path(path)
    try:
        payload = json.loads(source.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TEM1ReceiptError(f"cannot read TEM-1 receipt: {source}") from exc
    if payload.get("target") != "TEM-1 beta-lactamase":
        raise TEM1ReceiptError("receipt target is not TEM-1 beta-lactamase")
    if not verify_receipt_integrity(payload):
        raise TEM1ReceiptError("TEM-1 receipt integrity check failed")
    rounds = payload.get("rounds")
    if not isinstance(rounds, list) or len(rounds) != 2:
        raise TEM1ReceiptError("TEM-1 receipt must contain exactly two rounds")
    expression = payload.get("protein_synthesis", {}).get("confirmation", {})
    if "passed" not in expression:
        raise TEM1ReceiptError("TEM-1 receipt is missing expression confirmation")
    payload = dict(payload)
    payload["mode"] = "receipt-replay"
    payload["receipt_path"] = str(source)
    payload["hardware_commands_issued_by_replay"] = 0
    return payload


def run_expression_refusal() -> dict:
    spec = TEM1AssaySpec(
        expression_confirmation_method="modeled sfGFP fluorescence",
        expression_min_fold_over_background=2.0,
    )
    evidence = ExpressionEvidence(
        {
            "tem1_expression": [1.02, 0.98, 1.01],
            "no_template_control": [1.00, 1.01, 0.99],
        },
        provenance="modeled:fault-injection",
        evidence={"fault": "expression_not_above_background"},
    )
    verdict = confirm_expression(evidence, spec)
    return {
        "schema_version": "1.0",
        "status": "REFUSED",
        "stage": "TEM-1 expression confirmation",
        "confirmation": verdict,
        "compound_screen": {"executed": False, "wells_read": 0},
        "world_model": {"updated": False},
        "round2": {"planned": False},
        "robot_commands_after_failure": 0,
    }


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>bay-hack &middot; TEM-1 closed loop</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200;400;500;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--matcha:#5cae5a;--deep:#3c8446;--ink:#28372a;--wash:#f2f8f3;--line:#e3eee5;
--muted:#6f8274;--blue:#2f6fd6;--gold:#b67a18;--bad:#b23a2e;--sans:'Manrope',system-ui,sans-serif;
--mono:'JetBrains Mono',ui-monospace,monospace}
*{box-sizing:border-box} body{margin:0;background:#fff;color:var(--ink);font-family:var(--sans);line-height:1.45}
.wrap{max-width:1180px;margin:auto;padding:30px 24px 80px}.top{display:flex;align-items:flex-start;justify-content:space-between;gap:24px}
.eyebrow{color:var(--deep);font-size:11px;letter-spacing:.2em;text-transform:uppercase;font-weight:800;margin:0 0 8px}
h1{font-size:clamp(32px,5vw,54px);line-height:1.04;letter-spacing:-.04em;margin:0;font-weight:800}h1 span{font-weight:200;color:var(--deep)}
.sub{max-width:760px;color:var(--muted);font-size:16px;margin:12px 0 0}.brand{display:flex;gap:7px;align-items:center;color:var(--deep);font-weight:800}
.dot{width:14px;height:14px;border-radius:50%;background:var(--matcha);box-shadow:18px 0 0 #a8d7ac,36px 0 0 #dceede;margin-right:36px}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:28px 0 10px}.btn{border:0;border-radius:999px;padding:12px 22px;font:800 12px var(--sans);letter-spacing:.09em;text-transform:uppercase;cursor:pointer}
.btn.run{background:var(--matcha);color:#fff}.btn.run:hover{background:var(--deep)}.btn.refuse{background:#fff5f3;color:var(--bad);border:1px solid #e8b8b2}
.seed{width:96px;padding:10px;border:1px solid var(--line);border-radius:10px;font:600 12px var(--mono)}.status{font:500 12px var(--mono);color:var(--muted)}
.pipeline{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:25px 0}.step{border:1px solid var(--line);border-radius:12px;padding:12px 10px;background:#fff;min-height:76px}
.step b{display:block;color:var(--deep);font-size:12px}.step span{font:400 10px var(--mono);color:var(--muted)}.step.ok{background:var(--wash);border-color:#acd2b1}
.banner{border-left:5px solid var(--matcha);background:var(--wash);padding:18px 20px;border-radius:0 14px 14px 0;margin:18px 0}.banner.bad{border-color:var(--bad);background:#fff5f3}
.banner h2{margin:0;font-size:21px}.banner p{margin:5px 0 0;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:16px 0 28px}.stat{border:1px solid var(--line);border-radius:13px;padding:14px;background:#fff}.stat b{display:block;font-size:22px;color:var(--deep)}.stat span{font:500 10px var(--mono);color:var(--muted);text-transform:uppercase}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}.card{border:1px solid var(--line);border-radius:16px;padding:20px;background:#fff;min-width:0}.card h3{margin:0 0 4px;font-size:18px}.note{color:var(--muted);font-size:12px;margin:0 0 15px}
.plate{display:grid;grid-template-columns:repeat(12,1fr);gap:4px}.well{aspect-ratio:1;border-radius:50%;background:#eef3ef;border:1px solid #d8e4da;display:flex;align-items:center;justify-content:center;font:600 7px var(--mono);color:#637368;cursor:default}
.well.vehicle{background:#dce8fb;border-color:#9ebbe9;color:#285ca7}.well.noenzyme{background:#f2f2f2;border-color:#cfcfcf}.well.candidate{color:#fff;border-color:#fff}
table{border-collapse:collapse;width:100%;font-size:12px}th{text-align:left;color:var(--deep);font:800 10px var(--mono);letter-spacing:.05em;text-transform:uppercase;border-bottom:2px solid var(--line);padding:8px 6px}td{padding:9px 6px;border-bottom:1px solid var(--line)}
.rank{font:600 11px var(--mono)}.hit{color:var(--deep);font-weight:800}.wait{color:var(--gold);font-weight:800}.prov{font:600 10px var(--mono);color:var(--blue)}
.dose{display:grid;grid-template-columns:1.35fr repeat(4,80px);gap:7px;align-items:center;font-size:12px}.dose>div{padding:8px;border-bottom:1px solid var(--line)}.dose .head{font:800 9px var(--mono);color:var(--deep);text-transform:uppercase}.curve{display:block;color:var(--muted);font:500 9px var(--mono);margin-top:3px}.bar{height:8px;background:#deebdf;border-radius:10px;overflow:hidden;margin-top:4px}.bar i{display:block;height:100%;background:var(--matcha)}
.final{margin-top:18px;border:2px solid var(--matcha);border-radius:16px;padding:22px;display:flex;justify-content:space-between;gap:20px;align-items:center}.final strong{font-size:25px;color:var(--deep)}.pill{font:800 10px var(--mono);padding:7px 10px;border-radius:999px;background:var(--wash);color:var(--deep)}
.hidden{display:none}.footer{margin-top:42px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font:500 11px var(--mono);display:flex;justify-content:space-between}
@media(max-width:850px){.pipeline{grid-template-columns:repeat(2,1fr)}.stats{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.top{display:block}.brand{margin-top:18px}.dose{grid-template-columns:1fr repeat(4,56px)}}
</style>
</head>
<body><main class="wrap">
<div class="top"><div><p class="eyebrow">AI for Science World Models Hack &middot; Track A</p><h1>TEM-1 <span>closed loop</span></h1>
<p class="sub">Produce the antibiotic-resistance enzyme, prove it was made, screen candidate inhibitors on robots, read kinetic evidence, and let round 1 observations sharpen round 2.</p></div><div class="brand"><span class="dot"></span>bay-hack</div></div>
<div class="controls"><button class="btn refuse" onclick="proveRefusal()">Prove expression refusal</button><button class="btn run" onclick="runLoop()">Run two-round screen</button><input class="seed" id="seed" value="17" aria-label="simulation seed"><span class="status" id="status">ready &middot; simulation fallback</span></div>
<section id="output" class="hidden">
<div class="pipeline" id="pipeline"></div><div id="banner"></div><div class="stats" id="stats"></div>
<div class="grid2"><section class="card"><h3>Round 1 plate</h3><p class="note">Controls at plate edges. Candidate replicates are spatially separated.</p><div class="plate" id="plate"></div></section>
<section class="card"><h3>Round 1 ranking</h3><p class="note">Selection score is inhibition minus one standard error.</p><div id="ranking"></div></section></div>
<section class="card" style="margin-top:18px"><h3>Round 2 confirmation</h3><p class="note">The top observed candidates return across four organizer-configured dose factors.</p><div class="dose" id="dose"></div></section>
<div class="final" id="final"></div></section>
<footer class="footer"><span>di-omics &middot; two world models, one verified scientific loop</span><span>modeled values stay labeled modeled</span></footer>
</main>
<script>
const $=s=>document.querySelector(s);
const steps=['SYNTHESIZE TEM-1','CONFIRM EXPRESSION','ROUND 1 ROBOT','READ KINETICS','ASSAY QC','ROUND 2','NOMINATE'];
function pipeline(ok=true){$('#pipeline').innerHTML=steps.map((s,i)=>`<div class="step ${ok?'ok':''}"><b>${i+1}. ${s}</b><span>${ok?'evidence recorded':'blocked'}</span></div>`).join('')}
function fmt(v,n=1){return Number(v).toFixed(n)}
function wellMap(round){const values={}; round.candidates.forEach(c=>c.wells.forEach(w=>values[w]=c.mean_inhibition_pct));const roles={};round.plan.assignments.forEach(a=>roles[a.well]=a.role);const rows='ABCDEFGH';let html='';for(const row of rows){for(let c=1;c<=12;c++){const w=row+c,role=roles[w]||'',v=values[w];let cls='well';let style='';if(role==='vehicle_control')cls+=' vehicle';else if(role==='no_enzyme_control')cls+=' noenzyme';else if(role==='candidate'){cls+=' candidate';const light=82-Math.max(0,Math.min(100,v))*.34;style=`background:hsl(128 34% ${light}%);`}html+=`<div class="${cls}" style="${style}" title="${w} ${role} ${v===undefined?'':fmt(v)+'% inhibition'}">${w}</div>`}}return html}
function ranking(round){return `<table><thead><tr><th>#</th><th>compound</th><th>inhibition</th><th>uncertainty</th><th>decision</th></tr></thead><tbody>${round.candidates.map((c,i)=>`<tr><td class="rank">${i+1}</td><td><b>${c.compound_id}</b></td><td>${fmt(c.mean_inhibition_pct,2)}%</td><td>&plusmn;${fmt(c.standard_error_pct,2)}%</td><td class="${c.hit?'hit':'wait'}">${c.hit?'ADVANCE':'HOLD'}</td></tr>`).join('')}</tbody></table>`}
function dose(round){const chosen=round.plan.selection_rationale.selected.map(x=>x.compound_id);const factors=round.plan.selection_rationale.dose_factors;let html=`<div class="head">compound</div>${factors.map(f=>`<div class="head">${f}x</div>`).join('')}`;for(const id of chosen){const summary=round.dose_response.find(x=>x.compound_id===id);const crossing=summary.inhibition_50_status==='interpolated'?`I50 ~${fmt(summary.inhibition_50_factor_estimate,2)}x`:`I50 ${summary.inhibition_50_status.replaceAll('_',' ')}`;html+=`<div><b>${id}</b><span class="curve">${crossing} &middot; ${summary.monotonic_with_uncertainty?'monotonic':'inspect curve'}</span></div>`;for(const f of factors){const c=round.candidates.find(x=>x.compound_id===id&&x.concentration_factor===f);const v=c?c.mean_inhibition_pct:0;html+=`<div>${fmt(v)}%<div class="bar"><i style="width:${Math.max(0,Math.min(100,v))}%"></i></div></div>`}}return html}
async function runLoop(){const seed=parseInt($('#seed').value||17);$('#status').textContent='running two gated rounds...';const r=await fetch(`/api/run?seed=${seed}`);const d=await r.json();render(d)}
function render(d){$('#output').classList.remove('hidden');pipeline(true);const e=d.protein_synthesis.confirmation,r1=d.rounds[0],r2=d.rounds[1],f=d.follow_up;const replay=d.mode==='receipt-replay';$('#status').textContent=replay?'safe receipt replay · zero hardware commands':'simulation complete · physical protocol still locked';$('#banner').innerHTML=`<div class="banner"><h2>TEM-1 expression confirmed before screening</h2><p>${fmt(e.fold_over_background,2)}x over no-template control &middot; expression CV ${fmt(e.expression_cv_pct,2)}% &middot; <span class="prov">${e.provenance.toUpperCase()}</span></p></div>`;$('#stats').innerHTML=`<div class="stat"><b>${fmt(e.fold_over_background,1)}x</b><span>expression / background</span></div><div class="stat"><b>${fmt(r1.assay_qc.z_prime,3)}</b><span>round 1 Z-prime</span></div><div class="stat"><b>${r2.plan.selection_rationale.selected.length}</b><span>compounds advanced</span></div><div class="stat"><b>${fmt(f.inhibition_50_factor_estimate,2)}x</b><span>relative I50 estimate</span></div><div class="stat"><b>${fmt(f.mean_inhibition_pct,1)}%</b><span>best inhibition</span></div>`;$('#plate').innerHTML=wellMap(r1);$('#ranking').innerHTML=ranking(r1);$('#dose').innerHTML=dose(r2);$('#final').innerHTML=`<div><span class="pill">FOLLOW-UP EXECUTED</span><br><strong>${f.compound_id} at ${f.concentration_factor}x nominated</strong><div class="note" style="margin:6px 0 0">${fmt(f.mean_inhibition_pct,2)}% ${f.provenance} inhibition &middot; relative I50 ${fmt(f.inhibition_50_factor_estimate,2)}x &middot; monotonic curve ${f.dose_response_monotonic?'PASS':'REVIEW'}</div></div><div class="pill">${d.mode.toUpperCase()}</div>`}
async function proveRefusal(){const r=await fetch('/api/refusal');const d=await r.json();$('#output').classList.remove('hidden');pipeline(false);$('#status').textContent='screen refused before compound execution';$('#banner').innerHTML=`<div class="banner bad"><h2>REFUSED: TEM-1 expression not confirmed</h2><p>${d.confirmation.reasons.join('; ')}. Compound wells read: ${d.compound_screen.wells_read}. Model updated: ${d.world_model.updated}. Round 2 planned: ${d.round2.planned}.</p></div>`;$('#stats').innerHTML=`<div class="stat"><b>${fmt(d.confirmation.fold_over_background||1,2)}x</b><span>expression / background</span></div><div class="stat"><b>0</b><span>compound wells read</span></div><div class="stat"><b>0</b><span>model updates</span></div><div class="stat"><b>0</b><span>round 2 plans</span></div><div class="stat"><b>0</b><span>commands after failure</span></div>`;$('#plate').innerHTML='';$('#ranking').innerHTML='<p class="note">No compound result exists because the upstream biological gate failed.</p>';$('#dose').innerHTML='<div class="head">round 2 blocked</div>';$('#final').innerHTML='<div><strong>Recovery: inspect protein synthesis controls</strong><div class="note">Do not turn background noise into an inhibitor claim.</div></div>'}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        elif parsed.path == "/api/run":
            try:
                if RECEIPT_PATH is not None:
                    payload = replay_tem1_receipt(RECEIPT_PATH)
                else:
                    seed = int(parse_qs(parsed.query).get("seed", ["17"])[0])
                    payload = run_simulated_closed_loop(seed=seed)
                body = json.dumps(payload).encode()
                self.send_response(200)
            except (ValueError, TEM1Error, TEM1ReceiptError) as exc:
                body = json.dumps({"error": str(exc)}).encode()
                self.send_response(400)
            self.send_header("Content-Type", "application/json")
        elif parsed.path == "/api/refusal":
            body = json.dumps(run_expression_refusal()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        else:
            body = b"not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="serve the TEM-1 Track A dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument(
        "--receipt",
        help="replay a saved TEM-1 receipt without issuing hardware commands",
    )
    args = parser.parse_args()
    global RECEIPT_PATH
    RECEIPT_PATH = Path(args.receipt) if args.receipt else None
    if RECEIPT_PATH is not None:
        replay_tem1_receipt(RECEIPT_PATH)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"TEM-1 dashboard: http://{args.host}:{args.port}")
    print(
        f"mode: safe receipt replay ({RECEIPT_PATH})"
        if RECEIPT_PATH else "mode: deterministic simulation"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
