# R17: Horizon native mod picks (2026-11-06)

Read-only. Sources: `gh api` on horizon-rust/horizon-mods (94 tomls: 84 native-mod, 3 mod, 5 shader, 1 resourcepack; `native/` holds coords-hud, fps-overlay, keystrokes, minimap, recipes, smp, tools, voicechat-server, zoom), registry `.hnmod` release assets read in memory (only `horizon-native.json` inspected), local launcher-data, local docs (`launcher-data/native/stage/docs/{native-mods,mods,launcher-commands}.md`). Target f42ef42 (2026-11-03T08:12Z), `NATIVE_HOOKS_API = 359` (`native/stage/crates/horizon-client/src/game/native_hooks.rs:1033`). Registry tomls carry NO pin/API field; the pin is in each `.hnmod`'s `horizon-native.json` (registry release tag `<id>-<version>`). Pins below are from the newest `.hnmod` per mod.

## Answer first

1. Pin type decides everything. A mod with `"hooks": N` (N <= 359) builds on any newer Horizon, so it builds on f42ef42. A mod with only a `horizon` commit (hooks none) is a raw-target mod: the launcher compiles on THAT commit (native-mods.md "Pinned to a Nightly"; mixed pins -> newest pin, needs "Build anyway" / `--allow-version-mismatch`). Most community mods are raw-pin on commits OLDER than f42 (Oct 28-Nov 1); two are NEWER (998b1d8, Nov 3 23:51). Installing one moves the whole game off f42ef42. Install hooks-based mods only.
2. A launcher native build does NOT keep r3 (below).

## r3 question (critical)

- r3 (`versions/native-f42-m1-r3-6b039bd4b49f`) was not built by the launcher. Its `source-patches.json` says `build_method = direct-cargo-source-patches`: cargo run directly on `m1-performance-r3/candidate-source` with 17 patched files (horizon-threads, game.rs, remote.rs, shader_packs.rs, native_shaders.rs, lan/chunks.rs, horizon-client-render gfx/terrain.wgsl/native_emissive/lod/sprites/assets/particles/animate/pack_post). Build took 520 s.
- `native-build` ("Rebuilds stay on the instance's Horizon", native-mods.md:1652) recompiles "the same commit ... from the same game files" = launcher's pristine `native/source/f42ef42...` + horizon-mixins in the shared `native/stage/`. r3's patched files are not there. Result: new version `native-f42ef42-<hash>` that the instance then plays. `horizon-zoom-pilot` already plays such a build (`native-f42ef42-898af830522b`, no r3).
- So installing a native mod through the launcher and building gives f42ef42 + mods WITHOUT r3 perf patches. The r3 dir stays on disk and can be re-selected, but then it has no new mods. Whether `mods install` also rewrites `settings.json` `selected` (now r3) is unverified.
- To get mods AND r3 you must run the mixin pass on r3's candidate-source, or re-apply the 17-file patch on the launcher stage before cargo. No documented launcher switch. Unverified, not attempted. Hooks-only mods touch mod crates and `native_hooks.rs`; r3 touches game.rs/render, so overlap may be small but is not checked.

## Install path (our launcher)

Binary: `outputs/horizon-runtime/launcher-app/Horizon.app/Contents/MacOS/horizon-launcher`, data `launcher-data`.
```
horizon-launcher mods install <id> --instance <instance>                 # registry: checksum + minisign checked; stored in <instance>/horizon-native-mods/
horizon-launcher native-build --instance <instance> --trust-native-code  # compiles all installed+enabled native mods
horizon-launcher mods add-github <URL> --trust-native-code               # not registry-reviewed
```
GUI equivalent: Mods page -> Install; "Native build of {instance}" row -> Build (badge Not built / Needs rebuild / Up to date). Default profile `performance` (incremental). `--trust-native-code` = unsandboxed full access; read source first (R14 rule).

Cost on this Mac:
- `native/target/fast` is 7.1 GB (incremental 5.8 GB); `native/{patched,source,stage}` 97 MB each; each version dir about 1.3 GB (r3). Disk: 11 GB free of 228 (95% used). Each distinct mod set makes a new ~1.3 GB version dir. Free space first.
- Time: `native/build.log` (2026-11-04, this Mac) full `fast` build 5 m 25 s; r3 candidate 8 m 40 s. Docs (x86 desktop, 2 mods): first 4 m 29 s, mod change 56 s incremental. Expect several minutes per rebuild on M1/8 GB (unverified). Rust 1.99.1 and cargo cache already present in launcher-data, so no 20-30 min toolchain download. Close Safari/Roblox, do not play during the build.
- `built.json` now: `cem_alias_f42` + `zoom` 2.0.0, horizon f42ef42, mixins e8cd0aa. Adding mods = "Incremental rebuild: mods X, Y", recompiles horizon-client only.

## Registry classification (94)

Fits (client perf/looks/QoL): appleskin, appleskin_horizon, armor_status, armorhud, basic_hud, blockscope, chat_animation, chatheads, classic_zoom, compass_bar (mod kind), connected_textures, coords_hud, crosshair_indicator, customhud, dynamic_fps_for_rust, eatinganimation, elytratrails, enchantmenthints, fair_freecam, fast_items, flair, fps_overlay, freecam, freecam_plus, freelook, fullbright, fullbright_horizon, fullbright_nofog, held_item_info, horizon_physics, inventory_profiles, inventory_wizard, invisible_frames, itemnew, jade, jei, keystrokes, light_overlay, lookat, menu_panorama (resourcepack), minimap, mod_menu, motion_blur, mousetricks, recipes, resourcify, shulker_peek, skins_3d, smartf3, smoothie_capes, status_effect_hud, toggle_sprint, viahorizon, visuality_horizon, voicechat, waymap, waypoints, zoom; shaders daybreak, montarc, radiant, wisdom_horizon, wisdom_horizon_lite; distant_horizons (fits but too heavy for 8 GB).
Not a fit: baritone, xtoxray (cheats); accurate_block_placement, hitbox_plus, fly_speed, killc, stuck, veinminer, treefall, chop, carryblock, rightharvest, right_click_crops, gyro, spider_man, astral_cruiser, biomecompass, worldedit, horizonmatica, create, deepbore_quarry(+_native), wayfarer_stones(+_native), tectonic_horizon, speedrun_timer (gameplay/content/building); crossversion, rmotd, server_browser, serverify (multiplayer/server tools).
Built-in duplicates (R7): fullbright (extras.md:45), dynamic FPS (graphics.md:24), smooth chat, Continuity/CTM (resource-packs.md:43), Mouse Tweaks (extras.md:128), inventory sorting (extras.md:158), dynamic lights, LOD, zoom (already in our build).

### Hook-based (portable to f42)

| id | ver | hooks | tested on | source | R14 |
|---|---|---|---|---|---|
| jade | 26.3.6 | 359 (= f42) | 6475f62 | Joeypc6/Jade-Horizon | unreviewed; 222 KB, largest |
| appleskin_horizon | 1.0.0 | 1 | ba6344a | CayMac97/appleskin | safe |
| appleskin (soufied) | 0.1.3 | 139 | 02c8607 | soufied/AppleSkin-Horizon | unreviewed |
| status_effect_hud, armor_status, toggle_sprint, light_overlay, crosshair_indicator, inventory_profiles | 1.0.0 | 1 | ba6344a | CayMac97 | unreviewed (same author as safe mods) |
| fullbright_horizon | 1.0.0 | 1 | ba6344a | CayMac97 | safe |
| fullbright (bezi5kt) | 1.0.0 | 1 | 41672b1 | bezi5kt/gamma-rust | unreviewed |
| fullbright_nofog | 1.0.0 | 80 | c9d474d | Nirokx | unreviewed |
| held_item_info | 0.1.0 | 139 | 3db53df | AltMugen | unreviewed |
| inventory_wizard | 2.3.3 | 35 | f99f8fe | VanishingTacos | unreviewed |
| minimap (official) | 2.0.0 | 1 | 6f8c7a0 | horizon-rust/horizon-mods | official, not in R14 |
| zoom, classic_zoom, fps_overlay, keystrokes | 2.0.0 | 1 | 6f8c7a0 | official | zoom already built in |
| coords_hud / recipes | 2.0.0 | 1 / 2 | 4baa571 | official | unreviewed |
| chatheads, blockscope | 0.1.1 / 0.3.1 | 2 | 4aa6854 | Domanffe | unreviewed |
| eatinganimation | 0.1.1 | 1 | 142388e | soufied | unreviewed |
| motion_blur | 0.1.0 | 80 | c9d474d | levzzz5154 | unreviewed (GPU cost) |

### Raw-pin (hooks none): would build on that commit, not f42

freecam af55a73 (R14 safe; source-hash pins), fair_freecam aa27eca, freecam_plus 1da354b, waypoints c9d474d, waymap 0.2.0 c9d474d (R14 safe was 0.2.1 / 6475f62, so registry differs), connected_textures 9d979ca, mod_menu 6475f62, armorhud c9d474d, visuality_horizon c9d474d, smartf3 / itemnew / enchantmenthints / mousetricks / lookat 142388e, shulker_peek 5e391eb, basic_hud 68ac6f6, freelook a491181, skins_3d 2944480, smoothie_capes 68ff469, customhud ba6344a, fast_items + dynamic_fps_for_rust 998b1d8 (NEWER than f42). Commit dates: ba6344a Oct 30, aa27eca Oct 31, c9d474d Nov 1, 142388e Oct 28, f42ef42 Nov 3.

## Duplicate resolution

- Fullbright: use built-in extra first. If native wanted: `fullbright_horizon` (hooks 1, R14 safe, key G) over `fullbright` (/gamma only) and `fullbright_nofog` (hooks 80, also removes fog).
- Freecam (freecam / freecam_plus / fair_freecam): all raw-pin on older commits. Best is `freecam` (R14 safe, port of the user's Freecam) but its source-hash pin likely rejects on f42 (R14); `fair_freecam` second. Defer; needs a scratch test off r3.
- Zoom: keep official `zoom` 2.0.0 (already built); `classic_zoom` redundant.
- Minimap/waypoints: `minimap` (official, hooks 1) for the corner map. Waypoints only exist raw-pin (`waymap` over `waypoints`: derived from it, persistent store plus minimap dots). Hold waymap until a hooks-based release.

## Final ranking, top 10

| # | mod | does | replaces (user's Java pack) | compat | R14 |
|---|---|---|---|---|---|
| 1 | appleskin_horizon | saturation/food preview HUD | AppleSkin | OK (hooks 1) | safe |
| 2 | jade 26.3.6 | look-at tooltip (covers lookat/blockscope) | Jade | OK (hooks 359 = f42) | unreviewed; read 222 KB first |
| 3 | status_effect_hud | potion/effect bars | Status Effect Bars, Effect Insights | OK (hooks 1) | unreviewed (same author) |
| 4 | armor_status | armor + durability HUD | Detail Armor Bar Reconstructed | OK (hooks 1) | unreviewed (same author) |
| 5 | minimap (official) | corner map | Xaero's Minimap (disabled; no cave mode/world map) | OK (hooks 1) | unreviewed (official) |
| 6 | held_item_info | durability/count/enchants over hotbar | Held Item Info, Durability Tooltip | OK (hooks 139) | unreviewed |
| 7 | toggle_sprint | toggle sprint/sneak HUD | Tweakeroo (partial) | OK (hooks 1) | unreviewed (same author) |
| 8 | chatheads 0.1.1 | player head by chat line | Chat Heads | OK (hooks 2) | unreviewed |
| 9 | light_overlay | F7 spawn-light overlay | MiniHUD (partial) | OK (hooks 1) | unreviewed (same author) |
| 10 | eatinganimation | eating/drinking hand animation | none (visual) | OK (hooks 1) | unreviewed |

Skip for now: freecam/waymap (raw pin leaves f42), fast_items/dynamic_fps (pin newer than f42; built-in covers), fullbright/inventory_*/chat_animation (built-in covers), motion_blur (GPU), distant_horizons (RAM), voicechat (friend needs matching server side; unreviewed).

## Suggested sequence

1. Free disk above 20 GB (old version dirs: b6f52e28, control, r2, r3noqos, nightly-*), close Safari/Roblox.
2. Read each pick's source (R14 method); start with appleskin_horizon only.
3. Use a separate instance for the mod build; leave the r3 instance alone. One rebuild for the whole set. Compare benchmarks against `native-f42ef42-898af830522b`, not r3 (r3's 17 patched files are absent).
4. To keep r3 as well: port its patch onto the launcher stage by hand (unverified, needs cargo).

Unverified: whether `mods install` changes `selected`; real M1 incremental time; r3/mod file overlap; pins of the tomls not fetched (zoom-like official ones fetched; all listed above were read from release assets).
