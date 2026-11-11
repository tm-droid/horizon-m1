# Frame vs GPU-timer gap (2026-11-11)

Tree: native/build-src.noindex (fdc87ae). Read-only analysis, nothing built or run. Paths below are relative to `crates/horizon-client-render/src/` unless noted.

## Data
d5-19-makeup-DAILY5.json: static frame avg 1000/36.46 = 27.43 ms, gpu avg 24.49 -> gap 2.94 ms. Flight: 29.45 vs 28.08 -> gap 1.37 ms.
CPU 7.0 ms is work only: game.rs:18206 computes `elapsed - r.last_wait`, so waits are excluded.

## Frame loop (macOS)
- Surface: gfx.rs:2618-2627 picks mode; `set_present_mode` (gfx.rs:5163-5190) with vsync off + `presentMode:auto` -> Immediate. wgpu-hal Metal: displaySync=false (third_party/wgpu-hal/src/metal/surface.rs:264-266,339), `setMaximumDrawableCount(latency+1)` (surface.rs:333), latency range 1..=2 (adapter.rs:450-456), wgpu default 2 -> 3 drawables, the Metal maximum. Cannot be raised.
- Order, all on the main thread: `queue.take_waited` -> `surface.get_current_texture()` (gfx.rs:7623, blocks in `nextDrawable`, surface.rs:~362) -> encode (one encoder, timer.begin gfx.rs:9364 ... timer.end gfx.rs:11126) -> `queue.submit` (gfx.rs:11250) -> `queue.present` (gfx.rs:11315) -> limiter.
- Submit thread is OFF on macOS: gfx/submit.rs:14-24 `wanted()` is true only on Linux unless `HORIZON_SUBMIT_THREAD=1`. (The earlier cpu-hotpaths note that says "submit thread" for this build is wrong for macOS.) The `submit_later` branch at gfx.rs:11196-11241 is not taken.
- CPU waits on the GPU per frame: only `nextDrawable`. No `device.poll(Wait)` in the frame path (gfx.rs:6742 is screenshot-sequence only, 11793 offscreen `wait_frames`, 11836 screenshot). Occlusion/cull/depth readbacks use `map_async` after submit (non-blocking). GPU timer: `collect` uses `PollType::Poll` (gfx/timing.rs:~253), `submitted` uses `on_submitted_work_done` callbacks only. So (b-fence) and (d) are refuted.
- Present-mode pacing: limiter `end_frame_on_grid` (client-input/src/window.rs:248-315, maxFps 60 = 16.7 ms) never waits when frames are 27 ms: it resets `last_frame_time` when the deadline already passed. Not a factor. Fifo/60 Hz quantisation does not apply (Immediate).
- Frame format = swapchain 8-bit (hdr:false, MakeUp is not a 0.2 pack; gfx.rs:2063-2076), so `Readback::target` returns None and there is no extra full-screen blit after the timer end marker.

## What the timer covers
Interval = start of a 1-thread compute pass (gfx/timing.rs:155-168, first in the frame CB) to the end of a 1-pixel Load render pass on the frame target after `draw_overlay` (timing.rs:184-208; gfx.rs:11126). Whole 3D/pack/HUD pipeline is inside. NOT covered:
1. Anything before the start stamp in the same CB: section-copy blits (`section_copies` encoder is reused as the frame encoder, gfx.rs:7430/~7690) and wgpu's pending-write staging CB.
2. Anything after the end stamp: `uploads.finish`, `section_uploads.finish`, `readback.present` (no-op here), presentDrawable.
3. The gap between consecutive command buffers and any wait for the drawable to be free.
Static scene uploads 0 bytes (`static_bytes_uploaded 0`), so (1)/(2) should be tiny.

## Verdict
Gap is not CPU-GPU serialization and not a missing timed pass. Most likely (confidence ~50%) it is GPU idle between frames caused by drawable recycling: with Immediate the compositor releases the previous on-screen drawable only when a newer one is taken for display, which lands on its ~16.7 ms composite grid (possibly a tick late). Frame N+2 cannot acquire until frame N is displayed, then still needs ~5 ms of CPU encode (render 4.4 + submit) after the acquire. If the release lands more than ~19 ms after N's GPU end, frame N+1's 24.5 ms of queued work runs out first and the GPU idles. Supporting: (i) prior profile shows ~50% of CPU time in `semaphore_timedwait` (= nextDrawable); (ii) gap shrinks from 2.9 to 1.4 ms when GPU grows 24.5 -> 28.1 ms (more queue slack), which untimed fixed GPU work would not do. Alternative (~35%): untimed GPU work/inter-CB scheduling gap of ~1-3 ms (items 1-3 above). Remaining ~15%: timestamp period/clock error on Apple GPU.
Cannot be separated by reading code; needs one measurement.

## Discriminating experiments (no rebuild)
- `resolutionScale:75` (horizon-graphics.txt) and compare `frame avg - gpu avg`. Gap stays ~constant or grows as GPU shrinks (less queue slack) -> drawable bubble. Gap scales with GPU (~10%) -> timer clock/period error. Gap shrinks with resolution but not to zero -> untimed per-pixel work.
- `HORIZON_SUBMIT_THREAD=1` in the bench env: moves finish/submit/present off the main thread. Expected gain 0-0.5 ms (acquire still blocks before encode). It stalled on Metal offscreen per submit.rs:14-18, so bench it, do not ship it.
- `presentMode:fifo`: expected worse (30 fps lock, 33 ms), only useful to confirm vsync-quantised recycling.
Settings that cannot help: framePacing (limiter inert at 27 ms), maxFps (60), frame latency (already at the Metal maximum 2 -> 3 drawables).

## Proposed fix (needs a build; no patch written because it cannot be compiled/tested here)
Defer the acquire: draw the frame into the persistent offscreen texture (existing `Readback::target` path, gfx/readback.rs:23-62, already supports "frame in own texture, then blit onto swapchain"), call `get_current_texture` after encoding, and finish with a full-screen copy (`copy_texture_to_texture`, swapchain already has COPY_DST, gfx.rs:2615) just before submit. This hides ~5 ms of encode behind the drawable wait, so a late release stalls the GPU only if it exceeds ~24 ms instead of ~19 ms. Cost: one 16 MB copy (~0.3-0.5 ms GPU, adds to the timer-uncovered part). Expected net gain 0.5-1.5 ms/frame (1-5%) IF the bubble model is right; zero otherwise. Touches gfx.rs:7620-7700 (acquire, surface_frame uses at 7660-7700, 11196, 11305-11315), readback.rs, frame_gen/hdr paths. Do the resolutionScale experiment first; do not build this on the current evidence alone.
A cheaper diagnostic to add first: bench JSON field for `last_wait` split (acquire vs queued) plus GPU idle = frame - gpu per frame, so the acquire stall time is visible (gfx.rs:7625 already measures `acquire.elapsed()`).
