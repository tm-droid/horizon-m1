# R20: M1 GPU optimisations for Horizon (2026-11-06)

Scope: Horizon f42 (wgpu 30.0.1 on Metal) on a MacBook Air M1 with 8 GB. The M1 GPU is a tile-based deferred renderer (TBDR) with 8 cores, unified memory and about 68 GB/s of bandwidth. Constraint: the game must look the same. Baseline: MakeUp Ultra Fast 9.6 at ~43 FPS static and ~36 FPS in flight. It is GPU-bound (p99 ~25 ms). Without a shader pack Horizon runs at ~170 FPS, so nearly all headroom is in the shader-pack path (`gfx/pack_post.rs`).
Not repeated here: R2, R3, R8, R9, R16 and deep-pass §2/§5d.
Source refs are pristine stage (`outputs/horizon-runtime/launcher-data/native/stage`) line numbers unless noted. Nothing was compiled or benchmarked: a benchmark was running on this Mac.

## Ranked candidates

| # | Candidate | Expected gain (MakeUp) | Look risk | Effort | Where | Status |
|---|---|---|---|---|---|---|
| 1 | Composite passes that cover the target: `LoadOp::Clear` instead of `Load` | 1-3 ms GPU (~250 MB/frame of tile loads at 2560x1600) | None for passes that pass the proof | Low | `gfx/pack_post.rs:4196-4206` (load-op choice), `build_pass` 1380-1619; `horizon-shaders/src/post.rs:210-235` | **Patched**: `outputs/horizon-native/composite-overwrite-f42/` |
| 2 | Fuse the gbuffers render passes in `begin`/`draw_opaque` (one pass per target set instead of reopening with Load/Store, depth copies kept outside) | 1-3 ms, possibly | Medium (ordering of the depth1/depth2 snapshots) | High | `gfx/pack_post.rs:2828` (`begin`), `3178-3215` (`draw_opaque`) | Not patched |
| 3 | Turn off naga MSL loop bounding | 0-5% of loop-heavy pass time; may be ~0 | None | Trivial | `third_party/wgpu-hal/src/metal/device.rs:224`; emitter `third_party/naga/src/back/msl/writer.rs:1079-1093` | **Patched**: `outputs/horizon-native/msl-loop-bound-f42/` |
| 4 | Draw the screen effects (vignette, pumpkin, portal, etc.) into the HUD pass instead of their own pass | 0.2-0.5 ms (one full-screen load/store saved) | Low | Medium | `gfx.rs:9597-9660` (screen effects), `hud.rs:2714` (HUD pass), `gfx.rs:9699` | Not patched |
| 5 | Swapchain `framebufferOnly=true` (drop COPY_SRC/COPY_DST from the surface usage) | Small (lossless compression of the drawable) | None | Medium (screenshots and the world blit need another path) | `gfx.rs:2112-2118`; `third_party/wgpu-hal/src/metal/surface.rs:263` | Already listed as #8 in earlier research and skipped |
| 6 | `TRANSIENT` usage (memoryless on Metal) for depth attachments that are always discarded | Memory only (a few MB), no FPS | None | Low | mirror `gfx.rs:8121`, 3d crosshair `9683`, hand `9474`; hal `metal/device.rs:561-564` | Not patched (no FPS gain) |
| 7 | Generate mips in one pass, or with compute, instead of one render pass per level | Low (colortex1 only; small levels) | None | Medium | `gfx/pack_post.rs:3439-3462` (`mipmap`) | Not patched |
| 8 | `StoreOp::Discard` on sink pass depth | 0 for MakeUp | None | Low | `gfx/pack_post.rs:4211` | Not worth it |
| 9 | Remove the depth1/depth2 copies | None: packs read `depthtex1`/`depthtex2` | n/a | n/a | `gfx/pack_post.rs:3198-3213` | Needed, refuted |
| 10 | `SHADER_F16`: translate GLSL `mediump` and pack `half` to f16 | Up to 10-20% ALU in theory | Real (precision, banding) | High (feature is not requested at `gfx.rs:1843-1853`; translator work) | `gfx.rs:1843`, `horizon-shaders` translator | Not patched |
| 11 | Skip the per-frame clears | Low: MakeUp sets `clear=false` on all but colortex2 | None | Low | `gfx/pack_post.rs:4039` | Not worth it |

### 1. composite-overwrite (patched)
Every shader-pack composite pass opens its colour attachments with `LoadOp::Load` (`pack_post.rs:4196-4206`), unless it is a sink without a viewport. Iris ping-pongs colortex sides, so the written side holds the frame before last. On a TBDR GPU a Load copies the whole attachment from memory into tile memory before the first fragment. When a pass writes every pixel anyway, that read is wasted. `LoadOp::Clear` skips it.

The patch proves coverage before it switches. The vertex stage must be the unmoved quad: the only `gl_Position` write is one of three textual forms (`ftransform()`, `gl_ModelViewProjectionMatrix * gl_Vertex`, `gl_ProjectionMatrix * gl_ModelViewMatrix * gl_Vertex`). Horizon's composite matrix is a constant ortho (`translate/rewrite.rs:70-72`), so the quad (`hz_quad[gl_VertexIndex]`, `translate/mod.rs:419`) covers the target. The fragment module must contain no `Statement::Kill`. No target blends. No `scale.` viewport. Not the final pass, not a sink, and not geometry.

Evidence for MakeUp 9.6 (extracted from `tests/gm-a-1/shaderpacks/MakeUp-UltraFast-9.6.zip`):
- passes: prepare, deferred (`DRAWBUFFERS:14`), composite (016), composite1 (1), composite2 (135), final;
- every composite-group vertex file has exactly one `gl_Position=gl_ModelViewProjectionMatrix*gl_Vertex;`;
- `discard` appears only in the gbuffers fragment code (`common/water_blocks_fragment`, `solid_blocks_fragment`, `solid_dh_*`, `shadow_fragment`), never in a composite;
- `shaders.properties` has no `blend.`, `scale.` or `flip.` directive for a composite;
- formats (`final_fragment.glsl`): colortex0 R11F_G11F_B10F (4 B); colortex1 and colortex3 RGBA16F (8 B) or R11G11B10F; colortex2 R8; gaux1 and gaux4 R11G11B10F; gaux2 R8; gaux3 R16F.
So all 5 quad passes qualify: about 9 attachment loads per frame, about 63 bytes per pixel. At 2560x1600 that is about 250 MB per frame. At 68 GB/s that is up to ~3.7 ms of pure bandwidth; lossless framebuffer compression and overlap with ALU make 1-3 ms a realistic range.

Residual risk: a pack whose matching `gl_Position` assignment sits inside a branch that can skip it. Its uncovered pixels would become transparent instead of stale. GL leaves that case undefined as well.

### 2. gbuffers pass fusion (not patched)
`begin()` (2828) and `draw_opaque()` (3178-3215) open and close several render passes over the same colour and depth attachments, each with Load/Store. Each reopen costs one full read and write of every gbuffers target. Fusing them is the next-largest bandwidth item. It needs care because the depth1/depth2 snapshots (copies at 3198-3213) must land between the opaque and translucent draws. This is cross-cutting and needs a benchmark, so it was left as a design note.

### 3. msl-loop-bound (patched)
The safe `create_shader_module` makes every module request `force_loop_bounding`. naga then wraps every MSL loop with a `uint2` down-counter and a branch (`writer.rs:1079-1093`). MakeUp's heavy passes loop on every pixel (AO, volumetric clouds and light, bloom and DoF taps). Horizon cannot use the per-module opt-out (`create_shader_module_trusted`) because `horizon-client-render/src/lib.rs:3` has `#![forbid(unsafe_code)]`. The patch gates the bound in the vendored hal behind `HORIZON_MSL_LOOP_BOUNDING=1` (off by default). Bounds checks stay on. Risk: a shader that really never ends would hang the GPU until Metal's timeout instead of breaking out. GL runs the same packs with no bound.

### 4. Screen effects in the HUD pass (not patched)
The screen-effect overlay (`gfx.rs:9597-9660`) is its own render pass with Load on the swapchain, and it is followed by the HUD pass (`hud.rs:2714`). Drawing it as the first draws of the HUD pass saves one full-screen load and store (~30 MB at 2560x1600, ~0.2-0.5 ms). It is only active while an effect is visible, so the average gain is lower.

## Checked and already optimal (refuted)
- Formats: the colortex formats follow the pack's directives; R11G11B10F is already used where the pack asks for it.
- `STORAGE` usage is added only when a compute program needs it (`pack_post.rs:3560-3660`).
- Bind groups are cached; there is no per-frame bind-group churn in the composite loop.
- `split_solid` on Metal (`gfx.rs:8190`) is already tuned.
- The final pass already uses `Clear` (comment at `pack_post.rs:4030`: clearing lets a tiled GPU skip loading).
- Native sky and mirror passes already `Discard` depth (`gfx.rs:8030`, `8125`); the world pass stores depth only when `keep_depth` is set (`gfx.rs:8212-8243`).
- The world blit at frame start is needed (the pack reads the vanilla frame).

## Patches
Both are uncompiled. Both pass `git apply --check` against stage + the 12 r3 patches (order: cloud-prep, shadow-scratch, qos-backport, jobpool-qos, sprite-compress, emissive-bsearch, pass-merge, shadow-dedup, particle-cull, adaptive-upload, pbr-cpu-drop, anim-frame-compact) with no offsets, and also against the pristine stage. They touch disjoint files and can be applied in either order.
- `outputs/horizon-native/composite-overwrite-f42/composite-overwrite.patch`: `crates/horizon-shaders/src/post.rs`, `crates/horizon-client-render/src/gfx/pack_post.rs`. Includes the unit test `only_the_unmoved_quad_covers_the_target`.
- `outputs/horizon-native/msl-loop-bound-f42/msl-loop-bound.patch`: `third_party/wgpu-hal/src/metal/device.rs`.

Compile-risk notes: the naga `Statement` shapes used by `kills()` were checked in the vendored naga (`Kill`, `Block`, `If{accept,reject}`, `Switch{cases[].body}`, `Loop{body,continuing}`). `PostProgram` is built only in `post.rs` (3 sites, all updated). `Pass` is built in 2 literals (both updated). The hal crate has `extern crate std` for metal (`lib.rs:245-247`).

## Bench plan
1. Build r4 = r3 + both patches.
2. Use the usual method (CLAUDE.md: world list, `test stuf`, midnight, tp to 238.5 65 440.5) with MakeUp, static and in flight. Close background apps first.
3. Run the loop-bound A/B on the same build: `HORIZON_MSL_LOOP_BOUNDING=1` versus unset. Add `HORIZON_SHADER_PACK_TIMING=1` for per-pass GPU times.
4. For composite-overwrite, take a screenshot diff of the bench scene against r3. It must be pixel-identical (allowing for normal frame-to-frame noise such as clouds).
