# adaptive-upload-f42 (java-perf-mod-map port #1)

Status: **ready, UNBUILT / UNTESTED in engine** (anchors, `git apply --check`, rustc `-Zunpretty` parse, and std-only logic tests; no cargo, no game).
Base: r2 stage (f42 + cloud-prep + shadow-scratch + qos-backport, jobpool-qos, sprite-compress, emissive-bsearch, pass-merge, shadow-dedup). Touches `crates/horizon-client/src/game.rs` and `crates/horizon-client/src/game/remote.rs` (reset calls). Order-independent with particle-cull-f42.

## What
`Game::update_world` uploads queued section meshes under one of two allowances: the player's Chunk Updates / Upload Budget
(`graphics.rs:573-575`, consumer `game.rs` ~16279), or, when both are 0 (default), a 2 ms slice (6 ms while the view is arriving).
This multiplies that allowance by a factor `s` in `[1.0, 2.0]` computed by `mod adaptive_upload` (appended to game.rs):
`chunk_updates` and the KiB budget via `scale_count/scale_bytes` (0 = unlimited stays 0), the time slice via `scale_duration`.

Factor inputs
- busy time = max(CPU ms, GPU ms) of the last rendered frames (EMA 0.2), fed from the existing `record_cpu` spot. It is not the frame interval, so vsync waits do not hide headroom.
- `<= 8 ms` busy: 2.0, `>= 14 ms`: 1.0, linear between (frame over budget: back to today's allowance).
- backlog grew within the last 10 updates: at least 1.5. Player standing still (centre chunk unchanged for 20 updates): 2.0. Both only while the frame is not busy: busy time `>= 14 ms` (r3 review fix) or no timed frame yet caps the factor at 1.0, so it never adds work to a slow frame. Empty backlog: 1.0.
- The tracker is reset (`adaptive_upload::reset`) on world open, server join and each login/respawn/dimension change (`remote.rs` `enter_remote_dimension`, join, `finish_open_world`), so a new load starts with the fixed allowance until frames are timed again.
- `HORIZON_ADAPTIVE_UPLOAD=0` disables it (factor 1.0 = r2 behaviour) for A/B inside one binary.

## Why this cannot regress settle
The factor is never below 1 and the per-frame allowance is `ceil(base * s) >= base`, so every frame uploads at least what r2 uploads. Total wall time to drain a backlog is frames*base_cost + per_mesh*meshes: more meshes per frame only removes per-frame overhead. Post-flight (player stopped) the factor is 2.0 at once, i.e. the opposite of the failed fixed-512 KiB test. Tested by a closed-loop model (`settle_never_takes_longer_than_the_fixed_allowance`).

## Expected gain / risk
- Gain: faster fill-in when frames are cheap (flight over cheap terrain, arrival, settle); during busy frames identical to r2. It does NOT lower 1% lows by itself: the floor is r2's allowance, so a spike r2 has (burst when budgeted at defaults = unlimited-ish) remains. If the goal is fewer spikes at default (0/0 = auto 2 ms slice), this is a throughput feature, not a spike limiter. Lower the base values to trade the other way.
- Risk: a 2x slice (4 ms / 12 ms arriving) on a frame that was cheap but whose next frame is heavy can add one hitch; the EMA reacts within ~5 frames. Possible (unmeasured) GPU upload contention. Effect on visuals: none (same meshes, same order, only timing).
- Visual change: none (meshes appear a few frames earlier, never later than r2).

## Files
`prepare.py` (render()/CLI like emissive-bsearch), `edits.json`, `adaptive-upload.patch`, `build-plan.json`, `standalone_tests.py` (extracts the module, 8 tests).
