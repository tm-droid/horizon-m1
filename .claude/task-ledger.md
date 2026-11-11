# Goal: Horizon tuned for MacBook Air M1 8 GB/60 Hz; native mods vs ours compared; launcher tuned; daily8 selected only if it beats daily7; Amphetamine fully off.
Plan: ~/.claude/plans/make-my-horizon-super-cozy-crescent.md

## Rules (every unit)
- 8 GB RAM: builds, benches, game sessions strictly one at a time.
- Before settings change: `tools/config-sync.sh snapshot` + commit. Commit only, never push. Public repo: no accounts.json, servers.dat, chat logs, tokens, email.
- Build needs >=8 GiB free (delete native/target.noindex/fast/incremental or old build dirs if low).
- Adopt only if median of >=3 runs gains >=2% avg FPS or 1% low, no metric regresses >2%, gallery 0 fails, no new log errors, no visible diff.

## Units
- [ ] U1: baseline daily7 bench (makeup + packs x3), bench.py daily7 entry + env.K=V variants | files: outputs/bench-2026-11-10/bench.py, runs/ | done when: runs/*.json for daily7 both scenarios
- [x] U2: native-mod comparison (upstream catalog vs ours) | files: docs/research/native-mods-compare-2026-11-11.md, mods.lock.tsv | done when: doc with adopt/drop list; minimap hash fixed
- [x] U3: upstream perf since fdc87ae ranked | files: docs/research/upstream-perf-2026-11-11.md | done when: doc with ranked candidates
- [ ] U4: M1 build profile (thin LTO, cgu=1, target-cpu=apple-m1) | files: outputs/horizon-runtime/build-fast-fdc87ae.py, new patch | done when: build rc 0 + bench + verdict
- [ ] U5: runtime knob sweep | files: config, bench runs | done when: winners table here
- [ ] U6: MakeUp tierA + MATERIAL_GLOSS + resolutionScale | done when: adopted or rejected w/ numbers + gallery
- [ ] U7: off-stack + upstream patch candidates -> daily8 stack | done when: daily8-stack.txt + bench per candidate
- [ ] U8: frame bubble (HORIZON_SUBMIT_THREAD, drawables) | done when: verdict w/ numbers
- [ ] U9: launcher tune (native_cache_gib 8, env persistence) | done when: `horizon-launcher settings` shows values
- [ ] U10: final daily8 build, gallery, bench vs daily7, 10-min soak, select, report docs/m1-tune-2026-11-11.md | done when: report + selection
- [ ] U11: Amphetamine off (end session, quit, CDMManager.app, SleepDisabled 0) | done when: pmset checks pass

## Decisions
- Builds based on fdc87ae stack; daily7 stays installed as rollback.
- U7 candidates from U3: backport 2a33c013, 562175df, 81a8d04a, 203b3ac8, 89733192; A/B revert 6a8ea6fc (shadow near/far cull, top MakeUp regression suspect) and samplers back to Nearest (8794c49a, 4c0ef1d7). Skip 957ecaff, 5ec521bb, 4a701935.

## Log
- 2026-11-11 U3 done: docs/research/upstream-perf-2026-11-11.md; nightly still fdc87ae (2026-11-08), main f23176af +4947; BACKPORT 2a33c013, 562175df, 81a8d04a, 203b3ac8, 89733192; suspects 6a8ea6fc (shadow cull), 8794c49a+4c0ef1d7 (trilinear samplers), 3c794c28; 957ecaff (#12448 fix) SKIP, 4a701935 moot
- 2026-11-11 U2 done: docs/research/native-mods-compare-2026-11-11.md; ADOPT zoomify (MCRE pin ok), official minimap, dynamic-fps (idle cap off), BetterDynamicLights 1.0.3 non-shader only; DROP zoom-pilot, fast-items, dynamic-fps-f42 patch, fps_overlay; only MCRE-Mods has newer commits (23, none in dirs we use); daniliammo hash already 40 chars and = local HEAD, upstream repo 404, lock unchanged
