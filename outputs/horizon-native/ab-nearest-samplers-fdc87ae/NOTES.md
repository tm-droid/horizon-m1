# ab-nearest-samplers (A/B experiment; NOT in daily8 stack)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/gfx/pack_post.rs (2 lines).

## What
8794c49a (atlas) and 4c0ef1d7 (colortex) gave shader-pack reads of the block atlas and colortex buffers a sampler with `mipmap_filter: Linear` (blend two nearest mip levels, as Iris 1.11.7 does). fdc87ae contains both. This patch sets `mipmap_filter: Nearest` in both samplers (`atlas_sampler`, `buffer_sampler`), which is sampling-equivalent to the old `NearestRepeat` atlas / `Linear` colortex samplers (mag/min filters unchanged). Minimal form: no SamplerKind/bind-layout changes; the Atlas kind stays "Filtering" binding type (a nearest sampler is legal there).

## Visual risk (gallery needed: YES)
Only affects packs reading these via sampler2D in composite/final/gbuffers custom textures (and anything calling textureLod at fractional levels or auto-mip on the atlas through this path): trilinear -> nearest-level changes visible at mip transitions (banding on distant terrain textures, colortex blur chains such as bloom/DoF mip pyramids look slightly blockier). Vanilla (non-pack) rendering is unaffected. Compare MakeUp: distant terrain texture shimmer, bloom softness. Also: unit tests `atlas_mip_tests` and `colortex_mip_blend_tests` will fail with this patch (A/B only; do not run cargo test with it).

## Expected effect
Cheaper texture sampling in post chain (bilinear mip taps -> fewer ALU/sample units per tap). Probably small; this is the second suspect for the MakeUp GPU regression.
