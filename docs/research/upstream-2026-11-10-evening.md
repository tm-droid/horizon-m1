# Upstream check 2026-11-10 evening (base fdc87ae, hooks 411)

## Nightly status
- Release tag `nightly` still = fdc87ae (published 2026-11-08 15:14Z). No newer nightly. Main is 4373 commits ahead (tip 8933e8c2, 2026-11-10 10:25Z, governance merge). Launcher releases only to 0.2.58 (11-09).
- Newer main commits are NOT in any nightly: need own build from main to get them.

## Main commits after fdc87ae (relevant)
- 3d5216e7 (11-07) perf(render): terrain interpolants 5 locations not 12
- 702b0895 (11-07) Draw vanilla terrain flat on Metal at any section count
- bec6ac64 (11-07) Fix legacy Intel Metal startup and terrain rendering
- 3004b649 (11-07) Fix speckled players with Improved Transparency on Metal (issue 12059)
- e1434f2e (11-07) perf(game): reduce dimension swap overhead, cache raycast chunk lookups
- 5ec521bb (11-07) Shader packs: dynamic lights as uniforms, horizonTier
- d6f88d24 (11-08) GPU Culling Auto mode (not offered on Metal/macOS)
- 33c96ac1 (11-08) padded mesh bounds for CPU terrain occlusion
- 1f11377f (11-08) perf: share entity models across startup loaders
- 2d708ace/3fd4fed9/02cc303c/603ff703/21aabee4 Far terrain: no render-thread lock waits, kept tiles
- 085e9f60 (11-08) Keep shader terrain attributes tied to source block
- cca1842d (11-08) Shader packs: rain/snow never write depth
- 076e9533 (11-09) Scheduled ticks: chunk queue gives back memory once drained
- 998b82e7 (11-09) Renderer: fall back when adapter cannot present
- d84e8fa4, b4b59960, 4a701935 (11-09) Shader pack GLSL fixes (varyings, shadow program)
- b2ba0cb3 (11-09) HDR Lighting greyed under shader pack
- Many perf(mobs/spawning/machines/lan/audio/particles) server-side commits 11-09.
- NOT found by title: e0e48c36 terrain-twice fix, CEM rot_y/rot_x unit fix, fullbright+shader fix, dimension-change shader stall fix, HUD GPU cost fix. (Title grep only; bodies not read.)

## Issues
- 12448 OPEN: shader packs drop compact terrain layout -> section memory 5.9 GB at RD 64 (vs ~3 GB), Apple silicon, wait_frames stalls. Directly relevant to 8 GB.
- 14015 OPEN: macOS camera jitter at >60 Hz (M2 Metal, version fdc87ae).
- 12494 OPEN: perf GUI / iGPU unified memory request.
- 11294 closed 11-07: M4 worker pool crowds 4 P-cores; leaf faces dominate GPU.
- 11577 closed 11-07: Metal solid terrain pays HDR lighting cost (~15% GPU).
- 7958 closed 11-03: switching shader packs at runtime made CPU frame 7x slower.
- 5960 closed: MakeUp gl_FogFragCoord unknown.
- 7986 closed: sheep parts detached with Fresh Animations. 8251 open: slow resource pack load.
- 13007 open: stalls with many falling blocks. 14503 open: Assets::load leaks ~11 MB BlockRegistry per call (tests).
- 3823 open: fullbright and multiplayer compliance (policy, not shader fix).
- No issue found for rot_y/rot_x units or dimension-change stall.

## horizon-mods
- minimap_worldmap_waypoints_reworked (daniliammo): 0.4.1, 2026-11-09 (commit a4b09b49). Toml has no pin text; revision pin NOT verified (native/minimap/compatibility.json shows hooks 359, eaa7da4f, but that is the separate `minimap` mod).
- waypoints (Nirokx): 1.1.0, 2026-11-05, "Pinned to Horizon c9d474d".
- worldmap 0.7.1 (11-09), dynamiclights 1.0.0 (11-09, new), dynamic_fps_for_rust 0.1.0 (11-04, caps 30 hovered/10 unfocused/1 minimised/20 idle/30 battery), fps_overlay.
- No entity-culling or memory mod found in index by name.

## Settings docs (docs/graphics.md)
- Settings in horizon-graphics.txt beside options.txt. Worker threads, graphics API, translucent batching apply at next start.
- Battery mode: 60 fps cap in world, half workers. Entity/leaf/cave culling, chunk update and upload budgets per frame, frame pacing (Efficient default), present mode.
- GPU Culling and translucent batching unavailable on Metal/macOS.
- Env: HORIZON_MINECRAFT_DIR, HORIZON_SERVER_JAR, HORIZON_HDR_OUTPUT, HORIZON_HDR_FRAME=float, HORIZON_HDR_DEBUG. No frames-in-flight env found. docs/profiling.md, docs/benchmark.md exist.
