# Partial f42 CEM aliases as a native bundle

This is a separate **source-only candidate**, not a planned, compiled, installed or tested mod. The existing two-function source patch in `outputs/horizon-native/cem-binding-f42/` remains unchanged. This candidate implements only the [verified partial native route](native-build-patch-route.md).

`outputs/horizon-native/cem-alias-f42-bundle/bundle/` is a raw mixin bundle with unique ID `cem_alias_f42`. Its TOML explicitly pins engine `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`; there is deliberately no hooks-only `horizon-native.json`. A cancellable `HEAD` injection targets `horizon_client_lib::mobs::cem::vanilla_part`, binding the original `model: &str` and `part: &str`. The single private, safe, synchronous helper returns `core::ops::ControlFlow<String>`: `Break` only for the audited alias pairs and `Continue(())` otherwise. It contains no copied original resolver or modification of pack data.

The [pinned horizon-mixins contract](https://github.com/horizon-rust/horizon-mixins/blob/ddd9700b21997c95d95ac6ee5ecafe3830cf622a/docs/advanced-injections.md#cancellable-head) explicitly specifies `cancellable = true`, `ControlFlow<R>`, `Continue(())` continuing the original function, and `Break(result)` returning through any RETURN modifiers. A byte-for-byte downloaded copy of that document and its license are retained under `provenance/`; `provenance.json` records all hashes. This verifies the source schema, not that the launcher has successfully planned or compiled this candidate. The launcher's selected mixins revision must be recorded during the later real build.

The earlier target `horizon_client::mobs::cem::vanilla_part` was unverified and **failed actual e8 APPLY with `TARGET_NOT_FOUND` after the macro guard passed**, as reported by the root. This candidate now targets the defining crate `horizon_client_lib::mobs::cem::vanilla_part`; that correction has not yet been planned or applied. The old `combined-e8-r1` failure artifact is unchanged. The existing helper bytes, aliases and exact engine pin are unchanged.

Cargo topology explains the correction: [horizon-client-lib/Cargo.toml](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-lib/Cargo.toml) names package `horizon-client-lib` and sets `[lib] path = "../horizon-client/src/client_lib.rs"`. That entry declares `pub mod mobs;`, whose `mobs.rs` declares `pub mod cem;`. The physical `horizon-client/src/` directory therefore does not identify the defining crate. `horizon-client/src/lib.rs` only re-exports `horizon_client_lib::*`; its re-export and the internal `extern crate self as horizon_client` alias are not the defining Cargo crate target. Five exact-commit Cargo/lib/module fixtures were freshly fetched, compared byte-for-byte with the root's actual pinned source cache, and retained under `provenance/topology/`; their source URLs and SHA256 hashes are recorded in `provenance.json`. The regression derives the crate name and module path from these fixtures, separately checks the re-export, and rejects the failed target.

Included aliases cover guardian/elder body, wolf/armor mane, happy-ghast harness body, small-puffer tail/eyes, tropical-pattern top fin, salmon fins/tail (main/small/large named skeletons), and horse/skeleton-horse armor neck/mouth. Each alias's installed EMF bytecode and exported node/pivot evidence is in the [binding audit](cem-binding-gaps-2026-11-03.md). Other inputs fall through to the untouched original resolver, preserving existing canonical lookup and raw-name behavior. The exact f42 caller already strips `_baby`; aliases therefore inherit that existing adult-family treatment rather than recovering baby identity.

**The baby-villager clothing fix is omitted.** Its exact identity has already been erased before this hook runs; do not infer it from `villager`. Both `villager/bodywear` and a hypothetical direct `villager_baby/bodywear` helper call return `Continue`, so the existing engine behavior remains visible as a separate gap. Piglin-baby `jacket` also remains a review task with the original unknown-name zero fallback. Wolf collar and zombie-horse armor aliases are outside this bounded candidate. No warning-count reduction or visual parity is claimed.

## Prepare a later combined input

The preparation utility only reads the exact target source and copies bundle inputs. It requires the original f42 `cem.rs` SHA256 `4c7f8650070be17789d500aa86dd013fed9ddbcd0dc754d953f0208acb442cd8`, verifies this candidate's recorded bundle hashes, rejects bundle symlinks, and requires the existing Zoom package's ID and hook version. The engine pin comes from the alias TOML; the source-file hash guard does not independently authenticate every other source file in the supplied workspace. It refuses existing destinations, overlapping inputs and outputs outside this candidate directory or `/private/tmp`. It does not modify source, Zoom, packs, staging, caches or installed runtimes.

Later, with an explicitly verified f42 source root:

```sh
python3 outputs/horizon-native/cem-alias-f42-bundle/prepare.py \
  --source-root /private/tmp/horizon-f42-clean \
  --zoom-bundle outputs/horizon-native/zoom-f42-candidate/bundle \
  --output-dir outputs/horizon-native/cem-alias-f42-bundle/combined-input
```

This produces sibling `combined-input/cem_alias_f42/` (raw alias bundle) and `combined-input/zoom/` (unchanged unpacked Zoom bundle), plus `combined-input-provenance.json` containing every input-file hash. The launcher's `bundles()` recognizes both formats independently; the root collection has no bundle manifest. Existing Zoom's hook-only compatibility follows the explicitly pinned f42 engine without changing Zoom's original manifests, ID or license. The retained candidate license is the upstream Horizon MIT license; pinned mixin documentation has its own retained license.

The root must acquire the device queue, request a fresh review, run exact-revision mixin plan/apply and inspect the transformation before any combined build. Use the supported launcher `native-build` route described in the [integration investigation](native-build-patch-route.md), passing this new combined-input directory. Do not edit `stage`, snapshots, `native/source`, or installed artifacts, and do not use a version-mismatch override. Record both bundle hashes/IDs, actual engine/tool/compiler/profile, transformation plan, transformed `cem.rs` SHA and executable SHA in build provenance. This document does not authorize this worker to launch those operations.

Actual queue52 evidence supplied by the root: Zoom alone selected its older `0d6b103c70633d8fd9443d8d0acd3aadaacedb06` tool and failed APPLY with `E_UNSUPPORTED_MACRO` before the full engine build. Therefore the documented `ddd9700b...` contract is **not proof that this launcher invocation will select that tool**. The raw alias bundle does not add a mixins-tool override. Resolve the tool/attribute compatibility and verify the exact selected tool before planning this combined input; this worker has neither changed Zoom's metadata nor attempted that fix.

## Pending checks

Authored but **not run** in this task:

```sh
python3 -m unittest discover -s tests -p 'test_horizon_cem_alias_bundle.py' -v
```

The tests check schema pins, evidence hashes, source-drift/fresh-destination guards, unchanged inputs and combined layout. A focused case compiles the actual helper with `rustc` and executes positive/neighboring-negative `ControlFlow` assertions; it skips when `rustc` is absent. It does not use Cargo or launch game code. No tests, planning, application, compilation or runtime commands were executed by this worker.

After review, planning and compilation, grouped shader-independent visual checks must establish correct canonical nodes, descendant reachability, replacement visibility, pivots and parent composition, including guardian/elder, harness, wolf, puffer, salmon sizes, tropical patterns and horse armor. Preserve original pack hashes and record baby-villager/piglin gaps explicitly. A successful helper assertion or fewer warnings does not establish animation parity or resolve every current warning.
