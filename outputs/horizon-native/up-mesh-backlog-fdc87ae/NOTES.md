# up-mesh-backlog (upstream 562175df)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/streaming.rs; client/src/game.rs.

## What
`Streaming::upload_backlog` (meshes finished but not yet uploaded = `pending_uploads.len()`, set by the game before `streaming.update`) is subtracted from the meshing room: `room = workers*32 - (meshing + upload_backlog)`. When uploads lag (low FPS at wide distance) meshing stops instead of piling gigabytes of meshes into RAM until the system swaps.

## Expected effect (M1 8 GB)
Directly targets memory growth / swap stutter during fast flight or low-FPS shader-pack sessions (see docs/research/memory-stutter-2026-11-10.md). Slightly slower chunk fill when uploads are the bottleneck (by design).

## Conflicts resolved
- Upstream also moved `nearest_first` + its unit test into new `streaming/bounded.rs` (pure refactor): SKIPPED here (smaller diff, no behaviour change).
- Upstream added integration test `meshes_waiting_for_upload_hold_back_new_mesh_jobs` in client/tests/streaming_meshes.rs; fdc87ae's test file lacks the helpers it needs: SKIPPED. Call site is game.rs (upstream's `game/world_update.rs` does not exist at fdc87ae).
