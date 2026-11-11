# Horizon upstream delta since f42ef42 (2026-11-05)

Repo: https://github.com/horizon-rust/horizon . f42ef42 -> main 41d5649e = 2793 commits (300+ files). f42 -> nightly 6475f62 = 1339 commits. 6475f62 -> main = 1454 more. Nightly 6475f62 released 2026-11-04.
Method: commit-subject grep + commit bodies + issue search. Code-level claims marked UNVERIFIED were not read in source.

## 1. Perf-relevant commits (subject-level; full list via compare API)
Renderer / culling
- GPU culling opt-in (Vulkan/DX12 only, never Metal): [9952a853](https://github.com/horizon-rust/horizon/commit/9952a853), [85b95500](https://github.com/horizon-rust/horizon/commit/85b95500), [1a3125fc](https://github.com/horizon-rust/horizon/commit/1a3125fc), [a58946a3](https://github.com/horizon-rust/horizon/commit/a58946a3) (setting). Issue #6415 says "never on Metal" -> no M1 gain.
- Metal: [5631f912](https://github.com/horizon-rust/horizon/commit/5631f912) occlusion phase 2 splits draws by pass; [a2d36b2f](https://github.com/horizon-rust/horizon/commit/a2d36b2f) Metal sprite texture array splitting fix (closes #8471, missing block textures with large sprite arrays).
- Async entity occlusion culling + particle culling workers: [9c101044](https://github.com/horizon-rust/horizon/commit/9c101044), [37380065](https://github.com/horizon-rust/horizon/commit/37380065), [7e22c998](https://github.com/horizon-rust/horizon/commit/7e22c998), [7fc42e82](https://github.com/horizon-rust/horizon/commit/7fc42e82), [d3ae3e9f](https://github.com/horizon-rust/horizon/commit/d3ae3e9f) (reuse traversal buffers), [d87992bd](https://github.com/horizon-rust/horizon/commit/d87992bd), [37780269](https://github.com/horizon-rust/horizon/commit/37780269) (Hidden Faces leaf culling mode).
- macOS VSync-off no longer locked to refresh rate (fixes #1333 family): commit titled "macOS: VSync off no longer holds a window to the display's refresh rate" (PR #1415 was closed unmerged; fix landed separately, hash not resolved).
Threading
- [9cfac94b](https://github.com/horizon-rust/horizon/commit/9cfac94b) far-terrain threads at utility QoS on macOS; [0f7f9db8](https://github.com/horizon-rust/horizon/commit/0f7f9db8) step back only while near terrain loads (macOS stayed on E-cores for minutes).
- [893fc9ae](https://github.com/horizon-rust/horizon/commit/893fc9ae) LOD sampler gets 2/3 of cores; [c4bc3a29](https://github.com/horizon-rust/horizon/commit/c4bc3a29) idle generator release; [2a1cfe65](https://github.com/horizon-rust/horizon/commit/2a1cfe65) fixed network thread pool.
Memory (relevant to 8 GB)
- [2c9dac6b](https://github.com/horizon-rust/horizon/commit/2c9dac6b) block sprite CPU copy lz4-compressed after upload (~21 MB); [d8742781](https://github.com/horizon-rust/horizon/commit/d8742781) less atlas memory; [e7bdd164](https://github.com/horizon-rust/horizon/commit/e7bdd164) "Remove the RAM limit" (check what the launcher's Maximum memory does now; [908d81bd](https://github.com/horizon-rust/horizon/commit/908d81bd) keeps Java heap controls).
Shader pipeline (Iris-compat; mostly correctness, some cost)
- [5b58cd73](https://github.com/horizon-rust/horizon/commit/5b58cd73) clouds via gbuffers_textured/basic fallback; [36e330d3](https://github.com/horizon-rust/horizon/commit/36e330d3) timed compute passes and mip chains; [6d40db2b](https://github.com/horizon-rust/horizon/commit/6d40db2b) shadowtex linear sampler; [e2e4df37](https://github.com/horizon-rust/horizon/commit/e2e4df37) shadow pass draws back faces; [51ea650d](https://github.com/horizon-rust/horizon/commit/51ea650d) stitched block atlas for packs; [fc93a1d4](https://github.com/horizon-rust/horizon/commit/fc93a1d4) per-draw uniforms; [b5d03948](https://github.com/horizon-rust/horizon/commit/b5d03948) pack options turn [shadow] map off / pick size.
Tooling: [b0fa8940](https://github.com/horizon-rust/horizon/commit/b0fa8940) scene_replay (offscreen renderer timing), [41cf95bc](https://github.com/horizon-rust/horizon/commit/41cf95bc) GPU memory report.

## 2. Does upstream already do our local patches?
- Skip vanilla cloud geometry when pack disables clouds: PARTIAL / UNVERIFIED. `hides_clouds` (`post.clouds_off || ...`) exists in pack_post.rs at BOTH f42 and main (line 2083 vs 2328), so "don't draw game clouds" is old. No commit found that skips cloud geometry building. Likely still need our patch; diff against main to confirm.
- Reuse shadow-visibility scratch buffers: no matching commit (only [d3ae3e9f](https://github.com/horizon-rust/horizon/commit/d3ae3e9f), which is entity occlusion, not shadow). UNVERIFIED in source; pack_shadow.rs has no scratch/with_capacity hits at f42 or main.
- Metal/wgpu pipeline cache: NO. Only open Vulkan-only issue #8010 (PIPELINE_CACHE; wgpu 30.0.1); DX12 shader cache exists. wgpu pipeline cache is not supported on Metal, so nothing upstream will help.
- Worker thread defaults: only far-terrain/LOD threads changed (QoS utility on macOS, 2/3 samplers). Near-chunk meshing counts: no change found. Possible conflict in crates/horizon-client-render/src/lod.rs and crates/horizon-threads/src/lib.rs if we patched those.

## 3. Known macOS/Metal issues (open unless noted)
- #7870 shaders weird on Mac (M2; Photon renders only in bottom-left quadrant; same family as our right-half artifact). https://github.com/horizon-rust/horizon/issues/7870
- #5042 VSync: 30 fps in fullscreen on M2, 60 windowed; may tie to reduce-fps-when-minimized. https://github.com/horizon-rust/horizon/issues/5042
- #1333 Mac capped at refresh rate with VSync off (drawable acquisition); fix landed per title above.
- #8471 (closed) Metal missing block textures with large sprite arrays -> a2d36b2f.
- #6156 wgpu validation error; #8931 keychain prompt; #4727 launcher hang on macOS 27.2/M4 Max.
- #3397 (closed) M1 Air benchmark of v0.2.95, no 144 cap in real window: https://github.com/horizon-rust/horizon/issues/3397
- No issue found on App Nap or occluded-window presentation stalls (searches: "App Nap OR occluded OR minimized").
- Repo discussions disabled.

## 4. Mod registry / perf-oriented native mods
Registry: https://github.com/horizon-rust/horizon-mods (mods/*.toml, MOD-POLICY.md); schema docs/api/mod-index.md. No Sodium/Lithium/EntityCulling/ImmediatelyFast clones; those roles are built into the engine (async entity/particle occlusion, GPU culling, Hidden Faces). Perf-ish mods: `dynamic_fps_for_rust` (caps FPS unfocused/minimised/battery), `fast_items` (2D item entities), `fps_overlay`, `distant_horizons`, `motion_blur`/`radiant` (visual, cost GPU).
Hook API compat: docs/native-mods.md says a bundle `"hooks": N` runs on any Horizon whose version is N or later, and "a contract is never changed; an incompatible change adds a version" (native-hooks.json). Main docs reference hooks up to 385-409 (API 362 FOV modifier, 372 name tag, 409 stamped). So hooks 359 should remain valid on main. BUT injection-style mixins are pinned to an exact commit (`[compatibility] horizon_revision`), rebuilt on the installed commit; mismatch needs `native-build --allow-version-mismatch`. Our zoom/cem_alias mods using mixins into moved code (e.g. lod.rs, renderer) can fail E_HOOK_UNKNOWN/E_HOOK_VERSION or compile errors. UNVERIFIED: whether our mods use hooks only or mixin targets; also note main ships `native_compute_fov_modifier` (362) which could overlap zoom.

## 5. Recommendation
Stay on f42 for daily play; trial 6475f62 (nightly) in a separate instance, not main.
- Pro: macOS QoS thread fix, Metal sprite-array fix, 21 MB+ atlas RAM savings, VSync-off fix, async entity/particle culling (CPU win on 4 P-cores).
- Con: 2793 commits of churn (1454 of them after the nightly), GPU culling excluded on Metal, no Metal pipeline cache, shader-pack fidelity changes (stitched atlas, back-face shadow pass, compute timing) may add GPU cost on M1, and "Remove the RAM limit" could change memory behavior on 8 GB.
- Risk to local patches: cloud/shadow patches likely rebase cleanly (upstream has no equivalent) but pack_post.rs grew 4656 -> 5492 lines; thread patches may conflict in lod.rs/horizon-threads. Hook API 359 is forward-compatible by contract; verify with a build of zoom/cem_alias on 6475f62 before committing.
- Next step: build 6475f62 with our patches in a scratch worktree, run the existing M1 bench, compare memory (swap) and Mellow artifact (#7870).
Note: search results also show third-party repos (e.g. "Horizon-Offline-Launcher", "Smelt" converters) that are not official; ignored.
