# Track A field guide: TEM-1 inhibitor search

## The announced challenge

Track A asks teams to close a physical scientific loop around a real
antibiotic-resistance target:

1. Produce TEM-1 beta-lactamase with the supplied protein synthesis kit.
2. Confirm that the enzyme was produced.
3. Choose candidate compounds and design a liquid-handling protocol.
4. Execute the screen on robots.
5. Read the plate and quantify inhibition.
6. Let round 1 evidence sharpen round 2.
7. Determine a dose response and nominate a confirmed condition.

The public guide confirms sfGFP expression, nitrocefin at A490, a 30-second
kinetic cadence, vehicle controls, no-enzyme controls, and a 95-compound DMSO
library. Organizer instructions at kickoff are the source of truth for the
remaining scaled protocol and hardware details. See
[OFFICIAL_TRACK_A_MATERIALS.md](OFFICIAL_TRACK_A_MATERIALS.md).

## The bay-hack answer

```text
cell-free TEM-1 synthesis
  -> replicated expression evidence vs no-template control
  -> expression gate
  -> feature-diverse round 1 compound plan
  -> verified robotic liquid handling
  -> kinetic reader slopes
  -> vehicle and no-enzyme control QC
  -> Z-prime gate
  -> inhibition plus replicate uncertainty
  -> conservative ranking
  -> four-factor round 2 confirmation
  -> monotonicity and 50 percent inhibition crossing
  -> nominate or refuse
```

This couples two complementary world models:

- Zeon's physical world model represents the bench, geometry, labware, robot
  state, and safe execution.
- bay-hack's scientific world model represents assay response, uncertainty,
  control quality, and the next experiment.

Round 2 is not hard-coded. It is built from round 1 observations. The selection
score is mean inhibition minus one standard error, then the chosen compounds
return across organizer-configured dose factors.

## What is implemented now

- An explicit, fail-closed `TEM1AssaySpec`
- An organizer compound-library CSV with optional `priority_score`,
  `priority_source`, and numeric `feature_*` columns
- Feature-diverse first-round selection
- Replicated candidate wells with spatial separation
- Vehicle and no-enzyme controls placed across plate edges
- A 95-row organizer packet that defaults to 45 compounds in duplicate, filling
  one 96-well plate with six controls
- An organizer-selectable breadth policy: set `candidate_replicates` to 1 to
  screen 90 unique compounds plus six controls in round 1, while round 2 remains
  replicated
- Kinetic reader CSV ingestion with source path and SHA-256 digest
- Per-well linear slope estimation
- Control normalization and Z-prime assay QC
- Replicate SD, standard error, conservative score, and hit gate
- Failed-control quarantine with no scientific-model update
- Adaptive round 2 planning from round 1 evidence
- Four-factor dose-response confirmation
- Uncertainty-aware monotonicity checking
- Relative factor estimate for the 50 percent inhibition crossing
- Final nomination only after round 2 QC and confirmation pass
- Tamper-evident closed-loop receipts
- A deliberate failed-expression path with zero compound wells, model updates,
  round 2 plans, or robot commands after the failure

## Published facts and remaining venue fields

The default configuration pre-fills these published values:

- expression confirmation method: sfGFP fluorescence
- expression guide wavelengths: Ex 485 nm and Em 528 nm
- substrate: nitrocefin
- activity read: A490
- kinetic cadence: every 30 seconds

Physical execution still refuses to start. Fill these only from the event
protocol and track-lead confirmation:

- expression pass threshold and actual instrument
- event-scaled CFPS volume, shaking speed, and duration
- total kinetic duration
- total reaction volume
- assay-mix, compound, and substrate volumes
- preincubation time
- exact vehicle and no-enzyme compositions
- source well for every compound
- confirmation that the organizer reviewed the configuration

The following defaults are scientific software policy, not wet-lab protocol
claims: two round 1 candidate replicates, two round 2 candidate replicates,
three replicates for each control type, Z-prime minimum 0.50, hit threshold
30 percent, and four relative round 2 dose factors. If the track lead approves a
breadth-first primary screen, `candidate_replicates: 1` fits 90 unique compounds
plus six controls on one plate. Round 2 still requires at least two replicates.

## Create the on-site packet

```bash
python -m bayhack.tem1_cli init --output-dir run_artifacts/tem1
```

This creates:

- `assay-spec.json`: unconfirmed fields remain null
- `compounds.csv`: placeholder identifiers that must be replaced
- `README.txt`: the on-site sequence

## Evidence schemas

### Expression evidence

```csv
role,replicate,value
tem1_expression,1,VALUE
tem1_expression,2,VALUE
no_template_control,1,VALUE
no_template_control,2,VALUE
```

The `value` is whatever quantitative output the organizer-approved expression
confirmation method produces. Do not mix units or methods in one file.

### Compound library

```csv
compound_id,name,source_well,screen_concentration,concentration_unit,priority_score,priority_source,feature_1,feature_2
C01,organizer name,A1,ORGANIZER_VALUE,ORGANIZER_UNIT,OPTIONAL_HIGHER_IS_BETTER,OPTIONAL_METHOD,OPTIONAL,OPTIONAL
```

Priority and feature columns are optional. A complete `priority_score` column
selects the highest organizer-approved or agent-generated scores and records
their source. Without complete priority scores, numeric feature columns drive
greedy farthest-point coverage. Without either, the planner uses deterministic
library coverage and makes no chemical-similarity or activity-prediction claim.

### Kinetic reader export

```csv
well,time_s,value
A1,0,VALUE
A1,30,VALUE
A1,60,VALUE
```

Each assigned well needs at least three unique time points. `absorbance` or
`signal` may replace the `value` column name.

## On-site command sequence

```bash
# 1. Confirm the published defaults, then fill only organizer-confirmed values.
python -m bayhack.tem1_cli init --output-dir run_artifacts/tem1

# 2. Prove enzyme production before any compound screen.
python -m bayhack.tem1_cli confirm-expression \
  --config run_artifacts/tem1/assay-spec.json \
  --evidence run_artifacts/tem1/expression.csv \
  --output run_artifacts/tem1/expression-confirmation.json

# 3. Build and inspect the balanced first plate.
python -m bayhack.tem1_cli round1-plan \
  --config run_artifacts/tem1/assay-spec.json \
  --compounds run_artifacts/tem1/compounds.csv \
  --output run_artifacts/tem1/round1-plan.json

# 4. Execute only after plan verification and the human motion gate.
#    Export the kinetic reader data, then analyze it.
python -m bayhack.tem1_cli analyze \
  --config run_artifacts/tem1/assay-spec.json \
  --compounds run_artifacts/tem1/compounds.csv \
  --plan run_artifacts/tem1/round1-plan.json \
  --reader run_artifacts/tem1/round1-reader.csv \
  --output run_artifacts/tem1/round1-analysis.json

# 5. Build round 2 from round 1 evidence.
python -m bayhack.tem1_cli round2-plan \
  --config run_artifacts/tem1/assay-spec.json \
  --compounds run_artifacts/tem1/compounds.csv \
  --analysis run_artifacts/tem1/round1-analysis.json \
  --output run_artifacts/tem1/round2-plan.json

# 6. Execute, export, and analyze round 2.
python -m bayhack.tem1_cli analyze \
  --config run_artifacts/tem1/assay-spec.json \
  --compounds run_artifacts/tem1/compounds.csv \
  --plan run_artifacts/tem1/round2-plan.json \
  --reader run_artifacts/tem1/round2-reader.csv \
  --output run_artifacts/tem1/round2-analysis.json
```

## Hard stops

- No confirmed TEM-1 expression means no compound screen.
- Missing organizer protocol fields mean no physical execution.
- A plan with missing source wells means no physical execution.
- Missing kinetic wells mean no analysis.
- Z-prime below the declared threshold means no model update and no round 2.
- Failed round 2 QC means no dose-response claim.
- A nonmonotonic or non-hit confirmation means no final nomination.
- Modeled values must never be described as measured.
- Receipt replay must issue zero hardware commands.

## Questions to settle during kickoff

1. Confirm the OpenCFPS Z0001 event lot and the event-scaled reaction recipe,
   volume, plate geometry, shaking speed, orbit, and incubation duration.
2. Which instrument measures sfGFP, and what quantitative threshold passes?
3. Confirm nitrocefin at A490 every 30 seconds and state the total kinetic
   window.
4. What exact DMSO percentage and composition define the vehicle controls?
5. What exact composition defines the no-enzyme controls?
6. Is a known TEM-1 inhibitor supplied as an optional reference control?
7. Which compounds, source wells, stock concentrations, solvents, and metadata
   are supplied?
8. What dose range and dilution pattern should round 2 use?
9. Which liquid handler, plate reader, plate, tips, and labware definitions are
   calibrated?
10. What Zeon skill or workflow executes an organizer-approved transfer?
11. What units do the electronic pipette volume and speed parameters use?
12. Who owns the E-stop and confirms every transition from simulation to motion?

## Scientific references

- The Z-prime assay-quality statistic comes from Zhang, Chung, and Oldenburg,
  *A Simple Statistical Parameter for Use in Evaluation and Validation of High
  Throughput Screening Assays*.
- The repository uses kinetic slopes, controls, and replicated uncertainty
  because endpoint intensity alone can confuse assay drift with inhibition.
- The dashboard calls all built-in TEM-1 values modeled. Only organizer data
  loaded through the evidence adapters can be labeled measured.
