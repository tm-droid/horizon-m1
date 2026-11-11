# dimension-warm (v2: v1 patch + main-thread trim)
Patch: dimension-warm.patch (one commit on top of the 28-patch daily4 stack; `git apply --check` passes on the stack, and after thread-cap).
v1's NOTES are kept in NOTES-v1.md; v1's patch dimension-cache.patch applies cleanly on the stack too (checked) and is superseded.
NOT compiled/run. It touches gfx.rs and gfx/pack_post.rs (v1's hunks, unchanged): re-check against the other agent's edits to those files.

## Findings
1. Metal caches persist ACROSS launches: `$(getconf DARWIN_USER_CACHE_DIR)/com.apple.metal/{16777235_322/functions.data (20 MB),32024/libraries.data (44 MB)}`
   is a system-wide on-disk cache keyed by shader source/pipeline. Evidence in bench logs (outputs/bench-2026-11-10/logs): MakeUp
   overworld pack build 5191 ms / 6105 ms in a-11 / a-12 (first run of a build with new shader text), then 360-665 ms in every later launch
   (a-13..a-18, a-10) of the same build. So the 2.5-3 s is a first-time-per-(build, dimension folder) cost, and not per process.
   Consequence: warm-up pays off once per fresh nightly/patch stack and after cache eviction (the cache is shared with all apps, ~64 MB total).
2. No app-side persistent cache is possible: wgpu 30 `PipelineCache` is Vulkan-only (repo uses `cache: None` everywhere); no
   MTLBinaryArchive binding in wgpu-hal metal. The system cache is the only one; nothing to add to the game dir.
3. v1 design is correct: warm builds the identical pipeline (same macros, same folder via `dimension_folder_named`, same target formats), so the
   real build hits the cache (observed return-to-overworld 372 ms). No dimension macro exists in the shader text (grepped), so no key mismatch.
   Pipelines don't depend on the mc_Entity/block/item tables (`pack_post::block_ids` takes any length and `min_binding_size` is None).
4. Does it fix the first-entry stall? Yes for the compile part (~2.1-2.7 s of the 3 s), once per build. Remaining ~0.35 s main-thread prep stays.

## What v2 changes (shader_packs.rs only)
Warm path skips `terrain_table` (105 ms logged), block/entity/item.properties parse and the `pack_ids` rebuild/restore dance, passing an empty
table. Mid-play hitch per warm drops from ~0.35 s toward ~0.2 s (Pack::open + read_properties + load_post stay). Real switches are untouched.

## Not done (needs gfx.rs / pack_post.rs, off limits now) - do these when those files are free
a. Lower the warm threads' QoS: in `load_shader_pack`'s `build` closure, `if warm { horizon_threads::far_terrain_current(); }` before
   `PackPost::new_with` (utility QoS; compile threads spawned from it inherit). Today the warm thread and its 2 compile threads inherit the render
   thread's class and compete with it for ~5-15 s, twice per session.
b. Memory: warm builds a full `PackPost` (colortex ping-pong, shadow targets) just to compile: ~150-450 MB transient on an 8 GB machine.
   Better: a `PackPost::build` flag that creates 1x1 targets / 16x16 shadow (pipelines depend on formats not sizes) so warm costs ~0 RAM.
   Until then leave `HORIZON_PACK_WARM=0` as the opt-out.
c. `Warm::pick` is asked on the main thread each time due(): it opens the zip (`Pack::open`) once per warm; fine.

## Risks
Transient memory (above), mid-play 0.2 s hitch x2 per session, extra compile CPU for ~10 s. Cancelled on any real dimension change
(CancelOnDrop), failures never turn the pack off.
