# U7a: daily8 candidates (prepared, not built)

Checked with `git apply --check`/apply on a clone of pristine fdc87ae + daily7 (33 patches), no cargo run (benchmark was running). Each applies alone on daily7 AND all together in the order below (a-e, then h1-h4, then A/B f, g). Layout follows build-fast-fdc87ae.py: `<name>-fdc87ae/<name>.patch`.

| dir | source | alone | combo | files touched | risk | gallery |
|---|---|---|---|---|---|---|
| up-frustum-regions | 2a33c013 | Y | Y | gfx.rs, gfx/resident.rs, streaming.rs, game.rs | low-med (Box->Arc, hand-ported far closure; 1 hunk dropped, already covered by shadow-scratch) | N (upload order only) |
| up-mesh-backlog | 562175df | Y | Y | streaming.rs, game.rs | low (bounded.rs refactor + test skipped) | N |
| up-flat-bindgroups | 81a8d04a | Y | Y | gfx.rs, gfx/binding_cache.rs (new), gfx/flat.rs | med (hand-ported; needs compile) | N (check GPU-culling still draws) |
| up-cloud-reupload | 203b3ac8 | Y | Y | clouds.rs | low | Y quick (clouds near edge/inside layer) |
| up-sky-octagon | 89733192 | Y | Y | terrain.wgsl | low (same math) | N |
| ab-shadow-cull-revert | reverse of 6a8ea6fc | Y | Y | gfx/pack_post.rs | A/B only; reintroduces #10403 | Y (MakeUp caves/high altitude shadows) |
| ab-nearest-samplers | reverse of 8794c49a+4c0ef1d7 | Y | Y | gfx/pack_post.rs | A/B only; mip blend off; unit tests atlas_mip/colortex_mip_blend fail | Y (distant terrain, bloom/DoF) |
| thread-cap (existing) | memory-stutter doc | Y | Y | horizon-threads/lib.rs, lan/{chunks,io_pool,mod}.rs, vanillagen/lod.rs, client-render/lod.rs, save.rs | med (fewer far LOD/decoration threads, may slow chunk fill) | N |
| dimension-warm (existing) | memory-stutter doc | Y | Y | gfx.rs, gfx/pack_post.rs, gfx/pack_warm.rs, game/shader_packs.rs | med (transient 150-450 MB RAM on 8 GB, ~0.2 s hitch x2) | N (check pack loads after switch) |
| gpu-a (existing) | in-house | Y | Y | gfx/pack_post.rs | med-low (merges gbuffers passes; encoder-locked errors) | Y (sky seams, outline, split-pack cutout) |
| gpu-e (existing) | in-house | Y | Y | gfx/pack_post.rs | med (skips B->A copies; stale data / TAA ghosting) | Y (TAA, reflections, exposure) |

## Off-stack patches (h)
No port needed: all four apply unchanged on daily7 and after the a-e candidates (their dirs untouched; no -d7 files). No reason for being dropped is recorded in the repo (they were authored on daily4 and never added to a daily stack; thread-cap, dimension-warm were never compiled/run, see their NOTES).
- thread-cap: `fast_cores()` caps worker pools to Apple P-cores (M1: 4); LAN encode pool threads beyond default skip jobs unless a listener is open; network threads utility QoS until listening; far decoration 3->2, far LOD 5+2->1+2, region compress 4->2. Aimed at memory/CPU contention stutter.
- dimension-warm: after load, warms the other dimension's shader pack pipelines on a background thread (cancelled on real switch) so the first portal trip skips the 2.5-3 s compile; v2 trims main-thread work. Metal cache is system-wide, so it only matters once per fresh build/dimension.
- gpu-a: sky + solid + cutout gbuffers (and lines + clouds) share one render pass when compatible; saves tile store/reload (~1-1.5 ms per merged boundary at 2560x1600).
- gpu-e: skips start-of-frame B->A buffer copies nothing reads (~0.3-0.5 ms each).

## Proposed order
1. `daily8-cand-stack.txt` = daily7 + up-frustum-regions, up-mesh-backlog, up-flat-bindgroups, up-cloud-reupload, up-sky-octagon, thread-cap, dimension-warm, gpu-a, gpu-e. Build once, `cargo check`/tests first (all candidates uncompiled; flat-bindgroups and frustum-regions most likely to need a compile fix).
2. If a regression appears, bisect by halves: safe set = up-sky-octagon, up-cloud-reupload, up-mesh-backlog, up-frustum-regions; GPU set = up-flat-bindgroups, gpu-a, gpu-e; memory/threads set = thread-cap, dimension-warm.
3. A/B on top of the best stack, one at a time: ab-shadow-cull-revert first (top MakeUp suspect), then ab-nearest-samplers; gallery check before keeping either.
