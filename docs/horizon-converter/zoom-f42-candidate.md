# f42 C-key Zoom source candidate

Status: **UNBUILT / UNTESTED**. Authoring prepared `outputs/horizon-native/zoom-f42-candidate/bundle/` as an unpacked `.hnmod` source candidate. No Cargo, rustup, mixin application, tests, build, install or game launch was run. The existing pilot remains unchanged. Parent owns the device/build queue and disk-capacity decision.

Fresh official [f42 native hooks](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/native_hooks.rs) has SHA256 `ebdacd725862572d04f595f0b8020f33f18f1d1785beaade306ca6c01d90b53b`, matching the earlier cached file. Its API359 and the following signatures were inspected directly. Exact declarations, source lines and source copies are retained in the candidate's `hook-contract.json` and `provenance/`.

| Hook | f42 line | Existing binding compatibility |
| --- | --- | --- |
| `native_key(&mut self, key: &str, pressed: bool)` |2367|Mutable game, key and pressed bindings retained|
| `native_wheel(&mut self, steps: f32, claimed: &mut bool)` |2399|Shared helper borrow plus mutable claimed retained|
| `native_zoom(&self, zoom: &mut Option<NativeZoom>)` |2495|Shared game and mutable optional zoom retained|
| `native_mods(&mut self, mods: &mut Vec<NativeMod>)` |2742|Mutable list binding retained|
| `native_settings(&mut self, mod_id: &str, buttons: &mut Vec<String>)` |2748|Mutable game/id/buttons retained|
| `native_settings_click(&mut self, mod_id: &str, button: usize)` |2752|Mutable game/id/index retained|

Helpers `native_on`, `native_playing`, `native_mod_key`, `native_setting` and `native_set_setting` retain their used signatures (8124,8437,8820,8861,8866). NativeMod/NativeZoom are re-exported by native_hooks at890–891. Key dispatch omits repeats; claimed wheel steps bypass the hotbar. `native_zoom_now` at9799 applies zoom only during gameplay, gives spyglass precedence, clamps factor1–10 and turn0.05–1, and emits no active zoom at1. These observations establish a source candidate; mixin application, type construction and runtime behavior remain unverified.

The source retains C, initial4x, scroll1.5x, min1/max10, hold/release reset, settings persistence and upstream smooth/turn controls. A preexisting Horizon key override still takes precedence. Runtime code and helpers were copied byte for byte from the local pilot; its preserved prior provenance identifies [upstream245ab9…](https://github.com/horizon-rust/horizon-mods/tree/245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d/native/zoom) and the local default changes. License is under `bundle/mixins/zoom/LICENSE`.

The [f42 hook-only contract](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/docs/native-mods.md#mods-on-the-hook-points) and upstream Zoom compatibility justify minimum `hooks:1`; host359 is not the minimum. The [official packager](https://github.com/horizon-rust/horizon-mods/blob/bc40e7bafeee66c57a2013617bf893ca8e4b2154/native/tools/native.py#L173) supplies the schema used in `horizon-native.json`. Both JSON and TOML preserve historical tested6f8c7a… consistently; desiredf42 lives explicitly in build-plan/provenance. The [installed-launcher reader](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/native_mods.rs#L481) reads hooks from the unpacked JSON, selects the requested compatible base, then repins only its own staging copy. `compatibility.json` alone is ignored. No `--allow-version-mismatch` is required by this plan.

After queued capacity/resource checks, create the disposable instance **only if absent**, using the isolated launcher `instance create Horizon-Zoom-Pilot`. The exact planned build is:

```sh
TASK_ROOT='/Users/tanushmalhotra/Library/Application Support/ElyPrismLauncher'
env CARGO_BUILD_JOBS=1 \
  "$TASK_ROOT/outputs/horizon-runtime/launch-isolated.command" native-build \
  "$TASK_ROOT/outputs/horizon-native/zoom-f42-candidate/bundle" \
  --instance Horizon-Zoom-Pilot \
  --version nightly-2026-11-03-f42ef42 \
  --profile performance --trust-native-code
```

This command has **not run**. It can require a cold engine build. The machine-readable argv is `outputs/horizon-native/zoom-f42-candidate/build-plan.json`; see [capacity/toolchain plan](native-port-build-plan-2026-11-03.md). Performance selects Cargo fast and must not be compared as if it were the official release profile.

Before gameplay acceptance, `native-mods.json` must name base `nightly-2026-11-03-f42ef42` and full horizon revision `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`. Record exact native version/executable SHA256, compiler, mixins/profile and copied source digests. Any fallback to an older engine fails this target, even if it builds.

Later acceptance must verify mod listing/enabling, C hold4x, wheel1.5x and1–10 limits, hotbar suppression only while held, release reset and re-press4x, persisted key/settings, smooth/turn behavior and no sticky state across menus/focus/disable. Retain visual and hand/HUD comparison evidence. Zoomify's high range (~230.66x after ten upward steps), exact step count, easing durations/scroll smoothness/sensitivity, hand FOV/view bobbing, F6 secondary/HUD and spyglass combination remain explicit gaps. The existing standalone pilot tests do not prove f42 integration.
