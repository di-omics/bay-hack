# Official Track A materials

Reviewed on 2026-07-23 from the organizer email, the public Track A guide, the
attached Sepia Bio protocol, and the complete Zeon documentation set.

## Primary sources

- [Track hub](https://app.notion.com/p/Track-Info-389ee7a4c45780a590b8c5945a6d5477)
- [Track A: Close the Loop](https://app.notion.com/p/Track-A-Close-the-Loop-3a5ee7a4c457800eb2f2e8bc115e5663)
- [Zeon Systems documentation](https://readme.zeonsystems.app/docs/what-is-zeon-systems)
- [Zeon documentation index for coding agents](https://readme.zeonsystems.app/llms.txt)
- [Sepia Bio OpenCFPS](https://sepiabio.com/products/opencfps-core-ecoli-z0001)
- [Google Agent Development Kit](https://adk.dev/)

The organizer and track lead remain the source of truth if any venue instruction
differs from these public materials.

## The actual win condition

Track A asks for two connected systems:

1. Robotic workflows that make TEM-1, confirm expression, and screen compounds.
2. An agent that designs each plate, consumes reader evidence, and decides the
   next plate.

The guide explicitly prioritizes a visible round 1 to round 2 change. The
strongest demonstration is:

```text
round 1 measured data
  -> quality gate
  -> ranked candidates with uncertainty
  -> a visibly different round 2 plate
  -> better or confirmed result
```

The goal is to inhibit TEM-1 as much as possible and show the loop closing over
two rounds. An isolated robot move, a generic chat agent, or a simulated chart
without a physical evidence handoff is not the core Track A result.

## Confirmed scientific design

### Workflow 1: make the enzyme

- Use the supplied Sepia Bio cell-free protein synthesis kit.
- Add the supplied TEM-1 template, expressed as an sfGFP fusion.
- Include a known-good positive template control.
- Include a no-template negative control.
- Seal with a gas-permeable seal, incubate with shaking, then cool.

### Workflow 2: confirm expression

- Read sfGFP fluorescence before spending an inhibitor assay on the product.
- The Sepia quick-start guide specifies Ex 485 nm and Em 528 nm, or equivalent.
- A quantitative pass threshold is not published. The track lead must define it.

### Workflow 3: screen inhibition

- Fill wells with assay buffer.
- Add enzyme except to no-enzyme control wells.
- Add one compound per candidate well.
- Pre-incubate at room temperature.
- Add nitrocefin to all wells while tracking timing.
- Read A490 every 30 seconds for several minutes.
- Use the initial A490 versus time slope as enzyme velocity.

Nitrocefin is yellow before cleavage and red after TEM-1 cleavage. Lower slope
means lower enzyme activity.

### Controls on every assay plate

- Vehicle control: maximum velocity, no inhibitor.
- No-enzyme control: minimum velocity and background.

The official guide says results are scored relative to these two control
classes. A known inhibitor control is useful only if the organizers supply one.
It must not be assumed.

## Confirmed supplied materials and equipment

The organizers say these are provided and pre-validated. Track A participants
do not need to source them.

### Reagents

- Sepia Bio cell-free expression kit
- TEM-1 template expressed as an sfGFP fusion
- Nitrocefin
- Assay buffer
- A 95-compound library in DMSO, supplied in source plates

### Labware

- 96-well flat-bottom assay plates
- Gas-permeable seals
- Standard microcentrifuge tubes

### Equipment

- Axygen PlateMax plate sealer
- Benchmark Incu-Mixer MP incubator and shaker
- BioTek ELx808 plate reader
- Zeon robotic system with organizer-provided skills

The guide names example skills such as `plateshaker_open`,
`epipette_aspirate`, and `platesealer_run`. Use the skill names in the actual
event project rather than guessing the rest in advance.

## Sepia OpenCFPS quick-start facts

The attached protocol is for OpenCFPS E. coli Core Kit Z0001.

- Thaw on ice and mix by flicking, inversion, or light vortexing.
- Use a master mix to reduce well-to-well variation.
- The base 10 uL recipe is 3 uL extract, 4 uL buffer, and DNA plus water.
- Positive control: 0.2 uL of 200 nM control DNA in the 10 uL base recipe.
- Negative control: no DNA.
- Sample target: 4 nM plasmid DNA or 8 nM linear DNA in the base recipe.
- Oxygen matters.
- For shaking, use a gas-permeable seal and hydrate above the seal.
- Remove bubbles with a quick low-speed spin.
- Incubate at 29 C for 6 to 12 hours, then cool to 4 C.
- sfGFP can become visible in about 30 minutes.
- The guide lists 30 to 100 uL and 1200 rpm for a shaking 96-well plate on a
  3 mm orbit instrument.

The 10 uL mixing table and the 30 to 100 uL shaking guidance are different
formats. Do not silently choose one. Ask for the event-specific scaled reaction
volume, plate geometry, orbit, speed, and incubation duration.

## Zeon facts that change the integration plan

### Project model

- A Zeon project contains skills, workflows, worlds, objects, and optional
  canvases.
- Skills are Python under `skills/<skill_id>/`.
- The Python function signature is the source of truth for skill parameters.
- Workflows are graphs that normally use `on_success` edges between skill nodes.
- World-object anchors provide geometry at runtime. Plate well anchors are named
  `A1` through `H12`.

### Simulation and hardware

- Cloud runs are simulation only.
- Physical runs use the local Zeon app at `http://localhost:3000`.
- The same workflow can run in simulation and then in Real Hardware mode.
- A successful simulation sets workflow validation metadata, but it does not
  prove a physical move is safe.
- The `zeon verify` CLI command is registered but not implemented. Do not use it
  as a safety or correctness claim.

### Pipetting

- The electronic pipette API uses `init_epipette`,
  `epipette_aspirate`, `epipette_dispense`, `epipette_tip_eject`,
  `epipette_home`, and `epipette_blow_out`.
- Pipette calls have no simulation branch. Even a cloud simulation attempts to
  reach real pipette hardware unless calls are guarded with `is_sim_mode()`.
- Zeon documentation does not state the pipette volume unit. Confirm the event
  convention before passing any value.
- Zeon has a native liquid-transfer resume ledger:
  `is_transfer_done`, `record_transfer`, `load_liquid_state`, and
  `liquid_state_path`.
- Record a transfer only after a successful dispense.

### Physical preflight and stop behavior

- A real run checks both wrist cameras and homes the pipette before execution.
- The header hardware indicator is a boot snapshot, not a live proof that a
  device is healthy.
- Pause and Stop are software commands, not an emergency stop.
- Arms are never automatically homed after pause, stop, failure, or completion.
- Resume can continue an incomplete liquid-handling run using the native ledger.
- A human must own the physical emergency stop and confirm the deck is clear.

## What bay-hack now covers

| Official requirement | bay-hack |
|---|---|
| Confirm TEM-1 expression | Replicated sfGFP versus no-template gate |
| Plan from a 95-compound library | 95-row packet, a 45-compound duplicate default, and an organizer-selectable 90-compound singlicate primary screen |
| Vehicle and no-enzyme controls | Three spatially distributed replicates of each |
| Kinetic A490 analysis | Per-well linear slopes from timestamped CSV |
| Assay quality | Z-prime on vehicle versus no-enzyme control separation |
| Round 1 changes round 2 | Conservative rank drives four-factor confirmation |
| Honest evidence | Source path, SHA-256 digest, and modeled versus measured provenance |
| Failure behavior | Failed expression or control QC blocks all downstream learning |
| Stage-safe demo | Sealed receipt replay issues zero hardware commands |

## Facts still needed at kickoff

1. Exact event-scaled CFPS reaction volume, plate, speed, orbit, and duration.
2. Instrument and threshold used for sfGFP expression confirmation.
3. Final assay volume and the assay-mix, compound, and nitrocefin volumes.
4. DMSO percentage and exact vehicle-control composition.
5. Exact no-enzyme-control composition.
6. Pre-incubation duration and the total A490 kinetic window.
7. Whether a known inhibitor control is supplied.
8. Compound CSV, source plate type, source wells, stock concentrations, and
   permitted chemical metadata.
9. Exact Zeon project, world, object names, well anchors, and provided skills.
10. Confirmed pipette volume units, tip policy, and aspirate/dispense speeds.
11. How the BioTek ELx808 export represents wells and timestamps.
12. Who owns the emergency stop and approves the first physical transfer.

## Recommended event strategy

1. Get the official Zeon project and compound map before writing any adapter.
2. Confirm one real sfGFP evidence file.
3. Make one vehicle transfer and one candidate transfer work in Zeon simulation.
4. Repeat those two transfers physically with the emergency-stop owner present.
5. Parse one real kinetic export before attempting the full plate.
6. Run round 1, freeze its raw reader file, and generate round 2 automatically.
7. Use Zeon's native resume ledger instead of inventing a second physical ledger.
8. Record the real run as soon as it works.
9. Freeze the demo path before adding docking, computer vision, or extra agents.
