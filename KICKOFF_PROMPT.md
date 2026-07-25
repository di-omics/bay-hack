# Paste this into the coding agent at the venue

Read `README.md`, `TRACK_C.md`, `TRACK_C_ONSITE.md`, `STRATEGY.md`,
`HOUSE_RULES.md`, and `CONVENTIONS.md`. Track C is the primary entry. The project is
TubeProof: verified tube uncapping and recapping for liquid handling. Preserve
the complete Track A code as a fallback.

Before editing:

1. Run `python3 -m bayhack.track_c_demo --fault partial_uncap`.
2. Run `python3 -m bayhack.track_c_demo --fault persistent_open_ambiguity`.
3. Run `python3 -m bayhack.preflight`.
4. Run `pytest -q`.
5. Restate the core rule: no verified opening, no pipetting; no verified
   closure, no completed run.

Then ask me for only these venue facts:

- assigned arm and official SDK example
- gripper model and approved first-motion speed
- exact tube or container and cap geometry
- camera type, mount, and one-frame API
- named Zeon objects or taught poses
- E-stop owner
- whether a pipette or liquid handler is available

Do not guess missing hardware APIs, coordinates, dimensions, credentials, or
safety settings. Keep the simulator working while venue integration proceeds.

## Build order

### Step 0: freeze the guaranteed path

Keep the Track C demo, preflight, and tests green before every commit. Never
break `python3 -m bayhack.demo` or the preserved Track A demo.

### Step 1: official arm simulation

Run the organizer's smallest supported simulation example unchanged. Add a
narrow `TubeActuator` adapter for `localize`, `grasp_cap`, `uncap`,
`present_for_pipetting`, and `recap`. Use named objects or taught poses. Record
commands in the existing event trace. No physical motion yet.

### Step 2: physical geometry

Measure the actual tube and cap. Fit the existing thread-pitch choreography or
the organizer's provided skill. Adapt `hardware/tube_nest.scad` only after
measurement. Prefer an existing rack or approved temporary fixture if it is
faster and more repeatable.

### Step 3: independent camera evidence

Capture capped, open, partial, and reclosed frames. Produce the existing JSON
observation contract with state, confidence, provenance, and evidence. Return
`ambiguous` below threshold. Store frame SHA-256 and detector version. Do not use
the actuator's internal world-state flag as physical verification.

### Step 4: slow hardware ladder

With a clear workspace and named E-stop owner: approach and retreat, grasp and
release, partial turn, full uncap, cap park, recap. Start at the approved slow
speed. Require human approval before the first motion-producing command.

### Step 5: recovery proof

Plant one safe failure such as a deliberately short rotation or cap slip. The
camera must detect the unresolved state. The controller must retry within its
budget or stop with pipetting locked. Rehearse both recovery and safe-stop paths.

### Step 6: liquid-handling handoff

Unlock the presentation pose only after cap-off verification. Add an approved
dyed-water transfer only if the mechanics are already stable. Do not let wet
work endanger the dexterity proof.

### Step 7: demo freeze

Update the dashboard with measured evidence labels and the real arm name. Save
one clean receipt, one recovery receipt, and one safe-stop receipt. Record a
fallback video. Freeze at least two hours before submission.

## Git workflow

- Author and committer: `di-omics <di.autonomouslab@gmail.com>`.
- Use factual Conventional Commit subjects.
- Never add assistant attribution, generated-by notes, or co-author trailers.
- Never use em dashes in repository text.
- Never change the GitHub avatar or profile.
- Do not commit secrets or private venue configuration.
- Push only after the Track C demo, preflight, generic demo, and tests pass.
- Keep `main` green. Do not rewrite public history.

After every green step report: what changed, evidence status, test status,
commit hash, and the exact remaining physical unknown.
