# Horizon memory audit (2026-11-05)

Scope: read-only. No cargo, no game launch. Source: `outputs/horizon-runtime/m1-performance/candidate-source/crates/`
(paths below are relative to it). Overlap avoided: `outputs/horizon-native/sprite-compress-f42` (block-sprite CPU
copy, `RenderAssets.pixels`) and `docs/horizon-converter/m1-code-audit-2026-11-05.md` (perf only, no memory items).
Estimates marked (est) are from code and counters, not measured. Nothing here was built or run.

## 1. Measured RSS / swap (72 `tests/*/result.json`)

Source fields: `system_before|after.process.output` (`ps` RSS in KiB, then %CPU), `.swap.output` (`vm.swapusage`),
`.vm_stat.output`. Medians (min-max), MB, over runs that have the field:

| group | runs | RSS before | RSS after | swap used before | swap used after | avg FPS med | 1% low med |
|---|---|---|---|---|---|---|---|
| base (default resources) | 38 | 160 (107-823) | 161 (95-802) | 4035 (2532-5982) | 3992 (2622-5459) | 60 | 40 |
| 52-pack (`f42-m1-packs-*`) | 13 | 237 (160-370) | 219 (168-280) | 2762 (2563-4471) | 2686 (2558-4577) | 127 | 49 |
| MakeUp (`f42-m1-makeup-*`) | 16 | 243 (177-280) | 237 (174-269) | 3746 (2771-5177) | 3715 (2720-5225) | 39 | 22 |
| other shader packs | 5 | 260 (190-270) | 251 (201-253) | 4139 (3601-6060) | 4123 (3601-6114) | 11 | 8 |

Reading it:
- Swap is 2.5-6 GB in every group (swap file is 4.6 GB total, `4608M`), yet the Horizon process RSS is only
  0.1-0.4 GB. `ps` RSS cannot be the game's cost: `docs/claude-history.md:103` already found `ps rss`
  undercounts about 7x (compressed or swapped pages). Horizon is mostly paged out/compressed, or its memory is GPU
  memory that RSS never counts (Metal buffers/textures on M1 are system RAM, wired).
- One full `vm_stat` (`base-auto-full-noafk-r1`, before): free 4112 pages (64 MiB at 16 KiB pages), wired 136615
  (2.1 GiB), anonymous 121603 (1.9 GiB), stored in compressor 332087 (5.1 GiB). The machine runs with ~0 free RAM.
  The `background_processes` list in the same file shows Codex Renderer 432 MB, codex 125 MB, WindowServer, plus the
  user-approved Xcode/DeviceHub load. Most swap is therefore other processes, not Horizon.
- MakeUp swap median is ~1.0 GB above the pack-only median (3746 vs 2762) at a third of the FPS. Confounded by
  run order and background load, but the direction matches the shader-pack render targets (candidate 4).
- GPU-side counters in `result.json` (`renderer.*`), base run: arena 268431360 B (256 MiB), `section_vertex_bytes`
  211-229 MB with 4171-4342 resident sections (52.8 KB per section), `uploaded_bytes` 530-723 MB cumulative (churn,
  not residency). Display 2880x1800 at scale 2.0, `resolutionScale:100`, `improvedTransparency:false`, `hdr:false`,
  LOD all zero, sounds decoded 2-3 MiB, `pending_uploads` 0.
- Sprite array (console.log): base `1291 layers at 64 px`, packs/MakeUp `2303 layers at 64 px`, budget 256 MiB.

**Measurement gap to fix first (zero code):** the harness should record `footprint -p <pid>` (`phys_footprint`,
what the OS charges) before and after, as `src/.../resource_memory.rs` and the `claude-history.md` notes do. Without
it none of the savings below can be confirmed, and the swap number mixes in every other app.

## 2. Already handled in the source (do not re-patch)

- mimalloc `purge_delay` is already 0 at startup: `crates/horizon-threads/src/lib.rs:252-265`
  (`configure_allocator`, `PURGE_DELAY = 15`). Allocator is `capped.rs` over mimalloc v3; `purge_decommits` default 1
  (`third_party/libmimalloc-sys/c_src/mimalloc/v3/src/options.c:127`). No useful `MIMALLOC_*` env left (see section 4).
- wgpu device already uses `MemoryHints::MemoryUsage` (`gfx.rs:1875`).
- Mesh pool capped at 16 MiB / 128 meshes (`streaming.rs:356-357`). Sound cache is LRU-capped at 64 MiB
  (`audio.rs:147`) and measured at 2-3 MiB. Staging belt chunk 1 MiB (`gfx/upload.rs:8`). Far-chunk body cache
  and shared frame cache are byte-capped (`lan/far.rs`, `lan/conn.rs:1478-1530`).
- Chunks are `Vec<Arc<Section>>` with paletted containers and uniform-section sharing (`chunk.rs:421-570`).
- GUI/HUD textures use `mip_level_count: 1` (`gfx.rs:2702-2870`). Pack-sized texture budget 256 MiB is not hit
  (2303 x 64 x 64 x 4 = 37.7 MB top level).
- No `stack_size(...)` call exists in `crates/`; threads use Rust's 2 MiB default (virtual, ~0 resident).
- Arena grows only on the newest page, compacts and shrinks (`gfx/arena.rs:102-105, 520-523`).

## 3. Ranked candidates

### 1. Lossless-pack terrain vertices 24 B to 16 B (largest steady item)
- Where: `mesher.rs:66-78` (`TerrainVertex`: `pos [f32;3]`, `uv [u16;2]`, `layer u16`, `light u16`, `color u32` = 24 B),
  `TerrainVertex::new` `mesher.rs:94`, strides `gfx.rs:1973, 2269`, `gfx/arena.rs:874, 1041`, `gfx/gpu_culling.rs:1257`,
  `terrain.wgsl` and the OIT/pack vertex fetch.
- Evidence: `section_vertex_bytes` 211-229 MB resident at render distance 12 (all in unified RAM).
- Estimated saving: ~70-76 MB (1/3 of 211-229 MB) plus the same in `uploaded_bytes` traffic.
- Sketch: `pos` is section-relative (0..16 plus overhang). Store `[u16;3]` fixed point at 1/256 block and decode in
  the vertex shader (`pos = vec3(u16) / 256`). Only zero-visual if every emitted position is a multiple of 1/256
  (model elements are on 1/16 grids, but rotated/scaled and entity-like block models can break it). First step is a
  debug assert in `TerrainVertex::new` that counts positions not exactly representable across a test world.
- Risk: high. Touches mesher, arena `stride`, culling compute, LOD (`gfx/lod.rs`), pack geometry export
  (`pack_*` shaders read the vertex layout). Only attempt if the assert shows 0 unrepresentable vertices.

### 2. Animated-sprite frames: kept at layout size on the CPU, plus GPU chain buffer at layout size
- Where: `sprites.rs:262-271` (`resized`, `animation.frames = resized[..]` uses `resample(f, from, size)`),
  `sprites.rs:9` (`SpriteAnimation.frames: Arc<Vec<Vec<u8>>>`), `assets.rs:309` (moved into `RenderAssets.animations`),
  `gfx/animate.rs:93-135` (`source_chains` builds every frame with every mip into storage buffers).
- Evidence: every layer is laid out at the largest texture size (64 px here, `console.log`), so a 16x16 animated
  texture costs 16x its native size on CPU and GPU. The CPU copy only matters for a rebuilt renderer, like `pixels`.
- Estimated saving (est): CPU 15-40 MB (vanilla ~40 animated layers x ~20 frames x 16 KiB = ~13 MB, more with packs and
  Fresh Animations); GPU chain buffer is ~1.33x that with mips. Not measured: count animated layers and frames with a
  one-off log line in `lay_out` first.
- Sketch: (a) CPU: lz4 `animations[].frames` after the first renderer build, same pattern as `sprite-compress-f42`
  (extend `SpriteAnimation::pixels` to decompress on demand). Byte-identical, so zero visual change. (b) GPU (harder):
  store chains at native size and upsample in the compute path.
- Risk: low for (a), medium-high for (b).

### 3. LabPBR normal/specular CPU copies kept after upload
- Where: `assets.rs:103-104` (`pbr_normals`, `pbr_specular`, built in `sprites.rs:283-296`), consumed by
  `PreparedTextures.with_pbr` at `horizon-client/src/game.rs:19833-19835`, uploaded as GPU array textures
  `gfx.rs:2616-2660`.
- Evidence: separate Vec per map at `pbr_size`^2 x layers x 4 B; GPU already holds both arrays.
- Estimated saving (est): 0 when no loaded pack ships `_n/_s` (base). When a pack does, up to 2 x 37.7 MB = 75 MB at
  2303 layers x 64 px, less if `pbr_size` is smaller (`side_within(.., MAX_MAP_BYTES)`). I did not confirm which of the
  52 packs ship LabPBR maps; check `pbr_size` in the log line `LabPBR maps at N px`.
- Sketch: add the same `SpritePixels`-style lz4 holder (or an `Option<Vec<u8>>` taken after the first successful
  `build_renderer`) as the sprite-compress patch. Byte-identical on rebuild.
- Risk: low.

### 4. Shader-pack full-screen targets: A/B pair per colortex at 2880x1800
- Where: `gfx/pack_post.rs:3562-3640` (`resize`: `let sides = [0, 1].map(|_| texture_sized(..))` for every used
  buffer; plus mip chains `full_chain`, `depth`, `depth1`, `depth2`, `scratch` at `pack_post.rs:408-427`).
- Evidence: MakeUp runs show ~1 GB more swap than pack-only runs. One RGBA16F target at 2880x1800 is 41.5 MB, RGBA8 is
  20.7 MB, Depth32F 20.7 MB; every used colortex costs two.
- Estimated saving (est): 40-160 MB, depends on how many buffers MakeUp uses and which are never read and written in
  the same program chain (those need no B side). Needs a per-buffer log of `used`, `mipped`, `copied` and formats
  from `resize` before choosing.
- Sketch: allocate the B side lazily only for buffers whose pass graph flips (a pass samples the buffer it writes,
  the existing `scratch` and `copied` bookkeeping). Free `depth2`/`depth1` when no program reads them.
- Risk: medium-high (pass correctness, shader packs are visual).

### 5. OIT targets never released once created (inactive in the tested config)
- Where: `gfx/oit.rs:593` creates 2x Rgba32Float (`BOUNDS_FORMAT`, `oit.rs:18`), 3x Rgba16Float (`COEFFICIENT_FORMAT`)
  and optional 2 Depth32Float; there is no `targets = None` path (compare `entity_outline.rs:195`, which frees).
- Evidence: at 2880x1800 that is about 166 + 124 + up to 41 = 290-330 MB. All tested runs have
  `improvedTransparency:false`, so this costs nothing in the benches, and it only bites a user who toggles it on.
- Estimated saving: 0 in benches; ~300 MB for a user who turned it on then off.
- Sketch: in `Renderer` where `oit_on` is computed (`gfx.rs:7291`), call a new `Oit::release_targets()` after N frames
  with `oit_on == false`.
- Risk: low.

### 6. Sprite lay-out transients (peak, not steady)
- Where: `sprites.rs:262-271` resamples every layer into `resized` (all layers, not only animated), and
  `sprites.rs:93, 668` keeps a `still` map keyed by a clone of each still frame (`frames[0].clone()`, `sprites.rs:650`),
  alive until `Sprites` is dropped after `RenderAssets` is built (`assets.rs:296-320`).
- Evidence: code only. At 2303 layers x 64 px that is another ~38 MB for `still` keys plus ~38 MB for `resized`, at the
  startup peak, while the 8 GB machine is already swapping.
- Estimated saving (est): 0 steady, up to ~75 MB lower startup peak (less compressor/swap churn at load).
- Sketch: call `self.still = Default::default()` and drop `self.native` at the end of `lay_out`. Key `still` by a
  hash of the pixels instead of the pixels.
- Risk: low (hash collision handling needed for the second part).

### 7. Per-size sprite arrays (all layers upscaled to the largest texture)
- Where: `sprites.rs:241-262` (`lay_out`), `gfx.rs:2648-2680` (one `Rgba8Unorm` array per `split`, full mip chain).
- Evidence: base has 1291 layers at 64 px (`largest 64 px`). If most layers are 16 px natively, 1291 x 16 KiB =
  21 MB (+7 MB mips) is mostly replicated pixels.
- Estimated saving (est): up to ~25 MB base, ~45 MB with packs, and only if a small fraction of layers are really 64 px.
  Not measured: log the count of layers per native size.
- Sketch: group layers into arrays by native size using the existing `SPRITE_ARRAYS` split. Nearest-integer upscale was
  chosen so it is lossless, but texture filtering at layer edges and mip levels must still match.
- Risk: high (shader indexing across `terrain.wgsl`, OIT, pack atlas copy in `pack_atlas.rs`).

### 8. Arena headroom
- Where: `gfx/arena.rs:14` (`PAGE_BYTES = 256 MiB`), doubling growth at `arena.rs:520-523`.
- Evidence: `arena_bytes` 268431360 vs 211-229 MB used, so 40-57 MB of headroom. On Metal untouched shared-buffer
  pages are normally not resident, so the real saving is probably near 0. Listed only to close the question.
- Estimated saving: 0-50 MB. Risk: medium (reuse and compaction logic). Not recommended.

## 4. Zero-code knobs to put in the overrides matrix

Existing knobs found in source, with the memory effect to expect:
- `HORIZON_WORKER_THREADS=N` (`horizon-threads/src/lib.rs:25-33`): caps every pool (streaming takes all but one,
  decoration a third). On the 8-core M1 default is 8 (4 P + 4 E). Try 6 and 4. Fewer concurrent meshing jobs means less
  scratch and mesh buffers in flight, but slower chunk streaming. Measure footprint and 1% lows; not zero-cost.
- `HORIZON_MEMORY_LIMIT_MB` / `HORIZON_MEMORY_HARD_MB` (`docs/native-client.md:246-272`): on macOS the game drops far
  terrain and then render distance when near the limit. This changes the picture when it triggers, so it is a safety
  net, not a zero-visual knob. Use a value above steady footprint only to check it never fires.
- `textureBudgetMiB` (`graphics.rs:770`): not useful here, since the array is 38 MB and the budget is 256 MiB.
  Lowering it downsamples textures (visual change).
- `HORIZON_HDR_LIGHTING=0` (`gfx.rs:7285-7288`): only skips an HDR lighting path, not a clear memory item.
- mimalloc env: no remaining zero-visual win. `purge_delay` is already forced to 0 in code, `purge_decommits` is on,
  and `MIMALLOC_ARENA_RESERVE` only changes virtual reservation. If anything is tested, `MIMALLOC_PAGE_RECLAIM_ON_FREE=-1`
  is the only one that changes fragmentation, and expect noise.

Harness knobs (not Horizon): record `footprint -p`, and drop the Codex renderer and Xcode load from the run window.
Swap of 2.5-3 GB is present with a 0.2 GB-RSS game, so it will not fall by patching Horizon alone.
`resolutionScale` below 100 would cut every full-screen target proportionally, but it changes the image.

## 5. Suggested order

1. Harness: add `footprint -p` before/after (no code). Re-baseline base / packs / MakeUp.
2. Candidates 2(a), 3, 6: low risk, byte-identical, same pattern as `sprite-compress-f42`; est 15-115 MB in packs runs.
3. Candidate 4 after a per-buffer log from `pack_post.rs resize` (shader runs only).
4. Candidate 1 only after the representability assert reports zero misses.
