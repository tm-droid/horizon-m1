# up-metal-flat
Upstream: horizon-rust/horizon main commit `702b0895` (Metal always draws vanilla terrain flat (min_sections=0)).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/gfx.rs (+4)
Conflicts / resolution: textual none; behaviour overlaps terrain-single-draw/fullbright-shaderpack (same gfx.rs region touched by 5 stack patches)
Risk: medium (behaviour change)
Expected benefit: Mostly fixes Intel-Metal leaf dropping; M1 gain unproven (fewer draw calls, same GPU work). Optional; benchmark first.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
