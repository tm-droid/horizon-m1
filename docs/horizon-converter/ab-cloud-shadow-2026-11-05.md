# A/B: control vs M1 candidate (cloud-prep + shadow-scratch), 2026-11-05

Status: INCOMPLETE. Shader-off arm complete (4 runs per build). MakeUp arm has 2 runs per build (ABBA done, BAAB not run). The matrix aborted at run 13 (see Abort).

Raw data: `outputs/horizon-runtime/m1-performance-matrix-r2.json` (per run, incl. gate/swap/window state), derived `m1-performance-matrix-r2-analysis.json`, tooling `run-m1-performance-matrix.py` (extended; backup `.bak-2026-11-05`) and `analyze-ab-r2.py`.

## Setup
- Control `native-f42-m1-control-09391c2a8210`, candidate `native-f42-m1-b6f52e288ed1`. Cow scene, 2560x1440 surface (1280x720 window at 2x), RD 12 / sim 8, cap 260 (Unlimited), VSync off, warmup 15 s, static 20 s, flight 16 s. Flight capture is now "settled" (waits for terrain), so post-flight settle is measured; the earlier r1 used "endpoint".
- Run via device queue with `/usr/local/bin/python3` (the only python with Quartz; window state needs it). Safety gate (AC, unlocked, no xcodebuild/cargo/rustc, no PineconeMC) passed before every run.
- Swap was 2.5 to 3.0 GB used of 4096 MB for all runs (system was already swapping before the runs; shader-off 2.56-2.80 GB, MakeUp 2.80-3.02 GB). Treat absolute numbers as noisy.
- Noise = max of the two builds' own min-max range. "Significant" = |median delta| > noise.

## U4 harness verification
Two makeup/control runs (`m1-performance-matrix-u4.json`) both passed: flight presented 15.99 s and 16.03 s, no `front_error`, Horizon was frontmost, one flight attempt each, static 20.0 s. Fix works.

## Which patch can show an effect
- Cloud-prep triggers only when the Iris pack declares `clouds=off`. MakeUp 9.6 sets `clouds = off` whenever `V_CLOUDS > 0`; the saved setting is `V_CLOUDS=2`, so it is exercised in the MakeUp arm. The shader-off arm has no Iris pack, so it is not exercised.
- Shadow-scratch needs a shadow pass. Console log of MakeUp runs: terrain, translucent terrain, entities and block entities cast shadows, shadow map 840x840. Exercised in MakeUp only. Shader-off draws no shadows.
- The shader-off arm therefore acts as a control for binary/layout side effects: any shader-off delta is not caused by either patch.
- Both patches ship in one candidate, so this A/B cannot attribute an effect to one patch alone.

## Results (median [min-max], candidate minus control)
Shader-off full 52-pack stack, n=4 per build:

| metric | control | candidate | delta | noise | sig |
|---|---|---|---|---|---|
| static avg FPS | 128.0 [115.6-155.6] | 136.4 [117.3-154.4] | +8.4 | 40.0 | no |
| static 1% low | 44.5 [41.9-54.0] | 48.9 [42.2-53.5] | +4.3 | 12.1 | no |
| static p99 ms | 21.5 [17.9-21.8] | 19.2 [17.7-22.6] | -2.3 | 4.9 | no |
| static CPU ms | 3.08 [2.79-5.97] | 3.81 [3.36-6.22] | +0.73 | 3.2 | no |
| static GPU ms | 8.58 [7.12-9.01] | 7.60 [6.64-9.04] | -0.99 | 2.4 | no |
| flight avg FPS | 111.0 [101.4-137.7] | 119.8 [105.7-136.4] | +8.8 | 36.3 | no |
| flight 1% low | 35.5 [22.2-40.8] | 39.4 [33.4-42.4] | +3.9 | 18.6 | no |
| flight p99 ms | 26.5 [22.0-27.9] | 23.6 [21.0-27.0] | -3.0 | 6.0 | no |
| flight CPU ms | 2.73 [2.10-5.31] | 3.92 [2.33-4.63] | +1.18 | 3.2 | no |
| flight GPU ms | 10.19 [8.34-10.71] | 9.11 [7.72-10.72] | -1.08 | 3.0 | no |
| settle s (full) | 5.99 [4.18-9.55] | 7.39 [5.68-15.53] | +1.40 | 9.9 | no |

MakeUp 9.6, n=2 per build (ABBA only; ranges of 2 samples understate noise):

| metric | control | candidate | delta | noise | sig |
|---|---|---|---|---|---|
| static avg FPS | 33.7 [32.2-35.3] | 35.5 [34.9-36.2] | +1.8 | 3.1 | no |
| static 1% low | 22.31 [22.21-22.41] | 23.14 [23.04-23.24] | +0.83 | 0.20 | yes (n=2) |
| static p99 ms | 43.4 [43.4-43.4] | 41.3 [40.6-42.0] | -2.2 | 1.4 | yes (n=2) |
| static CPU ms | 7.47 [7.12-7.82] | 7.47 [7.23-7.70] | 0.00 | 0.70 | no |
| static GPU ms | 28.97 [27.62-30.32] | 27.36 [26.99-27.74] | -1.6 | 2.7 | no |
| flight avg FPS | 25.6 [24.4-26.8] | 25.5 [25.2-25.8] | -0.08 | 2.4 | no |
| flight 1% low | 18.7 [18.0-19.4] | 18.2 [17.8-18.6] | -0.48 | 1.4 | no |
| flight p99 ms | 52.5 [49.7-55.3] | 52.0 [51.4-52.6] | -0.5 | 5.5 | no |
| flight CPU ms | 9.99 [7.84-12.13] | 10.21 [9.89-10.53] | +0.22 | 4.3 | no |
| flight GPU ms | 37.6 [36.0-39.2] | 37.7 [37.3-38.1] | +0.04 | 3.2 | no |
| settle s (full) | 9.95 [9.43-10.47] | 15.35 [14.62-16.08] | +5.4 | 1.5 | yes (n=2), worse |

Reading: GPU-bound (GPU ms ~29 static vs CPU ~7.5), so a CPU-side saving would not show in FPS. Shader-off is dominated by run-to-run noise (FPS range of 40). The only "significant" MakeUp items are static tails (small gain) and slower post-flight settle (regression), all from two samples per build. Not trustworthy until the BAAB half is run.

## Visual parity (scene.png, pixel diff %)
Same-build baseline shows how much differs run to run anyway.
- Shader-off: control vs candidate 4.36% pixels differ (>8/255: 1.84%); across all 16 pairs 2.7-4.5%. Baseline control vs control 3.13%, candidate vs candidate 4.26%. Candidate is inside baseline noise: no visible parity loss.
- MakeUp: control vs candidate 95.9% differ (>8/255: 26.9%, mean abs 6.9); all pairs 92.9-96.1%. Baseline control vs control 96.1% (26-30%), candidate vs candidate 93.8%. The shader output differs between any two runs (animated sky, temporal effects), so pixel diff cannot show parity here. Inconclusive, not a failure.

## Verdicts (provisional)
- cloud-prep: NO EFFECT measurable (exercised only in MakeUp; no significant avg FPS/CPU/GPU change; GPU-bound).
- shadow-scratch: NO EFFECT measurable (exercised only in MakeUp; the sub-ms CPU saving is hidden by GPU bound and noise). Small static-tail gain is n=2 and unconfirmed.
- Combined candidate: no REJECT evidence on FPS/visuals. One flag: MakeUp post-flight settle slower by 5.4 s (n=2). Needs the BAAB half to confirm or dismiss.

## Abort
Run 13 (makeup candidate, first of BAAB) was tainted: console log shows "motion input from a person while an agent was driving" (a person was at the Mac). The runner redid it once; the redo failed because `tests/base-smoke/saves/Horizon-Test` (the seed world the harness copies) no longer exists. The `base-smoke` and `base-auto-offscreen-r1` directories were modified at 21:02, between run 13 and its redo, while I was running nothing else. Something outside this A/B removed the seed world. I did not recreate it; the fixture must match earlier runs. Disk is also at 98% (4.2 GiB free; the runner requires 4 GiB).

To finish: restore or regenerate `tests/base-smoke/saves/Horizon-Test`, free disk, then run makeup BAAB (candidate, control, control, candidate) with a new tag and merge with runs 9-12.
