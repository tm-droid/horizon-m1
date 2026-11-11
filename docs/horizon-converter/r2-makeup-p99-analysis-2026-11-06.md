# r2 MakeUp static p99: which patch, and how to bisect (2026-11-06)

Read-only analysis. Nothing built, run or queued. Data: `outputs/horizon-runtime/tests/f42-m1-makeup-*-u6ab/result.json`,
`m1-performance-matrix-u6ab.json`. r2 tree: `m1-performance-r2/candidate-source` (paths below are relative to it).
Control source = `launcher-data/native/stage` + cloud-prep + shadow-scratch (diffs against `stage` also show those two; ignore them).

## 1. Outlier or consistent?

Run order: C9 K10 K11 C12 K13 C14 C15 K16 (C = control, K = r2). Consecutive runs form the 4 pairs. Static frame-interval metrics (ms):

| Pair | p99 C | p99 K | delta p99 | p95 C / K | p50 C / K | max C / K | GPU avg delta | GPU p99 delta |
|---|---|---|---|---|---|---|---|---|
| 1 (C9,K10) | 32.82 | 38.25 | +5.43 | 29.8 / 33.9 | 22.46 / 22.21 | 65.9 / 50.6 | +0.26 | -0.43 |
| 2 (K11,C12) | 33.91 | 37.89 | +3.97 | 28.3 / 31.9 | 22.21 / 22.71 | 175.2 / 42.7 | +1.04 | -0.77 |
| 3 (K13,C14) | 33.09 | 36.05 | +2.96 | 30.2 / 30.9 | 22.18 / 22.16 | 47.5 / 40.6 | +0.09 | -0.85 |
| 4 (C15,K16) | 34.08 | 36.03 | +1.95 | 31.0 / 30.0 | 21.66 / 22.69 | 247.4 / 48.3 | +0.68 | +0.33 |

- Verdict: consistent sign (4/4 positive), not one outlier, but the reported CI [+1.95,+5.43] is just min..max of 4 deltas (bootstrap of n=4). Sign test p=0.125 two-sided.
- Magnitude decays with time: +5.43, +3.97, +2.96, +1.95 (candidate p99 38.25 to 36.03, control flat 32.8-34.1). Either warm-up/thermal drift or the effect is smaller than quoted. Interleaving did not randomise this away.
- Tail shape: p50 equal; K p95 higher in 3/4; GPU p99 not worse in 3/4 (GPU avg +0.09..+1.04, 4/4 >= 0 but small). So the extra tail is not GPU-pass cost; it looks like CPU/scheduling or present pacing. Control has rare giant stalls (max 175 and 247 ms in pairs 2, 4); K has none (max <= 50 ms). K's tail is a fatter mid-tail (1-5% of frames about +4 ms), not rare spikes.
- Periodicity: not checkable. Static `measurement` has no per-frame series (`frame_ms`/`cpu_ms`/`gpu_ms` exist only under `flight`, which shows no effect). `slow_phases_avg_ms.render` is higher for K in 3/4 pairs (24.8/18.2, 18.2/14.2, 15.9/18.7, 18.5/15.6 as K/C), consistent with render-thread waits, not proof.
- Entities: `dynamic_entities_drawn` and `static_entities_drawn` are 0 in the static MakeUp result.

## 2. Patch-by-patch (does it run on MakeUp static, can it add GPU time or CPU stalls?)

| Patch | Runs on MakeUp static? | Verdict |
|---|---|---|
| QoS: `horizon-threads/src/lib.rs:153` `pool_helper_current` (USER_INITIATED, relative -15; gated by `put_helpers_behind()`, called at `horizon-client/src/game.rs:20762`), `jobs.rs:222` (every Pool worker), `lan/chunks.rs:393`, `lod.rs:1174,1262,1277` (`far_terrain_current` = UTILITY, not gated) + `step_behind` at `lod.rs:1020-1025` | Threads exist always; they only matter when they do work. Workers are idle in a static scene except tick-driven jobs (`tick` slow phase 2-3 ms). Control helpers inherited the render thread's USER_INTERACTIVE; r2 helpers run below it and far threads on E-cores. | Top suspect. It is the only change that affects scheduling of every thread, and it matches the signature (tail only, p50 and GPU p99 unchanged). Mechanism unproven: it needs the render thread to wait on a demoted helper (fork-join or upload wait); that is why a QoS-only build is needed. |
| sprite-compress: `assets.rs:120-188` `SpritePixels::pack` (lz4, own thread), `game.rs:14882` `pixels.pack()` per frame, `game.rs:19828,19862` `.get()` | Per frame: one atomic swap. Compress: once, after first render (2303 layers x 64 px = ~38 MB, tens of ms), 20+ s before the bench window. `.get()` decompress only when a renderer is rebuilt (`game.rs:19573`, `game/packs.rs:543`), not in the window. | Low. One-shot, and it frees memory (should help). Not periodic. |
| emissive-bsearch: `terrain.wgsl:393-410`, `native_emissive.rs` `table_cached` (`game.rs:15106`), `gfx.rs:6469` debug_assert only | Vertex-stage loop runs in every terrain vertex, MakeUp included. `table_cached` cuts per-frame CPU. | Low-medium. Shader-off GPU -1.3 ms shows the shader change is a win. For GPU +0.47 to come from it, Metal codegen for the 8-step loop would have to be worse inside the MakeUp world pass; no evidence. Cannot produce a CPU tail. |
| pass-merge: `pack_post.rs:3074-3145` (`draw_entities`, `run_lengths`, `Pass::merges`) | Executes per call, but only programs with `d.pack` draws are active. Entity draws are 0 in this scene, so `active` is empty. Cost when empty: one scan of the programs and 2 small Vecs. | Very low. Entity programs only, and nothing is drawn. |
| shadow-dedup: `gfx.rs:1049` and `gfx.rs:6711-6717` (Fx hasher, `seen.clear/extend`) | Only if the pack has a shadow camera. Per frame, CPU. | Very low. Fx is cheaper than SipHash; no GPU effect; no stall. |

## 3. Bisect (<= 3 builds)

`build-m1-performance-r2.py` `PERF_MODS` (line 26) order: qos-backport, jobpool-qos, sprite-compress, emissive-bsearch, pass-merge, shadow-dedup. Each build is ~9 min on `--profile fast` (r2 took 516 s); the control is reused.

1. B1 = r2 minus QoS (drop `qos-backport-f42` and `jobpool-qos-f42`). Regression gone means QoS is the cause. Regression still there means it is in sprite/emissive/merge/dedup.
2. B2 = control + QoS only. Confirms the sufficient cause (if B1 was clean), or, if B1 still regressed, use B2 = r2 minus emissive-bsearch.
3. B3 = only if still ambiguous. After B1 clean + B2 reproduced, split QoS: `qos-backport` only (far-terrain threads, `lod.rs`) vs `jobpool-qos` (pool workers). If B1 still regressed and B2 (r2 minus emissive) is clean, emissive is the cause; if not, B3 = r2 minus sprite-compress.

Bench: MakeUp-UltraFast static (+ flight as a sanity check), same runner, thermal gate and 60 s cooldown. Do 6 rounds of a 3-arm rotation (C, K=r2, Bx; a Latin-square order such as C K B / K B C / B C K / ... ) instead of pairs against stale r2 data, because the r2 effect decays over time (section 1). That is 18 runs, about 70 min.

Pairs needed: paired p99 delta SD is ~1.4 ms (control p99 SD ~0.6, K ~1.1). To tell Bx from 0 when the real effect is 3.5 ms, 4 pairs is enough. To detect a residual of ~1.75 ms at 80% power you need about 6 pairs. Use 6, and report median plus the sign count, not a bootstrap CI of 4.

Capture first: make the runner save the static per-frame `frame_ms` series (it only does so for flight). That is the only way to see periodic spikes and to compute tail fractions (p95-p99 band).
