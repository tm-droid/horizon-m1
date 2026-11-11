# R18: shader pack compatibility on Horizon f42 (M1 8 GB), 2026-11-06

Method: read the pristine f42 stage `crates/horizon-shaders/src` (paths below relative to it), `gh` read-only on horizon-rust/horizon, pack source trees via `gh api` (no zips downloaded).
**Gap:** the Modrinth API was unreachable from the sandbox (TLS `UNABLE_TO_VERIFY_LEAF_SIGNATURE`; WebFetch blocked by hook). So the "top 30 with a 26.3 build" list and all Modrinth version ids are NOT obtained. Slugs below marked (?) are unverified. Re-run the search from an unsandboxed shell.

## 1. Translator support matrix (f42)
Supported
- GLSL 110-460, compat or core -> Vulkan GLSL 450 -> naga (`translate/mod.rs:1-3`); `#version`/`#extension` split out, `#include` expanded in live code only, nest limit 10, guarded headers read once (`preprocess.rs:2-8,190-204`).
- Reported to packs as GL 3.3 / Iris 1.11.7 (`macros.rs:101-119`: MC_GL_VERSION 330, IS_IRIS, IRIS_VERSION 11107, MC_GL_VENDOR_OTHER). Packs gating on GL 4.3+ take their fallback path.
- Stage groups setup, begin, prepare, deferred, composite, final, gbuffers, translucent, shadow, shadowcomp..shadowcomp99 (`post.rs:24-41,202-205,887`).
- Compute `.csh` incl. setup/begin/prepare/composite/shadowcomp variants, shared memory, barriers, atomics, subgroupAdd (`post.rs:1090-1096,1221`; tests `translate/mod.rs:2496-2619`).
- Iris features list: BLOCK_EMISSION_ATTRIBUTE, COMPUTE_SHADERS, CUSTOM_IMAGES, ENTITY_TRANSLUCENT, REVERSED_CULLING, SEPARATE_HARDWARE_SAMPLERS, SSBO (`macros.rs:11-19`). Unknown `iris.features.required` -> pack rejected with a note (`macros.rs:143-157`).
- SSBO `bufferObject.N` (`post.rs:274,627`), `image.*` (`post.rs:308,634`), custom textures incl. 3D `.dat` and `customTexture.*` (`textures.rs:1-16,440-460`), custom uniforms/variables incl. smooth() (`custom.rs:1`).
- colortex formats incl. RGB10_A2, R11F_G11F_B10F, per-buffer clear/mipmap (`config.rs:13-60,97-116`); shadow buffers, shadowcolor0/1 (`config.rs:124-146`); flips (`post.rs:383`); `scale.<program>` (`post.rs:1346`).
- Dimension folders `world0/-1/1` and `dimension.properties` mappings (`post.rs:506-531`).
- textureGather, textureGatherOffsets (emulated), swizzled scalars, flat interface blocks (`translate/mod.rs:2015,2048,2251`).
Partial
- Geometry stage (.gsh): shadow pass terrain/entities only, other programs skipped with a note (`post.rs:229,1036`).
- Unsupported-feature gaps listed upstream as open: tessellation stages ignored (#7922), SSBO binary init files (#7899), SSBO indirect dispatch (#7924), shadowcolorimg0/1 bind zeros (#7921), sky/star/sun geometry switches ignored (#7928), `block.properties` render-layer overrides (#7926), translucent block/mixed particle programs never selected (#7904), per-buffer blending query (#7940), `flat` qualifier errors (#8174).
Unsupported
- DH / Voxy programs (`dh_*`, `voxy_*`): no references in src (rg: none). Harmless, packs fall back.
- Features absent from `FEATURES`: FADE_VARIABLE (`mc_chunkFade`, upstream #9545), HIGHER_SHADOWCOLOR / shadowcolor2-7 (#8134; rg: none in f42). Packs that list them only as `optional` still load.

## 2. Upstream reports (issues, state at 2026-11-06)
- Photon: #3525 crash (closed), #5112 smooth() uniforms (closed), #6696/#7870/#8269 Mac M2 reports "looks weird / bottom-left quadrant / 1/4 of screen": reporter says it happens with **resolution scale on** (#8269). Do not combine shader packs with the R16 resolution scale until tested.
- Complementary: #944, #9037 closed. Solas: #1544 crash closed. Bliss: #6811, #5370 closed; #8269 res-scale. Bloop: #7168 `prepare1` fails (open). Chocapic13: #9972 invisible leaves (open, Linux). I Like Vanilla: #7169 `gbuffers_block` fails, "Unknown variable: sampleCount" (open) -> block entities (chests, signs) not drawn by pack.
- BSL: open #8672 white sky below horizon rim, #7371 dark horizon, #8464 over-shadowing + stripe acne (all packs with shadows), #9857. MakeUp: #5960 fixed (gl_FogFragCoord); #8672 notes MakeUp does not show the sky bug. Lux/Fantasy/Pixel Perfect: End wrong (#10491). Visual Vibrance: daylight overworld black (#10490). PotatoShaders: caves/Nether too bright (#9307), rain streaks (#10492).
- No hits for Kappa/Eclipse/Insanity/SEUS/Rethinking Voxels reports beyond translation fixes (Kappa #5303 #6175 closed; `translate/mod.rs:2197,2691`).
- Merged after f42ef42 that we lack (seen in merged list, dates 11-04..11-06): #9002 min3/max3/mid3, #9815 keep programs with unsupported uniform defaults, #9545 mc_chunkFade, #9381 explicit rain.depth, #9007 integer colortex0, #10456 smooth() across teleport, #9978 Shaders page. 11-03 merges may or may not be in f42 (stage lacks #8134). Also main commit a66f8fa2: shadow pass draws only terrain that can shade the view (cheaper shadows).

## 3. Candidate judgement (from source trees)
- Photon (sixthsurge/photon): 4 deferred + ~22 composite passes, `.csh` in setup/shadowcomp/deferred4_a (subgroupAdd, local_size 256), 3D `.dat` textures, CUSTOM_IMAGES optional, `profile.low` = 1024 shadow map, no VL/colored lights. Features all in matrix. Heavy.
- Complementary (same Modrinth project HVnmMxH1 holds Reimagined and Unbound; one zip): `shadowcomp.csh` x3 dims, SSBO bufferObject 51-203 MB only when COLORED_LIGHTING > 0 (profiles up to LOW set 0), `profile.POTATO` shadowDistance 64, FXAA off. Translator has Complementary fixes (`translate/mod.rs:2215`).
- Solas (Septonious): `shadowcomp.csh`, `image.voxel_img` 128x64x128 r8ui and rgba16f floodfill (CUSTOM_IMAGES); LPV only at HIGH. `profile.LOW` drops bloom/VL/clouds. Translator has Solas fix.
- E-LITE: MakeUp UF derivative (Modrinth "lite-shaders" ?), same code base the translator was built on.
- Rethinking Voxels / Kappa / Lux / SEUS: ray tracing or SSBO voxel pipelines, too heavy for 8 GB. Skip.

## 4. Ranked shortlist (new packs, max 6)
1. E-LITE (MakeUp UF fork, slug lite-shaders ?, version id TBD). Compat: high (same GLSL 120 style, gl_FogFragCoord fix #5960 covers it). Cost: MakeUp +0-20%. Why: closest look, a bit fancier.
2. Complementary Reimagined style, POTATO/VERYLOW profile (slug complementary-shaders, project HVnmMxH1, version id TBD). Same zip as queued Unbound, so test as a profile variant, not a second download. Compat: good (older Unbound issues closed; shadowcomp.csh supported). Cost: 2-3x MakeUp at LOW; POTATO ~1.5-2x (prediction, unmeasured).
3. Solas, profile LOW (slug solas-shader ?, TBD). Compat: good (translator fix, CUSTOM_IMAGES/compute supported). Cost: ~1.5-2x MakeUp.
4. Photon, profile low (slug photon-shader ?, TBD; 26.3 build not confirmed, only 26.1.2 seen). Compat: medium (compute + 3D tex supported; Mac reports tied to res scale). Cost: 3x+ MakeUp. Look ceiling test only.
5. Chocapic13 Lite (Modrinth "LIGHT Shaders" is a Chocapic13 derivative; slug TBD). Compat: medium, #9972 invisible leaves. Cost: ~MakeUp x1.5. On Horizon's native roadmap.
6. PotatoShaders (slug ? TBD). Compat: daytime overworld OK, caves/Nether bright (#9307), rain broken (#10492). Cost: below MakeUp. Fallback only.

## 5. Queued packs predicted to fail or degrade
- I Like Vanilla: partial. `gbuffers_block` skipped (#7169), block entities drawn without the pack.
- Bliss: likely renders wrong with resolution scale (#8269) and is far too heavy (volumetric clouds + large shadow); expect <15 FPS. Low priority.
- BSL: loads, but white sky below horizon rim (#8672) and shadow acne (#8464); heavy. Expect poor.
- Complementary Unbound: loads; keep COLORED_LIGHTING=0 (SSBO 51-203 MB) and a LOW/POTATO profile.
- Super Duper Vanilla, Sildur's Vibrant, Mellow, Miniature, Baked Potato, Sildur's Enhanced Default: no upstream reports; Mellow and Miniature have dedicated translator fixes (`translate/mod.rs:2705,2147`). SDV and Vibrant not source-checked (unverified).
