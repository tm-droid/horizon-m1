# fix-cem-part-texture (on fdc87ae + daily4 stack)
Bugs: sheep wool/horns black, iron golem head wrong, 11 CEM mobs "per-part textures aren't drawn".
Cause: horizon-optifine/src/cem/model.rs ~276-280, ~406 set bake.unread for bones with `texture`/`sprites`; such bones were drawn with the body texture UVs.
Fix: ports cem-part-texture-f42 onto the cem-binding base (cem.rs hunks hand-ported), plus render.rs `wool_tint` so FA's box-less sheep_wool.jem keeps dye colour.
Apply: after daily4 stack, `git apply fix-cem-part-texture.patch`.
UNVERIFIED: cargo was not run (shared target dir, 8 GB). Needs `cargo test -p horizon-optifine -p horizon-client`.
Not covered: `sprites` key bones still warned/skipped. Goat black parts not reproduced (goat.jem has no per-part textures; UV texels valid).
