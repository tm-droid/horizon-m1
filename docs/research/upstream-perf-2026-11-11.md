# Upstream perf since fdc87ae (U3), 2026-11-11

Research only. Source: `gh api` on horizon-rust/horizon (read-only). Where a commit diff was fetched, applicability was tested with `git apply --check` / `patch -F3 --dry-run` against the pristine tree `outputs/horizon-src-nightly/nightly-2026-11-08-fdc87ae` (no daily7 stack applied, nothing compiled). Benefit figures are estimates, not measurements, unless stated.

## Upstream status
- Newest nightly: rolling tag `nightly`, "Nightly 2026-11-08 . fdc87ae", published 2026-11-08T15:14Z. Newest dated tag `nightly-2026-11-07`. No nightly since (checked 2026-11-11). Launcher 0.2.59 (2026-11-10T23:08Z) is newer than the nightly.
- main tip `f23176af` (2026-11-11T14:36Z): 4947 commits ahead of fdc87ae, 0 behind (~2105 non-merge in the date window; history is non-linear, so ancestry was decided by `git apply -R --check` on the pristine tree, see below).
- Hooks API: fdc87ae = 411, main = 415. The four additive bumps are native-hook reads (vehicle/passengers `de6cc998`, entity-by-UUID `a6204f1f`, `living_death_message` `03b7d245`, dedicated-server online mode `9f04ad53`). Hooks are additive, so hook-based mods built for 411 keep working; mods that pin a revision need the launcher's "Build anyway". Backporting render commits does not need the hook bump.
- Refactor churn on main (11-08/11-09) that makes later commits hard to cherry-pick: resource loader split into `game/resource_load*.rs` (`e38e4f6b`, `1f11377f` depends on it), `gfx/section_fade.rs` split (`46b6725e`), shaders/render-pipeline crate split (`5052d73c`, `83b9cfc1`), `surface_setup.rs` (`998b82e7`), horizon-hooks crate. Prefer commits dated 11-07 to 11-09 morning.

## macOS-specific upstream items since fdc87ae
- `702b0895` draw vanilla terrain flat on Metal at any section count (4 lines, gfx.rs). Same idea as our off-stack `up-metal-flat-fdc87ae`. Clean forward.
- `bec6ac64` legacy Intel Metal startup/terrain fix (wgpu-hal metal adapter/device). Intel only, SKIP.
- `3004b649` speckled players with Improved Transparency on Metal (oit_world.wgsl, 6 lines). Clean forward; only matters if Improved Transparency is on.
- `998b82e7` fall back when adapter cannot present (#13493). Not Metal-relevant, large gfx.rs rewrite, SKIP.
- `d6f88d24` GPU culling Auto: explicitly not offered on Metal.
- Nothing found for CAMetalLayer drawable count, frame pacing, or a submit thread. Issue #14015 (macOS camera jitter above 60 Hz) is still open with no fix commit. Our frame-bubble work (U8) has no upstream help.

## Ranked table

| # | commit | title | benefit (M1 8 GB) | difficulty / apply on pristine | conflicts with our patches | rec |
|---|---|---|---|---|---|---|
| 1 | 2a33c013 | branchless frustum culling, zero-copy Arc meshing regions, 3D upload priority | CPU frame + upload ordering; helps shaders and no-shaders; small-medium | medium; applies clean to pristine (4 files) | gfx.rs, resident.rs (up-padded-bounds, shadow-dedup, cloud-prep, a66f8fa2), game.rs (adaptive-upload) | BACKPORT |
| 2 | 562175df | meshes waiting for upload count against meshing room | bounds CPU-side mesh backlog memory, fewer stalls when flying; medium for 8 GB | medium; 1 hunk in streaming.rs + test fail at -F3 | none (no patch of ours touches streaming.rs); adaptive-upload is nearby in game.rs, semantic overlap, review | BACKPORT |
| 3 | 81a8d04a | cache flat compute bind groups | less per-frame wgpu bind-group creation on the Metal flat path; small-medium CPU | medium; 2 of 11 hunks fail in flat.rs (new binding_cache.rs is clean) | none (flat.rs untouched by us), gfx.rs +1 line | BACKPORT |
| 4 | 203b3ac8 | clouds: snap mesh origin to a grid, re-uploads 4x less in flight | small, flying/moving frames; no-shader and shader | easy; clean, clouds.rs only | none in clouds.rs (cloud-prep patches gfx.rs/pack_post.rs); read cloud-prep first | BACKPORT |
| 5 | 89733192 | sky octagon with half-planes (terrain.wgsl) | tiny fragment ALU saving, no-shader terrain | easy; clean, 7 lines | terrain.wgsl: emissive-bsearch, up-terrain-wire5 (different regions likely) | BACKPORT (cheap) |
| 6 | 36f20dd0 | startup reads each mod's content once | startup time with 16+ mods; no FPS | easy; clean (mods.rs, world_loading.rs) | none | BACKPORT (low priority) |
| 7 | 5ba542bf | startup reads content mods on threads at once | startup only | needs 36f20dd0 first (mods.rs hunk fails alone) | none | LATER |
| 8 | 7dda0df3 | fan out game CPU resource loads (startup) | startup with many resource packs | easy; clean in game.rs | game.rs is touched by 15+ of our patches; check hunks | LATER |
| 9 | 1f11377f | share entity models across startup loaders | startup only (not FPS); small RAM win | hard: targets `resource_load.rs`, missing at fdc87ae, hand port in 6 files | game.rs | LATER |
| 10 | 81c62c63 | reuse frame scratch buffers in renderer | fewer per-frame allocs; small | medium-hard; 3 of 10 hunks fail in gfx.rs | gfx.rs heavy (6+ patches) | LATER |
| 11 | fd70c6aa | reuse native sprite frames when sizes match | alloc churn on animated sprites; small | easy; clean | sprites.rs: anim-frame-compact (same area, may duplicate) | LATER |
| 12 | b5723fd3 | RGSS four taps at fractional mip level (terrain.wgsl) | no-shader terrain only, perf-neutral-to-slight, visual change | easy; clean | terrain.wgsl: emissive-bsearch, wire5 | LATER |
| 13 | 957ecaff | shader packs keep solid terrain in the compact layout (fix for #12448, PR #12449) | Memory: halves section vertices under packs (5.9 to 2.9 GB at RD 64). At our RD 12 expect only about 100-300 MB. Cost: about +1 to +1.7 ms GPU in gbuffers_terrain (their numbers, Apple silicon) | hard-ish: applies with fuzz 3 on pristine (8 files), but it is a gfx.rs layout flip + pack_atlas.rs GLSL pull + terrain.wgsl + mesher/packed.rs | gfx.rs (7 patches), pack_atlas.rs (fullbright-shaderpack), terrain.wgsl (emissive-bsearch, wire5) | SKIP for speed; LATER only if RAM pressure shows. We are GPU-bound under MakeUp (34 ms), +1 ms is a net loss at RD 12 |
| 14 | 5ec521bb | dynamic lights as uniforms, horizonTier | none for MakeUp (opt-in uniforms, extra per-frame uniform writes) | clean; we already have `up-pack-dynlights-fdc87ae` | pack_atlas/pack_uniforms/pack_entities (fullbright-shaderpack) | SKIP |
| 15 | 4a701935 | shadow program with no output keeps its water, no boat patches | none: the boats' water patches (`f9eb983b`, main only) are not in fdc87ae (no `water_patch` in tree), so the failure it fixes cannot occur. Our `up-shadow-nooutput-fdc87ae` is moot | 1 hunk fails in horizon-shaders post.rs; pack_post.rs shared with our patches | pack_post.rs: cloud-prep, composite-overwrite, pass-merge, up-rain-depth | SKIP |
| 16 | 702b0895 | vanilla terrain flat on Metal at any section count | possibly benefit on big RD when section count high; at RD 12 likely already flat | trivial, 4 lines | gfx.rs (same as up-metal-flat) | LATER (bench with up-metal-flat) |
| 17 | 3004b649 | speckled players, Improved Transparency on Metal | correctness only | trivial | none | LATER |
| 18 | 4543e2f4 | Opaque Ice performance option | tiny, ice only | 15 files, 1 hunk fails | mesher.rs/graphics.rs | SKIP |
| 19 | 9c1aca34 | Polytone colormap tints cost a twelfth to mesh | meshing CPU only if packs use Polytone/custom colormaps | medium; 9 hunks fail (environment.rs, mesher.rs) | none in those files | LATER (check if user packs use colormaps) |
| 20 | 2e88edc8 | preserve signed vertex and instance IDs | correctness for packs | clean | none | LATER |
| 21 | 998b82e7 | fall back when adapter can't present | no perf | rewrite of gfx.rs init | gfx.rs | SKIP |
| 22 | 55509cff / f9eb983b | boat water patches; unroll patch checks to avoid local array spill | f9eb983b ADDS shadow-pass varyings and per-fragment checks (a likely main-side shader-pack slowdown); 55509cff is the main-side cure. Neither is in fdc87ae | n/a | n/a | SKIP both; do not take f9eb983b |
| 23 | d6f88d24 | GPU culling Auto | not offered on Metal | n/a | n/a | SKIP |
| 24 | fec26a00, c2dd2d93, 9ddf48da | meshing/lighting allocation reuse, light scratch per worker | CPU alloc; small; reduces heap churn on 8 GB | fail on mesher.rs/light.rs/packed.rs | mesher/light not in our patches, but `packed.rs` is shared with 957ecaff | LATER |

Issue #12448: closed 2026-11-10T22:42Z by 957ecaff (PR #12449, merged 11-08 09:46Z). A maintainer review (ludovic111) accepted the +1 ms trade as default-on but asked for a discrete-GPU Vulkan measurement before default; the default shipped on main. Trade-off as above: wrong direction for a GPU-bound M1 at RD 12.

Not found upstream: any fix for the fdc87ae shader-pack GPU regression itself, any fix for our memory-stutter beyond 562175df and 076e9533 (already ported), any allocator change (no jemalloc/mimalloc/QoS commits except `fb9b1d35`, Linux hybrid CPUs only).

## Regression suspects: f42ef42 (2026-11-03) to fdc87ae under MakeUp
Facts from `docs/u7a-bench-2026-11-10.md`: with shaders off fdc87ae is 8-9% faster than f42ef42; with MakeUp it is 26-28% slower (GPU 34 ms vs 26 ms). So the regression is in the shader-pack path, not terrain or CPU. Between the two commits (about 3150 non-merge commits, mostly 11-04 to 11-06) upstream made an Iris-parity wave in the pack pipeline. Suspects, most to least likely:

1. `6a8ea6fc` (11-06) "shadow pass draws terrain outside the pack's near and far planes": for `shaders/` packs the shadow pass now culls by the box sides only (gfx.rs +59). More sections go into the shadow map every frame. MakeUp has shadows, so this directly adds vertex/raster work. Also `416704f1` (keeps edge columns), `cc6e8c65` (shadowDistanceRenderMul cube) and `7cc22c56` (margin 1.125) widen the set. `a66f8fa2` (draw only terrain that can shade the view) narrows it, and our `a66f8fa2-f42` backport plus shadow-dedup already target this. Check: log shadow-pass section/draw count per frame, f42 vs fdc87ae, or revert the gfx.rs hunk of 6a8ea6fc in a test build.
2. `8794c49a` (11-05) atlas sampler and `4c0ef1d7` (11-06) colortex sampler: both switch `mipmap_filter` to Linear (pack_post.rs, about 20 lines each). Trilinear on gtexture in gbuffers_terrain/entities and on every colortex read doubles texel fetches in minified areas. At 2560x1600 on M1 bandwidth this can be several ms. Cheapest A/B: set both `mipmap_filter` back to `Nearest` (two one-line edits; visual change only for fractional-LOD reads). Also `4b6cd5e2` (box-filter colortex mips, pack_post.wgsl +33) costs more per generated mip if the pack asks for mipmaps (MakeUp bloom/blur may).
3. `3c794c28` (11-05) "color-buffer reads in translucent draws": adds a snapshot copy of written-and-read buffers before translucent draws (`copies |= written` for the Translucent group). Full-screen copies per translucent group cost bandwidth on the M1. Depends on whether MakeUp's water/translucent programs read colortex above 3. Check: count copies per frame.
4. `4c44b577` + `02c05de4` (11-05/11-06): `shadowtex` read through `sampler2D` now uses translator helpers (4 gathers + 256ths rounding per tap). MakeUp declares `sampler2DShadow` for almost all shadow reads (8 declarations) and one `sampler2D shadowtex1`, so impact only if that one is on a hot path. Lower likelihood.
5. Terrain vertex precision snapping in the pack terrain vertex shader: `d652ec2f`, `9db60745`, `c9bc6104` (extra ALU per vertex, small) and `e0e48c36` (cutout alpha cut). Small.
6. For completeness (not in fdc87ae): 957ecaff compact pull (+1 ms), f9eb983b boat patches. Ruled out as the cause of the f42-to-fdc87ae gap because neither is in fdc87ae.

Our existing stack patches (composite-overwrite, pass-merge, shadow-dedup, cloud-prep) cover some of this region, so the residual gap with daily7 should be re-measured first; suspects 1 and 2 are the two quickest A/B tests (one test build each).

## Overlap with our patch files (paths grepped in outputs/horizon-native/*)
gfx.rs: 20 patches. pack_post.rs: 18. game.rs: 19. terrain.wgsl: 5. pack_atlas.rs / pack_uniforms.rs / pack_entities.rs: fullbright-shaderpack, up-pack-dynlights, makeup-dropped-light. resident.rs: up-padded-bounds, a66f8fa2. sprites.rs: anim-frame-compact. streaming.rs, mesher.rs, flat.rs, clouds.rs, light.rs, resource_load.rs: none.
