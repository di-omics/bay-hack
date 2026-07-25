"""Matcha stage dashboard for Track C verified tube access."""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .track_c import (
    SimulatedTubeCell,
    run_simulated_tube_access,
    verify_track_c_receipt,
)


RECEIPT_PATH: Path | None = None


class TrackCReceiptError(RuntimeError):
    """A Track C receipt cannot be safely replayed."""


def replay_track_c_receipt(path: str | Path) -> dict:
    source = Path(path)
    try:
        payload = json.loads(source.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TrackCReceiptError(f"cannot read Track C receipt: {source}") from exc
    if payload.get("track") != "Track C: Dexterity and Physical Verification":
        raise TrackCReceiptError("receipt is not a Track C tube-access run")
    if not verify_track_c_receipt(payload):
        raise TrackCReceiptError("Track C receipt integrity check failed")
    replay = dict(payload)
    replay["source_mode"] = payload.get("mode", "unknown")
    replay["mode"] = "receipt-replay"
    replay["receipt_path"] = str(source)
    replay["hardware_commands_issued_by_replay"] = 0
    return replay


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>bay-hack | TubeProof</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@200;400;500;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--matcha:#5cae5a;--deep:#3c8446;--ink:#28372a;--wash:#f2f8f3;--line:#e3eee5;--muted:#6f8274;--bad:#b23a2e;--gold:#a96f13;--blue:#2f6fd6;--sans:'Manrope',system-ui,sans-serif;--mono:'JetBrains Mono',ui-monospace,monospace}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--ink);font-family:var(--sans);line-height:1.45}.wrap{max-width:1180px;margin:auto;padding:28px 24px 70px}
.top{display:flex;justify-content:space-between;gap:30px;align-items:flex-start}.eyebrow{margin:0 0 8px;color:var(--deep);font-size:11px;font-weight:800;letter-spacing:.19em;text-transform:uppercase}h1{font-size:clamp(36px,6vw,62px);line-height:.98;letter-spacing:-.055em;margin:0;font-weight:800}h1 span{font-weight:200;color:var(--deep)}.sub{max-width:790px;color:var(--muted);font-size:16px;margin:14px 0 0}.brand{display:flex;align-items:center;gap:10px;color:var(--deep);font-weight:800;white-space:nowrap}.brandmark{width:36px;height:36px;border:3px solid var(--matcha);border-radius:50%;position:relative}.brandmark:before{content:'';position:absolute;width:8px;height:19px;border:3px solid var(--matcha);border-top:0;left:11px;top:7px;border-radius:0 0 6px 6px}
.claims{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}.chip{padding:7px 10px;border-radius:999px;background:var(--wash);color:var(--deep);font:700 10px var(--mono);text-transform:uppercase}.chip.mode{background:#eef3fb;color:var(--blue)}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:24px 0 12px}.btn{border-radius:999px;padding:12px 20px;font:800 11px var(--sans);letter-spacing:.07em;text-transform:uppercase;cursor:pointer}.btn.clean{border:0;background:var(--matcha);color:#fff}.btn.fault{border:1px solid #d6b977;background:#fffaf0;color:var(--gold)}.btn.stop{border:1px solid #e7b2ad;background:#fff7f5;color:var(--bad)}.btn:hover{transform:translateY(-1px)}.status{font:500 11px var(--mono);color:var(--muted)}
.pipeline{display:grid;grid-template-columns:repeat(7,1fr);gap:8px;margin:24px 0}.step{border:1px solid var(--line);border-radius:12px;padding:11px 9px;background:#fff;min-height:74px}.step b{display:block;color:var(--deep);font-size:11px}.step span{font:400 9px var(--mono);color:var(--muted)}.step.ok{background:var(--wash);border-color:#acd2b1}.step.retry{background:#fffaf0;border-color:#dec78e}.step.hold{background:#fff5f3;border-color:#e2aaa4}
.banner{border-left:5px solid var(--matcha);background:var(--wash);padding:18px 20px;border-radius:0 14px 14px 0;margin:18px 0}.banner.bad{border-color:var(--bad);background:#fff5f3}.banner h2{margin:0;font-size:22px}.banner p{margin:5px 0 0;color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0 24px}.stat{border:1px solid var(--line);border-radius:13px;padding:14px}.stat b{display:block;font-size:21px;color:var(--deep)}.stat span{font:500 9px var(--mono);color:var(--muted);text-transform:uppercase}
.grid2{display:grid;grid-template-columns:.85fr 1.15fr;gap:18px}.card{border:1px solid var(--line);border-radius:16px;padding:20px;min-width:0}.card h3{margin:0 0 5px;font-size:18px}.note{margin:0 0 16px;color:var(--muted);font-size:12px}
.cell{height:318px;background:linear-gradient(180deg,#fbfdfb,#f0f7f1);border-radius:14px;position:relative;overflow:hidden;border:1px solid var(--line)}.fixture{position:absolute;left:50%;bottom:25px;transform:translateX(-50%);width:230px;height:44px;background:#dcebdd;border:2px solid #a8cfac;border-radius:15px 15px 7px 7px}.fixture:after{content:'SELF-ALIGNING FIXTURE';position:absolute;bottom:-21px;left:37px;color:var(--deep);font:700 8px var(--mono);letter-spacing:.08em}.tube{position:absolute;left:50%;bottom:55px;transform:translateX(-50%);width:76px;height:148px;background:rgba(255,255,255,.78);border:3px solid #7fae84;border-radius:9px 9px 22px 22px}.tube:after{content:'';position:absolute;left:9px;right:9px;bottom:14px;height:55px;background:linear-gradient(180deg,#b5dfb8,#6db974);border-radius:4px 4px 14px 14px}.cap{position:absolute;left:50%;bottom:197px;transform:translateX(-50%);width:88px;height:44px;background:repeating-linear-gradient(90deg,#3c8446 0,#3c8446 5px,#5cae5a 5px,#5cae5a 9px);border-radius:10px 10px 5px 5px;transition:.5s}.cap.open{left:78%;bottom:64px;transform:rotate(8deg)}.camera{position:absolute;right:18px;top:18px;width:54px;height:38px;background:#fff;border:2px solid var(--deep);border-radius:8px}.camera:after{content:'';position:absolute;width:16px;height:16px;border:3px solid var(--matcha);border-radius:50%;left:16px;top:8px}.ray{position:absolute;right:62px;top:53px;width:135px;border-top:2px dashed #a6cba9;transform:rotate(28deg);transform-origin:right}.state-label{position:absolute;left:18px;top:18px;padding:7px 10px;border-radius:999px;background:#fff;color:var(--deep);font:700 10px var(--mono);box-shadow:0 2px 10px #dfe9e0}
.verify{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.vcard{border:1px solid var(--line);border-radius:12px;padding:12px}.vcard b{display:block;color:var(--deep)}.vcard span{display:block;color:var(--muted);font:500 9px var(--mono);margin-top:3px}.confidence{height:6px;border-radius:8px;background:#e7eee8;margin-top:9px;overflow:hidden}.confidence i{display:block;height:100%;background:var(--matcha)}
.timeline{max-height:390px;overflow:auto;padding-right:4px}.event{display:grid;grid-template-columns:28px 112px 1fr;gap:8px;padding:9px 0;border-bottom:1px solid var(--line);align-items:start}.seq{width:23px;height:23px;border-radius:50%;background:var(--wash);color:var(--deep);display:flex;align-items:center;justify-content:center;font:700 9px var(--mono)}.event.retry .seq{background:#fff1cf;color:var(--gold)}.event.fail .seq{background:#ffe5e1;color:var(--bad)}.event b{font:700 9px var(--mono);color:var(--deep);text-transform:uppercase}.event p{margin:0;color:var(--muted);font-size:11px}.event small{display:block;color:var(--blue);font:500 8px var(--mono);margin-top:3px}
.rule{margin-top:18px;border:2px solid var(--matcha);border-radius:16px;padding:18px;display:flex;justify-content:space-between;gap:18px;align-items:center}.rule strong{font-size:20px;color:var(--deep)}.rule code{font:700 10px var(--mono);color:var(--deep);background:var(--wash);padding:8px 10px;border-radius:9px}.footer{margin-top:38px;padding-top:17px;border-top:1px solid var(--line);display:flex;justify-content:space-between;color:var(--muted);font:500 10px var(--mono)}
@media(max-width:850px){.top{display:block}.brand{margin-top:18px}.pipeline{grid-template-columns:repeat(2,1fr)}.stats{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.event{grid-template-columns:28px 95px 1fr}.rule{display:block}.rule code{display:inline-block;margin-top:10px}}
</style>
</head>
<body><main class="wrap">
<div class="top"><div><p class="eyebrow">AI for Science World Models Hack &middot; Track C</p><h1>TUBE<span>PROOF</span></h1><p class="sub">A robot uncaps a lab tube, independently verifies that it is open, presents it for liquid handling, then recaps and verifies closure. Ambiguity triggers recovery or a safe stop.</p></div><div class="brand"><span class="brandmark"></span>bay-hack</div></div>
<div class="claims"><span class="chip">Dexterous manipulation</span><span class="chip">Physical verification</span><span class="chip">Failure recovery</span><span class="chip">Liquid-handling ready</span><span class="chip mode">Simulation labeled</span></div>
<div class="controls"><button class="btn clean" onclick="run('none')">Run clean loop</button><button class="btn fault" onclick="run('partial_uncap')">Inject partial uncap</button><button class="btn stop" onclick="run('persistent_open_ambiguity')">Prove safe stop</button><span id="status" class="status">ready</span></div>
<div id="pipeline" class="pipeline"></div>
<div id="banner" class="banner"><h2>Ready to prove the physical state</h2><p>Run the partial-uncap scenario for the strongest demo beat.</p></div>
<div class="stats"><div class="stat"><b id="openStat">waiting</b><span>cap-off gate</span></div><div class="stat"><b id="pipetteStat">locked</b><span>pipette handoff</span></div><div class="stat"><b id="closedStat">waiting</b><span>closure gate</span></div><div class="stat"><b id="retryStat">0</b><span>recoveries</span></div></div>
<div class="grid2"><section class="card"><h3>Physical world state</h3><p class="note">The camera observation is a separate evidence stream from the motion command.</p><div class="cell"><span id="stateLabel" class="state-label">CAPPED</span><div class="camera"></div><div class="ray"></div><div id="cap" class="cap"></div><div class="tube"></div><div class="fixture"></div></div><div class="verify"><div class="vcard"><b>Open check</b><span id="openEvidence">not observed</span><div class="confidence"><i id="openBar" style="width:0"></i></div></div><div class="vcard"><b>Closed check</b><span id="closedEvidence">not observed</span><div class="confidence"><i id="closedBar" style="width:0"></i></div></div></div></section>
<section class="card"><h3>Verified action trace</h3><p class="note">Every motion, observation, decision, and recovery remains visible.</p><div id="timeline" class="timeline"></div></section></div>
<div class="rule"><div><strong>No verified opening, no pipetting.</strong><br><span class="note">No verified closure, no completed run.</span></div><code>observe &gt; act &gt; verify &gt; recover</code></div>
<footer class="footer"><span>di-omics &middot; Track C &middot; 2026</span><span>VERIFY FIRST &middot; PIPETTE SECOND</span></footer>
</main>
<script>
const stages=[['observe_capped','Observe'],['localize','Localize'],['grasp_cap','Grasp'],['unscrew','Uncap'],['verify_open','Verify open'],['present_for_pipetting','Pipette handoff'],['verify_closed','Verify closed']];
const pipeline=document.getElementById('pipeline');
function resetPipeline(){pipeline.innerHTML=stages.map(([key,label])=>`<div class="step" data-stage="${key}"><b>${label}</b><span>waiting</span></div>`).join('')}
resetPipeline();
function esc(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function markPipeline(events){resetPipeline();for(const [key] of stages){const matches=events.filter(e=>e.state===key);if(!matches.length)continue;const node=pipeline.querySelector(`[data-stage="${key}"]`);const recovery=matches.some(e=>e.kind==='recovery');const failed=matches.some(e=>!e.passed)&&!matches.some(e=>e.passed&&e.kind!=='recovery');node.classList.add(failed?'hold':recovery?'retry':'ok');node.querySelector('span').textContent=failed?'stopped':recovery?'recovered':'verified'}}
function observationCard(prefix,obs){const label=document.getElementById(prefix+'Evidence');const bar=document.getElementById(prefix+'Bar');if(!obs){label.textContent='not observed';bar.style.width='0';return}label.textContent=`${obs.state} · ${(obs.confidence*100).toFixed(0)}% · ${obs.provenance}`;bar.style.width=`${obs.confidence*100}%`}
function render(data){const gates=data.gates;markPipeline(data.events);document.getElementById('openStat').textContent=gates.open_verified?'verified':'held';document.getElementById('pipetteStat').textContent=gates.pipetting_allowed?'unlocked':'locked';document.getElementById('closedStat').textContent=gates.closed_verified?'verified':'held';document.getElementById('retryStat').textContent=data.recoveries;observationCard('open',data.verification.open);observationCard('closed',data.verification.closed);const cap=document.getElementById('cap');const stateLabel=document.getElementById('stateLabel');cap.classList.toggle('open',gates.open_verified&&!gates.closed_verified);stateLabel.textContent=gates.closed_verified?'RECLOSED':gates.open_verified?'OPEN VERIFIED':'CAPPED OR AMBIGUOUS';const banner=document.getElementById('banner');banner.classList.toggle('bad',data.status!=='VERIFIED_COMPLETE');banner.innerHTML=data.status==='VERIFIED_COMPLETE'?`<h2>Verified complete</h2><p>${esc(data.reason)}. ${data.recoveries} recoveries. Receipt ${esc(data.integrity.digest.slice(0,16))}...</p>`:`<h2>Safe stop</h2><p>${esc(data.reason)}. Liquid handling stayed ${gates.pipetting_allowed?'unlocked after an earlier verified opening':'locked'}.</p>`;document.getElementById('timeline').innerHTML=data.events.map(e=>{const cls=e.kind==='recovery'?'retry':!e.passed?'fail':'';const prov=e.evidence&&e.evidence.provenance?e.evidence.provenance:'';return `<div class="event ${cls}"><span class="seq">${e.sequence}</span><b>${esc(e.state.replaceAll('_',' '))}<small>${esc(e.kind)}</small></b><p>${esc(e.detail)}${prov?`<small>${esc(prov)}</small>`:''}</p></div>`}).join('')}
async function run(fault){document.getElementById('status').textContent='running '+fault.replaceAll('_',' ')+'...';try{const response=await fetch('/api/run?fault='+encodeURIComponent(fault));const data=await response.json();if(!response.ok)throw new Error(data.error||'run failed');render(data);document.getElementById('status').textContent=data.status+' · simulated execution'}catch(err){document.getElementById('status').textContent='error: '+err.message}}
run('partial_uncap');
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(PAGE.encode(), "text/html; charset=utf-8")
            return
        if parsed.path == "/api/run":
            try:
                if RECEIPT_PATH is not None:
                    payload = replay_track_c_receipt(RECEIPT_PATH)
                else:
                    fault = parse_qs(parsed.query).get("fault", ["none"])[0]
                    if fault not in SimulatedTubeCell.FAULTS:
                        raise ValueError(f"unknown fault: {fault}")
                    payload = run_simulated_tube_access(fault)
                body = json.dumps(payload).encode()
                self._send(body, "application/json")
            except (ValueError, TrackCReceiptError) as exc:
                self._send(
                    json.dumps({"error": str(exc)}).encode(),
                    "application/json",
                    400,
                )
            return
        self._send(b"not found", "text/plain; charset=utf-8", 404)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="serve the Track C dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    global RECEIPT_PATH
    RECEIPT_PATH = Path(args.receipt) if args.receipt else None
    if RECEIPT_PATH is not None:
        replay_track_c_receipt(RECEIPT_PATH)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Track C dashboard: http://{args.host}:{args.port}")
    if RECEIPT_PATH is not None:
        print(f"receipt replay: {RECEIPT_PATH} (zero motion)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
