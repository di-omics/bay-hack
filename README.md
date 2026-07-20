# 🧪🤖 bay-hack

**A world model runs the bench.** Track-A entry for the 24hr AI for Science
World Models Hack @ Zeon Systems (Jul 25–26, SF).

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
nothing installed. On your machine, Claude Code swaps in the real modules — see
**[KICKOFF_PROMPT.md](KICKOFF_PROMPT.md)** and **[CLAUDE.md](CLAUDE.md)**.

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
