# up-pack-dynlights
Upstream: horizon-rust/horizon main commit `5ec521bb` (Horizon dynamic lights as uniforms, horizonTier for terrain/entities).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/gfx/pack_atlas.rs, pack_atlas/fade_test.rs, pack_entities.rs, pack_uniforms.rs
Conflicts / resolution: 3-way clean vs fullbright-shaderpack (pack_uniforms.rs)
Risk: medium
Expected benefit: Feature, no perf benefit for MakeUp (adds per-frame uniforms). Optional.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
