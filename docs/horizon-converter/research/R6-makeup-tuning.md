# R6: MakeUp Ultra Fast 9.6 tuning for Horizon (M1 8 GB, 720p, RD12)

Sources: GLSL in the zip (config.glsl, ao.glsl, volumetric_clouds.glsl, shadow_frag.glsl, composite*/deferred fragments). Web (Reddit, Modrinth comments, author docs) gave no per-option FPS numbers; costs below are inferred from the shader code, NOT benchmarked. Verify with the bench method in CLAUDE.md.

## Current effective state
Sidecar sets only `IMAGE_SHARPENING=true`, `V_CLOUDS=2`. Everything else = config.glsl defaults:
shadows ON, SHADOW_DISTANCE_SLIDER=1 (105 m), SHADOW_QTY_SLIDER=2 (840 px map), SHADOW_TYPE=1 (4 PCF taps), COLORED_SHADOW on,
AO=1 AOSTEPS=5 (10 depth taps/px), AA_TYPE=2 (TAA, SELECTIVE_TAA_V2), V_CLOUDS=2 (2 noise taps/step), CLOUD_STEPS_AVG=10, CLOUD_REFLECTION on,
REFLECTION_SLIDER=2 (raymarch, RAYMARCH_STEPS=10 fixed, water/glass only), VOL_LIGHT=1 (depth godrays, GODRAY_STEPS=6 fixed), BLOOM on (3.0), DOF/MOTION_BLUR/CHROMA_ABER off, MATERIAL_GLOSS on.

## Option table (cost = relative GPU, "look" = visible change)
| Option | Cost | Look change | Notes |
|---|---|---|---|
| SHADOW_CASTING | High (extra geometry pass + PCF in every lit pixel) | Large | Shadow pass re-draws terrain; likely part of chunk-load dips |
| SHADOW_DISTANCE_SLIDER 0/1/2 | Dist 0 cheapest; 2 (255 m) heavy | Small at 0 | Texel density 0/qty2 (600px/150m) = 1/qty2 (840px/210m) = 4 px/m, so 0 only loses shadows at 75-105 m. Smaller range = less shadow geometry |
| SHADOW_QTY_SLIDER 1/2/3 | Fill/memory: res 420/840/1680 at dist1 | 1 is blocky (2 px/m at dist0) | Keep 2 |
| SHADOW_TYPE 1 | 4 taps vs 1 | Medium (soft vs pixelated) | keep 1 |
| SHADOW_BLUR | None (tap count fixed) | Softness only | free to leave |
| COLORED_SHADOW | Low-med (extra shadowtex0 + shadowcolor0 fetch) | Near zero (only tinted shadow under stained glass/water) | cheap win to disable |
| VOL_LIGHT 0/1/2 | 1 = 6-step depth godrays, low-med; 2 = shadow-map marching, high | 1: subtle at sun angles | 2 not worth it |
| AO / AOSTEPS | 2*AOSTEPS depth taps/px; high on 8 GB UMA | Medium (contact darkening) | 5 -> 4 near-invisible; TAA dither hides it |
| AO_STRENGTH | None | Look only | |
| REFLECTION_SLIDER 2 | Only on water/glass pixels; 10-step raymarch | Visible on water | 1 = flipped image, much cheaper, noticeable on water |
| REFRACTION / SUN_REFLECTION | Low | Small | |
| CLOUD_REFLECTION | Low-med (cloud march in water reflection) | Near zero | cheap win |
| V_CLOUDS 0/1/2 | 2 = dual-noise, 2 fetches per step; 1 = one; 0 = vanilla clouds | 2 vs 1: shape detail only | CLOUD_STEPS_AVG per sky pixel, runs in deferred pass |
| CLOUD_STEPS_AVG | Linear in sky pixels; High | 10->8 is dither noise only (TAA hides) | 7 is the floor |
| BLOOM / BLOOM_SAMPLES | Low-med; 3.0 -> 2.0 trivial | Near zero | |
| DOF | High | Large | keep off |
| MOTION_BLUR | Med | Medium | keep off |
| AA_TYPE 2 (TAA) | Low-med + history buffers (colortex3) | Large (shimmer) | keep; SELECTIVE_TAA_V2 minor |
| IMAGE_SHARPENING (CAS) | Low | Small, user chose it | keep |
| CHROMA_ABER | Low | Medium | off |
| WAVING | Vertex only, low | Small | |
| MATERIAL_GLOSS | Low | Very subtle | |
| FOG_ACTIVE / FOG_ADJUST | Negligible | Look | |
| COLOR_SCHEME / tone map / WATER_* | Negligible | Look only | do not touch |

## Presets (sidecar lines; booleans written as true/false)
### 1. same-look-cheaper
```
IMAGE_SHARPENING=true
V_CLOUDS=2
COLORED_SHADOW=false
CLOUD_REFLECTION=false
CLOUD_STEPS_AVG=8
AOSTEPS=4
BLOOM_SAMPLES=2.0
SHADOW_DISTANCE_SLIDER=0
```
### 2. balanced
```
IMAGE_SHARPENING=true
V_CLOUDS=1
COLORED_SHADOW=false
CLOUD_REFLECTION=false
CLOUD_STEPS_AVG=8
AOSTEPS=3
BLOOM_SAMPLES=2.0
SHADOW_DISTANCE_SLIDER=0
REFLECTION_SLIDER=1
VOL_LIGHT=0
```
### 3. max-fps
```
IMAGE_SHARPENING=true
V_CLOUDS=0
SHADOW_CASTING=false
COLORED_SHADOW=false
CLOUD_REFLECTION=false
AO=0
BLOOM=false
REFLECTION_SLIDER=1
VOL_LIGHT=0
AA_TYPE=2
```

## Horizon translator risks (UNVERIFIED, from GLSL only)
- shadow2D/sampler2DShadow (shadowtex0/1) needs a comparison sampler in naga/WGSL; preset 3 (shadows off) sidesteps it.
- `const int shadowMapResolution` / `shadowDistance` / `shadowDistanceRenderMul=-1.0` (only VOL_LIGHT=2) are Iris directives read from source; Horizon must parse them.
- `clouds = off` under `#if V_CLOUDS > 0` in shaders.properties (preprocessed properties).
- texture2DLod, gl_FragCoord dither, gaux2/gaux3 aliases, colortex3 history (TAA) need ping-pong buffer support. Test AA_TYPE and V_CLOUDS changes visually.
- Changing SHADOW_DISTANCE/QTY alters shadow map size: confirm Horizon reallocates it on reload.
- Chunk-load FPS dips are likely mesh upload plus shadow-pass geometry, not post effects; shadow distance 0 is the only option here that targets that.
