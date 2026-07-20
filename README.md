# 🧪🤖 bay-hack

**A world model runs the bench.** Track-A entry for the 24hr AI for Science
World Models Hack @ Zeon Systems (Jul 25–26, SF).

**Live site:** https://di-omics.github.io/bay-hack/ &middot; **Pitch slide:** [docs/slide.html](docs/slide.html)

bay-hack is the **glue** that composes the [@di-omics](https://github.com/di-omics)
autonomous-lab stack into one closed loop, plus a **bridge to Zeon's platform**.
It is deliberately thin — the heavy lifting already lives in your repos.

> Plain-English goal → a **GP world model** proposes the next experiment → an
> agent executes it on a real (sim-first) liquid handler **through plr-mcp** →
> fluorescence + a **Rhodamine-B gate** + **CV** verify it physically → a
> **conformal QC gate** decides accept/escalate → repeat → then swap one backend
> and the same loop drives **Zeon's arm**.

See **[STRATEGY.md](STRATEGY.md)** for the full winning plan, demo script, and
6-day countdown.

## Run the loop now (pure simulation, stdlib only)

```bash
python -m bayhack.demo
```

You'll watch the world model recover a planted optimum in ~6 runs vs ~26 for a
grid sweep, with the Rhodamine gate and conformal gate gating each round.

## Run it for real — against the @di-omics stack, still no hardware

```bash
pip install -e ../plr-mcp -e ../plr-epigenome -e ../plr-lab-robot
PYTHONPATH=../../ml-bio-eval/lab-world-model \
  python -m bayhack.demo --real
```

`bayhack/seams.py` holds lazy adapters that swap the stdlib stand-ins for your
actual code — **verified to run with no instrument**:

- **Execute** → `plr_mcp.lab.Lab` (chatterbox) runs the real pick/aspirate/
  dispense/read choreography.
- **Verify** → `tipseq_plr.validation.evaluate` (the real Rhodamine gate, reaches
  `tier=liquid_tested`, R²=1.0) + `tipseq_plr.steps.vision.SimVision`.
- **Design/Learn** → `labworld` GP + ParEGO + the split-conformal QC gate
  (empirical coverage ~0.90 at α=0.10).
- **Plan** → `tipseq_plr.sow` compiles English → a routed protocol.
- **Dexterity** → `plr_lr` `Workcell.sim()` moves a plate between taught sites.

**Honest by design (so it survives judge questions):**
- PyLabRobot 0.2.1's chatterbox plate reader returns zeros — decoupled from what
  was dispensed — so the numeric fluorescence stays **modeled** until a real
  reader + reagents are wired on-site. The pipetting/read *choreography* is real.
- Compiled protocols report `validation_tier=untested`; nothing is promoted to
  `liquid_tested`/`biovalidated` until real Rhodamine data clears the gate.

## What composes into what

`bayhack/loop.py` is the orchestrator. Every stage is a **SEAM** to a real repo:

| Stage | SEAM → your repo |
|---|---|
| Design (propose next) | `ml-bio-eval/lab-world-model` — GP + ParEGO |
| Build / Test (execute) | `plr-mcp` — `plr_setup_deck`, `plr_transfer`, `plr_read_plate` |
| Move / dexterity | `plr-lab-robot` (`plr_lr`) — `Workcell`, `vision_guided_pick`, `DecapSkill` |
| Verify (volumes) | `plr-epigenome` — `validation/rhodamine.py` |
| Verify (steps) | `plr-epigenome` `steps/vision.py` + `lab-cv` |
| Learn (gate) | `ml-bio-eval` — split-conformal accept/reject/escalate |
| Plan (NL → protocol) | `plr-epigenome` — `tipseq_plr/sow.py` |
| **Bridge** | `bayhack/zeon_bridge.py` — a PyLabRobot arm backend for Zeon |

Out of the box those seams use tiny stdlib stand-ins so the loop runs with
nothing installed. The real adapters live in **[`bayhack/seams.py`](bayhack/seams.py)**
and fire when the repos are installed (`python -m bayhack.demo --real`, above) —
see **[KICKOFF_PROMPT.md](KICKOFF_PROMPT.md)** and **[CLAUDE.md](CLAUDE.md)** for
the on-site build order (real reader, hardware confirms, the Zeon arm backend).

## Wire it up

```bash
# from a folder containing your repos as siblings
pip install -e ../plr-mcp -e ../plr-lab-robot -e ../plr-epigenome
# ml-bio-eval components install per-folder (see its README)
```

Then open Claude Code in this folder and paste `KICKOFF_PROMPT.md`.

## The Zeon bridge (the win)

Zeon doesn't use PyLabRobot. Write a PLR arm backend that targets their platform
(`bayhack/zeon_bridge.py`), and the whole PLR ecosystem + your DBTL loop +
Rhodamine validation run on Zeon hardware. Prep the shape now; wire their SDK
on-site. Pure-PLR loop is the guaranteed fallback.

MIT licensed.
