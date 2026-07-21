# Bring-your-own liquid-handling kit

The portable demo is a six-run, two-component formulation on one 96-well plate.
Each experiment mixes 40 uL in a destination well. The accepted well then sends
20 uL to H12 as the Track A follow-up action.

## Pack this no matter what the venue provides

- Laptop, charger, USB-C hub, HDMI adapter, and a long charging cable
- Phone tripod or small USB camera
- Diffuse white LED light or compact light panel
- White and black cards for camera exposure and color calibration
- Two clear, flat-bottom, 96-well plates with lids, ideally 360 uL wells
- One extra plate as a sealed fallback plate for the walk-around showcase
- One P20 or P200 manual pipette as a rescue path, if you own a calibrated one
- At least 48 compatible manual tips in clean racks
- Six 1.5 mL tubes and two 15 mL tubes
- DI water in a sealed, labeled tube or bottle
- Food-grade dye in a sealed, labeled tube for the camera-color fallback
- Nitrile gloves, absorbent bench pads, wipes, labels, and secondary containment
- Painter's tape, a fine marker, zip ties, and a small ruler or caliper
- Printed QR code for the repo and live site

The working run uses 12 tips for six formulations and one more tip for the
follow-up transfer. The volume qualification uses at least six more robot
dispenses plus independently prepared standards. Bring at least 48 so one full
qualification, one assay run, and one recovery do not become a crisis.

## Only bring these after the host confirms compatibility

- Robot-specific tip racks
- A black or black-clear-bottom plate for fluorescence
- Rhodamine B or any other fluorescence standard
- Instrument-specific carriers, nests, adapters, or plate seals
- Any chemical beyond food dye and water

Ask the host which liquid handler, pipetting end effector, reader, plate type,
tip type, wavelengths, and chemical rules will be available. Robot tips and
plate-reader optics are not universal.

If Rhodamine B is approved, bring only a small pre-diluted quantity, the current
SDS, clear labels, and secondary containment. Follow the venue's PPE and waste
rules. Do not bring live cells, clinical samples, biohazards, or unlabeled liquids.

## Plate map

Use one plate for the assay below and a second plate for the independent volume
standards and replicated dispense test. Keep the third plate sealed as the
walk-around fallback.

| Position | Purpose | Suggested starting load |
|---|---|---:|
| A1 | assay stock | 250 uL |
| A2 | diluent | 250 uL |
| B1 onward | world-model proposals | 40 uL each |
| H12 | accepted product | receives 20 uL |

The deterministic showcase normally converges in six runs, so 250 uL in each
source well provides comfortable headroom. If you change the assay volume or
budget, calculate source demand before loading the plate.

## Three readout modes

### Mode A: real plate reader

Use the reader and approved reagent supplied or confirmed by the venue. Keep the
camera aimed at the plate so the physical run stays visible to the audience.

### Mode B: camera colorimetry

Use food dye plus water, lock camera exposure and white balance, and measure a
fixed region of each well. Call this a colorimetric linearity gate, not a
Rhodamine gate.

### Mode C: no liquid handler

Use the venue arm for plate movement or pipette manipulation, then execute the
same verified plan manually with the rescue pipette. The scientific loop,
measurement, trust receipt, and follow-up remain real.

## Before leaving home

- Run `python -m bayhack.preflight --output run_artifacts/preflight.json`
- Run `python -m bayhack.demo --ledger run_artifacts/trust.json`
- Run `python -m bayhack.dashboard` and load it once with Wi-Fi disabled
- Save a screen recording of the full simulated run
- Confirm the source plate, tips, camera, and HDMI adapter fit in one bag
- Photograph the packed kit and the plate map

## Files to collect on-site

- `reader.csv` or one calibrated plate image per destination well
- `volume-gate.csv` with independent standards and replicated robot dispenses
- `cv_{well}_{run_id}.json` plus its image or venue trace ID
- `trust.json` from the completed physical loop
- `refusal.json` and `preflight.json` from the zero-motion checks

See `MEASUREMENT_ADAPTERS.md` and `VERIFICATION_ADAPTERS.md` for exact formats.
