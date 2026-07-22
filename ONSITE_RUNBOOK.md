# Track A on-site runbook

## Win condition

Show this with at least one real measured artifact and one real robot action:

**produce TEM-1 -> confirm expression -> screen round 1 -> read kinetics ->
pass assay QC -> design round 2 from evidence -> confirm dose response -> act**

The best outcome is a real round 1 reader export that automatically changes the
round 2 robot plate.

## Before kickoff

```bash
git pull --ff-only
python -m bayhack.preflight --output run_artifacts/preflight.json
python -m bayhack.tem1_demo --receipt run_artifacts/tem1-trust.json
pytest -q
python -m bayhack.tem1_dashboard
```

Keep the dashboard loaded at `http://127.0.0.1:8010` as the guaranteed fallback.

## 10:00 to 11:00: capture facts, do not code guesses

Ask the track lead:

- Which Sepia Bio kit and exact TEM-1 construct are supplied?
- What is the official expression protocol and expected completion time?
- How should expression be confirmed, and what quantitative threshold passes?
- What substrate, wavelength or channel, read cadence, and kinetic window apply?
- What exactly are the activity, inhibition, and blank controls?
- Which compounds, solvents, source wells, stock concentrations, and metadata
  are supplied?
- What screen concentration and round 2 dose range are intended?
- Which plate, reader, tips, liquid handler, and labware definitions are ready?
- Which Zeon workflow or skill API performs an organizer-approved transfer?
- Can the exact workflow run in simulation before physical execution?
- Who owns the E-stop and the human motion confirmation?

Record answers in `run_artifacts/tem1/hardware-matrix.json` and the generated
`assay-spec.json`. Ask the lead to review the filled configuration before
setting `protocol_confirmed_by_organizer` to true.

## 11:00 team formation

Recruit for two missing seams only:

1. A Zeon or robotics integrator who owns simulation, the physical adapter, and
   E-stop coordination.
2. A reader or assay teammate who owns expression evidence, plate-reader export,
   controls, and the kinetic window.

Di owns the liquid-handling plan, PyLabRobot and MCP path, scientific model,
evidence gates, dashboard, and final pitch.

Recruit line:

> I have the complete TEM-1 Track A loop running now: expression gate, balanced
> compound plate, kinetic analysis, Z-prime QC, uncertainty-aware selection, and
> adaptive round 2 dose response. I need one teammate on Zeon's physical
> executor and one on the real reader export. Our goal is a measured round 1
> that automatically changes the next robot plate.

## 11:00 to 12:00: orient and assign ownership

1. Run the full green baseline.
2. Create the unconfirmed event packet:

   ```bash
   python -m bayhack.tem1_cli init --output-dir run_artifacts/tem1
   ```

3. Fill the compound map and assay configuration from organizer facts.
4. Verify source wells and all physical protocol fields.
5. Decide the smallest real hardware loop that can finish before dinner.
6. Assign one owner to each of: assay, robot, reader, evidence, demo.

## 12:00 to 3:00: first physical truth

Priority order:

1. Run or observe the cell-free expression step.
2. Capture replicated expression evidence and the no-template control.
3. Run `confirm-expression` before preparing the compound screen.
4. In Zeon simulation, execute one control transfer and one candidate transfer.
5. Confirm source, destination, tip policy, volume, deck pose, and waste behavior.
6. Run the same two transfers physically at safe speed with a human gate.
7. Export one reader kinetic trace and prove the parser accepts it.

Do not attempt the full plate until those two wells and one real export work.

## 3:00 to 6:00: round 1

1. Generate `round1-plan.json` from the real compound library.
2. Review the plate map with the assay and robot owners.
3. Verify every source well and control definition.
4. Run the plan in Zeon simulation.
5. Execute physically after the human motion gate.
6. Export `round1-reader.csv`.
7. Analyze immediately.
8. If Z-prime fails, stop and troubleshoot controls. Do not tune the code to
   bless a failed plate.
9. If QC passes, generate `round2-plan.json` from the saved analysis.
10. Photograph the plate and save the robot and reader traces.

## 7:00 to 10:00: round 2 and evidence freeze

1. Review the measured compounds selected for round 2.
2. Confirm the organizer-approved dose factors and source demand.
3. Run round 2 in Zeon simulation.
4. Execute and export the kinetic reader data.
5. Analyze the curves and inspect monotonicity.
6. Nominate only after QC and confirmation pass.
7. Save the final receipt, source-file digests, photos, and video.
8. Start the dashboard in safe receipt-replay mode.

By 10:00 PM, freeze the stage path. Any later change must be reversible and must
not alter the green simulator.

## Hard stop rules

- No expression confirmation means no compound screen.
- No organizer-confirmed protocol means no physical run.
- No clear deck and E-stop owner means no motion.
- No plan verification means no backend dispatch.
- No fresh-tip or approved wash policy means no liquid transfer.
- No passing controls means no model update.
- No round 1 QC means no round 2.
- No round 2 confirmation means no inhibitor nomination.
- No modeled value may be presented as measured.

## Fallback ladder

1. **Best:** real liquid handling, real kinetic reader, real adaptive round 2.
2. **Strong:** real round 1 liquid handling and reader, modeled round 2 replay.
3. **Good:** real expression or reader artifact plus Zeon simulation and the
   complete deterministic loop.
4. **Guaranteed:** deterministic two-round dashboard, refusal proof, sealed
   receipt, and generic liquid-handling fallback.

Never hide which level was achieved.

## Sunday schedule

- 8:00 AM: fresh-machine rehearsal and evidence audit
- 9:00 AM: fix only demo-blocking defects
- 10:30 AM: freeze code and final receipt
- 11:00 AM: update slide with the exact measured facts
- 12:00 PM: rehearse the 90-second pitch three times
- 1:00 PM: record final fallback and photograph the physical plate
- 2:00 PM: submit before the 2:30 PM deadline
- 3:30 PM: dashboard in receipt-replay mode, plate visible beside it
- 4:30 PM: pitch from the frozen path

## Final pre-demo check

```bash
python -m bayhack.preflight --output run_artifacts/final-preflight.json
pytest -q
python -m bayhack.tem1_dashboard --receipt run_artifacts/tem1-trust.json
```

Confirm the projected slide says only what the evidence supports.
