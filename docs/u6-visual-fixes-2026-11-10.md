# U6 visual and compat fixes, 2026-11-10

Prep phase only. The game was not launched, nothing was built, `options.txt`, `settings.json` and the `versions` directory were not touched, and no existing zip was modified (so `backups/u6/` is empty by design). New pack: `~/Library/Application Support/horizon/resourcepacks/Horizon-Tanush-Compat-2026-11-10.zip`, not yet active. Builder: `tools/u6_build_compat.py`. Resolver: `tools/u6_cem_resolve.py`.

## Table

| # | Issue | Root cause | Fix | Files | Verify in game |
|---|---|---|---|---|---|
| 1a | Salmon `no part fin_back_N` / `tail` | `FA+All_Extensions` salmon.jem has three empty placeholder entries (`fin_back_1`, `fin_back_2`, `tail`): no boxes, no submodels, no animation refers to them, and the native salmon has no such bones | pack: overlay salmon.jem without the three entries | `Horizon-Tanush-Compat-2026-11-10.zip` `optifine/cem/salmon.jem` | salmon looks the same, warnings gone from the log |
| 1b | Cow, warm_cow, cold_cow `unknown target mushroomN.*` | FA's shared `cow_animations.jpm` writes `mushroom1..3`; only the baby jems declare those nodes | pack: add empty stub nodes (no boxes) at the baby's tree positions in the three adult jems | same zip, `cow.jem`, `cold_cow.jem`, `warm_cow.jem` | cows unchanged, warnings gone |
| 1c | Guardian, elder_guardian `unknown target spine_N.*` | jem part `body` has no native node; `vanilla_part` lacks the alias | client: `cem-binding.patch` | `patches/u6/issue1-guardian-and-aliases.md`, `cem-binding.patch` | spines animate, warning gone |
| 2 | Eleven CEM mobs skip per-part textures | renderer drops the part `texture` path | client: r10 part-texture plus part-variants patches, both need a rebase on fdc87ae | `patches/u6/issue2-part-textures.md` | horse chest, trader pouches, stray clothing visible; red sheep wool stays red |
| 3 | Recolourful DARK text shader rejected | `sampler2D` function parameters collide with the translator's `#define Sampler0` and Naga rejects them | client sketch only; pack-side rewrite judged unverifiable | `patches/u6/issue3-text-shader-sampler-param.md` | no shader-rejected line; container text coloured |
| 4 | `using the missing texture for minecraft:block/` | Better Lanterns templates default the texture keys to `block/`; vanilla chain and hanging-lantern children do not set the new keys | pack: three child models with the extra keys (Codex's hash-checked lantern-compat contents) | same zip, `models/block/iron_chain.json`, `lantern_hanging.json`, `soul_lantern_hanging.json` | hanging lanterns and iron chains show their textures, not magenta |
| 5 | MakeUp `block.properties` `betterendforge::` lines | upstream typo in the shader pack, unknown namespace, ignored | none (noise) | none | n/a |
| 6 | Charged creeper shell white under MakeUp | shell blue with shaders off; white even with the vanilla texture restored, so it is the shader-pack entity pass for the energy swirl, not the asset | client: `charged-creeper.patch` fixes shell geometry and the missing-import warning only; the white colour is unresolved | `patches/u6/issue6-charged-creeper-makeup.md`, `charged-creeper.patch` | needs a MakeUp run; compare with shaders off |
| 7 | Two recipe books on the crafting screen | atlas button drawn at native sprite size | none new: already fixed by `Horizon-GUI-Compatibility.zip` (position 55 in the list, active) | none | single recipe book button |
| 8 | Player leans sideways | FA+Player writes `root_rz` on purpose (the lean) | none, intended behaviour | none | n/a |
| 9 | `is_gliding` reads 0 | no `is_gliding` in `params!` in `cem_anim.rs` | client: two-line `is-gliding.patch` (applies cleanly, not compiled) | `patches/u6/is-gliding.patch`, `issue9-is-gliding.md` | elytra pose in FA+Player plays while gliding |

## options.txt change (not applied)

Append the new pack as the last (highest priority) entry of `resourcePacks`, after `"file/Horizon-Better-Beds-Compatibility.zip"`:

    ,"file/Horizon-Tanush-Compat-2026-11-10.zip"

It only touches salmon and cow jems and three lantern models, which no later pack overrides. Quit the game before editing the line.

## Offline checks run

- `python3 -I u6_cem_resolve.py` against the live stack: before, salmon reports `fin_back_1`, `fin_back_2`, `tail`; cow, cold_cow, warm_cow report `mushroom1..3`. With `--extra Horizon-Tanush-Compat-2026-11-10.zip`: none for all four.
- Zip integrity (`unzip -t`) and JSON parse of all 8 members pass.
- `git apply --check -p1` on `nightly-2026-11-08-fdc87ae`: `cem-binding.patch`, `charged-creeper.patch`, `is-gliding.patch` apply; `cem-part-texture` and `cem-part-variants` fail (cem.rs:113, render.rs:1391, cem.rs:1023); `daily-compat` fails at game.rs:15498 and perspective.rs:439.
- `pytest` is not installed for any python3 here, so `python3 -I -m pytest tests -q` could not run. `python3 -I -m unittest discover -s tests -q` ran 141 tests, OK, 3 skipped.

## Not done

Nothing was run in game. The text-shader rewrite, the charged creeper white shell and the part-texture rebase remain open. The `creeper_charge_animations.jpm` missing-import warning is left to `charged-creeper.patch` rather than stubbed in the pack, so the carrier is not replaced by an empty one.
