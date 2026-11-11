# MakeUp UltraFast + resource packs: GPU audit for M1 (2026-11-10)

Method: read the unzipped pack GLSL (/private/tmp/claude-503/makeup/), the user's sidecar and options, and the r12 client source. No game run. **All ms figures are estimates** scaled from R22's per-pass table (docs/horizon-converter/research/R22-freeze-and-tune.md) and the 2560x1600 / ~34 ms frame; none were measured. Bench before keeping anything (HORIZON_SHADER_PACK_TIMING=1 gives per-pass GPU ms).

## 1. Current values (sidecar MakeUp-UltraFast-9.6.zip.txt + config.glsl defaults)
Sidecar: IMAGE_SHARPENING=true, V_CLOUDS=2, AOSTEPS=4, BLOOM_SAMPLES=2.0, CLOUD_REFLECTION=false, CLOUD_STEPS_AVG=8, COLORED_SHADOW=false, SHADOW_DISTANCE_SLIDER=0. This is exactly R6's "same-look-cheaper" preset, so the cheap option-only wins are already taken.
Defaults still in force: SHADOW_CASTING on, SHADOW_QTY 2 (600 px map over 75 blocks, confirmed in the client log), SHADOW_TYPE 1 (4 shadow taps/pixel, SHADOW_BLUR 2.0), AO=1, AA_TYPE=2 (TAA + SELECTIVE_TAA_V2 FXAA on masked pixels), REFLECTION_SLIDER 2 (10-step raymarch), VOL_LIGHT 1 (4-tap depth godrays), BLOOM on, MATERIAL_GLOSS on, REFRACTION 1, WAVING 1; DOF, motion blur, chroma aberration off.

## 2. Ranking: 8 costliest items, proposed value, honoured?
All sidecar keys are compile-time #define rewrites (horizon-shaders/src/options.rs `apply`), so every one is honoured. Hard-coded constants without a `// [list]` (RAYMARCH_STEPS 10, GODRAY_STEPS 6, CHEAP_GODRAY_SAMPLES 4) are not sidecar-tunable; they would need a patched zip.

| # | Cost item (per frame) | Est. ms | Proposal | Est. saving | Look change |
|---|---|---|---|---|---|
| 1 | Pixel count: every pass runs at window x resolutionScale (graphics.txt, not sidecar) | whole frame | resolutionScale 85 (or 75) | 85: 5-8 ms; 75: 9-12 ms | Soft, see section 5 |
| 2 | gbuffers fragments (terrain, entities, hand, particles, weather): 4 shadow taps + gloss + fog tex fetch, in solid_blocks_fragment.glsl | 6-8 (R22) | MATERIAL_GLOSS=false; SHADOW_TYPE 0 only if needed | gloss 0.3-0.8; type 0: 1-2 | Gloss "very subtle"; type 0 gives harder, stair-stepped shadow edges (600 px / 150 m = 4 px/m) |
| 3 | Shadow map pass (terrain + entities re-rasterised into 600x600, shadowCache off) | 1-2.5 | already small (dist 0, qty 2); keep | 0 | none. QTY 1 (300 px) is blocky |
| 4 | deferred AO: 2 x AOSTEPS depth taps + linearise per pixel, full screen (lib/ao.glsl) | ~1.5-2 of the 3-4 ms deferred | AOSTEPS 3 | 0.4-0.7 | Near invisible: per-pixel dither + TAA hide it |
| 5 | deferred volumetric clouds: sky pixels only, CLOUD_STEPS_AVG x (2 noise taps with V_CLOUDS=2) | up to 1.5-2 looking at sky; 0 in caves/nether | V_CLOUDS 1 (tier B); steps already 8 | 0.5-1 (sky views) | Less cloud shape detail |
| 6 | composite2: TAA (18 fetches) or FXAA (13 fetches) on masked pixels | 1-1.5 | AA_TYPE must stay 2 | 0 | n/a |
| 7 | Water/glass SSR raymarch (REFLECTION_SLIDER 2, 10 steps, water pixels only) | 0.5-2 with water | REFLECTION_SLIDER 1 (tier B) | 0.5-2 | Flipped-image reflections, visible on water |
| 8 | composite: godrays 4 taps (VOL_LIGHT 1); bloom 2x4 taps (already minimum); final CAS 9 taps | 0.3-0.5; ~1; 0.7-1 | VOL_LIGHT 0 (tier B); keep bloom and CAS | 0.3-0.5 | No sun godrays |

Already optimal or zero-risk: COLORED_SHADOW off, CLOUD_REFLECTION off, BLOOM_SAMPLES 2.0 (list minimum), AOSTEPS list minimum is 2. SHADOW_BLUR costs nothing (tap count fixed).
Net of the proposal file (tier A): about 0.7-1.5 ms. Tier B adds up to ~3-5 ms in the worst case (sky + water views). resolutionScale and the rain/particle settings are far bigger.

## 3. Rain (~10 FPS) and lava (~13 FPS)
**Rain, code path found.** Horizon draws the game's weather quads through the pack's gbuffers_weather (pack_weather.rs, pack_post.rs `weather`), after translucent terrain. MakeUp's gbuffers_weather.fsh includes the *same* solid_blocks_fragment.glsl as terrain, so every rain/snow fragment runs the full lit-surface path: 4 shadow2D taps, material gloss, fog texture fetch, alpha blend. weatherRadius is 10 in options.txt, i.e. 21x21 camera-facing columns of large alpha-blended quads, with heavy overdraw at 2560x1600. The program also writes colortex2=1 (src/writebuffers.glsl), so rain pixels go through the FXAA branch in composite2 and lose TAA, which adds shimmer but no cost. The splash particles (particles:0 = All) go through gbuffers_textured with the same fragment. The clouds loop is a fixed count, so heavier rain cloud cover does not change its cost.
Cheaper, in order: (a) options.txt `weatherRadius:10 -> 5` (about 3.6x fewer columns; drops distant rain, fog hides most of it; est. 3-6 ms in rain); (b) `particles:0 -> 1` (Decreased); (c) MATERIAL_GLOSS=false; (d) a patched pack where `#ifdef GBUFFER_WEATHER` forces shadowValue=1.0 and skips gloss in solid_blocks_fragment.glsl (rain is unlit by shadows anyway; est. 1-2 ms; needs a zip edit, not applied).
**Lava, not proven.** Lava is just solid terrain in MakeUp (block.properties id 10090 only sets omniLight 0.45 in the vertex stage; no extra passes), so the pack has no lava-specific cost. Plausible contributors, unverified: (1) lava pop, drip, smoke and the better_flame_particles flame sprites, all drawn through the full lit fragment (particles:1 helps); (2) engine block-light grid: "a lava lake lists thousands" of sources, up to 2048 splatted per rebuild every 16 blocks (gfx/block_light.rs:21), plus bright terrain relight/remesh; (3) animated lava_still/fire atlas updates with full mip regeneration (animatedTextures:true, pack_post.rs ~4849). Next step: HORIZON_SHADER_PACK_TIMING=1 and `gpu-passes on`, stand at a lava lake and away from it, compare per-pass ms. If a GPU pass does not grow, the cost is CPU/engine and no shader option will fix it.

## 4. Resource packs (options.txt order; 63 enabled, 56.1 MB zipped, ~592 MB if every PNG were decoded to RGBA8)
Widths read from PNG headers (script /private/tmp/claude-503/rp/scan.py; equivalent to `sips -g pixelWidth`). Animated strips use frame width. Vanilla is 16x. Packs with nothing above 16x: all the Horizon-* compat packs, Tanush Fixes, Connected Bricks/Rocks, Gentler Weather, Vocal Villagers, Fine/Low/etc. that read 16/32 only for a few sprites.
Flags (>16x):
- Weskerson's Torches: block max 256, item max 256 (flame gradients), particle glows 430x430. 16 MB decoded. Flag.
- Fresh Buckets: items 32 median, 3D strips up to 640x12160 (each 31 MB decoded, ~169 MB total). Item atlas gets 21 sprites above 16x (~8.9 MB before mips and frames). Flag, biggest waste.
- Dramatic Skys Demo: 3072x2048 skybox PNGs plus 4000x2000 moon phases, ~212 MB decoded (~280 MB with mips on the GPU). Under MakeUp the sky is drawn by gbuffers_skybasic, so this is probably wasted memory (unverified whether the custom skybox still draws over it). Flag.
- Recolourful Containers DARK: GUI textures up to 512, 94 MB decoded (animated written_book strip). Only GUI, no world cost.
- Fresh Flowers and Plants (blocks 24 median, 64 max, 3D bowls), Bushier Bushes (32), Fancy Crops (32), RAYs 3D Rails (32, 28 sprites), Fresh Food / Fresh Ores / Fresh Music Discs (32 items), Teddy Totems (64), Fine Armoury (32 items, 64 entity), Better Beds (64), visuals (400 px spawn-egg strips), Icons (256 toast art, UI only), 1.18 Panorama (6 x 1024, menu only).
- Entity textures 128-256 (Fresh Animations, FA+ extensions, 3D Harness, 192 max) are standalone textures, not atlas.
Atlas verdict: sprites that go into block/item atlases total about 18 MB at one frame each, so the *block atlas is not meaningfully inflated* (few >16x block sprites). The real cost is memory on an 8 GB UMA machine (u7a bench footprint 1.2-1.9 GB), not per-frame GPU time. Disabling Dramatic Skys and Fresh Buckets would free roughly 300-450 MB. No GPU time estimate; texture sampling of the sky is cheap.

## 5. resolutionScale and the upscaler (graphics.rs ~435, gfx/pack_post.rs ~5250 and ~5694, shader-api reference.rs:185)
- horizon-graphics.txt has `resolutionScale:100`, `upscaling:native`, `taa:false`, `fxaa:false`.
- Under a shader pack, Horizon's own TAA, FXAA and the Upscaling enum (Native 1.0, Quality 1.5, Balanced 1.7, Performance 2.0, UltraPerformance 3.0 per axis) **do not run**; the docs say so explicitly. Those are Horizon's FSR-like Halton-jittered TAA upscaler (world_post.rs), not FSR2 or MetalFX; there is no MetalFX anywhere ("FSR 3.1" is frame generation only).
- With a pack, resolutionScale is the only lever: every gbuffers and composite pass and the pack's `final` (CAS) run at window x scale, then one bilinear fs_copy stretches the picture to the window (pack_post.rs:5694, "one upscale, smoothly"; issue 9291 is handled in this source). HUD, hand overlay and text stay native resolution. MakeUp's own TAA still runs inside the pack at the lower resolution.
- 75% = 1920x1200 (56% of the pixels), 85% = 2176x1360 (72%). Expected: 75% saves ~9-12 ms (about 34 to 22-25 ms, roughly 40-45 FPS), 85% saves ~5-8 ms (about 26-29 ms). Look: plain bilinear stretch of 1.33x (75) or 1.18x (85), slightly soft edges and softer texture detail; CAS sharpens before the stretch, so raise SHARPENING to 0.7 (tier B line in the proposal) to compensate. 85 is the subtle option; 75 is noticeable on high-res packs like the 32x/64x ones.

## 6. Web research (one standard search)
Little hard data. Sources only say MakeUp Ultra Fast ships with most expensive effects off, shadows are the main strain, shadowless presets are the low-end start, and to configure it in its own menu rather than OptiFine's. No per-option M1 numbers exist; the costs above come from the GLSL. Sources: https://shadersmods.com/makeup-ultra-fast-shaders , https://modrinth.com/shader/makeup-ultra-fast-shaders , https://cybrancee.com/blog/the-best-minecraft-shader-packs-for-low-end-computers/

## 7. Files and caveats
- Proposed sidecar (not installed): ~/Developer/Horizon/outputs/makeup-m1-proposal-2026-11-10/MakeUp-UltraFast-9.6.zip.txt (tier A active, tier B commented).
- Not touched: user game dir, shader zips, options.txt, horizon-graphics.txt.
- Context: u7a bench shows R11 build runs MakeUp at ~26 ms GPU versus ~34 ms on fdc87ae/DAILY builds, so a larger regression sits in the engine than any option here removes. Prior audit (gpu-m1-audit-2026-11-10.md) items 2-4 (merged gbuffers passes, redundant vanilla pass, alpha-test discard) are bigger than the pack options.
