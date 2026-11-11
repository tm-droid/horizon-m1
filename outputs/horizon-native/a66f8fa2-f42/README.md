# a66f8fa2-f42

Status: UNBUILT / UNTESTED. Copy of `docs/horizon-converter/research/R4-patches/a66f8fa2-port.patch` (gfx.rs, gfx/resident.rs,
gfx/native_post.rs, gfx/pack_post.rs).

## What
Upstream a66f8fa2: for Iris-format packs, the shadow pass culls to sections whose shadow can fall into the camera view (frustum
stretched toward the light, `ShadowCull`). Horizon's native packs keep `view_casters: false`. Upstream tests dropped (need `every_face`).

## Why / saving
Fewer sections/draws in the shadow pass (MakeUp runs it every frame). No memory change; CPU/GPU time only. Unmeasured upstream.

## Look risk
Medium: a wrong plane silently drops shadows. Test low sun while turning, sun ahead, looking straight up/down vs the unpatched build.

## Verify
`git apply --check` after shadow-scratch (done in r4 stack); then build and A/B shadows.
