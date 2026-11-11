# up-lod-locks
Upstream: horizon-rust/horizon main commit `2d708ace` (Far terrain: render thread try-locks sampling/meshing queue instead of waiting).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/lod.rs (+16/-2)
Conflicts / resolution: none
Risk: low
Expected benefit: Removes render-thread lock waits; only matters with far-terrain/LOD on.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
