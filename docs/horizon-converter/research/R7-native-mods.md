# R7: Java mods vs Horizon built-ins and native mods

Date 2026-11-06. Scope: 259 files in `instances/Tanush-26.3/minecraft/mods` (239 enabled + 20 `.disabled`), mod ids read from `fabric.mod.json`. Horizon source: `outputs/horizon-runtime/m1-performance/candidate-source` (docs paths below are relative to its `docs/`). Registry: `horizon-rust/horizon-mods` main `d2de4c1` (2026-11-05, 94 entries: 84 native-mod, 3 mod, 5 shader, 1 resourcepack), read via `gh api` into scratch.

## Summary

| Class | Count |
|---|---|
| Built-in in Horizon (B, incl. both) | 31 |
| Native mod in registry (N, incl. both) | 39 |
| of which built-in AND native | 8 |
| Missing (feature with no equivalent) | 115 |
| N/A (library, perf/engine mod moot in a Rust client) | 82 |
| Total | 259 |

Notes that change the picture:
- Upstream `mods/` in horizon-rust/horizon holds only Java parity-test fixtures (`mods/horizon/src/{bench,test,neoforge-*}`), no native mods. Native mods live in `horizon-rust/horizon-mods`: `native/{coords-hud,fps-overlay,keystrokes,minimap,recipes,smp,tools,voicechat-server,zoom}` plus community entries in `mods/*.toml` (docs/mods.md:488-504 lists only the official six).
- Converter run `2026-11-05-Tanush-f42-v4` does not classify built-in vs native: `porting-index.json` only gives `asset_carry` (210 assets-only, 29 no-assets) and `candidate_hooks` per jar (key/tick/hud). It confirms the 239 active jars; no Java behaviour is converted (README.md: 'No Java behavior was translated').
- Registry entries are community-made with varying fidelity; 'native' means a registry entry covers the feature, not 1:1 parity. Partial coverage is spelled out in the Equivalent column.
- Zoom and CEM/ETF aliases: counted as covered per the task brief (docs/extras.md:67; resource-packs.md:41-42).
- Built-in extras are all default off (extras.md:4). The user's feature list (fullbright, dynamic lights, mouse tweaks, sort, smooth chat) is therefore covered once enabled.

## Top 10 missing, ranked by value to the user

Ranking weights the user's stated priorities (minimap/waypoints, freecam, fullbright, inventory/HUD/chat tweaks, dynamic lights, sound). Freecam, fullbright, dynamic lights, minimap core and waypoints are already covered, so they do not appear. Effort: S = under a day, one hook set already present; M = a few days or one new hook; L = engine work.

| # | Java mod | Area | Effort | Why / what it needs |
|---|---|---|---|---|
| 1 | InvMove (invmove) | inventory | S | Hooks exist: `native_movement_input` (native-mods.md:992) and screen key hooks (native-mods.md:895 area). Client-only: keep WASD/jump live while a container screen is open, skip text fields. Tiny, daily-use. |
| 2 | ChatPatches (chatpatches) | chat | M | Chat history beyond 100 lines, search, timestamps, copy-to-clipboard. Hook `native_chat` exists; needs own persistent buffer plus a drawn search box. Registry only has chat_animation/chatheads. |
| 3 | SoundController (soundcontroller) | sound | M | Per-sound-event volume sliders and mute. extras.md:116,225 only cover UI-channel reserve and music page. Needs a per-event volume hook (not in native-mods.md; likely a new hook API, sound-engine side) plus settings screen. |
| 4 | Xaero's World Map (xaeroworldmap, disabled) | map | L | Fullscreen explored-chunk map. Registry minimap/waypoints/waymap give a corner map and waypoints only. Needs chunk-tile cache persistence plus a full screen; engine already builds 16x16 map tiles (extras.md:75-80) so reuse is possible. User disabled it (suspected Xaero join fix), still a stated minimap priority. |
| 5 | Stack To Nearby Chests (stack-to-nearby-chests) | inventory | M | Quick-stack/restock into nearby containers. Client packet sequence: open each container, move items. Hooks: `native_inventory_ticks`/screen hooks; server-side `native_inventory_move_item` (native-mods.md:1492) is hopper only, so client clicks must be simulated. Needs a container-click helper. |
| 6 | Clickthrough Plus (clickthrough) | inventory/QoL | M | Click through signs/item frames to the chest behind. Needs a client raycast override at interaction time (`native_interaction_key`, `native_block_highlight`); server-side `native_right_click_block` (API 21) cannot retarget. Medium: needs a client interaction-target hook. |
| 7 | Item Borders (itemborders) | inventory | S | Rarity-coloured borders on item slots. `native_screen_slot*`, `native_slot_tick` and `native_tooltip_color` (rarity) hooks exist; draw rect behind each slot. Small. (Related lookups in the registry: itemnew only.) |
| 8 | Controlling (controlling) | input | M | Keybind search and conflict highlight on the Controls screen. Horizon draws its own options UI (options_ui.rs); needs either an engine setting or a screen hook on the keybinds page. Medium. |
| 9 | Tooltip Scroll (tooltip-scroll) | tooltip | S | Scroll long tooltips. `native_screen_mouse_scrolled_pre` (native-mods.md:895) plus `native_tooltip` lines (API 12) already available. Small. |
| 10 | Sound Physics Remastered (sound_physics_remastered) | sound | L | Reverb and occlusion. `native_play_local_sound` (native-mods.md:2624) only triggers sounds; there is no DSP, raycast-to-listener or per-source filter hook. Needs engine audio work (OpenAL EFX equivalent) before any mod. Highest sound value, highest cost. |

Next candidates: Better Advancements (advancement screen), BetterStats, Camera Overhaul (`native_camera`, native-mods.md:3218), Legendary Tooltips (`native_tooltip_component_draw`), Better Mount HUD (`native_health_hud` API 27), PingView, Tweakeroo remainder.

## Per-mod table

Status: B built-in, N native registry mod, B+N both, MISSING, n/a. Libraries and engine mods are collapsed into groups after the table.

| Java mod (id) | State | Category | Status | Horizon equivalent |
|---|---|---|---|---|
| A Good Place (`a_good_place`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Advancement Plaques (`advancementplaques`) | on | visual/QoL | MISSING | nothing equivalent |
| AmbientEnvironment (`ambientenvironment`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| AmbientSounds (`ambientsounds`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Audio Engine Tweaks (`audio_engine_tweaks`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Axolotl Buckets (`axolotlbuckets`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Better Selection (`better-selection`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Better Snow Coverage (`better-snow-coverage`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Better Advancements (`betteradvancements`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Better Clouds (`betterclouds`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Better F1 (`betterf1`) | on | misc QoL/UI | MISSING | nothing equivalent |
| BetterGrassify (`bettergrass`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Better Mount HUD (`bettermounthud`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Better Smoke (`bettersmoke`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Better Statistics Screen (`betterstats`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Big Water (`bigwater`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Blur+ (`blur`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Boat Item View (`boatiview`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| CameraOverhaul (`cameraoverhaul`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Cape Provider (`cape-provider`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Chat Patches (`chatpatches`) | on | chat | MISSING | nothing equivalent (hook native_chat exists) |
| Cherished Worlds (`cherishedworlds`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Cinematic Respawn (`cinematic_respawn`) | on | misc QoL/UI | MISSING | nothing equivalent |
| ClickThrough Plus (`clickthrough`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Clumps (`clumps`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| CMD + Delete (`cmd_delete`) | on | chat | MISSING | nothing equivalent (hook native_chat exists) |
| CommandQMod (`commandqmod`) | on | chat | MISSING | nothing equivalent (hook native_chat exists) |
| Controlling (`controlling`) | on | input | MISSING | nothing: keybind search/conflict UI |
| CoolRain (`coolrain`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Cosy Critters & Creepy Crawlies (`cosycritters`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Delete Worlds To Trash (`deleteworldstotrash`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Dense Flowers (`dense-flowers`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Durability Notifier (`durabilitynotifier`) | disabled | misc QoL/UI | MISSING | nothing equivalent |
| e4mc (`e4mc`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Particle Interactions (`eg_particle_interactions`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Elytra physics (`elytra_physics`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Elytra Trims (`elytratrims`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Enchanted Fishing Line (`enchanted_fishing_line`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Explosive Enhancement (`explosiveenhancement`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Falling Leaves (`fallingleaves`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| FastBack (`fastback`) | on | misc QoL/UI | MISSING | nothing equivalent |
| FirstPerson (`firstperson`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Flashback (`flashback`) | disabled | misc QoL/UI | MISSING | nothing equivalent |
| Footprint Particle (`footprintparticle`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Fancy World Animations (`fwa`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Glowing Torchflower (`glowing-torchflower`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Grassier Grass (`grassiergrass`) | disabled | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Handful (`handful`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Hear the Wind (`hear_the_wind`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Horse Stats Vanilla (`horsestatsvanilla`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Hover Items (`hover_items_bundle`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Immersive Hotbar (`immersive-hotbar`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Immersive Storms (`immersive-storms`) | disabled | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Inventory Particles (`inventory_particles`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| InvMove (`invmove`) | on | inventory | MISSING | nothing; hooks exist: native_movement_input (native-mods.md:992), native_screen_key_pressed_pre |
| Item Particles (`item_particles`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Item Borders (`itemborders`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Ji AFK Cinematic (`ji-afk-cinematic`) | on | misc QoL/UI | MISSING | nothing equivalent |
| LeadPhysics (`leadphysics`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Leave My Bars Alone (`leavemybarsalone`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Legendary Tooltips (`legendarytooltips`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Logarithmic Volume Control (`logarithmic-volume-control`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Make Bubbles Pop (`make_bubbles_pop`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| No Chat Reports (`nochatreports`) | on | chat | MISSING | nothing equivalent (hook native_chat exists) |
| NoRecipeBook (`norecipebook`) | disabled | misc QoL/UI | MISSING | nothing equivalent |
| Now Playing (`nowplaying`) | disabled | misc QoL/UI | MISSING | nothing equivalent |
| Paperdoll (`paperdoll`) | disabled | misc QoL/UI | MISSING | nothing equivalent |
| Particle Rain (`particlerain`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Particle Tweaks (`particletweaks`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Particular Reforged (`particular`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Pause Music on Pause (`pause_music_on_pause`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Ping View (`pingview`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Presence Footsteps (`presencefootsteps`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Recipe Book Reveal (`recipe-book-reveal`) | on | inventory | MISSING | nothing (recipe book itself matches vanilla, README.md:46) |
| Screencopy (`screencopy`) | on | visual/QoL | MISSING | nothing equivalent |
| SeedCrackerX (`seedcrackerx`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Shadow Drop (`shadowdrop`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Shield Fixes (`shieldfixes`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Shield Status (`shieldstatus`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Shoulder Surfing Reloaded (`shouldersurfing`) | disabled | camera | MISSING | nothing equivalent (disabled by user) |
| Show My World (`showmyworld`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Shut Up Dead Entities (`shut_up_dead_entities`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Simple Music Control (`simple_music_control`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Smooth F5 (`smooth_f5`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Smooth Steps (`smooth_steps`) | on | misc QoL/UI | MISSING | nothing equivalent |
| SmoothGui (`smoothgui`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Smooth Scrolling Refurbished (`smoothscrollingrefurbished`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Smooth Skies (`smoothskies`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Smooth Swapping (`smoothswapping`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Soft Imprints (`softimprints`) | disabled | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Sound Physics Remastered (`sound_physics_remastered`) | on | sound | MISSING | nothing: reverb/occlusion DSP (native_play_local_sound, native-mods.md:2624, plays sounds only) |
| Sound Controller (`soundcontroller`) | on | sound | MISSING | nothing: per-sound volume (extras.md:116 only reserves UI channels, :225 music page) |
| Sound Culling (`soundculling`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Sounds (`sounds`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Spyglass Astronomy (`spyglass_astronomy`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Sodium Shadowy Path Blocks (`sspb`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Stack to Nearby Chests (`stack-to-nearby-chests`) | on | inventory/tooltip | MISSING | nothing equivalent |
| Stendhal (`stendhal`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Stfu (`stfu`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| stupid block animations (`stupid-block-animations`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Subtle Effects (`subtle_effects`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Swinging Lanterns (`swinginglanterns`) | disabled | misc QoL/UI | MISSING | nothing equivalent |
| Telepistons (`telepistons`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Tightfire (`tightfire`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Tools On My Back (TOMB) (`tools_on_my_back`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Tooltip Scroll (`tooltipscroll`) | on | inventory/tooltip | MISSING | nothing equivalent |
| True Adaptive Music (`trueadaptivemusic`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Vectorientation (`vectorientation`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Visual Workbench (`visualworkbench`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Wakes (`wakes`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Drip Sounds (`waterdripsound`) | on | sound | MISSING | nothing equivalent (music page extras.md:225 covers music selection only) |
| Wavify (`wavify`) | on | visual | MISSING | nothing equivalent (cosmetic/visual effect) |
| Windy (`windy`) | on | visual/QoL | MISSING | nothing equivalent |
| World Play Time Reborn (`worldplaytimereborn`) | on | misc QoL/UI | MISSING | nothing equivalent |
| Xaero's World Map (`xaeroworldmap`) | disabled | map | MISSING | nothing: fullscreen explored-chunk world map |
| Accurate Block Placement (`accurateblockplacement`) | on | building | native | registry accurate_block_placement |
| AppleSkin (`appleskin`) | on | HUD | native | registry appleskin, appleskin_horizon |
| BetterF3 (`betterf3`) | on | HUD | native | registry smartf3 |
| Chat Heads (`chat_heads`) | on | chat | native | registry chatheads |
| Detail Armor Bar Reconstructed (`detailabreconst`) | on | HUD | native | registry armor_status, armorhud (partial) |
| Durability Tooltip (`durabilitytooltip`) | on | tooltip | native | registry held_item_info/basic_hud (durability partial) |
| Dynamic Crosshair (`dynamiccrosshair`) | on | HUD | native | registry crosshair_indicator (partial: reach colouring only) |
| Effect Insights (`effectinsights`) | on | HUD | native | registry status_effect_hud |
| Elytra Contrails (`elytratrails`) | on | visual | native | registry elytratrails |
| EnchantmentDescriptions (`enchdesc`) | on | tooltip | native | registry enchantmenthints (English/Russian) |
| Freecam (`freecam`) | on | freecam | native | registry freecam, freecam_plus, fair_freecam |
| Freelook (`freelook`) | on | camera | native | registry freelook |
| Held Item Info (`held-item-info`) | on | HUD | native | registry held_item_info |
| Highlighter (`highlighter`) | on | inventory | native | registry itemnew |
| ItemPhysicLite (`itemphysiclite`) | on | visual | native | registry horizon_physics (partial) |
| Jade (`jade`) | on | HUD | native | registry jade, lookat, blockscope |
| Just Enough Items (`jei`) | on | inventory | native | registry jei, recipes |
| Litematica (`litematica`) | on | building | native | registry horizonmatica (schematic ghost blocks, verifier, printer) |
| MiniHUD (`minihud`) | on | HUD | native | registry light_overlay (spawn overlay only), smartf3; no structure/chunk bounds overlays |
| Mod Menu (`modmenu`) | on | UI | native | registry mod_menu |
| Pick Up Notifier (`pickupnotifier`) | on | HUD | native | registry basic_hud (recent pickups) |
| Resourcify (`resourcify`) | on | UI | native | registry resourcify |
| Shulker Box Tooltip (`shulkerboxtooltip`) | on | tooltip | native | registry shulker_peek (3x9 grid only; no ender chest/loot preview) |
| 3d-Skin-Layers (`skinlayers3d`) | on | visual | native | registry skins_3d |
| Status Effect Bars (`status-effect-bars`) | on | HUD | native | registry status_effect_hud |
| Tweakeroo (`tweakeroo`) | on | QoL | native | registry accurate_block_placement, toggle_sprint, fly_speed (partial; most tweaks absent) |
| ViaFabricPlus (`viafabricplus`) | on | multiplayer | native | registry viahorizon |
| Visuality (`visuality`) | on | visual | native | registry visuality_horizon |
| Simple Voice Chat (`voicechat`) | on | voice | native | registry voicechat, voicechat-server |
| WaveyCapes (`waveycapes`) | on | visual | native | registry smoothie_capes |
| Xaero's Minimap (`xaerominimap`) | disabled | map | native | registry minimap (corner map only; engine support native_minimap, extras.md:69-80), waypoints, waymap; no Xaero parity (cave mode, entity radar) |
| ChatAnimation (`chatanimation`) | on | chat | built-in+native | extras.md:170 (smooth chat); registry chat_animation |
| Continuity (`continuity`) | on | resource pack | built-in+native | resource-packs.md:43 (every CTM method); registry connected_textures |
| Distant Horizons (`distanthorizons`) | disabled | LOD | built-in+native | graphics.md:64 (LOD Distance); registry distant_horizons |
| Dynamic FPS (`dynamic_fps`) | on | perf | built-in+native | graphics.md:24,29 (inactivity framerate, battery mode); registry dynamic_fps_for_rust; hook native_framerate_limit (native-mods.md:1156) |
| Gamma Utils (`gammautils`) | on | fullbright | built-in+native | extras.md:45 (fullbright); registry fullbright, fullbright_horizon, fullbright_nofog |
| Inventory Profiles Next (`inventoryprofilesnext`) | on | inventory | built-in+native | extras.md:158 (sorting); registry inventory_profiles, inventory_wizard |
| Mouse Tweaks (`mousetweaks`) | on | inventory | built-in+native | extras.md:128 (Mouse Tweaks controls); registry mousetricks |
| Zoomify (`zoomify`) | on | zoom | built-in+native | registry zoom, classic_zoom; extras.md:67 (zoom moved to native mod) |
| Animatica Refabricated (`animatica`) | on | resource pack | built-in | resource-packs.md:23-45 partly (GUI sprites, colormaps, sky); OptiGUI/Polytone/Animatica formats not confirmed, port-ledger check needed |
| Better Biome Blend (`betterbiomeblend`) | on | visual | built-in | graphics.md:26 (biome blend) |
| BBE (`betterblockentities`) | on | perf | built-in | graphics.md:39 (block entity switches) |
| BetterRenderDistance (`betterrenderdistance`) | on | perf | built-in | graphics.md:24 (render/simulation distance) |
| BlockEntityDistance (`blockentitydistance`) | on | perf | built-in | graphics.md:39 (block entity switches) |
| Bobby (`bobby`) | on | LOD | built-in | graphics.md:64 partial (LOD Distance; Bobby caches chunks, not same) |
| Chunks Fade In (`chunksfadein`) | on | visual | built-in | graphics.md:26 (chunk fade) |
| Chunky (`chunky`) | on | server | built-in | docs/pregeneration.md:1 (/pregen) |
| EMF Compat: Not Enough Animations (`emf_compat_not_enough_animations`) | on | resource pack | built-in | resource-packs.md:41-42 (CEM/ETF, random, emissive, blink); aliases ported natively |
| Entity View Distance (`entity-view-distance`) | on | perf | built-in | graphics.md:26 (entity distance) |
| Entity Model Features (`entity_model_features`) | on | resource pack | built-in | resource-packs.md:41-42 (CEM/ETF, random, emissive, blink); aliases ported natively |
| Entity Texture Features (`entity_texture_features`) | on | resource pack | built-in | resource-packs.md:41-42 (CEM/ETF, random, emissive, blink); aliases ported natively |
| EntityCulling (`entityculling`) | on | perf | built-in | graphics.md:29,35 (cave/entity/leaf culling) |
| Iris (`iris`) | on | shaders | built-in | shaders.md:7 (Iris/OptiFine shader loader); IrisSearch is UI only |
| IrisSearch (`iris_search`) | on | shaders | built-in | shaders.md:7 (Iris/OptiFine shader loader); IrisSearch is UI only |
| Iris Shader Folder (`iris_shader_folder`) | on | shaders | built-in | shaders.md:7 (Iris/OptiFine shader loader); IrisSearch is UI only |
| LambDynamicLights (`lambdynlights`) | on | dynamic lights | built-in | extras.md:50-63 (dynamicLights extra, 16 sources, 96 blocks, ignores walls) |
| More Culling (`moreculling`) | on | perf | built-in | graphics.md:29,35 (cave/entity/leaf culling) |
| NotEnoughAnimations (`notenoughanimations`) | on | resource pack | built-in | resource-packs.md:41-42 (CEM/ETF, random, emissive, blink); aliases ported natively |
| OfflineLAN (`offlinelan`) | on | multiplayer | built-in | agent-control.md:123 (Pause > Open to LAN); offline-account specifics unverified |
| OptiGUI (`optigui`) | on | resource pack | built-in | resource-packs.md:23-45 partly (GUI sprites, colormaps, sky); OptiGUI/Polytone/Animatica formats not confirmed, port-ledger check needed |
| Polytone (`polytone`) | on | resource pack | built-in | resource-packs.md:23-45 partly (GUI sprites, colormaps, sky); OptiGUI/Polytone/Animatica formats not confirmed, port-ledger check needed |
| Skyboxify (`skyboxify`) | on | resource pack | built-in | resource-packs.md:23-45 partly (GUI sprites, colormaps, sky); OptiGUI/Polytone/Animatica formats not confirmed, port-ledger check needed |

### n/a group (82)
Libraries and perf/engine mods with no meaning in Horizon (renderer, mesher, loader, world gen are Rust): animated-mojang-logo, architectury, async-pack-scan, asynclogger, asyncparticles, authme, badoptimizations, baguettelib, betterloadingscreen, c2me, cloth-config, configurable, creativecore, debugify, eclipseui, emf_compat_core, fabric-api, fabric-language-kotlin, fastipping, fastquit, ferritecore, forcecloseworldloadingscreen, forgeconfigapiport, frozenlib, fzzy_config, gnetum, iceberg, immediatelyfast, ixeris, jasione, krypton, ksyxis, languagereload, libipn, libjf, lighty, lithium, mac-colorspace-rollback, macos_input_fixes_helper, malilib, metallum, mezz_config, midnightlib, modernfix, mossylib, mru, neruina, no-resource-pack-warnings, norealmsbutton, notenoughcrashes, packetfixer, papi, particle_core, placeholder-api, prickle, prism, puzzleslib, quick-pack, reeses-sodium-options, resourcefulconfig, respackopts, rrls, rsls, scalablelux, searchables, smoothtexturefix, sodium-extra, spark, structure_layout_optimizer, supermartijn642configlib, tcdcommons, timelesslib, vmp, walksylib, yeetusexperimentus, yet_another_config_lib_v3, zconfig, zfastnoise, zfastsurface, zmatcomp.

## Sources and caveats
- Built-in evidence: docs/graphics.md:24-29 (settings pages), :35 (entity culling), :39 (block entities), :64 (LOD Distance); docs/resource-packs.md:41-45 (CEM/ETF/CTM/emissive), :80 (CIT); docs/extras.md:45-63 (fullbright, dynamic lights), :128,158,170 (mouse tweaks, sort, smooth chat); docs/pregeneration.md (Chunky equivalent); docs/agent-control.md:123 (LAN).
- Hook evidence: docs/native-mods.md (API list, e.g. :895, :992, :1156, :1492, :2624, :3218) and `crates/horizon-client/src/game/native_hooks.rs` (528 hooks).
- Classification is by jar id and description, not by decompiling features; 'MISSING' means no registry entry or built-in setting was found, not that nothing partial exists. Verify before porting with `tools/port_ledger.py` (vanilla-parity skill).
- Optigui, Polytone, Animatica, Skyboxify mapped to 'built-in' on the strength of general pack support (resource-packs.md:23-45); their specific formats are unconfirmed.
- Repo text treated as data; nothing executed. Scratch: registry tomls under the session scratchpad `hm/`.
