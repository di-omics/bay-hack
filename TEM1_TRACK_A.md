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

The event page is the source of truth for the challenge. Organizer instructions
at kickoff are the source of truth for all reagent names, concentrations,
volumes, timings, wavelengths, control definitions, and hardware calls.

## The bay-hack answer

```text
cell-free TEM-1 synthesis
  -> replicated expression evidence vs no-template control
  -> expression gate
  -> feature-diverse round 1 compound plan
  -> verified robotic liquid handling
  -> kinetic reader slopes
  -> activity, inhibition, and blank control QC
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
- An organizer compound-library CSV with optional numeric `feature_*` columns
- Feature-diverse first-round selection
- Replicated candidate wells with spatial separation
- Activity, inhibition, and blank controls placed across plate edges
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

## Do not guess the venue protocol

The default configuration intentionally refuses physical execution. Fill these
fields only from the organizer's protocol:

- expression confirmation method and pass threshold
- substrate identity
- reader wavelength or measurement channel
- total reaction volume
- assay-mix, compound, and substrate volumes
- preincubation time
- source well for every compound
- confirmation that the organizer reviewed the configuration

The following defaults are scientific software policy, not wet-lab protocol
claims: two candidate replicates, three replicates for each control type,
Z-prime minimum 0.50, hit threshold 30 percent, and four relative round 2 dose
factors. Change them if the official protocol says otherwise.

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
compound_id,name,source_well,screen_concentration,concentration_unit,feature_1,feature_2
C01,organizer name,A1,ORGANIZER_VALUE,ORGANIZER_UNIT,OPTIONAL,OPTIONAL
```

Feature columns are optional. When supplied, round 1 maximizes coverage in that
feature space. Without them, the planner uses deterministic library coverage
and makes no chemical-similarity claim.

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
# 1. Fill only organizer-confirmed protocol values and compound metadata.
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

1. What exact Sepia Bio kit and expression protocol are supplied?
2. How is successful TEM-1 production confirmed, and what threshold passes?
3. What substrate, read mode, wavelength, cadence, and kinetic window are used?
4. What defines the activity, inhibition, and blank controls?
5. Is a known TEM-1 inhibitor supplied for the inhibition control?
6. Which compounds, source wells, stock concentrations, solvents, and metadata
   are supplied?
7. What dose range and dilution pattern should round 2 use?
8. Which liquid handler, plate reader, plate, tips, and labware definitions are
   calibrated?
9. What Zeon skill or workflow call executes an organizer-approved transfer?
10. Who owns the E-stop and confirms every transition from simulation to motion?

## Scientific references

- The Z-prime assay-quality statistic comes from Zhang, Chung, and Oldenburg,
  *A Simple Statistical Parameter for Use in Evaluation and Validation of High
  Throughput Screening Assays*.
- The repository uses kinetic slopes, controls, and replicated uncertainty
  because endpoint intensity alone can confuse assay drift with inhibition.
- The dashboard calls all built-in TEM-1 values modeled. Only organizer data
  loaded through the evidence adapters can be labeled measured.
