# U7b results: daily8 candidates built and benched

Machine: M1 Air 8 GB. Bench: outputs/bench-2026-11-10/bench.py, interleaved, n=4 per build, medians. Base F7 = installed daily7.
Runs: runs/u7a..u7f-*.json (indices 107-201).

## Builds
- d8cand (daily7 + 5 upstream + thread-cap, dimension-warm, gpu-a, gpu-e): compiled first try, rc 0, 396 s. No patch fixes needed. All 9 candidates kept.
- `--tests`: 6 failures (crash x2, native_hooks, 3 terrain/pack_post GPU tests) = identical set and counts (1272/1648 pass) to a fresh daily7-stack test run. No new failures from candidates.
- Confounder found: the builds first included official `minimap` 2.0.0 (U2 changed mods.lock.tsv), contrary to the U2 decision. All later builds use `--only` with the 16 daily7 mods (daily8-mods-only.txt). Builds that ever included it (d8cand/d8up/d8off) were only used for bisect, results below are from minimap-free builds.
- Second confounder: a REBUILD of the unchanged daily7 stack (D7N) is not identical to the installed daily7 (patched_tree_digest differs; cause not found). It benches +17.6% avg on packs (GPU 13.3 -> 11.2 ms) and renders the ender dragon as a flat light-blue silhouette instead of dark. D8C equals D7N on packs. So the packs gain is NOT from the candidates. Needs a look before U10 (what differs from installed daily7).

## D8C (minimap-free full candidate stack) vs F7 and D7N (u7e, n=4)
| scenario | build | st avg | st 1%low | fl avg | fl 1%low | fl p99 ms | gpu ms | RSS MB |
|---|---|---|---|---|---|---|---|---|
| makeup | F7 | 44.0 | 28.8 | 41.2 | 25.3 | 36.2 | 20.38 | 1614 |
| makeup | D7N (rebuild ctl) | 44.0 | 27.5 | 41.2 | 24.5 | 38.5 | 20.39 | 1595 |
| makeup | D8C | 44.2 | 29.0 | 41.3 | 26.3 | 35.9 | 20.41 | 1563 |
| packs | F7 | 85.9 | 33.2 | 86.0 | 32.4 | 28.0 | 13.29 | 1424 |
| packs | D7N | 101.0 | 35.0 | 99.0 | 34.0 | 27.4 | 11.15 | 1470 |
| packs | D8C | 101.0 | 34.1 | 98.6 | 32.1 | 29.1 | 11.16 | 1376 |

D8C vs F7: makeup avg +0.4% / +0.1% (static/flight), 1%low +0.7% / +4.0%, RSS -3.1%; packs avg +17.5% / +14.7%, 1%low +2.7% / -1.0%, RSS -3.4%.
Rule: flight 1%low >= +2%, nothing >2% worse in makeup, packs not >5% worse, RSS fine -> ADOPT by the letter. Honest read: makeup is GPU-bound (20 ms GPU vs 6 ms CPU), candidates change nothing in GPU time, 1%low gain is inside noise (+-15%). Packs gain is the rebuild effect (D8C = D7N). Cheap and safe to include; no real speedup shown.
Earlier runs (u7a, with minimap mod): makeup static 1%low -6.1%, others flat. Bisect (u7b makeup, n=4): upstream-5 half flight 1%low +5.7%, off-stack-4 half -1.3%, nothing >2% worse in either; static/avg flat. No culprit found; the u7a dip was noise.
Gallery (28 flagged-mob shots): 0 failures. Only visible difference vs installed daily7 is the dragon (blue), reproduced by D7N and every rebuild, not by the candidates. Wither/other shots match.

## A/B (makeup, vs D8C, u7f n=4)
| build | st avg | st 1%low | fl avg | fl 1%low | fl p99 | gpu ms | RSS |
|---|---|---|---|---|---|---|---|
| D8C | 44.0 | 28.6 | 41.0 | 23.5 | 37.9 | 20.34 | 1544 |
| D8SHADOW (shadow cull revert) | 44.1 | 29.1 | 40.9 | 21.9 | 40.5 | 20.35 | 1539 |
| D8NEAR (nearest samplers) | 44.1 | 26.9 | 40.7 | 20.9 | 46.5 | 20.08 | 1501 |
- ab-shadow-cull-revert: GPU time unchanged (20.35 vs 20.34 ms), avg flat, flight 1%low -7.0%. Gallery 28/0 fails, shadows identical (wither floor shadow same). REJECT: no gain, so 6a8ea6fc is not the MakeUp regression.
- ab-nearest-samplers: GPU -0.26 ms only, avg -0.7%, flight 1%low -11.1%, p99 +22.5%. Gallery 28/0, no visible sharpness change at normal view. REJECT: no gain. (Its 2 mip tests not run.)

## Verdict
daily8-stack.txt = daily8-cand-stack (all 9 candidates), build with `--only $(cat daily8-mods-only.txt)`. Neither A/B patch adopted. The MakeUp GPU regression since fdc87ae is not explained by shadow cull or sampler filter.
