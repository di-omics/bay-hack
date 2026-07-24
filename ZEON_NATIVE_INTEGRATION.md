# Zeon native integration plan

This is the venue bridge for Track A. It replaces the earlier assumption that
Zeon would expose a generic robot SDK client.

## What Zeon actually expects

A Zeon project contains:

- `skills/<skill_id>/robotic_code.py`
- `skills/<skill_id>/metadata.yaml`
- `workflows/<workflow_id>.json`
- `worlds/<world_id>/`
- `objects/<object_id>/`
- optional `canvas/<canvas_id>.tsx`

Skills are Python. Workflows chain them into protocols. Worlds and object anchors
provide runtime geometry. A plate should expose well anchors named `A1` through
`H12`.

## Before the event

The published CLI version is 1.2.2 and requires Python 3.9 or newer.

```bash
python3 -m pip install --upgrade zeon
zeon --help
zeon auth login --global
zeon auth status
```

Do not commit `ZEON_API_TOKEN` or any `.env` file.

## First hour on-site

1. Get the organizer's project name and access.
2. Clone or sync it:

   ```bash
   zeon clone ORGANIZER_PROJECT
   cd ORGANIZER_PROJECT
   zeon sync
   ```

3. Inspect the supplied skills, workflow, world, and object names.
4. Find the exact skills for:
   - picking and returning the electronic pipette
   - picking and ejecting a tip
   - moving to a source well
   - moving to a destination well
   - aspirating and dispensing
   - opening and closing the plate shaker
   - sealing a plate
   - loading and unloading the reader
5. Confirm the destination plate exposes `A1` through `H12` anchors.
6. Confirm the source plate object type and source-well anchors.
7. Run one organizer example in cloud simulation before editing it.

## The narrow contract

bay-hack should remain the scientific planner. Zeon should remain the physical
executor.

The handoff is one verified plan:

```json
{
  "round_id": 1,
  "plan_sha256": "DIGEST",
  "assignments": [
    {
      "destination_well": "B1",
      "role": "candidate",
      "compound_id": "ORGANIZER_ID",
      "source_well": "A1",
      "volume_ul": "ORGANIZER_VALUE",
      "replicate": 1
    }
  ]
}
```

Do not let an LLM improvise coordinates or volumes. The adapter may translate a
verified well assignment into the organizer's existing skill parameters. It may
not change the scientific plan.

## Preferred workflow shape

```text
start
  -> zero-motion plan validation
  -> operator motion confirmation
  -> pick electronic pipette
  -> execute verified transfer list
  -> return electronic pipette
  -> write run artifact and completion log
  -> end
```

Use `on_success` between every skill node after Start. Do not use unconditional
edges between motion steps.

## Native calls to use

Import the supported runtime API inside a Zeon skill:

```python
from execution.execution_functions import *
```

Relevant functions:

- `load_object_anchor(object_name, anchor_name)`
- `anchor_preapproach(anchor, default_standoff=...)`
- `move_arm(arm, position, orientation, speed=...)`
- `init_epipette(name, ble_device_name=...)`
- `epipette_aspirate(name, volume=..., speed=...)`
- `epipette_dispense(name, volume=..., speed=...)`
- `epipette_tip_eject(name)`
- `is_sim_mode()`
- `is_transfer_done(rxn_well, "step", index)`
- `record_transfer(rxn_well, "step", index=index, part=..., vol=...)`
- `execution_dir(create=True)`
- `print_log(..., runlog=True)`
- `ask_user_slack(...)`

Prefer the organizer's supplied motion skills over direct `move_arm` calls.
Those skills should already account for pipette tool geometry and venue
calibration.

## Required simulation guard

Zeon's electronic pipette calls have no simulation branch. They attempt to reach
physical hardware even during a cloud simulation.

```python
if is_sim_mode():
    print_log(
        "SIM: would aspirate and dispense verified transfer",
        runlog=True,
        runlog_type="transfer",
    )
else:
    result = epipette_aspirate(
        EPIPETTE_GREY,
        volume=confirmed_volume,
        speed=confirmed_speed,
    )
    if not result.get("success"):
        raise RuntimeError(result.get("error", "aspirate failed"))
```

Guard every `epipette_*`, `send_slack`, and `ask_user_slack` call used by a
simulation-capable skill.

## Native resume ledger

Use Zeon's ledger so the built-in Resume run flow can skip transfers that
already completed.

```python
for index, transfer in enumerate(verified_transfers):
    destination = transfer["destination_well"]
    if is_transfer_done(destination, "step", index):
        print_log(
            "Skipping completed transfer",
            destination,
            runlog=True,
        )
        continue

    # Call the organizer-supplied transfer skill here.
    # It must return or raise before this line on failure.

    record_transfer(
        destination,
        "step",
        index=index,
        part=transfer["compound_id"],
        vol=transfer["volume_ul"],
    )
```

Never record before the dispense succeeds.

## Human motion gate

On real hardware, require an explicit confirmation with a fail-safe default:

```python
if not is_sim_mode():
    answer = ask_user_slack(
        "Deck clear, correct world loaded, and physical E-stop owner ready?",
        {
            "Confirmed, continue": "confirmed",
            "Abort": "abort",
        },
        timeout_s=120,
        default="abort",
    )
    if answer != "confirmed":
        raise RuntimeError("operator did not confirm the motion gate")
```

The in-app prompt is not an emergency stop. A person must remain at the physical
E-stop.

## Simulation-to-real sequence

1. Run the exact workflow in cloud Simulation mode.
2. Confirm every graph node completed and the log names the expected wells.
3. Confirm pipette calls were skipped in simulation instead of attempting BLE.
4. On the lab machine, compare the real bench to the loaded Zeon world.
5. Confirm the arm endpoint, wrist cameras, pipette, plate, tips, and source map.
6. Run one vehicle well and one candidate well physically at the venue-approved
   speed.
7. Inspect the resulting liquid placement before running the complete plate.
8. Only then run the full verified plan.

## Important platform behavior

- Cloud runs cannot access real hardware.
- Real hardware runs use the local app at `http://localhost:3000`.
- A green hardware indicator is a boot snapshot, not a live safety signal.
- Real Run preflight checks fresh wrist-camera frames and homes the pipette.
- Pause and Stop are network software commands, not the physical E-stop.
- Arms do not automatically home after pause, stop, failure, or completion.
- `zeon verify` is not implemented. The required gates are bay-hack plan
  verification, an exact successful simulation, a bench comparison, and human
  approval.

## Do not do this

- Do not replace `bayhack.zeon_bridge` methods with invented `self.sdk` calls.
- Do not hard-code world-frame well coordinates.
- Do not pass unconfirmed volumes into `epipette_*`.
- Do not assume the pipette API volume unit from its parameter name.
- Do not create a second physical resume ledger when Zeon's native ledger is
  available.
- Do not let an agent write directly to hardware without the deterministic plan
  verifier and operator gate.
