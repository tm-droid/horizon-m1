# Private Better Lanterns overlay candidate

`tools/horizon-lantern-compat.py` prepares a tiny independent resource pack for the three audited texture-key mismatches in [the shared appearance audit](emissive-cap-gaps.md#2-minecraftblock-mismatched-better-lanterns-texture-keys). It does not activate a pack, edit options, launch a game, or modify the source pack/native assets. **No rendered fix or visual parity is established.**

The candidate retains the vanilla children's parents and every existing model/texture field. It adds only:

| Child | Added bindings |
| --- | --- |
| `iron_chain.json` | `chain` and `particle` = existing `texture` |
| `lantern_hanging.json` | `hanging_lantern` and `particle` = existing `lantern` |
| `soul_lantern_hanging.json` | `hanging_lantern` and `particle` = existing `lantern` |

The selected Better Lanterns custom parent geometry remains in the original pack. Standing/copper models and texture images are not copied or rewritten. The source author credit, original template bytes and metadata remain in the original archive and the candidate's source evidence.

## Generate only after queued validation

Example from this launcher workspace; use the original shared device queue for generation:

```sh
python3 tools/horizon-lantern-compat.py \
  --pack 'outputs/horizon-converter/2026-11-04-Tanush-f42-v3/resourcepacks/Better Lanterns v1.4.0 - 26.2+26.3.zip' \
  --vanilla-assets 'outputs/horizon-runtime/launcher-data/versions/nightly-2026-11-03-f42ef42/.local/horizon-client/26.3/assets' \
  --output outputs/horizon-native/lantern-compat-candidate-r1
```

`--vanilla-assets` means the prepared `assets/` directory containing `minecraft/models/`, not a game directory. `--output` must be a fresh directory disjoint from both the source pack directory and assets. The result is `lantern-compat.zip`, `provenance.json`, and byte-preserved source evidence. The ZIP has only three child JSON files and new `pack.mcmeta`. Activation would require placing it above Better Lanterns in a disposable profile; the tool never does that.

The source archive's exact `pack.mcmeta` has SHA256 `a4be1fb6933f9e366052d935f39195a035baed080c123a9a51bfba6304041689`, declares `pack_format:97`, and advertises formats88–99. The generated overlay derives format97 from those guarded bytes and narrows `min_format`/`max_format` to97. This is metadata for this source-qualified candidate, not a claim of compatibility with every97-format pack or another runtime. No format number was inferred from a Minecraft version name.

The tool checks that exact metadata, all three audited parent templates and all three vanilla children against recorded hashes. It refuses changed inputs, a pack that newly overrides any target child, duplicate relevant ZIP members, symlinks, nonregular/oversized inputs and an existing/overlapping output. Reads are bounded; it never extracts arbitrary archive paths. Unexpected or changed sources require manual review. An I/O failure during output writing may leave a partial fresh directory; it must not be activated.

The CLI inputs do not express the whole selected pack stack. Before activation, the caller must confirm that these remain the effective parent/child winners. That was audited for the captured52-pack f42 stack; another later pack can invalidate the assumption. The provenance records this unresolved condition and keeps `runtime_visual_parity_verified:false`.

## Authored validation, not executed in this source task

```sh
python3 -m unittest discover -s tests -p 'test_horizon_lantern_compat.py' -v
python3 -m py_compile tools/horizon-lantern-compat.py
```

The four tests use seven small byte-preserved real source examples under `outputs/horizon-native/lantern-compat-source/fixtures/`; their provenance records the origin and hashes. Checks cover exact semantic changes, preserved input/evidence bytes, metadata derivation, drift/duplicate/child-override refusal and output/symlink guards. They do not read an installed game. No tests, overlay generation or runtime actions were executed by this author.

Independent review and queued tests are required before use. Then render daylight/night views of iron chains and ordinary/soul hanging lanterns, plus standing/copper controls, at unchanged shader/settings/geometry. Require correct face and particle textures, no magenta/black fallback, unchanged custom geometry and no new pack failures. Verify Java/EMF baseline differences separately; the source diagnosis predicts a texture gap but is not a runtime comparison.

## Device result

Ticket 68 ran `python3 -m unittest discover -s tests -p 'test_horizon*.py' -q` using isolated Rust 1.99.1. It passed 127 tests and skipped one filesystem case check. Both subsequent f42 tests ran with `--case packs --scene lantern --fps-cap 60 --offscreen --compatibility-only`, the v3 migration and the audited native options candidate. The `f42-lantern-overlay-r1` profile added `--extra-pack outputs/horizon-native/lantern-compat-f42-r1/lantern-compat.zip` above all 52 packs. Each client exited 0. Live pack order and five block states were verified.

The control's iron chain, ordinary and soul hanging lanterns, and copper and standing controls already show their expected textures in both inspected views. The overlay has no visible benefit in this fixture. Both logs contain the same generic `minecraft:block/` missing-texture message. The source warning alone did not reproduce a visible defect here, so keep the overlay as evidence only. Breaking particles, other angles and Java parity remain untested. The raw captures and result records are in `outputs/horizon-runtime/tests/f42-lantern-{control,overlay}-r1/`.
