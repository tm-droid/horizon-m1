# R5: resource-pack stack vs Modrinth and Horizon f42 (2026-11-06)

Stack: `outputs/horizon-converter/2026-11-05-Tanush-f42-v4/resourcepacks` (52 zips, byte-for-byte the source packs in `instances/Tanush-26.3/minecraft/resourcepacks`).
Method: sha1 of each local zip against Modrinth `POST /version_files` (exact installed version), then `GET /project/<slug>/version` for latest + latest tagged `26.3`. API metadata only; no pack downloaded. Feature scan = zip directory listing only. Horizon support = reading `candidate-source/crates/horizon-optifine` (ctm, cit, random, random_textures, emissive, blink, fusion, cem incl. `emf/`) and `horizon-client-render` (sprite animations, native sky).

## Summary

- Outdated (hash-verified): 7. FreshAnimations 1.11.1 -> 1.11.2, FA+All_Extensions 1.9.2 -> 1.10.1, RAYs 3D Rails 3.6 -> 3.7, 3D Harness x FA 3.0.1 -> 3.0.2, Optimized Bushy Leaves v4.1 -> v4.3, Slightly Improved Font 1.1.5 -> 1.1.6 (by filename, hash not on Modrinth), Vocal Villagers 1.4 -> 1.5 (by filename; latest is tagged only 1.10).
- Unverifiable (no Modrinth hash match, same filename as latest): 5 Fresh packs (Buckets 1.3, Flowers 1.5, Food 1.3.8, Music Discs 1.4, Ores 1.4), all republished 2026-10-24..26, probably after the local copy; plus EnderEyes, Minecarts with Wheels, Fresh Skeleton Physics, NGO, Os' Leaves/Grasses, Recolourful, Weskerson's, animated-items, Remodeled Doors, Kosmolot, Teddy Totems (CurseForge/Planet MC or re-zipped). Re-download to confirm.
- Unsupported features: Dramatic Skys (OptiFine `sky/world0` + FabricSkyBoxes + Celestial: no sky reader in horizon-optifine; Horizon has one native sky), Recolourful Containers (`optifine/gui` 298 files + `optifine/anim` 120 files: no reader; base GUI textures still apply). Core shaders in packs are only inside old-format overlays (1.21.x, 26.1), never the 26.3 overlay; Recolourful's root has some.
- Cap risk: native emissive loader stops at 96 pairs. RAYs rails (75 pairs, mods Horizon does not run) take slots before NGO's vanilla ore CTM (124 dropped) (dedupe-audit-2026-11-05).

## Table

Installed = hash-verified Modrinth version, or `?` if the hash is unknown (filename version in brackets). Latest 26.3 = newest Modrinth version tagged 26.3 (date). Features from zip listing. Horizon: OK = reader exists in horizon-optifine/render; GAP = none. Overlays (`pack.mcmeta` overlays) are format-ranged: 26.3 = format 97.1+.

| # | pack | installed | latest 26.3 | features | Horizon | action |
|--:|---|---|---|---|---|---|
| 1 | 1.18 Panorama | 1.7.0 | 1.7.0 (09-16) | title panorama | OK | keep |
| 2 | Connected-Bricks | 3.1.1 | 3.1.1 | CTM 450 | OK ctm | keep |
| 3 | Connected-Rocks | 3.1.1 | 3.1.1 | CTM 522, emissive.properties, anim 17 | OK | keep |
| 4 | Os' Colorful Leaves | ? [Leaves-26.3] | ColorfulLeaves-26.3 (09-21) | plain textures | OK | keep; re-download to confirm |
| 5 | Optimized Bushy Leaves | v4.1 | v4.3 (10-24) | models, overlay patch34-46 | OK (old overlay inactive) | UPDATE |
| 6 | Bushier Bushes | v3.2.0 | v3.2.0 | models | OK | keep |
| 7 | Os' Colorful Grasses (Tall) | ? [Tall-26.3] | Tall-26.3 (09-21) | models | OK | keep |
| 8 | Fancy Crops | 1.3 | 1.3 | models | OK | keep |
| 9 | Fresh Flowers and Plants | ? [1.5?] | 1.5 (10-26) | models, emissive 6, anim 6, overlays 1.21.5..26.3 | OK | re-download |
| 10 | VanillaTweaks 3D Fungi | not on Modrinth (vanillatweaks.net) | n/a | models; 7 compat overlays fmt 84-97 | OK | keep |
| 11 | Fresh Flower Pots | 1.5.4 | 1.5.4 | models | OK | keep |
| 12 | Fresh Flower Pots 3D | 1.2.0 | 1.2.0 | models, 16 files win over #11 | OK | keep |
| 13 | Multi-Color Flowering Vines | 1.9 | 1.9 | textures | OK | keep |
| 14 | Fluffy Carpets | 1.1 | 1.1 | models | OK | keep |
| 15 | Renewed Bookshelf | 1.0.2 | 1.0.2 | 1 file | OK | keep |
| 16 | Remodeled-Doors | ? [2.3.1] | 2.3.1 (10-09) | models, mod namespaces (biomesoplenty, wilderwild) | OK | trim orphan mod namespaces (1.3 MB), keep minecraft |
| 17 | 3D Ladders | 1.2.2 | 1.2.2 | models | OK | keep |
| 18 | RAYs 3D Rails | ? [3.6] | 3.7 (11-03) | models 9853 files, emissive 19 (3 namespaces) | OK emissive; mod rails unreachable | UPDATE, trim orphan namespaces (20.5 MB, 75 emissive slots) |
| 19 | Weskerson's Torches | ? [1.0.3] | 1.0.3 (10-04) | models; overlays 1.21.5..26.3 | OK | keep |
| 20 | Better Beds | ? no Modrinth match | unknown slug | CEM 1 (optifine/cem 2) | OK cem | keep |
| 21 | Dramatic Skys Demo | 1.5.3.36.6 | 1.5.3.36.6 | optifine+mcpatcher sky/world0 (22), fabricskyboxes, celestial | GAP sky | DROP (7.7 MB dead; unsupported). Or keep only moon textures |
| 22 | better_flame_particles | 3.1 | 3.1 | particles textures, anim 18 | OK anim | keep |
| 23 | Gentler Weather Sounds | 2.3.0 | 2.3.0 | sounds | OK | keep |
| 24 | Vocal Villagers | ? [1.4] | 1.5 (11-03, tagged 1.10) | sounds | OK | UPDATE (check 26.3 compat, tag says 1.10) |
| 25 | Kosmolot's Colored Subtitles | ? [26.3+20260927] | same | lang/font | OK | keep |
| 26 | animated-items | ? [1.6.3] | 1.6.3 | anim 95, emissive.properties + 25 _e | OK anim+emissive | keep |
| 27 | Better Lanterns | 1.4.0 | 1.4.0 | models, anim 6 | OK | keep (6 files shadow animated-items) |
| 28 | Fine Armoury | 1.8 | 1.8 | textures | OK | keep |
| 29 | Visuals (thanos) | local `-26.3fix` of 2.0.2 | none tagged 26.3 (2.0.2 = 26.1.2) | 1345 files in 100+ overlays, anim 31 | OK if Horizon applies overlays | keep; REVIEW overlay application |
| 30 | Visual: Armor Trims | 4.3 | 4.3 | textures | OK | keep |
| 31 | Fresh Food | ? [1.3.8?] | 1.3.8 (10-24) | models, emissive 3, anim 6, overlays | OK | re-download |
| 32 | Fresh Buckets | ? [1.3?] | 1.3 (10-25) | models, anim 15 | OK | re-download |
| 33 | Fresh Music Discs | ? [1.4?] | 1.4 (10-26) | models | OK | re-download |
| 34 | Fresh Ores and Ingots | ? [1.4?] | 1.4 (10-26) | models, anim 9 | OK | re-download |
| 35 | New Glowing Ores | ? [2.0-1.21-border] | same (2024-10-23) | CTM 198, emissive 122 | OK, cap-limited | keep; see emissive cap |
| 36 | Even Better Enchants | 3-1.21.5 | same | textures | OK | keep |
| 37 | Teddy Totems | ? [1.2] | 1.2 | textures | OK | keep |
| 38 | Low Shield | 3.1.0 | 3.1.0 | textures | OK | keep |
| 39 | LowOnFire | 26.3 | 26.3 | anim 3 | OK | keep |
| 40 | Icons (WeNAN) | 1.14 | 1.14 (09-17) | 1783 files, overlays 1.20.2 / 26.2 | OK | keep (mod namespaces ~3 MB candidates) |
| 41 | Recolourful Containers DARK | ? [3.1.4] | 3.1.4 (10-01) | GUI textures, `optifine/gui` 298, `optifine/anim` 120, core shaders in root and 6 overlays | GAP gui+anim (base GUI OK) | keep base; ignore optifine/gui; verify no unintended shader load |
| 42 | FreshAnimations base | 1.11.1 | 1.11.2 (11-01) | CEM 218 (.jem+.jpm) | OK cem + expr | UPDATE |
| 43 | FA+All_Extensions | 1.9.2 | 1.10.1 (10-31) | CEM 86, emissive 46, random 124, emf/cem 12 | OK cem/random/emissive/emf | UPDATE |
| 44 | JustExpressions | 1.2.1 | 1.2.1 | emf/cem 6 | OK | drop candidate: 0/2 root JEMs win (FA+Player overrides); only overlay 21-2 left |
| 45 | FA+Player | 1.1.0 | 1.1.0 | emf/cem 21 | OK | keep |
| 46 | 3D Harness x FA | 3.0.1 | 3.0.2 (11-03) | CEM 9, random 14, emissive 5 | OK | UPDATE |
| 47 | Minecarts with Wheels | ? [1.5.0] | 1.5.0 | CEM 7 | OK | keep |
| 48 | Fresh Skeleton Physics | ? [2.0.1] | 2.0.1 | CEM 10 | OK | keep |
| 49 | Slightly Improved Font | 1.1.5 (name) | 1.1.6 (11-03, tagged 26.4 snapshot) | font | OK | UPDATE (optional) |
| 50 | EnderEyes | ? [26.3_v3.1] | 26.3_v3.1 (10-02) | anim 7 (blinking eyes) | OK anim/blink | keep |
| 51 | BetterEndPortalFrames NoFlame | 1.1 | 1.1 (tagged 26w14a only) | 2 files | OK | keep |
| 52 | Tanush Fixes | local | n/a | lang/sounds | OK | keep |

## Notes

- Horizon support observed: CTM (optifine/ctm via `ctm.rs`, Fusion layouts), CIT, random entities, emissive (`_e`, ETF suffix), blinking, CEM/JPM with expressions (`optifine/cem`, `emf/cem`), sprite animations (`.mcmeta`). No reader found for `optifine/sky`, `optifine/gui`, `optifine/anim`, `colormap`/`custom_colors`, `lightmap`, FabricSkyBoxes. (Packs here carry none of colormap/lightmap/CIT.)
- Overlay handling (`pack.mcmeta` overlays with `min_inclusive`/`max_inclusive`) was not located in the crates searched; 12 layers depend on it (dedupe audit). Unverified here.

## Dedupe / cheaper options (beyond dedupe-audit-2026-11-05)

1. Dramatic Skys: 79 files / 7.7 MB `skybox` for a feature Horizon cannot read. Drop, or reduce to the moon textures if the look matters.
2. RAYs 3D Rails: strip namespaces of mods Horizon does not run (railcraft, moreminecarts, thermal, create, alexscaves, caverns_and_chasms emissive.properties). Frees 75 emissive slots so NGO's vanilla ore overlays (124 now dropped) load; saves up to ~19 MB. Keep `minecraft:` and any pack-private namespace the models reference.
3. JustExpressions: root JEMs fully overridden by FA+Player. Drop unless overlay `21-2` matters (REVIEW).
4. Update FreshAnimations, FA+All_Extensions, 3D Harness in one step (the audit's 42 cross-layer JEM-to-JPM links depend on matching versions), then rerun the dedupe audit (counts will shift).
5. Recolourful Containers: remove `optifine/gui` (298) and `optifine/anim` (120); no Horizon reader, so only cost.
6. Optional cheaper same-look swaps: none found that match; leaf, grass, pot, torch packs each cover different blocks (audit: no functional overlap). Remove old-format overlays from the five Fresh packs and Weskerson's (1.21.x, 26.1 folders) if Horizon loads all overlays regardless of format; it saves only load time and holds duplicated models.
