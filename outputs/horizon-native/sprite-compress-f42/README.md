# sprite-compress-f42

Verdict: **needs-adaptation (done)**. Status: UNBUILT / UNTESTED (static symbol and anchor checks only; no cargo, no game run).

- Origin: horizon-rust/horizon main 2c9dac6b
- Hook API: none (plain engine source)
- What: RenderAssets.pixels becomes SpritePixels: raw until a renderer exists, then lz4-compressed on a 'Sprite packing' thread and the raw Vec dropped; get() uncompresses for a rebuilt renderer. Game::render calls self.pack.render.pixels.pack() next to the existing GUI atlas pack_pixels(); prepare_renderer_textures/build_renderer use .pixels.get().
- Why: The GPU already holds the block texture array; the CPU copy (about 21 MB with default resources) only serves a renderer rebuilt later. Frees RSS on an 8 GB machine.
- Expected gain on M1: About 20 MB less resident memory with default resources (upstream figure; the user's resource pack may differ). One-off lz4 pass on a background thread shortly after the first frame. No FPS gain expected; helps swap pressure marginally.
- Risk: Low-medium. Upstream hunk 2 (type block) and the test hunk did not apply to f42 (RenderAssets gained a `generation` field and a GENERATION static); re-anchored on `fn invalid(`, and the test is appended as a separate `mod sprite_pixels_tests` at EOF. Every other RenderAssets.pixels user in f42 was grepped: game.rs (2 sites), sprite_cache_parity.rs, resource_memory.rs (len() kept). Not compiled. Device loss or a resource reload decompresses once (about 21 MB alloc + lz4 decode, tens of ms).
- Visual change: None (byte-identical pixels after decompress; unit test included).
- Files: crates/horizon-client-render/src/assets.rs, crates/horizon-client/src/game.rs, crates/horizon-client/examples/sprite_cache_parity.rs

- 2026-11-05 re-anchor: game.rs anchors updated to the current launcher stage tree (rustfmt-wrapped call sites, no 'compressed' comment). Old edits/patch kept as *.bak-2026-11-05. Patch is now against the stage tree.

## Use
`python3 -I prepare.py --workspace <owned copy of f42> --record <new.json>` or, from build-m1-performance.py,
`mod.render(relative, bytes)` for each of `mod.FILES` plus `mod.NEW_FILES`. Anchors must match exactly once; files identical
to pristine f42 must hash to the reviewed output (`edits.json`). `sprite-compress.patch` is the same change as a unified diff (`git apply -p1`).
Verified: transform and patch apply cleanly to a clonefile copy of pristine f42 in the scratchpad; nothing under
launcher-data/native/source or candidate-source was touched.
Contract and plan: `hook-contract.json`, `build-plan.json`.
