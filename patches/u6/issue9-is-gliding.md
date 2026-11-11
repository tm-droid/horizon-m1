# Issue 9: is_gliding always 0

Root cause: `crates/horizon-client/src/mobs/cem_anim.rs` has no `is_gliding` entry in the `params!` flag list (lines 44 to 72), so FA expressions that read it get 0. `Extra::fall_flying` (`mobs.rs:1176`) already holds the elytra state.

Fix: `is-gliding.patch` (this directory), two lines in `cem_anim.rs`: `"is_gliding" => Gliding,` in `params!`, and `Gliding => flag(m.extra.fall_flying),` next to `Sprinting`. `git apply --check -p1` passes on `nightly-2026-11-08-fdc87ae`. Not compiled (no cargo builds allowed); it relies on the `params!` macro generating the `Gliding` variant like the other entries.
