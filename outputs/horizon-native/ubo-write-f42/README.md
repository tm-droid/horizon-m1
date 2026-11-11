# ubo-write-f42 (audit #5) - SKIPPED, no transform

Not low risk, so nothing is applied.
- The audit's fix (route `bind()`'s `queue.write_buffer` through `Uploads`/StagingBelt) needs `&mut Uploads` plumbed into
  `PackPost::run` and 11 `bind()` call sites, `uploads.finish()` ordering, and the bind-once-per-frame predicate
  (a pass bound twice with different blocks gets last-write-wins today but per-use blocks with encoder copies: a visible change).
- The cheap alternative (skip the write when `pass.block` equals the last written bytes) is unsafe as sketched:
  `Pass` is `#[derive(Clone)]` and clones share the same `ubo` buffer, so a per-`Pass` "last written" cache can go stale
  and skip a needed write. It would also rarely fire: camera/time members change every frame.
Do it with a compiler: one `bind_count` debug counter first, then the Uploads route for passes bound exactly once.
