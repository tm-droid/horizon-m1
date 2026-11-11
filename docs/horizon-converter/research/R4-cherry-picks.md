# R4 upstream cherry-pick triage

Local tree = candidate-source, which is effectively pure upstream f42ef42 (r3 patches live as separate transform scripts in `outputs/horizon-native/*-f42/`, not applied in it). Upstream is 2154 commits ahead of f42ef42 at these shas, so "applies clean?" = `git apply --check` of the commit's diff on a scratch copy of only the touched files, on pure f42 and on f42 + our patches. Source tree untouched. Scratch: `/private/tmp/claude-503/r4-scratch` (`r4/` subdir). Ready patches: `R4-patches/` next to this file.

Our patch set that stacks cleanly on f42 (checked): particle-cull, adaptive-upload, anim-frame-compact, emissive-bsearch, sprite-compress, qos-backport, jobpool-qos, pbr-cpu-drop. `shadow-scratch` and `cloud-prep` do not `git apply --check` against that stack even at -C0 (their line numbers assume a different order or base). They were judged by hunk position instead.

Summary: sha | applies clean? | deps | conflicts with ours | M1 gain | verdict

| sha | applies clean? | deps | conflicts | M1 gain | verdict |
|---|---|---|---|---|---|
| a66f8fa2 shadow pass culls to view casters | gfx.rs hunks 1-5 and resident.rs: yes (offsets -800..-1100). pack_post/native_post/tests: no, they need `every_face` (#9033) | none for the port; `cull_proj`, `ShadowView.light`, `Cull` trait all exist in f42 | none textual. shadow-scratch edits gfx.rs 6702-6716, this edits 6687-6696, no overlap. cloud-prep far away | unmeasured upstream (no FPS numbers). Fewer sections in the shadow pass for Iris packs, so fewer draws and vertex work in a pass MakeUp runs every frame | PICK (hand port, 183-line patch ready, `R4-patches/a66f8fa2-port.patch`). A/B test shadows |
| cb6a8069 3 ms budget for applying far detail | non-test hunks 1-7: yes on f42 and on f42+qos-backport. Test hunk 8: no (module differs) | none (f42 has `apply_detail`, `refreshed_since`, same `receive` shape) | qos-backport also edits lod.rs, no overlap | 0 at default `lodDistance=0`. Upstream: avg 94 -> 134 FPS over far terrain at 256 | OPTIONAL, only if far terrain gets enabled. `R4-patches/cb6a8069-nontest.patch` |
| 0e96b88a worker builds the widths detail reads | no | fixes #8815 (lazy `ReducedColumns` levels), which f42 does not have; f42 is still eager (`levels: [Vec<Column>; 4]`) | n/a | none: f42 lacks the regression it fixes | SKIP |
| ad491f1b one span per dampening run | mesh.rs: no. vanillagen/lod.rs hunks apply | b66c4484, a9e638a4, 3b3094e2 (mesh.rs), a7274ef8 (lod.rs) | none | memory only, far terrain only (off by default; Apple GPUs capped at 128) | SKIP |
| 695feba0 zoom detail off by default | no | `lod_zoom_detail` field and the feature do not exist in f42 | none | none | SKIP (N/A) |
| ce869452 LabPBR maps follow texture budget | no, hunk 1 fails on a comment only. Code shape matches (3 sites). A hand port is about 10 lines | 1 comment-changing commit | anim-frame-compact touches sprites.rs elsewhere, no overlap | zero at default budget. Raising `textureBudgetMiB` makes LabPBR maps bigger, which costs RAM on 8 GB | SKIP |
| e62b4a1e hide entities in sections the graph never reached | no (gfx.rs, game.rs, entity_culling.rs, occlusion.rs all fail; `occlusion_culling.rs` and `voxel_occlusion*` do not exist in f42) | the async entity/particle occlusion stack: 9c101044, a9a08ef1, 03ef1816, 37380065, 627309b8, 63c35fd5, 13217941, 946bfb55, d5abaf67, 7e22c998, d3ae3e9f, f28e838d, 70411290, 8f5ba77a, d87992bd. About 4500 added lines, adds `occlusion_culling.rs`, `particle_culling.rs`, new graphics options | high: the stack touches game.rs (175 intermediate commits), particles.rs (conflicts with particle-cull), gfx.rs, item_draw.rs. Ours edit the same files | CPU-side, scene dependent (entity-heavy only). Upstream bench was OpenGL release, nothing Metal specific | SKIP as a cherry-pick. The base stack is a separate project (see end) |
| d87992bd reduce occlusion query overhead | no (same reason; 10 files, 4 do not exist in f42) | same stack | same | same | SKIP |
| 1174737b one memo for last cell's chunk and section | alone: no. In chain 4d32656a -> 25b8c5d0 -> 1174737b onto f42: all three apply clean (world crate, tests, `collisions.rs`) | 4d32656a, 25b8c5d0 | none (no r3 patch touches horizon-world or collisions.rs) | none in normal play. Only helps a far teleport or move packet. 1174737b itself only repairs a 7.5% instruction regression that 25b8c5d0 added to mob moves | SKIP (optional chain if teleport hitches show up) |
| 25b8c5d0 far move: pass missing chunks/empty sections by row segment | alone: no (needs 4d32656a). Chain above applies | 4d32656a | none | removes a 2.3 s server tick for an 8,000-block hop. Zero for the benchmark (`/tp` is near) | SKIP (same chain) |
| 56e06994 snapshot cache keyed on source hash, not exe mtime | yes (build.rs is a new file, cache.rs applies; one test-only intermediate, 35a31534) | none | none | none at runtime for a released binary. Dev only: a rebuild keeps `.horizon-cache`. Adds a build.rs that hashes the horizon-world and horizon-core sources, which makes the first build slower | SKIP |

## Detail notes

### a66f8fa2 (the one worth taking)
- What it does: for Iris-format packs, builds a second pair of frusta ("casters") from the camera frustum stretched toward the light, and also requires each 16-block section to hit both. `shadow.culling=false` and `reversed` still draw everything out to their distance (the `unculled` path unions first). Horizon's own packs get `view_casters: false` and are unchanged.
- Port pieces, all verified with `git apply --check` on pure f42 copies of the 4 files:
  1. gfx.rs: comment, `ShadowCull` replaces `Frustum` as `light`, `Cull::tight()` default, `impl Cull for ShadowCull`, `shadow_casters()`.
  2. resident.rs: `let bounds = self.bounds[slot as usize].filter(|_| frustum.tight());` so shadow tests use whole sections, not tight bounds.
  3. pack_post.rs: `pub view_casters: bool` in `ShadowView`, `view_casters: true` in the Iris constructor. native_post.rs: `view_casters: false`.
- Dropped from the port: upstream tests (they use `every_face` from #9033, which f42 lacks). The 2 new tests (`shadow_caster_tests`) can be re-added; they do not use `every_face`, only the `view()` helper edit does. Not compiled: no cargo here, so compile and the tests are unverified.
- Risk: the commit says its test camera "matched our probe with the camera looking straight up" (a guess). A wrong plane drops shadows silently. Test: low sun while turning, sun ahead, looking straight up and down, then compare against the unpatched build.
- Metal relevance: pure CPU visibility plus fewer shadow-pass draws, so backend neutral. Tile GPUs gain from fewer vertices. MakeUp Ultra Fast has `SHADOW_CASTING` on at distance 105 m (R6), so it uses this path.
- Overlap with ours: `shadow-scratch` rewrites `boxed`/`seen` in the same function. Both still use `light` only as `&light` in `visible(...)` (generic over `Cull`), so a merge should be mechanical. Order: apply a66 hunk 3 first, then shadow-scratch.

### cb6a8069
- Same budget logic upstream measured (avg 94.4 -> 133.6 FPS, worst frame 739.7 -> 34.2 ms) but only over far terrain at `lodDistance` 256. Default is 0 and `lod_distance_capped` limits Apple GPUs to 128 (R2). Take only if far terrain is turned on.

### Entity occlusion stack (not a cherry-pick)
- f42 has `game/entity_culling.rs` (738 lines, synchronous). Upstream replaced it between f42 and e62b4a1e with an async pipeline: 9c101044 "Optimize asynchronous entity and particle culling" (`occlusion_culling.rs` +2035, `particle_culling.rs` +336, `particles.rs` +240). d87992bd and e62b4a1e are small follow-ups. Taking just those two is impossible; taking the stack means a new feature with its own thread pool (ray and plane workers) on a 4P+4E, 8 GB machine, and a rewrite of the area that our `particle-cull` already patches. Recommend a separate unit only if profiling shows entity/particle culling cost on the M1.

### Method caveats
- Intermediate-commit lists come from `gh api commits?path=` filtered to `compare/f42ef42...<sha>`, so merge commits can inflate counts (game.rs: 175).
- `git apply --check` shows textual fit only. Nothing was compiled.
- Pre-existing files in the scratch dir (`t_*`, `chain`, `check.txt`, `*.err`) belong to other runs and were not used.
