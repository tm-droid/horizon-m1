# colortex-lazy-b-f42

Status: UNBUILT / UNTESTED (no cargo run). Touches `gfx/pack_post.rs`, `gfx/pack_shadow.rs`.

## What
Backport of upstream 840a42cf ("a buffer gets its second texture only when a pass flips it"). New `PackPost.doubled` mask:
a colortex gets a separate B texture only if a prepare/deferred/composite/shadowcomp render program draws into it (writes its
"alt" side) or flips it. Every other buffer's B is a clone of its A texture (same data, no copy). Shadowcolor buffers get the
same treatment through `ShadowTargets::new(.., doubled, ..)`.

## Differences from upstream (f42 is older)
- Three hunks did not apply: the "three-channel start" and "alt_clears" skips (f42 has neither; its clears attach only the
  main side, `view(main, b, false)`) and the `linear` arg of `ShadowTargets::new`. The shadow call/notes/log hunk was hand-ported.
- Upstream test file `single_side_tests.rs` dropped: it needs `destination_tests::Fixture` (private in f42, only child modules can use it).
- Hand-checked in f42: every `[0,1]`/alt use is `view(.., alt)`; the only alt=true attach is shadowcomp (`t.color(buffer, true)`), which is counted via `pass.written`.

## Why / saving
Upstream: 35-224 MiB at 3440x1440. R3 estimate at 2560x1600: ~60-150 MiB when a shader pack is on. Zero effect with shaders off.

## Look risk
None expected (same data). Real risk is wgpu validation: a texture attached twice in one pass, or a missed alt writer leaving B == A
(then ping-pong reads == writes). Symptom: validation error / black or stale composite buffers.

## Verify
`git apply --check`, then build. Run MakeUp Ultra Fast plus one heavier pack; log line "shader pack: colortex buffers ... with two
textures ..." must appear and screenshots must match the unpatched build. Compare `horizon-ctl memory` before/after.
