# ab-shadow-cull-revert (A/B experiment; NOT in daily8 stack)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/gfx/pack_post.rs (1 line).

## What
Upstream 6a8ea6fc ("shadow pass draws terrain outside the pack's near and far planes", fixes #10403) added `ShadowView.depth_planes` and made `shadow_box()` ignore the near/far planes of the shadow cull projection for shaders/ packs, so the shadow pass draws far more terrain (everything along the light ray, from 535 blocks behind to ~120 before the shadow camera, bounded only by box sides). fdc87ae already contains it. This patch sets `depth_planes: true` in `PackPost::shadow_view` (the pack path), which restores the old behaviour: sections outside the pack's shadowNearPlane/shadowFarPlane are culled. Native (Horizon's own) path already uses true.

## Why / expected effect
Top suspect for fdc87ae being 26-28% slower on GPU under MakeUp than f42ef42. Expected: fewer shadow-pass draws and vertices; shadow map GPU time down.

## Visual risk (gallery needed)
Reintroduces #10403: with packs setting tight planes (e.g. 0.05/256) terrain toward the light (caves under a surface, high altitude) can be missing from the shadow map -> missing shadows/light leaks in those scenes. Compare MakeUp cave + high-altitude scene.
