# R22: freeze a translated Iris pack into a native `.hshader`, and tune it for the M1 (2026-11-06)

Scope: Horizon f42ef42 (pristine stage `outputs/horizon-runtime/launcher-data/native/stage`, read-only), MacBook Air M1 8 GB, 2560x1600 (`resolutionScale:100`, `upscaling:native` in `tests/u9-makeup-daily-1/horizon-graphics.txt:26,29`). Nothing was compiled, launched or benchmarked. Line numbers are pristine stage unless noted. Native packs read as data only: `outputs/horizon-native-packs/*.hshader`.

## Verdict

"Translate once, then repackage as `.hshader`" is **not feasible as a mechanical step**. The native format is a different model. It defines stages with fixed signatures inside Horizon's own passes. It is not a graph of GL programs. The translator's output does not fit into it.

What **is** feasible, ranked:

1. **Tune Montarc for the M1 (recommended first).** Montarc is MIT, native, and claims about 3 ms of GPU time. Its manifest and WGSL use nothing that f42 lacks (lexical check below). It is the only one of the five downloaded packs that does not pay for the 16 B/px surface target.
2. **Port MakeUp to the native API by hand**, using MakeUp's GLSL as the reference (LGPL-3.0, so the port stays LGPL). This is weeks of work, and entities stay unshaded.
3. **Freeze inside the Iris path.** Dump the translated naga modules to WGSL and hand-edit them. A small loader patch reads the edited WGSL back instead of re-translating. Gains are capped by the Iris pass structure in `pack_post.rs`.

## 1. Is `.hshader` supported by f42?

Yes. f42 has the full loader. Newer nightlies only add manifest keys and API fields.

- Format: `crates/horizon-shader-api/src/package.rs:12` (`EXTENSION = "hshader"`) reads a folder or a zip (`:57`). Builds are deterministic (`:157`). The manifest is `horizon-shaders.toml`, with `SCHEMA = 1` and `API = "0.1"` (`manifest.rs:7,10`). The spec with every key is `docs/api/shaders.md:37-131`.
- Contents:
  - stages `[sky]`, `[material]` (`fn material(MaterialInput) -> Surface`), `[vertex]`, `[weather]` and `[shadow]` (`resolution` 256-8192, `distance` 32-512);
  - `[[post]]`, at most 8 passes (`manifest.rs:12`), each `fn post(PostInput) -> vec4<f32>` (`inputs.rs:215`);
  - one colour output per pass, plus at most 4 named targets (`manifest.rs:273`) at scale 1, 0.5 or 0.25 (`:400-464`);
  - `[[options]]` as WGSL `override` constants (at most 64), plus `[[materials]]`, `[[lights]]`, `[[tags]]`, `[[textures]]` (8 PNGs, 2048 px at most) and `[budget] gpu_ms`.
- Uniforms: a single generated `Frame` struct. There are no custom uniforms and no preprocessor (`docs/api/shaders.md:16-28`).
- Post resources: `scene_color`, `scene_depth`, `previous`, `history`, `scene_surface` and others (`stages.rs:105-192`).
- Load path:
  - `gfx.rs:5717` `set_native_shader_pack` calls `native_pack.rs:37` `NativePack::new`, which builds sky, material, post and shadow (`native_post.rs`, `native_material.rs`, `native_shadow.rs`).
  - Launcher drop/import: `launcher/src/packs_page.rs:3`, `launcher/src/cli.rs:470`.
- Every manifest table is `#[serde(deny_unknown_fields)]` (`manifest.rs:80-395`). A key newer than f42 makes f42 refuse the whole pack.

Downloaded packs checked against f42. Each TOML table was compared with the fields of the f42 structs. Every identifier in the WGSL was compared with the `horizon-shader-api` sources.

| Pack | Unknown manifest keys on f42 | WGSL identifiers missing in f42 | Expected on f42 |
|---|---|---|---|
| montarc-1.1.1 | none | none | Loads, but the README says "needs nightly 2026-11-04+". The cause is not found lexically. Verify with `horizon-shader check` |
| daybreak-0.1.1 | none | none | Loads |
| daybreak-0.2.0 | `[shadow] option`, `distance_option`, `resolution_option` (f42 `Shadow` has only `resolution`, `distance`, `solid_materials`: `manifest.rs:81-91`) | none | **Refused** |
| meridian-26.3.1 | none | none | Loads |
| meridian_compat-26.3.1 | none | none | Loads |

The check is lexical: naga validation and the signature checks (`check.rs`) were not run. The `horizon-shader` CLI (`crates/horizon-shader-api/src/bin/horizon-shader.rs`) is not built in `target/fast`.

## 2. Can the translator output be frozen and repackaged?

The translator produces per program `Program { vertex: naga::Module, fragment: naga::Module, interface }` (`horizon-shaders/src/translate/mod.rs:124-127`). It wraps these in `PostProgram { name, group, program, buffers, flips, blend, buffer_blends, mipmaps, compute, geometry_triangles, scale }` (`post.rs:210-240`).

- **No WGSL dump and no shader cache exist in f42.**
  - `HORIZON_SHADER_PACK_DUMP` only logs a texel count of one image (`pack_images.rs:481-491`).
  - `.horizon-cache` holds world, registry and resource-pack snapshots only (`horizon-world/src/level/data/cache.rs:35`, `game/packs.rs:26`). The pack is re-translated on every load.
  - So freezing saves **load time only, not FPS**. The runtime cost comes from the passes and the shader work, not from the translation.
- Debug environment variables that exist:
  - `HORIZON_SHADER_PACK_SKIP=<program,...>` leaves programs out (`pack_post.rs:2127`). This gives ablation timing.
  - `HORIZON_SHADER_PACK_WITHOUT=compute,...` (`:276`).
  - `HORIZON_SHADER_PACK_TIMING=1` (`pack_timing.rs:87-91`).
- A dump is cheap to add. Vendored naga has `back/wgsl` (`third_party/naga/src/back/wgsl`), but `horizon-shaders` enables only `glsl-in` and `wgsl-in` (`crates/horizon-shaders/Cargo.toml:11`). It needs `wgsl-out` plus a `naga::back::wgsl::write_string` per module.
- Why the dump cannot become an `.hshader`:

| Iris concept (MakeUp uses it) | Native API 0.1 | Result |
|---|---|---|
| gbuffers programs with their own vertex and fragment stages, MRT `DRAWBUFFERS` | `material` returns one `Surface` for terrain only. "Entities, block entities and particles are not shaded yet" (Montarc README). `[vertex]` returns a position only | Rewrite. Entity, hand and particle looks are lost |
| `deferred`/`composite*` MRT, e.g. `DRAWBUFFERS:016`, `:135` | One `vec4` per pass and at most 4 named targets | Split or merge passes by hand |
| Pack formats (R11F_G11F_B10F, R16F, R8) | Chain targets are fixed `Rgba16Float` (`native_post.rs:14,739,815`). The surface target is `Rgba32Float` (`native_material.rs:284`) | Lossless but heavier |
| Custom uniforms (`uniform.float.dayMixer = ...`, `shaders.properties`) | `Frame` fields only | Recompute them in WGSL from `Frame` |
| Option `#define`s and `#if` branches | `override` constants. There is no preprocessor | Freeze one combination, or turn branches into overrides |
| `flip.`, ping-pong colortex sides, `colortexNClear`, mipmaps (`softLod` bloom) | Implicit chain with `previous`/`history`. No mip generation | Re-plumb by hand |
| `shadow` program (pack geometry, colored shadow) | Engine-drawn `[shadow]`, with `shadow_map_translucent` and `shadow_color` | Close equivalent; the shadow vertex code is lost |
| Custom PNG textures (clouds 512 R8) | `[[textures]]`, 8 at most, 2048 px at most | OK |

## 3. Where translated MakeUp spends GPU time

User settings: sidecar `IMAGE_SHARPENING=true`, `V_CLOUDS=2`. Everything else is the default in `lib/config.glsl`: `AO 1` with `AOSTEPS 5` (:55-56), `AA_TYPE 2` TAA (:58), `VOL_LIGHT 1` depth godrays with `GODRAY_STEPS 6`, `REFLECTION_SLIDER 2` SSR raymarch (:31-44), `BLOOM` with 3x4 taps, `SHADOW_TYPE 1` + `COLORED_SHADOW`, shadow 840 px over 105 blocks (`SHADOW_DISTANCE_SLIDER 1` / `QTY 2`, :202-262), `CLOUD_STEPS_AVG 10`.

Formats (`common/final_fragment.glsl:16-46`, no DOF): colortex0, colortex1 and colortex3 R11F_G11F_B10F (4 B); colortex2 R8; gaux1 (4) R11G11B10F; gaux2 (5) R8; gaux3 (6) R16F; gaux4 R11G11B10F; shadowcolor0 RGBA8. One full-res 4 B target is 16.4 MB at 2560x1600.

| Pass (order) | Writes | Work per pixel | Est. ms on M1 | Could be lower res? |
|---|---|---|---|---|
| shadow (840², 105 blocks, pack shader) | depth + shadowcolor0 | Terrain re-raster | 1-2.5 (cached when static: `ShadowCache`, `pack_post.rs:475-502`) | It is already small |
| gbuffers terrain/water/entities/hand (pack shaders on Horizon meshes; passes reopened with Load/Store, `pack_post.rs:2828`, `3178-3215`) | colortex1 and others | Forward light, soft colored shadow (2 shadow maps + colour), water SSR raymarch | **6-8** (largest) | No (geometry) |
| depth1/depth2 copies (`pack_post.rs:3198-3213`) | 2x D32 | Copy | about 1 | Needed |
| prepare | small | Sky gradient | 0.3 | – |
| deferred `DRAWBUFFERS:14` | colortex1, gaux1 (8 B) | AO 11 depth taps; volumetric clouds 10 steps on sky pixels | **3-4** | **Yes: AO and clouds at half res** |
| composite `016` | colortex0, colortex1, gaux3 (10 B) | 6-tap depth godrays, fog | 1.5-2 | Godrays at half res |
| mip chain of colortex0 (`mipmap` `:3439`) | mips | One pass per level | 0.3 | – |
| composite1 `1` | colortex1 | Bloom 12 taps at `softLod` | 1-1.5 | Bloom at 1/4 res |
| composite2 `135` | colortex1, colortex3, gaux2 (9 B) | Fast TAA (reproject + clamp) | 1-1.5 | No |
| final | swapchain | Tonemap + CAS sharpen (9 taps) | 0.7-1 | No |

The sum is about 16-21 ms. That matches the measured gap: the pack adds about 18 ms (43 FPS against about 170 FPS without a pack, R20). All rows are **estimates**: the bench logs have no per-pass data.

**How to get a real per-pass split.** `result.json`'s `measurement.gpu_passes` has only Horizon's own passes. The reason: `summary_with_passes` exports only `own_pass_times()` (`horizon-client/src/game/control.rs:133-147`). `gpu-passes on` (`control.rs:390-397`) already times the pack too, through `set_pass_timing(self.debug || self.gpu_passes)` (`game.rs:15516`, `gfx.rs:5821`, creation at `gfx.rs:7751`). Those times reach only `shader_pass_times()` (`gfx.rs:5837`), and from there only the F3 overlay (`game/debug_lines.rs:163-169`). Three ways to get them, cheapest first:

1. Launch with `HORIZON_SHADER_PACK_TIMING=1`. Every 30 timed frames `console.log` gets `shader pack GPU time per pass (median ms of the last 15 timed frames): <name> <ms>, ... = <total>` (`pack_timing.rs:14,253-256`). Names are the program names (`clear`, `world`, gbuffers programs, `shadow`, `deferred`, `composite1`...; `pack_post.rs:2860,3805,4062,4103,4225`). No rebuild is needed.
2. Patch **`outputs/horizon-native/r22-pass-split/pass-split.patch`** (written; `git apply --check` OK on pristine stage; no r4 patch touches `control.rs`). It adds `summary["shader_passes"]` from `shader_pass_times()`, so `bench`/`stats` and `result.json` carry the split. It is uncompiled.
3. Ablation: `HORIZON_SHADER_PACK_SKIP=deferred` (and each other post program, one at a time) and compare frame time. This is more trustworthy on Metal. Passes overlap there, so timestamp sums exceed the frame, which is why `benchmark.rs:118-131` skips pass timing on Metal. Use timestamps for ranking and ablation for absolute ms.

## 4. M1 tuning list (ranked by est. ms saved / visual cost)

### A. Montarc-M1 (native; recommended track)

Montarc structure (manifest): sky; material (`fog=false`) with shadow PCF; vertex wind; `[shadow] 2048 / 128`; `[reflection] option=reflections` (half-res mirror, `native_post.rs:202-203`); post chain: bloom prefilter/H/V at 0.25, then `composite`, then `fxaa`. It uses no `set_surface` (grep: 0 uses), so it skips the 16 B/px `Rgba32Float` target. Daybreak and Meridian both call it: about 65 MB written plus a read per frame, about 1.5-2 ms on M1. That is why Montarc is preferred.

| # | Change | Est. saved | Visual cost | How |
|---|---|---|---|---|
| A1 | `[shadow] resolution 2048 -> 1024`, `distance 128 -> 96` | 0.7-1.5 ms (4x fewer texels; less terrain in the shadow pass) | Softer far shadows; `shadow_softness` hides it | Manifest only |
| A2 | `shadow_samples` Medium -> Low (choice option) | 0.5-1 ms (PCF taps per lit pixel at full res) | Slight noise | Option |
| A3 | Drop the `fxaa` pass (the `fxaa` option likely only skips the work inside the pass, unverified; deleting the `[[post]]` entry removes the pass itself) and keep `sharpen` | 0.4-0.7 ms (one full-res RGBA16F read + write) | Aliasing on edges | Manifest |
| A4 | Engine: chain `INTERMEDIATE` `Rgba16Float -> Rg11b10Ufloat` when the pack does not need alpha (`native_post.rs:14`) | 0.3-0.6 ms per full-res chain pass | None for HDR RGB | f42 patch (opt-in key or env) |
| A5 | Engine: native shadow `Depth32Float -> Depth16Unorm` (`native_shadow.rs:196,201,379,546`) | 0.2-0.5 ms | Possible acne; tune `shadow_bias` | f42 patch |
| A6 | `reflections=false` | 1-3 ms when water is in view (a whole half-res mirror world draw) | Water mirror gone | Option |
| A7 | f16 in the material and composite math | 0-10 % ALU; needs `SHADER_F16`, which is not requested (`gfx.rs:1843-1853`) | Banding risk | Later |

### B. Frozen MakeUp (Iris path, or a native port)

| # | Change | Est. saved | Visual cost |
|---|---|---|---|
| B1 | R20 #1 composite-overwrite (Clear instead of Load), already in r4 | 1-3 ms | None |
| B2 | deferred AO + volumetric clouds at half res, bilateral upsample in composite | 1.5-2.5 ms | Slightly soft cloud and AO edges; TAA hides most of it |
| B3 | Fuse the gbuffers render passes (R20 #2) | 1-3 ms | None (ordering risk) |
| B4 | `REFLECTION_SLIDER 2 -> 1` (flipped image instead of SSR raymarch; option only) | 0.5-2 ms with water | Less accurate water reflection |
| B5 | Bloom at 1/4 res, merged into composite1 (drops the mip chain) | 0.5-1 ms | None visible |
| B6 | Shadow `QTY 2 -> 1` (840 -> 420 px; option) | 0.3-1 ms | Blurrier shadows |
| B7 | `AOSTEPS 5 -> 3` (option) | 0.3-0.6 ms | Slight AO noise |
| B8 | Merge final's CAS into the composite2 TAA pass | 0.3-0.5 ms | None |
| B9 | Memoryless (`TRANSIENT`) depth for discarded attachments | Memory only (R20 #6) | None |

Formats are already lean (R11G11B10F everywhere except gaux3 R16F, R20 "refuted"). Format work only matters after a native port, where chain targets become RGBA16F (A4).

## 5. Effort and first step

| Track | Effort | Expected FPS on the bench scene |
|---|---|---|
| 0. Per-pass split (env var + `r22-pass-split`) | 0.5 day (one build + one bench) | Measurement only |
| A. Montarc-M1 fork (A1-A3 manifest/option, one bench each) | 1 day | Unknown until measured. Native packs on M1: no published numbers. A guess of 5-9 ms GPU at 2560x1600 means about 2x MakeUp's FPS |
| A + engine patches A4/A5 | +1-2 days | +0.5-1 ms |
| C. Iris freeze: WGSL dump (`wgsl-out`) + override loader + B2/B5/B8 by hand | 3-5 days | +3-6 ms over r4 |
| B. MakeUp native port (material = gbuffers lighting; 6 post passes: AO/clouds, godrays, bloom 0.25, TAA (`history`), final) | 2-3 weeks, LGPL-3.0 | Highest ceiling; entities unshaded until the API gains a stage |

**First step (small, testable):** on the next bench slot, run the usual MakeUp scene twice on the r4 build.
- Run 1 with `HORIZON_SHADER_PACK_TIMING=1`. Grep `console.log` for `shader pack GPU time per pass`.
- Run 2 the same way with Montarc 1.1.1 at defaults, copied into the test profile's `shaderpacks/`.

Accept the step when both runs log a per-pass line and Montarc loads on f42. If Montarc is refused, the log names the check, which settles the "needs 11-04" question. Optionally build `r22-pass-split` into the next build, so `result.json` gets `shader_passes`. That number set replaces the estimates in §3. It also decides A versus C: if Montarc reaches 70 FPS or more, go with A.
