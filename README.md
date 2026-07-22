# 🧪🤖 bay-hack

[![ci](https://github.com/di-omics/bay-hack/actions/workflows/ci.yml/badge.svg)](https://github.com/di-omics/bay-hack/actions/workflows/ci.yml)

**Two world models hunt a TEM-1 beta-lactamase inhibitor.** Track A entry for
the 24hr AI for Science World Models Hack at Zeon Systems, July 25 to 26 in San
Francisco.

**[Live site](https://di-omics.github.io/bay-hack/)** ·
**[Pitch slide](docs/slide.html)** ·
**[Track A field guide](TEM1_TRACK_A.md)** ·
**[On-site runbook](ONSITE_RUNBOOK.md)** ·
**[Acceptance gates](ACCEPTANCE.md)** ·
**[Bring kit](HARDWARE_KIT.md)**

## The challenge-specific loop

```text
produce TEM-1
  -> prove expression against a no-template control
  -> choose a diverse first compound set
  -> verify and execute a replicated robotic plate plan
  -> read kinetic slopes
  -> require control quality and Z-prime
  -> rank inhibition with uncertainty
  -> build round 2 from round 1 evidence
  -> confirm four-point dose response
  -> nominate or refuse
```

This is liquid-handling first. Every candidate maps to a source well,
destination well, concentration factor, and replicate. Controls are distributed
across the plate. A failed biological or assay-quality gate stops the loop
before weak evidence can train the model or trigger the next robot action.

bay-hack couples two complementary world models:

1. **Zeon's physical world model** represents the bench, geometry, labware,
   robot state, and safe physical execution.
2. **bay-hack's scientific world model** represents assay response, replicate
   uncertainty, control quality, dose response, and the next experiment.

The physical model answers, "Can this action execute safely in the current
world?" The scientific model answers, "What should we run next, and is the
evidence trustworthy enough to act on?"

## Run the Track A demo now

The guaranteed path uses only the Python standard library. Every synthetic
value is explicitly labeled modeled.

```bash
python -m bayhack.tem1_demo --receipt run_artifacts/tem1-trust.json
python -m bayhack.tem1_dashboard
# open http://127.0.0.1:8010
```

The dashboard presents two stage-safe paths:

- **Prove expression refusal:** modeled TEM-1 signal fails against the
  no-template control. The result is zero compound wells, zero model updates,
  zero round 2 plans, and zero robot commands after failure.
- **Run two-round screen:** modeled expression passes, round 1 clears its
  control gate, the highest conservative scores advance, and round 2 estimates
  dose response before nominating a condition.

The deterministic fallback currently reports a modeled expression gate,
modeled Z-prime above the configured 0.50 threshold in both rounds, replicated
uncertainty, a monotonic confirmation curve, a relative 50 percent inhibition
crossing, and a SHA-256 sealed receipt. These are simulation results, not wet-lab
claims.

## Build the real event packet

```bash
python -m bayhack.tem1_cli init --output-dir run_artifacts/tem1
```

The generated assay configuration is intentionally incomplete. Physical
execution remains locked until the official track protocol supplies the
expression method, reagent and readout settings, component volumes, timing,
compound source wells, and organizer confirmation.

Then use the file workflow:

```bash
python -m bayhack.tem1_cli confirm-expression --help
python -m bayhack.tem1_cli round1-plan --help
python -m bayhack.tem1_cli analyze --help
python -m bayhack.tem1_cli round2-plan --help
```

See [TEM1_TRACK_A.md](TEM1_TRACK_A.md) for exact schemas and commands.

## Why round 1 genuinely sharpens round 2

- Round 1 uses organizer-supplied numeric features for greedy farthest-point
  diversity when they exist. It falls back to deterministic library coverage
  when they do not.
- Kinetic slopes are normalized to activity and blank controls.
- Activity and inhibition control separation must clear the configured Z-prime
  threshold before the scientific model updates.
- Candidate ranking uses mean inhibition minus one standard error.
- The top observed candidates return across four organizer-configured dose
  factors.
- Final nomination requires round 2 QC, a passing condition, and an
  uncertainty-tolerant monotonic curve.

The built-in 50 percent crossing is a relative dose-factor estimate. It is not
a definitive IC50 until real concentrations and sufficient fitted data support
that claim.

This is adaptive experimental design with a physical consequence, not an LLM
choosing labels in a dashboard.

## Fail closed, visibly

| Gate | Failure consequence |
|---|---|
| TEM-1 expression vs no-template control | compound screen blocked |
| Organizer protocol incomplete | physical execution blocked |
| Compound source well missing | physical execution blocked |
| Plan invalid | zero backend dispatch |
| Reader export incomplete | analysis blocked |
| Control quality or Z-prime fails | data quarantined, no model update |
| Round 1 QC fails | round 2 planning blocked |
| Round 2 QC fails | dose-response claim blocked |
| Confirmation fails | final nomination blocked |
| Receipt digest fails | stage replay blocked |

## What counts as evidence

- **modeled:** generated by the deterministic TEM-1 or generic assay simulator
- **simulated execution:** orchestration code exercised against a simulator
- **measured:** loaded from a physical reader, camera, or approved evidence file
- **hardware-validated:** measured evidence that also clears the physical gates

No modeled value may be described as measured. Source CSV files are tied to
analysis records by SHA-256 digest. The complete Track A receipt is sealed too,
and safe replay issues zero hardware commands.

## Zero-motion readiness audit

```bash
python -m bayhack.preflight --output run_artifacts/preflight.json
pytest -q
```

Preflight checks the new TEM-1 path, the generic liquid-handling fallback,
unsafe-plan refusal, benchmark claims, optional repository seams, evidence
files, and safe replay without initializing venue hardware.

## The generic liquid-handling fallback

The original two-component formulation loop remains intact as a backup:

```bash
python -m bayhack.demo --ledger run_artifacts/trust.json
python -m bayhack.dashboard
python -m bayhack.safety --output run_artifacts/refusal.json
python -m bayhack.benchmark
```

That simulator runs six visible 40 uL formulations, compared with a declared
26-point grid baseline. The modeled benchmark averages about six runs and saves
about 800 uL and 40 tips in the search phase. Its accepted well moves to H12 as
a verified follow-up. It is a demo fallback, not the announced biological
challenge.

## The di-omics composition

The standard-library path always works. Lazy adapters can swap in the existing
di-omics stack when sibling repositories are present:

| Stage | Repository or adapter |
|---|---|
| Scientific design | `ml-bio-eval/lab-world-model` |
| Liquid handling and reader | `plr-mcp` |
| Protocol compiler | `plr-epigenome` |
| Volume qualification | `plr-epigenome` |
| Dexterity and labware motion | `plr-lab-robot` |
| Zeon physical world | `bayhack/zeon_bridge.py` |
| Track A assay model | `bayhack/tem1.py` |

Expected sibling paths are relative to this repository, never hard-coded to a
home directory:

```text
../plr-mcp
../plr-epigenome
../plr-lab-robot
../ml-bio-eval/lab-world-model
```

The adapter discovers and verifies each path before use. Missing optional
repositories do not break the Track A simulator.

## Zeon bridge

`bayhack/zeon_bridge.py::ZeonArmBackend` defines the narrow on-site seam. Map its
enumerated operations to the organizer-supplied Zeon skill, workflow, or
executor API. Do not guess API names before kickoff. The same plan must run in
simulation before a human unlocks physical motion.

Zeon's public stack describes a live digital twin that represents geometry,
physical state, and scientific state for workflow execution. bay-hack adds a
challenge-specific scientific decision layer that turns trusted assay evidence
into the next plate.

## Supporting documents

- [TEM1_TRACK_A.md](TEM1_TRACK_A.md): exact challenge workflow and CSV schemas
- [STRATEGY.md](STRATEGY.md): win condition, pitch, and priority order
- [ONSITE_RUNBOOK.md](ONSITE_RUNBOOK.md): hour-by-hour build and demo freeze
- [ACCEPTANCE.md](ACCEPTANCE.md): evidence and refusal contract
- [HARDWARE_KIT.md](HARDWARE_KIT.md): what to bring and what not to bring
- [MEASUREMENT_ADAPTERS.md](MEASUREMENT_ADAPTERS.md): generic reader and camera adapters
- [VERIFICATION_ADAPTERS.md](VERIFICATION_ADAPTERS.md): physical volume and vision gates
- [KICKOFF_PROMPT.md](KICKOFF_PROMPT.md): precise coding-agent handoff
- [HOUSE_RULES.md](HOUSE_RULES.md): authorship, writing, evidence, and Git rules

## References

- [Official Track A challenge](https://luma.com/avi3l01q)
- [Inside the Zeon stack](https://www.zeonsystems.ai/blog/inside-the-zeon-stack)
- [Original Z-prime assay-quality paper](https://pubmed.ncbi.nlm.nih.gov/10838414/)
- [Cell-free synthesis and characterization of TEM-1 beta-lactamase](https://www.sciencedirect.com/science/article/pii/S0168165622000025)

Authorship and evidence rules are locked in [HOUSE_RULES.md](HOUSE_RULES.md).
MIT licensed.
