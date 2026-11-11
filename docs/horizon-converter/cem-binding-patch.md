# f42 CEM binding candidate

Source-only candidate for Horizon commit `f42ef42ef6ceccb3c6a20bea2481d87949a51c81`. **Not built, activated, or runtime-validated.** No native/public hook additions are needed: this extends the existing private `mobs/cem.rs::vanilla_part` resolver shared by replacement discovery, attachment, and animation-name lookup.

The [binding audit](cem-binding-gaps-2026-11-03.md) records installed EMF 3.3.12 bytecode offsets and exported node paths/pivots for each alias. This patch adds guardian body→head, wolf/armor mane, happy-ghast harness body, small-puffer tail/eyes, tropical-pattern top fin, salmon fins/tail (including the identical named small/large skeletons), and horse/skeleton-horse armor neck/mouth. It adds only the audited armor contexts; zombie-horse armor and wolf collar remain outside this candidate.

`villager_baby/bodywear→bb_main` is checked before the existing `_baby` removal. That removal moves from `CemLayer::build` into the shared resolver so all three existing call sites retain the original name until the exact override is consulted. Other baby aliases retain the previous adult-family normalization, including embedded `_baby` layer names. The patch preserves existing depth-first searches, raw-name fallback, custom ID precedence, attach/replacement behavior and pose construction. It never changes pack parts, IDs, geometry, UVs, transforms, skeletons, or expression strings. In particular, piglin-baby `jacket` remains unresolved, with the original zero-read fallback.

The candidate directory is `outputs/horizon-native/cem-binding-f42/`. It contains the exact upstream `cem.rs`, its original MIT `LICENSE`, the reviewable `cem-binding.patch`, `provenance.json`, and `apply.py`. The original upstream file was downloaded from the [pinned raw source](https://raw.githubusercontent.com/horizon-rust/horizon/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/mobs/cem.rs) and independently matched the earlier research cache. Source SHA256: `4c7f8650070be17789d500aa86dd013fed9ddbcd0dc754d953f0208acb442cd8`. Candidate SHA256: `819c426566a24f6511d8b9794e01e008b6cdb5bdeed46cb07d76030336f02006`. Diff SHA256: `12f6e4f994519840396e498899a3bbfe17b8797a74ad148328a90d64c92611f9`.

## Prepare a later build

Obtain a clean official Git checkout at the exact commit above. Supply its root explicitly; the destination must not exist. From this launcher workspace:

```sh
python3 outputs/horizon-native/cem-binding-f42/apply.py \
  --source-root /private/tmp/horizon-f42-clean \
  --output-dir outputs/horizon-source-candidates/f42-cem-binding
```

The utility requires the exact Git HEAD, a fully clean checkout (including untracked files), the exact source hash, unique edit contexts, and the expected patched hash. It rejects existing destinations, source/destination overlap, symlinked target paths and destinations outside `outputs/horizon-source-candidates/` or `/private/tmp/`. It creates a full fresh source copy, excluding root `.git` and Cargo `target`, preserving licenses and other source bytes. It changes only the copied `cem.rs` and adds `cem-binding-candidate.patch` plus `cem-binding-candidate.json` with before/after/diff hashes and provenance. The source checkout, original packs and published runtime are untouched. A copy failure can leave an incomplete destination; inspect/remove that candidate before explicitly choosing another fresh destination.

The utility does not download tools, compile, activate, launch or benchmark. Root must schedule any later build through the shared device queue using the [native build plan](native-port-build-plan-2026-11-03.md), retain candidate provenance, and label the result as a modified engine rather than an unchanged official build.

## Checks still pending

Authored command (not run in this source-only task):

```sh
python3 -m unittest discover -s tests -p 'test_horizon_cem_binding_patch.py' -v
```

The tests compare pinned source/diff/provenance, exercise fresh-copy/source-drift/dirty-checkout/destination guards, and compile the actual extracted Rust resolver with positive and neighboring negative assertions. That focused test invokes `rustc` and its tiny assertion executable, without Cargo, game code or public hooks; it skips that assertion case when `rustc` is absent. A passing patch test is not a full engine build or visual proof. No tests or native builds were run by this worker; artifact generation only produced the diff and recorded hashes.

Later acceptance: full exact-target build; unchanged original pack/source hashes; unique canonical targets in each intended layer; guardian custom descendants reachable and the 100 cascading unknown-target warnings gone; no duplicate vanilla eye/spine/fin/clothing surfaces; zero/nonzero pose matrices preserve original pivot and parent composition. Use grouped shader-independent scenes for guardian/elder tails/eyes/spines, harness riding, wolf shake, all three salmon sizes, puffer inflation, tropical patterns, horse armor/head movement, and baby-villager clothing. Record the baby-piglin warning separately. The forecast of addressing **132/133 warnings is unverified**, and fewer warnings alone do not establish parity. Adult-file fallback onto a baby consumer remains subject to the engine's existing file-context behavior; this candidate does not redesign that separate mechanism.
