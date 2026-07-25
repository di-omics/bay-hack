# Track C fixture

`tube_nest.scad` is a configurable split-collar fixture for one-tube demos. It
adds three useful physical constraints:

1. A funnel guides the tube into a repeatable pose.
2. A split collar resists tube rotation while the arm applies cap torque.
3. A visible cap pocket gives the camera a second cue that uncapping succeeded.

## Before printing

Measure the actual tube outer diameter with calipers. Update `tube_od_mm` and
print a short fit coupon first. Start with 0.25 mm radial clearance, then adjust
for the printer and material. Confirm that the tube cannot lift or rotate during
uncapping, but can still be removed without excessive force.

Do not export a final STL before the venue tube and mounting surface are known.
The source stays parametric so the event team can adapt it in minutes.
