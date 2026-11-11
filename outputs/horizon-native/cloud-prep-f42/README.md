# f42 cloud preparation source candidate

The renderer prepares the vanilla cloud mesh and uploads its vertices/uniform before the Iris pack cloud-draw decision. A pack declaring `clouds=off` therefore retains this CPU/transfer work. This candidate checks that declaration before preparation. Shader settings, projection, cloud range, environment uniforms and post-processing stay on their existing paths.

The patch adds an explicit declaration field and query to `PackPost`. Existing `has_clouds()` returns true for both suppression and a real `gbuffers_clouds` program. Using that existing query to skip preparation would remove geometry that other Iris packs need. The candidate preserves clouds for such programs, native shader cloud eligibility, missing/unloaded Iris posts, and title rendering.

The exact f42 consumers were checked in `gfx.rs`. Cloud quads contribute to index capacity (7588), OIT needs (7870), OIT drawing (8713/8801), classic drawing/marking (8850/8952), and Iris cloud input (9102). Active Iris posts bypass the OIT path. A `clouds=off` post has no cloud pass because `horizon-shaders/src/post.rs:822–823` filters it out. Returning zero cloud quads in this case removes unused input and index demand. Existing native-post rendering keeps its own `vanilla_clouds` guard. The patch does not reinterpret ordinary game cloud options.

`patch-spec.json` records exact before/after hashes and replacement contexts for both target files. `prepare.render(relative_path, original_bytes)` provides the transformation API for root's separately guarded build orchestration. It rejects source drift and verifies the reviewed output hash. `cloud-prep.patch` is the corresponding human-readable diff. The upstream MIT license is retained in `LICENSE`.

The standalone CLI can prepare fresh source trees inside this candidate's directory. It excludes root `.git`, `.local`, and `target`, rejects remaining symlinks/special entries, verifies the revision marker, inventories copied files and rechecks the source. A partial output after an I/O failure must be discarded before retrying. Run source copying only under the shared device queue.

```sh
python3 outputs/horizon-native/cloud-prep-f42/prepare.py \
  --source outputs/horizon-runtime/launcher-data/native/stage \
  --output outputs/horizon-native/cloud-prep-f42/candidate-source \
  --mode patched
```

The normal launcher native-build pipeline cannot directly express this small two-file renderer edit through verified stable hooks. It regenerates its stage and derives its cache key from bundles. Apply this patch only to a fresh source copy, then build using the isolated Rust 1.99.1 toolchain and the same `fast` Cargo profile as the existing local control. Root owns its process/disk guard, clone, composed source provenance, build and installation metadata. Preserve separate binary hashes and source-patch manifests. A source change must never reuse a standard native build's identity or be described as a same-profile comparison with the publisher release.

```sh
# Command shape for root's queued guarded build, not executed by this unit.
cargo build --locked --profile fast --manifest-path <fresh-source>/Cargo.toml \
  -p horizon-client --bin horizon-client
```

Executed lightweight checks were Python compilation and `check.py --source <exact-f42-source>`. The checker renders both target files, rejects drift, and extracts the actual patched query/predicate. Its optional `--rustc <isolated-rustc>` compiles a GPU-free 36-case check for title, missing/unloaded/ordinary Iris posts, real cloud programs, explicit suppression and native shader cloud eligibility. Root's verifier must run that option under its queue. Full Rust engine compilation, program loading, actual clouds/water appearance, pack switching and frame-time gains remain unverified by this source unit.
