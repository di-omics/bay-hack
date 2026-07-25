# On-site runbook

Track C is the primary entry. Use [TRACK_C_ONSITE.md](TRACK_C_ONSITE.md) as the
operating runbook.

## Fast start

```bash
git pull
python3 -m bayhack.track_c_demo --fault partial_uncap
python3 -m bayhack.track_c_dashboard
python3 -m bayhack.preflight
pytest -q
```

Then collect the assigned arm, gripper, tube, camera, fixture, named Zeon
objects, E-stop owner, and approved speed. Do not write a venue adapter until
those facts are known.

## Demo freeze

Rehearse one clean run, one recovered partial uncap, and one safe stop. Freeze
physical changes at least two hours before submission. Keep the Track A TEM-1
dashboard and the standard-library Track C simulation as fallbacks.
