# Track C build guide: TubeProof

## One-sentence project

TubeProof gives a lab robot one trustworthy physical skill: open a screw-cap
tube, prove it is open before liquid handling, then close it and prove closure.

## Why this capability matters

Liquid handlers are excellent once a consumable is accessible. Real workflows
still stall at caps, lids, foil, misaligned tubes, and ambiguous physical state.
Uncapping alone is not autonomy. A useful system must know whether uncapping
worked and decide what to do when it did not.

## State machine

| State | Action or evidence | Pass condition | Failure behavior |
|---|---|---|---|
| observe capped | cap-state observation | capped at confidence threshold | stop before motion |
| localize | tube and cap pose | pose inside fixture tolerance | re-localize, then stop |
| grasp cap | gripper action and force cue | stable cap grasp | open, re-localize, retry |
| unscrew | rotate and lift by thread geometry | command completes | move to verification |
| verify open | independent cap observation | uncapped at confidence threshold | regrasp and retry, then stop |
| present | move tube opening to access pose | pose reached after open gate | stop, no pipetting |
| recap | replace and tighten cap | command completes | retry closure |
| verify closed | independent cap observation | capped at confidence threshold | re-seat and retry, then stop |

The physical observation is deliberately separate from the action result. A
successful motion command is not proof that the world changed.

## Demo scenarios

### Recovery scenario

`partial_uncap` completes the commanded wrist motion but leaves the visual cap
state ambiguous. The controller refuses to unlock pipetting, re-localizes,
regrips, retries the unscrew, verifies the open tube, exposes it to the liquid
handler, recaps, and verifies closure.

### Refusal scenario

`persistent_open_ambiguity` keeps the cap contour occluded. The controller uses
its retry budget, never presents the tube for pipetting, and seals a
`STOPPED_SAFE` receipt.

### Other planted faults

- `cap_slip`
- `rotated_tube`
- `ambiguous_close`

Each fault is visible in the event trace. No retry is hidden.

## Camera evidence contract

The live camera process can write ordered observations to JSON:

```json
{
  "observations": [
    {
      "checkpoint": "initial",
      "state": "capped",
      "confidence": 0.98,
      "provenance": "measured:camera",
      "evidence": {
        "image_sha256": "sha256 of source frame",
        "camera_id": "venue camera name",
        "detector_version": "git hash or model version"
      }
    },
    {
      "checkpoint": "open",
      "state": "uncapped",
      "confidence": 0.96,
      "provenance": "measured:camera",
      "evidence": {
        "tube_mouth_visible": true,
        "cap_in_parking_nest": true
      }
    },
    {
      "checkpoint": "closed",
      "state": "capped",
      "confidence": 0.95,
      "provenance": "measured:camera",
      "evidence": {
        "continuous_seating_line": true
      }
    }
  ]
}
```

Use two visual cues for cap-off when possible:

1. The tube mouth is visible.
2. The removed cap is visible in its parking pocket.

If either cue is unresolved, return `ambiguous`. Do not force a binary label.

## Arm adapter contract

Keep the venue SDK behind five operations:

```text
localize
grasp_cap
uncap
present_for_pipetting
recap
```

Use named Zeon objects or taught poses, not copied coordinates. Start at the
organizer's safe speed. Confirm an E-stop owner before physical motion. The
current `plr-lab-robot` choreography supplies the motion shape for a threaded
cap: approach, grip, counter-clockwise rotation with pitch lift, park, retrieve,
clockwise rotation with controlled descent.

## Fixture contract

The fixture should:

- constrain tube translation and rotation
- expose the cap to the gripper
- keep the tube mouth visible to the camera
- expose a cap parking region to the camera
- mount repeatably to the bench or deck
- release the tube without damage

The OpenSCAD source is parametric because tube dimensions are not yet known.

## Acceptance gates

A hardware demo is accepted only when all are true:

- the actual tube and cap are measured and configured
- the arm runs the exact sequence in simulation first
- camera observations carry measured provenance and source evidence
- the opening gate passes before the liquid-handler handoff
- a planted partial-uncap or cap-slip fault is detected
- recovery succeeds or the system stops safely
- closure is independently verified
- the final receipt passes SHA-256 integrity verification

## Claims that are safe on stage

- "The motion is simulated" when using the built-in backend.
- "This observation is modeled" when using the built-in cap sensor.
- "This frame was measured" only when loaded from the venue camera.
- "This skill ran on hardware" only after a physical run clears all gates.

Never call an internal world-state flag independent physical verification.
