# up-terrain-wire5
Upstream: horizon-rust/horizon main commit `3d5216e7` (Terrain vertex outputs in 5 locations not 12 (TerrainWire)).
Base: fdc87ae + daily3 stack (applies in the order listed in the summary doc; generated sequentially by `git cherry-pick -n`, 3-way).
Files: render/terrain.wgsl, oit_world.wgsl
Conflicts / resolution: 3-way clean vs emissive-bsearch (terrain.wgsl). visbuffer.wgsl still uses TerrainOut, which upstream keeps
Risk: medium (WGSL; naga/pipeline errors are runtime)
Expected benefit: Upstream numbers are RX 580 (+13..21%). M1 is TBDR so gain smaller but vertex-stage bound shaders benefit; best GPU candidate.
Verified: `git apply --check` in sequence on scratch copy only. NOT compiled or tested (no cargo run allowed).
