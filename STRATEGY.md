# 🏆 bay-hack — Winning Strategy

**24hr AI for Science World Models Hack @ Zeon Systems** · Jul 25–26, SF · Track A
**You (@di-omics):** full-stack biologist, PyLabRobot power-user, an entire autonomous-lab stack already built.
**Today:** Sun Jul 19 → **6 days out.** This is a *composition + pitch* job, not a build-from-scratch.

---

## 0. The one-liner

> **A world model runs the bench.** An agent turns a plain-English goal into a validated protocol, a **GP world model proposes the next experiment**, it executes on a real (sim-first) liquid handler **through your MCP server**, fluorescence + a **Rhodamine-B gate** + CV **physically verify** it, a **conformal QC gate** decides accept/escalate, and it converges in far fewer runs than brute force — then the *same code* drives **Zeon's arm** via a one-line backend swap.

Every word of that is something you've already shipped. bay-hack just wires them into one demo and adds the Zeon bridge.

---

## 1. Isn't there already something here? — Yes. You have ~90% of it.

Here's the map from the hack's asks to your repos. This is your unfair advantage: almost nobody shows up with *validated-on-real-hardware* pieces.

| Loop stage (Track A) | Your repo / module | What it gives the demo |
|---|---|---|
| **Plan** (NL → protocol) | `plr-epigenome` → `tipseq_plr/sow.py` | Statement-of-Work compiler: `sow plan --text "…"` → runnable method **with a validation tier attached**. This is Zeon's "English → run," but *honest about trust*. |
| **Design** (what next) | `ml-bio-eval/lab-world-model` | **GP world model + multi-objective BO (ParEGO)** proposes the next experiment. ~29% fewer runs than random. **This is the "World Models" theme, literally.** |
| **Execute** (Physical MCP) | `plr-mcp` (`plr_setup_deck`, `plr_transfer`, `plr_read_plate`) | The host evangelizes "Physical MCPs." You *built the MCP server for PyLabRobot.* Chatterbox sim by default, `star`/`ot2`/`evo` real backends. |
| **Move / dexterity** | `plr-lab-robot` (`plr_lr`: `Workcell.sim()`, `vision_guided_pick`, `DecapSkill`) | Arm plate moves, **eye-in-hand vision** (7 mm→sub-mm correction), **dexterous uncapping**. Covers Track C too. |
| **Measure** | `plr-mcp` `plr_read_plate` (fluorescence) + `ml-bio-eval` Cytation read | Real readout in the loop. |
| **Verify (volumes)** | `plr-epigenome` → `validation/rhodamine.py` | **Rhodamine-B gate**: R²≥0.995, accuracy/CV within tolerance. Proof the robot dispensed what the code said. *This is the differentiator judges remember.* |
| **Verify (steps)** | `plr-epigenome` `steps/vision.py` + `lab-cv` | CV checkpoints at the reader-blind moments (bead loss, no pellet). Catches *execution* faults the reader can't. |
| **Learn** (close loop) | `ml-bio-eval` conformal gate + `plr-minimum-effective` | Split-conformal **accept/reject/escalate** with a coverage guarantee; auto-decides ~79% at zero error. Plant-and-recover scoring. |
| **Credibility** | `plr-tested` (Hamilton STAR, real) + `benchmarks`/`omics-demos` | You don't just sim — you've run it, and you score everything against planted ground truth. |

**What to leave out** (don't dilute the demo): the deep omics analysis (`fullstack-omics` bioinformatics), `blastocyst-if`, `awesome-wetlab-cv`, `ot-flex-automation`. Keep them as "and I've also built…" depth for judge Q&A, not on the critical demo path.

---

## 2. The winning play: the Zeon bridge 🔌

**Zeon's stack is vision-first, not PyLabRobot-based.** They built an NL→computer-vision→arm platform (off-the-shelf arms + depth cameras, general-purpose). PyLabRobot is the established open ecosystem (Hamilton, Tecan, Opentrons, plate readers) — and *you* bring the validation rigor that makes automation trustworthy for serious labs.

So the move that turns heads:

> **Write a PyLabRobot backend that targets Zeon's arm** (shape it like `plr_lr`'s `SimulationArmBackend`/`SCARABackend`, or `plr-epigenome`'s `robot_arm.py` `RobotArmBackend`). The moment it works, *the entire PyLabRobot protocol library — plus your DBTL loop, Rhodamine validation, and conformal gate — runs on Zeon's platform.* You'd hand Zeon instant compatibility with the whole open lab-automation world **and** the reliability layer (sim-first verify + fluorescent ladders + conformal QC) they need to be trusted by serious labs.

Prep the adapter *shape* now (`bayhack/zeon_bridge.py` is the stub). Wire it to their SDK on-site during build #1. If they don't expose an SDK, you still have the full pure-PLR loop as the guaranteed demo — the bridge is upside, not a dependency.

---

## 3. The demo (90 seconds, one tight slice)

Pick **one** visible, convergent instantiation and let the rest be depth. Recommended spine: **a fluorescence assay optimized by the world model, validated by Rhodamine, executed through MCP, with an arm uncap beat.**

**Script:**
- **0:00–0:12 — Pain.** "Zeon makes it easy to go from English to a moving robot. The hard part isn't motion — it's *trust*. Did it actually dispense what you asked? Most automation finds out after it's wasted the reagents."
- **0:12–0:28 — The idea.** "bay-hack closes the loop with a world model. Plain-English goal in; a GP world model proposes the next experiment; it runs on a real liquid handler through my PyLabRobot MCP server; and — this is the part nobody else has — a Rhodamine-B gate proves the volumes were real before we trust a single number."
- **0:28–0:58 — Live.** Type a goal → `sow` compiles it → world model proposes design → agent calls `plr_transfer`/`plr_read_plate` (chatterbox) → arm does a **vision-guided uncap** (`plr_lr`) → **fluorescence reads out**, Rhodamine gate goes green (R²≥0.995), CV checkpoint confirms the step executed → **conformal gate: accept** → next round, response climbs. Show the convergence curve: ~N runs vs thousands for brute force.
- **0:58–1:15 — The bridge.** "Everything you saw was simulation-first and validated. Now watch me swap the backend —" flip `SimulationArmBackend` → `ZeonArmBackend` — "and the exact same loop drives Zeon's arm. I just made Zeon speak PyLabRobot."
- **1:15–1:30 — Vision + ask.** "This is the trust layer for autonomous science: any protocol, any arm, physically verified. Repo's public. I'm Di — I build autonomous labs."

**Wow beats:** fluorescent plate + Rhodamine gate flipping green; the backend-swap-to-Zeon moment; the convergence curve. All read from the back of the room.

---

## 4. 6-day countdown (today = Sun Jul 19)

**Tonight / Mon (Jul 19–20) — wire the spine in sim.** Push bay-hack. Have Claude Code compose `sow` → `lab-world-model` → `plr-mcp` (chatterbox) → `rhodamine` gate into one `bayhack` loop that runs end-to-end simulated. Green `python -m bayhack.loop`.

**Tue (Jul 21) — add the physical-verification beats.** Wire `plr_lr` `Workcell` + `vision_guided_pick` + `DecapSkill` into the loop; add the CV checkpoint (`SimVision`). Confirm the Rhodamine gate + conformal gate both gate the loop.

**Wed (Jul 22) — the demo surface.** A clean dashboard/CLI narrative: goal ▸ world-model proposal ▸ MCP execution ▸ fluorescence + gates ▸ convergence curve. Record a **sim-only fallback video**.

**Thu (Jul 23) — the Zeon bridge shape + pitch.** Finalize `zeon_bridge.py` interface so on-site it's fill-in-the-SDK. Lock the 90-sec script; build the one slide (loop diagram + the 3 world-model words + repo QR). Rehearse 3×.

**Fri (Jul 24) — buffer + pack.** Freeze scope. Rehearse 5×. Pack: laptop, charger, USB-C/HDMI, phone tripod, and if you're bringing labware/dye for a physical flourish, a Rhodamine/food-dye kit + a plate. Register for final demos: https://luma.com/5m9yhtzj

**Sat/Sun (Jul 25–26) — on-site.** 11a team formation (recruit; see §5). Build #1: wire `HardwareBackend`/`ZeonArmBackend` to the provided arm + camera, and the reader if available. Keep the sim path warm as fallback. **Sun 3p submit, 4:30–5:30 demo.** A sim demo that *works* beats a hardware demo that crashes.

---

## 5. Team (form on arrival) — you're the magnet

You show up with a *running, validated* autonomous-lab loop. That recruits people. Keep it ≤4; you own the science + the loop.

**Recruit line:** "I've got a world-model DBTL loop already running in sim — English in, robot pipettes out, Rhodamine-validated, MCP-driven. I want someone on the provided arm/camera and someone on the demo UI, and we'll bridge it to Zeon's platform live. Come close the loop with me."

**Roles to fill:** (1) robotics/hardware for on-site arm + camera wiring; (2) a front-end/storyteller to build the dashboard and help deliver the 90 seconds. You cover science, PLR, and the world model.

---

## 6. Judge-rubric fit

| Criterion | Why you win it |
|---|---|
| Innovation | A GP **world model** driving a **physically-verified** DBTL loop — verification-before-trust is novel. |
| Technical execution | A real closed loop across planner + world model + MCP + arm + reader, sim-first with hardware swap. |
| Relevance / impact | Trust is the actual blocker for autonomous labs; you have Hamilton-validated cred. |
| Demo / wow | Rhodamine gate green + backend-swap-to-Zeon + convergence curve. |
| Platform/theme fit | *World Models* + *simulation-first* (Zeon's thesis) + *Physical MCP* (host's) + the Zeon bridge. |

---

## 7. Risks & fallbacks (pre-decided)

- **No Zeon SDK on-site** → demo the full pure-PLR loop; present the bridge as the roadmap. Still wins.
- **Provided hardware flakes** → chatterbox sim backend, identical loop. Keep it warm.
- **Reader unavailable** → your fluorescence read is simulated already; show the Rhodamine gate on canned paired data (`validation.cli evaluate --data run.json`).
- **Scope creep** → one convergent assay slice, done clean. Depth lives in Q&A, not the demo path.
- **Solo if team doesn't gel** → the loop runs end-to-end by itself. You always have a demo.

**Next:** open `KICKOFF_PROMPT.md` in Claude Code (inside `bay-hack/`) and let it compose your repos + push. `bayhack/loop.py` already runs the skeleton in sim so you feel the loop tonight.
