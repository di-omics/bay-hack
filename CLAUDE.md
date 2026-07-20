# CLAUDE.md — working in bay-hack

Context for Claude Code. Read before editing.

## What this is
The **integration/glue** repo for a hackathon Track-A demo. It composes the
@di-omics stack into one closed loop and bridges it to Zeon. It is NOT a place
to reimplement lab-automation primitives — those already exist and are better
than anything written from scratch here.

Pipeline: `sow` (plan) → world model (design) → `plr-mcp` (build/test) →
Rhodamine + CV (verify) → conformal gate (learn) → repeat → Zeon bridge.

## Golden rules
1. **Compose, don't reimplement.** Prefer importing the real repos
   (`plr_mcp`, `plr_lr`, `tipseq_plr`, `ml-bio-eval` components) over writing new
   logic. Each stage in `bayhack/loop.py` is a SEAM naming the real module.
2. **Simulation-first.** `python -m bayhack.demo` must always run and converge
   with zero hardware and zero heavy deps (stdlib stand-ins are the fallback).
   Never make the sim path import pylabrobot/mcp/etc. at module load — lazy
   import inside the swap.
3. **Keep the demo + tests green** before every commit (`python -m bayhack.demo`,
   `pytest -q`).
4. **Trust before promote.** Physically-trustworthy measurements (Rhodamine +
   CV pass) train the world model; the conformal gate decides accept/escalate.
   Don't let the model learn from unverified reads.
5. **The Zeon bridge is upside, not a dependency.** Everything must still demo
   on the pure-PLR path if Zeon exposes no SDK.

## Swapping seams (the real work)
- Design → `ml-bio-eval/lab-world-model` (GP surrogate + ParEGO acquisition).
- Execute → `plr_mcp.lab.Lab` for programmatic calls, and/or the `plr-mcp`
  server for the "agent drives it over MCP" demo beat. Chatterbox backend first;
  `star`/`ot2`/`evo` only with hardware and human-gated `confirm=true`.
- Move/dexterity → `plr_lr` `Workcell.sim()`, `vision_guided_pick`, `DecapSkill`.
- Verify → `tipseq_plr.validation.rhodamine` (R²≥0.995 gate) + `steps/vision.py`
  (`SimVision` now, `LabCvVision` on-site).
- Learn → `ml-bio-eval` split-conformal accept/reject/escalate gate.
- Plan → `tipseq_plr.sow` (`sow plan --text` / `sow run --text`).
- Bridge → implement `bayhack/zeon_bridge.py::ZeonArmBackend` against Zeon's SDK.

## Do NOT
- Do not add heavy deps to the sim path.
- Do not remove the stdlib fallback or the `--sim` demo.
- Do not drive real hardware without the repos' existing human-gated confirms.
