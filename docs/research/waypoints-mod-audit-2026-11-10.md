# Audit: daniliammo Minimap, Worldmap and Waypoints Reworked v0.5.0

Date: 2026-11-10. Read-only audit, nothing built. Mod git 20f1d56, written for Horizon 2ebf00a, to be built on fdc87ae.

Mod path: `/Users/tanushmalhotra/Developer/Horizon/outputs/horizon-runtime/m1-performance-r12/mod-src/daniliammo__Minimap-Worldmap-and-waypoints-reworked`
Mixin dir: `mixins/minimap_worldmap_waypoints_reworked/` (runtime.rs 5130 lines, client.rs 4193, binding_ui.rs, small helpers, horizon-mixin.toml).
Reference tree: `outputs/horizon-runtime/m1-performance-r12/20261110-195836/source/crates`.

Verdict: SHIP WITH SETTINGS. Preset the settings file before first launch, and watch memory when exploring caves or the Nether. Confirm with one real compile, since I could not build.

## Architecture

- Three injected modules: `runtime` and `client` (reworked_maps) in game.rs, `keybindings` (minimap_binding_ui) in options_ui.rs, plus `lod_adapter` in lod.rs.
- One background thread "map-terrain" fed by a sync_channel of 8 jobs. A global `Mutex<State>` is used only on the client thread.
- The mod replaces the old `minimap` mod. The old mod provided the `native_minimap` injection that drives Horizon's own minimap (`extras.rs update_minimap`, active only when `native_minimap_now()` is Some). This mod does not, so the core minimap stays off and this mod draws only when `native_minimap_now().is_none()`.

## 1. Memory

Per terrain tile (runtime.rs ~2313-2336): pixels 1024 B, heights 1024 B, walls 256 B, portals Vec, biomes `Vec<Option<Arc<str>>>` 256 x 16 B = 4096 B. About 6.5-6.6 KB per tile, with biomes about 62% of it.

The cache is UNCAPPED.
- `Cache::insert` (runtime.rs:3053-3081) and `insert_lod` (:3082-3129) have no eviction. README and PERFORMANCE.md say the old 512-LOD and 4096-terrain limits were removed on purpose. The cache clears only on session change (world or server identity, disconnect, relogin).
- Key space is `(Dimension, Layer, cx, cz)`. `Layer::Below(head_y)` is chosen in the Nether or when skylight at head is 0 (client.rs:2148-2158). Each distinct head Y in caves or the Nether creates a new key space of up to 625 tiles at render distance 12 (about 4 MB per Y).
- A layer change resubmits every chunk because the `seen` check misses (client.rs:2406-2414). Worst case about 80 tiles/s, 0.5 MB/s, with no ceiling.
- Rough growth: 100k chunks is about 660 MB. A long cave or Nether session on 8 GB hardware is the real risk, since the game already sits near 3.2 GB.
- Coverage rebuild (runtime.rs:3130-3158, :3519-3529): every changed batch rebuilds `Coverage` (BTreeMaps of Arc clones, LOD masks) and the `resident` BTreeSet. O(N tiles) per batch, 100-300 KB of churn.

Other memory:
- Waypoints: MAX_WAYPOINTS 64 per world, MAX_TOTAL_WAYPOINTS 4096 (runtime.rs:1318-1319), about 400 KB max. Settings file read limit 16 MiB (runtime.rs:1836).
- GPU: `MOD_IMAGE_SPRITE` is a 1024x1024 RGBA atlas slot, 4 MiB (hud.rs:131-132). The slot exists whenever native mods are built (`built_with_native_mods`, game.rs:2327), so there is no new VRAM versus the current build.
- Minimap frame texture = `(size*4).clamp(64,1024)` per side (client.rs:2618): size 64 gives 256 KB, 128 (default) gives 1 MiB, 256 gives 4 MiB. Each upload also does `rgba.to_vec()` (native_hooks.rs:12791-).
- LOD tiles come only from `game.lod` (client.rs:2185-2343). The user's `horizon-graphics.txt` has `lodDistance:0`, so LOD is likely off (not confirmed).

Estimate at render distance 12, surface play: 5-8 MB terrain and presentation plus 1-3 MB minimap buffers. Cave, Nether and exploration play grow it without bound.

## 2. Per-frame CPU

All numbers are estimates from reading, not measurements.

`frame` hook (client.rs:2065-2683):
- Every frame: clones the world's waypoint Vec (up to 64), builds `maps.portals()` Vec, and calls `runtime::initialize(game.native_data_dir(..))`. `native_data_dir` uses `std::env::current_dir()` (options.rs:100) plus PathBuf joins, so a getcwd syscall plus allocations per call. Also repeated in hud() and draw(). Small cost.
- Every 50 ms scan (client.rs:2346-2596): collects Weak refs for all loaded chunks (about 625), sorts with `View::demands` (sin_cos, runtime.rs:2566-2581), runs `seen.retain`, submits at most 4 chunk samples per scan (`sent == 4`, client.rs:2592) via `native_client_chunks` on 3x3 areas. Estimated 1-1.5 ms per scan, about 5% of main-thread frame time at 30 FPS.
- Any block update that replaces a chunk Arc triggers an immediate resample, capped at 4 per 50 ms (80/s). Initial join of 625 chunks takes about 8 s.

Minimap raster is CPU, not GPU:
- `Cache::render` (runtime.rs:3282-3407) allocates `vec![0; w*h*4]` and loops per pixel with relief shading. The camera eases (EASE_RATE 24/s, runtime.rs:2619+), so while moving the view changes every frame: full re-raster plus upload each frame.
- 512x512 at default is about 262k px per frame; 256x256 at size 64 is about 65k px, 4x less.
- Runs on the worker thread, not the render thread, but costs memory bandwidth and a 1 MiB alloc and copy per frame at the default. Stops when stationary (worker blocks on recv, `same && !changed` skips).

World map: baked once per repository change, drawn as quads from the shared atlas. PERFORMANCE.md quotes 0.025-0.05 ms per frame for quad clipping; historical, not rerun.

HUD (client.rs:2685-2862): `coordinate_lines` allocates strings per frame when coordinates are on. `draw_world_waypoints` allocates a letter String per visible waypoint per frame (client.rs:1995-2037).

Bonus: `render_map_only` (render.rs) skips the 3D world when the full map covers it (`covers_world`, client.rs:3415), which saves GPU time while the map is open. It replicates part of `render_frame` but omits `pbr_normals.pack()` and `pbr_specular.pack()` (game.rs:15132+). Minor behavior difference.

CPU risk: low to moderate. The game is GPU-bound at 30-38 FPS, and the heavy work is on the worker thread.

### Settings (runtime.rs:227-255 Settings, 258-330 decode, 322-340 encode)

Keys: `enabled`, `corner` (top_left|top_right|bottom_left|bottom_right), `size`, `shape` (round|square), `zoom`, `rotate`, `mini_dimension`, `world_dimension`, `overworld_coordinates`, `nether_coordinates`.
Allowed values: SIZES = 64, 96, 128, 160, 192, 224, 256; ZOOMS = 0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 4.0 (runtime.rs:24-25). Anything else is ignored.
Defaults: enabled true, top_right, size 128, zoom 1.0, rotate false, square, dimensions player, both coordinate flags true.

There is NO "distant smoothing" setting and NO "retain cached biomes" setting in 0.5.0. Smoothing was removed (CHANGELOG.md:16); a legacy `smooth_worldmap=` key is ignored. `Cache::insert` always copies prior biomes into a resampled tile. The only real cost levers are `size` (raster side = size x 4) and the coordinate flags. Zoom does not change raster cost.

Settings file:
`~/Library/Application Support/horizon/horizon-mods/.horizon-mod-data/minimap_worldmap_waypoints_reworked/settings.ini`
(cwd is the horizon support dir; `native_data_dir` at native_hooks.rs:13241, `game_dir()` at options.rs:100.) Format is `key=value` lines under `# Minimap Reworked settings`; waypoints are `waypoint_v3=` records in the same file. Written atomically (tmp + rename + sync_all, runtime.rs:1876-1895) by a settings worker.

Recommended M1 8 GB values:
```
enabled=true
corner=top_right
size=64
shape=square
zoom=1
rotate=false
mini_dimension=player
world_dimension=player
overworld_coordinates=false
nether_coordinates=false
```
Rationale: size 64 gives a 4x smaller raster than default (and matches the old mod's size=64). Rotation off avoids the rotated lookup. Coordinates off avoid per-frame string allocations. Preset the file only while the game is closed; the worker rewrites it on exit. The old mod's data dir `horizon-mods/.horizon-mod-data/minimap/` is separate and is not migrated.

## 3. File I/O, network, process, unsafe

- Writes: only `settings.ini` and `.settings-<pid>-<rev>.tmp` in the mod data dir (runtime.rs:1876-1895). Reads: only `settings.ini`.
- `std::env::temp_dir` appears only in tests (runtime.rs:1918).
- grep for `unsafe`, `std::net`, `Command::new`, `extern "C"`, `env::var` outside tests: none. No network, no process spawning, no unsafe.
- Clipboard write only on user click ("copy coordinates", client.rs:1236, 1268, 2087).
- Errors go to `eprintln!` only.
- Toolchain: rust-toolchain.toml 1.95.0, edition 2024; the Horizon workspace is edition 2024, rust-version 1.95, so let-chains are fine.

## 4. Keybind conflicts

- Mod keys (list.rs; runtime.rs:19-22): `world_map` default M, `waypoints` default N. Stored via `native_mod_key` in `~/Library/Application Support/horizon/horizon-mods.txt` as `key.<modid>.<name>:key.keyboard.x`.
- Current file: fullbright toggle J, toggle_sprint toggle_sneak right shift, zoom C. Other mod defaults: fullbright G, zoom Z, toggle_sprint V/C, light_overlay F7, jade keypad 0-5 and left shift, jei R/U. Old minimap had no keys.
- Vanilla/Horizon `options.txt`: no M or N bindings. The only N is the debug chord `key.debug.spectate` (keybinds.rs:62), which is F3+N.
- Result: no conflict. Low risk: F3+N may also fire the N hook.
- Behavior (key.rs): M or N while the mod screen is open closes it (N does not switch map to waypoints). Opening is gated on `native_playing()` and `text_input_active()`, so chat typing is safe.
- `binding_ui.rs` cancels and replaces `OptionsUi::native_rows` for ALL native mods (a copy from 2ebf00a) and overrides `tooltip_text` (options_ui.rs:1856). Reference `native_rows` (options_ui.rs:2598-2630) is identical apart from conflict highlighting, which this copy loses. Low risk, affects every mod's key page.

## 5. Hook and API compat, 2ebf00a to fdc87ae

No 2ebf00a source exists on disk (only fdc87ae in `outputs/horizon-src-nightly/nightly-2026-11-08-fdc87ae` and older 66f3981), so I checked the mod against the reference tree only.

All injection targets exist with matching parameter names and types:
- native_hooks.rs: native_mods (:3759), native_settings (:3896), native_settings_click (:4067), native_key (:3114), native_frame (:2314), native_hud (:2716), native_screen_render_post (:4754), screen mouse_button_pressed_pre (:4802), mouse_dragged_pre (:4899), mouse_scrolled_pre (:4954), key_pressed_pre (:5025), char_typed_pre (:5135), client_disconnecting (:2259), client_player_network_logging_in (:2273), client_resources_reloaded (:2390), menu_background (:2281).
- game.rs: forget_atlas_slots (:14277), render_frame (:15132), `exiting` in `impl ApplicationHandler for Game<'_>` (:16740; the other `exiting` at :20523 belongs to `App`).
- options_ui.rs: `native_rows` (:2598), `tooltip_text` (:1856). Private field `selected_native_key` (:1590) and `Lod.ready` (lod.rs:1258) are reachable from the injected child modules.
- Game APIs used all exist with matching signatures: native_fill, native_text, native_data_dir, native_mod_key, native_mod_image(&mut self, w, h, &[u8]) -> bool, native_sprite, native_client_chunks -> Result<NativeClientChunks, String>, native_client_state, native_player, native_camera, native_minimap_now, native_corner_shown, native_mod_screen_open/close, click_command, loading_frame.
- Game fields used all exist: focused, skin_frame, glint_frame, locator_camera, native_camera_frame, posed_rotation, map_patches, screen_blur_requested, frame_drawn, border (`bounds()` worldborder.rs:146), `world.air`, `ui.registries.permission: u8`, `lod: Option<Lod>` (game.rs:2648).

Block facts, resolved: the mod calls `game.res.facts()`, `book.is_air(id)` (horizon-client-render/src/world.rs:459), and reads `state.render_shape`, `state.classes`, `state.map_color as usize`, `state.fluid` against `horizon_client::blocks::{MAP_COLORS, RenderShape, Fluid}`. `horizon_client::blocks` is `pub use horizon_items::blocks` (horizon-client/src/client_lib.rs:179), and `horizon_items::blocks::StateFacts` has `render_shape: RenderShape`, `fluid: Fluid`, `classes: Arc<[Arc<str>]>`, `map_color: u8`; `MAP_COLORS: [u32; 62]` is at horizon-items/src/blocks.rs:77. The earlier worry came from a different struct (`BlockStateFacts`). These match, so compile risk here is low.

Behavior drift (compiles, differs):
- `render_map_only` skips PBR pack calls (see section 2).
- Screen mouse hooks gained a `modifiers` param the mod ignores.
- `binding_ui` replaces native_rows (loses conflict highlighting).

Remaining risk: unverified without a build. A single `cargo check` through the mixins tool on fdc87ae is the only real confirmation.

## 6. Multiplayer (mc.leftseat.ca)

- Sampling reads only client-loaded chunks. The mod sends no packets of its own.
- Teleport is user-click only. It runs `tp x y z` or `execute in <dim> run tp ...` via `game.click_command` (client.rs:1196-1210, 1283-1300), which uses `send_unattended_command` on a server (chat.rs:1448; remote_chat.rs:302). Gated by `teleport_allowed = game.ui.registries.permission >= 2` (client.rs:903), so it is hidden for non-ops.
- Waypoints are keyed by `NativeWorldId::Server(address)` as typed at join (native_client_services.rs:90-99). A different address alias gives a separate waypoint set.
- The below-surface "cave map" layer shows underground layout from client-loaded chunks. Check the server rules on cave mapping before using it.
- The map screen does not pause the game. The player stays vulnerable while it is open. Opening clears held keys.
- Session reset on disconnect and login hooks (disconnect.rs). Resample bursts on busy servers are bounded at 80/s.

## Caveats and follow-ups

1. Terrain RAM is uncapped. Cave and Nether Y-layer keying is the worst case. Consider a patch that caps tiles or drops old `Below(Y)` layers.
2. Minimap re-rasters every frame while moving. Keep size at 64.
3. Compile check on fdc87ae not done.
4. 2ebf00a source was unavailable, so compat is judged against fdc87ae only.
5. CPU numbers are estimates, not benchmarks.
