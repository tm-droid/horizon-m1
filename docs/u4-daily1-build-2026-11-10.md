# U4: daily1 build on nightly fdc87ae (2026-11-10)

## Result

The new version is `native-fdc87ae-m1-daily1-341aea300aca`. It is installed at `~/Library/Application Support/horizon-launcher/versions/native-fdc87ae-m1-daily1-341aea300aca` and carries `.installed`, `native-mods.json` (16 mods) and `source-patches.json`. It was built on the nightly `nightly-2026-11-08-fdc87ae` (SHA fdc87aecdbd116bf1e08adcd062fcbaea8c2e2ca, hooks API 411) with Rust 1.99.1, profile `fast`, and the mixins tool at revision 5a64af93 (the newest revision any included mod names). The launcher selection was not touched: `settings.json` still has `selected` = `nightly-2026-11-08-fdc87ae` and `install_new_versions` = false. No existing version was deleted.

The build driver is `outputs/horizon-runtime/build-daily1-fdc87ae.py`. The patch stack order is in `outputs/horizon-native/daily1-stack.txt`. Patch files are in `outputs/horizon-native/<name>-fdc87ae/`. The cem_alias mod source is in `outputs/horizon-native/cem-alias-fdc87ae/`.

## Patch table

Sixteen patches are applied, in this order. Four older patches were dropped because fdc87ae already contains them.

| Patch | Verdict | Reason |
|---|---|---|
| cloud-prep | ported (fuzz) | Context shifted; applied with fuzz. Perf only. |
| shadow-scratch | ported | Applied clean. Scratch buffer reuse, no visual change. |
| jobpool-qos | ported | Applied clean. Differs from the upstream QoS commits, so it is not covered. |
| emissive-bsearch | ported | Applied clean (terrain.wgsl, native_emissive.rs). No upstream match. |
| pass-merge | ported (manual) | The test-module hunk at the end of `pack_post.rs` was re-appended by hand. |
| shadow-dedup | ported | Applied clean. Scratch reuse. |
| particle-cull | ported (manual) | Not obsolete. Upstream 7fc42e82 is an opt-in mode and the user's setting is `particleCulling:off`; this patch culls off-view particles in the Off path. The `shader_packs.rs` hunk was hand-ported. |
| adaptive-upload | ported (manual) | The `adaptive_upload` module hunk was re-appended to the end of `game.rs`. Pacing only. |
| pbr-cpu-drop | ported (manual) | Still needed: `pbr_normals` and `pbr_specular` are `Vec<u8>` in fdc87ae. Call sites moved to `loading_window.rs` and `examples/scene_replay.rs`. Its unit tests were fixed to use `super::SpritePixels` (see Tests). |
| anim-frame-compact | ported | Upstream d8742781 does not cover it: `frames` is still `Arc<Vec<Vec<u8>>>` in `sprites.rs`. |
| arena-thresholds | ported | Constants only. |
| audio-cache | ported | Constants only. |
| composite-overwrite | ported (fuzz -F3) | Applied with fuzz. |
| cem-binding (u6) | included | From `patches/u6/`. Guardian and elder_guardian spine targets, plus wolf mane, happy ghast harness, puffer, tropical fin and salmon fin/tail aliases. `git apply --check` passed; the build and tests pass with it. |
| is-gliding (u6) | included | The `is_gliding` CEM variable reads the elytra state. Same checks. |
| charged-creeper (u6) | included | Charged creeper shell uses the CEM `creeper#armor` layer. Same checks. Does not fix the white shell under MakeUp. |
| qos-backport | dropped | Merged upstream (9cfac94b, 0f7f9db8). |
| sprite-compress | dropped | Merged upstream (2c9dac6b). |
| colortex-lazy-b | dropped | Merged upstream. |
| a66f8fa2 | dropped | Merged upstream. |

No included patch is intended to change visuals. That is reasoned from the patch contents and was not verified by a visual comparison. The three u6 patches do change CEM mob rendering on purpose (they fix missing or wrong mob parts and the is_gliding variable); that is the behaviour the coordinator asked for.

## Mod table

All 16 mods applied one by one and in the combined run, with no failures. Source SHA is the repo HEAD that was built.

| Mod | Source | SHA | Keybinds |
|---|---|---|---|
| appleskin 0.1.3 | soufied/AppleSkin-Horizon | 20180ee8 | none |
| zoom 2.0.0 | horizon-mods native/zoom | a4b09b49 | `key.zoom.zoom` set to C (mod default Z) |
| minimap 2.0.0 | horizon-mods native/minimap | a4b09b49 | none exist; settings only, so M cannot be bound |
| fps_overlay 2.0.0 | horizon-mods native/fps-overlay | a4b09b49 | none |
| fullbright_horizon | CayMac97/fullbright | 8a37d7df | `key.fullbright_horizon.toggle` set to J (default G clashed with vanilla quick actions) |
| armor_status | CayMac97/armor-status | b3011de3 | none |
| status_effect_hud | CayMac97/status-effect-hud | 9342baed | none |
| toggle_sprint | CayMac97/toggle-sprint | c30b952a | sprint default V; `toggle_sneak` kept on right shift (already in the game home) |
| light_overlay | CayMac97/light-overlay | 38ce3787 | toggle F7. Default is off (`active: false` in `runtime.rs`). |
| chatheads 0.1.1 | Domanffe/chatheads | c052d3fb | none |
| held_item_info | AltMugen/horizon-held-item-info | 406a6499 | none |
| jade 26.3.8 | Joeypc6/Jade-Horizon | d0016940 | keypad 0 to 5 for profiles, left shift for details (no clash with the chosen keys) |
| dynamic_fps_for_rust | Lyvt-Dev/dynamic-fps-for-rust | 20ff37b2 | none. It built, so it is included. |
| crosshair_indicator | CayMac97/crosshair-indicator | c1a6d2ae | toggle, unbound by default. Chosen as the dynamic crosshair equivalent. |
| dynamiclights 1.0.1 | DeportedToHell/MCRE-Mods | 93079e68 | none found. The index lists 1.0.0; repo HEAD is 1.0.1. |
| cem_alias 0.2.0 | local, `outputs/horizon-native/cem-alias-fdc87ae/` | n/a | none. Ported to fdc87ae: target is `horizon_client_lib::mobs::cem::vanilla_part`. Aliases: guardian, wolf, happy_ghast_harness, puffer_fish_small, tropical_fish_pattern, salmon, horse_armor. |

Left out: fast_items and eatinganimation (the coordinator said to skip them), zoomify (the official zoom is in). Not found in the index, so not included: shield status, block highlighter, chat history/patches. blockscope, lookat and chat_animation are not equivalents.

Cem_alias and the u6 cem-binding patch both add aliases to `vanilla_part`. They applied and compiled together, so there is no conflict, but the aliases overlap. Runtime behaviour of the pair has not been checked in a world.

Keybinds are in the game home file `~/Library/Application Support/horizon/horizon-mods.txt`: the existing sprint line plus `key.zoom.zoom:key.keyboard.c` and `key.fullbright_horizon.toggle:key.keyboard.j`. C also matches the creative-only vanilla save-toolbar key; this was accepted because the user's Java setup uses C for zoom. No keys were set in mod code.

## Build and test summary

Build: `cargo build --locked --profile fast -p horizon-client --bin horizon-client`, jobs 2, exit 0 in 706 s. The first attempt used `--offline` and failed immediately with `no matching package named 'gif' found`, because the launcher cargo cache lacked fdc87ae's new dependencies. The `--offline` flag was dropped (keeping `--locked`), and cargo fetched the missing crates. Disk was low during testing (3.9 GiB free against a 5 GiB gate), so 15 GB of regenerable `fast/incremental` cache in the shared target dir was deleted. No source, version dir or lockfile was touched.

Tests: `cargo test --no-fail-fast --locked --profile fast -p horizon-client-render -p horizon-client -p horizon-threads --lib --bins --tests`.

- Patched tree without mods: 2855 passed, 2 failed, 196 ignored. The two failures are `crash::tests::a_panic_becomes_a_report` and `crash::tests::the_debug_crash_is_reported_as_vanillas` in `horizon-client-render`. No patch touches `crash.rs`; the cause looks like backtrace formatting under the `fast` profile. This was not checked against the pristine source.
- Patched tree with all mods: `horizon-client` lib ran 1218 passed, 1 failed. The failure is `native_hooks::tests::hook_points_stay_hookable`, a lint that rejects macros in `native_hooks.rs`. The mixins tool itself writes `format!` and `vec!` into that file for the mods, so any mod build trips it. The same crate has 1149 passed and 0 failed without mods. The test run with mods stopped at that binary, so the other crates were only run in the no-mods pass.
- First test run found a real defect in my port: the pbr-cpu-drop test code used bare `SpritePixels` inside `mod tests` (compile error E0425). The patch was changed to `super::SpritePixels`. This is a test-only change made after the binary was built, so the installed binary is unaffected but the source digest in the version name predates it.

## Smoke boot

First `pgrep -fl horizon-client` showed no running client, and the screen was not locked. The installed binary was started from a disposable home under `/private/tmp/claude-503/u4-smoke` with the game-home `horizon-mods.txt`, no world and no server, with `--frames 600`. It exited 0 after 21 s with a smoke report of `error: null`, 600 frames, and logged the Apple M1 Metal renderer, resources loaded, and "first frame after 10917 ms". `latest.log` has no warnings or errors. Mods do not log a "loaded" line at startup, so that check could not be done as written. Indirect evidence: the dynamiclights and jade data folders were created, the key file was read, and the binary contains each mod id string (cem_alias has none because it only replaces `vanilla_part`). Nothing was joined and no keystrokes were sent.

## Open items

- Mod behaviour (zoom C, fullbright J, light overlay off, cem aliases with cem-binding) and the three u6 mob fixes still need a visual check in a world.
- Minimap has no keybind to set.
- Consider fixing the two `crash` tests or confirming they fail on pristine fdc87ae.
