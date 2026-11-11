# Shadow visibility scratch reuse for f42

This original Rust transform replaces the fresh per-shadow-frame boxed-section vector and standard-library key set with renderer-owned scratch storage. It keeps the standard `HashSet` hasher and the existing culling, duplicate semantics and light-depth sort. Draining the boxed vector preserves capacity. Both containers clear before use. The stored keys are plain copied section coordinates and never refer to scene-owned allocations.

The scratch containers stay on `Renderer` throughout the render call. This adds no taken-out state to restore on the deferred-submit early return or final return. A world/camera change replaces their logical contents on the next shadow pass. Capacity remains bounded by the largest previously observed shadow visibility list, following the existing `shadow_visible` scratch policy.

Apply only to a separate caller-owned workspace with one of the two reviewed file hashes. The second accepted input is the exact cloud-preparation intermediate recorded by `../cloud-prep-f42/patch-spec.json`.

```sh
python3 outputs/horizon-native/shadow-scratch-f42/prepare.py \
  --workspace /absolute/path/to/isolated-f42-clone \
  --record /absolute/path/to/fresh-shadow-provenance.json
```

The script refuses launcher staging/source caches, unknown input bytes, repeated application and existing provenance output. It applies only three unique anchors in `crates/horizon-client-render/src/gfx.rs`. An output-record I/O failure after atomic source replacement leaves a modified disposable workspace requiring hash inspection before build. Installed version identity must include these transformed source hashes. The stock native-build cache identity does not incorporate arbitrary external patches.

The focused checker extracts the exact new merge body from the transformed real source and generates a standalone Rust test. Only the unchanged visibility collector is replaced by a fixture collector. The assertions compare ordered visible records with the previous algorithm across duplicate keys, changed camera/scene coordinates, empty scenes and repeated warm capacity reuse. It also verifies drift/repeat refusal and preservation of existing early-return restoration lines.

```sh
python3 outputs/horizon-native/shadow-scratch-f42/regression.py \
  --rust-output /private/tmp/shadow-scratch-check.rs
# Execute under the device queue using the isolated compiler.
outputs/horizon-runtime/launcher-data/rust/1.99.1-aarch64-apple-darwin/bin/rustc \
  --edition=2021 --test /private/tmp/shadow-scratch-check.rs \
  -o /private/tmp/shadow-scratch-check
/private/tmp/shadow-scratch-check
```

Source transform checks and Python compilation passed during authoring. The Rust test and real renderer compilation remain for the queued verifier. Runtime performance, visible shadow equivalence, and M1 benefit remain unmeasured. This is a source optimization candidate with an MIT license, authored without copying Java optimizer implementations.
