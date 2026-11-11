# Issue 6: charged creeper shell white under MakeUp

Evidence from Codex's runs (`docs/horizon-converter/open-compatibility-2026-11-07.md` lines 25, 35, 48): with shaders off the r8 and r9 shells are blue; with MakeUp both are white. Restoring only vanilla's transparent charge texture under MakeUp (ticket 198) was still white. So the texture is not the cause: the shader-pack path for the energy-swirl overlay (`crate::gfx::ENERGY_SWIRL_OVERLAY`, `mobs/render.rs`, the block that draws `layer_poses` with `fs_energy_swirl` colour bytes) is. It is the entity span split of the shader pack, which cannot be isolated offline.

Two separate things:
- Shell geometry: `charged-creeper.patch` (this directory, from `outputs/horizon-native/charged-creeper-f42/`) makes the swirl use the CEM `creeper#armor` layer, so the shell follows FA's custom body, and silences `missing creeper_charge_animations.jpm`. `git apply --check -p1` passes on fdc87ae. It does not fix the white colour.
- White colour: no pack-side fix found. Next client step: run the energy-swirl draw with a MakeUp pack and check which gbuffers program the swirl is bound to and whether its alpha is forced to 1 (the colour bytes carry the sprite size with `vertex.normal = [0; 4]`, which an entity program that reads normals or colour as lighting would turn white). Needs a game run; not attempted.
Not built, not run.
