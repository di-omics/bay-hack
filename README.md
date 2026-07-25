# 🧪🤖 bay-hack

[![ci](https://github.com/di-omics/bay-hack/actions/workflows/ci.yml/badge.svg)](https://github.com/di-omics/bay-hack/actions/workflows/ci.yml)

## TubeProof: verified tube access for liquid handling

**Track C entry for the 24hr AI for Science World Models Hack at Zeon
Systems.** A robot uncaps a tube, independently verifies that the cap is off,
presents the opening for liquid handling, then recaps and verifies closure.
Ambiguity triggers recovery or a safe stop.

**[Live site](https://di-omics.github.io/bay-hack/)** ·
**[Pitch slide](docs/slide.html)** ·
**[Track C build guide](TRACK_C.md)** ·
**[On-site runbook](TRACK_C_ONSITE.md)** ·
**[Hardware and labware](TRACK_C_HARDWARE.md)** ·
**[Coding-agent handoff](KICKOFF_PROMPT.md)**

```text
observe capped
  -> localize tube and cap
  -> grasp and unscrew
  -> independently verify cap off
  -> unlock liquid-handler access
  -> recap
  -> independently verify closure
  -> complete, retry, or stop safely
```

The hard rule is simple:

> No verified opening, no pipetting. No verified closure, no completed run.

## Run the winning demo

The core uses only the Python standard library. The default scenario injects a
partial uncap so the robot must detect ambiguity, recover, and finish safely.

```bash
python3 -m bayhack.track_c_demo \
  --fault partial_uncap \
  --receipt run_artifacts/track-c.json

python3 -m bayhack.track_c_dashboard
# open http://127.0.0.1:8000
```

The dashboard has three stage-safe buttons:

- **Run clean loop:** verifies a nominal open, handoff, and closure.
- **Inject partial uncap:** catches an uncertain cap state, re-localizes,
  regrips, retries, and completes with a sealed receipt.
- **Prove safe stop:** keeps the pipetting handoff locked when camera evidence
  stays ambiguous after the retry budget.

Every value is labeled. The built-in motion is simulated execution. The
built-in camera observation is modeled. Receipt replay always issues zero
hardware commands.

## Why this maps directly to Track C

| Track C direction | TubeProof evidence |
|---|---|
| Open and close containers | threaded tube decap and recap choreography |
| Physical verification | separate cap-state observations gate each transition |
| Recover from failures | cap slip, tube rotation, partial uncap, and ambiguous closure |
| Build useful lab capability | tube opening is presented to a liquid handler |
| Self-aligning fixtures | configurable split-collar nest with cap parking pocket |
| Transparent or reflective objects | confidence threshold and explicit ambiguity state |

The demo is deliberately narrow. It proves one lab capability end to end
instead of showing many unverified motions.

## Physical state is evidence, not an internal flag

Motion and observation use separate interfaces:

```python
class TubeActuator:
    def localize(self): ...
    def grasp_cap(self): ...
    def uncap(self): ...
    def present_for_pipetting(self): ...
    def recap(self): ...

class CapVerifier:
    def observe(self, checkpoint): ...
```

The controller accepts `capped`, `uncapped`, or `ambiguous`, plus confidence,
provenance, and evidence. `EvidenceFileCapVerifier` consumes the same contract
from a camera process without importing a vision stack into the safety core.

Example camera evidence:

```json
{
  "observations": [
    {
      "checkpoint": "open",
      "state": "uncapped",
      "confidence": 0.96,
      "provenance": "measured:camera",
      "evidence": {"image_sha256": "..."}
    }
  ]
}
```

## Compose the shipped di-omics arm stack

`plr-lab-robot` already contains real simulation-first `DecapSkill` and
`RecapSkill` choreography. bay-hack adds the independent physical-verification
and recovery layer around those skills.

```bash
pip install -e ../plr-lab-robot
python3 - <<'PY'
from bayhack.seams import tube_access_checkpoint
print(tube_access_checkpoint())
PY
```

The adapter runs cap rotation and thread-pitch lift through the real
`plr-lab-robot` simulation backend. At the venue, use the organizer's supported
arm SDK or Zeon project. Do not invent an arm API. Keep the swap behind the
`TubeActuator` boundary and prove it in simulation before unlocking motion.

## Print the fixture after measuring the venue tube

[`hardware/tube_nest.scad`](hardware/tube_nest.scad) is a configurable
split-collar nest. It has a funnel entry, an anti-rotation split, mounting holes,
and a visible cap parking pocket. Measure the exact tube outer diameter first.
Print a short fit coupon before committing printer time to the full fixture.

## Zero-motion readiness audit

```bash
python3 -m bayhack.preflight --output run_artifacts/preflight.json
pytest -q
```

Preflight proves both Track C outcomes:

1. A partial uncap is detected, recovered, and reclosed.
2. Persistent visual ambiguity blocks the liquid-handling handoff.

It also exercises the original generic liquid-handling loop and the complete
Track A TEM-1 build as fallbacks. It never initializes venue hardware.

## Track A remains available as a fallback

The TEM-1 closed-loop inhibitor campaign is preserved. Nothing was deleted.

```bash
python3 -m bayhack.tem1_demo --receipt run_artifacts/tem1.json
python3 -m bayhack.tem1_dashboard
```

See [TEM1_TRACK_A.md](TEM1_TRACK_A.md),
[OFFICIAL_TRACK_A_MATERIALS.md](OFFICIAL_TRACK_A_MATERIALS.md), and
[ADK_PREP.md](ADK_PREP.md). Track A remains useful if the assigned hardware or
team makes the biological screen more practical than dexterity.

## Evidence vocabulary

- **modeled:** generated by a deterministic scientific or sensor model
- **simulated execution:** action code exercised against a simulator
- **measured:** loaded from a physical camera, sensor, or reader
- **hardware-validated:** measured evidence that clears the physical gates

No modeled value may be described as measured. No simulated motion may be
described as physical execution.

## Public project map

- [`bayhack/track_c.py`](bayhack/track_c.py): state machine, gates, recovery, receipts
- [`bayhack/track_c_demo.py`](bayhack/track_c_demo.py): narrated CLI demo
- [`bayhack/track_c_dashboard.py`](bayhack/track_c_dashboard.py): local stage UI
- [`hardware/tube_nest.scad`](hardware/tube_nest.scad): configurable fixture
- [`bayhack/seams.py`](bayhack/seams.py): `plr-lab-robot` and other di-omics seams
- [`TRACK_C.md`](TRACK_C.md): architecture and camera contract
- [`TRACK_C_ONSITE.md`](TRACK_C_ONSITE.md): venue integration and demo freeze
- [`TRACK_C_HARDWARE.md`](TRACK_C_HARDWARE.md): what to bring and measure
- [`STRATEGY.md`](STRATEGY.md): scoring strategy and pitch
- [`HOUSE_RULES.md`](HOUSE_RULES.md): authorship, evidence, and Git rules

## Reference

- [Official Track C challenge](https://app.notion.com/p/Track-C-Open-Build-for-Dexterity-and-Physical-Verification-3a5ee7a4c457805a8e19f18a2669f670?pvs=25)

Authored as `di-omics`. MIT licensed.
