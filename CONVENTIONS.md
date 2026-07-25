# Repository build rules

Read `HOUSE_RULES.md` before editing.

## Current target

Track C is TubeProof, a verified tube-access capability for liquid handling:

`observe capped -> localize -> grasp -> uncap -> verify open -> present -> recap -> verify closed`

Track A TEM-1 and the generic liquid-handling loop remain green fallbacks. Do
not delete them or make them the primary public story.

## Architecture

- `TubeActuator` owns motion commands.
- `CapVerifier` owns independent physical observations.
- `VerifiedTubeAccessController` owns gates, retry limits, and safe stops.
- The receipt owns provenance, event history, decisions, and integrity.
- Venue hardware stays behind an adapter and uses official SDK calls only.

## Golden rules

1. No verified opening, no pipetting.
2. No verified closure, no completed run.
3. A successful motion command is not proof that the physical state changed.
4. Return `ambiguous` when a camera cue is unresolved.
5. Preserve every attempt, observation, recovery, and stop in the receipt.
6. Stop after the configured retry budget.
7. Run the venue arm in simulation before physical motion.
8. Use named Zeon objects or taught poses, not copied coordinates.
9. Require a clear workspace, named E-stop owner, and approved speed before the
   first physical command.
10. Never guess arm APIs, gripper limits, tube dimensions, camera calibration,
    or venue credentials.
11. Preserve `python3 -m bayhack.track_c_demo` as the dependency-free primary
    fallback.
12. Preserve `python3 -m bayhack.tem1_demo` and `python3 -m bayhack.demo` as
    fallbacks.
13. Keep modeled, simulated, measured, and hardware-validated claims distinct.
14. Preserve receipt integrity checks and zero-motion replay.
15. Keep venue hardware behind lazy adapters.
16. Push only green commits authored and committed by `di-omics`.
17. Do not commit secrets or private venue configuration.
18. Never add assistant attribution or co-author trailers.
19. Never use em dashes in repository text.
20. Preserve the GitHub profile and avatar.

## Track C modules

- `bayhack/track_c.py`: state machine, verification, recovery, evidence adapter
- `bayhack/track_c_demo.py`: narrated deterministic fallback
- `bayhack/track_c_dashboard.py`: stage UI and safe receipt replay
- `hardware/tube_nest.scad`: parametric split-collar fixture
- `bayhack/seams.py::tube_access_checkpoint`: real `plr-lab-robot` skill seam
- `TRACK_C.md`: system and evidence contract
- `TRACK_C_ONSITE.md`: integration ladder and demo freeze
- `TRACK_C_HARDWARE.md`: labware, measurements, and packing list
- `STRATEGY.md`: scoring strategy and pitch
- `KICKOFF_PROMPT.md`: venue coding-agent handoff

## Supporting seams

- Dexterity: `plr_lr.manipulation.DecapSkill` and `RecapSkill`
- Liquid handling: `plr_mcp.lab.Lab`
- Protocol compilation and volume qualification: `plr-epigenome`
- Scientific optimization: `ml-bio-eval/lab-world-model`
- Physical world: organizer-supplied Zeon workflow or skill executor

Supported paths are derived from the current repository root:

- `../plr-mcp`
- `../plr-epigenome`
- `../plr-lab-robot`
- `../ml-bio-eval/lab-world-model`
- `../../lab-automation/plr-mcp`
- `../../lab-automation/plr-epigenome`
- `../../lab-automation/plr-lab-robot`
- `../../research-and-ml/ml-bio-eval/lab-world-model`

Discover the root with `git rev-parse --show-toplevel`. Verify a checkout before
importing it. Never hard-code an absolute home path.

## Event evidence directory

All run-specific data belongs under ignored `run_artifacts/track-c/`:

- capped, open, partial, and closed camera frames
- camera observation JSON and frame digests
- arm simulation and physical traces
- tube and cap measurements
- fixture revision and print settings
- clean, recovery, and safe-stop receipts
- photos, video, and human confirmation notes

Track A evidence continues under `run_artifacts/tem1/`.

## Before every commit

```bash
python3 -m bayhack.track_c_demo --fault partial_uncap
python3 -m bayhack.track_c_demo --fault persistent_open_ambiguity
python3 -m bayhack.preflight
python3 -m bayhack.tem1_demo
python3 -m bayhack.demo
python3 -m bayhack.safety
python3 -m bayhack.benchmark
python3 scripts/validate_tem1_structures.py
.venv/bin/python -m bayhack_adk.smoke
.venv/bin/pytest -q
python3 -m compileall -q bayhack bayhack_adk tests
git diff --check
```

Confirm the staged diff has no secrets, no em dashes, no assistant attribution,
and no evidence claim stronger than the recorded provenance.
