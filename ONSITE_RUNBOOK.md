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
zeon auth status
```

Keep the dashboard loaded at `http://127.0.0.1:8010` as the guaranteed fallback.
The organizers provide and pre-validate the Track A reagents, plates, seals, and
equipment. Do not bring or substitute personal assay materials.

## 10:00 to 11:00: capture facts, do not code guesses

The public guide already confirms OpenCFPS, TEM-1-sfGFP, nitrocefin, A490 reads
every 30 seconds, vehicle controls, no-enzyme controls, a 95-compound DMSO
library, the BioTek ELx808 reader, the Axygen PlateMax, and the Benchmark
Incu-Mixer MP. Ask only for the missing operational facts:

- What event-scaled CFPS reaction volume, plate geometry, speed, orbit, and
  incubation duration should we use?
- Which instrument reads sfGFP, and what quantitative threshold passes the
  expression gate?
- What are the final assay volume, buffer, enzyme, compound, and nitrocefin
  volumes?
- What pre-incubation duration and total A490 kinetic window apply?
- What DMSO percentage and exact compositions define the vehicle and no-enzyme
  controls?
- Is a known TEM-1 inhibitor supplied as an optional reference control?
- Where is the 95-compound source map, with stock concentrations, units,
  solvents, and any permitted feature metadata?
- What round 1 screen concentration and round 2 dose range are intended?
- Should round 1 favor 45 compounds in duplicate or 90 unique compounds in
  singlicate, given the available plates and time?
- Which Zeon project, workflow, world, objects, and skills are approved?
- Do the source and destination plates expose well anchors, and what are their
  object names?
- What units and safe speeds do the electronic-pipette parameters use?
- What tip policy and liquid-transfer resume behavior are approved?
- How does the ELx808 export wells, timestamps, and A490 values?
- Who owns the physical E-stop and the human motion confirmation?

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
5. Clone or sync the organizer's Zeon project and inspect its supplied skill
   signatures, workflow, world, objects, and well anchors.
6. Decide the smallest real hardware loop that can finish before dinner.
7. Assign one owner to each of: assay, robot, reader, evidence, demo.

## 12:00 to 3:00: first physical truth

Priority order:

1. Start the organizer-approved cell-free expression plate immediately. The
   attached quick-start guide gives a 6-to-12-hour incubation range, although
   sfGFP can become visible earlier. Use the track lead's event timing.
2. While expression runs, map one vehicle transfer and one candidate transfer
   into the organizer's native Zeon workflow.
3. Guard every electronic-pipette and operator-message call with
   `is_sim_mode()` on any simulation-capable skill.
4. In Zeon simulation, execute the exact two-transfer workflow and confirm that
   no physical pipette call was attempted.
5. Confirm source, destination, well anchors, tip policy, volume unit, deck
   pose, resume ledger, and waste behavior.
6. Run the same two transfers physically at safe speed with a human gate and
   the physical E-stop owner present.
7. Export one ELx808 kinetic trace and prove the parser accepts it.
8. Capture replicated sfGFP evidence and the no-template control when the
   organizer-approved expression window completes.
9. Run `confirm-expression`. Do not begin the compound screen if it fails.

Do not attempt the full plate until those two wells and one real export work.

## 3:00 to 6:00: round 1

1. Generate `round1-plan.json` from the real compound library.
2. Review the plate map with the assay and robot owners.
3. Verify every source well and control definition.
4. Run the plan in Zeon simulation.
5. Confirm Zeon's native liquid-transfer ledger is clear for this run.
6. Execute physically after the human motion gate.
7. Export `round1-reader.csv`.
8. Analyze immediately.
9. If Z-prime fails, stop and troubleshoot controls. Do not tune the code to
   bless a failed plate.
10. If QC passes, generate `round2-plan.json` from the saved analysis.
11. Photograph the plate and save the robot and reader traces.

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
- No confirmed pipette units means no electronic-pipette call.
- No round 1 QC means no round 2.
- No round 2 confirmation means no inhibitor nomination.
- No modeled value may be presented as measured.
- Pause and Stop are software controls, not the physical E-stop.
- A successful simulation does not prove a physical move is safe.

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
