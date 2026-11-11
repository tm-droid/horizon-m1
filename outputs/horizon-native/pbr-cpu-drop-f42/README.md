# pbr-cpu-drop-f42 (u17 memory transform)

Status: **ready for r3 review, UNBUILT / UNTESTED in engine** (anchors, `git apply --check` alone and stacked with particle-cull-f42 + adaptive-upload-f42, std-only test generator; no cargo, no rustc, no game).
Base: r2 stage (needs sprite-compress, which r2 has: `SpritePixels`). Touches `crates/horizon-client-render/src/assets.rs` and `crates/horizon-client/src/game.rs`.

## What
- `RenderAssets.pbr_normals` / `pbr_specular` become `SpritePixels` (the lz4 holder the block sprites already use). Built exactly as before, then `shrink_to_fit` (the doubling `extend` left spare capacity) and wrapped.
- `Game::render` packs both next to `pixels.pack()` (background "Sprite packing" thread, raw copy dropped after).
- `prepare_renderer_textures` reads them with `.get()` (raw `Arc` before packing, lz4 decode after), so every rebuild path still works.
- Not a plain drop: `prepare_renderer_textures` runs again for device-loss recovery, `renderer_for` and the world handoff, so the data has to stay recoverable.

## Guarantees
- Byte-identical maps after decode (unit tests: round trip, empty). Empty maps (no LabPBR pack) cost nothing: `pack()` returns at once for length 0, `with_pbr` still sees an empty slice.

## Expected gain / risk
- Gain: 0 MB without a LabPBR resource pack. With one, up to 2 x 37.7 MB at 2303 layers x 64 px; lz4 keeps roughly 15-50 % of that, so about 20-60 MB freed (estimate, not measured).
- Risk: low. Decode on rebuild allocates the full map pair once (tens of ms). The pack thread peaks at one output buffer per map. Not compiled.
- Visual change: none.
