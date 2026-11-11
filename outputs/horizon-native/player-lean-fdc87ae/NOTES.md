# Player lean/stiff with FA+Player-v1.1

Cause: cem_anim.rs fed `rot_y` (and `rot_x`) to EMF expressions in DEGREES (`m.body_yaw`, raw tick value).
EMF/OptiFine supply them in RADIANS. The pack (a_player_variables.jpm) treats rot_y as radians:
`var.compass = wraprad(-rot_y + pi)`, and
`var.yaw_drag = rot_y*min(1,frame_time*12..)+var.yaw_drag*...`, `var.yaw_speed = var.yaw_drag - rot_y`.
`var.root_rz = torad(30*clamp(var.yaw_speed*2,-1,1)*limb_speed)*var.mforward*...` and
`var.root_ry = torad(60*clamp(var.yaw_speed*3,-1,1))*...` (root.rz/ry applied when varb.21_2_plus; overlays 21-2 and 21-5 both
apply since pack formats >=42/55). In degrees, yaw_speed is ~57x too large, and the 20Hz non-interpolated body yaw
steps saturate the clamp, so root leans +-30deg*limb_speed whenever the player runs.
Fix: rot_x/rot_y radians, rot_y uses partial-tick interpolated body yaw (previous_body_yaw -> body_yaw by s.partial).
head_yaw stays degrees (pack uses torad(head_yaw)). No CEM warnings about player in logs.
Not verified at runtime (no build). Unit test added: rot_x_and_rot_y_are_radians.
Test: cargo test -p horizon-client rot_x_and_rot_y; in game, run straight in 3rd person with the pack.
