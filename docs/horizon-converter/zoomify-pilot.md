# Zoomify native pilot preparation

Research date: 2026-11-02. **Preparation only: no runtime downloaded, installed, built or launched by this research unit. The native pilot is not complete.** Target source: Horizon `e6e12d40c522b8f5ee8740dd861c96689023737a` (hooks API 153). See [existing API findings](../horizon-converter-api.md) and [isolated install plan](install-plan.json).

## Actual source settings

Read-only evidence: `instances/Tanush-26.3/minecraft/config/zoomify.json`, installed `zoomify-2.17.0+mc26.3-universal.jar`, and `options.txt` lines 293–294. Primary key is **C**, secondary key **F6**. Settings observed:

| Behavior | Actual value | Official Horizon Zoom 2.0.0 equivalent/gap |
|---|---|---|
| Key/activation | C; hold | Hold supported; native default Z is rebindable |
| Starting zoom | 4x | 4x default, configurable |
| In/out | 1.0 / 0.5, both `ease_out_exp` | Only Boolean smooth; exact timing/curve absent |
| Wheel | enabled, 10 steps, 150% per step | Native wheel consumes hotbar scroll; 1.25x steps, range 1.25–10x |
| Wheel smoothing | 70 | No separate setting |
| Retain steps | false | Native resets on each press |
| Affect hand FOV | true | NativeZoom does not expose hand FOV |
| Relative sensitivity | 100 | Native Boolean slower turning uses 1/factor; precise Java parity unverified |
| Relative view bobbing | true | No corresponding Zoom setting |
| Cinematic camera | 0 | No corresponding Zoom setting; disabled source behavior needs no camera smoothing |
| Spyglass | combine; overlay holding; sound with overlay | Engine explicitly suppresses NativeZoom while scoping; composition gap |
| Secondary | F6, 4x, in 10.0/out 1.0; hide HUD true | Absent from official native Zoom |
| Internal markers | `_keybindScrolling=false`, `_firstLaunch=false` | Preserve as provenance, not native user options |

Zoomify's tagged [2.17.0 source](https://github.com/isXander/Zoomify/tree/4abaf61b97e9615b98de57c5171393b8f8ef5bb0) verifies 150 means **1.5x per step**, with raw divisor clamped 1–500. At steady initial 4x, ten positive steps mathematically give `4 * 1.5^10 = 230.66015625x`; Horizon's 10x limit therefore loses meaningful range. Timing numbers above are stored values; do not label them seconds without inspecting the interpolator's time unit. [Step math](https://github.com/isXander/Zoomify/blob/4abaf61b97e9615b98de57c5171393b8f8ef5bb0/src/main/kotlin/dev/isxander/zoomify/zoom/ZoomHelper.kt), [interpolator selection](https://github.com/isXander/Zoomify/blob/4abaf61b97e9615b98de57c5171393b8f8ef5bb0/src/main/kotlin/dev/isxander/zoomify/zoom/DefaultZoomHelpers.kt).

## Verified existing native implementation

Official source is [horizon-mods/native/zoom](https://github.com/horizon-rust/horizon-mods/tree/245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d/native/zoom), pinned repository revision `245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d`, MIT. This was formerly built in, then a WebAssembly mod, now a **native source bundle requiring compilation into the client**. Installing a jar/resource pack cannot provide it. Official registry [zoom.toml](https://github.com/horizon-rust/horizon-mods/blob/245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d/mods/zoom.toml) advertises `zoom-2.0.0.hnmod`, SHA-256 `49fa2d7d635225c53304fbf1477606c0677eb23d94dac75b730f6c3ba065f127`; that hash applies to the published upstream artifact, **not** a changed local bundle.

Its [runtime](https://github.com/horizon-rust/horizon-mods/blob/245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d/native/zoom/mixins/zoom/runtime.rs) maintains thread-local state and has independent Rust unit tests. Its real config uses `horizon-mods/.horizon-mod-data/zoom/{level,smooth,sensitivity}`, one text file per value, plus `horizon-mods.txt`:

```text
mod.zoom:true
key.zoom.zoom:key.keyboard.c
```

The [actual codec](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client-render/src/mod_list.rs#L64-L102) uses `:` separators. Proposed isolated values are `level` → `4`, `smooth` → `true`, `sensitivity` → `true`. These settings make the core C-hold workflow available when the bundle is compiled; they are not a complete Zoomify config conversion.

## Bounded source pilot for a worker

Vendor the entire official `native/zoom/` subtree into a new workspace pilot directory, retaining `LICENSE`, all helper files, `Cargo.toml`, `Cargo.lock`, `compatibility.json`, README and provenance. Use its existing bundle rather than generating a new API. The inspected generic template is [revision cc8ce2d896782099abfa9f0abf26fa80c9e4bddb](https://github.com/horizon-rust/horizon-native-mod-template/tree/cc8ce2d896782099abfa9f0abf26fa80c9e4bddb); prefer the smaller working Zoom bundle as the implementation baseline.

The following actual Rust changes adapt the native subset to this user's key and scroll factor:

```diff
--- a/mixins/zoom/runtime.rs
+++ b/mixins/zoom/runtime.rs
@@
-pub const DEFAULT_KEY: &str = "key.keyboard.z";
+pub const DEFAULT_KEY: &str = "key.keyboard.c";
@@
-const MIN: f32 = 1.25;
+const MIN: f32 = 1.0;
@@
-const STEP: f32 = 1.25;
+const STEP: f32 = 1.5;
@@
-        assert_eq!(view().map(|v| v.0), Some(5.0));
+        assert_eq!(view().map(|v| v.0), Some(6.0));
```

Keep `MAX=10` because the game clamps it anyway. Update upstream descriptive comments/range docs and add a real behavior check for wheel down reaching 1x, release clearing state, and re-press starting at 4x. Do not claim these three constants implement ten-step range or Java transition parity. The existing key binding can be changed without Rust; changing DEFAULT_KEY makes a fresh pilot choose C consistently.

The [upstream manifest](https://github.com/horizon-rust/horizon-mods/blob/245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d/native/zoom/mixins/zoom/horizon-mixin.toml) is real `horizon-mixin.toml` schema: `[mod]`, `[compatibility] horizon_revision`, `[[module]]` (`file`, `name`, `source`), and `[[injection]]` (`id`, `kind="HEAD"`, `target`, `helper`, `bindings`). Preserve its proven bindings. It currently pins Horizon `6f8c7a0e5d531d3834c4d0be4659a1db8e7e5c2a` and mixins `0d6b103c70633d8fd9443d8d0acd3aadaacedb06`; repinning the local target to `e6e12d4…` is **an uncompiled compatibility assertion**, not an upstream test result. Distinguish local target metadata from original provenance. Do not mislabel a native source folder as a ready binary.

Verified source hooks at the pinned game revision ([native_hooks.rs](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/native_hooks.rs)):

```rust
pub(super) fn native_key(&mut self, key: &str, pressed: bool)
pub(super) fn native_wheel(&mut self, steps: f32, claimed: &mut bool)
pub(super) fn native_zoom(&self, zoom: &mut Option<NativeZoom>)
pub(super) fn native_frame(&mut self, elapsed: Duration)
```

The official Zoom injects key/wheel/zoom/list/settings/click hooks and adds `official_zoom` to `crates/horizon-client/src/game.rs`. `NativeZoom` has `factor`, `smooth`, `turn`; its type is imported through native hooks. This is in-tree source access, not a public dynamic plugin library. [Game adapter](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/extras.rs#L258-L286) applies smooth FOV, instant FOV and turning; [native_zoom_now](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/crates/horizon-client/src/game/native_hooks.rs#L8257-L8277) clamps factor to 1–10 and turn to .05–1 and returns none while scoping. API109 `native_compute_fov` affects world FOV only, explicitly excluding hand/HUD. Exact high-range, hand-FOV and spyglass composition require further engine source changes and acceptance evidence; do not promise them through unsupported fields.

Acceptance before calling this a source pilot: preserved provenance and license; manifest TOML parses; exact helper target signatures checked; standalone runtime tests pass with command recorded. Acceptance before calling it a functioning replacement: successful bundle application/game compilation against target plus C press/release, menu/focus transitions, scroll consumption, reset and visual checks. **No game launch or benchmark is authorized in this pass.** The core source pilot may be delivered explicitly uncompiled against the game; full behavior parity stays partial.

## Isolated runtime staging

Official launcher ZIP is `launcher@0.2.37`, commit `c1f308fe62beec70cee597b0483f1e0ee172844c`, 14,547,266 bytes, SHA-256 `e3e8a21f229d8b64602a6ce64c21e2d2fddffa4129cb10168aa0d5d51985b227`. [Release](https://github.com/horizon-rust/horizon/releases/tag/launcher%400.2.37), [asset API](https://api.github.com/repos/horizon-rust/horizon/releases/assets/701038214). A separately pinned stable game ZIP `v0.2.97`, commit `a3acb5f0d2f59d2d5ff21a5aa000809ba1e35e2f`, is 29,490,171 bytes, SHA-256 `587fb8a653324e6f1b3bf59f1f2227ad99201ccaaf3f31024db25ccd4f37c63e`. [Release](https://github.com/horizon-rust/horizon/releases/tag/v0.2.97), [asset API](https://api.github.com/repos/horizon-rust/horizon/releases/assets/686319521). GitHub asset digests are publisher metadata; verify downloaded bytes locally before extracting. Neither release is the research pin; do not call its binary `e6e12d4`.

Proposed root: workspace `outputs/horizon-runtime/`; extract launcher under `launcher-app/`, downloaded ZIPs under `downloads/`, separate `launcher-data/` and `game/`. Invoke the actual extracted executable with environment overrides, not Finder/open (which might attach to another launcher). `HORIZON_LAUNCHER_HOME` and `HORIZON_HOME` are verified [source environment variables](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/launcher/src/backend.rs#L535-L543), [game home](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/launcher/src/backend.rs#L2002-L2012), **not CLI flags**. `HOME` must remain untouched. Set `HORIZON_LAUNCHER_NO_SELF_UPDATE=1`; use optional XDG scratch directories as upstream's [native build scratch example](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/docs/native-mods.md#L1260-L1269) does.

Verified CLI subcommands are `install <tag>`, `prepare --version <tag> --minecraft <source-folder>`, and `native-build <folder> --version <tag> --trust-native-code`; `play` is separate. [CLI source](https://github.com/horizon-rust/horizon/blob/e6e12d40c522b8f5ee8740dd861c96689023737a/launcher/src/cli.rs#L699-L805). Staging may download/extract the approved launcher ZIP after converter improvements. Do not automatically run prepare/build/play, import saves, link original configs, or modify system/default Horizon storage. The real extracted ZIP layout and released binary help still require inspection before invoking any command. No binary digest was locally verified during this research-only unit.
