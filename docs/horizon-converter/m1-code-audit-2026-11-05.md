# Horizon M1 code audit (2026-11-05)

Scope: read-only audit of the patched candidate source
`outputs/horizon-runtime/m1-performance/candidate-source/crates/` (f42 plus cloud-prep and shadow-scratch patches).
Target: M1 Air (4P+4E, 8 GiB, Metal through wgpu 30 + vendored `third_party/wgpu-hal`), 2560x1440, RD 12, 52 packs.
Paths below are relative to `crates/` unless they start with `third_party/`.

Nothing here was built or benchmarked. The gains are estimates from code structure and M1 TBDR and bandwidth behaviour. Each candidate lists the harness run that would confirm or reject it.

## Ranked candidates

| # | Candidate | Main effect | Est. gain | Effort |
|---|---|---|---|---|
| 1 | Emissive overlay lookup: linear scan of up to 128 pairs in **every terrain vertex** | Shader-off GPU | 0.5-2.5 ms GPU (full stack) | XS |
| 2 | macOS helper threads never lowered: `behind()` is a no-op on Apple | CPU wall time, 1% lows | 1% lows +5-15 %, render wall -0.3-1 ms | XS |
| 3 | Shader-pack gbuffer programs each open their own render pass (Load+Store of every target + depth) | Shader-on GPU | 1-4 ms GPU | M |
| 4 | Colortex clears run as separate clear-only passes before the first writer | Shader-on GPU | 0.2-1.5 ms GPU | M |
| 5 | Pack UBOs go through `queue.write_buffer` once per pass per frame | Shader-on CPU | 0.1-0.5 ms CPU | S |
| 6 | Shadow visibility: wasted pre-sort of `boxed` and a SipHash dedup set | CPU | 0.05-0.2 ms CPU | S |
| 7 | Emissive table rebuilt every frame through `BTreeMap<String,_>` lookups | CPU | 0.02-0.1 ms CPU | XS |
| 8 | Swapchain always has COPY_SRC|COPY_DST, so `framebufferOnly = false` on Metal | GPU bandwidth | 0.1-0.4 ms GPU (low confidence) | M |

---

### 1. Emissive lookup: per-vertex linear scan (shader-off terrain)

**Where:** `horizon-client-render/src/terrain.wgsl:393-404`. The table is filled at `gfx.rs:6467-6478`, capped by `native_emissive.rs:8` (`MAX = 128`), and holds OptiFine pairs up to `MAX - NATIVE = 96` (`native_emissive.rs:82`).

```wgsl
// The pairs are sorted by base layer: stop at the first past this one.
let sprite_layer = layer & 0x7fffu;
for (var i = 0u; i < min(globals.emissive_count.x, 128u); i++) {
    let pair = globals.emissive_layers[i];
    if pair.x == sprite_layer { out.emissive_layer = pair.y; break; }
    if pair.x > sprite_layer { break; }
}
```

**Evidence that it matters:** `terrain_vertex` runs for every terrain vertex of every section in the main pass (`terrain.wgsl:302-366` all call it). The 52-pack stack has 286 `_e.png`, so the table is full (128, the code logs "more than 96 emissive block overlays"). Every vertex whose sprite layer is above most base layers walks up to 128 dynamically indexed UBO entries. The base pack has 0 pairs, so the loop is empty. That matches the measured shader-off GPU doubling (3.79 -> 7.22 ms) better than texture size alone.

**Why it costs on M1:** RD 12 is a few million terrain vertices per frame. Up to 128 iterations of a dependent constant-buffer load plus compare per vertex is roughly 10^8-10^9 ALU and load operations. The M1's 8-core GPU sees that directly in vertex time. TBDR also runs the vertex stage for the whole frame before any fragment shading.

**Patch sketch (exactly equivalent):** `native_emissive::table` builds the table from a `BTreeMap<u32, _>` (`native_emissive.rs:120-128`), so it is sorted and unique by `pair.x`. A lower-bound binary search therefore returns the same first match as the linear scan.

```diff
-    for (var i = 0u; i < min(globals.emissive_count.x, 128u); i++) {
-        let pair = globals.emissive_layers[i];
-        if pair.x == sprite_layer { out.emissive_layer = pair.y; break; }
-        if pair.x > sprite_layer { break; }
-    }
+    let n = min(globals.emissive_count.x, 128u);
+    var lo = 0u;
+    var hi = n;
+    for (var s = 0u; s < 8u && lo < hi; s++) {   // ceil(log2(128)) + 1 bounded steps
+        let mid = (lo + hi) / 2u;
+        if globals.emissive_layers[mid].x < sprite_layer { lo = mid + 1u; } else { hi = mid; }
+    }
+    if lo < n && globals.emissive_layers[lo].x == sprite_layer {
+        out.emissive_layer = globals.emissive_layers[lo].y;
+    }
```

An optional cheap pre-check: `if n == 0u || sprite_layer < globals.emissive_layers[0].x || sprite_layer > globals.emissive_layers[n-1u].x` skips the search.

**Expected gain:** shader-off full stack 0.5-2.5 ms GPU, flight and static alike. Shader-on: none, because pack programs do their own terrain.

**Visual risk:** zero. The result is identical for sorted unique keys. Add a Rust test asserting `table()` output is strictly increasing in `[0]`, so the invariant stays guarded.

**Test:** `tools/horizon-offline-test.py --case packs --flight` and static, shader off, original/patched/patched/original. Compare GPU ms and do an exact image diff of the end captures. Diagnostic upper bound (not shippable, visual change): force `emissive_count = 0` and confirm how much of the 3.4 ms delta this loop explains.

**Effort:** XS (one WGSL function plus one unit test).

---

### 2. macOS: helper threads are never placed behind the render thread

**Where:** `horizon-threads/src/lib.rs:138-161`, with callers in `jobs.rs:220-222`, `lan/conn.rs:1277`, `lod.rs:1161/1247/1261` and `lod_net/server.rs:200`. The main thread is favoured at `horizon-client/src/game.rs:20761-20764`.

```rust
#[cfg(not(any(target_os = "linux", target_os = "android")))]
fn behind() -> bool {
    false
}
```

Only the render, server and remote-chunk threads get `QOS_CLASS_USER_INTERACTIVE` (`lib.rs:55-60`). The job pool (`worker_count()-1` = 7 threads, `jobs.rs:168`) calls `behind_server()`, which does nothing on macOS. The LAN `horizon-chunk-encode-*` warm pool (another 7 threads, `lan/chunks.rs:382-392`) does not call it at all. So 14+ helper threads plus the server, submit and render threads compete for 4 P-cores.

On Darwin a `pthread_create` thread without a QoS attribute inherits the creator's QoS. Workers spawned lazily from the already-favoured main thread therefore probably run at USER_INTERACTIVE too, which cancels the favour completely. This is likely but unverified; check it with the test below.

**Evidence:** the earlier diagnostic (`m1-deep-performance-2026-11-05.md:37`) measured shadow visibility at **0.6-1.2 ms wall but only 0.1-0.3 ms thread CPU**. A render thread that is runnable but not running is what preemption or E-core placement looks like.

**Why it costs on M1:** with 4 P-cores, an equal-priority mesher wave during flight takes P-cores from the render thread, or pushes it onto an E-core at about one third of the speed. The result is long frames, which show up as 1% lows (flight 42 FPS). Lower helper QoS also keeps the fanless Air cooler, which delays throttling.

**Patch sketch:**

```diff
-#[cfg(not(any(target_os = "linux", target_os = "android")))]
+#[cfg(target_vendor = "apple")]
+fn behind() -> bool {
+    // Below the user-interactive render/server threads; still allowed on P-cores when free.
+    // SAFETY: sets the calling thread's own QoS class; no pointers.
+    unsafe { libc::pthread_set_qos_class_self_np(libc::qos_class_t::QOS_CLASS_UTILITY, 0) == 0 }
+}
+#[cfg(not(any(target_os = "linux", target_os = "android", target_vendor = "apple")))]
 fn behind() -> bool {
     false
 }
```

Also add `horizon_threads::behind_server();` as the first line of the `horizon-chunk-encode-*` thread closure (`lan/chunks.rs:391`). For A/B, also try `QOS_CLASS_USER_INITIATED` with relative priority `-15`, which keeps helpers further from E-core-only placement.

**Expected gain:** 1% lows +5-15 % in flight, frame-time variance down, render-thread wall time down 0.3-1 ms in slow frames. Average FPS is roughly unchanged.

**Visual risk:** no per-frame image change. Terrain fill-in during flight may be slightly slower when the P-cores are saturated. Measure the harness's pending-terrain count and post-flight settle time; reject the patch if the settle time regresses by more than about 10 %.

**Test:** a unit test like `lib.rs:485` that spawns a pool worker and checks `pthread_get_qos_class_np` (first record the current class to prove or refute inheritance). Then run the flight scene with shaders off and with MakeUp, 4 interleaved runs, comparing 1% lows, p99 frame time, pending terrain and settle time.

**Effort:** XS.

---

### 3. Shader-pack gbuffers: one render pass per program (TBDR load/store churn)

**Where:** `gfx/pack_post.rs:2832-2878` (`begin`), `draw_opaque` at `3182-3197`, `draw_entities` at `3018-3032` (one pass per entity program), `draw_terrain` at `2899-2901`, and similar in `draw_lines`, `draw_clouds`, `draw_hand`, `draw_translucent` and `draw_weather`.

```rust
let load = wgpu::Operations { load: wgpu::LoadOp::Load, store: wgpu::StoreOp::Store };
...
depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
    view: shadow.map_or(&targets.depth, |s| &s.depth.1),
    depth_ops: Some(depth_ops),   // pack_shadow::load(): Load + Store
```

```rust
self.draw_sky(..);  self.draw_terrain(.., Solid, ..);  self.draw_entities(.., false);
self.draw_lines(..); self.draw_clouds(..);
```

Each `draw_*` (and each entity program) calls `begin()`. That opens a new render pass which loads and stores every written colortex plus the 2560x1440 depth. `draw_sky` already merges its two programs when `p.writes == pass.writes` (`pack_post.rs:2970-2976`), so the codebase accepts the idea; it just is not applied across programs.

**Why it costs on M1:** on Apple TBDR each pass boundary flushes tiles to memory and reloads them. At 1440p with 2-4 RGBA8/RGBA16F targets plus D32, that is about 30-90 MB per boundary (load and store). A typical frame has 4-10 boundaries (sky, terrain, 2-6 entity programs, lines, clouds, hand), so several hundred MB of avoidable traffic on a 68 GB/s shared bus that the CPU also uses.

**Patch sketch:** generalise the sky's `same` rule into a small "open pass" holder on `PackPost`.

```diff
+struct OpenPass<'e> { rp: wgpu::RenderPass<'e>, writes: Vec<(u32, usize)>, shadow: bool }
 fn draw_entities(&mut self, .., open: &mut Option<OpenPass<'_>>) {
     let group = self.bind(device, queue, encoder, pass, size);
-    let mut rp = self.begin(encoder, pass);
+    // bind() records copies/clears on the encoder: only reuse when it recorded none.
+    let reusable = pass.copies == 0 && pass.image_copies == 0 && !has_stand_ins(pass);
+    if !(reusable && open.as_ref().is_some_and(|o| o.writes == pass.writes && o.shadow == pass.group.shadow())) {
+        drop(open.take());
+        *open = Some(OpenPass { rp: self.begin(encoder, pass).forget_lifetime(), writes: pass.writes.clone(), .. });
+    }
+    let rp = &mut open.as_mut().unwrap().rp;
```

Close the open pass (`open.take()`) before any encoder op: the `depth2`/`depth1` copies in `draw_opaque`, `mipmap`, compute dispatch, and any `bind()` that records copies. Because `bind()` must run before the pass opens, call it per program only after closing a non-matching pass. Never pre-bind ahead of earlier draws, so snapshot copies keep their order.

**Expected gain:** MakeUp and Complementary 1-4 ms GPU (more with more entity programs on screen). Shader-off: none.

**Visual risk:** zero when the predicate holds: same attachments and depth, no encoder op in between, same draw order. A program cannot sample a texture it also writes (wgpu would already reject that), so equal `writes` sets cannot create a new hazard. A validation error, not a silent change, is the failure mode.

**Test:** MakeUp and Complementary static and flight, exact image diff at the fixed end pose, GPU ms from `pack_timing`. Also log the pass count per frame before and after.

**Effort:** M (lifetimes and one shared "open pass" through 6-8 `draw_*` functions).

---

### 4. Colortex clears as separate clear-only passes

**Where:** `gfx/pack_post.rs` around `4026-4090` (`clear_op`, `other_clears`, `by_size`, then a `begin_render_pass` per size group), before the blit, shadow and gbuffer passes.

```rust
// Overwritten whole: clearing lets a tiled GPU skip loading the old content.
let overwrite = wgpu::Operations { load: wgpu::LoadOp::Clear(..), store: wgpu::StoreOp::Store };
...
for &b in &self.other_clears { ... by_size ... }
for (_, chunk) in &by_size { ... encoder.begin_render_pass(...) // clear-only pass
```

The cleared buffer is stored to memory, and the first gbuffer pass that writes it `Load`s it back (`begin()` always uses `LoadOp::Load`).

**Why it costs on M1:** one full write plus one full read per cleared colortex per frame. Apple lossless compression makes uniformly cleared tiles cheap, but the clear pass still flushes, and the first writer still pays the load setup.

**Patch sketch:** track `pending_clear: u16` (a bitmask of buffers) instead of encoding the clear pass. In `begin()` and the composite attachment builder, use `clear_op(b)` instead of `load` for a buffer in `pending_clear`, then clear its bit. Before any pass that *samples* `b` while its bit is set, or at the end of `run()`, flush the remaining bits with today's clear pass.

```diff
-        attachments[l] = ... attach(&t[side], load)
+        let ops = if self.pending_clear & 1 << buffer != 0 { self.pending_clear &= !(1 << buffer); clear_op(buffer) } else { load };
+        attachments[l] = ... attach(&t[side], ops)
```

Clear-then-Load is semantically identical to `LoadOp::Clear`, and the clear covers the whole attachment regardless of viewport.

**Expected gain:** 0.2-1.5 ms GPU with shader packs (depends on how many buffers the pack clears; MakeUp and Complementary clear several).

**Visual risk:** zero when the flush-before-sample rule is implemented; the risk is a missed sampler path. Guard it with a debug assertion that no bound texture has a pending clear.

**Test:** exact image diff for MakeUp, Miniature and Complementary (static) plus GPU ms. Include a pack whose composite reads a buffer no gbuffer writes, so the flush path is exercised.

**Effort:** M.

---

### 5. Pack UBOs: `queue.write_buffer` per pass per frame

**Where:** `gfx/pack_post.rs:2620-2622` inside `bind()`, which runs for every program each frame (11 call sites: `2814, 2899, 2960, 3030, 3078, 3243, 3286, 3323, 3415, 3795, 4198`).

```rust
if !pass.block.is_empty() {
    queue.write_buffer(&pass.ubo, 0, &pass.block);
}
```

The project's own note in `gfx/upload.rs:1-5` says `Queue::write_buffer` "create[s] a fresh staging buffer for every call (on Metal a kernel call each)". It built `Uploads` (a `StagingBelt`) for that reason. Pack passes did not get it. This differs from the demoted "skip identical UBO copies" idea: here the number of writes stays the same and only the per-call staging allocation goes away.

**Why it costs on M1:** 20-40 programs (Complementary) means 20-40 `newBufferWithLength` + track + free per frame on the render thread, plus pending-writes bookkeeping. That hurts CPU 1% lows.

**Patch sketch:** pass `&mut upload::Uploads` (the renderer's `self.uploads`, `gfx.rs:987`) into `PackPost::run`. In `bind()`:

```diff
-            queue.write_buffer(&pass.ubo, 0, &pass.block);
+            uploads.buffer(encoder, &pass.ubo, 0, &pass.block);
```

`bind()` is always called before `begin_render_pass`, so the copy lands outside any pass. Make sure `uploads.finish(&encoder)` runs after `PackPost::run` for the same encoder.

**Ordering caveat (must check first):** queue writes all land before the submission, so a pass bound twice in one frame with different contents currently sees the *last* block in both uses. Encoder copies give each use its own block. Before switching, add a debug counter asserting each `Pass` is bound at most once per frame, or keep `queue.write_buffer` for passes that bind more than once (shadow cascades, per-layer terrain). If that holds, output is identical.

**Expected gain:** 0.1-0.5 ms CPU per frame with shader packs; slightly better 1% lows.

**Visual risk:** zero under the bind-once predicate.

**Test:** Complementary static and flight CPU ms, p99; exact image diff.

**Effort:** S.

---

### 6. Shadow visibility: redundant sort and SipHash dedup

**Where:** `gfx.rs:6700-6719`, `gfx/resident.rs:392`, and `gfx.rs:1049` (`shadow_seen: std::collections::HashSet<SectionKey>`).

```rust
self.sections.visible(camera, radius, &light, |_| true, |_, _| false, boxed);   // sorts boxed by distance
seen.extend(shadow_visible.iter().map(|s| s.key));
shadow_visible.extend(boxed.drain(..).filter(|s| !seen.contains(&s.key)));
shadow_visible.sort_unstable_by(|a, b| { ... height(b).total_cmp(&height(a)) });   // full resort
```

`Resident::visible` ends with `out.sort_unstable_by_key(|v| (v.distance, v.key))`, and the shadow path then discards that order with a full resort by light height. The dedup builds a SipHash set of every near section each frame. The near pass uses the all-accepting frustum and `|_| true`, so "already in `shadow_visible`" is exactly `in_view_distance(camera_column(camera), near, key.0, key.2)`. That is a pure integer test.

**Patch sketch:** add `sorted: bool` to `visible()` (or a `visible_unsorted` wrapper) and pass `false` for both shadow calls. Replace `seen` with the column distance predicate, deleting `shadow_seen`. Make the final sort total so the order no longer depends on input order: `(height desc, distance, key)`.

**Expected gain:** 0.05-0.2 ms render-thread CPU with shadows on.

**Visual risk:** opaque shadow depth is identical. Only sections with *exactly* equal light height could reorder, and only translucent shadowcolor blending could notice. Today's order for such ties is already unspecified (`sort_unstable_by`). To keep bit-identical output, keep the pre-sort and only swap the dedup set.

**Test:** extend the shadow-scratch Rust test (exact sequence equality across camera moves) with the new predicate; MakeUp static CPU span "shadow visibility".

**Effort:** S.

---

### 7. Emissive table rebuilt every frame

**Where:** `horizon-client/src/game.rs:15102-15111` -> `horizon-client-render/src/native_emissive.rs:115-145`.

```rust
let emissive_layers = if self.title.is_none() {
    let mut requests = Vec::new();
    self.native_emissive(&mut requests);
    horizon_client::native_emissive::table(&self.pack.render.sprite_layers, requests, &self.pack.render.emissive)
```

`mappings()` does up to 2x96 `BTreeMap<String,u32>::get` string lookups (log N over thousands of sprite names) and builds 2 BTreeMaps every frame. Yet the OptiFine half (`pack.render.emissive`) only changes on resource reload.

**Patch sketch:** cache `mappings(layers, optifine)` in `pack.render` at reload (`Vec<[u32;4]>`). `table()` then merges the cached sorted vector with the (usually empty) native list. When the native list is empty, return the cached vector directly.

**Expected gain:** 0.02-0.1 ms CPU per frame. Small, but trivial and exact.

**Visual risk:** zero (same table).

**Test:** a unit test comparing the cached and uncached `table()` for the full-stack pack list.

**Effort:** XS.

---

### 8. Swapchain usages force `framebufferOnly = false` (low confidence)

**Where:** `gfx.rs:2113-2121` and `third_party/wgpu-hal/src/metal/surface.rs:263,281`.

```rust
if caps.usages.contains(wgpu::TextureUsages::COPY_SRC) { config.usage |= wgpu::TextureUsages::COPY_SRC; }
if caps.usages.contains(wgpu::TextureUsages::COPY_DST) { config.usage |= wgpu::TextureUsages::COPY_DST; }
```

```rust
let framebuffer_only = config.usage == wgt::TextureUses::COLOR_TARGET;
render_layer.setFramebufferOnly(framebuffer_only);
```

Apple recommends `framebufferOnly = YES` so the drawable can use display-optimised (compressed) layout. COPY_SRC is used only by screenshots and frame generation; COPY_DST only by frame generation's present thread.

**Patch sketch:** configure the surface with RENDER_ATTACHMENT only while frame generation is off. Take screenshots from the last offscreen or final pack target instead of the swapchain, or reconfigure with COPY_SRC for the one screenshot frame.

**Expected gain:** 0.1-0.4 ms GPU at 1440p. Unmeasured; Apple does not publish how much this changes on M1.

**Visual risk:** zero for frames. Screenshot path behaviour must be re-verified.

**Test:** shader-off static GPU ms A/B; F2 screenshot equality.

**Effort:** M (touches the screenshot and frame-gen paths). Do it last.

---

## Refuted or deprioritised leads

| Lead | Verdict | Evidence |
|---|---|---|
| `gfx.rs:7094` per-frame `Vec::new()` for `shadow_translucent` | Refuted (negligible) | One allocation per frame, consumed by value at `gfx.rs:7163`. Amortised it costs microseconds. It could join the scratch patch, but the gain is under 0.01 ms. |
| Metal pipeline cache / ~105-116 pipeline+module sites | Refuted for frame time | `third_party/wgpu-hal/src/metal/device.rs:1908-1914`: `create_pipeline_cache` returns a unit `PipelineCache`, so a wgpu `PipelineCache` does nothing on Metal. The OS Metal shader cache already caches `newLibraryWithSource` (`device.rs:1307`) across launches. Pack pipelines are built synchronously at `gfx.rs:5683` (a hitch on pack load and switch only). An async build or `MTLBinaryArchive` is a large change with no steady-state FPS gain. |
| Worker *count* (`lib.rs:25`, `jobs.rs:168`, `lan/chunks.rs:382`) | Partly refuted, replaced by #2 | Pools already take all-but-one, and the harness already has `--workers`. The real defect is priority: `behind()` is a no-op on Apple and the encode pool never calls it. |
| `gfx/upload.rs:222` `write_texture` | Refuted | That line is inside a `#[test]`. Runtime sprite, section, cloud and HUD uploads already go through `Uploads` (`StagingBelt`, `gfx.rs:987/991`, `6019`, `6078`). |
| `native_render.rs:236`, `pack_post.rs:747`, `block_light.rs:96` | Refuted | Creation-time stand-in textures and the noise texture. `block_light::update` rebuilds only when the camera crosses a grid step or the revision changes. |
| `resident.rs:323` `visible()` cost at RD 12 | Mostly refuted | Already column-hierarchical (a column box test, then per-section only when partially inside) with Fx sets for `lod_cutout` and `leaving`. Only the shadow-path waste in #6 remains. |
| Skip native clouds for MakeUp's own clouds (`gfx.rs:7339-7345`) | Refuted (already covered) | MakeUp 9.6 `shaders.properties` has `#if V_CLOUDS > 0` / `clouds = off`, which the existing cloud-prep patch already honours. Skipping clouds for packs that keep a `gbuffers_clouds` program would change visuals. |
| `compositor.rs:86-109` present mode and frame latency | Refuted | That file is the splitscreen compositor only. The main surface (`gfx.rs:2122-2131`) prefers Mailbox, but Metal offers only Fifo/Immediate (`metal/adapter.rs:464`), so VSync off = `displaySyncEnabled=false`. `maximumDrawableCount = latency + 1 = 3` (`metal/surface.rs:333`). The 11-17 ms acquire waits are GPU back-pressure, not a config bug. |
| `MemoryHints::MemoryUsage` (`gfx.rs:1875`) | Refuted on Metal | `metal/adapter.rs:72` takes `_memory_hints` and ignores it. Metal allocates per resource. |
| Raise the emissive cap (96/128) for 286 `_e.png` | Correctness, not performance | With the linear scan, raising the cap would *add* GPU cost. After #1 (log-time), raising it becomes nearly free. Treat it as a separate correctness change (UBO size grows by 16 B per pair). |
| Composite passes at lower resolution | Rejected | Changes visuals. Packs control scale via `size.buffer`. |
| Composite `LoadOp::Load` to `Clear` | Rejected for now | Composite passes write the alternate ping-pong side with `Load` (`pack_post.rs:4205-4211`). Packs that `discard`, blend, or shrink `gl_Position` (bloom tiles) rely on preserved content, and no safe static predicate exists. |
| Per-frame bind group creation | Refuted | Pack bind groups are cached per key (`pack_post.rs:2634`, `pass.groups.entry(key).or_insert_with`). Page groups are cached in `page_groups`. |
| Pass `copies` (`copy_texture_to_texture` in `bind`) | Refuted | Only for read-and-image-write or `*Before` images (`pack_post.rs:1610,1735`); required by semantics. |
| Hot `HashMap` with SipHash | Mostly refuted | Renderer hot sets use `fast_hash::Fx*`. The exception is `shadow_seen` (#6). |
| Depth prepass, translucent overdraw sort, mip/aniso defaults | Not audited in depth | A depth prepass adds a geometry pass, which is a poor trade on TBDR with hidden-surface removal. No zero-visual change identified. |

## Suggested order

Do #1 and #2 first: both are XS and measurable in one interleaved harness session (shader-off flight for #1, MakeUp flight 1% lows for #2). Then do #5 and #7, which are small and exact. #3 and #4 are the real shader-on GPU levers but need careful pass plumbing and exact-image verification.
