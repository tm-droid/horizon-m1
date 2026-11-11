# Native mods: upstream catalog vs ours (U2, 2026-11-11)

Base: Horizon fdc87ae (NATIVE_HOOKS_API 411). Read-only research; nothing built, installed or run. Sources: registry index https://horizon-rust.github.io/horizon-mods/index.json (generated 2026-11-11T06:36Z), `horizon-rust/horizon-mods` tree and `native/*`, the 13 pinned repos via `gh api compare`, local mod sources in `outputs/horizon-runtime/m1-performance-r12/mod-src/`, fdc87ae source in `outputs/horizon-src-nightly/nightly-2026-11-08-fdc87ae`.

Note on `horizon-launcher mods search`: it searches Modrinth packs and Java mods (fps/zoom/minimap queries return resource packs such as "Fast Grass + FPS Boost", "Clear Spyglass Scope", "Icon Fresh"), NOT the native-mod registry. The native catalog is the registry index/repo, enumerated below. Nothing was installed.

Catalog size: 158 entries = 133 native-mod, 12 shader, 11 mod (asset/data halves), 2 resourcepack. 23 of the 133 native mods are `broken_on` fdc87ae (do not build). 61 declare `hooks` <= 411 (build on any commit >= that API); 20 pin fdc87ae exactly; the rest pin an older nightly with no `hooks` field and are marked OK only because the registry's daily `native-compat` run did not flag them (the launcher may ask "Build anyway" on mixed pins).

## Verdict summary

ADOPT (cheap, fits M1 8 GB + MakeUp):
1. **Zoomify 1.1.1** (`DeportedToHell/MCRE-Mods` `zoomify/`, already inside our pin 93079e6, exact fdc87ae pin): smooth/scroll/secondary zoom; replaces official `zoom` + our zoom-pilot defaults patch. Cost: 0 when not zooming. Needs one in-game check (hand FOV, spyglass, shader pack).
2. **Official Minimap 2.0.0** (`horizon-mods/native/minimap`, 17 KB of Rust, hooks 359 ok): drives Horizon's built-in minimap. Use instead of the 9k-line daniliammo mod unless a full-screen world map is wanted.
3. **Dynamic FPS (Lyvt-Dev, pinned 20ff37b)**: keep, but with idle throttle disabled (see below); gain is battery/thermal only when unfocused.
4. Conditional: **Better Dynamic Lights 1.0.3** (`MCRE-Mods` @ 04a7e98a, `betterdynamiclights/`, pinned exactly fdc87ae) for NON-shader play only; has no effect under MakeUp (see below).

DROP: zoom-pilot / zoom-f42-* patch dirs (superseded by Zoomify), fps_overlay mod (built-in `overlay:fps|graph` setting covers it), Lyvt `dynamic-fps-f42` in-tree patch (redundant with the mod), `fast-items-f42` (visual change, scene-dependent gain), daniliammo as default minimap (uncapped cache, repo now 404). KEEP CayMac97/fullbright: it is complementary to our fullbright patches, not a duplicate.

UPDATE: only `DeportedToHell/MCRE-Mods` has newer commits (23, none touch the dirs we use except new `betterdynamiclights`); the other 12 pins are identical to their default branch head. No bump needed now.

## Mods.lock.tsv daniliammo hash

Asked to fix a 38-char hash. The field is already 40 chars: `20f1d569d4f8b468515525b2b3ad196bcc4c9342` (`awk length` = 40) and equals `git rev-parse HEAD` of the local clone `mod-src/daniliammo__Minimap-Worldmap-and-waypoints-reworked` ("Release 0.5.0: retain cached biomes and add individual 16px icons"). No change made to `mods.lock.tsv`. The GitHub repo itself now returns 404 (`gh api repos/daniliammo/...`, `git ls-remote`: "Repository not found"), so the commit cannot be re-verified remotely and a fresh clone of the pin is impossible. The registry still serves 0.4.1 (mods repo a4b09b49, 2026-11-09, pin 2ebf00a/d9c83d7, no hooks) as a release asset (`minimap_worldmap_waypoints_reworked-0.4.1.hnmod`). Keep the local clone as the only copy of 0.5.0 (back it up).

## Overlap verdicts (ours vs upstream)

| Area | Ours | Upstream | Verdict |
|---|---|---|---|
| Fullbright | patches `fullbright-inputs` (adds `fullbright: false` field to PackInputs, shader_packs.rs, 11 lines) + `fullbright-shaderpack` (89 lines): `hz_fullbright` uniform, terrain/entity vertex prelude forces block light to 240, `nightVision >= 1`; toggles next frame, no pack reload | `CayMac97/fullbright` (pin 8a37d7d, hooks 1, 337+101 lines): key G toggle, smooth gamma fade, HUD banner; sets `renderer.gamma` and `renderer.fullbright` each frame in `on_frame` (glue.rs). Does nothing for shader packs by itself. Alternatives: `fullbright` (bezi5kt, /gamma command, 41672b1, hooks 1), `fullbright_nofog` (hooks 80) | Complementary, not duplicates. Mod = UI/toggle (key J in our horizon-mods.txt); our patches = the only thing that makes `renderer.fullbright` reach MakeUp. Ours better for packs; theirs needed for the toggle. Upstream has no equivalent (open policy issue 3823, nothing for packs found by title in main). Cost: one uniform write + one `max()` per vertex when pack active. |
| Dynamic FPS | none in stack. Off-stack `dynamic-fps-f42` = same Lyvt code transplanted in-tree (542-line patch), marked "NOT recommended" in its own README | Lyvt-Dev mod 0.1.0 (pin 20ff37b = default head), 500 lines, no hooks (pin 998b1d8, needs "Build anyway" if other pins differ) | Duplicate; theirs better (no maintenance). Drop the in-tree patch. Defaults: unfocused 10 fps (30 hovered), minimised 1, idle 20 fps after 60 s with no input while FOCUSED, battery 30. |
| Zoom | `zoom-pilot/zoomify-defaults.patch` on official zoom: key C, step 1.5, min 1.0 (46 lines); `zoom-f42-fixed-tool` unbuilt bundle. Currently built mod: `zoom` (built.json hash 9edc3a4267aa4d84) | official `zoom` 2.0.0 (hooks 1, 7 files, 9.8 KB), `classic_zoom` 2.0.0 (V, instant), `zoomify` 1.1.1 (smooth transitions, scroll zoom, secondary zoom; pin fdc87ae exactly; unchanged since our pin) | Theirs better (Zoomify). Our pilot is partial by its own README (no timed transitions, no hand FOV, no spyglass). Switch to zoomify; drop pilot dirs. |
| Particle culling | stack patch `particle-cull` (136 lines): per-particle view-box test in `ParticleEngine::render_in_view`, skipped particles still simulate, order preserved | fdc87ae already has upstream 7fc42e82 "standalone particle culling worker" (+301 in particles.rs, async, settings UI) and 9c101044 "async entity and particle culling" (both 2026-11-02); our `horizon-graphics.txt` has `particleCulling:off`, `entityCulling:off` | Overlap. Ours is simpler and synchronous, and is the only one active with those settings off. Theirs is thread-based and configurable. Verdict: undecided without a bench; the U5 knob sweep should compare `particleCulling:auto` against our patch. Upstream mod `visuality_horizon` (small pixel particles) would ADD particles; `trails`, `blood_particles` too; skip. |
| FPS display | none | official `fps_overlay` 2.0.0 (6.8 KB, FPS + min + 1% low) vs engine setting `overlay` (enum Off/Fps/Graph in graphics.rs:296: FPS+frame time, or numbers+frame-time graph) | Duplicate for our needs; built-in graph is better for tuning (`overlay:graph`). Mod only adds 1% low. Not adopted. |
| Minimap / world map | `daniliammo` 0.5.0 (runtime.rs 5130 + client.rs 4193 lines, bg thread, CPU raster) | official `minimap` 2.0.0 (17 KB, drives Horizon's own minimap, hooks 359); `worldmap` 0.6.0 (Px228, pin 66f3981, hooks 404, 3264 dl); `atlas` 0.2.0 (Xaero clone, hooks 409, 391 dl); `waymap` 0.1.4; `waypoints` 1.0.0 (Nirokx, c9d474d); `ayynoxs_map_pack` 0.4.2 | Official minimap is lighter by ~two orders of magnitude and uses the engine path. daniliammo has the only polished full world map + waypoint set but our own audit (docs/research/waypoints-mod-audit-2026-11-10.md) found an UNCAPPED tile cache (~6.6 KB/tile, ~660 MB per 100k chunks, new key space per head Y in caves/Nether) on an 8 GB machine, per-frame getcwd+Vec clones, and its upstream repo is now gone. Use official minimap by default; run daniliammo only with the audit's preset settings and short cave sessions. Not benchmarked here. |
| Dynamic lights | patch dir `up-pack-dynlights-fdc87ae` (off-stack, 290 lines, cherry-pick of main 5ec521bb: lights as uniforms for packs, never built) | engine "Horizon Extras > Dynamic lights" (held/dropped/burning only, default off); mods `dynamiclights` 1.0.0 (registry, pin 2ebf00a) and Better Dynamic Lights 1.0.3 (repo, pinned fdc87ae) | See ADOPT-conditional below. |
| Item entities | `fast-items-f42` (off-stack, in-tree transform of Lyvt FastItems: flat dropped items) | `fast_items` 0.1.0 | Same code. Gain only in item floods; changes visuals (paper-flat, always camera-facing). Drop. |

## Dynamic lights: cost and shader packs

- What the mod does (read `dynamiclights/mixins/dynamiclights/glue.rs`, `gather.rs`): it hooks `gather_dynamic_lights` and fills `game.dynamic_lights` itself; Horizon's renderer lights the world. No extra render pass. Per frame it walks the entity lists once, keeps sources with level > 0 within `range` (default 64), `select_iter` keeps the nearest `max_sources` (default 16), then scales brightness. Estimated well under 0.1 ms CPU per frame on an M1 (from reading, not measured). GPU cost is the engine's existing fixed-size light loop in terrain/entity shaders (`dynamic_light::MAX`), the same as turning on the built-in extra.
- Memory: a Vec of at most MAX [f32;4] lights, one thread_local Vec; nothing meaningful on 8 GB.
- Shader packs: in fdc87ae the lights are consumed only by `Globals.dynamic_lights` in the engine's own terrain/entity shaders (gfx.rs:7813-7819; `pack_uniforms.rs` passes `dynamic_lights: &[]`). With MakeUp-UltraFast active those shaders are bypassed, so the lights would have NO visible effect (inferred from source, not run). Making them work needs our off-stack `up-pack-dynlights` (main 5ec521bb) AND a pack that reads the new uniforms, which MakeUp does not. So: useful only when playing without a shader pack.
- Version choice: registry `dynamiclights` 1.0.0 pins 2ebf00a (no hooks; registry says OK on fdc87ae). Repo `betterdynamiclights` 1.0.3 (04a7e98a, 2026-11-10) pins fdc87ae exactly and is the one to use (MCRE commits 6baeb71/a2c2ad7/347a644/226ffd7); its dir was renamed from `dynamiclights/` (the old dir now just points to the new one), so our pinned commit 93079e6 still has the old `dynamiclights/` 1.0.0.

## Our 13 pinned repos: newer commits?

| mods.lock dir | pin | default-branch head | newer? | still fdc87ae-buildable |
|---|---|---|---|---|
| AltMugen__horizon-held-item-info | 406a649 | same | none (last push 2026-11-02) | yes: hooks 139 |
| CayMac97__armor-status | b3011de | same | none (10-31) | yes: hooks 1 |
| CayMac97__crosshair-indicator | c1a6d2a | same | none | yes: hooks 1 |
| CayMac97__fullbright | 8a37d7d | same | none | yes: hooks 1 |
| CayMac97__light-overlay | 38ce378 | same | none | yes: hooks 1 |
| CayMac97__status-effect-hud | 9342bae | same | none | yes: hooks 1 |
| CayMac97__toggle-sprint | c30b952 | same | none | yes: hooks 1 |
| DeportedToHell__MCRE-Mods | 93079e6 | 04a7e98a (2026-11-10) | 23 commits: new mods Emotecraft, Particle Rain, Ping Wheel, Plasmo Voice 1.0.0/1.0.1, bwncr/clumps 1.0.1-1.0.2, Better Dynamic Lights 1.0.2/1.0.3 (renamed dir), README work, bug-report form. Files touched: emotecraft 108, particlerain 73, .github 58, betterdynamiclights 30, bwncr 10, clumps 10, pingwheel 9. None of the existing dirs (zoomify, betterf3, modmenu, mousetweaks, smoothswapping, shulkerboxtooltip, justenoughitems, roughlyenoughitems, clientsort, firstpersonmodel, plasmovoice, pickupnotifier, fallingleaves) changed in this range | yes: horizon-native.json of zoomify/particlerain/betterdynamiclights all pin fdc87ae + mixins 5a64af9 |
| Domanffe__chatheads | c052d3f | same | none (11-02) | yes (registry pin a46ce68, no hooks field, not flagged) |
| Joeypc6__Jade-Horizon | d001694 | same | none (11-07) | yes; registry still lists 26.3.5 (pin c9d474d, hooks 80), our pin is the newer 26.3.8 source (earlier note: 26.3.6 was E0308) |
| Lyvt-Dev__dynamic-fps-for-rust | 20ff37b | same | none (11-04) | registry pin 998b1d8, no hooks; not flagged |
| daniliammo__Minimap-Worldmap-and-waypoints-reworked | 20f1d56 | repo 404 | unknown | registry 0.4.1 not flagged; local 0.5.0 is untested on fdc87ae |
| horizon-rust__horizon-mods | a4b09b4 | same | none | yes (zoom/minimap/fps_overlay hooks 1/359) |
| soufied__AppleSkin-Horizon | 20180ee | same | none (11-05) | yes (registry: `appleskin` 1.0.0 pin 142388e, hooks 1; CayMac97's `appleskin_horizon` is BROKEN with E_TARGET_NOT_FOUND, not in our lock: good) |

## ADOPT list

| Mod | Commit | Why | Expected cost |
|---|---|---|---|
| Zoomify 1.1.1 | MCRE-Mods `zoomify/` @ 93079e6 (already pinned; horizon-native.json pins fdc87ae/5a64af9) | smooth + scroll + secondary zoom beats our partial zoom-pilot; no engine patch | ~0: logic runs only while the zoom key is held; confirm FOV with MakeUp and spyglass in one session |
| Official Minimap 2.0.0 | horizon-mods a4b09b4 `native/minimap` | uses engine minimap, 8 small .rs files, no big cache; replaces daniliammo as default | negligible CPU, no growing memory |
| Dynamic FPS | Lyvt-Dev 20ff37b (already pinned) | on a fanless Air, throttling when unfocused/minimised saves heat/battery | 0 while focused and active. Set config so the 60 s idle cap never triggers (keys `idle_timeout_seconds`/`idle_fps` in mixins/dynamic_fps_for_rust/runtime.rs:12-22; config file `config/dynamic-fps-for-rust.json`, `{"enabled": false}` for benches) |
| Better Dynamic Lights 1.0.3 (conditional, non-shader sessions only) | MCRE-Mods 04a7e98a `betterdynamiclights/` (needs a pin bump to use; fdc87ae-exact) | torch/lantern/fire/projectile light with a 16-source cap and 64-block range | <0.1 ms CPU est.; no benefit under MakeUp |
| shulkerboxtooltip 1.0.1, mousetweaks 1.0.1, smoothswapping 1.1.0 (optional QoL, all MCRE dirs in our pin) | 93079e6 | inventory QoL, no per-frame world cost | UI-only; unmeasured |

Already fine to keep (HUD/QoL, small): armor-status (495 lines), status-effect-hud (453), toggle-sprint (548), crosshair-indicator (368), held-item-info (47), chatheads (379), appleskin (804), light-overlay (619, only active on F7), fullbright (needed with our patches).

## DROP list

| Item | Why |
|---|---|
| `zoom-pilot/`, `zoom-f42-candidate`, `zoom-f42-fixed-tool/` | superseded by Zoomify; pilot targets e6e12d4/hooks 153 and is partial |
| `dynamic-fps-f42/` in-tree patch | same Lyvt code; mod is maintained upstream; patch is UNBUILT |
| `fast-items-f42/` | visual change, benefit only in item floods |
| `fps_overlay` mod | engine `overlay` setting already shows FPS/frame time/graph |
| daniliammo as default | uncapped tile cache on 8 GB, ~9.3k lines of per-frame hook code, upstream repo 404; keep only as optional with the audit's preset |
| Jade-Horizon if memory is tight (risk) | 7848 lines, largest of our HUD mods; per-frame target tooltip; keep unless profiling shows cost (not measured) |
| Avoid adding | `motion_blur`, `visuality_horizon`, `trails`, `blood_particles`, `horizon_physics` (extra GPU/CPU work on M1 8 GB), and anything in the 23 BROKEN list |

## UPDATE list

| Pin | Action | Risk |
|---|---|---|
| MCRE-Mods 93079e6 -> 04a7e98a | Only needed to get `betterdynamiclights/`; every dir we use is byte-identical in the diff range. If bumped, build only the dirs we enable. | Low: compare shows no edits in zoomify/betterf3/etc. Not needed for ADOPT 1-3. |
| daniliammo | none possible (repo 404); back up the local 0.5.0 clone. If it must be replaced use registry 0.4.1 (pin 2ebf00a) | Medium: 0.4.1 has no cached-biome retain |
| everything else | no newer commits | none |

## Broken on fdc87ae (do not build), from the registry index

appleskin_horizon (CayMac97), astral_cruiser, basic_hud, biomecompass, carryblock, chop, context_tools, create, customhud, distant_horizons, fair_freecam, freecam, freelook, gyro, hitbox_plus, shulker_peek, smartf3, spider_man, strangely_charming, treefall, voicechat, worldedit, xtoxray. Notable for this user: `customhud` and `basic_hud` (HUD editors), `distant_horizons`, `smartf3` all fail; `hud_plus` (hooks 139) and `betterf3` (MCRE) are the working HUD alternatives.

## Gaps / caveats

- No measurements were taken; costs are from source reading. Do not adopt without the U-ledger bench rule (>=2% avg FPS or 1% low, gallery 0 fails).
- Mods without a `hooks` field pin an older nightly and rely on the registry's `native-compat` run; they can break on the next nightly.
- `Nirokx/waypoints` 1.0.0 (c9d474d) is the lighter waypoint alternative to pair with the official minimap; its code was not read.
- Global graphics `particleCulling:off` and `entityCulling:off` are set in config/game/horizon-graphics.txt; the upstream culling workers are therefore untested on this machine.

## Full catalog: native mods (133), registry index 2026-11-11T06:36Z

Columns: id, latest version, published (MM-DD, 2026), pinned Horizon commit, `hooks` field, status on fdc87ae/411, purpose. Non-native entries (12 shaders: aurora, daybreak, lumen, lumina, montarc, nimbe, pastel_mystic, radiant, vivid_horizon, volex, wisdom_horizon, wisdom_horizon_lite; 11 asset/data `mod` halves; 2 resourcepacks) omitted.

| id | ver | pub | pin | hooks | fdc87ae | purpose |
|---|---|---|---|---|---|---|
| accurate_block_placement | 1.0.0 | 11-03 | aa27eca | - | OK per registry (pin only) | Hold right click with a block and every new spot you look at gets one,... |
| ae2 | 15.4.17 | 11-08 | 6560641 | 411 | OK hooks 411 | Unofficial port of Applied Energistics 2 15.4.12: ME networks, autocra... |
| appleskin | 0.1.3 | 11-05 | 02c8607 | 139 | OK hooks 139 | Shows how much HP, hunger, and saturation will be restored. |
| appleskin_horizon | 1.0.0 | 10-31 | ba6344a | 1 | BROKEN E_TARGET_NOT_FOUND | 1:1 Minecraft Java parity food value preview & saturation HUD overlay. |
| armor_status | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | Displays equipped armor & held items with authentic Java durability co... |
| armorhud | 1.0.0 | 11-04 | c9d474d | - | OK per registry (pin only) | Your worn armor and its durability in a column left to the off-hand sl... |
| astral_cruiser | 0.1.0 | 11-01 | 68ac6f6 | - | BROKEN E0061 | A huge pilotable starship with a walkable interior, lasers, dash and l... |
| atlas | 0.2.0 | 11-08 | f319701 | 409 | OK hooks 409 | A clone of Xaero's Minimap and World Map: a sharp minimap, a world map... |
| ayynoxs_map_pack | 0.4.2 | 11-05 | 6475f62 | - | OK per registry (pin only) | Minimap and full-screen world map with waypoints, cave layers and opt-... |
| baritone | 1.1.52 | 11-05 | 6475f62 | - | OK per registry (pin only) | A Rust port of the Baritone pathfinder: #goto, #mine, #farm, #build, #... |
| basic_hud | 0.5.0 | 11-04 | 68ac6f6 | - | BROKEN E0609 | A visual HUD editor with 14 customizable widgets, recent pickups, effe... |
| betterf3 | 1.0.0 | 11-09 | 2ebf00a | - | OK per registry (pin only) | A port of BetterF3: a customizable, colour-coded, human-readable debug... |
| big_nukes_native | 0.1.3 | 11-08 | 6560641 | 410 | OK hooks 410 | Nuclear bombs whose shockwave digs real craters and leaves fallout. La... |
| biomecompass | 0.2.2 | 10-29 | 142388e | - | BROKEN E0433 | Craft a Biome Compass, pick a biome and its needle points to the neare... |
| blockscope | 0.3.1 | 11-02 | 4aa6854 | 2 | OK hooks 2 | The block under your crosshair: its name, id, distance and icon, plus ... |
| blood_particles | 1.2.0 | 11-08 | 2ebf00a | 411 | OK hooks 411 | Blood particles upon a mob hit |
| carryblock | 0.1.2 | 10-29 | 142388e | - | BROKEN E0599 | Sneak and right-click with an empty hand to pick up a chest (with its ... |
| chat_animation | 0.1.3 | 11-09 | fdc87ae | - | exact fdc87ae | ChatAnimation for Horizon |
| chat_heads_rust | 1.0.2 | 11-06 | 4aa6854 | 2 | OK hooks 2 | Chat Heads displays player heads in the chat before the players name m... |
| chatheads | 0.1.1 | 11-02 | 4aa6854 | 2 | OK hooks 2 | A player's head left of every chat line they wrote. |
| chop | 1.0.1 | 11-03 | c9d474d | - | BROKEN E0308 | Cut one log and the whole tree tips over, crashes down and breaks apar... |
| cinematic_interactions | 0.12.2 | 11-09 | fdc87ae | - | exact fdc87ae | Using a crafting table, furnace, anvil, enchanting table and more move... |
| classic_zoom | 2.0.0 | 10-29 | 6f8c7a0 | 1 | OK hooks 1 | Hold V to zoom 3x, scroll for more, release to snap back. Instant, no ... |
| clientsort | 1.2.0 | 11-09 | fdc87ae | - | exact fdc87ae | Inventory sorting from ClientSort: Sort, Restock and Transfer buttons,... |
| connected_textures | 0.1.7 | 11-09 | fdc87ae | - | exact fdc87ae | Continuity for Horizon |
| context_tools | 1.3.0 | 11-08 | 6475f62 | - | BROKEN E_TARGET_NOT_FOUND | Classic Tool swap |
| coords_hud | 2.0.0 | 10-29 | 4baa571 | 1 | OK hooks 1 | Your coordinates and facing in a corner of the screen. |
| cpm | 0.1.2 | 11-06 | 02c8607 | 355 | OK hooks 355 | Customize your Minecraft avatar with custom models and animations |
| create | 0.7.0-alpha.2 | 11-05 | 9c7f9b2 | - | BROKEN E_TARGET_NOT_FOUND | Build rotating machines and small factories in Horizon with gears, bel... |
| crosshair_indicator | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | Dynamic target reach awareness: visual feedback on your crosshair when... |
| crossversion | 0.8.0 | 11-03 | 07b7ea3 | 80 | OK hooks 80 | Allows version hopping offline. |
| customhud | 1.7.0 | 11-06 | c9d474d | - | BROKEN E0609 | A lightweight day counter, clock and day/night cycle bar for the HUD, ... |
| deepbore_quarry_native | 0.1.2 | 11-08 | 67dad0d | 309 | OK hooks 309 | A machine that digs a square pit down to bedrock on furnace fuel and f... |
| distant_horizons | 0.1.0 | 10-29 | d009ebd | - | BROKEN E0609 | See far past your render distance: Distant Horizons' level-of-detail t... |
| dynamic_fps_for_rust | 0.1.0 | 11-04 | 998b1d8 | - | OK per registry (pin only) | Reduce resource usage while Minecraft is in the background, idle, or o... |
| dynamiclights | 1.0.0 | 11-08 | 2ebf00a | - | OK per registry (pin only) | Torches and other glowing items light up the world while you hold them... |
| eatinganimation | 0.2.0 | 11-06 | 6d99e14 | 1 | OK hooks 1 | While you eat food, or drink a potion or milk, the item in your hand s... |
| elytratrails | 0.1.2 | 11-05 | 02c8607 | 8 | OK hooks 8 | A Horizon mod that adds elytra trails with additional features. |
| enchantmenthints | 0.1.0 | 10-29 | 142388e | - | OK per registry (pin only) | A short description under every enchantment in item tooltips, in Engli... |
| fair_freecam | 1.2.0 | 10-31 | aa27eca | - | BROKEN E_INVALID_HELPER | Fly the camera freely while your player stays where it is, with an opt... |
| fast_items | 0.1.0 | 11-04 | 998b1d8 | - | OK per registry (pin only) | Optimize item rendering by transforming item entities to 2D |
| fast_trading | 1.0.0 | 11-06 | 3fb4c31 | - | OK per registry (pin only) | A speed-trade button on the merchant screen repeats the selected trade... |
| fence_perch | 1.0.0 | 11-08 | 2ebf00a | - | OK per registry (pin only) | Jump onto fences, walls and closed gates from a standstill, stand on t... |
| first_person_body | 1.0.0 | 11-09 | fdc87ae | 411 | exact fdc87ae | See your own body in first person: look down to see your legs and feet |
| firstpersonmodel | 1.0.0 | 11-09 | 2ebf00a | - | OK per registry (pin only) | A port of First-person Model: see your own body in first person, with ... |
| flair | 1.0.1 | 11-06 | 66f3981 | - | OK per registry (pin only) | Custom accessory mod |
| fly_speed | 0.2.0 | 11-04 | 9d979ca | 35 | OK hooks 35 | Allows you to change your flight speed |
| fps_overlay | 2.0.0 | 10-29 | 6f8c7a0 | 1 | OK hooks 1 | Frames per second in a corner of the screen, with the minimum and the ... |
| freecam | 0.1.0 | 10-31 | af55a73 | - | BROKEN E_TARGET_NOT_FOUND | Freecam mod ported for Horizon |
| freecam_plus | 1.0.1 | 11-06 | 66f3981 | - | OK per registry (pin only) | Fly the camera anywhere while your player stays perfectly still. |
| freecam_yannis | 1.0.1 | 11-08 | 2ebf00a | 402 | OK hooks 402 | Free camera, F6 follow view and nine tripod positions for Horizon. |
| freelook | 0.3.1 | 10-31 | a491181 | - | BROKEN E_TARGET_NOT_FOUND | Hold a key for a third person camera you can look around in |
| fullbright | 1.0.0 | 10-30 | 41672b1 | 1 | OK hooks 1 | Brightness past 100%: set your own gamma with /gamma, or toggle full b... |
| fullbright_horizon | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | Toggle maximum 1000% gamma cave and night brightness with smooth fade ... |
| fullbright_nofog | 1.0.0 | 11-02 | c9d474d | 80 | OK hooks 80 | Toggle full brightness and the world's fog with a key (G / N), /fullbr... |
| gyro | 1.4.1 | 11-05 | ba6344a | 3 | BROKEN E_TARGET_NOT_FOUND | Full 6DOF flight physics and immersive gyro camera tilt for Minecraft ... |
| held_item_info | 0.1.0 | 11-02 | 3db53df | 139 | OK hooks 139 | Selected-item durability, count and enchantment names above the hotbar... |
| hitbox_plus | 1.3.0 | 11-03 | 68ac6f6 | 1 | BROKEN E0432 | Customizable entity hitboxes with exact weapon & spear in-reach colors... |
| horizon_physics | 0.20.7 | 11-09 | fdc87ae | - | exact fdc87ae | Physics for Horizon, inspired by PhysicsMod: ragdolls, waves, physical... |
| horizonmatica | 0.3.2 | 11-08 | fdc87ae | - | exact fdc87ae | Litematica for Horizon: schematics as ghost blocks, a verifier, materi... |
| hud_plus | 4 | 11-06 | f42ef42 | 139 | OK hooks 139 | One fully configurable HUD with a drag-and-drop editor and four views ... |
| imfast | 0.1.0 | 11-09 | 1d63e0a | - | OK per registry (pin only) | Removes Minecraft's server-side player and elytra movement limits. |
| inferium_lab | 0.1.0 | 11-09 | 66f3981 | - | OK per registry (pin only) | Grow Inferium on farmland and harvest its essence in Horizon 26.3. |
| inventory_profiles | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | R-key & UI sorting (Category, A-Z, Count, ID), Auto-Refill depleted st... |
| inventory_wizard | 2.3.3 | 11-01 | f99f8fe | 35 | OK hooks 35 | InventoryWizard's one-click sorting as a native mod for Horizon |
| invisible_frames | 0.1.1 | 11-03 | 3db53df | 139 | OK hooks 139 | Sneak-right-click a filled frame to hide and lock it, or restore it. |
| itemnew | 0.1.1 | 10-29 | 142388e | - | OK per registry (pin only) | Newly picked-up items glow in your hotbar and inventory until you look... |
| jade | 26.3.8 | 11-08 | 6560641 | 411 | OK hooks 411 | The look-at tooltip: what you're pointing at, its mod, its details and... |
| jei | 0.2.1 | 11-08 | 6560641 | 313 | OK hooks 313 | An item and recipe viewer for Horizon: every item beside container scr... |
| justenoughitems | 1.1.0 | 11-09 | fdc87ae | - | exact fdc87ae | JEI for Horizon: every item beside your inventory, JEI's search, recip... |
| keystrokes | 2.0.0 | 10-29 | 6f8c7a0 | 1 | OK hooks 1 | Your movement keys, mouse buttons and space bar in a corner, lit while... |
| killc | 5.1.0 | 11-01 | d91cab6 | 40 | OK hooks 40 | /killc, /killc <player> and /suicide, with an optional random respawn ... |
| light_overlay | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | 1:1 Light Overlay & MiniHUD (F7): visualizes mob-spawnable blocks with... |
| living_camera | 1.0.0 | 11-09 | fdc87ae | 369 | exact fdc87ae | A camera that moves with you: it leans into strafes, sways on turns, d... |
| livingmotion | 1.2.0 | 11-07 | f319701 | - | OK per registry (pin only) | Punchy moves ported into a hnmod. |
| lookat | 0.2.1 | 10-29 | 142388e | - | OK per registry (pin only) | The block or mob under your crosshair as a vanilla tooltip: icon, name... |
| map_preview | 1.0.0 | 11-09 | fdc87ae | 411 | exact fdc87ae | See a map's picture in its tooltip and in its inventory slot, so you c... |
| minelights | 2.4.0 | 11-07 | 67dad0d | 1 | OK hooks 1 | MineLights is a Minecraft mod that brings RGB lighting integrations to... |
| minimap | 2.0.0 | 10-29 | 6f8c7a0 | 1 | OK hooks 1 | A map of the world around you in a corner of the screen. |
| minimap_worldmap_waypoints_reworked | 0.4.1 | 11-09 | 2ebf00a | - | OK per registry (pin only) | An adaptive minimap and world map with named waypoints, portals, world... |
| mod_menu | 0.3.5 | 11-09 | fdc87ae | - | exact fdc87ae | ModMenu For Horizon |
| modmenu | 1.1.0 | 11-08 | 2ebf00a | - | OK per registry (pin only) | A port of TerraformersMC's Mod Menu: a Mods button on the title screen... |
| motion_blur | 0.1.0 | 11-02 | c9d474d | 80 | OK hooks 80 | Blurs what moves: mobs, players, items and vehicles along their own mo... |
| mousetricks | 0.2.0 | 10-29 | 142388e | - | OK per registry (pin only) | Inventory mouse tricks: drag to spread or gather, the wheel moves item... |
| mousetweaks | 1.1.0 | 11-09 | fdc87ae | - | exact fdc87ae | Mouse Tweaks from Java: right-drag to spread, left-drag to gather or q... |
| movement_status | 0.1.0 | 11-05 | f319701 | - | OK per registry (pin only) | Better toggle Sprint/Sneak display functionality |
| notenoughanimations | 0.2.76 | 11-09 | fdc87ae | - | exact fdc87ae | tr7zw's third-person animations for Horizon: eating, climbing, rowing,... |
| orbital | 0.5.10 | 11-06 | e57b1d3 | - | OK per registry (pin only) | Fifteen orbital strikes, from a laser to a Planet Killer: a designator... |
| projecte_core | 0.1.0 | 11-06 | 66f3981 | 411 | OK hooks 411 | Unofficial port of ProjectE: EMC, transmutation tables, collectors, co... |
| pvp_music | 1.2.0 | 11-06 | 3fb4c31 | - | OK per registry (pin only) | Battle music during combat: fades, death fades and the phased two-half... |
| rarity_borders | 0.1.1 | 11-09 | 2ebf00a | 139 | OK hooks 139 | Adds clean, vanilla-style colored borders to inventory items based on ... |
| recipes | 2.0.0 | 10-29 | 4baa571 | 2 | OK hooks 2 | Every item beside your inventory, with its recipes and uses. |
| resourcify | 0.1.2 | 11-09 | fdc87ae | - | exact fdc87ae | Resourcify for Horizon |
| rider_hud | 0.1.0 | 11-08 | 2ebf00a | 1 | OK hooks 1 | Improves the Minecraft HUD while riding mounts, keeping hunger, mount ... |
| right_click_crops | 1.0.1 | 11-07 | 66f3981 | - | OK per registry (pin only) | Right-click harvest for 16 plant families, with replanting and individ... |
| rightharvest | 0.1.1 | 11-02 | 4aa6854 | 2 | OK hooks 2 | Right-click a ripe crop to pick it and sow it again. |
| rmotd | 1.0.0 | 11-01 | d91cab6 | 8 | OK hooks 8 | Rotating server list MOTDs, managed in game with /randommotd and /motd... |
| roughlyenoughitems | 1.1.0 | 11-09 | fdc87ae | - | exact fdc87ae | REI for Horizon: REI's item list, search, recipe screen, favorites, cr... |
| schematics | 1.0.0 | 11-05 | c9d474d | - | OK per registry (pin only) | Load schematics in every common format, see them as ghost blocks in th... |
| seedcrackerx | 0.2.3 | 11-05 | 6475f62 | - | OK per registry (pin only) | SeedCrackerX for Horizon: finds the world seed of a server from the st... |
| server_browser | 2.2.1 | 11-05 | 6475f62 | - | OK per registry (pin only) | Find and organize Minecraft servers with local notes, favorites, filte... |
| server_flags | 1.0.0 | 11-09 | fdc87ae | 411 | exact fdc87ae | A flag beside each server in the Multiplayer list for the country it's... |
| serverify | 0.1.0 | 10-30 | 6f8c7a0 | 1 | OK hooks 1 | Find Minecraft servers and add them to your Multiplayer list, from a p... |
| shulker_peek | 0.1.0 | 10-29 | 5e391eb | - | BROKEN E0061 | A shulker box's contents as a 9 x 3 grid in its tooltip. |
| shulkerboxtooltip | 1.0.1 | 11-09 | fdc87ae | - | exact fdc87ae | A port of ShulkerBoxTooltip: the contents of shulker boxes, chests, th... |
| simple_voice_chat | 1.0.0 | 11-05 | 3fb4c31 | 359 | OK hooks 359 | Client-side voice chat: mic capture, Opus, positional mixing, push-to-... |
| skins_3d | 1.1.0 | 11-06 | 66f3981 | - | OK per registry (pin only) | The outer layer of every player's skin drawn as real 3D pixels. |
| smartf3 | 0.1.0 | 10-29 | 142388e | - | BROKEN E0308 | A tidier, configurable F3 debug screen: the same information in module... |
| smoothie_capes | 0.5.1 | 11-08 | 298f165 | - | OK per registry (pin only) | An Wavey Capes inspired mod for Horizon |
| smoothswapping | 1.1.0 | 11-08 | 2ebf00a | - | OK per registry (pin only) | A port of Smooth Swapping: items fly from slot to slot instead of jump... |
| speedrun_timer | 1.0.1 | 11-04 | 6f8c7a0 | 1 | OK hooks 1 | Speedrun Timer Is a mod made to count the time it took you to beat the... |
| spider_man | 0.2.0 | 11-03 | 2944480 | - | BROKEN E_UNSUPPORTED_CONTROL_FLOW | Web swinging, zips, wall running and parkour, tuned against the consol... |
| spotify_hud | 1.0.0 | 11-05 | 20186e4 | 111 | OK hooks 111 | What Spotify is playing on your HUD, with play, pause, skip, shuffle, ... |
| status_effect_hud | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | 1:1 Status Effect Bars & Inventory HUD+ Potion HUD: displays active po... |
| strangely_charming | 0.2.11 | 11-08 | 2ebf00a | - | BROKEN E_TARGET_NOT_FOUND | An exploration and quality-of-life mod |
| stuck | 1.0.0 | 11-01 | d91cab6 | 28 | OK hooks 28 | /stuck and /escape move you to a safe spot nearby, off the Nether roof... |
| tectonic_horizon | 0.3.4 | 11-04 | 8dbbde4 | - | OK per registry (pin only) | Unofficial native port of Tectonic: mountain ranges, underground river... |
| toggle_sprint | 1.0.0 | 10-31 | ba6344a | 1 | OK hooks 1 | 1:1 Better Sprinting & Lunar ToggleSprint HUD: toggle sprint and toggl... |
| trails | 1.0.0 | 11-08 | 2ebf00a | 411 | OK hooks 411 | Paw prints, particles, lines or ribbons follow you as you move. Client... |
| treefall | 0.3.0 | 10-29 | 142388e | - | BROKEN E0599 | Cut one log of a natural tree with an axe and the whole tree comes dow... |
| veinminer | 0.3.2 | 10-31 | d91cab6 | - | OK per registry (pin only) | Mine connected ores and matching trees using Horizon's native player-m... |
| viahorizon | 0.8.8-dev | 11-08 | fdc87ae | - | exact fdc87ae | Connect to older Minecraft servers using Horizon 26.3. |
| visuality_horizon | 1.0.2 | 11-03 | c9d474d | - | OK per registry (pin only) | Small pixel particles: hit fragments, slime blobs, creeper sparks, gli... |
| voicechat | 1.0.0 | 11-02 | c9d474d | - | BROKEN E0599 | Talk with Simple Voice Chat players: proximity voice, groups, push to ... |
| voltz_core | 0.3.0 | 11-06 | 66f3981 | - | OK per registry (pin only) | Machines, power, pipes, a nuclear reactor, missiles, turrets and force... |
| wayfarer_stones_native | 0.6.3 | 11-08 | 67dad0d | 145 | OK hooks 145 | Place stones around your world, activate them, and travel between the ... |
| waymap | 0.2.1 | 11-05 | 6475f62 | - | OK per registry (pin only) | Persistent client-side waypoints with 3D world markers, minimap dots, ... |
| waypoints | 1.1.0 | 11-05 | c9d474d | - | OK per registry (pin only) | Place waypoints with N, manage them with M, and see their name and dis... |
| worldedit | 1.2.1 | 10-30 | 83f15fa | - | BROKEN E_MODULE | working port of java world edit |
| worldmap | 0.7.1 | 11-08 | fdc87ae | 404 | exact fdc87ae | A full screen, self-writing world map with a minimap, waypoints (group... |
| xtoxray | 2026.29.0 | 10-30 | 942e3b2 | 7 | BROKEN E0063 | Opensource Xraymod |
| zoom | 2.0.0 | 10-29 | 6f8c7a0 | 1 | OK hooks 1 | Hold a key to zoom in; the mouse wheel zooms further while you hold it... |
| zoomify | 1.1.1 | 11-09 | fdc87ae | - | exact fdc87ae | A port of Zoomify: a zoom key with smooth transitions, scroll zoom, a ... |
