# R13: fast bench mode, live A/B in one launch (2026-11-06)

Implements R10 proposal 2 (+ parts of 3/4). Script: `outputs/horizon-runtime/run-live-ab.py`. Written and dry-run only; no launch, no cargo. Paths below are under `outputs/horizon-runtime/m1-performance/candidate-source/crates/horizon-client/src/game/` unless stated.

## Design

One `horizon-client` process. After `wait-ready`, a discarded `bench` warmup and one priming flight each way, blocks run in ABBA order (`A B B A` x cycles). Per block: apply the arm's control commands, `wait-ready`, sleep `--settle` (3 s, discarded), then measure one deterministic `fly` (12 s, `raw`, direction alternates so A and B each get both directions inside an ABBA group). `--scene static` uses `stats reset` / sleep / `stats raw reset` instead.

Analysis unit = ABBA group: `d = mean(B) - mean(A)` over its 4 blocks (cancels linear drift and, with alternating direction, the direction effect). Report per-arm mean/SD, mean of group deltas, SD, t-based 95% CI (n groups - 1 df). Metric = 1000 / mean(frame_ms) from the raw series (falls back to `avg_fps`). Full per-block series saved to `outputs/horizon-runtime/liveab-<tag>-<time>.json`.

Usage: `--preset {cull,section-cull,section-sides,rd,clouds}` or `--a "cmd; cmd" --b "..."`; `--aa` runs A/A; `--cycles N`; `--dry-run` validates inputs, arm syntax and the stats code (synthetic self-test).

Harness reuse: `tools/horizon-offline-test.py` has only `main()` (line 26) and no importable launch function. The script imports it for `ROOT/RUNTIME/SHADERS` and mirrors profile staging (harness 120-200), the launch command (205-212), `ctl` (299-309), and `bring_front` (289) verbatim in behaviour. Drift risk: if the harness staging changes, update `stage_profile`.

## Live-toggleable knobs (confirmed in source)

| command | file:line | live? | note |
|---|---|---|---|
| `gpu-culling on/off` | control.rs:409 -> `set_gpu_culling` crates/horizon-client-render/src/gfx.rs:4499 | yes | |
| `section-cull on/off` | control.rs:380 | yes | |
| `section-sides on/off` | control.rs:399 | yes | |
| `gpu-passes on/off` | control.rs:390 | yes | sets `self.gpu_passes`; keep identical in both arms (script default off for both; `--gpu-passes` on for both) |
| `render-distance N` (2..max) | control.rs:743 | yes | `apply_settings()`; needs chunk (re)load, so `wait-ready` + settle |
| `options-set KEY VALUE` | options.rs:59 | yes | applies at once and rewrites options.txt; `resourcePacks` triggers `reload_packs` (seconds; avoid or lengthen `--settle`) |
| `stats [reset] [raw]` | control.rs:925 | n/a | `raw` adds `frame_ms/cpu_ms/gpu_ms`; summary is built before reset, so `stats raw reset` = read then restart |
| `fly ... raw` | control.rs:949 | n/a | errors if a flight/bench is pending; reply carries the summary and series |
| `bench S` | control.rs:937 | n/a | summary only, no series; used for warmup |
| `HORIZON_GPU_CULL` occlusion mode | env, gfx.rs:3940 (R10) | no | needs a new `occlusion-cull` command (R10 sec. 2) |
| shader pack / binary A vs B | none | no | not covered; use the existing runner |

## Validation plan (do in this order)

1. **A/A** (`--preset cull --aa --cycles 4`, repeat in 3 launches): group deltas must have mean CI containing 0 and |mean diff| < 0.5% of A. If not, toggle-reapply overhead or position/order bias exists; fix before trusting anything.
2. **Positive control** (`--preset rd`, 12 vs 8): expect a large, correctly signed diff (B faster). CI must exclude 0 with 2-3 cycles. Confirms flight FPS responds to render work.
3. **Known effect** (`--preset cull` vs the u9 `daily` vs `daily-cull` result for the same build): live diff should agree in sign and roughly in size. Disagreement means hysteresis (culling state not fully applied) so raise `--settle`.
4. **Order test**: run once with `--a`/`--b` swapped; the diff must flip sign with similar magnitude.
5. Check first-block outliers in the saved JSON: if block 0 differs systematically, raise `--warmup`.

## Expected wall-time saving

Current runner: ~165 s per run (R10), one process per arm sample. 3 ABBA cycles = 6 A + 6 B samples.
- Current: 12 runs x 165 s = ~1980 s (plus 30 s cooldown each = ~2340 s in `run-u9-daily.py`, COOLDOWN=30).
- Live A/B: script estimate 358 s (85 s launch/load + 15 s warmup + 2 priming flights + 12 blocks x ~19 s). About 5.5x less (6.5x vs u9 with cooldown).
- Pairing gain is on top: process-level variance (rho 0.6-0.9 for adjacent processes in R10) is removed because both arms share one process; expected SD of the pair delta falls further. [estimate, A/A pilot decides]
- One launch also means one thermal trajectory, so the u9 gates (AC, idle, thermal) need to hold only once.

## Caveats

- Covers only live-toggleable knobs. Binary A/B (control vs r3), migration changes and shader choice still need the old runner.
- State carry-over: a toggle may leave caches, pipelines or chunk meshes warm for the other arm (hysteresis). ABBA balances first-order carry-over only; step 3 and 4 above check it.
- Flight is partly streaming-bound (R10 sec. 1); a pure shader-cost change may under-respond. The positive control tells how much.
- `render-distance` and `renderClouds` change work per frame and loaded-chunk memory; on 8 GB, watch swap in the saved samples.
- Not run yet: only `--dry-run` was executed (stats self-test and arm parser pass); control JSON key names (`avg_fps`, `frame_ms`, `p99_ms`) come from R10 and `control.rs:925-960`, and are unverified against a live reply.
