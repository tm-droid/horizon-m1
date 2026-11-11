# anim-frame-compact-f42 (u17 memory transform)

Status: **ready for r3 review, UNBUILT / UNTESTED in engine** (anchors, `git apply --check` alone and stacked with particle-cull-f42 + adaptive-upload-f42, std-only test generator; no cargo, no rustc, no game).
Base: r2 stage. Touches `crates/horizon-client-render/src/sprites.rs`, `gfx/animate.rs` and `gfx.rs`. `lz4_flex` is already a dependency of horizon-client-render and in Cargo.lock (no new crate).

## What
- `SpriteAnimation.frames` becomes a shared `AnimationFrames` (raw `Arc<Vec<Vec<u8>>>` until packed, then one lz4 block plus per-frame lengths). Clones share it, including the clone the `SpriteAnimator` keeps (`animate.rs` `Sprite.animation`), so packing frees the single copy.
- `pack_animations(&[SpriteAnimation])` runs right after `SpriteAnimator::new` in `Renderer::new` (the animator has then built every frame's mip chain on the GPU side). One "Animation packing" thread packs the not yet claimed stores one after another; repeat calls cost one atomic read per animation.
- `SpriteAnimation::pixels` now returns an owned `Vec<u8>`; new `frames()` returns all frames. `SpriteAnimator::new` and three tests use `frames()`; the HUD resize and parity example are unchanged in effect.

## Guarantees
- Byte-identical frames after decode (unit tests: round trip, resized_pixels equal, shared clones, unequal and empty frame lists). The animator only reads `layer` and `blend`/clip after construction (`animate.rs` tick), never the pixels.

## Expected gain / risk
- Gain: roughly 12-33 MB (the audit estimates 15-40 MB of CPU frames; frames upscaled by whole pixels are runs of equal texels and lz4 keeps about 1/6 or less). Not measured: the audit asks for a one-off count of animated layers first.
- Risk: low-medium. API change to `pixels()` (5 call sites edited: animator build, three animate tests, one gfx test; the rest compile unchanged against `Vec<u8>`, the parity example hashes it the same as a slice). Not compiled. A rebuilt renderer decodes each animation once (a few MB at a time).
- Visual change: none.

## r3 review fixes
- `sprites.rs` test `animation_boundaries_and_repeated_frames_do_not_depend_on_render_rate` built `SpriteAnimation { frames: Arc::new(vec![..]) }`; it now uses `Arc::new(AnimationFrames::new(Arc::new(vec![vec![], vec![], vec![]])))` (the real constructor).
- `resized_pixels` reads through the shared store (`self.frames.get()`) instead of `pixels()`, so a packed animation is decoded once and the frame is not copied out.
