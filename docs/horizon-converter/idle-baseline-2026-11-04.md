# Horizon baseline with Xcode closed — 2026-11-04

This is the on-screen renderer baseline for the pinned official Horizon f42ef42 ARM64 client on the M1 MacBook Air. Both passes used the same disposable offline world, fixed NoAI cow, camera pose, 637 loaded terrain columns, and scripted 128-block flight. Both used Metal Immediate at 2560×1440, native 100% scale, 12/8 render/simulation distance, FOV 95°, cloud range 64, auto workers, efficient pacing, unlimited frame rate (slider 260), and shaders off. The built-in panel is 60 Hz; frame rates here measure the renderer rather than the number of distinct frames the display showed.

| Profile | Static avg / 1% low FPS | Flight avg / 1% low FPS | Static / flight p99 frame time | Static / flight mean GPU time |
| --- | ---: | ---: | ---: | ---: |
| Base Horizon | 252.85 / 59.80 | 188.37 / 56.22 | 13.23 / 15.93 ms | 3.79 / 5.36 ms |
| Horizon + 52 selected packs | 160.11 / 53.02 | 132.76 / 42.08 | 17.24 / 21.24 ms | 7.22 / 8.31 ms |

The complete stack increased GPU work in this scene. It still exceeded 60 FPS on average by a wide margin, but the flight tail crossed the 16.67 ms display budget. The main-loop CPU averages were 1.90/2.44 ms base and 2.39/3.06 ms full-stack. Frame intervals, CPU work and GPU timestamps are different sample sets; their difference cannot identify presentation wait. Base had an isolated 68.76 ms static maximum, so a single max or a single pair is insufficient to rank settings.

Each pass captured its full 25-second static and 16-second flight windows, no new user input during sampling, identical renderer and monitor geometry, matching start/finish camera checks and a clean client exit. macOS foreground ownership was not independently sampled. Xcode, xcodebuild, Cargo and rustc were absent at preflight. This was a normal macOS desktop with background system services and about 2.5–2.7 GiB of swap in use at sample boundaries, not a fresh-boot lab result. No thermal warning was reported at the sampled boundaries. The pack run had 160 CEM diagnostics; loading the full stack does not establish visual parity.

Commands, executed under the shared `minecraft` lease:

- Ticket 62: `python3 outputs/horizon-runtime/run-idle-baseline-f42.py` completed the base case, then stopped before starting the pack case because available storage dropped below 4 GiB.
- Ticket 63: verified the isolated Rust 1.99.1 compiler, removed the obsolete task-owned Rust 1.95.0 compiler cache (~525 MiB), then `python3 outputs/horizon-runtime/run-idle-baseline-f42.py --packs-after-base` revalidated the existing base output and completed the pack case, exit 0.

Raw samples, process snapshots and screenshots are in `outputs/horizon-runtime/tests/f42-base-idle-uncapped-r1/` and `outputs/horizon-runtime/tests/f42-packs-idle-uncapped-r1/`. Queue logs are in `outputs/horizon-runtime/idle-baseline-f42-2026-11-04.log` and `outputs/horizon-runtime/idle-baseline-f42-resume-2026-11-04.log`. The Java instance and original pack files were not edited.

## Capped presentation comparison

Ticket 66 used `python3 tools/horizon-offline-test.py --runtime nightly-2026-11-03-f42ef42 --case packs --label f42-presentation-ab-r1 --migration outputs/horizon-converter/2026-11-04-Tanush-f42-v3 --native-options-candidate outputs/horizon-converter/2026-11-04-Tanush-f42-v3/native-settings-candidate.json --scene cow --fps-cap 60 --warmup 15 --seconds 20 --presentation-ab`. The same warmed full-stack session completed four stationary 20-second windows in Immediate/Fifo/Fifo/Immediate order. Each reported approximately 60.00 FPS. Immediate gave 57.55/57.82 FPS 1% lows and 17.30/17.19 ms p99. FIFO gave 57.68/58.10 FPS 1% lows and 17.21/17.17 ms p99. Both modes fit within the same narrow frame-time range. Keep the existing Immediate setting for the shader comparison. This run did not measure flight, monitor delivery, tearing or input latency.

Result and per-window live mode, pack order, input and camera readback are in `outputs/horizon-runtime/tests/f42-presentation-ab-r1/result.json`. Client and queue command exited 0.
