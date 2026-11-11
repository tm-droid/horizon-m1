# R3 memory research (2026-11-06)
Source: outputs/horizon-runtime/m1-performance/candidate-source (f42ef42e + local patches). Read-only, no runs, no census numbers exist in bench dirs (none ran `horizon-ctl memory`), so sizes below are computed from code + bench logs, not measured. Next step for real numbers: `horizon-ctl memory` (docs/horizon-ctl-commands.md:16) on a shader-on run, or scene_replay `--memory on` (upstream 41cf95bc, post-f42).
Paths below are relative to candidate-source/crates/horizon-client-render/src unless noted.

## 1. Big resident allocations
| Item | Where | Size (computed) |
|---|---|---|
| Block sprite arrays, Rgba8 + full mips | gfx.rs:2610-2680; sizes sprites.rs:104,141,257 | 2303 layers @64px (bench logs "block sprites: 2303 layers at 64 px") = 36 MiB top, ~48 MiB with mips. Budget 256 MiB is NOT binding. |
| Block sprites CPU copy (`RenderAssets.pixels`) | assets.rs:87, held by game.rs:19827/19861 | ~36 MiB, kept after upload. Not compressed (the HUD atlas copy is, hud.rs:67-68). |
| Animated-sprite frame buffer + CPU frames | gfx/animate.rs:102-198, sprites.rs:265 | tens of MiB, mip chains for every frame, plus `Arc<Vec<Vec<u8>>>` frames on CPU (Writer::Cpu path animate.rs:309). Not sized; check with census. |
| LabPBR normals+specular | gfx.rs:2612-2640; sprites.rs:121-130 | only if native shader pack on; cap 64 MiB each (MAX_MAP_BYTES) => up to ~2x(48 MiB w/ mips) |
| Shared HUD/GUI atlas | gfx.rs:2795-2830; hud.rs:111,978 | Rgba8, no mips, width >=4096, height up to 16384 (max 1 GiB if packs force it). Unknown real H; likely 64-128 MiB with 52 packs. CPU copy already lz4'd. |
| Section (terrain mesh) arena | gfx/arena.rs:14 PAGE_BYTES=256 MiB pages, :102 COMPACT_MIN_FREE=128 MiB, :105 SHRINK_MIN_BYTES=64 MiB | grows in pages; up to ~128+ MiB sits in free ranges before compaction; whole arena probably 150-300 MiB at RD12 with 3D-model packs |
| Shader-pack colortex | gfx/pack_post.rs:3598-3626 | BOTH sides A/B ALWAYS allocated (`sides = [0,1].map(texture_sized)`), plus depthtex0/1/2 Depth32, shadow maps (pack_shadow.rs:78-88), scratch copies. At 2560x1600 RGBA16F = 31 MiB per side per buffer. |
| Far terrain (LOD) | lod.rs (5051 lines); graphics.rs:646 default `lodDistance:0` = OFF | ~430 MiB when on (upstream #9111, open, unassigned). Bench profiles use lodDistance:0 so not in swap numbers unless user turned it on. |
| Audio | audio.rs:149 CACHE_BYTES=64 MiB (f32 samples) | <=64 MiB + streamed music decode |
| Allocator | horizon-threads/src/lib.rs:252-304 | mimalloc already global, purge_delay=0, mi_collect(true) exists. wgpu `MemoryHints::MemoryUsage` already (gfx.rs:1875). Nothing to gain here. |
| ram_limit governor | horizon-client/src/ram_limit.rs | env HORIZON_MEMORY_LIMIT_MB / HORIZON_MEMORY_HARD_MB: auto drops far terrain, then render distance (visible!) |

## 2. Knobs / code changes
1. Backport upstream 840a42cf: B texture of a colortex = second view of A unless a pass flips it (pack_post.rs:3618-3626 + alt-clear skip). Upstream states 35-224 MiB saved at 3440x1440 (BSL/Complementary/Bliss/SDV). No visual change (same data). Effort: medium, a ~60-line patch + clear logic.
2. Backport 7b80ab60 (free old pack buffers before resize creates new): removes transient 2x peak when window resizes/fullscreen toggle. No steady-state saving, avoids swap spike. Small patch (pack_post.rs resize at :3561).
3. arena.rs constants: COMPACT_MIN_FREE 128->32 MiB, SHRINK_MIN_BYTES 64->32 MiB. Est 30-100 MiB. No look change; costs more compaction copies (frame hitches risk, bench it).
4. Drop/compress `RenderAssets.pixels` after upload (reuse hud.rs lz4 pattern; sprites.rs:299 only shrink_to_fit). Est ~36 MiB. Need to check game.rs:19827,19861 consumers (re-upload paths: renderer rebuild, splitscreen).
5. audio.rs:149 CACHE_BYTES 64->24 MiB, or store i16: ~30-40 MiB. Re-decode hitches in villages/caves.
6. User-side, zero code: keep `lodDistance:0` (or farDetail:reduced = ~1/4 far quads, graphics.md); `resolutionScale` <100 shrinks pack targets (visible); `textureBudgetMiB` (graphics.rs:770): 32 would drop sprites to 32px => saves ~36 MiB GPU+CPU but visibly blurs 64px packs. Do not.
7. Texture compression (ASTC/BC via wgpu features): sprites 48 -> ~12 MiB (ASTC 4x4) and atlas 4x, but needs an encoder at load (seconds, 2303 layers x mips), banding on pixel art and GUI text, and sprite arrays use COPY_SRC|STORAGE_BINDING (shader packs' atlas copy, animation compute writes) which compressed formats cannot satisfy. Saves ~40-90 MiB total. Not worth it.
8. Other candidates tried, no gain: mip level cut (levels below 4px are <0.1%); allocator swap; MemoryHints.

## 3. Upstream commits after f42ef42e (f42 = 2026-11-03 08:12Z; all listed are ahead of it: gh compare behind=0)
- 840a42cf (11-05) Shader packs: a buffer gets its second texture only when a pass flips it. -35..-224 MiB @3440x1440. BEST.
- 7b80ab60 (11-06) free old buffers before resize makes new ones (SEUS PTGI OOM'd on fullscreen).
- 4c0ef1d7 / 4b6cd5e2 / 8794c49a (11-05/06) colortex+atlas mip blend: quality, may ADD small mip memory; skip.
- 663ce801 (11-04) "compressed sprite pixel storage" (scene_replay adapts to it); candidate already has hud lz4 (hud.rs:68), sprites path may differ.
- 41cf95bc, 797d6d0a, 512d5cf8 (11-03/04) GPU-memory census in scene_replay (tooling only).
- 3f941752, 7a450789 (11-03) RAM limit steps down before the limit; docs of hard limit.
- 23e710f7 (11-05) launcher screenshot byte budget (launcher only, irrelevant to game RSS).
- 0e96b88a / 0f7f9db8 / 49886f71 / 695feba0 / 893fc9ae (11-03/04) far-terrain perf/threads; none cut resident memory. #9111 still open.
- cfccbb8f (11-05) GUI animated sprites sliced to first frame in atlas: shrinks atlas; candidate already has `first_frame` (hud.rs:366), verify identical.
- Full list: scratchpad commits.txt (4043 unique commits since 11-03).

## 4. Estimates (MB saved / looks risk)
| Change | MB | Looks risk |
|---|---|---|
| 840a42cf backport (shader on) | 60-150 at M1 Air res (2560x1600), 35-224 upstream | none |
| arena compaction thresholds | 30-100 | none (hitch risk) |
| Drop sprite CPU copy | ~36 | none |
| Sound cache cut | 30-40 | none |
| 7b80ab60 backport | 0 steady, avoids ~50-200 MiB spike | none |
| lodDistance stays 0 | up to 430 | n/a |
| ASTC/BC | 40-90 | medium-high |
