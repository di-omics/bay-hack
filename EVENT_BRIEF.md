# Event brief -- confirmed from the host (emails, Jul 20)

Source of truth for the **challenge** is the event page / track guide. Source of
truth for every reagent name, concentration, volume, timing, wavelength, control
definition, and hardware call is the **organizer at kickoff**. This file records
only what the host announced, and guesses no protocol values (see
[TEM1_TRACK_A.md](TEM1_TRACK_A.md) and `bayhack/tem1.py`, which refuse to run
physically until the organizer configures those fields).

## Track A -- Close the Loop  (our track)

Hunt for **TEM-1 beta-lactamase inhibitors**: choose compounds, design the
protocol, run the assay on robots, read the plate, and let round 1 sharpen
round 2. This maps 1:1 onto the bay-hack DBTL loop.

## Announced partners / hardware / platform

- **Arms: UFactory** (affordable open-source robotic arms).
- **Zeon: a simulation AND control environment** -- develop and verify in Zeon's
  simulator, then execute physically. Zeon Systems docs are the API reference.
  (This answers `ONSITE_RUNBOOK.md`'s "can we sim first?" -> yes.)
- **Reagents: Sepia Bio Cell-Free Protein Synthesis (CFPS) kits** -- express
  TEM-1 in vitro, confirm expression vs a no-template control, then screen.
- **Track B partner: OpenShelf** (automated storage <-> bench execution).
- **Agent framework partner: Google ADK** -- our loop is agent-agnostic (it runs
  over MCP today via `bayhack/mcp_agent.py`, and is ADK-drivable).

## Logistics

- **Sat:** doors 9:30a, kickoff **10:00a sharp** (be on time -- teams form here),
  finalize teams 11:00a, build #1 12:00p, dinner + roundtables 6:00p, build #2
  7:00p, midnight snack.
- **Sun:** doors 8:00a, **final submission 2:30p**, walk-around showcase
  3:30-4:30p, demos + pitching 4:30-5:30p.
- **Bring:** laptop + charger, notebook, water, a coding agent (Claude Code),
  an extra layer, optional sleeping bag. Uber/Lyft (street parking limited).
  925 Harrison St, SF.

## Still owed at kickoff (do not guess)

substrate name (e.g. a chromogenic/fluorogenic beta-lactam), read wavelength,
reaction + assay-mix + compound + substrate volumes, pre-incubation time, control
definitions, and the exact UFactory / Zeon motion calls. `tem1.py` already lists
these as "venue fields owed" and blocks physical execution until they are set.
