# up-dimension-swap
Upstream: horizon-rust/horizon main commit `e1434f2e` (Less dimension-swap overhead; cached raycast chunk lookups).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: client/game/levels.rs (+6), client/mobs/world.rs (+39/-3)
Conflicts / resolution: none (disjoint from stack)
Risk: low
Expected benefit: Targets the 340-1000 ms stall per dimension change; does not fix 2.5-3 s first shader compile. Overlaps nothing in dimension-warm.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
