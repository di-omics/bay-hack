# Event brief: confirmed from the host and official guide

Reviewed 2026-07-23 from the organizer email, Track A guide, attached Sepia Bio
protocol, and Zeon documentation. See
[OFFICIAL_TRACK_A_MATERIALS.md](OFFICIAL_TRACK_A_MATERIALS.md) for the complete
source-grounded notes.

The public guide is the source of truth for published facts. The track lead is
the source of truth if the venue protocol differs.

## Track A -- Close the Loop  (our track)

Hunt for **TEM-1 beta-lactamase inhibitors**: choose compounds, design the
protocol, run the assay on robots, read the plate, and let round 1 sharpen
round 2. The guide says the most valuable proof is round 1 data visibly changing
the round 2 plate.

Three robotic workflows are required:

1. Make TEM-1 with cell-free protein synthesis.
2. Confirm expression from the TEM-1-sfGFP fusion.
3. Screen compounds with nitrocefin kinetics.

## Announced partners / hardware / platform

- **Zeon:** Python skills, workflows, world objects, anchors, cloud simulation,
  and local real-hardware execution.
- **Arms:** UFactory hardware is an event partner. Confirm the exact model at
  kickoff.
- **Reagents:** Sepia Bio OpenCFPS kit, TEM-1-sfGFP template, nitrocefin,
  assay buffer, and a 95-compound DMSO library in source plates.
- **Labware:** 96-well flat-bottom assay plates, gas-permeable seals, and
  microcentrifuge tubes.
- **Equipment:** Axygen PlateMax sealer, Benchmark Incu-Mixer MP, and BioTek
  ELx808 reader.
- **Track B partner: OpenShelf** (automated storage <-> bench execution).
- **Agent framework partner: Google ADK.** The Track A guide says a framework
  such as ADK can drive the decision layer. It is optional, not the scientific
  acceptance gate.

## Confirmed assay facts

- Expression confirmation uses sfGFP fluorescence.
- The Sepia guide specifies Ex 485 nm and Em 528 nm, or equivalent.
- Activity uses nitrocefin, read at A490.
- Read every 30 seconds for several minutes.
- Use the initial A490 versus time slope as enzyme velocity.
- Every assay plate uses vehicle controls for maximum velocity and no-enzyme
  controls for minimum velocity and background.
- Everything is scored relative to those two control classes.

## Logistics

- **Sat:** doors 9:30a, kickoff **10:00a sharp** (be on time -- teams form here),
  finalize teams 11:00a, build #1 12:00p, dinner + roundtables 6:00p, build #2
  7:00p, midnight snack.
- **Sun:** doors 8:00a, **final submission 2:30p**, walk-around showcase
  3:30-4:30p, demos + pitching 4:30-5:30p.
- **Bring:** laptop + charger, notebook, water, a coding agent (Claude Code),
  an extra layer, optional sleeping bag. Uber/Lyft (street parking limited).
  925 Harrison St, SF.

## Still owed at kickoff

- event-scaled CFPS volume, plate format, speed, and duration
- sfGFP instrument and quantitative pass threshold
- assay-mix, compound, nitrocefin, and total volumes
- DMSO percentage and exact vehicle composition
- exact no-enzyme well composition
- pre-incubation duration and total kinetic window
- whether a known inhibitor control is supplied
- compound names, source wells, stocks, and permitted metadata
- exact Zeon project, skill, workflow, world, object, and anchor names
- electronic pipette volume units, speeds, and tip policy

`TEM1AssaySpec` pre-fills only facts published in the guide: sfGFP, Ex 485,
Em 528, nitrocefin, A490, and a 30-second cadence. Physical execution remains
blocked until all remaining fields are filled and the track lead confirms the
configuration.
