# up-rain-depth
Upstream: horizon-rust/horizon main commit `cca1842d` (Rain/snow never write depth (Iris behaviour)).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/gfx/pack_post.rs, pack_post/weather_depth_tests.rs, shaders/post.rs
Conflicts / resolution: one comment-only hunk in pack_post.rs (HEAD has clouds_off lines from stack); resolved keeping stack lines + new comment. Also touches pack-pass code of pass-merge/composite-overwrite/terrain-single-draw (clean)
Risk: low
Expected benefit: Fixes pack depth reads of rain columns; may reduce overdraw/rain cost under MakeUp. rain.depth property now unread (field kept).
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
