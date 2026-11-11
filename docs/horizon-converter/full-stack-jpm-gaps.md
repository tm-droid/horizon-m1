# Full-stack missing JPM imports — 2026-11-04

The11 runtime warnings are **absent resource references in higher-priority addon models**, not evidence of Horizon resolving a present file from the wrong folder. No global native filename fallback is justified by this evidence. Keep these imports visible as grouped pack-compatibility blockers; do not generate empty JPMs or claim that suppressing the warnings restores animations.

## Effective inputs and exact evidence

The selected stack has53 layers including vanilla. Layer42 is FreshAnimations1.11.1; layer43 FA+AllExtensions1.9.2, layer46 3D Harness x Fresh Animations, and layer48 Fresh Skeleton Physics override the relevant JEMs. Later layers win. Each missing path is `assets/minecraft/optifine/cem/<entity>_animations.jpm`. Central-directory inspection of all52 selected ZIPs found none of these11 names anywhere, including the EMF folder. This is an effective selected-pack inventory, not a claim about all possible Java-mod resource providers or unselected packs.

| Entity | Winning layer / pack | Base FA1.11.1 imports instead | Winning JEM SHA256 |
| --- | --- | --- | --- |
| parched | 48: Fresh Skeleton Physics.zip | skeleton_animations.jpm | `99c1c3337359773766a10f79a20d70d99795392692e048386badb47f7aef3997` |
| bogged | 48: Fresh Skeleton Physics.zip | skeleton_animations.jpm, bogged_mushroom_animations.jpm | `7c7998fd0560cf7d7e10ed0a954b200407f453694ae6f058d19640e0b9e20794` |
| stray | 48: Fresh Skeleton Physics.zip | skeleton_animations.jpm | `431a7860aa62e15bd3848b8bb2c789c894fda47fb06003ad016af9edb18f5d3c` |
| cave_spider | 43: FA+All_Extensions-v1.9.2.zip | spider_animations.jpm | `4fbe8b3fe36cf7e01014710f7200d759490581c36a44192ae2c5a415426922d9` |
| happy_ghast_harness | 46: 3D Harness x Fresh Animations.zip | happy_ghast_animations.jpm | `3fccbb506071d01ef91a641c17c9230098c471bccacc5790273a75273fc0fc1c` |
| skeleton_horse | 48: Fresh Skeleton Physics.zip | horse_animations.jpm | `01e1b2382a6439c1c75b8eb0b225e017a2e8e780d41a5d3ff2b3fa166895fbe4` |
| creeper_charge | 43: FA+All_Extensions-v1.9.2.zip | creeper_animations.jpm | `747bdcef3ad6d90f8f8c9f5ad3b017c7f496f98d019bdb4e6e51ce6e9cc6ed9d` |
| mule | 43: FA+All_Extensions-v1.9.2.zip | donkey_animations.jpm | `616802e095fe0f529eb8fb5f479c4226595a4c6362c8bc90c2c9c4859828e809` |
| mooshroom | 43: FA+All_Extensions-v1.9.2.zip | cow_animations.jpm | `f0fb34ef12bc7f000b6cdacb294aea3f0924114a654c6b9c712027f4bc7148d6` |
| elder_guardian | 43: FA+All_Extensions-v1.9.2.zip | guardian_animations.jpm | `a1c2a4da1771f61321a3b45d2bfc3cd8e51f4c5208b404cbe0954e64028b109a` |
| wandering_trader | 43: FA+All_Extensions-v1.9.2.zip | villager_animations.jpm | `9e05010eeafa9c0c8ad3051cc04e4bbae9c4da11299b5dde1a96e3a078195cf6` |

All paths in the table are relative to `assets/minecraft/optifine/cem/`. The three addon root entries inspected directly contain only the root part/id/import/attachment transform, with no own animation array to supply the absent import. At least that imported animation carrier is therefore missing from native evaluation. The remaining geometry/parts can still load; a world that looks plausible does not prove the lost animations are present.

Pack ZIP hashes:

- `FreshAnimations_v1.11.1_26.1+.zip`: `f9c2f58eb4cc109b7055d9d0da163269caf61af816538e71ed4f1ea97607372e`.
- `FA+All_Extensions-v1.9.2.zip`: `027acba5f64c9d1bf5ccb8daecb7fc756961bfeee866434a0ee5f7809a48d326`.
- `Fresh Skeleton Physics.zip`: `3ce9fcec650dffa5524b195088d6dc386d6b6c7e4cf2f2914724c0ae4f22cb2d`.
- `3D Harness x Fresh Animations.zip`: `5b872f867a5e4113f9e4830af60b13bb8004993b8223d6a10e3bbc81f50d5e35`.

## Native behavior and diagnosis

Pinned f42 `crates/horizon-optifine/src/cem/model.rs` reads a referenced JPM using the resource-relative resolved path and caches the result per file. Missing input produces the exact warning; the importer records it and skips that `models[]` entry. It does not search semantically related entity names or merge a lower-priority JEM with an overriding JEM. [Import failure handling203–214](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L203), [JPM resolution284–311](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-optifine/src/cem/model.rs#L284). Verified cached source SHA256: `267cd4eddd66185c3f844dfe9abdc98ba91be70a355c5c0216c7aa2df0128ed2`.

The base FA JEMs provide direct evidence for the shared animation-family references in the table. The addon overrides instead request absent entity-specific files. This supports a **pack-version/reference mismatch inference**, rather than a missing Horizon lookup feature. It does not establish that the same addon is correct or incorrect in Java/EMF: Java fallback behavior and all mod resource providers were not audited in this bounded pass. EMF's public format also describes `model` as an external part-model file and supports sharing animation JPMs; it does not document an implicit `<entity>_animations` alias rule. [EMF model format](https://github.com/Traben-0/Entity_Model_Features/blob/master/.github/emf_model.txt), [EMF animation format](https://github.com/Traben-0/Entity_Model_Features/blob/master/.github/emf_animation.txt).

The reusable converter preflight lists9 unresolved dependencies; its bounded budget means that count is incomplete. The actual runtime supplies11 concrete missing imports. Preserve both results and the coverage-limit note; do not treat the preflight's9 as exhaustive.

## Smallest justified next action

1. Group the11 failures into three tasks by overriding addon, retaining each source JEM hash, import pointer `/models/0/model`, layer order and missing path. Check for compatible addon updates before locally adapting assets. Do not change the Java originals.
2. If no compatible addon exists, a **private, explicit, hash-guarded overlay candidate** can replace only the erroneous import references using the base FA references as evidence. This is a pack migration, not a generic engine resolver fix. Check target bone/variable dependencies first; similar filenames alone are insufficient to guarantee animation compatibility.
3. Bogged needs special handling: current base FA imports both `skeleton_animations.jpm` and `bogged_mushroom_animations.jpm`. A one-string bogged alias does not restore the second carrier. Preserve addon-specific physics/geometry and check both animation dependencies before claiming support.
4. Acceptance is one full-stack run, unchanged original/source ZIP hashes, resolved imports, no new unknown animation targets or duplicate geometry, and short grouped idle/movement checks for the skeleton family, shared-family mobs and harness. The user can later judge subjective appearance. Fewer warnings alone is not parity.

No source/native resolver patch is warranted for these11 absent files on current evidence. No files were rewritten, no empty stubs were introduced, and no builds, tests, launches or installs were performed by this research task.
