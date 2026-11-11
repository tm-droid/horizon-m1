# R11: Horizon native mods, what they can do, how to port Tanush's Java mods (2026-11-06)

Read-only research. Nothing built or run. Source = f42 candidate (`SRC` = `outputs/horizon-runtime/m1-performance/candidate-source`), `NH` = `SRC/crates/horizon-client/src/game/native_hooks.rs` (11568 lines, 526 `native_*` fns, `NATIVE_HOOKS_API = 359` at NH:1033), `DOC` = `SRC/docs/native-mods.md`. Upstream main checked with `gh api` (updated 2026-11-06).
Converter = `outputs/horizon-converter/2026-11-05-Tanush-f42-v4` (`porting-index.json`, `tasks/mod-NNNN.json`).

## 0. What a "native mod" is (corrects the dylib assumption)

- NOT a dylib, NOT sandboxed. A native mod is a **horizon-mixins bundle**: Rust source patched into the game's own source, then the whole `horizon-client` is recompiled per instance (DOC:7-16, DOC:1543-1636). Two flavours:
  1. mixin bundle: `horizon-mixin.toml` + `.rs` helpers; injections HEAD/BEFORE_CALL/RETURN/MODIFY_ARG/OVERWRITE on any function (DOC:7-11).
  2. trait mod: `[api] path=...` crate exporting `hooks() -> Box<dyn Hooks>` linked into the game (DOC:2837-2870); may only use crates already in Horizon's `Cargo.lock` (DOC:2851).
- So "needs unsafe/dylib vs sandboxed" is moot: everything is full-trust in-process native code. No sandbox tier exists (DOC:1808 "does not sandbox the compiled game"). Old WebAssembly mods were the sandboxed tier; Zoom etc. migrated off it. Runtime dylib/wasm loading is only a proposal (#7386, open).
- Two ways to touch the game: **named hooks** (stable, `"hooks": N` in `horizon-native.json`, additive-only API, DOC:73-87) or **raw targets** (any function, e.g. `Game::camera_view`; pins the bundle to one Horizon commit, DOC:60-71). Existing community mods mix both: freecam patches `perspective::camera_view`, `own_body_in_view`, `turn_player`, `play_mouse`, `MotionWorld::controlled_simulation_tick_with_sprint_window` (hakergeniusz/freecam `horizon-mixin.toml`).

### Build / trust flow
- CLI: `horizon-launcher native-build [FOLDER] [--instance NAME] [--update] [--profile performance|dev|release] [--version TAG] [--allow-version-mismatch] --trust-native-code` (DOC:1567; flags DOC:67, 1545-1548). `--trust-native-code` is the player's consent; an agent must not supply it (DOC:1569, DOC:1842).
- Pipeline (DOC:1571-1636): pinned Rust 1.99.1 into launcher home; horizon-mixins built at pinned commit; ~63 MB source of the pinned commit; apply mixins to stage; `cargo build --locked --profile fast -p horizon-client`; post-build steps; installs `versions/native-<commit>-<key>` + `native-mods.json`.
- First build 20-30 min (DOC:1552); on this 8 GB M1 use `CARGO_BUILD_JOBS=1` (docs/horizon-converter/native-port-build-plan-2026-11-03.md:11). One-line change rebuild upstream measured 570 s vs 812 s cold (#9987). Use `--profile dev` only while developing (6x faster rebuild, game ~2x slower, DOC:1604-1608).
- Pin rules: `hooks: N` mods build on any Horizon with `NATIVE_HOOKS_API >= N`; raw-target mods pin a commit (DOC:60-87). f42 = 359.
- Trust: first install notice, red warning every build, registry lists only after maintainer review (DOC:1789-1809). Multiplayer: joining servers, only client-side hooks act (DOC:1815).

### Hot reload (upstream main)
- #9987 (design `docs/design/mod-hotload.md`) and #10217 are closed (presumably merged; not verified). Content mods (assets+data only) switch live; registries/worldgen need world reload; **native**: only built-in trait mods switch at runtime via `Hooks` dispatch (#10218, merged). Any new/changed native mod still needs a full rebuild; background builds / `RenderHooks` switching are "next" (#9987 text). `native_on(id)` gate exists in f42 (NH:2424 pattern). **Verdict: no hot reload of freshly written native code.**
- #10203 (closed): `horizon-mod-deps` adds mysql/redis/tungstenite/rusty-opus to Cargo.lock so native mods may depend on them; arbitrary crates still rejected (`E_CRATE_DEPENDENCY`).

## 1. Capability matrix (f42)

| Area | Hook / helper | file:line | Status / notes |
|---|---|---|---|
| HUD boxes | `native_hud(batch, corners)` (corner stacking, not under F1) | NH:2312 | Good. Draw with `native_fill` 9404, `native_text` 9670, `native_sprite` 9448, `native_item_stack` (API 313), `native_text_width` 9400 |
| HUD layers | `native_gui_layer_pre/post` per vanilla layer (crosshair, hotbar, effects, player_health, chat, ...; can cancel) | NH:2332, 2343 | Good. Debug screen + camera overlays are NOT layers (NH:2326) |
| Health/food HUD replace | `native_health_hud` | NH:2408 | Replaces rows; AppleSkin-style previews can overlay instead |
| Per-frame / tick | `native_frame`, `native_tick`, `native_player_tick` (server) | NH:2068, 2137, 2398 | Good |
| World rendering | `native_visuals` (block rims, local light sources, validated+limited), `native_block_highlight`, `native_world_drawn` (API 58, colour/depth/matrices), `native_render_fog`, `native_render_hand`, block entity / mob / player submit, `native_shader_params` | NH:2160, 2142, 2647, 2695, 2827; DOC:743 | Boxes/rims/lines OK; arbitrary block-model ghosts NOT (open #10442). `native_world_primitives` appears only in newer upstream (absent in f42) |
| Camera | `native_camera()` (pos, matrices, fov), `native_compute_fov(_modifier)`, `native_camera_distance` (3rd person), `native_camera_shake`, `native_movement_input` | NH:9617, 2596, 2562, 2770, 2669, 2577 | Read + tweak yes; **detached camera / shoulder offset has no named hook** -> raw targets (see freecam) |
| Keybinds | `native_key(name, pressed)` (any screen), `native_input_key` (winit event), `native_mouse_button_pre/post`, `native_mouse_scrolling`, `native_interaction_key`, `native_mapping(name)`, `native_mod_key(id,name,default)` | NH:2420, 2442, 2451, 2468, 2498, 2529, 9718, 9730 | Mod keys appear in Options>Mods list via `NativeMod.keys` (NH:2881-2896). Not vanilla Controls screen |
| Screens / GUI | `native_screen*` (draw over open screen, mouse/key/char pre-hooks), `native_mod_screen_open/close`, `native_screen`/`native_screen_draw`, slots/screen geometry reads | NH:3277-3544, 9557-9595, 10405-10452 | Can draw own full screens (Waymap editor, seedmap do). No widget toolkit; hand-drawn |
| Settings / config UI | `native_mods` list, `native_settings(mod_id, buttons)`, `native_settings_click` (button rows only) | NH:2881, 2901, 2921 | Buttons only: no sliders/text fields; richer UIs use own mod screen |
| Persistence | `native_setting/set_setting` (one file per key under `horizon-mods/.horizon-mod-data/<id>/`), `native_config_dir()` (`config/`), `native_data_dir`, `native_instance_dir`; plain `std::fs` also works (full trust) | NH:9769, 9774, 9785, 9758, 9752 | Good |
| Read world | `native_block(pos)` (name), `native_block_property`, `native_block_collision`, `native_light(pos)`, `native_weather`, `native_clock`, `native_world_height`, `native_biome_colors` | NH:9612, 9634, 9621, 9094, 9105, 9699, 9120, 2794 | Name-level block reads on main thread. Raw chunk/colour snapshots for worker threads: NOT in f42 (open #10152). Client entity list: **no named helper** (entity hooks are server-side: `native_entities_load` NH:6282, mob/player submit give per-frame callbacks only) |
| Client player state | `native_player()` = pos/yaw/pitch/dim only; `native_carried_stack` 9027; `native_frame_rate()` (fps, slowest, 1% low) 9709; `native_clicks` 9713; `native_physical_window_size` 9656; `native_cursor` 9661 | NH:9684, 9709 | **No named helper for health/food/saturation/inventory on the client.** `native_health_hud` carries a `HealthInputs` struct (NH:2408) so health/food/air is readable there; inventory needs raw access or `native_tooltip` (NH:6836) stack views |
| Tooltips | `native_tooltip`, `native_tooltip_color`, `native_tooltip_component(_draw)` | NH:6836, 6845, 6864, 6874 | Good; food previews can go in tooltips |
| Inventory | server: `native_inventory_ticks/slot_tick/carried_slot/hidden_slots`, `native_inventory_move_item`, panel API (`native_panel_items`, API 2); client: screen slot reads (NH:10432-10452), `native_screen_press` 10592 | NH:10074-10338, 6634 | Sorting/click sim possible via screen hooks (inventory_profiles does it) |
| Chat / commands | `native_chat(text)` client line, `native_commands`/`native_command` (client commands, API 35) | NH:9740, 2549 | Good |
| Sound | `native_play_local_sound` (play/delay), `native_music(_layers)`; server `native_play_sound` | NH:9363, 2806, 8781 | **No playback intercept/attenuate** (open #10444) |
| Networking | `native_net_from_client/server` mod messages between mod halves (API 40); server hooks (join/leave, chunks, damage, commands, menus...) | NH:7340, 7350; DOC:275 | Strong server side. Dedicated server needs `--server-output` export (DOC:1820) |
| Server / world events | ~300 hooks: block break/place, use, damage, loot, mobs, fluids, explosions | DOC:101-1460 | Far beyond what the client QoL set needs |
| Settings in vanilla options | `horizon-extras.txt`, built-in extras (fullbright, dynamic lights, mouse tweaks, sort, name tag) | SRC/docs/extras.md:3-100 | Built-in, off by default |
| Hot reload | see section 0 | #9987/#10217/#10218 | Content only; native = rebuild |

Biggest strengths: HUD/layers, keys/mouse, own screens, tooltips, server-side events, config/persistence, camera read/FOV. Biggest gaps: client entity + inventory + player-vitals read helpers, chunk snapshots/world map (#10152), sound intercept (#10444), block-model world primitives (#10442), detached camera / third-person offset, F3/debug screen hooks, stable (non-pinned) path for these.

## 2. Already in Horizon / registry (important: most are ports-for-free)

Built into f42: **fullbright** and **dynamic lights** (extras.md:45-63, off by default; torches/lava/fire lights, 16 nearest sources within 96 blocks, ignores walls), **Mouse Tweaks-style controls + inventory sorting** (extras.md:19-20), FPS counter / Keystrokes / Zoom / Minimap / Recipes / Coords HUD as official native mods (SRC/docs/mods.md:488-504; minimap draw engine kept in game: extras.md:74-81).
Registry (`horizon-rust/horizon-mods/mods/*.toml`, kind native-mod, game 26.3, MIT): `appleskin`, `appleskin_horizon` (CayMac), `freecam`, `freecam_plus`, `fair_freecam`, `freelook`, `fullbright` (MoreGamma, /gamma), `fullbright_horizon` (G, 1000%), `fullbright_nofog`, `inventory_profiles` (IPN+Sorter port), `mousetricks`, `mod_menu` (clean-room), `smartf3` (BetterF3-like), `waypoints`, `waymap`, `minimap`, `light_overlay`, `basic_hud`, `status_effect_hud`, `toggle_sprint`, `held_item_info`. **None** for Xaero World Map parity, Shoulder Surfing, Sound Physics, LambDynamicLights-specific. Registry presence is not a review/quality verdict for the community ones.

## 3. Port specs

Converter columns: `task_id`/`candidate_hooks` from `porting-index.json`. The converter's hook vocabulary is only `native_tick`, `native_key`, `native_hud` (62/56/15 of 239 mods) = coarse constant-pool heuristics, not an API mapping; it does not read or translate Java code. Per-task acceptance list (all mods, tasks/mod-NNNN.json) demands: inspect original, classify built-in / content-carry / Rust logic / unsupported, compile against runtime, test parity. `asset_carry` = `assets-only-runtime-unverified` for all but Mouse Tweaks (`no-assets`): lang/textures carried byte-preserved as `mod-asset-packs/mod-NNNN.zip`, behavior NOT.
**Converter provides for every spec below:** asset pack zip, candidate hooks list, task JSON with acceptance checklist, scan evidence under `mods/`. **Still manual:** all behavior, config import (e.g. `gammautils.json`), keybind mapping, build, visual test.

### 3.1 Xaero's Minimap + World Map (or simpler minimap)
- Converter: **no entry** (Xaero is disabled/not in the 239-mod index; nearest `mod-0237 Fast Surface []`, unrelated). Manual task needed.
- Hooks: `native_minimap` (NH:2831), `native_hud` 2312, `native_frame` 2068, `native_key` 2420, screens (NH:3277-3544) for a map screen, `native_command` for commands, `native_setting` for config. Game already draws the 128x128 map from cached 16x16 chunk tiles (extras.md:74-81).
- Bases: official `minimap` mod (DOC:86); **DenoxyYT/ayynoxs-map-pack** (MIT, "minimap and world map", pushed 2026-11-05; injects `native_minimap`, `native_hud`, `native_frame`, `native_key`, `native_command`, `native_net_from_client`, plus advancements-screen internals reused as a map screen: raw targets, so commit-pinned); **AzaelMew/horizon-seedmap** (MIT, Chunkbase-style seed map + minimap; named hooks only: frame/hud/key/mods/commands/screen mouse+key pre-hooks; worker.rs thread).
- Missing: explored-chunk disk cache beyond loaded chunks, entity radar, cave/slime-chunk modes, Xaero waypoint/map import. Needs #10152 (client world snapshots for worker threads) to be stable.
- Effort: simple minimap = **S** (install official/ayynoxs); Xaero-parity world map = **L**. Risks: raw-target pinning (ayynoxs), CPU budget (<0.3 ms/frame, extras.md:256), 8 GB RAM for cached map, seedmap needs seed (server-only on non-local worlds).

### 3.2 AppleSkin (mod-0065, candidate_hooks `[]`)
- Base: **CayMac97/appleskin** (MIT, = registry `appleskin_horizon`, "1:1 parity"; also registry `appleskin` by soufi). Targets: `native_mods`, `native_settings`, `native_settings_click`, plus raw `titles::draw_titles` (hud.rs).
- Hooks needed: `native_gui_layer_post("minecraft:player_health")` (NH:2343) or `native_health_hud` (NH:2408; has health/food/air inputs), `native_tooltip` (NH:6836) for food tooltips. Missing: stable saturation/exhaustion read and held-item food value helper (they use internals). 
- Effort **S** (install CayMac97 build, then diff config). Risk: raw `draw_titles` target = commit pin; check saturation numbers vs Java.

### 3.3 Freecam (mod-0133, hooks `native_key, native_tick`)
- Base: **hakergeniusz/freecam** (MIT, port of Freecam, pushed 2026-10-31; registry `freecam`; alternatives `freecam_plus`, `fair_freecam`). Raw targets: `perspective::camera_view`, `cycle_camera`, `own_body_in_view`, `turn_player`, `Game::aim`, `mapped_key`, `play_mouse`, `MotionWorld::controlled_simulation_tick_with_sprint_window`; named: `native_frame/hud/key/tick/mods/settings`.
- Missing named hooks: detached camera position/rotation override, input freeze (movement/aim/mouse) while detached, body visibility. `native_camera_distance` (API 112) and `native_movement_input` (NH:2577) cover only parts. User wants F4 (CLAUDE.md keybinds) and tripod/collision toggles (daily-use-viability-2026-11-03.md:44).
- Effort **M** (build + verify on f42; modifications to key F4 and settings). Risk: pinned raw targets break on newer Horizon; detached-camera is not "complete Freecam" without server-movement check; freeze of server movement is client-side only.

### 3.4 Fullbright / gamma (Gamma Utils mod-0023, hooks `native_key, native_tick`)
- Built-in extra `fullbright` (extras.md:45-48): lightmap-level, no key, no gamma steps. Registry `fullbright_horizon` (G key, 1000% smooth), `fullbright` (MoreGamma `/gamma`), `fullbright_nofog`.
- User config: `config/gammautils.json` gamma.value 15.0, default 100, toggled 1500 (native-settings-parity-2026-11-03.md:11). Hook needs: `native_key` + a lightmap/gamma setter; none named, built-in only offers on/off. Registry mods work through own raw targets.
- Effort **S** (use `fullbright_horizon` with G/H keys; map 15.0 -> its scale manually). Risk: gamma and night-vision parity unverified; interacts with MakeUp shader.

### 3.5 Mod Menu-like config (mod-0163, `native_key, native_tick`)
- Built in: Options > Mods lists native mods with key rebinding and a settings page (`native_mods` NH:2881, `native_settings` 2901, `native_settings_click` 2921; zoom shows the pattern at NH:2883-2943). Registry `mod_menu` adds a richer clean-room list.
- Missing: sliders/text inputs in settings (buttons only); per-mod icons/descriptions beyond `NativeMod{id,title,description,keys}`.
- Effort **S** (nothing to port; each ported mod registers itself). Custom UI: **M** via `native_mod_screen`.

### 3.6 Dynamic Lights, LambDynamicLights (mod-0148, `native_key`)
- Built in: `dynamicLights` extra (extras.md:50-63; `dynamic_light.rs`, `game/dynamic_lights.rs`, shaders). Issue #1162 shipped v2026.10.22 (ROADMAP.md:906). Off by default; enable in Extras (`horizon-extras.txt`).
- Gaps vs Lamb: per-item/entity light config, light not occluded by walls (explicitly "doesn't stop at walls"), 16-source cap, tile/entity shader interplay with MakeUp not tested.
- Effort **S** (enable), **M** to add per-item config via raw target in `dynamic_light::select`. Risk: render-path cost on 8 GB M1; needs bench.

### 3.7 Inventory Profiles Next (mod-0030, `native_key`) / Mouse Tweaks (mod-0041, `[]`, no-assets)
- Built in: Mouse Tweaks-style controls and inventory sort (extras.md:19-20, `game/tweaks.rs`, `inv_sort.rs`). Registry `inventory_profiles` (CayMac, IPN + Inventory Sorter port: R sort, auto-refill, tool-break protection, quick-stack) and `mousetricks` (d3grando).
- Hooks: `native_key`, `native_screen_*` pre hooks and `native_screen_slots/press` (NH:10432, 10592), `native_inventory_ticks` for server-side. 
- Missing: profile files/rules engine of IPN; saved profiles. Effort **S** (install) / **M** for IPN profile import.

### 3.8 Better F3 / FPS display (BetterF3 mod-0008 `[]`)
- FPS: official `fps-overlay` mod + `native_frame_rate()` (NH:9709). `smartf3` in registry (d3grando, modules, reorder, colours).
- F3 is not a GUI layer (NH:2326); deep F3 changes need raw target (`debug_overlay.rs`, `debug_entries.rs` exist in crate). Effort **S** (install) / **M** custom. Risk: raw target pin.

### 3.9 Waypoints (Xaero waypoints; no converter entry)
- Registry `waypoints` (Nirokx, N/M, in-world markers) and `waymap` (Aron: 3D markers, minimap dots, native editor screen, per-world files, death points). Hooks: `native_visuals`/`native_world_drawn` for markers, `native_mod_screen` for editor, `native_command` `/wp`, `native_player()` for pos, `native_setting`/`native_config_dir` for storage.
- Missing: Xaero waypoint file import (manual converter). Effort **S** (waymap) + **S/M** importer. Risk: waymap relies on minimap dot integration.

### 3.10 Shoulder Surfing (disabled on the instance; no converter entry)
- Hooks: `native_camera_distance` (NH:2770), `native_camera` read 9617, `native_compute_fov` 2596, `native_movement_input` 2577, `native_interaction_key` 2529 (crosshair), `native_gui_layer_pre("crosshair")` 2332 to move the crosshair. Missing: camera sideways/vertical offset hook, aim-from-camera raycast, collision of offset camera; freecam's raw `camera_view` shows it is feasible.
- No registry mod. Effort **M-L**. Risk: pinned raw targets, interaction raycast mismatch (hit point vs crosshair), possibly conflicts with freecam (same function).

### 3.11 Sound Physics Remastered (mod-0206, `[]`)
- Upstream blocker: **#10444 open**, "no sound playback hook" to attenuate/reverb played sounds; world reads for raymarch ride #10152 (open). Partial port exists: `Sparticle62ops/horizon-modport/ports/sound-physics-remastered` (acoustics core tested; slice 2 waits on the hook), per #10444.
- Hooks now: `native_play_local_sound` (NH:9363) plays only. Not portable 1:1 today. Effort **L**, blocked. Risk: CPU raymarching on M1 8 GB; reverb needs audio-engine access.

## 4. Recommended first 3 ports

1. **AppleSkin (CayMac97 build)**: highest value/effort. S. Existing, MIT, uses named settings hooks plus one raw target. Install, build, diff behaviour (also exercises the full native-build flow on the 8 GB M1 and sets up the one-time engine build cache).
2. **Freecam (hakergeniusz) + Fullbright (fullbright_horizon, G/H)** in ONE build: M + S. Matches the user's F4 and gamma keys; shares one rebuild (build cost dominates). Zoom pilot already stages the flow (outputs/horizon-native/zoom-f42-candidate, docs/.../native-port-build-plan-2026-11-03.md).
3. **Minimap/world map base: AzaelMew/horizon-seedmap or DenoxyYT/ayynoxs-map-pack** (or just official `minimap` + `waymap`): M. Prefer official minimap + waymap for waypoints; evaluate ayynoxs as the world-map base (raw targets pinned to a commit: check against f42). Skip Xaero parity for now.

Do NOT port: Dynamic Lights (enable built-in extra), Mod Menu (built into Options>Mods + registry), Inventory/Mouse Tweaks (built-in extras + registry). Defer: Shoulder Surfing (M-L, no base), Sound Physics (blocked by #10444).

### Does upstream plan any of these?
- Already shipped: dynamic lights (#1162), fullbright, Mouse Tweaks/sort, FPS/Keystrokes/Zoom/Minimap/Recipes. Roadmap asks (ROADMAP.md:515): angled world map, drag/scroll inventory tweaks, block info tooltips, schematic overlays.
- Open API requests: #10444 sound intercept (SPR), #10152 client world snapshots (minimaps/world maps/radars), #10442 block-model world primitives (Litematica), #10461 server hook points for plugin ports. #10425 (entity model layers) closed. #7386 (large mods without rebuild), #7387 (Host services) open.
- Not found upstream: Shoulder Surfing, Xaero import.

## 5. Caveats / unverified
- Registry/community repos: structure and hook targets inspected via GitHub tree and `horizon-mixin.toml`; no code was compiled or reviewed for safety. Native code = full trust: read before building.
- #9987/#10217 shown "closed", merged status inferred. `native_world_primitives` exists upstream per #10442, not in f42.
- Converter `candidate_hooks` are heuristics; per-mod task acceptance must be done anyway.
