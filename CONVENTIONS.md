# Repository build rules

Read `HOUSE_RULES.md` before editing.

## Architecture

bay-hack couples two world models:

- Zeon's physical world model handles geometry, labware, state, and execution.
- bay-hack's scientific world model predicts assay response and selects the next
  liquid-handling experiment.

Pipeline:

`goal -> verified plate plan -> execute -> measure -> physical gates -> learn -> follow-up`

## Golden rules

1. Compose the existing `di-omics` repos. Do not rebuild their primitives here.
2. Keep `python -m bayhack.demo` dependency-free and green.
3. Gate seed runs exactly like optimization runs.
4. Verify every physical plan before execution.
5. Train only on physically trustworthy measurements.
6. Label measurement provenance honestly.
7. Keep venue hardware behind lazy adapters.
8. Treat the Zeon integration as upside, not a fallback dependency.
9. Use the shipped CSV or camera measurement adapter before writing a new one.
10. ACCEPT requires both the assay objective and uncertainty clearance.
11. Preserve `python -m bayhack.safety` as a zero-command refusal proof.
12. Use `CsvVolumeGate` and `JsonCvCheckpoint`. Never promote physical evidence
    by setting a label manually.

## Supporting seams

- Design: `ml-bio-eval/lab-world-model`
- Execute: `plr_mcp.lab.Lab` and the `plr-mcp` server
- Move: `plr_lr.Workcell`
- Volume gate: `tipseq_plr.validation`
- Vision gate: `tipseq_plr.steps.vision` and `lab-cv`
- Learn: `labworld.ConformalQCGate`
- Plan: `tipseq_plr.sow`
- Physical world: Zeon's Python workflow or skill executor

When the repositories are sibling checkouts, their expected paths are:

- `../plr-mcp`
- `../plr-epigenome`
- `../plr-lab-robot`
- `../ml-bio-eval/lab-world-model`

Do not hard-code an absolute home-directory path. Discover the current repo root
with `git rev-parse --show-toplevel` and verify each sibling before using it.

On-site evidence belongs under ignored `run_artifacts/`:

- `reader.csv` or `plate_{well}.jpg`
- `camera-calibration.json`
- `volume-gate.csv`
- `cv_{well}_{run_id}.json`
- `trust.json`, `refusal.json`, and `preflight.json`

## Before every commit

```bash
python -m bayhack.preflight
python -m bayhack.demo
python -m bayhack.safety
python -m bayhack.benchmark
pytest -q
```

Confirm the author is `di-omics`, the working tree contains no secrets, and the
commit subject describes only the product change.
