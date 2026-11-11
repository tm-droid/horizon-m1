# Issue 2: eleven CEM mobs skip per-part textures on the nightly build

Root cause: the fdc87ae CPU CEM mob renderer ignores a part's explicit `texture` path and draws every bone with the body sprite. Codex's r10 patch (`outputs/horizon-native/cem-part-texture-f42/cem-part-texture.patch`, 446 lines, touching `horizon-optifine/src/cem/model.rs`, `mobs/cem.rs`, `mobs/render.rs`, `block_entity_cem.rs`) fixes this. Its follow-up `cem-part-variants-f42/cem-part-variants.patch` restores per-part colour rules (dyed sheep rendered white without it).

Status on fdc87ae: neither applies. `git apply --check` fails at `crates/horizon-client/src/mobs/cem.rs:113` (the `CemLayer::build` / `layer_suffix` block) for part-texture, and at `mobs/render.rs:1391` (`PartPaint`) and `cem.rs:1023` for part-variants. Both need a rebase onto fdc87ae; no pack-side fix exists, because the texture path in the jem is the correct data and the client drops it.

Patch sketch: re-apply the three failing hunks by hand against the new code. In `cem.rs` keep the "texture = None when layer suffix differs" rule but resolve each bone's texture after it. In `render.rs` carry the bone sprite through `PartPaint` as in the original. Then re-run the two Rust tests the patches ship.

Not done here: no rebase, to avoid colliding with the U4 rebase of daily-compat on the same files (cem.rs, render.rs).
