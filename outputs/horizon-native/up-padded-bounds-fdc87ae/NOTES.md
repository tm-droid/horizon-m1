# up-padded-bounds
Upstream: horizon-rust/horizon main commit `33c96ac1` (Padded mesh bounds for CPU terrain occlusion (resident bounds reuse)).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/gfx.rs, gfx/cull.rs, gfx/cull.wgsl, gfx/resident.rs
Conflicts / resolution: 3-way clean vs cloud-prep, shadow-scratch, emissive-bsearch, shadow-dedup, anim-frame-compact, fullbright-shaderpack (gfx.rs touched by all)
Risk: medium (culling correctness: popping/holes)
Expected benefit: CPU-side culling accuracy; little help when GPU-bound.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
