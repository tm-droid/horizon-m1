# composite-overwrite-f42

Not compiled. Written 2026-11-06 (R20). Apply after the 12 r3 patches (it also applies to the pristine stage).

## What
Shader-pack quad passes (prepare, deferred, composite*; everything before `final`) open their colour attachments with `LoadOp::Load` (`gfx/pack_post.rs`, the loop in `render`, pristine line 4199). On Apple's tile-based GPU a Load reads the whole old attachment from memory into tile memory before the pass draws. When the pass is proven to write every pixel, this patch uses the existing `overwrite` ops (`LoadOp::Clear`, which costs no memory read) instead.

A pass counts as `overwrites` only when all of these hold:
- the vertex stage is our quad unmoved: its only mention of `gl_Position` is `gl_Position = ftransform();`, `gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;` or `gl_Position = gl_ProjectionMatrix * gl_ModelViewMatrix * gl_Vertex;` (whitespace ignored). Horizon's composite matrix maps the quad onto the whole target (`translate/rewrite.rs:72`, `hz_quad`);
- the fragment module has no `discard` (naga `Statement::Kill` anywhere in its functions or entry points);
- no colour target blends;
- no `scale.<program>` viewport; not the final pass, not a sink, no geometry.

Every other pass keeps `LoadOp::Load` exactly as before.

## Files
- `crates/horizon-shaders/src/post.rs`: new `PostProgram::covers` field, `covers_target()` helper, a unit test.
- `crates/horizon-client-render/src/gfx/pack_post.rs`: new `Pass::overwrites` field, `kills()` helper, the load-op choice.

## Why (M1)
MakeUp Ultra Fast 9.6 qualifies for all five of its quad passes: prepare (colortex0), deferred (1, 4), composite (0, 1, 6), composite1 (1), composite2 (1, 3, 5). All use `gl_ModelViewProjectionMatrix * gl_Vertex`, none discards or blends, and there is no `scale.`. That is about 9 attachment loads per frame, about 63 bytes per pixel. At 2560x1600 that is about 250 MB per frame that no longer has to be read. On 68 GB/s that is an estimated 1-3 ms of the ~25 ms GPU frame. This is not measured. Apple's lossless framebuffer compression may lower the real gain.

## Look risk
None for passes that pass the proof: every pixel is written by the fragment shader whatever the old contents were. Residual edge cases:
- the matching `gl_Position` assignment sits inside an `if` whose other branch leaves the position unset. Then the unshaded pixels become transparent instead of keeping stale data. GL leaves that case undefined too.
- naga output defaults: outputs a shader never assigns are zero-initialised by naga with Load and with Clear alike, so they do not differ.

## Verify
`cargo test -p horizon-shaders only_the_unmoved_quad_covers_the_target`, then A/B with MakeUp (GPU p99, avg FPS), plus a screenshot diff of the bench scene (it should be pixel-identical). With `HORIZON_SHADER_PACK_TIMING=1` (per-pass GPU timestamps, `gfx/pack_timing.rs`), the prepare/deferred/composite* pass times should drop.
