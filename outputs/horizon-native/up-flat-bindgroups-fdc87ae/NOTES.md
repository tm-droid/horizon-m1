# up-flat-bindgroups (upstream 81a8d04a)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/gfx.rs (+`mod binding_cache;`), gfx/binding_cache.rs (new, with its unit test), gfx/flat.rs.

## What
Flat (GPU culling) flatten compute pass recreated its bind groups every frame. Now `Flat` caches phase-2 and per-segment groups keyed by (range first/count, identity of the 3-4 wgpu buffers); they are rebuilt only when a buffer is reallocated or ranges change. Cleared in `clear()` and when the frame cannot use flat draws.

## Expected effect (M1 8 GB)
Less per-frame CPU in the render thread (create_bind_group x ~5-10 per frame) and less Metal argument-buffer churn. Small but free. Relies on `wgpu::Buffer: PartialEq/Clone` (used upstream on the same wgpu).

## Conflicts resolved
Hand-ported flat.rs: daily7 has `Vec<(BindGroup,u32)>` instead of SmallVec and the `use` block differs, so upstream hunks 1/3/4/6/8 rejected; same logic applied manually (SmallVec import no longer needed, none left in flat.rs). Needs compile check for `Option::is_none_or` (Rust 1.82+) and borrow splits on `self.segments`/`self.groups`.
