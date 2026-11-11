# Native CEM patch route on the installed launcher

Read-only source investigation, 2026-11-04. No build, test, installation, cache mutation or game launch was performed. Target engine is f42ef42ef6ceccb3c6a20bea2481d87949a51c81; installed launcher source is c1f308fe62beec70cee597b0483f1e0ee172844c.

The reproducible supported integration point is a second native **mixin bundle**, supplied alongside the existing Zoom bundle. An arbitrary external `.patch` file is not consumed by this launcher pipeline. Do not edit `native/stage`, `stage.new`, injection snapshots or `native/source/<revision>` as an integration shortcut: the pipeline reconstructs/synchronizes staging, and its installed-version identity hashes the revision, tool/compiler/profile and bundle bytes, not arbitrary cache edits. A matching cached installed version can skip compilation altogether. Such changes could be overwritten or reused under misleading provenance. See the locally retained `outputs/horizon-native/zoom-f42-candidate/provenance/launcher-native_mods.rs`, lines1509–1774, and [pinned upstream pipeline](https://github.com/horizon-rust/horizon/blob/c1f308fe62beec70cee597b0483f1e0ee172844c/launcher/src/native_mods.rs#L1509).

## Verified supported partial route

Create a separately named, raw native bundle whose TOML explicitly pins f42, then supply a **new collection directory** containing that bundle and the existing unpacked Zoom bundle. The launcher's `bundles()` recognizes each child independently; distinct IDs avoid duplicate-ID rejection. Zoom's existing hook-only packaging can follow the explicit f42 pin of the new bundle. The later command shape is:

```sh
env CARGO_BUILD_JOBS=1 \
  "$TASK_ROOT/outputs/horizon-runtime/launch-isolated.command" native-build \
  "$TASK_ROOT/outputs/horizon-native/NEW-COMBINED-INPUT" \
  --instance Horizon-Zoom-Pilot --version nightly-2026-11-03-f42ef42 \
  --profile performance --trust-native-code
```

`NEW-COMBINED-INPUT` is a placeholder, not a prepared directory or executed command. Preserve bundle IDs/licenses and hash every input. No `--allow-version-mismatch` is needed when pins agree. Actual output `native-mods.json` must record f42, both mod IDs/digests, actual mixins/compiler/profile and executable SHA256; retain the transformation plan and patched source digest as additional evidence.

For `horizon_client_lib::mobs::cem::vanilla_part`, a **cancellable HEAD** helper returning `core::ops::ControlFlow<String>` can supply an exact replacement result using `Break(result)`. Bind `model: &str` to `model` and `part: &str` to `part`; the helper has one private safe synchronous function with no explicit generics. HEAD boundary validation permits the original function's closures/nested constants. The alias helper can preserve the old normalized-model behavior and add the evidence-backed adult/layer aliases. This is a source-supported candidate, **not yet a successfully planned or compiled bundle**. An earlier version of this document guessed `horizon_client::mobs`; that crate identity was wrong and is corrected below.

The relevant versioned schema/implementation is horizon-mixins `ddd9700b21997c95d95ac6ee5ecafe3830cf622a`, the installed launcher's minimum tool pin. [HEAD cancellation contract](https://github.com/horizon-rust/horizon-mixins/blob/ddd9700b21997c95d95ac6ee5ecafe3830cf622a/docs/advanced-injections.md#cancellable-head), [boundary validation](https://github.com/horizon-rust/horizon-mixins/blob/ddd9700b21997c95d95ac6ee5ecafe3830cf622a/crates/horizon-mixins-core/src/plan.rs#L929), [helper contracts](https://github.com/horizon-rust/horizon-mixins/blob/ddd9700b21997c95d95ac6ee5ecafe3830cf622a/crates/horizon-mixins-core/src/helpers.rs#L330).

## Material gap for the complete two-function patch

Do **not** package the current two-function source patch as two OVERWRITEs. The pinned planner validates original bodies and rejects closures/nested items for OVERWRITE; both `vanilla_part` and `CemLayer::build` contain such constructs. Cancellable HEAD avoids that body restriction for the resolver, but it does **not** currently replace `CemLayer::build`: its return type is spelled `Self`, and `helpers::unsupported_type` rejects `Self` for cancellation contracts, even if a helper uses concrete `CemLayer`. See [original-body safety rules](https://github.com/horizon-rust/horizon-mixins/blob/ddd9700b21997c95d95ac6ee5ecafe3830cf622a/crates/horizon-mixins-core/src/plan.rs#L1099) and [concrete-result guard](https://github.com/horizon-rust/horizon-mixins/blob/ddd9700b21997c95d95ac6ee5ecafe3830cf622a/crates/horizon-mixins-core/src/helpers.rs#L96).

Therefore preserving exact `villager_baby` identity before the existing `_baby` stripping remains an **unresolved integration gap** for the complete patch. A resolver-only bundle must explicitly omit that fix and retain its warning/review task. Do not infer child identity from the normalized adult name, silently route child clothing to adult jacket, or introduce guessed pack rewrites. A controlled manual build could apply the full guarded source patch after official mixin staging, but installation/provenance/cache-key handling for that separate path has not been implemented or verified here.

The first validation should be mixin `plan`/`apply` against an exact fresh f42 workspace with the chosen tool revision, then compilation of the real combined client. Planning success alone does not establish type or runtime correctness. The CEM target file SHA256 guard remains necessary before generating helper bodies; preserve authored pack bytes and keep pivot/geometry acceptance checks.

## Capacity limits

Known paths are isolated launcher `rust/`, `cargo/`, `native/source/`, `native/tools/`, `native/stage/`, transient `stage.new`, injection snapshots, `native/target/fast/` and installed `versions/native-*`. The pipeline can retain source, multiple transformed copies, downloaded crates, compiler components and incremental objects concurrently. `CARGO_BUILD_JOBS=1` limits concurrent Cargo units, not all compiler/linker memory. APFS clone savings are not guaranteed for every artifact.

This investigation did not measure current free space or run a build. The prior ~12GiB free reading does **not** establish sufficient working space or swap reserve. Before any unattended cold build, the root must acquire the shared queue, inspect current disk/memory and these cache paths, use one profile, preserve a chosen free-space reserve and monitor actual growth. Stop the owned build cleanly if reserve is crossed; never delete unrelated files or original saves. No reliable M1 peak disk/RAM requirement or completion estimate has been established.

## Erratum: defining crate and a plan-only preflight

The downloaded exact f42 workspace proves the CEM implementation belongs to **`horizon_client_lib`**, despite its physical files remaining under `crates/horizon-client/src/`. `crates/horizon-client-lib/Cargo.toml:2,12–13` declares package `horizon-client-lib` and `[lib] path = "../horizon-client/src/client_lib.rs"`; client_lib.rs:90 declares `pub mod mobs`, and mobs.rs:24 declares `pub mod cem`. The `horizon_client` crate reexports `horizon_client_lib::*`; reexports do not create a second defining AST function. The earlier guessed target `horizon_client::mobs::cem::vanilla_part` was therefore incorrect. Use **`horizon_client_lib::mobs::cem::vanilla_part`**. [Defining manifest](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-lib/Cargo.toml#L12).

The installed e8cd0aa tool has only `plan`, `apply` and `check` subcommands; it has no CLI `index` or `query`. `Index::load(root)` / `Index::resolve(target)` exist as Rust APIs but do not justify inventing CLI flags or compiling another helper. A **queued `plan`** is the direct available preflight. It validates manifests, indexes source, resolves the target and writes a schema6 plan; it does not stage or compile the game. It does invoke `cargo metadata --no-deps --offline --locked` and `rustc --version`, so provide the same isolated compiler environment as the launcher.

After the worker's target correction and source guard checks, the root may run this command shape under its shared queue (not executed by this research unit):

```sh
TASK_ROOT='/Users/tanushmalhotra/Library/Application Support/ElyPrismLauncher'
NATIVE_HOME="$TASK_ROOT/outputs/horizon-runtime/launcher-data"
env \
  PATH="$NATIVE_HOME/rust/1.99.1-aarch64-apple-darwin/bin:$PATH" \
  CARGO_HOME="$NATIVE_HOME/cargo" \
  RUSTC="$NATIVE_HOME/rust/1.99.1-aarch64-apple-darwin/bin/rustc" \
  "$NATIVE_HOME/native/tools/e8cd0aa38cff/bin/horizon-mixins" plan \
  --workspace "$NATIVE_HOME/native/source/f42ef42ef6ceccb3c6a20bea2481d87949a51c81" \
  --mods "$TASK_ROOT/outputs/horizon-native/cem-alias-f42-bundle" \
  --out "$TASK_ROOT/outputs/horizon-native/cem-target-plan-e8-r1.json"
```

Use a new output filename if that artifact already exists. The tool's `--mods` loader reads direct TOML files and immediate children named `horizon-mixin.toml`; the parent above discovers `bundle/horizon-mixin.toml`. Passing `bundle/` itself would treat the TOML as a direct mod rather than a bundle and can alter relative-helper ownership semantics. The nested unpacked Zoom `.hnmod` layout is not directly the mixin CLI's loader format; for a later combined plan use an owned flat staging collection with one raw manifest bundle per immediate child and the same effective repinned metadata as the launcher.

Success is exit0 plus stdout JSON containing `status:"ok"`, `plan:<output path>`, injection/module counts and elapsed seconds. The plan file must contain `schema:6`, the actual `rustc`, source `inputs` SHA256s and an `injections` entry with the exact target above, `file:"crates/horizon-client/src/mobs/cem.rs"`, `function_fingerprint`, bindings and helper source. Failure emits structured diagnostic JSON on stderr and exits nonzero. Require that exact entry before another full build; a successful plan still does not prove Rust types, runtime warning reduction or visual parity.

Verified against locally cached exact e8cd0aa sources: `crates/horizon-mixins-cli/src/main.rs:23–48,65–79`, `core/src/manifest.rs:240–265`, `core/src/index.rs:150–167,524–582` and `core/src/plan.rs:20–90`. The actual launcher chose old0d6b103 when Zoom alone pinned it; e8cd0aa was then selected explicitly to fix the demonstrated recursion_limit classification bug. The original default-tool discussion above is source context, not a claim that the default was used in either attempt.
