# Zoomify settings pilot: native source only

This local source pilot derives from Horizon's official MIT Zoom module at
`horizon-rust/horizon-mods@245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d`, `native/zoom`.
It targets source inspection against Horizon
`e6e12d40c522b8f5ee8740dd861c96689023737a` (native hooks API 153).
No package manifest is invented, no game is built or launched, and nothing is installed or activated.

- `upstream/`: all 14 original native/zoom files, unchanged, including MIT license.
- `source/`: the same module with the focused `zoomify-defaults.patch` applied.
- `pilot-status.json`: exact source hashes, pinned revisions, current user configuration hash,
  implemented behavior and explicit pending work.
- `hook-contract.json`: pinned hook declaration evidence and the engine's zoom clamp/scoping code.

The runtime changes the default Z binding to C, wheel multiplier from 1.25 to 1.5,
and lower wheel limit from 1.25 to 1.0. It preserves the upstream 4x start,
settings codec, hold/release behavior, smooth boolean, sensitivity implementation,
upper 10x limit and all mixin helpers. Existing Horizon key/settings overrides win.
Its existing unit test now expects 4x → 6x and also checks the lower clamp and
reset on a new hold. No Zoomify JSON is copied into Horizon's different settings codec.

This is partial Zoomify behavior: exact timed transitions, scroll smoothness,
levels above 10x, ten-step limit, hand FOV, relative bobbing, spyglass combination,
and secondary F6/HUD behavior remain pending. The engine suppresses native zoom
while scoping and at a factor of 1.0. See the status file for all gaps.

`source/compatibility.json` and the mixin compatibility revision retain upstream's
historical tested revision. Static matching against the target's declarations is
not proof that mixins apply or that a game build succeeds. The upstream README's
Z default and proof/build instructions describe the original module; the README
and proof script are retained unchanged as provenance. Shared `native/tools`
proof/build tooling is outside this source bundle; do not run `proof.py` here.

The logic is a standalone dependency-free Rust library. When an isolated Rust
2024-capable toolchain is available, its focused check is:

```sh
cargo test --offline --locked --manifest-path outputs/horizon-native/zoom-pilot/source/Cargo.toml
```

This checks runtime logic only. Compilation with the target game and game behavior
remain unverified. Keep any build artifacts outside this source bundle.
