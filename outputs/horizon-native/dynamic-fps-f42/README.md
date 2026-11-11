# dynamic-fps-f42

Verdict: **needs-adaptation (done) but NOT recommended for the bench candidate**. Status: UNBUILT / UNTESTED (static symbol and anchor checks only; no cargo, no game run).

- Origin: Lyvt-Dev/dynamic-fps-for-rust 0.1.0 (MIT), registry horizon-rust/horizon-mods mods/dynamic_fps_for_rust.toml
- Hook API: none declared (horizon-mixins HEAD/RETURN injections on engine functions). Pinned to 998b1d83; all injection targets and every game field it touches exist in f42 (see hook-contract.json). f42 already has native_framerate_limit hooks and its own AFK/minimised/menu throttle (horizon-client-input window.rs framerate_limit) plus Battery Mode (settings.horizon.battery_limit); this mod adds unfocused/hovered caps and a render gate on top.
- What: Per-frame decision from focus/hover/occlusion/minimise/idle: caps FPS (defaults: 0=uncapped focused, hovered 30, unfocused 10 after 500 ms, minimised 1, idle 20 after 60 s without input while FOCUSED, battery 30) by lowering framerate_limit and skipping Game::render in between (returns Ok(false)). Optional volume lowering (off by default). Config config/dynamic-fps-for-rust.json, written on first start; unknown keys are rejected.
- Why: Power/thermal savings for a backgrounded or idle client on a fanless M1 Air.
- Expected gain on M1: Zero while focused and active. Savings only when unfocused/idle. No benchmark gain; bench risk instead.
- Risk: BENCH HAZARD: (1) unfocused window drops to 10 FPS (30 if the cursor hovers it) and render() is skipped, so a harness driving an unfocused window would stop presenting; (2) a FOCUSED window with no input for 60 s drops to 20 FPS (idle phase), which hits long soak runs and hands-free benches. Neutralise with the bench config below or leave the mod out of bench candidates. Windows with --headless/--offscreen/--frames are exempt (supported() returns false).
- Visual change: None while focused and active. Presented frame rate drops when unfocused, idle, or minimised.
- Files: crates/horizon-client/src/game.rs, game/options.rs, game/music.rs; adds game/dynamic_fps_runtime.rs and game/dynamic_fps_adapter.rs

## Use
`python3 -I prepare.py --workspace <owned copy of f42> --record <new.json>` or, from build-m1-performance.py,
`mod.render(relative, bytes)` for each of `mod.FILES` plus `mod.NEW_FILES`. Anchors must match exactly once; files identical
to pristine f42 must hash to the reviewed output (`edits.json`). `dynamic-fps.patch` is the same change as a unified diff (`git apply -p1`).
Verified: transform and patch apply cleanly to a clonefile copy of pristine f42 in the scratchpad; nothing under
launcher-data/native/source or candidate-source was touched.
Contract and plan: `hook-contract.json`, `build-plan.json`.

## Bench configuration
Pre-seed `config/dynamic-fps-for-rust.json` as `{"enabled": false}` for any benchmark, soak or hands-free run, or the window
is throttled when unfocused (10 FPS, 30 hovered, skipped render) and after 60 s idle while focused (20 FPS).

Third-party code (MIT, see LICENSE) is copied unmodified into `new-files/`; the injection glue is rewritten as direct edits.
