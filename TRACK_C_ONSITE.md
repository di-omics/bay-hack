# Track C on-site runbook

## The first 15 minutes

Ask the track lead these questions before writing venue-specific code:

1. Which arm is assigned to the team?
2. What is the smallest official Python example that moves it in simulation?
3. What gripper or end effector is installed, and what cap sizes can it hold?
4. Which screw-cap tubes or bottles are available in multiples?
5. Is the camera fixed, wrist-mounted, or both?
6. How do we fetch one frame and identify its calibration?
7. Can we print or clamp a tube fixture, and what is the printer queue?
8. What named Zeon objects or taught poses already exist for this cell?
9. Who owns the E-stop, and what speed is approved for first motion?
10. Is there a pipette or liquid handler available for the handoff beat?

Write the answers in a scratch note. Photograph the exact arm, gripper, tube,
fixture surface, and camera view. Do not commit credentials or private venue
configuration.

## Pick the physical target

Choose one container using this order:

1. Identical screw-cap tubes already demonstrated with the gripper
2. A bottle with a large ribbed cap and a stable base
3. A hinged container only if screw caps are unavailable

Prefer a cap with visible texture and a tube that contrasts with the bench.
Avoid transparent-on-white as the first target. Add removable colored tape or a
printed fiducial only with organizer approval.

## Integration order

### Gate 0: preserve the guaranteed demo

```bash
python3 -m bayhack.track_c_demo --fault partial_uncap
pytest -q
```

Keep this green at all times.

### Gate 1: arm simulation

- Run the organizer's official arm example unchanged.
- Map the five `TubeActuator` calls to the supported simulation API.
- Use named objects and taught poses.
- Record each command in the event trace.
- Do not unlock physical motion yet.

### Gate 2: fixture and tube geometry

- Measure tube outer diameter, cap outer diameter, exposed cap height, and tube
  height.
- Adjust `hardware/tube_nest.scad`.
- Print a fit coupon or clamp a temporary fixture first.
- Confirm the tube does not spin during manual cap torque.

### Gate 3: camera verification

- Capture capped, uncapped, partially uncapped, and recapped frames.
- Start with robust geometry and color cues before training anything.
- Return `ambiguous` when confidence is below the threshold.
- Save frame digests and camera metadata in the observation evidence.

### Gate 4: slow physical motion

- Clear the workspace.
- Name the E-stop owner.
- Use the organizer-approved speed.
- Test approach and retreat without contacting the tube.
- Test grasp and release.
- Test a partial turn.
- Test one full uncap with human confirmation.
- Only then enable controller-driven verification and recovery.

### Gate 5: liquid-handling handoff

The minimum winning handoff is a verified open tube presented at a known access
pose. If a pipette is available, add one approved dyed-water transfer only after
the mechanics are stable. The dexterity and verification proof comes first.

## Demo freeze deadline

Freeze the physical path at least two hours before submission. After freeze:

- no architecture changes
- no dependency upgrades
- no unreviewed geometry changes
- no new model training
- only fixes that restore the rehearsed sequence

Record one clean run and one fault-recovery run before freeze.

## Fallback ladder

1. Full physical uncap, camera gate, handoff, recap, camera gate
2. Physical uncap and verification, simulated liquid-handler handoff
3. Physical approach and grasp, simulated wrist rotation, measured camera gate
4. Full simulation with the partial-uncap recovery dashboard
5. Track A TEM-1 closed-loop dashboard

Always demo the highest rung that ran cleanly three times in a row.

## Ninety-second demo order

1. **Problem, 10 seconds:** liquid handlers stop at closed or ambiguous labware.
2. **Rule, 10 seconds:** no verified opening, no pipetting.
3. **Clean action, 20 seconds:** uncap and show the independent camera evidence.
4. **Fault, 25 seconds:** inject or create a partial uncap. Show recovery.
5. **Close, 15 seconds:** recap and independently verify closure.
6. **Receipt, 10 seconds:** show the sealed action and evidence trace.

## Final proof checklist

- [ ] exact arm and SDK named
- [ ] exact tube and fixture named
- [ ] simulation run recorded
- [ ] capped observation saved
- [ ] open observation saved
- [ ] partial-open observation saved
- [ ] closed observation saved
- [ ] no pipetting before open verification
- [ ] retry or safe stop demonstrated
- [ ] closure verification demonstrated
- [ ] receipt integrity passes
- [ ] dashboard labels modeled, simulated, and measured evidence correctly
- [ ] physical demo rehearsed three times
- [ ] fallback video and local simulation ready
