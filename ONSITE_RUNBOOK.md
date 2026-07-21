# On-site runbook

## The win condition

Show two coupled world models:

1. Zeon's physical world model tracks the bench, labware, robot, and state.
2. bay-hack's scientific world model predicts assay response and chooses the
   next liquid-handling experiment.

The complete Track A loop is visible and literal:

**plan -> pipette -> measure -> verify -> learn -> follow up**

## 10:00 to 10:20: answer these before coding

- What arm and pipetting end effector are available?
- Is there a liquid handler, or is the robot arm operating a pipette?
- What Python skill, workflow, or executor API does Zeon expose?
- Can we run the same workflow in Zeon's simulator before physical execution?
- How are meshes, labware identities, coordinate frames, and state updates exposed?
- Which plate reader or camera is available?
- Which plate and tip definitions are already calibrated?
- Are food dye and water allowed? Is Rhodamine B allowed?
- Where are the E-stop, safe speed limit, waste, and human confirmation gate?

Write every answer into an issue or `run_artifacts/hardware_matrix.json`. Do not
code against a guessed API.

## 10:20: choose the hardware lane

| Available setup | Build lane |
|---|---|
| Liquid handler plus reader | Real pipetting and real quantitative readout |
| Liquid handler plus camera | Real pipetting and camera colorimetry |
| Robot arm plus pipette | Zeon physical world model plus bay-hack assay model |
| Robot arm only | Real plate movement and follow-up, manual rescue pipetting |
| Hardware unstable | Full simulator plus prerecorded physical fallback |

## 11:00 team formation

Recruit only the missing capabilities:

- One Zeon or robotics integrator who owns the physical adapter and E-stop
- One camera or reader integrator who owns measurement calibration
- Optional storyteller who protects the 90-second demo and records every run

Di owns the assay, PyLabRobot path, scientific world model, and final pitch.

Recruit line:

> I have a verified liquid-handling loop running now. A scientific world model
> chooses each well, Physical MCP executes it, Rhodamine or camera data verifies
> it, and the accepted result moves downstream. I need one person on Zeon's
> physical world model and one on measurement. We will couple both models live.

## Build order

1. Run `python -m bayhack.preflight` and keep the JSON report.
2. Run `pytest -q` and `python -m bayhack.demo` unchanged.
3. Run the dashboard and keep it open as the guaranteed demo.
4. Calibrate one plate pose and one safe transfer, not an entire workcell.
5. Select a shipped adapter from `MEASUREMENT_ADAPTERS.md` and connect one real
   measurement to the ledger.
6. Qualify the dispense method with `CsvVolumeGate` and one real visual
   checkpoint with `JsonCvCheckpoint`. Follow `VERIFICATION_ADAPTERS.md`.
7. Execute one full round with plan verification and a human confirmation gate.
8. Repeat until the scientific model selects an accepted well.
9. Execute the 20 uL follow-up transfer to H12.
10. Record the successful physical run immediately.
11. Restart the dashboard with `--receipt run_artifacts/trust.json` for a safe
   stage replay that never moves hardware.
12. Only then add the Zeon backend flourish, arm motion, or extra UI.

## Two-minute safety rehearsal

```bash
python -m bayhack.preflight --output run_artifacts/preflight.json
python -m bayhack.safety --output run_artifacts/refusal.json
python -m bayhack.dashboard
```

On the dashboard, click **Prove refusal** first. Say: "The invalid tip assignment
never reached the robot, never became a measurement, and never trained the
scientific model." Then click **Run the loop** to show recovery and follow-up.

## Hard stop rules

- Never execute a plan that failed volume, capacity, tip, or destination checks.
- Never let a modeled value appear as measured in the dashboard or ledger.
- Never reuse a wet tip. The current MCP simulator returns tips to rack positions;
  use unique positions and wire a real waste drop before physical execution.
- Never home or move real hardware until the deck is clear and the E-stop owner
  explicitly confirms readiness.
- Never let the Zeon integration become a dependency of the guaranteed demo.

## Saturday evening freeze

By dinner, require one complete recorded run. By 10:00 PM, freeze the demo path.
After that, changes must be reversible and cannot alter the green simulator path.
Robots stop at midnight, so do not postpone physical recording.

## Sunday

- 9:00 AM: run the full demo from a fresh terminal
- 11:00 AM: freeze code and generate the final trust receipt
- 12:00 PM: rehearse the 90-second pitch three times
- 1:00 PM: record final fallback video and take plate photos
- 2:00 PM: submit early
- 3:30 PM: walk-around mode, dashboard open, physical plate visible
- 4:30 PM: live demo with the simulator already loaded behind it

## 90-second spine

1. **Problem:** motion is not the same as trustworthy science.
2. **Scientific model:** it chooses the next formulation under uncertainty.
3. **Physical model:** Zeon keeps the robot and bench state aligned with reality.
4. **Live run:** show concrete wells, volumes, measurement, and shrinking search.
5. **Proof:** show the Rhodamine or colorimetric gate and the trust receipt.
6. **Follow-up:** move 20 uL from the accepted well to H12.
7. **Close:** two world models, one physically verified scientific loop.
