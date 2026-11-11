# Block entity distance probe

The enabled Fabric BlockEntityRD 1.0.0 JAR has SHA-256 `2f8de175d785821b8bb44d399e088c4fa4e13b4dc25206acf3feb1d87b139d32`. Its installed config enables per-type distance checks, with common cuts at 24, 32 and 48 blocks. The config lists chests at 48, signs and banners at 32, decorated pots at 24, and an optional global value of 40. The JAR's checker compares the squared distance from the center of the block. Horizon already keeps a separate 256-block End gateway range, which this experiment preserves.

Horizon submits cached native static geometry as a whole section. A per-entity cutoff inside the renderer could still draw cached members beyond that cutoff when the camera moves. Sending mixed sections through the dynamic CPU batch could also make former static geometry eligible for a different shadow path. The probe measures ordinary candidates and the different geometry submissions without moving work between those paths.

Check the patch from the launcher data directory:

```sh
git -C outputs/horizon-runtime/m1-performance-r11/20261108-091244/source \
  apply --check --whitespace=error \
  "$PWD/outputs/horizon-native/block-entity-distance-r11/block-entity-distance-probe.patch"
```

Run the candidate with `HORIZON_BLOCK_ENTITY_DISTANCE_PROBE=1` inside the shared device queue. The usual `bench` and `stats` summaries gain a `block_entity_distance_probe` object. All counters are summed over measured frames, so divide by `frames` for per-frame comparisons.

- `ordinary_candidates_by_band` counts vanilla candidates that passed section and block visibility and fit the current renderer distance. The bands are disjoint and use full 3D center distance. Candidates can later contribute no geometry. The bands measure opportunity for a distance limit.
- `special_candidates` tracks beacons, gateways and off-screen outlines separately under their current limits.
- `vanilla_cpu_quads` and `mod_cpu_quads` count the submitted CPU geometry before the renderer routes it. Legacy packs can classify that geometry into entity/block stages and shadow subsets. Native shader packs can include the CPU entity batch in shadows. These are submitted quads, and actual shadow draws are a separate measure.
- `native_static_quads` counts the visible GPU section batches Horizon would draw. It includes all members of each selected section, even where the section spans distance bands.

For an attribution fixture, use a disposable world and a stationary, verified camera with loaded groups of separated chests, signs with text and decorated pots near distances 16, 28, 40 and 56 blocks. Keep one ordinary group beyond 64 as a negative control. Verify exact block positions and camera coordinates, then warm the caches before taking a fixed-duration sample. Compare an empty scene with the same terrain, in both native and MakeUp modes. Require nonzero expected bands, no ordinary count from the beyond-64 group, positive vanilla CPU quads for MakeUp, and positive native static quads with its model caches enabled. Cross a section boundary, return to the original camera, and verify candidate counts and visible static section behavior separately. Check a loaded gateway beyond 64 and a beacon in view. Keep shader options, cache settings, camera, render distance and asset order fixed within each comparison. A probe-disabled run should omit the new object and look identical.

Exact-source apply check passed. Compilation, runtime samples and performance remain pending.
