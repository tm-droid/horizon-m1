# Combined-stack shader screen — 2026-11-04

Queue53 completed three official f42 offscreen runs with all52 selected file packs, native100% scale,2560×1440 targets and a60FPS cap. Each runner exited0 and recorded a complete full-terrain scene. The parent visually reviewed the full frames and reported no right-half artifact. **These are offscreen screening measurements, not on-screen FPS or full visual parity.**

| Case | Static avg /1% low FPS | Static p99 /max ms | CPU /GPU average ms | Flight avg /1% low FPS |
| --- | --- | --- | --- | --- |
| packs | 60.00 /58.69 | 16.93 /17.17 | 2.89 /8.43 | 59.95 /54.57 |
| makeup | 43.88 /24.16 | 33.81 /59.67 | 16.84 /21.85 | 36.15 /27.56 |
| miniature | 47.47 /19.29 | 30.56 /101.36 | 8.72 /20.35 | 47.99 /15.52 |

Static samples lasted about20seconds and flights about16seconds. GPU averages for both shaders exceed the16.67ms budget for60FPS; that supports prioritizing shader GPU cost in these scenes. CPU cost also rose, especially with MakeUp. CPU/GPU work overlaps, so do not add their means or infer an exclusive bottleneck from these summaries. Neither shader sustained the cap. Miniature's higher average coexisted with worse low-percentile/max-frame results; neither is an accepted stable-FPS winner.

## Activation evidence and its limits

Full console review found no shader preprocessing/translation errors, no `program: skipped`, and no `writes no buffer` message in either f42 run. MakeUp loaded6 composite-style programs (`prepare deferred composite composite1 composite2 final`), terrain/water/sky/sun/moon/hand/weather/entity/particle routes, and a840² shadow map over105blocks. Miniature loaded its final program, terrain/water/sky/cloud/hand/weather/entity routes and a1024² shadow map over128blocks. Its one final program is its observed pipeline, not evidence that it should have MakeUp's six. These logs establish active routes, not correct shading of every material or complete Iris parity.

Two apparent omissions have source explanations in the unchanged installed ZIPs:

- **Miniature entity shadows:** `shaders/shader.h:55` defaults `SHADOW_ENTITY` to0. `shaders/shaders.properties:26–37` then disables ordinary entity/block-entity shadows and enables player shadows. Runtime explicitly reports only the player casting entity shadows. This matches the shader's selected default, not a demonstrated lost native pass. It changes appearance relative to shaders that cast all mob shadows and must remain visible in the comparison.
- **MakeUp clouds:** preserved sidecar sets `V_CLOUDS=2`. `shaders/common/clouds_blocks_fragment.glsl:29–37` writes vanilla cloud buffers only for `V_CLOUDS==0`/unknown dimensions, or the old-Minecraft fallback. Absence of a vanilla cloud draw route is therefore not itself a failure; check the volumetric cloud result produced later in its pipeline. Preserve this option rather than disabling clouds to improve FPS.

MakeUp also reports five malformed `betterendforge::...` block names at block.properties line35. These are mod-specific material references, not evidence that the vanilla test scene failed shader compilation. They remain recorded, and are not a proof that arbitrary modded blocks work.

The f42 loader intentionally rejects individual programs after preprocessing/translation failure; therefore future checks must continue reading all stage diagnostics. [Pinned program load/rejection](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-shaders/src/post.rs#L1033), [separate native-WGSL and Iris loaders](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/docs/shaders.md#L1). Installed ZIP hashes and author sources are in [next batch plan](shader-batch-next.md); those local versioned sources are authoritative for the options above.

## Shared appearance blockers take priority

All three baseline/shader logs include `using the missing texture for minecraft:block/` and `more than96 emissive block overlays: ...deepslate_diamond_ore/3_e.png and later skipped`. These are independent of shader selection and must not be ignored as shader compatibility success. Missing-JPM and native CEM binding issues also remain; fewer shader diagnostics does not resolve them. Investigate these shared pack/rendering limits before expanding the shader list.

## Next small acceptance batch

Use one full-stack disposable world, preserving runtime, pack order, FOV95, cloud range64,12/8 distances and native100%. A short **daylight** view should show a cow/player/block-entity shadow, foliage and cloud motion; verify Miniature's intentional shadow setting separately from missing shadows. A **water/shore** view should inspect reflection/refraction, depth/transparency, hand and underwater transition without changing shader settings. A **night** view with an ore/torch cluster should check emissive masks, dark lighting and the unresolved GammaUtils state. Capture shader-off and each candidate at matched camera/time/weather. Subjective preference can wait for the user.

Retest individual components only when those grouped views reveal a concrete problem. Do not lower resolution, remove effects, silently switch profiles or claim on-screen FPS from these offscreen records. The old Mellow50% streaks are absent in the parent-reviewed new frames, but that does not prove Mellow's CAS scaling bug was fixed.

Evidence: `outputs/horizon-runtime/tests/f42-{packs,makeup,miniature}-full-stack-offscreen-r1/{result.json,console.log}`. This review performed no runtime actions, builds, tests or shader edits.
## Full-resolution on-screen follow-up

Ticket 67 ran `python3 outputs/horizon-runtime/run-shader-followup-f42.py`. The f42 client used the complete ordered 52-pack stack, existing shader ZIPs and sidecars, native 2560×1440, 12/8 distances, auto workers, efficient pacing, Immediate presentation and a 60 FPS cap. The harness used the same NoAI cow view and 128-block flight for each case. It checked live options, camera, input, actual renderer dimensions and duration. Foreground ownership was not independently measured.

| Shader | Static avg / 1% low FPS | Flight avg / 1% low FPS | Static / flight mean GPU time | Acceptance |
| --- | ---: | ---: | ---: | --- |
| Off | 60.0 / 57.6 | 60.0 / 57.8 | 7.5 / 7.8 ms | Completed |
| MakeUp 9.6 | 22.8 / 17.1 | 18.5 / 11.8 | 42.8 / 52.7 ms | Completed, background `xcodebuild` seen |
| Miniature 2.19 | 41.1 / 19.1 | 40.8 / 19.0 | 24.2 / 23.7 ms | Completed |
| Complementary Reimagined r5.9.3 | 10.6 / 7.6 | 8.7 / 6.6 | 94.8 / 115.0 ms | Partial timing, post-flight settle failed |

The reviewed MakeUp and Miniature daylight and water captures, and the Complementary daylight capture, rendered across the full frame. MakeUp visibly retained volumetric clouds and water reflections. Miniature used a simpler sky and water look, and its shader config limits entity shadows to the player. Complementary loaded nine post programs and a 2048² shadow map, with `gbuffers_line` skipped. Its 20-second static and 16-second flight measurements were recorded before it missed the post-flight five-sample quiet terrain gate at 240 seconds. Terrain reached 637 columns but meshing periodically resumed. The client exited 0 and the batch exited 1 as designed. No Complementary post-flight image was accepted.

Each shader exceeded the 16.7 ms GPU budget on average in these cases. The shader-off control is the configuration that met the measured 60 FPS target. Timing here does not establish Java/Iris visual parity, a clean boot workload, or compatibility in every biome or dimension. Evidence is in `outputs/horizon-runtime/shader-followup-f42-r1.json`, the `f42-*-shader-onscreen-r1` profiles, and `shader-followup-f42-2026-11-04.log`.

Ticket 69 repeated only MakeUp with the same shader and sidecar hashes. It called `python3 tools/horizon-offline-test.py --runtime nightly-2026-11-03-f42ef42 --case makeup --label f42-makeup-shader-onscreen-r2 --migration outputs/horizon-converter/2026-11-04-Tanush-f42-v3 --native-options-candidate outputs/horizon-converter/2026-11-04-Tanush-f42-v3/native-settings-candidate.json --scene cow --fps-cap 60 --warmup 15 --seconds 20 --flight` and exited 0. The repeat passed the same review gates. It measured 18.76/10.88 FPS average/1% low static and 16.67/8.93 flight, with GPU means of 50.41/57.37 ms. No `xcodebuild` was present in the sampled top-process lists, and system swap was near 3.8 GiB. The repeat confirms that the sampled background build cannot account for MakeUp missing 60 FPS. Workload and swap differences still limit a controlled ranking. Raw evidence is in the `f42-makeup-shader-onscreen-r2` profile and `makeup-shader-repeat-f42-2026-11-04.log`.

## Uncapped follow-up

Ticket 70 ran `python3 outputs/horizon-runtime/run-shader-followup-f42.py --uncapped --tag uncapped-r1` and exited 0. All four cases completed 20-second stationary and 16-second flight samples with the same f42 client, 52 packs and native 2560×1440. Live readback confirmed Horizon's Unlimited setting, VSync off and Immediate presentation. The screenshot is taken at the flight endpoint, before terrain settlement. Initial terrain, camera, input, duration and pack gates stayed in place.

| Shader | Static avg / 1% low FPS | Flight avg / 1% low FPS | Flight p99 |
| --- | ---: | ---: | ---: |
| Off | 130.40 / 42.54 | 100.01 / 30.38 | 28.03 ms |
| MakeUp 9.6 | 19.68 / 10.65 | 16.87 / 9.21 | 95.35 ms |
| Miniature 2.19 | 38.68 / 16.69 | 41.72 / 19.06 | 49.40 ms |
| Complementary Reimagined r5.9.3 | 8.07 / 5.56 | 7.30 / 4.63 | 213.32 ms |

An `xcodebuild` process appeared in Complementary's sampled workload. The other cases showed no such process in their sample lists. The results measure renderer output during this batch. They do not establish physical display delivery or a controlled cap-only comparison across the two batches. See `outputs/horizon-runtime/shader-followup-f42-uncapped-r1.json` and each linked raw result. Both game process checks were clear and the shared queue returned idle.

