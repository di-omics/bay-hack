# KICKOFF_PROMPT.md — paste into Claude Code (inside `bay-hack/`)

Prereqs so CC can wire + push: have your repos available locally as siblings
(e.g. `../plr-mcp`, `../plr-lab-robot`, `../plr-epigenome`, `../ml-bio-eval`),
be signed in with `gh auth login`, and (optional) `export ANTHROPIC_API_KEY=…`.

---

You are my build partner on **bay-hack**, the Track-A integration repo for the
AI for Science World Models Hack. The job is to **compose my existing @di-omics
repos** into one closed loop and bridge it to Zeon — not to reimplement anything.

**Orient first (before code):**
1. Read `STRATEGY.md`, `CLAUDE.md`, and `bayhack/loop.py`.
2. Run `python -m bayhack.demo` and `pytest -q`; confirm both green.
3. Restate in 5 bullets: the loop stages, which of my repos fills each SEAM, the
   golden rules, and the Zeon-bridge plan.

**Golden rules (never violate):**
- Compose, don't reimplement — import `plr_mcp`, `plr_lr`, `tipseq_plr`, and the
  `ml-bio-eval` components; replace the stdlib stand-ins in `bayhack/loop.py`.
- Keep `python -m bayhack.demo` + `pytest -q` GREEN at all times (the pure-sim
  path must run with no hardware and no heavy deps; lazy-import the real modules).
- Physically-trustworthy reads (Rhodamine + CV pass) train the world model; the
  conformal gate only decides accept/escalate.
- The Zeon bridge is upside, not a dependency.

**Git workflow — every step, automatically:**
- If no `origin`: `gh repo create bay-hack --public --source=. --remote=origin --push`
  (if `gh` is unavailable, stop and ask me for the URL).
- Per step: branch `feat/<name>`, implement, run demo + tests, and only if green
  → conventional commit → push → merge to `main`. Keep `main` green and pushed.
  After each step print: what changed, demo/test status, commit hash, branch.

**Build order (push after each green step):**

0. **Wire deps.** Add `plr-mcp`, `plr-lab-robot`, `plr-epigenome`, and the
   `ml-bio-eval` components as optional/dev dependencies (editable installs from
   the sibling repos). Keep them out of the core sim import path.

1. **Execute seam → plr-mcp.** Replace `bayhack/loop.py`'s `Bench.run_design`
   and `rhodamine_series` with real calls: `plr_setup_deck` (chatterbox), then
   `plr_transfer`/`plr_aspirate`/`plr_dispense` to build the reaction, then
   `plr_read_plate(mode="fluorescence")`. Import `plr_mcp.lab.Lab` for
   programmatic use. Keep a `--sim` flag that falls back to the stdlib Bench.

2. **Verify seam → Rhodamine + CV.** Replace `rhodamine_gate` with
   `tipseq_plr.validation.rhodamine` and wire a `steps/vision.py` `SimVision`
   checkpoint into the loop. The loop must refuse to trust a read that fails
   either gate.

3. **Design + Learn seams → ml-bio-eval.** Replace `WorldModel` with the
   `lab-world-model` GP + ParEGO acquisition, and `conformal_gate` with the
   split-conformal accept/reject/escalate gate. Preserve plant-and-recover
   scoring (report runs-to-recover vs a grid baseline).

4. **Plan seam → sow.** Add an entrypoint that takes an English goal, runs
   `tipseq_plr.sow` to compile it (with its validation tier), and feeds the
   compiled design space into the loop.

5. **Dexterity beat → plr_lr.** Add a `Workcell.sim()` step that moves the plate
   to the reader and performs a `vision_guided_pick` + `DecapSkill` uncap,
   logged as a physical-verification checkpoint. (Track C bonus.)

6. **Demo surface.** A single-file dashboard/CLI: goal ▸ world-model proposal ▸
   MCP execution ▸ fluorescence + Rhodamine/CV gates ▸ convergence curve ▸ the
   backend-swap-to-Zeon beat. Runs on the pure-sim path with zero hardware.

7. **Zeon bridge shape.** Flesh out `bayhack/zeon_bridge.py::ZeonArmBackend` to
   match the arm backend interface `plr_lr` targets (setup/home/move/gripper),
   with clear TODOs for the on-site SDK. Add a `--arm zeon` switch that would
   route the same loop through it. Do NOT block the demo on it.

**Also expose the MCP beat:** document how to run my `plr-mcp` server and have an
agent (Claude) drive the loop over MCP — that's the "Physical MCP" pitch moment.

**Final report:** repo URL + latest `main` hash, how to run the demo, how to run
it against real chatterbox PLR, and exactly what's left for on-site (ZeonArm SDK,
camera calibration, hardware confirms).

Start with step 0. Confirm your 5-bullet plan first, then go.
