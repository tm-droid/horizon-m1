# up-tick-shrink
Upstream: horizon-rust/horizon main commit `076e9533` (Scheduled-tick queues release memory once drained).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: core/ticks/mod.rs (+59)
Conflicts / resolution: none
Risk: low
Expected benefit: Memory only (8 GB box); no FPS effect.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
