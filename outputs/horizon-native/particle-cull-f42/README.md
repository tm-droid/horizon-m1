# particle-cull-f42 (java-perf-mod-map port #3)

Status: **ready, UNBUILT / UNTESTED in engine** (anchors, `git apply --check`, rustc `-Zunpretty` parse, std-only conservativeness test; no cargo, no game).
Base: r2 stage. Touches `crates/horizon-client-render/src/particles.rs`, `crates/horizon-client/src/game.rs` (shared with adaptive-upload-f42, order-independent), `game/shader_packs.rs` and `game/native_shaders.rs`.

## What
- `ParticleEngine::render` becomes a wrapper over new `render_in_view(.., in_view, out)`; `render` passes an always-true test, so probes/tests are unchanged.
- In the loop, right after `quad_size`, the particle's centre box `center +- cull_reach(size)` (`1.5*|size| + 0.05`, bounding the sqrt(2)*size quad diagonal in any rotation, shriek/vibration two-quad forms included) is tested; outside means `continue` before light lookup and vertex build.
- `game.rs` entity geometry passes `Frustum::intersects` from `self.view_frustum` (same camera-relative convention block entities already use; the frustum includes the far plane, which is the distance cull).
- Native shader packs: the frustum is not used, because their shadow pass draws the same entity buffer and off-screen particles can cast into view. The test reads `NativeShaders::native`, set every frame in `shader_pack_inputs` to `package::is_pack(picked path)` (exactly `picks_native_pack`, which would otherwise redo an env lookup, path join and stat per frame). The flag follows the pick one frame late: `shader_pack_inputs` runs after the entity geometry in a frame, so the first frame after a new native pick still culls. (r3 review fix; `pack_ids.is_some()` is not equivalent: it is set only for `shaders/` packs, never for native ones.)

## Guarantees
- Simulation untouched: only `render` (a `&self` read) skips work. Same particle count, ticks, sounds.
- Visible output identical: skipped particles have no pixel in the view; kept ones are emitted in the original order, so translucent layering is the same.
- NaN positions fail open (drawn).

## Expected gain / risk
- Gain: small average CPU/GPU saving; helps heavy particle scenes (explosions, rain splash, campfires) when most are behind or beside the camera. Roughly proportional to the fraction off-screen (about half in a typical 70-90 degree FOV when particles surround the player).
- Risk: frustum lag (cull view vs actual draw view) would pop particles at the screen edge. The cull uses the same `camera_frustum(fov, yaw, pitch, bob*spin, far)` as block entities and a 1.5x+0.05 margin. Nearby mirror/portal/second views are not special-cased (none known for the main entity buffer). Cap 16384 and the soft taper are unchanged.
- Visual change: none intended.

## Files
`prepare.py`, `edits.json`, `particle-cull.patch`, `build-plan.json`, `standalone_tests.py` (copies `cull_reach`, `Frustum::intersects`, `frustum` verbatim onto a glam stand-in; 4 tests incl. 80k random rotated quads).
