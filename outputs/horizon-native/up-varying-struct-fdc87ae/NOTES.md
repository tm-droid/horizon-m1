# up-varying-struct
Upstream: horizon-rust/horizon main commit `b4b59960` (Struct defined in a varying's declaration counts as varying).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: shaders/translate/mod.rs, scan.rs
Conflicts / resolution: 3-way clean; apply after up-varying-prune
Risk: low
Expected benefit: Pack compatibility fix.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
