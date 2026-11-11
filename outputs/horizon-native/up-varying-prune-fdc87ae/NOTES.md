# up-varying-prune
Upstream: horizon-rust/horizon main commit `d84e8fa4` (Varying the fragment stage never reads takes no location (new translate/varyings.rs)).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: shaders/translate/mod.rs, translate/varyings.rs (new)
Conflicts / resolution: 3-way clean vs fullbright-shaderpack
Risk: medium (588 lines, GLSL translation)
Expected benefit: Avoids location-limit failures; fewer interpolants for MakeUp-style packs. Needs shader-crate tests run.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
