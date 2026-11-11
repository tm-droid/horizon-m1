# up-shadow-nooutput
Upstream: horizon-rust/horizon main commit `4a701935` (Shadow program with no output keeps water, without boats' patches).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/gfx/pack_post.rs, pack_post/{full_outputs_tests,image_formats}.rs (new), shaders/post.rs, post/lifecycle_tests.rs (new)
Conflicts / resolution: post.rs test-module conflict: upstream parent had extracted buffer_blend_tests/material_variant_tests, base keeps buffer_blend_tests inline. Kept base's inline module; dropped orphan buffer_blend_tests.rs. lifecycle_tests extraction kept. Non-test hunks auto-merged with pass-merge/composite-overwrite/terrain-single-draw/shadow-dedup region
Risk: medium-high (shadow path, adjacent to shadow-dedup)
Expected benefit: Only matters if a pack has a shadow program without outputs; shadow-dedup may already cover the cost.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
