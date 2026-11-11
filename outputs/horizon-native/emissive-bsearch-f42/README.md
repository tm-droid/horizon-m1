# emissive-bsearch-f42 (audit candidates #1 and #7)

Status: **ready, UNBUILT / UNTESTED** (anchors and pure-logic tests only; no cargo, no game).
Base: f42 + cloud-prep + shadow-scratch (candidate-source). Applies standalone or after qos-backport/sprite-compress.

## What
1. `terrain.wgsl` `terrain_vertex`: the per-vertex linear scan of `globals.emissive_layers` (up to 128 dynamically
   indexed UBO reads) becomes a lower-bound binary search (8 bounded halvings, max 128 pairs).
2. `native_emissive.rs`: new `optifine_table()` (the OptiFine half of the table, flagged `CUTOUT`) and
   `table_cached()` (same output as `table()`). `RenderAssets` gets `emissive_table`, built once in `RenderAssets::load`.
   `game.rs` calls `table_cached` with it, so a frame with no native-mod requests (the usual one) does zero name
   lookups and no BTreeMap build. `table()` is kept (tests compare against it).
3. `gfx.rs`: `debug_assert!` that the table handed to the shader is strictly increasing by base layer.

## Why this is exact
`table()` builds from a `BTreeMap<u32,_>`, so entries are sorted ascending and unique by `[0]`. The old loop returns
the first entry with `x == layer`, stopping at the first `x > layer`; a lower bound returns the first `x >= layer` and
the code then requires equality: same pair for every input, including duplicates (first wins) and an empty table.
Pairs past `emissive_count` (zero padding) are never read. A layer with the high bit is masked first, as before.
The CPU side needs no new sort: the invariant already holds and is now asserted (debug) and unit tested.
`table_cached` equals `table` because `mappings()` + `or_insert` over the same OptiFine list is what produced the
cached vector, and native entries are inserted first exactly as before (native non-empty takes the generic path).
`RenderAssets` is behind `Arc` and `emissive`/`sprite_layers` are never mutated after load, so the cache cannot go stale.

## Expected gain / risk
Shader off, 52-pack stack (full 128-pair table): 0.5-2.5 ms GPU (audit estimate, unmeasured); CPU 0.02-0.1 ms.
Shader packs: none (pack terrain has its own vertex stage). Visual risk: zero by the argument above.
Compile risk: low; new code is plain std. `entity.wgsl` has the same table but never scanned it.

## Tests
- Passed here without cargo (`standalone_tests.py` + isolated rustc, 5 tests): search == scan for every table size
  0..=128 and every layer, 8 halvings suffice for MAX, WGSL text uses the search and the 128-entry array,
  strictly-increasing tables, `table_cached == table` (native overrides, missing names, >32 native requests, empty).
- After the build: `cargo test -p horizon-client-render native_emissive` (same tests inside `emissive_lookup_tests`).
- Harness: shader-off `--case packs` flight and static, original/patched/patched/original; exact image diff of end captures.
- WGSL: `naga` is not installed, so terrain.wgsl was not parsed by a validator. The edit uses only constructs already in
  the shader (`var`, `for`, `&&` in a for condition, `min`, uniform array indexing). The build's pipeline creation
  validates it; a shader error shows at startup, not as a silent change.

## Files
`prepare.py` + `edits.json` (library: `render(relative, bytes)`), `emissive-bsearch.patch` (`git apply -p1`),
`standalone_tests.py`. MIT, as the sibling transforms.
