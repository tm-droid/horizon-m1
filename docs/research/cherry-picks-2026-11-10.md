# Upstream cherry-picks onto fdc87ae + daily3 stack (2026-11-10)

Note: fdc87ae..main has ~27k commits and history is non-linear, so `merge-base --is-ancestor` is unreliable. In-base was decided by `git apply -R --check` on the pristine tree.

## Already in base (content)
| Item | Upstream | Status |
|---|---|---|
| #11577 HDR lighting 15% GPU, HDR off | e3b3159901 (PR #11596; e979fbc2ad is its earlier version) | in base (reverse-apply clean) |
| #11294 worker pool vs perf cores | 81261cc98d (PR #11692) | in base (perflevel0 code present) |

## Candidates (apply in this order)
| # | Patch | Upstream | In base | Applies | Conflicts / overlaps | Risk | Benefit on M1 8 GB under MakeUp |
|---|---|---|---|---|---|---|---|
| 1 | up-dimension-swap | e1434f2e Less dimension-swap overhead; cached raycast chunk lookups | no | yes | none (disjoint from stack) | low | Targets the 340-1000 ms stall per dimension change; does not fix 2.5-3 s first shader compile. Overlaps nothing in dimension-warm. |
| 2 | up-lod-locks | 2d708ace Far terrain: render thread try-locks sampling/meshing queue instead of waiting | no | yes | none | low | Removes render-thread lock waits; only matters with far-terrain/LOD on. |
| 3 | up-tick-shrink | 076e9533 Scheduled-tick queues release memory once drained | no | yes | none | low | Memory only (8 GB box); no FPS effect. |
| 4 | up-metal-flat | 702b0895 Metal always draws vanilla terrain flat (min_sections=0) | no | yes | textual none; behaviour overlaps terrain-single-draw/fullbright-shaderpack (same gfx.rs region touched by 5 stack patches) | medium (behaviour change) | Mostly fixes Intel-Metal leaf dropping; M1 gain unproven (fewer draw calls, same GPU work). Optional; benchmark first. |
| 5 | up-padded-bounds | 33c96ac1 Padded mesh bounds for CPU terrain occlusion (resident bounds reuse) | no | yes | 3-way clean vs cloud-prep, shadow-scratch, emissive-bsearch, shadow-dedup, anim-frame-compact, fullbright-shaderpack (gfx.rs touched by all) | medium (culling correctness: popping/holes) | CPU-side culling accuracy; little help when GPU-bound. |
| 6 | up-terrain-wire5 | 3d5216e7 Terrain vertex outputs in 5 locations not 12 (TerrainWire) | no | yes | 3-way clean vs emissive-bsearch (terrain.wgsl). visbuffer.wgsl still uses TerrainOut, which upstream keeps | medium (WGSL; naga/pipeline errors are runtime) | Upstream numbers are RX 580 (+13..21%). M1 is TBDR so gain smaller but vertex-stage bound shaders benefit; best GPU candidate. |
| 7 | up-rain-depth | cca1842d Rain/snow never write depth (Iris behaviour) | no | yes | one comment-only hunk in pack_post.rs (HEAD has clouds_off lines from stack); resolved keeping stack lines + new comment. Also touches pack-pass code of pass-merge/composite-overwrite/terrain-single-draw (clean) | low | Fixes pack depth reads of rain columns; may reduce overdraw/rain cost under MakeUp. rain.depth property now unread (field kept). |
| 8 | up-varying-prune | d84e8fa4 Varying the fragment stage never reads takes no location (new translate/varyings.rs) | no | yes | 3-way clean vs fullbright-shaderpack | medium (588 lines, GLSL translation) | Avoids location-limit failures; fewer interpolants for MakeUp-style packs. Needs shader-crate tests run. |
| 9 | up-varying-struct | b4b59960 Struct defined in a varying's declaration counts as varying | no | yes | 3-way clean; apply after up-varying-prune | low | Pack compatibility fix. |
| 10 | up-shadow-nooutput | 4a701935 Shadow program with no output keeps water, without boats' patches | no | yes | post.rs test-module conflict: upstream parent had extracted buffer_blend_tests/material_variant_tests, base keeps buffer_blend_tests inline. Kept base's inline module; dropped orphan buffer_blend_tests.rs. lifecycle_tests extraction kept. Non-test hunks auto-merged with pass-merge/composite-overwrite/terrain-single-draw/shadow-dedup region | medium-high (shadow path, adjacent to shadow-dedup) | Only matters if a pack has a shadow program without outputs; shadow-dedup may already cover the cost. |
| 11 | up-pack-dynlights | 5ec521bb Horizon dynamic lights as uniforms, horizonTier for terrain/entities | no | yes | 3-way clean vs fullbright-shaderpack (pack_uniforms.rs) | medium | Feature, no perf benefit for MakeUp (adds per-frame uniforms). Optional. |

## Not produced
| Upstream | Why |
|---|---|
| 1f11377f entity models shared across startup loaders | touches crates/horizon-client/src/game/resource_load.rs which does not exist in base (prerequisite refactor missing); startup-only gain |
| PR #12449 957ecaff5f (#12448 compact layout under packs, open) | open, unreviewed, maintainer asked for Vulkan measurement; conflicts in gfx.rs and render_control.rs; trades +1 ms GPU for section memory |

## Recommended stack order (after daily3-stack)
Low risk first: up-dimension-swap, up-lod-locks, up-tick-shrink, up-rain-depth, up-terrain-wire5, up-varying-prune, up-varying-struct, up-padded-bounds.
Optional, benchmark first: up-metal-flat, up-shadow-nooutput, up-pack-dynlights.
Patch files were generated sequentially in the table order; changing order may need re-diffing. None were compiled.
