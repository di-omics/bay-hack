# Repository build rules

Read `HOUSE_RULES.md` before editing.

## Current target

Track A is a two-round TEM-1 beta-lactamase inhibitor search:

`synthesize -> confirm expression -> round 1 -> kinetic read -> QC -> adaptive round 2 -> dose response -> nominate or refuse`

The generic two-component formulation loop remains a fallback. Do not make it
the primary public story.

## Architecture

- Zeon's physical world model represents geometry, labware, robot state, and
  safe execution.
- bay-hack's scientific world model represents expression evidence, assay
  response, uncertainty, dose response, and the next experiment.

The physical model controls how an approved action happens. The scientific
model controls which action should happen next and whether evidence is trusted.

## Golden rules

1. Preserve `python -m bayhack.tem1_demo` as a dependency-free fallback.
2. Preserve `python -m bayhack.demo` as the generic fallback.
3. Treat `OFFICIAL_TRACK_A_MATERIALS.md` as the confirmed baseline. Do not
   guess the remaining venue protocol values, object names, or skill
   parameters.
4. Keep physical execution locked until `TEM1AssaySpec.physical_ready` is true.
5. Confirm TEM-1 expression before compound screening.
6. Verify every plate plan before backend dispatch.
7. Require vehicle and no-enzyme controls in every assay round. Add a known
   inhibitor reference only if the organizers supply one.
8. Quarantine failed Z-prime data. Never train or plan round 2 from it.
9. Generate round 2 from saved round 1 observations.
10. Preserve replicate uncertainty and source-specific provenance.
11. Require round 2 QC and dose-response confirmation before nomination.
12. Never describe the relative 50 percent crossing as a definitive IC50 unless
    the data and organizer protocol support that claim.
13. Preserve receipt integrity checks and zero-motion replay.
14. Keep venue hardware behind lazy adapters.
15. Push only green commits authored and committed by `di-omics`.
16. Build physical execution inside the organizer's native Zeon project, not
    through invented generic SDK calls.
17. Guard every electronic-pipette and operator-message call with
    `is_sim_mode()` on simulation-capable Zeon skills.
18. Use Zeon's native liquid-transfer resume ledger and record a transfer only
    after a successful dispense.

## Track A modules

- `bayhack/tem1.py`: assay specification, compound library, plate design,
  kinetics, QC, adaptive selection, dose response, and sealed receipt
- `bayhack/tem1_cli.py`: on-site file workflow
- `bayhack/tem1_demo.py`: narrated deterministic fallback
- `bayhack/tem1_dashboard.py`: stage and walk-around UI
- `TEM1_TRACK_A.md`: exact schemas and field guide
- `OFFICIAL_TRACK_A_MATERIALS.md`: source-grounded event facts and open fields
- `ZEON_NATIVE_INTEGRATION.md`: exact Zeon skill and workflow handoff

## Supporting seams

- Execute: `plr_mcp.lab.Lab` and the `plr-mcp` server
- Plan and volume qualification: `plr-epigenome`
- Move: `plr_lr.Workcell`
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

Discover the repository root with `git rev-parse --show-toplevel`. Verify a
checkout exists before importing it. Never hard-code an absolute home path.

## Event evidence directory

All run-specific data belongs under ignored `run_artifacts/tem1/`:

- `assay-spec.json`
- `compounds.csv`
- `expression.csv` and `expression-confirmation.json`
- `round1-plan.json`, `round1-reader.csv`, `round1-analysis.json`
- `round2-plan.json`, `round2-reader.csv`, `round2-analysis.json`
- Zeon simulation and physical traces
- photos, confirmation notes, and final receipt

## Before every commit

```bash
python -m bayhack.preflight
python -m bayhack.tem1_demo
python -m bayhack.demo
python -m bayhack.safety
python -m bayhack.benchmark
pytest -q
python -m compileall -q bayhack tests
git diff --check
```

Confirm the staged diff has no secrets, no em dashes, no assistant attribution,
and no evidence claim stronger than the recorded provenance.
