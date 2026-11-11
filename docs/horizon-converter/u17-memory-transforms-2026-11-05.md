# U17 memory transforms (2026-11-05)

Scope: two low-risk CPU-memory transforms from `memory-audit-2026-11-05.md` (candidates "LabPBR CPU copies" and "animation-frame CPU copy"), stacked on the r2 tree (`outputs/horizon-runtime/m1-performance-r2/candidate-source`, f42ef42 + r2 mods). Scratch-only: no cargo, no rustc (none on disk, so not even a parse check), no game run. Nothing in r2 was edited; patches were generated from copies and checked in a scratch git repo.

Dirs: `outputs/horizon-native/pbr-cpu-drop-f42/` and `outputs/horizon-native/anim-frame-compact-f42/` (prepare.py, edits.json, `<name>.patch`, README.md, build-plan.json, standalone_tests.py, LICENSE; same layout as particle-cull-f42).

Codec: `lz4_flex 0.14` is in Cargo.lock (also flate2, miniz_oxide) and is already a dependency of `horizon-client-render` (Cargo.toml:12, features std, safe-encode, safe-decode, checked-decode). No new crate, `--offline --locked` unaffected.

## 1. pbr-cpu-drop-f42

Verdict: ready for r3 (review, then build). A plain drop is NOT safe, so the transform compresses (reusing `SpritePixels` from sprite-compress, which r2 already contains) and keeps the data recoverable.

Readers traced (r2 tree):
- `assets.rs:107-108` fields; written once at `assets.rs:389-390` from `sprites.normals/specular` (built `sprites.rs:277-296`).
- Only reader: `game.rs:19835-19836` in `prepare_renderer_textures` (`with_pbr`, `gfx.rs:1409` copies into box mip chains and keeps its own copy in `PreparedTextures`; `normals.is_empty()` means no LabPBR).
- `prepare_renderer_textures` callers, i.e. every path that needs the data again: background handoff `game.rs:19573` (before any renderer, data still raw), `build_renderer` fallback `game.rs:19856` (reached from device-loss recovery `13672`, `renderer_for` `13708`, world handoff `20499`). Resource reload builds a fresh `RenderAssets`. Shader-pack switch, resize and screenshots use GPU textures only; they do not read the CPU maps. No reader in examples, tests, tools, xtask, mods, native shader code (WGSL reads the GPU arrays).
- Conclusion: the copy is needed on any renderer rebuild, so "drop after upload" would break device-loss recovery. Compress with on-demand decode instead (`.get()`), exactly as `pixels` does.

Change: 2 fields to `SpritePixels`, `shrink_to_fit` on both Vecs before wrapping, `.pack()` for both next to `pixels.pack()` in `Game::render` (`game.rs:14882`), `.get()` at the two `with_pbr` args, 2 unit tests (round trip, empty). 6 edits, 2 files, ~104 patch lines.

Expected saving: 0 MB with no LabPBR pack (empty Vecs, `pack()` returns for length 0). With one: up to 2 x 37.7 MB raw (2303 layers x 64 px, audit); flat filler and smooth normals compress well, so about 20-60 MB freed (estimate, unmeasured; check the log line `LabPBR maps at N px`). No FPS effect.
Risk: low. Not compiled. Decode on rebuild is a one-off allocation of the pair. Visual change: none (byte-identical).
Ready for r3: yes, but only worth benching with a LabPBR pack in the instance; otherwise it is a no-op.

## 2. anim-frame-compact-f42

Verdict: ready for r3 (review, then build), more invasive than #1.

Readers traced (r2 tree):
- `sprites.rs:9` field; built `sprites.rs:265-271` (`resized`, every frame of every layer resampled to layer size); pushed pre-layout at `sprites.rs:679`; copied for layer duplication at `sprites.rs:517-522`; `finish_without_pixels` empties it (`sprites.rs:257`); moved into `RenderAssets.animations` (`assets.rs:~387`).
- Pixel readers: `animate.rs:108` (`SpriteAnimator::new`, once per renderer build via `gfx.rs:2684`); `sprites.rs:45-52` `resized_pixels` (tests only); tests `animate.rs:651,696,876`, `gfx.rs:11126`, `sprites.rs:1186,1215`; example `sprite_cache_parity.rs:27-28`.
- Non-pixel readers (layer/clip only, unaffected): `mesher.rs:621-623`, `block_sprites.rs:121`, animator tick `animate.rs:369-381` (`sprite.animation.layer/blend`).
- Important finding: the animator keeps `animation.clone()` per sprite (`animate.rs:144`, field `animate.rs:28`), which pins the `Arc` of raw frames for the renderer's whole life. Compressing only `RenderAssets.animations` would free nothing, so the store is shared by every clone and compressed in place.
- Rebuild paths (device loss, second window, world handoff) call `Renderer::new` again, which calls `SpriteAnimator::new` and reads frames via `frames()`, decoding one animation at a time.

Change: `SpriteAnimation.frames` becomes `Arc<AnimationFrames>` (raw until packed, then one lz4 block + per-frame lengths, shrunk to fit). `pack_animations()` is called in `Renderer::new` right after `SpriteAnimator::new` (`gfx.rs:2684`), one "Animation packing" thread, claim flag per store so repeats are cheap. `pixels()` now returns `Vec<u8>`, new `frames()`; 5 call sites adjusted (names `sheet`, because `animate.rs:102` already has a local `frames`). 4 unit tests in a new `animation_frames_tests` module. 11 edits, 3 files, ~312 patch lines.

Expected saving: about 12-33 MB (audit: 15-40 MB CPU frames; whole-pixel upscaled frames are runs of equal texels, lz4 ratio estimated >= 6x; unmeasured, the audit's suggested layer/frame count log was not done). The GPU chain buffer (audit part b) is untouched. No FPS effect; one short background compress after renderer build.
Risk: low-medium. `pixels()` signature change (compile-checked only by reading; no rustc available), thread created per renderer build. Visual change: none (byte-identical decode, tests assert equality and `resized_pixels` equality).
Ready for r3: yes, after a real `cargo check` and the new tests; bench RSS/swap and eyeball animated water/lava/fire/kelp.

## Apply checks (scratch git repo, files copied from the r2 tree)
- `git apply --check` alone: pbr ok, anim ok, particle-cull ok, adaptive-upload ok.
- pbr + anim together: ok.
- u15 (particle-cull + adaptive-upload) applied first, then pbr, anim, both: all ok.
- u17 (both) applied first, then `git apply --check` of both u15 patches: ok.
- `prepare.py render()` on the r2 files reproduces the patch bytes and each reviewed output hash; re-apply is refused ("already applied"); renders also pass on the u15-stacked game.rs (anchors only).
- `standalone_tests.py WORKSPACE OUT.rs` runs on the transformed tree (anchor presence checks pass) and writes std-only Rust tests with an RLE stand-in for lz4; generated files were not compiled or parsed (no rustc on disk).
- Overlap: pbr and anim touch disjoint files; game.rs hunks (14882, 19835) are far from adaptive-upload (16275, 17839, EOF) and particle-cull.

## Not done / caveats
- No cargo check, no `cargo test`, no rustc parse check: all Rust is reviewed by reading only. First build may need small type fixes. Reviewed for shadowing (`frames` in `SpriteAnimator::new`), `Clone` closure for spawn fallback, `Send + Sync` of the store, deref coercion at `with_pbr`.
- Both transforms assume sprite-compress is in the tree (it is in r2; `R2_WITH_SPRITE` note in build-m1-performance-r2.py is for pristine stages).
- Integration (r3): add `pbr-cpu-drop-f42` and `anim-frame-compact-f42` to PERF_MODS after sprite-compress; order against the u15 ports is irrelevant. Build/test commands are in each build-plan.json.
