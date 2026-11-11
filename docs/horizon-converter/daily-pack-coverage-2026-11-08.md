# Daily Horizon pack coverage — 2026-11-08

All 52 original selected ZIPs passed archive reads, with 5,426 PNG and 59 Ogg decodes. The earlier disposable world tests used the R11 client and MakeUp Ultra Fast 9.6. The live session below uses the November 7 nightly with 63 resource layers. Layer numbers refer to the original snapshot, before local overlays.

| Layers | Pack or group | Evidence and remaining checks |
|---|---|---|
| 1 | 1.18 Panorama | Archive checked. Compare the six title background faces in the actual title screen. |
| 2–3 | Connected Bricks, Connected Rocks | Matched mixed-material panels show the expected CTM overlay on stone beside brick and cobblestone. Other connection rules and emissive rocks remain unverified. |
| 4–7 | Colorful Leaves, Optimized Bushy Leaves, Bushier Bushes, Colorful Grasses | Loaded during the outdoor tests. Compare leaf edges, grass variant rotation, tint and pack priority on a fixed biome panel. |
| 8 | Fancy Crops | Full versus excluded fixture shows the selected mature wheat and carrot models. Other growth stages and plant types remain unverified. |
| 9 | Fresh Flowers and Plants | Archive checked. Separate block, held and GUI models, then check Java-only Hold My Items and Punchy data. |
| 10–12 | 3D Fungi, Fresh Flower Pots and its 3D add-on | Exclusion pair shows a different loose red mushroom/crimson fungus and potted warped fungus. Other pot models and rotations remain unverified. |
| 13–15 | Flowering Vines, Fluffy Carpets, Renewed Bookshelf | Archive checked. Compare directional vines, carpet edge depth and two bookshelf faces against controls. |
| 16–17 | Remodeled Doors, 3D Ladders | Oak doors were checked open and closed with both halves, alongside a wall-mounted ladder. Other materials, hinges and inventory views remain unverified. |
| 18 | RAYs 3D Rails | Straight, curved and powered geometry and state readback verified. Emissive, slope and other rail states remain separate. |
| 19 | Weskerson's Torches | Ground and wall torch sampled with a matched exclusion. Hold My Items poses, offhand, redstone and repeaters are separate. |
| 20 | Better Beds | Discovered that placed beds skipped the source `bed.jem`. Local overlay restores the raised pillow and quilt for 16 colors. Four colors/facings plus a red bed in hand and inventory verified. Original entity-atlas repaint on the mattress is outside this geometry fix. |
| 21 | Dramatic Skys | Archive contains OptiFine/MCPatcher sky stages. No matching loader path found in the R11 source scan; MakeUp draws its own sky. Dawn/noon/night comparison still needed before a runtime verdict. |
| 22 | Better Flame Particles | Archive checked. Compare visibly spawned torch/fire particles from fixed camera and weather. |
| 23–25 | Gentler Weather Sounds, Vocal Villagers, Colored Subtitles | Rain, thunder and villager events produced the expected subtitles/colors. Ogg decode and event paths verified. No recording of emitted audio samples. |
| 26 | Animated Items | Archive checked. Need frame-by-frame item preview and held animation for an explicitly targeted item. |
| 27 | Better Lanterns | Exclusion pair shows changed normal, soul and copper models in standing and hanging contexts, with iron and copper chains. Other oxidation/material states and particle textures remain unverified. |
| 28 | Fine Armoury | Redstone Sentry trim initially rendered gray. Restored missing palette metadata and verified worn red trim. Other armor materials and palettes not exhaustively sampled. |
| 29–30 | Visuals and Visual Armor Trims | Some terrain/item and trim assets load during broader checks. Polytone, per-item variants and inventory trim composition need dedicated controls. |
| 31–34 | Fresh Food, Buckets, Music Discs, Ores and Ingots | Fresh Buckets tropical fish bucket verified in inventory and first person. Other items, Java hand overlays and animation frames need individual checks. |
| 35 | New Glowing Ores | Prior ore tests cover the trimmed set; don't infer every CTM variant or depth/material combination. |
| 36–39 | Even Better Enchants, Teddy Totems, Low Shield, Low On Fire | Archive checked. Enchantment-dependent books, held/activated totem, main/offhand blocking and the fire overlay need matched captures. |
| 40–41 | Icons, Recolourful Containers | 24 functional screen checks and 33 views verified the container repairs, including recipe book, armor slots, smithing, beacon and station labels. Other fonts and non-English UI remain unverified; the log still records an unsupported text-shader function. |
| 42–46 | Fresh Animations, Extensions, Just Expressions, FA Player, 3D Harness | Multiple creature/body/equipment states and player idle/walk/jump tested. R11 validates explicit parts and texture variants on 12 fixtures. Stationary adult ghast fit verified; moving leash attachment, named harness and untested animation states remain open. |
| 47 | Minecarts with Wheels | Archive checked. Ordinary/chest and driven cart parity still needs a source and visual fixture. |
| 48 | Fresh Skeleton Physics | Bare skeleton horse standing and death poses checked. Saddle and reins remain separate. |
| 49 | Slightly Improved Font | General English UI was visible during functional checks. Need font-specific side-by-side and mixed glyphs. |
| 50–51 | Ender Eyes, Better End Portal Frames | Archive checked. Need empty/filled frame, held and placed eye, and active portal effects. |
| 52 | Tanush Fixes | Both sound definitions target Presence Footsteps namespaces. Native villager/weather checks do not exercise this Java feature. |

The Java audit is separate: 259 JAR archives read, and the in-house porter matched 239 exact source files. That establishes an inventory. Java execution, native replacements and gameplay parity each need their own evidence. For the next batch, prioritize the renderer gaps visible in the active stack, then compare inventory/held/item activation families together and test custom sky and text separately.

## Live November 7 nightly session

The session observed on November 8 used `nightly-2026-11-07-2ebf00a` with the same 63 selected layers. The R11 visual results above apply to the tested R11 executable. The nightly log reports these distinct runtime gaps.

- Eleven CEM files use per-part textures or sprites the nightly skips. They are trader llama, pillager, mule, iron golem, donkey, wandering trader, vindicator, sheep, stray, bogged and llama. Use a dyed sheep, a trader and a chested donkey or mule as the shortest visible checks for this shared capability.
- The player animation engine reads `is_gliding` as zero. Guardian and elder guardian logs contain missing body and tail targets. Salmon logs report missing fins and tail. These are model binding diagnostics. Motion and screenshots on this executable remain separate checks.
- The rejected shader helper `getCorner` is supplied by Recolourful Containers DARK in `assets/minecraft/shaders/include/interfaces.glsl`. Record the affected screen or glyph before changing the pack. The local GUI overlay covers the previously verified station cases.
- The MakeUp log records 14 setup runs across alternating Nether and Overworld folders through the 21:14 inspection. Setup took 8.19 seconds in total, with a median of 548 ms and a range of 356–1155 ms. The separately logged block-to-shader ID table accounts for 2.14 seconds of that total, with a median of 140 ms. The enclosing timer also covers pack reading, translation and pipeline creation. Existing steady-frame measurements are from separate R11 captures.
- The 21:11:17 F2 frame shows the third-person player rolling to one side with a level HUD and upright terrain. FA+Player v1.1's `a_player_variables.jpm` explicitly drives `var.root_rz` from turn speed, limb speed and smoothed strafe input. The frame establishes the pose. A stationary comparison is needed to decide whether it persists when the inputs settle.

The window capture timed out during this observation. Evidence comes from the active session's log, pack bytes and the saved F2 frame at `outputs/horizon-runtime/game/screenshots/2026-11-08_21.11.17.png`.

The available R11 source gives a concrete place to split the transition cost. `game/shader_packs.rs` reopens the ZIP and reads its properties, translates the dimension programs, resolves pack inputs, builds the sprite ID table, then calls `Renderer::set_shader_pack`. The renderer retains a single active dimension and replaces the previous `PackPost`. That structure owns render targets, temporal buffers, shadow state and compiled programs. A later fix should measure translation and pipeline creation separately on the exact nightly before choosing what to reuse. Retaining only reusable inputs or compiled programs would avoid keeping a second set of full-size frame targets and prevent stale history across dimension changes. Verify the return trip to each dimension, shader-option reload, resource-pack reload and memory footprint alongside visual parity.
