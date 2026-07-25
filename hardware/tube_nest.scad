// Parametric split-collar nest for Track C tube-access trials.
// Measure the actual venue tube before exporting an STL.

$fn = 96;

tube_od_mm = 13.0;
radial_clearance_mm = 0.25;
collar_wall_mm = 4.0;
collar_height_mm = 24.0;
base_x_mm = 72.0;
base_y_mm = 46.0;
base_z_mm = 6.0;
entry_funnel_mm = 2.0;
split_width_mm = 2.0;
mount_hole_d_mm = 4.2;
mount_hole_spacing_mm = 54.0;
cap_park_d_mm = 18.0;
cap_park_depth_mm = 3.0;

tube_bore_mm = tube_od_mm + 2 * radial_clearance_mm;
collar_od_mm = tube_bore_mm + 2 * collar_wall_mm;
center_x = base_x_mm / 2;
center_y = base_y_mm / 2;

difference() {
  union() {
    translate([0, 0, 0])
      cube([base_x_mm, base_y_mm, base_z_mm]);
    translate([center_x, center_y, base_z_mm])
      cylinder(h = collar_height_mm, d = collar_od_mm);
  }

  // Tube bore with a shallow funnel for fast, self-aligning insertion.
  translate([center_x, center_y, base_z_mm - 0.1])
    cylinder(h = collar_height_mm + 0.2, d = tube_bore_mm);
  translate([center_x, center_y, base_z_mm + collar_height_mm - entry_funnel_mm])
    cylinder(
      h = entry_funnel_mm + 0.2,
      d1 = tube_bore_mm,
      d2 = tube_bore_mm + 2 * entry_funnel_mm
    );

  // Split lets the collar flex and resist tube rotation during cap torque.
  translate([
    center_x - split_width_mm / 2,
    center_y,
    base_z_mm - 0.1
  ])
    cube([
      split_width_mm,
      collar_od_mm,
      collar_height_mm + 0.2
    ]);

  // Two mounting holes for a deck plate or temporary clamp fixture.
  for (x = [
    center_x - mount_hole_spacing_mm / 2,
    center_x + mount_hole_spacing_mm / 2
  ])
    translate([x, 8, -0.1])
      cylinder(h = base_z_mm + 0.2, d = mount_hole_d_mm);

  // Cap parking pocket keeps the removed cap visible to the camera.
  translate([base_x_mm - 13, base_y_mm - 13, base_z_mm - cap_park_depth_mm])
    cylinder(h = cap_park_depth_mm + 0.2, d = cap_park_d_mm);
}
