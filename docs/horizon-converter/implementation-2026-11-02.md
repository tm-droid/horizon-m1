# Horizon converter implementation — 2026-11-02

The improved migration is in `outputs/horizon-converter/2026-11-02-Tanush-v2/`.
It finished with exit 0, `prepared-needs-review`, and identical before/after
SHA256 inventories for 666 source files. The Java instance was not edited and
performance work remains paused at the user's request.

## Delivered

- 239 active Java mod reports and per-mod agent tasks, 293 nested archive
  analyses, six nested cache hits, and explicit remaining coverage limits.
- 210 resource-only mod asset candidates with licenses, source hashes and
  provenance. These omit Java behavior and data registrations and are not enabled.
- All 52 selected file packs copied, with vanilla retained in the original
  53-layer selection; Mellow source/override sidecar preserved. Twelve selected
  settings files are retained as source evidence, without semantic translation.
- 1,921 grouped tasks reference all 64,865 raw findings exactly once. Detailed
  evidence remains in `raw-review-queue.jsonl` and the mod reports. No blocking
  input/export tasks remain in this snapshot.
- `appearance-contract.json` prioritizes Fresh Animations, EMF/ETF, connected
  textures, fonts, sounds, layer order and Mellow. Java engine optimizers have a
  separate classification, always retaining feature/settings review.
- Legal case-distinct ZIP entries are preserved; filesystem extraction still
  rejects conflicting paths. The former three archive export blockers are gone.
- Fabric metadata uses strict parsing first and a recorded control-character
  fallback for the five installed descriptions accepted by the loader. Original
  metadata bytes are not rewritten.
- Source pack metadata is preserved as evidence; omitted filter/overlay semantics
  and overlay assets are explicit. Nested scans use depth/member/shared read caps,
  hash caching, and archive-chain provenance.

Twelve top-level analyses retain coverage limits (class/evidence caps, undeclared
nested archives or incomplete descendants); these remain review work. Static
inspection and successful preparation do not establish native feature parity.

## Native Zoomify pilot

`outputs/horizon-native/zoom-pilot/` contains 14 verified files from the official
MIT native Zoom source at `245ab9b4f6108ca9dc5a7184fe6a3b7e06a1eb1d`, an unchanged
baseline, provenance and a focused patch. Runtime defaults now use C, scroll
multiplier 1.5 and minimum factor 1.0, retaining the engine's maximum 10. Starting
factor 4 is already the upstream default. Related assertions were updated.

The standalone runtime compiles and passes its three Rust tests. This is not a
full Zoomify replacement: >10x zoom, exact transitions, hand/bobbing behavior,
spyglass combination and F6 configuration parity remain unresolved. The upstream
bundle metadata's historical Horizon pin is deliberately unchanged; it has not
been built into the research target or installed into a game. See
`zoomify-pilot.md`, `pilot-status.json` and `standalone-verification.json`.

An isolated minimal Rust 1.95.0 toolchain was installed under
`outputs/horizon-runtime/toolchain/`, with no global PATH/profile/HOME changes.

## Isolated launcher preparation

The official ARM64 launcher `launcher@0.2.37` is staged at
`outputs/horizon-runtime/launcher-app/Horizon.app`.
SHA256: `e3e8a21f229d8b64602a6ce64c21e2d2fddffa4129cb10168aa0d5d51985b227`.
Its 14,547,266-byte archive matches publisher metadata; executable architecture
was inspected without running it.

`launch-isolated.command` sets verified Horizon/XDG storage variables to local
workspace directories and disables launcher self-update. It was created but
**not executed**. `installation.json` records the exact app, environment and
artifact provenance. No launcher/game was opened, no game assets/worlds were
prepared, and no candidate native mod or pack was activated. Runtime isolation
and visual behavior have not been tested. The launcher release and converter
research commit differ; future game/native compatibility needs verification.

## Checks

All substantial work ran through the shared device queue. The final Python check:

```sh
python3 -m unittest discover -s tests -p 'test_horizon*.py' -v
```

Exit 0: 61 tests, 60 passed, one skipped because this case-insensitive source
filesystem cannot represent a case-alias folder fixture. Log:
`/private/tmp/horizon-native-python-tests.log` (exact actual path also in the verification JSON).

The isolated Cargo command used `+1.95.0 test --offline --manifest-path
outputs/horizon-native/zoom-pilot/source/Cargo.toml --target-dir
outputs/horizon-runtime/toolchain/target/zoom-pilot --jobs 1`: exit 0, three tests
passed. Exact absolute argv, CARGO_HOME/RUSTUP_HOME, publisher/installer hashes,
versions and logs are in `outputs/horizon-native/zoom-pilot/standalone-verification.json`.

Regeneration command, exit 0:

```sh
python3 tools/horizon-convert.py --game-dir instances/Tanush-26.3/minecraft --output outputs/horizon-converter/2026-11-02-Tanush-v2 --stage-packs --stage-mod-assets
```

Launcher preparation command, exit 0:

```sh
python3 tools/prepare-horizon.py --plan docs/horizon-converter/install-plan.json --output outputs/horizon-runtime
```

Independent review found no remaining blockers. It checked source/staging hashes,
pack order, settings, complete grouped/raw line accounting, native provenance,
and launcher staging safety. Review and tests exclude game builds, launches,
benchmarks and visual parity. Base Horizon, Mellow and Complementary Reimagined
remain future runtime comparisons.
