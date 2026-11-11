# Upstream gap status — 2026-11-04

Checked official GitHub REST releases, file contents, file histories and issue search at **2026-11-04 01:08–01:09:30UTC (09:08–09:09:30 Singapore)**. This is a timestamped snapshot, not a permanent latest-version claim. No installation, baseline retarget, test, build or source mutation was performed by this check.

## Newer official prebuilt exists

The rolling `nightly` release was published2026-11-03 15:23:23UTC with commit **`294448014fba585f8d5d09dd8886f482493b6417`**, five commits ahead of the installed dated f42 release (published09:30:50UTC that day). The release API listed the dated release first despite its earlier publication: selecting the first entry would miss the newer rolling publication.

- Release snapshot: ID432871107, rolling tag `nightly`; [official release metadata](https://api.github.com/repos/horizon-rust/horizon/releases/432871107). The tag can move; pin the commit and asset identity below.
- ARM64 archive: asset **706072221**, `horizon-macos-arm64.zip`,37239024bytes, updated15:23:20UTC.
- Publisher SHA256: **`26f79d59f62c4ec691d71f565d6cb38f9ade3329e8747d5f42ceba2e983efacc`**. [Immutable asset metadata](https://api.github.com/repos/horizon-rust/horizon/releases/assets/706072221), [source commit](https://github.com/horizon-rust/horizon/commit/294448014fba585f8d5d09dd8886f482493b6417).

The relevant new change is **native-build repair**, not one of the visual fixes: [7f0f0e4 drops the client crate recursion_limit](https://github.com/horizon-rust/horizon/commit/7f0f0e45841ce521c1b03275d71a4ef64bd3ed18), [b1eb5e1 splits the mob-control JSON keys](https://github.com/horizon-rust/horizon/commit/b1eb5e1d5cb5037c4eb57ce3a6f0ac385a9c9540), merged in [PR8193](https://github.com/horizon-rust/horizon/pull/8193). The other new feature is live server allow-flight management. These source facts make the build fix relevant if the current exact-f42 native pipeline fails; they do not establish that an already running build will fail or justify silently changing its target/provenance.

[Exact five-commit comparison](https://github.com/horizon-rust/horizon/compare/f42ef42ef6ceccb3c6a20bea2481d87949a51c81...294448014fba585f8d5d09dd8886f482493b6417).

## Appearance gaps are not fixed by that update

The current `main` snapshot was **`9abb7dc50f01bbd87f79cdc4de237b24d2cfd0b8`**, committed2026-11-04 00:59:44UTC. All three exact owning source files below are byte-identical to installed f42 **both in newer prebuilt2944480 and in this main snapshot**:

| Gap | Owning source | SHA256 at all three revisions | Finding |
| --- | --- | --- | --- |
|96 OptiFine emissive overlay ceiling | `crates/horizon-client-render/src/native_emissive.rs` | `b712963c7735a6225bf218058afb90ad750e8b645d1359fc2557c711c994fa71` | MAX128/NATIVE32, loader break at96 unchanged; no config parameter added in this path. |
| Recolourful Containers core-text sampler fallback | `crates/horizon-shaders/src/core_shader.rs` | `8b8ceec57d1b8ead6684e45ceb559ec3eb33507b798ed45df510d3913de359ad` | Same global sampler rewriting/translation source; no targeted sampler-parameter repair found. Transitive dependency changes were not runtime tested. |
| Guardian body binding and related aliases | `crates/horizon-client/src/mobs/cem.rs` | `4c7f8650070be17789d500aa86dd013fed9ddbcd0dc754d953f0208acb442cd8` | Shared vanilla_part binding remains unchanged; the missing model-specific aliases are not supplied by a newer version of this resolver. |

Immutable newer-prebuilt sources: [emissive loader](https://github.com/horizon-rust/horizon/blob/294448014fba585f8d5d09dd8886f482493b6417/crates/horizon-client-render/src/native_emissive.rs), [core-text translator](https://github.com/horizon-rust/horizon/blob/294448014fba585f8d5d09dd8886f482493b6417/crates/horizon-shaders/src/core_shader.rs), [CEM resolver](https://github.com/horizon-rust/horizon/blob/294448014fba585f8d5d09dd8886f482493b6417/crates/horizon-client/src/mobs/cem.rs). Immutable main-snapshot sources: [emissive](https://github.com/horizon-rust/horizon/blob/9abb7dc50f01bbd87f79cdc4de237b24d2cfd0b8/crates/horizon-client-render/src/native_emissive.rs), [core text](https://github.com/horizon-rust/horizon/blob/9abb7dc50f01bbd87f79cdc4de237b24d2cfd0b8/crates/horizon-shaders/src/core_shader.rs), [CEM](https://github.com/horizon-rust/horizon/blob/9abb7dc50f01bbd87f79cdc4de237b24d2cfd0b8/crates/horizon-client/src/mobs/cem.rs).

## Related history and search limits

The last emissive-loader source change is [7520499,2026-11-02](https://github.com/horizon-rust/horizon/commit/752049907d273ac369c7894ebd5c04faee5b7691), retaining ordinary blocks before CTM tiles. [Initial block-emissive PR6457](https://github.com/horizon-rust/horizon/pull/6457) is already merged and does not remove this96 limit. Core-text translation's file history still ends at [e759c90,2026-10-30](https://github.com/horizon-rust/horizon/commit/e759c905f1863bd04529adef310164215c52ef9c). Recent CEM history includes [15bbf5c,2026-11-03](https://github.com/horizon-rust/horizon/commit/15bbf5c3fe03907ee67b2a4de07da94c1509d96d), a block-under-mob lookup scheduling change, not the guardian alias fix.

Bounded official issue searches for `emissive 96`, `sampler2D text` and `guardian CEM body` did not find a targeted newer repair. Search results included Iris-shadow issue8176 and sheep-model issue7986; neither title/closed status establishes repair of the exact local core-text sampler failure or guardian resolver aliases. Source comparisons are stronger evidence here than an unrelated closed issue. This does not rule out an unmerged, differently titled or future patch.

## Action

Keep the tested f42 comparison baseline and all in-progress build identity unchanged. Finish the current build or diagnose its concrete failure. If the known recursion-limit problem appears, evaluate the two verified upstream build-fix commits explicitly, or prepare the newer official runtime separately with its own provenance and fresh acceptance. Continue treating the three appearance gaps as unresolved; there is no verified update-only or newly exposed config solution for them in this snapshot. A dependency-only shader improvement remains untested, so retain the exact core-text translator acceptance case.
# Follow-up on the November 4 rolling build

The published rolling build `67dad0d1a5adca139b426c8114e74a33b376ba64` is a small title panorama and mob movement update. Its `pack_post.rs` Git blob is byte-identical to both f42 and `2944480` (`6a17557911c8c59653f2b5f4bbe8a24d46e13fbb`). The shader-removal release note is copied from the known-issues file that also appears in the measured f42 source. The active comparisons use f42. [Official releases](https://github.com/horizon-rust/horizon/releases) · [Exact rolling commit](https://github.com/horizon-rust/horizon/commit/67dad0d1a5adca139b426c8114e74a33b376ba64)

Main `3319108619dfc0c8057b4fd2921fe1f17d0b79e2` changes Iris post-processing buffer clears, blend behavior, RGB alpha handling, shadow color targets, and mipmap timing. Other changes reduce sprite atlas deduplication bookkeeping and calculate far terrain reductions on demand. The next published build containing these changes warrants a separate shader and flight comparison. Their M1 impact and the Mellow right-side artifact remain unmeasured. [Post-processing source](https://github.com/horizon-rust/horizon/blob/3319108619dfc0c8057b4fd2921fe1f17d0b79e2/crates/horizon-client-render/src/gfx/pack_post.rs) · [Atlas bookkeeping](https://github.com/horizon-rust/horizon/pull/8787) · [Far terrain](https://github.com/horizon-rust/horizon/pull/8815)

The owning source for native emissives, the core GUI shader translator, CEM bindings, and the older-server connection adapter remains byte-identical in f42, the rolling build and that main commit. Main improves persistence for specific player fields, including velocity and food exhaustion. Unknown Fabric world state and server version coverage still need separate checks. The official mod catalog yielded no verified general M1 optimizer. [Player save patch](https://github.com/horizon-rust/horizon/pull/8693) · [Official catalog](https://playhorizon.dev/mods)

