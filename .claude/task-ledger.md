# Goal: Horizon tuned for MacBook Air M1 8 GB/60 Hz; native mods vs ours compared; launcher tuned; daily8 selected only if it beats daily7; Amphetamine fully off.
Plan: ~/.claude/plans/make-my-horizon-super-cozy-crescent.md

## Rules (every unit)
- 8 GB RAM: builds, benches, game sessions strictly one at a time.
- Before settings change: `tools/config-sync.sh snapshot` + commit. Commit only, never push. Public repo: no accounts.json, servers.dat, chat logs, tokens, email.
- Build needs >=8 GiB free (delete native/target.noindex/fast/incremental or old build dirs if low).
- Adopt only if median of >=3 runs gains >=2% avg FPS or 1% low, no metric regresses >2%, gallery 0 fails, no new log errors, no visible diff.

## Units
- [x] U1: baseline daily7 bench (makeup + packs x3), bench.py daily7 entry + env.K=V variants | files: outputs/bench-2026-11-10/bench.py, runs/ | done when: runs/*.json for daily7 both scenarios
- [x] U2: native-mod comparison (upstream catalog vs ours) | files: docs/research/native-mods-compare-2026-11-11.md, mods.lock.tsv | done when: doc with adopt/drop list; minimap hash fixed
- [x] U3: upstream perf since fdc87ae ranked | files: docs/research/upstream-perf-2026-11-11.md | done when: doc with ranked candidates
- [x] U4: M1 build profile (thin LTO, cgu=1, target-cpu=apple-m1) | files: outputs/horizon-runtime/build-fast-fdc87ae.py, new patch | done when: build rc 0 + bench + verdict
- [x] U5: runtime knob sweep | files: config, bench runs | done when: winners table here
- [ ] U6: MakeUp tierA + MATERIAL_GLOSS + resolutionScale | done when: adopted or rejected w/ numbers + gallery
- [x] U7: off-stack + upstream patch candidates -> daily8 stack | done when: daily8-stack.txt + bench per candidate
- [ ] U8: frame bubble (HORIZON_SUBMIT_THREAD, drawables) | done when: verdict w/ numbers
- [ ] U9: launcher tune (native_cache_gib 8, env persistence) | done when: `horizon-launcher settings` shows values
- [ ] U10: final daily8 build, gallery, bench vs daily7, 10-min soak, select, report docs/m1-tune-2026-11-11.md | done when: report + selection
- [ ] U11: Amphetamine off (end session, quit, CDMManager.app, SleepDisabled 0) | done when: pmset checks pass

## Decisions
- Builds based on fdc87ae stack; daily7 stays installed as rollback.
- U7 candidates from U3: backport 2a33c013, 562175df, 81a8d04a, 203b3ac8, 89733192; A/B revert 6a8ea6fc (shadow near/far cull, top MakeUp regression suspect) and samplers back to Nearest (8794c49a, 4c0ef1d7). Skip 957ecaff, 5ec521bb, 4a701935.
- U2 verdict: keep current mod set (no feature loss: daniliammo waypoints, zoom on C, fps_overlay). Not adopting Zoomify/official Minimap/BetterDynamicLights (no perf gain; dynlights no effect under MakeUp). daniliammo upstream 404 -> local clone backed up outside repo. Particle culling upstream vs ours -> bench in U5.
- U5 base: F7 (daily7) stays base. Makeup pooled n=6 each: F8M static 1%low -2.2%, flight 1%low -7.1%, flight avg -1.9% vs F7 (noise ~+-2 fps; u5a block alone favoured F8M). 
- U5 winners (makeup, base F7): ONLY gfx.uploadBudgetKiB=4096: flight 1%low +9.5%, p99 -10.1%, avg +1.7%, RSS +3.1% (n=6 pooled); packs flight 1%low -7.9% (2/6 hitches) so conditional. Rejected: workers 3 (RSS +13.8%), 4 (not robust; combo w4+upl flight 1%low -12.5%), 5, HORIZON_WORKER_THREADS=6 (flight avg -10%), chunkUpdates=6 (flight run invalid), HORIZON_MEMORY_LIMIT_MB=4800, particleCulling=async (flight avg -8%). MIMALLOC_PURGE_DELAY: no-op (code sets purge delay 0 at startup). Env persistence: `horizon-launcher instance launch horizon --env "K=v"` (instances.json launch.env); RAM slider -> launch.memory_limit_mb -> HORIZON_MEMORY_LIMIT_MB. Details: outputs/bench-2026-11-10/u5-sweep-NOTES.md

- U4 m1prof + U7b invalid (unpatched; build script silently skipped patches, see outputs/horizon-native/u7c-rebuild-diff.md); redo.

## Log
- 2026-11-12 U7e BLOCKED: screen locked 05:02-07:53+ (no frames presented, benches invalid). Built STK/NOP/NOV/NOU variants (rc0) ready in versions/; resume cmds in outputs/horizon-native/u7e-bisect.md. U7c commit 0bfea4b; dragon check pending.
- 2026-11-11 U3 done: docs/research/upstream-perf-2026-11-11.md; nightly still fdc87ae (2026-11-08), main f23176af +4947; BACKPORT 2a33c013, 562175df, 81a8d04a, 203b3ac8, 89733192; suspects 6a8ea6fc (shadow cull), 8794c49a+4c0ef1d7 (trilinear samplers), 3c794c28; 957ecaff (#12448 fix) SKIP, 4a701935 moot
- 2026-11-11 U2 done: docs/research/native-mods-compare-2026-11-11.md; ADOPT zoomify (MCRE pin ok), official minimap, dynamic-fps (idle cap off), BetterDynamicLights 1.0.3 non-shader only; DROP zoom-pilot, fast-items, dynamic-fps-f42 patch, fps_overlay; only MCRE-Mods has newer commits (23, none in dirs we use); daniliammo hash already 40 chars and = local HEAD, upstream repo 404, lock unchanged
- U1: bench.py +F7 (env.K=V already supported); baseline tag u1 x3 makeup/packs valid; medians static avg/1%low: makeup 44.1/27.7, packs 85.6/32.5; env plumbing verified via ps eww (WORKER_THREADS=6).
- U4: m1 profile built (726 s, 77.1 MB vs 89.7); packs +16-18% avg, makeup flight -4%/1%low -21% (likely noise): REJECT by rule, rerun makeup advised; see outputs/horizon-runtime/m1-profile-NOTES.md
- U7a: candidates prepared: up-frustum-regions, up-mesh-backlog, up-flat-bindgroups, up-cloud-reupload, up-sky-octagon (+ A/B ab-shadow-cull-revert, ab-nearest-samplers; off-stack thread-cap/dimension-warm/gpu-a/gpu-e re-checked) all apply on daily7 alone+combined, uncompiled; see outputs/horizon-native/u7-candidates.md, daily8-cand-stack.txt
- 2026-11-12 U5 done: runs u5a-u5d (52-106); base F7; sole winner uploadBudgetKiB=4096 (makeup flight 1%low +9.5%, packs risk); see u5-sweep-NOTES.md
- 2026-11-12 U7b done: d8cand built (rc0, tests = daily7 baseline fails), D8C vs F7 n=4: makeup avg +0.3%, flight 1%low +4.0%, packs avg +17% but D7N rebuild control shows same +17% (rebuild of daily7 stack differs from installed daily7, dragon renders blue; investigate in U10); ADOPT all 9 in daily8-stack.txt (build with --only daily8-mods-only.txt, official minimap leaked in via mods.lock); A/B shadow-cull-revert and nearest-samplers REJECT (no GPU gain); see outputs/horizon-native/u7b-results.md
