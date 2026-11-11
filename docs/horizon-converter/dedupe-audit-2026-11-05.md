# Horizon resource stack dedupe audit, 2026-11-05

Scope: migration `outputs/horizon-converter/2026-11-04-Tanush-f42-v3` (52 resource packs, vanilla = layer 0, plus 210 carried mod-asset packs). Analysis only: no migration or source file was changed. Reproduce with:

```sh
python3 -I tools/horizon-layer-shadowing.py outputs/horizon-converter/2026-11-04-Tanush-f42-v3 --json shadow.json --md table.md
```

## Bottom line

- **Path-level waste is almost nil.** DROP: **0** layers. TRIM: **1** layer (FreshAnimations 1.11.1). Confirmed removable with zero visual change: **149 files / 0.23 MB** of 249.6 MB (0.1%). Another 13 files / 0.05 MB sit in 12 REVIEW layers (overlays). The simulated removal was verified: the effective path-to-sha256 map is identical before and after.
- Carried mod-asset packs: 17 files / 0.29 MB are shadowed by 4 resource packs (Recolourful Containers covers files of 5 mod packs; Fresh Buckets, Better Lanterns and Fresh Flower Pots one each). No mod pack is fully shadowed. Byte-identical duplicates: 1 (Language Reload vs Recolourful Containers).
- **The real problem is the emissive cap, not disk.** 286 effective block/CTM `_e.png` files exist; after the shared-base rule only 220 are eligible and the loader keeps 96. The model predicts 96 kept / 124 dropped, headroom 0.
- **Biggest lever (needs a decision, not a shadowing result):** namespaces that neither vanilla nor any carried mod provides total 13297 files / 34.7 MB. Removing them from the emissive pool drops it to 85 pairs, so **all of them load and headroom becomes 11** (vs 0 now). See "Orphan namespaces".

## Layer order and method

Higher `order` wins (options.txt order, last pack on top). Carried mod packs form one tier above vanilla and below all packs. Vanilla files are not in the manifest, so shadowing of vanilla is not modelled. Hash is the manifest sha256 (stronger than sha1). Rules used:

- A file is *dead* if a higher resource-pack layer ships the same path. *Removable* adds files byte-identical to the nearest lower provider (computed bottom-up so each removal keeps the effective map unchanged).
- lang, sounds.json, atlases and font json merge across packs, so they never count as shadowed (Kosmolot's Colored Subtitles and Tanush Fixes are 100% such files: KEEP).
- Layers with a pack.mcmeta `filter`, overlay directories that hold files, or nested sub-packs are **REVIEW**, never DROP/TRIM. 12 layers qualify. No layer has a `filter`.
- Percentages use all asset files of the layer (root tree + merged). Overlay-directory files are reported separately and not counted as shadowed.

## Per-layer table

`emissive kept/dropped` = pairs the effective stack contributes (see Emissive). `CEM` = winning .jem / total .jem of the layer (optifine and emf cem dirs).

| # | layer | files | % shadowed | dead MB | removable MB | emissive kept/dropped | CEM (jem won/total) | verdict | reason |
|--:|---|--:|--:|--:|--:|--:|---|---|---|
| 1 | 1.18 Panorama.zip | 6 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 2 | Connected-Bricks 26.2-26.3 v3.1.1.zip | 476 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 3 | Connected-Rocks 26.2-26.3 v3.1.1.zip | 570 | 0.2 | 0.00 | 0.00 | 0/0 | - | KEEP | 0.2% removable |
| 4 | Os' Colorful Leaves.zip | 54 | 25.9 | 0.01 | 0.01 | 0/0 | - | KEEP | 25.9% removable |
| 5 | Optimized Bushy Leaves.zip | 401 | 0.0 | 0.00 | 0.00 | 0/0 | - | REVIEW | 14 overlay files (patch34-46); root tree 0% removable |
| 6 | §6Bushier Bushes§r.zip | 15 | 6.7 | 0.00 | 0.00 | 0/0 | - | KEEP | 6.7% removable |
| 7 | Os' Colorful Grasses (Tall).zip | 66 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 8 | Fancy Crops v1.3.zip | 122 | 0.8 | 0.00 | 0.00 | 0/0 | - | KEEP | 0.8% removable |
| 9 | Fresh Flowers and Plants.zip | 1686 | 0.4 | 0.01 | 0.01 | 0/0 | - | REVIEW | 34 overlay files (1.21.5,1.21.6,1.21.9,26.1); root tree 0% removable |
| 10 | VanillaTweaks 3D Fungi.zip | 32 | 25.0 | 0.01 | 0.01 | 0/0 | - | KEEP | 25.0% removable |
| 11 | §3Fresh §bFlower Pots.zip | 99 | 5.1 | 0.00 | 0.00 | 0/0 | - | KEEP | 5.1% removable |
| 12 | §3Fresh §bFlower Pots 3D.zip | 16 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 13 | Multi-Color Flowering Vines.zip | 15 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 14 | Fluffy Carpets v1.1.zip | 51 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 15 | Renewed Bookshelf v1.0.2 - 26.3.zip | 1 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 16 | §aRemodeled-Doors§8_§62.3.1.zip | 558 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 17 | §l3D§f Ladders v1.2.2 - 26.3.zip | 2 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 18 | RAYs_3D_Rails_v3.6.zip | 9853 | 0.0 | 0.00 | 0.00 | 75/0 | - | KEEP | 0.0% removable |
| 19 | Weskerson's Torches.zip | 142 | 0.7 | 0.01 | 0.01 | 0/0 | - | REVIEW | 16 overlay files (1.21.5,1.21.6,1.21.9,26.1); root tree 1% removable |
| 20 | §lBetter Beds.zip | 17 | 0.0 | 0.00 | 0.00 | 0/0 | 1/1 | KEEP | no overlap |
| 21 | Dramatic Skys Demo 1.5.3.36.6.zip | 79 | 1.3 | 0.00 | 0.00 | 0/0 | - | KEEP | 1.3% removable |
| 22 | better_flame_particles-v3.1-mc1.21.9+-resourcepack.zip | 40 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 23 | Gentler Weather Sounds 2.3.0.zip | 18 | 5.6 | 0.00 | 0.00 | 0/0 | - | KEEP | 5.6% removable |
| 24 | §a§lVocal Villagers §r§71.4.zip | 46 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 25 | Kosmolot's Colored Subtitles 26.3+20260927.zip | 144 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 26 | animated-items 1.21.x-26.3 - v1.6.3.zip | 1299 | 1.2 | 0.01 | 0.01 | 0/0 | - | KEEP | 1.2% removable |
| 27 | Better Lanterns v1.4.0 - 26.2+26.3.zip | 155 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 28 | Fine Armoury v1.8.zip | 130 | 8.5 | 0.01 | 0.01 | 0/0 | - | KEEP | 8.5% removable |
| 29 | visuals-2.0.2-26.3fix.zip | 0 | 0.0 | 0.00 | 0.00 | 0/0 | - | REVIEW | 1345 overlay files (axolotl_items,bee_blocks,bogged_spawn_eggs,books); root tree 0% removable |
| 30 | visual_armor_trims_4.3.zip | 7327 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 31 | Fresh Food.zip | 1452 | 0.2 | 0.02 | 0.02 | 0/0 | - | REVIEW | 32 overlay files (1.21.5,1.21.6,1.21.9,26.1); root tree 0% removable |
| 32 | Fresh Buckets.zip | 360 | 0.0 | 0.00 | 0.00 | 0/0 | - | REVIEW | 50 overlay files (1.21.4,1.21.5,1.21.9,26.1); root tree 0% removable |
| 33 | Fresh Music Discs.zip | 396 | 0.3 | 0.00 | 0.00 | 0/0 | - | REVIEW | 34 overlay files (1.21.5,1.21.6,1.21.9,26.1); root tree 0% removable |
| 34 | Fresh Ores and Ingots.zip | 1075 | 0.0 | 0.00 | 0.00 | 0/0 | - | REVIEW | 34 overlay files (1.21.5,1.21.6,1.21.9,26.1); root tree 0% removable |
| 35 | NewGlowingOres-§6[Border]§r.zip | 446 | 0.2 | 0.00 | 0.00 | 21/124 | - | KEEP | 0.2% removable |
| 36 | EvenBetterEnchants_v3_1.21.5+.zip | 261 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 37 | §lTeddy Totems.zip | 7 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 38 | Low Shield.zip | 2 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 39 | LowOnFire v26.2§8.zip | 14 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 40 | Icons v.1.14.zip | 1783 | 0.0 | 0.00 | 0.00 | 0/0 | - | REVIEW | 573 overlay files (1.20.2,26.2); root tree 0% removable |
| 41 | Recolourful Containers DARK 3.1.4 (1.19.4+).zip | 1678 | 0.0 | 0.00 | 0.00 | 0/0 | - | REVIEW | 70 overlay files (-1.21.2_assets,1.20.2-1.20.4,1.20.5-1.20.6,1.21.0-1.21.1); root tree 0% removable |
| 42 | FreshAnimations_v1.11.1_26.1+.zip | 565 | 13.5 | 0.16 | 0.16 | 0/0 | 146/189 | TRIM | 76 files / 0.16 MB removable |
| 43 | FA+All_Extensions-v1.9.2.zip | 307 | 3.6 | 0.03 | 0.03 | 0/0 | 66/77 | KEEP | 3.6% removable |
| 44 | JustExpressions_v1.2.1.zip | 24 | 8.3 | 0.01 | 0.01 | 0/0 | 0/2 ALL-OVERRIDDEN | REVIEW | 1 overlay files (21-2); root tree 8% removable |
| 45 | FA+Player-v1.1.zip | 22 | 0.0 | 0.00 | 0.00 | 0/0 | 4/4 | REVIEW | 7 overlay files (21-2,21-5); root tree 0% removable |
| 46 | 3D Harness x Fresh Animations.zip | 46 | 0.0 | 0.00 | 0.00 | 0/0 | 9/9 | KEEP | no overlap |
| 47 | Minecarts with Wheels.zip | 8 | 0.0 | 0.00 | 0.00 | 0/0 | 7/7 | KEEP | no overlap |
| 48 | Fresh Skeleton Physics.zip | 10 | 0.0 | 0.00 | 0.00 | 0/0 | 10/10 | KEEP | no overlap |
| 49 | Slightly-Improved-Font-1.1.5.zip | 5 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 50 | EnderEyes_26.3_v3.1.zip | 84 | 1.2 | 0.00 | 0.00 | 0/0 | - | KEEP | 1.2% removable |
| 51 | BetterEndPortalFrames_ NoFlame.zip | 2 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |
| 52 | Tanush Fixes.zip | 2 | 0.0 | 0.00 | 0.00 | 0/0 | - | KEEP | no overlap |

Not listed above: layer 0 `vanilla` (built in).

## Emissive pairs vs the loader cap

Model of `native_emissive::load_optifine` (candidate-source): bases are `ns:block/name` sprites then CTM tiles, each sorted by name, bases with identical pixels skipped (shared layer), stop at MAX-NATIVE = 96. Native `emissive/` textures (32 reserved) are separate. Assumes vanilla base sprites exist; shared-pixel exclusion only sees pack files. It does not reproduce the runtime's first omitted file (`optifine/ctm/ores/deepslate_diamond_ore/3_e.png`), so treat counts as an estimate, but the ordering conclusion holds.

| Layer | pairs kept | pairs dropped | notes |
|---|--:|--:|---|
| RAYs 3D Rails v3.6 (order 18) | 75 | 0 | block overlays for rails of mods Horizon does not run (moreminecarts, thermal, create, rays_3d_rails ...); sorted before CTM so they take the slots |
| New Glowing Ores (order 35) | 21 (9 CTM) | 124 (all CTM) | vanilla-namespace ore CTM overlays are the ones cut |
| all others | 0 | 0 | no `_e` files in Fresh Ores and Ingots |

No `_e.png` is shadowed by a higher layer (0 dead emissive files); emissive loss comes only from the cap. Removing all orphan-namespace overlays (RAYs mod rails, NGO mekanism/create/werewolves) leaves 85 eligible pairs, under 96. Caveat: some orphan namespaces are pack-private (e.g. `rays_3d_rails`) and may be referenced from `minecraft:` models, so confirm per namespace before trimming.

## CEM winners

Effective: 243 .jem and 87 .jpm; 50+ paths exist in more than one layer, none byte-identical.

| Layer | .jem | won | overridden |
|---|--:|--:|--:|
| FreshAnimations 1.11.1 (42) | 189 | 146 | 43 (32 by FA+All_Extensions, 8 by Fresh Skeleton Physics, 3 by 3D Harness) |
| FA+All_Extensions (43) | 77 | 66 | 11 (4 by Skeleton Physics, 7 by Minecarts with Wheels) |
| JustExpressions (44) | 2 | **0** | 2 (player.jem / player_slim.jem overridden by FA+Player); REVIEW because of overlay `21-2` |
| FA+Player (45) | 4 | 4 | 0 |
| 3D Harness x FA (46), Minecarts with Wheels (47), Fresh Skeleton Physics (48), Better Beds (20) | 9 / 7 / 10 / 1 | all | 0 |

No layer's JEMs are entirely overridden except JustExpressions' two root JEMs (its overlay content may still apply, so it stays REVIEW). FreshAnimations is the base: its 146 winning JEMs and the JPM animation files they feed are still required. 42 winning JEMs (mostly FA+All_Extensions, Skeleton Physics) reference a JPM supplied by a different layer (FreshAnimations); dropping FreshAnimations would break them. This matches the full-stack-jpm-gaps note and means FA cannot be trimmed beyond the 76 dead files.

## Texture families

- **Ores:** New Glowing Ores (421 files, CTM + blocks), Fresh Ores and Ingots (246 files, 72 MB), RAYs 3D Rails: zero shared paths. No functional CTM-vs-block-texture name overlap detected, so no dedupe here; the cost is emissive slots, not files.
- **CTM:** Connected-Bricks (475), Connected-Rocks (568), NGO (352): zero shared paths.
- **Lanterns:** Better Lanterns (125) vs animated-items (30): 6 shared paths, animated-items loses 6 files (Better Lanterns is higher). Part of the TRIM list for animated-items (15 removable files, 8 KB), too small to act on.
- **Torches:** 6 layers touch torch paths; 1 shared path. Weskerson's Torches is the only large one (61 files).
- **Flower pots:** Fresh Flower Pots (99) / Fresh Flower Pots 3D (16) / VanillaTweaks 3D Fungi (12) / Weskerson's: 9 shared paths. Fresh Flower Pots loses 5 files and 3D Fungi loses 8 of its 12 pot files (25% of that pack) to higher layers, about 14 KB total. Fresh Flower Pots 3D is above Fresh Flower Pots and wins its 16.

## Orphan namespaces (candidates, not verified)

Pack content under namespaces with no vanilla/carried-mod owner: 13297 files, 34.7 MB. Largest: RAYs 3D Rails 20.5 MB (rays_3d_rails 16.2 MB, railcraft 1.7 MB, moreminecarts, thermal, create ...), Dramatic Skys `skybox` 7.7 MB, Vocal Villagers 1.2 MB, Icons 4 namespaces ~3 MB, Remodeled-Doors (biomesoplenty, wilderwild) 1.3 MB, NGO (mekanism, create, werewolves) 0.1 MB. Horizon does not run Java mods, so mod-owned namespaces (mekanism, create, biomesoplenty ...) are unreachable and removing them is expected to be visually neutral. Pack-private namespaces (rays_3d_rails, skybox, vocal_villagers, icons, tooltrims) are normally referenced by the same pack's `minecraft:` files and must NOT be dropped. These are not counted in the savings above; check each against runtime logs.

## Summary of expected savings

| Item | Layers | Files | MB | Risk |
|---|--:|--:|--:|---|
| DROP (100% shadowed/identical) | 0 | 0 | 0 | none |
| TRIM confirmed (FreshAnimations dead entity textures, 76 files in `assets/minecraft/textures/entity/*`) plus scattered dead files in 13 KEEP layers | 1 (+13 minor) | 149 | 0.23 | none (verified) |
| REVIEW layers, root tree only | 12 | 13 | 0.05 | overlay may change which file is live |
| Carried mod assets shadowed by resource packs | 7 mod packs | 17 | 0.29 | none |
| Orphan-namespace candidates | n/a | 13297 | 34.7 | needs per-namespace confirmation |

Emissive cap headroom: 0 now (96 kept, 124 dropped, 54 more skipped for shared bases). With orphan-namespace overlays excluded: 11 spare. Warnings: no filters; 12 layers with overlays; 42 cross-layer JEM-to-JPM references; JustExpressions JEMs fully overridden at root level.

## Caveats

Path-level analysis only: it cannot see functional shadowing (a CTM rule hiding a plain block texture, a model never referenced, a properties file matching the same blocks under another name). Zero-change claims apply to the effective path-to-hash map, not to rendered pixels. Overlays are evaluated conservatively (never used to justify DROP/TRIM). Vanilla and runtime atlas behaviour are assumed, not measured.
