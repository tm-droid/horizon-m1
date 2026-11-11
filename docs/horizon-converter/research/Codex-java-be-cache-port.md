# Original cache-preserving block-entity occlusion trial (f42/r3)

2026-11-06. Prepared, **not compiled, enabled, selected, or benchmarked**.

## Porter relationship

The read-only v4 [porting index](../../../outputs/horizon-converter/2026-11-05-Tanush-f42-v4/porting-index.json) identifies EntityCulling as `entityculling`, task [mod-0121](../../../outputs/horizon-converter/2026-11-05-Tanush-f42-v4/tasks/mod-0121.json), with only coarse `native_key`/`native_tick` candidate hooks and assets-only/unverified carry. BlockEntityDistance is `blockentitydistance` / `mod-0011`; Sodium is `sodium` / `mod-0204`. None establishes a translated implementation.

This is original Rust code for the general technique of avoiding hidden block-entity drawing, implemented against Horizon's existing conservative occluder proof. No Java mod source was read or copied. It is not an EntityCulling behavior/config port and does not complete mod-0121's acceptance list. Neither the porter nor immutable v4 outputs were modified.

## Actual baseline path and safety evidence

The baseline is `outputs/horizon-runtime/m1-performance-r3/candidate-source` (f42-based). `game.rs:10652` obtains visible vanilla BEs from `visible_block_entities_in_frustum`; `game.rs:10720` submits the cache branch through `render_with_gpu_cache_options`. Its no-model-cache branch already calls ordinary vertex culling. Mod-generated BEs have a separate path.

`block_entity_render.rs:1492` warms `cache_candidates` independently of visibility, then publishes static section snapshots. A snapshot contains all cached model vertices in that section, including models not individually visible, so filtering a section by one representative block is unsafe. Section-local vertices are assembled at `block_entity_render.rs:1156`; the complete snapshot catalog is sorted at publication. `gfx.rs:7462` retains/uploads GPU buffers based on catalog and section revisions, independently of the visible draw-ID list.

`gfx/occlusion.rs:623` exposes the terrain visibility graph, but graph membership alone proves neither bounds containment nor a current opaque plane for arbitrary block-entity geometry. It can return false outside its searched volume (`Graph::contains`, around line 162). This trial does not use that graph as a BE visibility proof.

`game/entity_culling.rs:380` already gates synchronous culling on vanilla models (including active server packs), player presence, nonspectator camera, and camera outside an opaque block. Its `occluder_ready` requires full opaque blocks with an uploaded section and no dirty/meshing/pending section. `entity_culling.rs:82` proves a complete covered block plane, falling back visible when the lookup budget is exhausted. The trial reuses those conditions rather than adding a second occluder policy.

## Artifact and behavior

[Patch](../../../outputs/horizon-native/be-occlusion-cache-f42/be-occlusion-cache.patch), [sparse disposable candidate](../../../outputs/horizon-native/be-occlusion-cache-f42/candidate-source), [verification script](../../../outputs/horizon-native/be-occlusion-cache-f42/verify_preparation.py). Only these copies are edited. Baseline hashes are recorded alongside the patch.

Set `HORIZON_BE_OCCLUSION_CACHE=1` before launching a separately built trial. All other values leave the filter disabled. Each consuming module caches the env once; bounds scans are skipped when disabled. This initial trial additionally requires synchronous `entityCulling`, an active existing culler, no shader-pack span path (`pack_ids`), and `native_shadow() == false`. Async mode and shadows retain the original draw list.

- Compute a complete world-space min/max over actual cached vertices when the section snapshot is published. Include negative origins and cross-section overhangs; expand by the existing culler's 0.05 margin. Empty/nonfinite geometry has no proof and remains visible.
- Restrict proofs to bounds within 512 blocks of the camera on every axis, so the static shader's camera-relative f32 conversion stays comfortably inside that margin. Oversized geometry remains visible.
- After cache publication, remove a static section's draw ID only if its entire bounds pass the existing synchronous plane-coverage proof. Recompute `static_entities_drawn` to match the surviving IDs.
- Preserve warm candidates, catalog identity/revisions, snapshots, CPU geometry, GPU buffers/uploads, dynamic geometry, offscreen/long-range special renderers, gameplay, and ticking. A camera turn can only change the draw-ID list. No stale result cache is introduced.

The whole-section AABB can contain empty space and therefore lose opportunities to cull; that is conservative. This trial saves neither warm-cache CPU generation nor dynamic draw work. It shares the entity culler's finite lookup budget after ordinary entities; busy scenes may leave no budget for BEs. It adds bounds work on snapshot publication and section-query work when enabled. No speed benefit is established. The current nonvanilla resource-pack stack may make this trial a deliberate no-op.

## Checks and remaining acceptance

Passed, exit 0:

```sh
python3 outputs/horizon-native/be-occlusion-cache-f42/verify_preparation.py
```

This checks all three r3 source hashes, runs read-only `git apply --check` against r3, applies the patch only in a temporary sparse tree, compares it exactly with the prepared candidate, and confirms the cache warming/publication function is unchanged. It checks that two Rust pure tests are present; it does **not** execute Rust code.

Standalone read-only check, exit 0, working directory `outputs/horizon-runtime/m1-performance-r3/candidate-source`:

```sh
git apply --check ../../../horizon-native/be-occlusion-cache-f42/be-occlusion-cache.patch
```

An initial apply-check from the launcher data root failed because that root has no `crates/` paths; the correctly scoped check above passed. No baseline mutation occurred.

Prepared Rust tests: `static_occlusion_bounds_tests::includes_overhangs_and_negative_section_origins`, `static_occlusion_bounds_tests::invalid_or_empty_geometry_has_no_occlusion_proof`. Existing pure `entity_culling` wall/opening/budget tests remain relevant to the reused proof. After the active benchmark is finished, apply into a full disposable r3 copy and run formatting/type checks and focused crate tests there; none of those commands has been run in this unit.

Before selection: fresh review; compile; closed chest-wall fixture with a one-block aperture, partial peeking, camera turns, negative section boundaries, section-spanning banners/signs/shulkers, open animated chests, edited/dirty/meshing terrain, budget exhaustion, shader/native shadow bypass, resource/server-pack bypass, and long-range gateway/beacon checks. Compare enabled/disabled images and static section counters; confirm camera turns do not cause snapshot rebuild/upload spikes. Benchmark only after parity. No game, compiler, cargo/rustc/xcodebuild, device, or benchmark queue action was used here.

## Parent review/applicability decision
Fresh static review found no blocking correctness issue. Async worker-start failure can use the existing synchronous fallback, in which case filtering follows the synchronous path; ordinary async-worker operation is bypassed. Current MakeUp/v4 custom-pack profile is ineligible under the culler/model/shadow guards. This trial remains unselected research, with no device performance claim.
