# up-frustum-regions (upstream 2a33c013)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/gfx.rs, gfx/resident.rs, streaming.rs; client/src/game.rs.

## What
- Frustum::intersects/contains: branchless box corner pick (`cmpge` + `Vec3::select`) instead of three if/else per plane. Runs per resident column and per section, every frame (also per shadow cascade).
- resident.rs column cull: builds the column box from f32 camera-relative offsets directly instead of `origin(...)` DVec3 -> as_vec3 for low/high corners.
- streaming.rs: `Job::Mesh` carries `Arc<Region>` and `Streaming::region` returns `Arc<Region>` (no Box moves of the 3x3 region snapshot through job queue/requeue; `borrow(&region)` deref-coerces).
- game.rs upload priority: pending-upload sort key now includes vertical distance `(k.1 - cam_y)^2` (3D distance, camera section from player y; 4 if no player), so sections above/below the camera no longer upload as late as far columns.

## Expected effect (M1 8 GB)
Small CPU win on the render thread (cull cost scales with sections x planes), slightly less alloc/copy per mesh job, better first-seen order when flying/digging. No visual change except upload order.

## Conflicts resolved
- gfx.rs hunk 1 (HashSet -> FxHashSet in shadow `seen`) DROPPED: daily7's shadow-scratch already replaced that code with the reused `shadow_seen` scratch set.
- game.rs `far` closure hand-ported: same line lives ~1.9k lines earlier in daily7 (patch had failed to apply at upstream offset). Other hunks apply clean.
- Risk: type-level only (Box -> Arc) and `self.player`/`position.y` use in game.rs (verified field exists: `player: Option<PlayerMotion>`, `position.y` f64).
