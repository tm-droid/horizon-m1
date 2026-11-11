# Base Horizon tuning — 2026-11-03

Target: M1 Air8GB, official ARM64 nightly c9d474d, Metal, shader OFF/vanilla packs, render12/simulation8, 2560×1440 surface at100% native world scale. User permits normal Xcode/DeviceHub load. This base stage is not a claim of appearance parity with the Java pack stack.

## Important measurement correction

The first worker pair (`base-auto-full-r1`, `base-w3-full-r1`, queue30) and first60FPS pacing pair (`base-cap60-efficient-r1`, `base-cap60-precise-r1`, queue31) completed cleanly, but are **invalid for choosing settings**. Default `inactivityFpsLimit:afk` applies30FPS after60seconds without player input. Control `bench`/`fly` do not exempt themselves. Their apparent worker/pacing regressions therefore cannot support a recommendation. Results retain raw evidence and explicit invalidation.

Corrected runner sets `inactivityFpsLimit:minimized`, exactly as the built-in benchmark does, while leaving the window visible. This is a measurement override rather than a recommendation to render minimized windows. Source conditions and links: [native research](base-native-research-2026-11-03.md).

Earlier Mellow50% runs are separately **visually invalid**: quarter-size world and right-side streaks. They do not demonstrate a quality-preserving FPS gain. Mellow100% is the conservative layout-correct workaround; its shader scaling bug is unresolved.

## Test commands

Each complete pair runs under the original shared queue, owner `minecraft`, with `HORIZON_TEST_QUEUE` set by the queued wrapper. Only one native game runs, on independent copies of the disposable Horizon-Test world. No Java-instance config, mod or world is edited.

```sh
python3 tools/horizon-offline-test.py --case base --resolution-scale 100 --fps-cap 260 --warmup 30 --seconds 30 --flight --workers 0 --label base-auto-full-noafk-r1
python3 tools/horizon-offline-test.py --case base --resolution-scale 100 --fps-cap 260 --warmup 30 --seconds 30 --flight --workers 3 --label base-w3-full-noafk-r1
```

Effective cap260 bypasses the normal limiter when the window is not minimized. Each run records warmup outside the measured interval, a16s flight, before/after GPU and CPU timing, actual workers in console.log, selected packs, screenshots, process CPU/RSS, system-wide swap traffic, pending terrain and post-flight settling time. `wait-ready` alone does not prove equal visible coverage; images/section counts must also be checked. Static samples must cover at least requested seconds minus1; flights must cover at least15s with nonzero frames. Optional diagnostic timeouts remain explicit and prevent CPU/paging attribution from missing snapshots.

## Candidate policy

- Retain native resolution, texture budget, distances, particles/effects and animation; no quality-reduction preset.
- Compare worker counts and60FPS efficient/precise scheduling before changing upload budgets. Upload throttling may hide stalls by delaying terrain.
- No compatible native optimizer was verified in the reviewed registry. No Fabric optimizers installed into Rust. At the initial c9 screening, no newer published prebuilt had been verified; f42 was subsequently installed and tested below. See [source-backed research](base-native-research-2026-11-03.md).
- Mainline resource-overlay improvements may address cold pack startup, but no full-game source rebuild or full52-pack compatibility pass has happened.

## Checks and limits

`python3 -m py_compile tools/horizon-offline-test.py` passed after each runner change. Fresh read-only reviewer found no blocking harness defect; requested image/terrain checks and settling-time recording were incorporated. Subsequent targeted source research found the AFK confound and prompted corrected measurements. No claim that the initial review established performance validity.

The shared queue script was temporarily iCloud-evicted between queues30/31; a documented Foundation download restored the same file. Queue locks/state were not replaced or bypassed. No test launched during that interruption.

## Corrected-run status

The attempts in this subsection produced no validated winner; later accepted measurements follow below. Queue32 (`base-auto-full-noafk-r1`) stopped presenting after about5s of its measured interval and returned zero flight frames, then timed out on the final screenshot; owned client quit0. Queue33's diagnostic app wrapper could not be identified by desktop controls and never passed its visibility gate; client quit0. The wrapper binary was a byte-identical APFS copy of the official client and is not used by the runner.

User then agreed to keep the test window visible. Queue34 (`base-auto-user-visible-r1`) stopped before measurement because the optional process-list snapshot timed out; client quit0. Runner now bounds optional diagnostics and records their failures without suppressing frame/settings failures. Queue35 (`base-auto-user-visible-r2`) verified effective `inactivityFpsLimit:minimized` / `maxFps:260`, but the log stopped at first-frame acquisition and a control action timed out; client quit0. Counterpart runs were not launched after each failed first condition, and queues were released normally.

Both effective-option queries and full-interval guards were added after independent review. A nonzero flight alone is insufficient: an earlier run captured only4.85s of its16s flight. No further blind comparisons should run until actual frame presentation is confirmed. Existing defaults remain in place; no fabricated optimization winner or native mod installation.

## Accepted c9 measurements and baseline choice

Queue37 completed a full-scene offscreen worker comparison after adding the source-derived637-column gate, five stable resident/column samples, quiet observed client stages and no pending uploads/light. Both static scenes contained637 columns,4171 resident sections and393 drawn sections; both images were reviewed. These are renderer-screening results, not on-screen FPS.

| c9 workers | Static avg /1% low | Flight avg /1% low | Columns/backlog immediately after flight | Additional full-terrain wait |
| --- | --- | --- | --- | --- |
|auto7|58.90 /32.49|58.93 /31.18|628 /0|about10.3s|
|3|59.04 /35.93|52.97 /4.81|592 /98|about22.1s|

No useful stationary improvement qualified with three workers, and its flight had substantially worse coverage and a1.35s maximum frame. This one noisy screening pair supports retaining auto, not a universal causal speedup claim. Source review later clarified that c9 can have three separate compute pools; its encoding pool ignores the workers setting. Newf42 uses shared pools, so this choice must be rechecked there.

Queues38/39 completed an on-screen pacing comparison and reverse-order repetition with auto workers/full native resolution/cap60. Every static sample covered20s with the same637/4171/393 column/resident/drawn counts. Each flight covered16s. Display-sleep prevention was active after the user enabled Amphetamine.

| On-screen c9 case | Static avg /1% low | Staticp99 /max ms | Flight avg /1% low |
| --- | --- | --- | --- |
|efficientr1|59.44 /43.13|20.05 /48.50|59.18 /40.10|
|preciser1|59.18 /53.75|18.43 /19.41|59.08 /50.51|
|preciser2|57.54 /26.66|30.94 /56.15|55.85 /17.73|
|efficientr2|59.12 /31.78|20.60 /59.09|59.16 /35.94|

Precise did not provide a repeatable win. Background load varied materially: initial full-terrain readiness ranged31–225s, and swap occupancy changed across cases. Retain efficient. Flight coverage varied, so flight FPS is streaming-stress evidence rather than equal-geometry throughput. No percentage gain or uncapped on-screen maximum is established by these cap60 tests.

The conservative isolated base profile is `outputs/horizon-runtime/game`: native100%, auto workers, efficient pacing, cap60/VSyncfalse, render12/simulation8 and `inactivityFpsLimit:minimized`. The latter prevents the observed60-second AFK cap while allowing minimized-window throttling. Java's files/settings were not edited. Textures/effects/distances were not reduced. Mellow remains unselected for this base stage.

## New-build priority and concurrent work

A new official nightly appeared during this pass: f42ef42 (2026-11-03), with shared compute pools and renderer/light/cache memory improvements. These are a more relevant engine candidate than further c9 micro-tuning. Its official ARM64 archive SHA256 is58432a760b6af8195a543b520daea89be9396a76633753db61eae3553b762593. The archive was verified and staged separately, preserving c9. Initial extraction retained a single `horizon-macos-arm64/` payload prefix; that was diagnosed/normalized before any executable ran. Detailed metadata is in the new version's runtime-record.json. Preparation and validation status must be read there; c9 conclusions are not automatically f42 results.

The user requested parallel source/converter work and briefly played Java. No test/preparer was running when play began; queues were idle. Device-heavy work resumed only after the user clarified they were done. Mellow-specific adapter work was stopped before any files were changed. Native compatibility and everyday-use audits now take priority over a chosen shader, alongside reusable runtime-provenance/CEM checks.

## f42 on-screen validation — 2026-11-04

The isolated preferred runtime is now the verified official f42 build. Its resources were prepared successfully in queue42. Queue44 compared full-terrain f42 and c9 scenes at native resolution, 12/8 distances, auto workers, efficient pacing and cap60. Both images showed the complete scene. These first comparisons used vanilla FOV70; later cow checks use the actual Java FOV95 and cloud range64.

| Case | Static average / 1% low FPS | Static p99 / maximum ms |
| --- | --- | --- |
| f42-base-full-r1 | 59.99 / 55.55 | 17.55 / 20.20 |
| c9-base-control-r3 | 59.74 / 53.30 | 17.98 / 27.29 |
| f42-cow-base-sourceopts-r1 | 60.00 / 57.13 | 17.29 / 18.43 |
| f42-cow-fa-sourceopts-r1 | 59.99 / 57.13 | 17.19 / 19.27 |

The f42 base flight sustained60FPS with a54.08FPS 1% low in this capped run. This supports continuing with the newer build; it does not establish maximum uncapped FPS or a universal performance improvement. Cold startup was not faster: full-scene readiness took60.94s for f42 versus46.23s for this c9 control. Shared pools and memory changes are verified source changes, while their effect on this laptop remains workload-dependent.

Queue46 used the same fixed, server-confirmed NoAI cow, camera and visual settings for vanilla and unchanged Fresh Animations. The FA cow showed distinct geometry/pose while maintaining the cap. This is a useful smoke check, not proof of every entity animation, texture condition or pack interaction. FA emitted133 CEM warnings; a source audit traced most to shared model-binding aliases and a source-only patch is under review. No pack assets were rewritten to hide the warnings.

The user prefers combined-stack checks. Subsequent acceptance loads the selected packs together, groups actionable failures and isolates components only when needed. Subjective visual differences can be reviewed by the user later. No exhaustive mod-by-mod runtime test requirement is imposed.
