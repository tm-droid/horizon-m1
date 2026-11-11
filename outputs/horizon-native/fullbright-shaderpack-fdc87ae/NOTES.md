# Fullbright with shader packs

Patch: fullbright-shaderpack.patch (`patch -p1` from source root). NOT built or tested (game was running).

## Design
Fullbright now reaches the pack as a per-frame uniform, `hz_fullbright` (float 0/1):
- translate/mod.rs: a gbuffers program whose `GbuffersInputs::body` mentions `hz_fullbright` gets
  it added to the frame uniform block (same mechanism as gbufferPreviousModelView for at_velocity), declared or not by the pack.
- pack_uniforms.rs: `PackInputs.fullbright`; `hz_fullbright` added to NAMES (before cloudTime, so the
  `ends_with` test still holds) and filled in `value()`. `nightVision` = max(frame, 1.0) while fullbright.
- gfx.rs: at the pack `post.run` call, `PackInputs { fullbright: self.fullbright, ..frame.pack }`. No game.rs change:
  the renderer flag the mod already sets is the source.
- pack_atlas.rs (terrain, also terrain_parts clones) and pack_entities.rs (entities): prelude
  `hz_MultiTexCoord1.x = max(float(hz_v_light.y), 240.0 * hz_fullbright)`. MultiTexCoord2 copies it; vaUV2 follows.
  Sky light (.y) untouched. Weather, lines, sky preludes untouched.

## Why
Toggle takes effect next frame, no pack reload. Off cost: one uniform write + one max() per vertex.

## Risks
- Untested/uncompiled. Check: `cargo test -p horizon-client-render --lib pack_uniforms` and pack_post tests (translate uniform lists).
- Packs reading block light in the fragment stage from other sources (not lmcoord) are unaffected.
- Shadow programs also get the uniform; harmless.
- Changing block-light of terrain via vertex prelude means shaders reading `at_midBlock.w` (block table) are unchanged.
- Fixture tests with hand-written `GbuffersInputs` bodies don't mention hz_fullbright, so no uniform is added for them.
