# Horizon perf mods and upstream backports: prep for the next f42 candidate (2026-11-05)

Pin: `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`, hook API 359. Everything here is **prepared, not built or run**. No cargo, no game, no device queue was touched. Source trees (pristine f42 and `m1-performance/candidate-source`) were read only; transforms were applied to `cp -cR` copies in the scratchpad.
Compatibility was checked statically: every symbol and anchor exists in f42 (rg), and the transforms apply cleanly. **Nothing is compiled**, so type and borrow errors are still possible.

## Verdicts

| Item | Verdict | Visual change | Bench-safe | Dir |
|---|---|---|---|---|
| qos-backport (upstream 9cfac94b + 0f7f9db8) | ready | none | yes | `outputs/horizon-native/qos-backport-f42/` |
| sprite-compress (upstream 2c9dac6b) | needs-adaptation, done | none | yes | `.../sprite-compress-f42/` |
| fast_items 0.1.0 | ready as in-tree transform | YES (flat, billboarded drops) | only with `enabled:false` for parity runs | `.../fast-items-f42/` |
| dynamic_fps_for_rust 0.1.0 | needs-adaptation, done; do not put in bench candidates | none while focused and active | NO unless `enabled:false` | `.../dynamic-fps-f42/` |

None is incompatible. Both mods ship as `.hnmod` source bundles pinned to Horizon `998b1d83` (832 commits after f42) and use horizon-mixins injections on engine functions, **not** `native-hooks.json` hooks, so API 359 is irrelevant to them. As bundles they would need the version-mismatch override; the in-tree transforms avoid that and compose with the existing cloud-prep and shadow-scratch transforms. Registry entries are TOML pointers only (`horizon-mods/mods/*.toml`, sources in Lyvt-Dev repos, MIT, cloned to the scratchpad and never executed).

## fast_items (Lyvt-Dev/FastItems-for-Horizon 0.1.0)
- Does: dropped (and pickup-animation) items. Sprite items keep only front quads flattened to a plane (only for canonical 1px slabs). All dropped items take the camera orientation instead of Y spin. Optional `entity_shadows:false`.
- Injections (3): `MODIFY_VARIABLE state` and `pose` in `game::item_draw::dropped_item_geometry`, `MODIFY_VARIABLE item` in `Game::entity_geometry`. All exist in f42 at the same shape (`let state = self.resolve_item(.. Ground ..)`, `let pose = Mat4::from_translation(..)`, `let item = shadow_params("minecraft:item")`). `item_draw.rs`, `item_render.rs`, `item_bake.rs` are unchanged between f42 and 998b1d83.
- Symbols verified in f42: `ItemRenderState.layers`, `LayerGeometry::Quads(Arc<BakedItemModel>)`, `BakedItemModel{quads,uses_block_light}` (Clone), `ModelQuad{positions,facing}`, `Direction`, `Game::camera_orientation() -> Quat`, deps serde/serde_json/glam in horizon-client.
- User-visible: yes. Paper-flat sprite drops, every drop faces the camera, including 3D blocks. Writes `config/fast-items.json` on first start (`render_sides`, `affect_3d_models`, `enabled`).
- Gain: small, only with many drops. Not a benchmark lever.

## dynamic_fps_for_rust (Lyvt-Dev/dynamic-fps-for-rust 0.1.0)
- Does: lowers `framerate_limit()` and skips `Game::render` (returns `Ok(false)`) by window state. Defaults: focused uncapped, hovered 30, unfocused 10 (after 500 ms), minimised 1, idle 20 (after 60 s without input **while focused**), battery 30. Volume lowering off by default.
- Injections (4): HEAD `Game::handle_window_event`, RETURN `options::Game::framerate_limit`, HEAD cancellable `Game::render`, HEAD `music::Game::tick_sound_engine`. All exist in f42; `handle_window_event` has an extra `origin` argument (harmless, not bound). Fields used all exist: `focused`, `last_input`, `window: Option<Arc<Window>>`, `title`, `options.{headless,offscreen,frames,world_frames}`, `settings.horizon.battery`, `settings.master_volume`, `audio.master`.
- Redundancy: f42 already throttles minimised, AFK and menu states, has Battery Mode, and `native_framerate_limit`. The mod adds unfocused/hovered caps and the render gate.
- Bench hazard (important): an unfocused window drops to 10 FPS and render is skipped, so the harness window stops presenting. A focused window with no input for 60 s drops to 20 FPS (idle phase), which also hits long soak and hands-free runs. Headless, offscreen and `--frames` runs are exempt. Pre-seed `config/dynamic-fps-for-rust.json` with `{"enabled": false}` for any bench, or leave the mod out. Config is written on first start with the defaults, and unknown keys are rejected.
- Gain on M1: none while focused. Power and thermals only when backgrounded or idle.

## qos-backport (upstream main 9cfac94b, 0f7f9db8)
- Far terrain threads (Far meshing, Far terrain, Far sampling) call `horizon_threads::far_terrain_current()`: utility QoS on macOS (Linux keeps `behind_server`, Windows below-normal). 0f7f9db8 steps them behind only while `Lod::set_near_loading` is true and back to default QoS afterwards.
- Both patches apply to f42 (sequentially; 0f7f9db8 depends on 9cfac94b). The Python transform output is byte-identical to `git apply` of the upstream patches (lod.rs `0e19619a...`, lib.rs `fcf03563...`).
- Expected: smoother world open and chunk-load frame times when far terrain/LOD is active on the M1's 4P+4E cores. Unmeasured. Steady-state FPS unchanged. Distant LOD may fill in slightly later while near terrain loads.

## sprite-compress (upstream main 2c9dac6b)
- Block texture array CPU copy (about 21 MB with default resources) is lz4-compressed on a "Sprite packing" thread once a renderer exists; `get()` decompresses for a rebuilt renderer.
- f42 drift: upstream's second assets.rs hunk and test hunk did not apply (f42 `RenderAssets` has `generation`, `GENERATION` static). Re-anchored on `fn invalid(`; the unit test is appended as a separate `mod sprite_pixels_tests`. `game.rs` and `sprite_cache_parity.rs` hunks apply as is; `lz4_flex` is already a dependency of horizon-client-render; `resource_memory.rs` keeps working through `SpritePixels::len()`. All `.pixels` users of `RenderAssets` were grepped (game.rs x2, two examples).
- Expected: about 20 MB less RSS. No FPS effect. Visual change none (pixels identical after decompress).

## Verification done
- Each transform (`prepare.py --workspace`) and each `.patch` (`git apply --check -p1`) applied cleanly to a clonefile copy of pristine f42 (diff counts, added/removed lines: qos 79/3, sprite 106/5, fast-items 311/3, dynamic-fps 485/2).
- All 24 application orders of the four mods give identical output, so they compose with each other. The shared file is `game.rs` (sprite, fast-items, dynamic-fps); composed `game.rs` SHA256 `9ecd00b4...5d1e`. No overlap with cloud-prep/shadow-scratch (`gfx.rs`, `pack_post.rs`).
- Not done: compile, clippy, unit tests, any runtime or visual check.

## Build step (next candidate)
Edit `outputs/horizon-runtime/build-m1-performance.py` (not edited here; it is the candidate build's owner file). After `transforms[target], _ = shadow.transform(transforms[target])` (about line 168) add:

```python
    # Optional perf mods: choose a subset. dynamic-fps stays out of bench candidates.
    new_files = set()
    for name in ("qos-backport-f42", "sprite-compress-f42"):   # add "fast-items-f42" only for non-parity runs
        spec = importlib.util.spec_from_file_location(name.replace("-", "_"), patch_root / name / "prepare.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for relative in mod.FILES:
            transforms[relative] = mod.render(relative, transforms.get(relative) or (WORKSPACE / relative).read_bytes())
        for relative, text in mod.NEW_FILES.items():
            transforms[relative] = text.encode()
            new_files.add(relative)
```

Then replace the expected-file check (about lines 173 to 176) with:

```python
    expected = {"crates/horizon-client-render/src/gfx.rs", "crates/horizon-client-render/src/gfx/pack_post.rs",
                "crates/horizon-client-render/src/lod.rs", "crates/horizon-threads/src/lib.rs",
                "crates/horizon-client-render/src/assets.rs", "crates/horizon-client/src/game.rs",
                "crates/horizon-client/examples/sprite_cache_parity.rs"}   # drop entries for mods not chosen
    if set(differences) != expected | new_files or set(patched) - set(baseline) != new_files:
        raise SystemExit("Unexpected transformed source files")
```

Notes: `differences` is built from `patched.items()` with `baseline.get`, so new files appear there too (hence `expected | new_files`). `(WORKSPACE / relative).write_bytes(data)` later works for new files because their parent dir (`game/`) exists. The candidate version string already derives from the transformed inventory. Also bump `CARGO_BUILD_JOBS=1` as is. Keep cloud-prep and shadow-scratch first; order among new mods does not matter.

Recommended inclusion for the next M1 candidate: qos-backport and sprite-compress (no visual change, low risk). fast-items only as a separate A/B candidate; dynamic-fps not for benches.

## Blocking / open
- Nothing blocks preparation. Blocked on: compile check (`cargo check --offline --locked -p horizon-client --lib`) once the device queue is free; no measurement of any gain exists yet.
- Possible unknown: workspace lints may promote the new modules' dead-code warnings (fast-items, dynamic-fps) to errors; not checked.
