# On-site physical verification adapters

The assay measurement answers, "How well did this formulation perform?"
Physical verification answers two different questions:

1. Did the liquid handler dispense accurately and repeatably?
2. Does the observed plate state match the expected physical state?

`bayhack.verification` answers both from venue-neutral files. The loop earns the
`hardware-validated` label automatically only when both measured gates pass.
A string set by the caller cannot bypass these gates.

## Gate 1: real volume CSV

Prepare an independent standard curve and replicated robot dispenses. Use the
second validation plate for this qualification. The A1 to A5 positions below
refer to that plate, not the assay plate. Export:

```csv
kind,well,target_ul,rfu
standard,A1,2,140
standard,A2,5,200
standard,A3,10,300
standard,A4,20,500
standard,A5,50,1100
test,B1,10,296
test,C1,10,300
test,D1,10,304
test,B2,20,492
test,C2,20,500
test,D2,20,508
```

`standard` rows must be independently prepared references, not the robot
dispenses being tested. `test` rows are replicated robot dispenses. The default
gate requires:

- At least three distinct standard volumes
- Standard-curve R2 of at least 0.995
- At least three test replicates per target volume
- Mean inferred-volume error of at most 10 percent
- Replicate CV of at most 10 percent

Run it:

```bash
python -m bayhack.verification volume-csv run_artifacts/volume-gate.csv
```

The output includes the fit, every target-volume group, pass/fail reasons,
source path, SHA-256 digest, and `measured:volume-csv` provenance. Save the file as the
run-level qualification evidence for the exact liquid handler, tips, liquid,
plate, and method used in the demo.

## Gate 2: real visual checkpoint

Store one checkpoint per formulation. A camera or CV tool can write it directly.
An operator may also write it after reviewing the named image, but must identify
the inspector honestly.

```json
{
  "checkpoint": "plate-present-no-spill",
  "passed": true,
  "note": "plate seated, destination well filled, no visible spill",
  "inspector": "lab-cv",
  "confidence": 0.97,
  "image": "plate_B1_after.jpg",
  "trace_id": "zeon-frame-0042"
}
```

Use an image path relative to the JSON file or a trace ID from the venue system.
If an image is named, it must exist. Confidence is optional, but when supplied
it must be at least 0.80 by default.

Run one checkpoint:

```bash
python -m bayhack.verification cv-json run_artifacts/cv_B1_1.json
```

## Wire both gates into the loop

```python
from bayhack.loop import DBTLLoop
from bayhack.measurements import CsvWellMeasurement, LinearSignalCalibration
from bayhack.seams import PlrMcpBench
from bayhack.verification import CsvVolumeGate, JsonCvCheckpoint

measurement = CsvWellMeasurement(
    "run_artifacts/reader.csv",
    calibration=LinearSignalCalibration(raw_low=100, raw_high=1100),
)
bench = PlrMcpBench(
    backend="VENUE_BACKEND",
    measurement_fn=measurement,
)
loop = DBTLLoop(
    bench,
    rhodamine_fn=CsvVolumeGate("run_artifacts/volume-gate.csv"),
    cv_fn=JsonCvCheckpoint("run_artifacts/cv_{well}_{run_id}.json"),
    target_signal=0.85,
)
loop.run()
loop.ledger.save("run_artifacts/trust.json")
```

The loop passes the verified plan into both adapters. `{well}` and `{run_id}`
therefore resolve to `B1`, `1`, and so on. All seed and optimization rounds use
the same evidence policy.

## Evidence promotion rules

| Volume gate | CV gate | Ledger physical-verification label |
|---|---|---|
| measured and pass | measured and pass | `hardware-validated` |
| measured | fixture or missing | `measured:partial-physical-gates` |
| both measured, either fails | both measured | `measured:failed-physical-gates` |
| fixtures only | fixtures only | `modeled` or `synthetic_fixture` |

A failed physical gate never trains the world model. It remains visible in the
trust receipt with its reasons, source evidence, and source-file digests.

## One-command zero-motion audit

Before connecting the venue backend:

```bash
python -m bayhack.preflight \
  --reader-csv run_artifacts/reader.csv \
  --reader-well B1 --reader-raw-low 100 --reader-raw-high 1100 \
  --volume-csv run_artifacts/volume-gate.csv \
  --cv-json run_artifacts/cv_B1_1.json \
  --receipt run_artifacts/trust.json \
  --output run_artifacts/preflight.json
```

The audit runs the simulator, benchmark, and refusal proof. It validates every
supplied evidence file and safe receipt replay. It issues zero hardware commands
and always reports `ready_for_motion: false`. Deck clearance, E-stop ownership,
safe speed, and explicit human confirmation still happen at the bench.
