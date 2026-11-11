# fast-items-f42

Verdict: **ready as in-tree transform (the .hnmod itself is pinned to 998b1d83; re-pin or --allow-version-mismatch needed if built as a bundle)**. Status: UNBUILT / UNTESTED (static symbol and anchor checks only; no cargo, no game run).

- Origin: Lyvt-Dev/FastItems-for-Horizon 0.1.0 (MIT), registry horizon-rust/horizon-mods mods/fast_items.toml
- Hook API: none declared: the mod uses horizon-mixins MODIFY_VARIABLE injections on engine functions, not native-hooks. compatibility.json pins horizon 998b1d83 (832 commits after f42; the only files in the compare that matter, game.rs and options.rs, are not the ones it hooks; item_draw.rs/item_render.rs/item_bake.rs are unchanged between f42 and 998b1d83).
- What: Dropped items (and pickup-animation items): sprite items lose their extruded sides (only the front quads are kept, flattened to z=0.5, only for canonical 1px-thick generated slabs) and every dropped item's pose takes the camera orientation instead of the Y spin (billboard). Optional entity_shadows=false removes item shadows. Config config/fast-items.json (written on first start).
- Why: Fewer vertices per dropped item (a sprite item drops from front+back+edge quads to 1-2 quads) and no per-item spin matrix work. Matches Lunar/BLC-style fast items.
- Expected gain on M1: Small, scene-dependent: only matters with many dropped items (mob farms, item floods, death piles). Negligible in a benchmark route with few drops. Unmeasured.
- Risk: Medium on correctness-not-compile: f42 anchors verified (state STORE in dropped_item_geometry, pose STORE, shadow_params in entity_geometry); in-tree edit replaces the mixin. Added code is MIT third-party; flatten cache holds up to 4096 Weak-keyed models. Not compiled.
- Visual change: YES. Dropped sprite items are paper-flat and all dropped items (including 3D blocks, affect_3d_models=true) always face the camera. Not vanilla parity. Set render_sides=true / affect_3d_models=false in config/fast-items.json to reduce, or enabled=false to turn off.
- Files: crates/horizon-client/src/game/item_draw.rs, crates/horizon-client/src/game.rs; adds game/fast_items_runtime.rs and game/fast_items_renderer.rs

## Use
`python3 -I prepare.py --workspace <owned copy of f42> --record <new.json>` or, from build-m1-performance.py,
`mod.render(relative, bytes)` for each of `mod.FILES` plus `mod.NEW_FILES`. Anchors must match exactly once; files identical
to pristine f42 must hash to the reviewed output (`edits.json`). `fast-items.patch` is the same change as a unified diff (`git apply -p1`).
Verified: transform and patch apply cleanly to a clonefile copy of pristine f42 in the scratchpad; nothing under
launcher-data/native/source or candidate-source was touched.
Contract and plan: `hook-contract.json`, `build-plan.json`.

Third-party code (MIT, see LICENSE) is copied unmodified into `new-files/`; the injection glue is rewritten as direct edits.
