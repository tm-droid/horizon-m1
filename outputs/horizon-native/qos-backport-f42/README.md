# qos-backport-f42

Verdict: **ready**. Status: UNBUILT / UNTESTED (static symbol and anchor checks only; no cargo, no game run).

- Origin: horizon-rust/horizon main 9cfac94b + 0f7f9db8 (both touch only lod.rs + horizon-threads/src/lib.rs)
- Hook API: none (no native hook; plain engine source, host_api 359 unaffected)
- What: Far terrain threads (Far meshing, Far terrain, Far sampling) call horizon_threads::far_terrain_current(): on macOS pthread_set_qos_class_self_np(QOS_CLASS_UTILITY) instead of the no-op behind_server(). From 0f7f9db8 they step back (far_terrain_behind) only while Lod::set_near_loading is true and return to QOS_CLASS_DEFAULT once the near terrain is in. Linux/Android keep behind_server; Windows gets BELOW_NORMAL.
- Why: On an M1 (4P+4E), far-terrain sampling/meshing competed with the threads that mesh and light chunks around the player, worst while a world opens. Utility QoS steers them toward E cores and below P-core work; the second commit avoids leaving them parked on E cores for the whole session.
- Expected gain on M1: Unmeasured. Expected: smoother world open and fewer frame-time spikes while flying into new chunks, only if far terrain / LOD is active in the instance. No effect on steady-state FPS with far terrain off.
- Risk: Low. Both commits apply byte-identically to f42 (verified against git apply of the upstream patches). Risk is scheduling-only: far terrain may fill in later (pop-in of distant LOD) while the near terrain loads. Compile not run: uses libc::qos_class_t::QOS_CLASS_UTILITY/DEFAULT, libc is already an apple dep of horizon-threads and idle() already uses QoS.
- Visual change: None in steady state. Distant LOD tiles may appear slightly later during world open.
- Files: crates/horizon-client-render/src/lod.rs, crates/horizon-threads/src/lib.rs

## Use
`python3 -I prepare.py --workspace <owned copy of f42> --record <new.json>` or, from build-m1-performance.py,
`mod.render(relative, bytes)` for each of `mod.FILES` plus `mod.NEW_FILES`. Anchors must match exactly once; files identical
to pristine f42 must hash to the reviewed output (`edits.json`). `qos-backport.patch` is the same change as a unified diff (`git apply -p1`).
Verified: transform and patch apply cleanly to a clonefile copy of pristine f42 in the scratchpad; nothing under
launcher-data/native/source or candidate-source was touched.
Contract and plan: `hook-contract.json`, `build-plan.json`.
