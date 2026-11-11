# Horizon settings and preset audit

Audited on November 5 against pinned f42 `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`, the captured Java settings, and the November 4 full-stack on-screen results. This is a source and recorded-state audit. Runtime A/B acceptance remains a separate step.

The user clarified that the old instance's settings were optimization attempts with no established benefit. Inherited values are experimental evidence, not preferred defaults or validated winners. “Keep” below means the audit currently lacks a justified replacement. Each setting remains open to comparison against native defaults, with any visual or gameplay difference recorded.

## What actually wins

1. Horizon loads ordinary options from the profile's `options.txt`. It separately loads `horizon-graphics.txt`, Extras, controller and mod settings from that profile. Missing ordinary values receive `Settings::default` values.
2. The test harness starts with the captured source-derived candidate, then explicitly sets the requested frame cap, VSync off, simulation distance 8, idle policy and ordered resource packs. It writes a separate graphics file with native resolution, worker and pacing choices.
3. The command-line `--render-distance 12` overrides the loaded render distance before game creation. A manual options-file edit alone cannot change that test.
4. The optional built-in `--benchmark` path forces Unlimited and VSync off in memory. Our control-socket tests use their recorded explicit options instead.
5. Selecting a preset applies a group of fields immediately. Its name is not evidence of the effective values after later edits. The ordinary Minecraft graphics preset and Horizon graphics preset are distinct controls.
6. A shader's `.zip.txt` sidecar overrides that pack's compile-time defaults. Its shadow range, cloud algorithm and render targets can differ from the ordinary world options. Resource packs also affect whether model-dependent culling can run.

Sources are [settings loading](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/settings.rs#L330), [CLI override and benchmark path](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game.rs#L20535), and local `tools/horizon-offline-test.py`. Recorded effective state is in `outputs/horizon-runtime/tests/f42-packs-shader-onscreen-uncapped-r1/result.json`.

## Current values, costs and actions

Priority 1 means a focused experiment can target unnecessary work while preserving the requested view. Priority 2 needs an explicit appearance or gameplay comparison. Keep means the audit found no reason to change it.

| Area | Recorded effective value and relevant default | Action and acceptance |
| --- | --- | --- |
| Terrain distance | 12 chunks, 637 loaded columns. Engine default 12. Source Java also 12. | Keep. No hidden 1,000-chunk terrain setting. A smaller radius changes visible terrain and the flight workload. |
| Simulation | 8 chunks. Engine missing-key default 12. Source Java 8. | Keep. Reducing to 6 can reduce server work while changing mob, farm and redstone activity. Treat as gameplay tradeoff. |
| Far terrain / BlueMap | Requested and effective LOD 0, no active or cached tiles, BlueMap radius 0. | Keep off for this baseline. Apple integrated GPUs bypass Horizon's non-Apple integrated 128-chunk LOD cap, so future presets/imports need explicit inspection. |
| Cloud range | 64 chunks, a 1,024-block radius. Missing-key default 128. Source Java 64. | Priority 2 in shader-off play. Reducing it can change the visible sky. It also sets the projection far-plane floor, so hold it constant when testing cloud-generation overhead. |
| Native clouds under MakeUp | Ordinary clouds on. MakeUp with existing volumetric option declares `clouds=off`. Native mesh preparation/upload occurs before the Iris draw decision. | Priority 1. Test only MakeUp with ordinary `renderClouds=false`, retaining cloudRange64 and the exact shader sidecar. Confirm the volumetric sky, water and horizon match. Test CPU/flight tails. Disabling clouds globally would change other looks. |
| Workers | `workers:0` means automatic, recorded as seven shared worker threads on this M1. | Keep auto initially. Previous manual three-worker trial hurt streaming. This setting sizes a shared client/server streaming pool. It is not seven independent pools. |
| Mesh uploads | `chunkUpdates:0`, `uploadBudgetKiB:0`. Zero selects automatic scheduling. Bursts use a 2 ms time allowance, increased to 6 ms while terrain arrives, with a small-batch fast path up to eight uploads. | Priority 1. Compare a modest explicit budget against auto on the same flight. Check p99/1% lows, pending uploads, visible pop-in and final settle time. An explicit count/byte budget replaces the auto time branch and can be worse. |
| Texture memory | `textureBudgetMiB:0` selects 256 MiB for the largest sprite array's top mip. | Keep. Zero is a finite default. Lowering this budget can silently resample larger textures. This is a fidelity control as well as a memory limit. |
| Native resolution | Native 100%, 2560×1440 renderer surface. FXAA, TAA, upscaling and frame generation off. | Keep for comparable quality. A smaller world scale saves pixel work but changes the image. Logical window size alone does not establish actual rendering resolution. |
| Mipmaps | 4, matching source Java and engine default. | Keep. Dropping levels can worsen distant shimmer and texture sampling. It is not an appearance-neutral FPS fix. |
| Cave culling | On by default and in the profile. Suppressed when the camera is inside an opaque solid block. | Keep. Source already avoids drawing sections hidden through closed terrain, subject to its camera guard. |
| Entity / leaf culling | Both off. Model-dependent checks require vanilla-only models across local and server packs. The full 52-pack stack fails that conservative eligibility gate. | Keep for this stack. Enabling the selector alone cannot establish a working optimization. Leaf modes can also remove visible foliage faces. |
| Block-entity caches | Sign text cache on. Chest, banner, bell, shulker, pot and copper statue caches off. | Priority 1 only in a relevant populated scene after source eligibility review. A grassland cow benchmark cannot establish their benefit or animated-state correctness. |
| Shadow cache | Off by default and in the profile. It checks view, sun/scene/pack state and avoids reuse with shadow-casting entities or custom images. | Priority 2. Moving-camera or animated scenes can defeat reuse. Require unchanged moving shadows and time-of-day behavior before adoption. |
| Shader shadow budgets | MakeUp 840² over105 blocks, Miniature1024² over128, Complementary2048² over192. | Priority 2. No extreme 1,000-block shadow radius was active. Lower resolution or range changes shadow detail or coverage. Complementary's radius already matches12×16 terrain blocks. |
| Shader cloud quality | MakeUp sidecar `V_CLOUDS=2` versus pack default1. The higher mode evolves volumetric cloud shape with extra per-step work. | Priority 2 after redundant native clouds. A2→1 trial preserves moving volumetric clouds but changes their evolution. Compare the sky over time. |
| Fog, sky, weather, animation | All on. Particle value0 means all particles. Weather radius10, source Java10. | Keep. These are visible features. Turning fog off can also expose distant boundaries and is not a general free performance fix. |
| Entities and biome blending | Entity distance1.0, shadows on, biome blend2, fancy cutout leaves. Source Java matches. | Keep unless the user accepts a specific visual tradeoff. Lower entity distance hides things sooner. |
| Unlimited / VSync | Latest batch uses260, VSync false, actual Immediate mode. Engine default is120 with VSync true. | User's current throughput baseline. Source skips the limiter at260 in both pacing modes. Capped60 is a separate smoothness experiment, not maximum throughput. |
| Pacing and battery | Efficient pacing, battery mode off, inactivity throttling only when minimized. | Keep. Efficient versus Precise has no limiter work at Unlimited. Window minimization can still throttle. Foreground ownership was not independently sampled in prior runs. |
| Graphics backend | Auto, actual Metal on Apple M1. | Keep. The source offers only Auto on macOS. Selecting a nonexistent alternative is not an optimization. |
| Java memory | Instance max3072 MiB, min1024 MiB. Current global max3584 is overridden by the instance. | Java-specific evidence only. Horizon's native client has no JVM heap setting. Lower native texture/geometry budgets must be evaluated on their actual allocation and fidelity behavior. |

Sources are [defaults and presets](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/graphics.rs#L642), [LOD and model gates](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/graphics.rs#L476), [sprite budget](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/sprites.rs#L101), [upload scheduler](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game.rs#L16728), [cloud radius](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/clouds.rs#L61), [cloud preparation](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/gfx.rs#L7331), and [shadow cache guards](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/gfx/pack_post.rs#L3712).

## Presets can replace several deliberate choices

Horizon presets apply the following groups. Every non-Custom preset also enables cave culling, animated textures, sky, fog and weather, and resets upload limits to automatic. Selecting Custom leaves the existing fields as they are.

| Horizon preset | Render / simulation | Clouds / particles | Mipmaps / entity distance | Other visible changes |
| --- | --- | --- | --- | --- |
| Performance | 8 / 6 | off / minimal | 0 / 0.5 | Shadows off, biome blend0, opaque cutout leaves, weather radius3 |
| Balanced | 12 / 8 | fast / decreased | 2 / 0.75 | Shadows on, biome blend1, fancy leaves, weather radius5 |
| Quality | 16 / 12 | fancy / all | 4 / 1.0 | Shadows on, biome blend2, fancy leaves, weather radius10 |
| Ultra | 24 / 12 | fancy / all | 4 / 1.5 | Shadows on, biome blend3, fancy leaves, weather radius10 |

The ordinary graphics preset has a different mapping. Fast selects8/6 distance, cloud range32, mipmaps2, reduced entity distance and disables smooth lighting/shadows. Fancy selects16/12 and cloud range64. Fabulous selects32/12 and cloud range128, entity distance1.25 and improved transparency. Thus clicking Fabulous could grow the measured12-chunk view to32 and cloud range to128. The recorded profile is Custom and has explicit12/8 values. Keep custom values while evaluating individual settings. [Ordinary preset implementation](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/options_ui.rs#L1143)

## First acceptance batch

1. MakeUp ordinary cloud preparation on versus off, with unchanged volumetric shader options, cloud range64, distances, full pack order and native resolution. Compare the sky/water view and an equal flight. This is the strongest source-backed duplicate-work candidate.
2. Shader-off automatic upload scheduling versus one modest budget. Preserve full initial terrain, record bytes/pending uploads and show endpoint plus settled captures so delayed loading cannot masquerade as a win.
3. Pursue shader cloud animation, shadow range or simulation reductions only with the specific appearance/gameplay difference recorded.

The audit does not establish an FPS gain for any candidate. The prior uncapped full-stack flight uploaded approximately124 MiB of terrain meshes, which supports investigating the upload path without identifying it as the sole cause of slow frames. A clean same-setting control remains necessary because ordinary desktop workload and swap differed between previous runs.

## November 5 device screening

Ticket 71 ran `python3 outputs/horizon-runtime/run-settings-audit-f42.py`, exit 0. Four fresh isolated profiles used the same official f42 client, complete ordered 52-pack stack, native 2560×1440, Unlimited with VSync off, 12/8 distances, automatic workers, fixed cow view and scripted flight. The runner checked active settings, camera, input, pack order, shader hashes and full sample durations. The upload setting is proven through the parsed profile file and source loading path. It lacks an independent live renderer query. System snapshots bracket the static sample, so flight-only background activity may be missed.

| Experiment | Static avg / 1% low FPS | Flight avg / 1% low FPS | Flight p99 | Post-flight settle |
| --- | ---: | ---: | ---: | ---: |
| Automatic uploads | 159.0 / 51.7 | 139.3 / 45.7 | 19.3 ms | 4.17 s |
| Upload budget 512 KiB | 161.9 / 53.5 | 140.2 / 44.9 | 21.0 ms | 8.77 s |
| MakeUp native clouds enabled | 42.1 / 19.1 | 35.8 / 18.3 | 46.1 ms | 19.19 s |
| MakeUp native clouds disabled | 44.0 / 23.8 | 35.9 / 22.2 | 42.5 ms | 4.36 s |

Reject the 512 KiB candidate after this screening. Its flight average stayed similar, its tail worsened slightly and recovery took longer. It had fewer resident and drawn sections at the flight endpoint, so it does not establish equal transient geometry. The images are settled captures. Transient pop-in was not visually accepted.

The MakeUp-qualified cloud toggle retained the original ZIP and sidecar, `V_CLOUDS=2`, 64-chunk cloud range and shader programs. The reviewed day captures retain volumetric clouds. Flight CPU mean fell from17.43 to14.62 ms while GPU means stayed near26.7 ms. The improved 1% low is a promising single-pair observation, with different endpoint uploads/recovery. Full visual equivalence and a repeatable FPS gain require further acceptance. Raw records are in `outputs/horizon-runtime/settings-audit-f42-2026-11-05.json` and the referenced profiles.

Ticket 72 tested the author defaults for both inherited MakeUp overrides. Archive `shaders/lib/config.glsl` defines `V_CLOUDS=1` and leaves `IMAGE_SHARPENING` disabled. The explicit `outputs/horizon-runtime/makeup-audited-defaults.txt` was passed through `--shader-options-file` to the normal harness entry point. Native clouds stayed enabled for the same conditions as the original MakeUp control. The unchanged shader ZIP loaded the same six post programs. The sidecar source and staged SHA256 were both `836863a69e057dce9b7784ad26b58e1283f0e979df5f6f1f37b67c34bf7b750b`.

This run completed at44.38/22.78 FPS static average/1% low and37.26/22.68 in flight, with38.98 ms flight p99. The source control was42.09/19.13 static and35.81/18.31 flight. The change combines two options, so individual costs are unresolved. The inspected image has volumetric clouds and softer texture edges. Default clouds retain movement but stop evolving their shapes, which is a visual difference. Treat it as a separate candidate for the user's later appearance choice. Neither shader-default changes nor the cloud suppression were applied to the original shader files. Raw result is `outputs/horizon-runtime/tests/f42-makeup-default-options-audit-r1/result.json`.

Executed commands under the shared queue were `python3 outputs/horizon-runtime/run-settings-audit-f42.py` and the normal harness with `--case makeup --scene cow --fps-cap 260 --warmup 15 --seconds 20 --flight --capture-flight-end --shader-options-file outputs/horizon-runtime/makeup-audited-defaults.txt`, explicit f42/v3/native-options paths and the fresh label above. Both exited0. Python compilation, CLI help, seven invalid sidecar input cases and four mocked staging/cloud-guard checks passed. Independent source and implementation reviews found no blocking issues.

## Upstream follow-up

The November 5 check found the same cloud preparation order and automatic upload scheduler in published nightly `6475f62f3c834b7489e1816bf47f47ea5eb2b879` and main `41d5649ed5b676065c2227a597e6e9ea9f370ebb`. Main still applies the same visible preset tradeoffs. This keeps the qualified cloud experiment relevant, with a separate compatibility check needed on an updated client. [Published renderer](https://github.com/horizon-rust/horizon/blob/6475f62f3c834b7489e1816bf47f47ea5eb2b879/crates/horizon-client-render/src/gfx.rs#L7886) · [Main renderer](https://github.com/horizon-rust/horizon/blob/41d5649ed5b676065c2227a597e6e9ea9f370ebb/crates/horizon-client-render/src/gfx.rs#L8383) · [Main scheduler](https://github.com/horizon-rust/horizon/blob/41d5649ed5b676065c2227a597e6e9ea9f370ebb/crates/horizon-client/src/game.rs#L474)
