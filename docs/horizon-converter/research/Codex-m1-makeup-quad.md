# One-pass cloud subgroup sharing — blocked before device testing

2026-11-07. Investigated a new cloud-only optimization, retaining full-size AO,
sharp scene colour and original MRT graph. No engine files, Java instance,
runners or halfres packs were edited. No compiler, game, queue or GPU test ran.

## Exact blocker

`subgroupBallot(true)` does not prove non-helper shuffle sources. The normative
[Khronos subgroup specification](https://raw.githubusercontent.com/KhronosGroup/GLSL/main/extensions/khr/GL_KHR_shader_subgroup.txt)
states at lines414-416 that helpers participate but may be treated inactive
for non-quad operations. Thus a bit accepted by ballot does not guarantee
the same helper is a valid indexed shuffle source. Coordinate/depth checks
also cannot distinguish helpers at a fullscreen triangle's diagonal boundary.

Local f42 evidence:

- `third_party/naga/src/front/glsl/variables.rs:211-212` exposes subgroup size
  and invocation ID, but its builtin mapping lacks gl_HelperInvocation.
- `front/glsl/builtins.rs:1163,1187-1215` supports ballot/indexed shuffle,
  but no subgroup quad functions.
- `back/msl/writer.rs:4310-4325,4391-4402` lowers directly to Metal simd_ballot
  and simd_shuffle without explicit helper exclusion.
- `crates/horizon-shaders/src/translate/mod.rs:1196-1197` allows subgroup
  operations and fragment stages. Renderer `gfx.rs:5860-5871` advertises feature
  macros when SUBGROUP is enabled. This proves availability, not helper safety.

Fresh static review independently found the helper proof absent. This is a
proof gap against the required safety condition, not an observed GPU failure.
A green diagnostic pixel could prove branch activation, not helper validity.

## Draft and next implementable step

`outputs/horizon-native/makeup-quad-prototype/` retains a guarded design draft,
README, blocked-status manifest and static test. Builder always exits with the
blocker; GLSL has an explicit compile-time error. No MakeUp-M1-Quad.zip/sidecar
remains in game shaderpacks. A local draft ZIP was removed before delivery;
it was never loaded. R1/r2 artifact hashes remain unchanged.

Draft design: advertised basic/ballot/shuffle, size32, source-lane ballot,
shuffled-coordinate proof of four distinct pixels in one aligned2x2 cell,
cohort-wide sky/hand/depth gate, leader-only cloud affine offset/transmission,
reconverged coefficient shuffle. Original full-size AO/sharp source and original
cloud fallback remain; underwater/DH/unsupported layouts cannot share.

Prerequisite: expose verified helper status through frontend/IR/Metal backend,
then ballot(nonHelper), requiring all four source bits before any shuffle.
That is an engine task outside shader-only ownership; no engine patch was
attempted. A supported quad-operation path with checked helper semantics is
another route. Do not replace this prerequisite with assumed lane layout or
silently all-fallback code.

After that prerequisite, diagnostic should mix60% green/shared or red/fallback
with40% actual computed scene colour to keep the expensive cloud result live.
Unobstructed overworld sky should show green where sharing activates; terrain
and rejected sky cohorts remain red. All-red is not success. Disable diagnostic
for matched timing. No shader compilation, activation, visual or speed claim
exists; masked SIMD execution may remove assumed raymarch issue-slot savings.

## Check

`python3 -m unittest discover -s outputs/horizon-native/makeup-quad-prototype -p 'test_*.py' -v`
→ exit0, 1 passed: builder refuses packaging, GLSL guard present, no runnable
ZIP/sidecar, original source and halfres r1/r2 hashes unchanged.

## Proper quad path: final read-only trace

Horizon submits parsed GLSL as `ShaderSource::Naga` directly (`translate/mod.rs:1196–1197`, `pack_post.rs:1508–1513`); a WGSL round-trip is not required. The missing frontend links are GLSL `builtins.rs` overload registration1187–1206, `GatherKind`1288/name mapping1297 and `MacroCall::SubgroupGather` lowering2425–2447. IR `GatherMode::QuadBroadcast` already exists at `ir/mod.rs:1489`; validation requires QUAD_FRAGMENT_COMPUTE and constant index; Metal writer4413 emits `metal::quad_broadcast`. Renderer `gfx.rs:5860–5871` must advertise quad only with verified fragment capability.

A future implementation must execute communication uniformly including helper lanes before divergent sky branches, derive leadership without assuming subgroup IDs for helpers, and replace implicit derivatives inside leader-only cloud work with verified explicit-LOD/gradient sampling. Comparing own fragment coordinates with quad-member0's broadcast coordinates is a proposed leader derivation, not yet a validated Metal guarantee. Exact Metal helper/leader semantics and visual edge behavior remain proof gaps. No runnable artifact or engine patch was created.

## Apple primary specification checked (broader continuation)
The current primary PDF was downloaded from https://developer.apple.com/metal/Metal-Shading-Language-Specification.pdf and text-extracted locally after the web reader's size limit. Edition2026-06-04, pages226–232: Metal only permits reads from active source threads; page227 says helper threads execute gradients and then become inactive. Therefore adding GLSLquad syntax alone does not close the helper safety gap on this backend. Page230 documents `quad_is_helper_thread`, and page218 documents `simd_is_helper_thread`; exposing and validating helper status is a concrete future frontend/IR/backend task. Existing inspected NagaIR/GLSL/MSL sources have no HelperInvocation mapping. Do not assume the GLSL/Vulkan helper guarantees automatically hold for Metal's lowering. Prioritize the directly applicable center-depth demand optimization and fresh-terrain profiling before expanding this shader experiment. No runnable quad artifact produced.
