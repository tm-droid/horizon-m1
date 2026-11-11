# Memory and stutter pass, 2026-11-10 (M1 Air, 8 GB)

Base: fdc87ae + the 28 patches of `outputs/horizon-native/daily4-stack.txt`, applied in order in `/private/tmp/claude-503/mem/src`.
Nothing was compiled or run (no cargo allowed); everything below is from reading code, logs and the Metal cache directory.
`git apply --check` passes for thread-cap and dimension-warm on the stack and with dimension-warm after thread-cap.

| Item | Result | Path |
|---|---|---|
| 1 thread-cap | patch | `outputs/horizon-native/thread-cap-fdc87ae/thread-cap.patch` (+NOTES.md) |
| 2 dimension warm-up | rewritten patch (v1 + main-thread trim) | `outputs/horizon-native/dimension-warm-fdc87ae/dimension-warm.patch` (+NOTES.md, NOTES-v1.md) |
| 3 compact layout under packs | documented only | this file |

## 1. thread-cap

Pools sized from `worker_count()` (8 on M1) vs 4 performance cores:

| Pool | Site | Before (M1) | After |
|---|---|---|---|
| chunk encode ("warm") | lan/chunks.rs:493 | 7 threads + caller | 7 spawned, 3 active unless a listener is open; + caller = 4 |
| net threads | lan/io_pool.rs:267 | 4 threads, inherited QoS | 4 threads, utility QoS until a listener opens |
| far decoration | vanillagen/lod.rs:75 | 3 | 2 (`fast_cores().div_ceil(3)`) |
| far LOD sampling + meshing | client-render/lod.rs:1339 | 5 + 2 | 1 + 2 (`cores = fast_cores()` = 4) |
| region compression helpers | save.rs:2148 | 4 | 2 |

New in horizon-threads: `fast_cores()`, `set_network_open`/`network_open`, `network_current(wide)`. `Lan::listen_on` sets the flag and
`stop_listening` clears it, so a LAN world or dedicated server gets the old behaviour (all encode threads, default-QoS net threads).
Non-Apple targets: `fast_cores()==worker_count()` and the encode cap equals the old count, so nothing changes there.

Why safe: the pool threads were optional helpers (`warm`, `bodies_with` run the job on the caller and never wait for them).
Risks: (a) `small: cores <= 4` in the far LOD now holds on an M1 (far sampling one job per 500 ms while near terrain loads; far terrain builds slower);
(b) utility-QoS net threads put loopback chunk framing on E-cores. Both have one-line reverts, listed in the patch NOTES. Gain not measured;
expect lower p99 while flying into new chunks, up to ~15% slower far/chunk arrival.

## 2. Dimension shader warm-up

- Old agent's `dimension-cache.patch` still applies cleanly to the stack (checked) and after up-dimension-swap. Logic reviewed and correct:
  warm key is the final folder (`dimension_folder_named`), cancelled by `CancelOnDrop` on a real switch, drops its result, warm failures never
  disable the pack, and no dimension macro exists in the translated shader text so the cache keys match the real build.
- **Metal persists across launches.** `$(getconf DARWIN_USER_CACHE_DIR)/com.apple.metal/` holds `16777235_322/functions.data` (20 MB) and
  `32024/libraries.data` (44 MB), a system-wide cache shared by all apps. Bench logs: MakeUp overworld build 5191 ms (a-11) and 6105 ms (a-12) on
  the first run of a build with new shader text, then 360-665 ms in all later launches (a-10, a-13..a-18). So the 2.5-3 s stall is paid once per
  (build, dimension folder) and again after eviction of the shared cache; it is not per process. Every new daily stack changes the generated shader
  text, which is why it keeps recurring in testing.
- App-side cache is impossible today: wgpu 30 `PipelineCache` is Vulkan only (code uses `cache: None`), wgpu-hal metal has no MTLBinaryArchive.
- Verdict: warm-up fixes the compile part (~2.1-2.7 s of ~3 s) for the first entry of each build; ~0.35 s of main-thread prep stays.
- Rewrite (shader_packs.rs only): the warm path no longer builds the mc_Entity table (105 ms logged), block/entity/item id tables or the `pack_ids`
  swap, since pipelines do not depend on them (`pack_post::block_ids` accepts any length; `min_binding_size: None`).
- Not done because gfx.rs / pack_post.rs are off limits: (a) lower warm threads to utility QoS (`horizon_threads::far_terrain_current()` at the top of the
  `build` closure in `load_shader_pack` when `warm`); (b) let `PackPost::build` make 1x1 targets and a tiny shadow map for warm so it costs ~0 RAM instead
  of ~150-450 MB transient. v1's hunks in those two files are kept unchanged: re-check them against the other agent's edits.
- Cost: transient RAM during warm, ~0.2 s main-thread hitch twice per session, 2 compile threads for ~10 s. Opt out: `HORIZON_PACK_WARM=0`.

## 3. Compact terrain layout under shader packs (#12448)

Where the wide layout is forced (gfx.rs, so documented not patched):
- `packed_quads = flat.is_some() && !shader_pack && packed_wanted()` at renderer creation (~4573 on the stack).
- `follow_packed_layout` (~6138): `want = flat.is_some() && !pack && native.is_none() && packed_wanted()`. Any running `shaders/` pack turns the compact
  record (24 B per whole-cube quad, `mesher/packed.rs`) off and drops every section; the arena then holds 4 x `TerrainVertex` (24 B) per quad.
- Reason: a pack's terrain/shadow programs read vertex buffers (`TERRAIN_ATTRIBUTES` in `load_shader_pack`; `buffers: if flat { &buffers[..1] }`),
  while the compact layout is expanded only by terrain.wgsl `section_corner` (storage pull).

Does MakeUp need extra attributes? No: its inputs (position, UV, layer/mc_Entity, light, colour/AO, normal, tangent, midBlock) are all derivable
from the record plus the quad's four corners; the flat pack path already reads neighbouring corners from the arena page for normals (`block_ids`
doc comment, pack_post.rs:1283). Upstream PR #12449 (commit 957ecaff5f, present in the scratch repo's objects) does exactly this: GLSL port of
`section_corner` (`pack_atlas::PULL_FLAT`), flat pack pipelines take no vertex buffer, per-corner alpha codes in records, whole-quad padding. Author's
numbers (BSL, Photon, RD 64, big Apple GPU): section vertices 5.9 -> 3.06 GB, flight 1% low 2-5 -> 8-10 fps, `gbuffers_terrain` +1.7 ms at noon,
pixel diffs within compare noise. Scratch cherry-pick against the stack: every file applies except `gfx.rs` and `game/render_control.rs` (help-text line).

Why no patch: the flip lives in gfx.rs (about 35 lines: `packed_on` field, `follow_packed_layout` condition `(!pack || self.pack_terrain_flat)`,
`buffers: if flat { &[] }` at both `Geometry` sites and `pull: String::new()`), the pack-side change must be validated with the GPU test
`midpoint_test::compact_records_feed_a_pack_the_vertices_they_hold`, the PR also changes record padding for the non-pack path, and it is
unreviewed/open with a +1.7 ms GPU cost on a heavy pack. Cannot show safety without running the test. Recipe when gfx.rs is free:
`git show 957ecaff5f -- <all files except gfx.rs and render_control.rs> | git apply`, then port the gfx.rs hunks by hand, run the GPU test and one
MakeUp flight with `horizon-ctl section-layout compact|wide`. Expected gain on this machine at RD 12: smaller than upstream's (their 3 GB saving is at
RD 64); roughly half of the solid-terrain arena, maybe 100-300 MB of the 1.3 GB GPU share. Note it needs `pack_terrain_flat` (Metal flat draws; see
up-metal-flat in the optional list), else it stays wide.

### Other RAM consumers (code reading + prior audit; no heap census was run)

Measure first with `horizon-ctl memory` (feature `alloc-census`, horizon-threads/heap_census.rs) to rank the CPU heap; GPU side via the arena logs.

1. Section vertex arena (gfx/arena.rs): 256 MiB pages, large pages up to 2 GiB - 1 MiB, growth `current + min(current, 256 MiB)` with old and new both live
   during the copy (up to +256 MiB transient). Safe cap on 8 GB: keep render distance 12; nothing else needs a hard cap if the layout item above lands.
2. Resource-pack textures (user pack list): audit `makeup-packs-gpu-audit-2026-11-10.md` puts decoded PNGs at ~592 MB; Dramatic Skys ~280 MB with mips,
   Fresh Buckets ~169 MB. No sprite or image size cap exists in the loader (grep for downscale/max sprite found none). Safe: disable those two packs
   (-300 to -450 MB), or add a loader cap of 512 px for images the world never samples at that size (GUI-only/sky when a pack draws the sky).
3. Pack post targets and shadow map (pack_post.rs `build`, pack_shadow.rs): colortex ping-pong at window resolution (Rgba16F is 8 B/px; 2560x1600 is
   ~33 MB each) and shadow depth32 + colours at `shadowMapResolution`, clamped only to the device limit (`shadow.resolution.clamp(1, max_texture_dimension_2d)`).
   Safe cap on 8 GB: clamp shadow resolution to 2048 (16 MB depth) unless the pack asks for fewer; this changes shadow sharpness for 4096 configs.
4. PBR material atlases: `pack_material_atlases` builds two more atlases the size of the colour atlas when the resource packs carry `_n`/`_s` maps
   (gfx.rs ~7058), so the block atlas costs 3x. Safe: skip building them when the active shader pack never samples them (MakeUp's MATERIAL_GLOSS off).
5. Integrated-server encode cache (`lan/chunks.rs` `ChunkEncoder.cache`, swept at `CACHE_SWEEP = 1<<15` entries): holds a wire copy per resident server
   section for the loopback client. Bounded, but 32768 entries is ~2x the sections of sim distance 8 (17x17x24 = 6.9k) to RD 12 (~15k). Safe cap: 16384.
   Others looked at and fine: audio cache 24 MB (`CACHE_BYTES`), vanilla LOD column cache `CACHE = 1024`, allocator purge delay already 0
   (horizon-threads/lib.rs `PURGE_DELAY`).

## Not verified
Nothing built, linted or run. The thread-cap patch adds a closure capture and a `filter(|&i|` change in `warm_pool`; please build before benching.
