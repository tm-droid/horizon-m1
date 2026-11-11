# Horizon runtime overrides matrix, 2026-11-06

Control build `native-f42-m1-control-09391c2a8210`, M1 Air 8 GB, on-screen 1280x720, RD 12/sim 8, uncapped (fps cap 260), 52 packs ("packs") and MakeUp ("makeup"), cow scene, 15 s warmup, 20 s static, 16 s flight. 39 of 40 budgeted game runs, all through the device-testing queue. Tools: `tools/horizon-offline-test-ovr.py` (adds `--env`, `--graphics-line`), `outputs/horizon-runtime/run-overrides-matrix.py`, `analyze-overrides.py`, raw data `outputs/horizon-runtime/overrides-matrix-{s2p,s2m,c1p,c1m,t1m}.json`.

## Result in one line
No override produced a confirmed gain. Screening hints (ub2048 on packs, GPU_CULL=all on makeup 1% lows) did not survive 4 paired rounds. Recommended daily override set: none (keep defaults).

## Knob inventory (source: candidate-source crates, graphics.rs parse(), env::var sites)

Harness / daily defaults: workers:0 (auto = cores-1 = 7), framePacing:efficient, presentMode auto (Immediate with vsync off), uploadBudgetKiB 0 / chunkUpdates 0 (auto time-sliced 2 ms, 6 ms while terrain arrives), maxFps 260 harness / 60 daily options.txt, enableVsync false, RD 12 / sim 8, particles 0, cloudRange 64, mipmapLevels 4, entityShadows true, resolutionScale 100, taa/fxaa/hdr off, batteryMode off, caveCulling true, entityCulling off, leafCulling off, shadowCache false, batchTranslucent true. Daily $R/launcher-data/settings.json has no perf keys.

| knob | where | default | class |
|---|---|---|---|
| HORIZON_WORKER_THREADS=N | horizon-threads lib.rs:25 | cores (8) | NEUTRAL, benched |
| workers:N (graphics file) | graphics.rs:786 | 0 = cores-1 | NEUTRAL (overlaps env), harness --workers |
| HORIZON_JOB_THREADS=N | threads/jobs.rs:180 | worker_count-1 | NEUTRAL, not benched (overlaps env) |
| uploadBudgetKiB / chunkUpdates | graphics.rs:768-769, game.rs:16242 | 0 auto | NEUTRAL, benched (ub2048) |
| HORIZON_GPU_CULL=0/all/shader | gfx.rs:3937 | on, Metal min 1600 sections | NEUTRAL (0 only slower); all benched |
| HORIZON_FLAT_DRAWS=0/1 | gfx/flat.rs:157 | flat on Metal already | N/A (already default) |
| HORIZON_SUBMIT_THREAD | gfx/submit.rs:19 | off on macOS | N/A (source says Metal stalls 10-50 % FPS) |
| framePacing:precise | graphics.rs:773 | efficient | N/A at uncapped (limiter skipped at 260) |
| presentMode auto/fifo/mailbox/immediate | graphics.rs:771 | auto = Immediate | N/A (already Immediate; Fifo = vsync) |
| desired_maximum_frame_latency | gfx.rs:2158 hardcoded 2 | 2 | N/A no knob |
| renderClouds=false under MakeUp (--disable-vanilla-clouds) | options.txt | true | NEUTRAL for MakeUp V_CLOUDS=2 only |
| leafCulling solid/solidaggressive | graphics.rs:520 | off | N/A: falls back Off when packs may replace leaf models (52-pack stack) |
| entityCulling async | graphics.rs:94 | off | NEUTRAL, scene-dependent; cow scene has ~no entities, not benched |
| blockEntityCache* | graphics.rs:559 | signs only | NEUTRAL, no block entities in scene, not benched |
| caveCulling | graphics.rs | true | already on |
| batchTranslucent | graphics.rs:636 | true | already on |
| HORIZON_MEMORY_LIMIT_MB/HARD_MB | ram_limit.rs | unset | LOOKS-CHANGING when it triggers (drops RD) |
| shadowCache:true | graphics.rs:627 | false | LOOKS-CHANGING (stale shadow on key hit) |
| resolutionScale, upscaling, fxaa/taa, hdr, frameGeneration | graphics.rs | 100/native/off | LOOKS-CHANGING |
| sky / fog / weather / animatedTextures / ditherCutoutMips / textureBudgetMiB | graphics.rs | on/off | LOOKS-CHANGING |
| lodDistance / farDetail | graphics.rs | 0 / Full | LOOKS-CHANGING |
| particles, cloudRange, mipmapLevels, biomeBlendRadius, entityDistanceScaling, entityShadows, weatherRadius | options.txt | user values | LOOKS-CHANGING |
| shader pack options (AOSTEPS, SHADOW_BLUR, ...) | sidecar .zip.txt | pack | LOOKS-CHANGING, out of scope |
| chunkSectionFadeInTime | settings.rs:446 | 0.75 | LOOKS-CHANGING (pop-in) |
| HORIZON_NO_AUDIO, TELEMETRY_*, NET_*, SPLIT_*, DEBUG/TEST/FIXTURE vars | various | unset | N/A (dev/test/server) |

## Screening (2 knob runs each, interleaved with shared base runs; median paired delta vs adjacent base)

Packs (flight is the point), n=2 pairs: 
| knob | flight avg FPS | flight 1% low | flight p99 ms | settle s | static avg FPS |
|---|---|---|---|---|---|
| uploadBudgetKiB:2048 | +2.0 | +3.6 | -0.5 | +1.4 | +5.7 |
| HORIZON_WORKER_THREADS=6 | -3.1 | -0.6 | -0.7 | +1.8 | -2.2 |

Makeup, n=2 pairs:
| knob | static avg | static 1% low | flight avg | flight 1% low | flight p99 ms |
|---|---|---|---|---|---|
| HORIZON_GPU_CULL=all | +0.9 | +5.7 | +0.1 | +7.1 | -5.6 |
| renderClouds=false (--disable-vanilla-clouds) | +0.6 | +2.7 | -0.2 | +2.6 | +0.1 |
| HORIZON_WORKER_THREADS=6 | -0.3 | -0.1 | -1.2 | -0.2 | -0.3 |

Not benched (budget or N/A): HORIZON_WORKER_THREADS=4, HORIZON_JOB_THREADS, entityCulling:async, blockEntityCache (cow scene has no entities or block entities), chunkUpdates (same mechanism as uploadBudgetKiB).

## Confirmation (4 rounds, arm order rotated per round; delta vs same-round base; median [bootstrap 95% CI, n=4])

Makeup (base medians: static 43.8 FPS / 1% low 27.0 / p99 34.2 ms; flight 36.0 / 19.1 / 42.3 ms; settle 12.1 s):
| arm | static avg FPS | static 1% low | flight avg FPS | flight 1% low | flight p99 ms | settle s |
|---|---|---|---|---|---|---|
| HORIZON_GPU_CULL=all | +2.2 [-0.6, 2.7] | -2.3 [-9.0, 3.2] | +0.8 [-1.3, 1.7] | -0.3 [-6.4, 12.3] | +1.6 [-3.9, 13.2] | -1.7 [-18, 8.6] |
| combo (GPU_CULL=all + renderClouds=false + uploadBudgetKiB:2048) | +0.3 [-0.7, 1.4] | +0.1 [-3.6, 2.3] | +0.4 [-1.0, 0.8] | +3.3 [-5.2, 12.0] | -1.2 [-8.8, 3.7] | -3.9 [-22, 20] |

Packs (base medians: static 157.4 FPS; flight 134.3 FPS / 1% low 41.2 / p99 22.3 ms; settle 7.4 s):
| arm | static avg | flight avg | flight 1% low | flight p99 ms | settle s |
|---|---|---|---|---|---|
| uploadBudgetKiB:2048 | -6.2 [-16.3, 1.5] | -0.1 [-2.4, 1.3] | +0.7 [-3.4, 3.2] | +0.1 [-0.5, 0.8] | -0.9 [-3.2, 3.2] |

All CIs include 0. The screening gains on packs 1% low (+3.6) and makeup 1% low (+7.1) reversed or vanished: that is the noise level of 1% lows (single-pair swings of 5-12 FPS). Only HORIZON_GPU_CULL=all static avg (+2.2, 3 of 4 rounds positive, about +5%) is suggestive; the lower bound is -0.6, so it is not confirmed and would need roughly 8+ rounds.

Visual check: scene.png mean abs channel diff vs base is inside base-vs-base noise for every arm (packs 0.5-0.8 vs 0.2-0.8; makeup 6.0-8.0 vs 6.8-9.3; makeup scene changes between runs because the volumetric clouds animate). No visible change from any neutral override.

## Recommended daily override set
None. Defaults stay: no HORIZON_* env vars, `workers:0`, `uploadBudgetKiB` unset, `framePacing:efficient`. Optional, unproven: `HORIZON_GPU_CULL=all` (MakeUp static +2 FPS median, CI crosses 0, no downside seen in 1% low beyond noise). Do not set HORIZON_WORKER_THREADS (no gain; previous 3-worker trial hurt streaming) or uploadBudgetKiB (settle was slower in screening, 512 KiB earlier doubled it).

## Optional trade-offs (LOOKS-CHANGING or risk; not in the daily set)
One pair each, makeup:
| knob | static avg | static 1% low | flight avg | flight 1% low | flight p99 ms | visual |
|---|---|---|---|---|---|---|
| shadowCache:true | 43.9 vs 46.3 | 17.1 vs 28.2 | 37.0 vs 36.9 | 20.3 vs 18.7 | 44.1 vs 49.5 | not measured against noise; source says a stale key can show old shadows |

shadowCache showed no gain (static worse in this single pair); not recommended.
Other looks-changing options (resolutionScale, shadow/cloud distances, shader options, particles, lodDistance, HORIZON_MEMORY_LIMIT_MB) were not run; budget went to confirming neutral knobs.

## Caveats
Swap 2.5-6 GB during every run, other agents active on the machine between runs, 1280x720 not 2560x1440. First two screen attempts (s1p, s1m) failed at the safety gate (python without Quartz) and used no game runs.
