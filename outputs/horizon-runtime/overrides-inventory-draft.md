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
