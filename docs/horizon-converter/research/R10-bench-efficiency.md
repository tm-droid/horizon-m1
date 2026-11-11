# R10: cutting Horizon bench runs for the same confidence (2026-11-06)

Scope: fanless M1 Air, paired A/B, ~2.5-3 min per run. Nothing existing was modified. All numbers marked [data] come from `outputs/horizon-runtime/r3-bisect-r3b.json` (24 valid runs, n=4 per arm: small, treat as order-of-magnitude). Numbers marked [src] come from reading `candidate-source`. Numbers marked [est] are my estimates and need a pilot.

Baseline cost: "57 runs/arm for 10 FPS shader-off" is an unpaired figure = 114 runs = ~5.2 h.

## Summary table (ranked by saving per effort)

| # | Proposal | Effort | Est. saving | Applies to |
|---|----------|--------|-------------|-----------|
| 1 | Use flight avg FPS (not static avg FPS) as the primary shader-off metric | analysis only | 10-30x fewer runs for that metric [data] | all A/B, incl. build A/B |
| 2 | Within-run live A/B (ABBA blocks inside one process) | new driver ~80 lines, +1 optional control cmd | 4-8x fewer launches for toggleable changes [est] | options/culling/RD/clouds, not binary A/B |
| 3 | Sequential testing (always-valid CI, stop per pair) | analysis ~40 lines | 30-60% of runs when effect is large; 0% for true nulls [est] | all |
| 4 | Cut fixed cost: several scenes per launch, shorter static, auto warmup | driver | 15-35% wall time [est] | all |
| 5 | Save per-frame series (works today) + cluster bootstrap, pooled tails | analysis | 1.5-2x for p99/1%-low questions, 0 for means [est] | tail metrics |
| 6 | CUPED / detrend on run index, swap, warmup FPS | analysis | 10-30% [data+est] | all, on top of pairing |
| 7 | GPU-ms as primary metric | none | no saving found [data]; keep as diagnostic | n/a |

## 0. Findings from existing data that drive the ranking

[data] Per-arm coefficient of variation (CV) of run-level means, 4 runs per arm:

| case | static avg FPS CV | static GPU avg-ms CV | flight avg FPS CV | flight avg FPS SD |
|------|------------------|----------------------|-------------------|-------------------|
| makeup (3 arms) | 3.1-3.5% | 2.9-3.3% | 0.7-1.7% | 0.2-0.6 FPS |
| packs/shader-off (3 arms) | 3.1-10.8% | 4.8-8.8% | 0.3-2.4% | 0.5-3.5 FPS (at ~146 FPS) |

- The "SD 19" shader-off noise is a property of the static 20 s window (175 FPS, uncapped). The 16 s flight on the same runs has about 5-20x lower SD. The camera path is deterministic, so the flight workload repeats; the static window is a free-running idle scene where the SoC DVFS/thermal state shows through.
- Pairing already helps: paired-delta SD vs sqrt2 x single-run SD: makeup 0.6 vs 1.8 (rho ~0.9), packs 11.0 vs 17.7 (rho ~0.6). Round means of the arm-demeaned shader-off FPS were -0.7, +13.8, +2.6, -15.7: a large shared round effect (drift), which is what pairing cancels.
- Run order matters: FPS vs run index within case: slope -0.14 FPS/run (makeup), -0.89 FPS/run (packs). Linear detrend cut SD 1.3 -> 0.9 (makeup), 12.5 -> 10.8 (packs). swap_before vs FPS: r=+0.71 makeup, +0.07 packs (confounded with time).
- GPU ms is not a quieter metric here. Makeup: corr(static FPS, GPU avg ms) = -0.98, so it carries the same information with the same noise (CV 3%). Shader-off: corr = +0.84 (wrong sign for a cost metric: faster frames show more GPU-busy time), CV 5-9%. Pass timings from `gpu-passes on` are for attribution.
- Frame-level lag-1 autocorrelation of flight frame_ms is -0.23 (n~1450 frames). Frames inside a run are not the bottleneck: the run (process) is the independent unit. More frames per run, or more blocks per run, do not shrink between-run variance. Only changes that remove between-process variance help (proposal 2).
- Time budget [est]: a run is ~165 s; the in-scene part is 15+20+16 s warmup/static/flight plus 30 s cooldown = ~81 s, so ~85 s is launch + world load + shutdown. Fixed cost per launch dominates; amortizing it is worth more than shortening windows.

## 1. Primary metric: flight avg FPS (and flight GPU/CPU ms)

Already in every result (`flight.avg_fps`, `flight.gpu.avg_ms`, `flight_frame_ms` series). Zero harness change.

Power with the pooled flight SD ~1.5 FPS (packs, n=4/arm [data], so tentative):
unpaired runs per arm = 2 x 7.84 x SD^2 / delta^2 = 15.7 x 2.25 / delta^2: delta 10 -> 0.4 (so 2-3 min), delta 3 -> 3.9, delta 2 -> 8.8. Versus 57/arm for static at delta 10. The static 10 FPS question becomes a 3-run-per-arm question.

Must validate before trusting (cheap, do it first):
- Sensitivity: flight is partly streaming-bound, so it may under-respond to pure render changes. Use positive controls that already exist live: `render-distance 12` vs `8`, `options-set renderClouds` on/off, `gpu-culling` on/off. If flight FPS moves by a similar relative amount as static, accept it.
- A/A: 8 runs of one build, report flight CV. Expect <2%.
- Report both; gate on flight, keep static as a secondary sanity check.

Saving: for the shader-off headline, ~114 -> ~8-16 runs (90%+) [data, tentative].

## 2. Within-run A/B via the control socket

What the socket supports today [src: crates/horizon-client/src/game/control.rs, options.rs, bin/horizon-ctl/commands.rs]:

| command | live toggle? | note |
|---------|--------------|------|
| `options-set KEY VALUE` | yes, applied at once, writes options.txt | any options.txt key: maxFps, enableVsync, renderClouds, cloudRange, resourcePacks (triggers reload_packs), etc. Harness already uses it for vsync. |
| `render-distance N` | yes | |
| `gpu-culling on/off` | yes | `set_gpu_culling` (gfx.rs:4499) |
| `section-cull on/off`, `section-sides on/off` | yes | |
| `gpu-passes on/off` | yes | timestamp queries; leave one setting fixed for both arms because the timing itself costs |
| `stats [reset] [raw]` | n/a | `raw` returns frame_ms, cpu_ms, gpu_ms series |
| `bench S` | n/a | reset, wait, summary only. No raw series. |
| `HORIZON_GPU_CULL` (occlusion cull, `cull.always`) | no: env read once in renderer init (gfx.rs:3940) | needs a new command |
| shader pack choice | no clean command: harness writes `horizon-graphics.txt` pickedShaderPack, or UI page `shader-packs` | needs a new command |
| binary A vs B | no | cannot be toggled in-process |

So proposal 2 covers option/feature A/Bs. It does not cover control-vs-r3 build comparisons. For those, use proposals 1, 3, 4.

Design: one launch, `warmup`, then blocks of ~10 s measure after ~3 s settle, order A B B A B A A B (ABBA/BAAB). Per-block pair delta, run-level delta = mean over pairs, and the process-level variance cancels because both arms share the process, window, memory layout and nearly the same thermal state. Time per launch for 4 pairs: ~85 s fixed + 15 s warmup + 8 x 13 s = ~205 s, giving 4 pairs, against ~4 launches x 2 arms x 165 s = 1320 s for the same 4 pairs today. About 6x less wall time at equal pair count; the paired noise should also be lower than the 0.6-11 FPS SD seen for adjacent-process pairs [est: A/A pilot of 6 launches decides].

Risks: toggle hysteresis (pipeline compiles, cache warmup, resource-pack reload takes seconds), so: discard the first 3 s after each switch, include A/A blocks in every launch to estimate the residual order effect, and treat anything with |A/A delta| > noise as a failed run.

Sketch (new file, do not edit the existing harness; copy its launch lines 203-212 and `ctl` from tools/horizon-offline-test.py):

```python
# tools/horizon-live-ab.py  (sketch)
import json, subprocess, time, statistics as st

def make_ctl(release, sock):
    def ctl(*a, timeout=30):
        r = subprocess.run([f"{release}/horizon-ctl", "--socket", sock, "--timeout", str(timeout), *map(str, a)],
                           capture_output=True, text=True, timeout=timeout + 5)
        v = json.loads(r.stdout)
        if r.returncode or "error" in v: raise RuntimeError(v)
        return v
    return ctl

ARMS = {  # arm -> list of control commands that put the game in that state
    "cull-on":  [("gpu-culling", "on")],
    "cull-off": [("gpu-culling", "off")],
}
ORDER = ["A","B","B","A","B","A","A","B"]          # ABBA BAAB

def measure(ctl, secs=10, settle=3):
    ctl("wait", int(settle * 20))                  # ticks
    ctl("stats", "reset")
    ctl("sleep", secs)                             # 'sleep' is local to horizon-ctl
    s = ctl("stats", "raw")                        # summary + frame_ms/cpu_ms/gpu_ms
    return {"avg_fps": s["avg_fps"], "p99_ms": s["p99_ms"], "gpu": s["gpu"]["avg_ms"],
            "frame_ms": s["frame_ms"]}             # keep series for proposal 5

def run_blocks(ctl, a_cmds, b_cmds):
    out = []
    for blk, which in enumerate(ORDER):
        for c in (a_cmds if which == "A" else b_cmds): ctl(*c)
        out.append({"blk": blk, "arm": which, **measure(ctl)})
    return out

def pair_deltas(blocks):                           # adjacent A/B blocks, sign-corrected
    d = []
    for i in range(0, len(blocks), 2):
        x, y = blocks[i], blocks[i+1]
        a, b = (x, y) if x["arm"] == "A" else (y, x)
        d.append(b["avg_fps"] - a["avg_fps"])
    return d                                       # 4 deltas per launch
```

Optional source diff (candidate-source, ~15 lines each): an `occlusion-cull off|on|all|shader` command next to `gpu-culling` in game/control.rs that sets `cull.always`/swaps `Option<Cull>` at runtime, and a `shader-pack NAME` command. This turns the u9 `daily` vs `daily-cull` arm (env `HORIZON_GPU_CULL=all`) into a live toggle.

Saving: 4-8x fewer launches for toggleable questions [est, pilot needed].

## 3. Sequential testing / early stop

Unit = one pair delta (or one launch's mean delta in proposal 2). After each pair compute an always-valid confidence sequence; stop when it excludes 0 (effect found), or sits inside an equivalence margin (no regression), or n hits the cap. With a Gaussian mixture prior N(0, tau^2) on the true delta, r = tau^2/s^2, s = plug-in SD of deltas (floor it by the pilot SD, since n<5 SD estimates are noisy):

half-width(n) = s * sqrt( 2 (1 + n r) / (n^2 r) * ln( sqrt(1 + n r) / alpha ) )

```python
import math, statistics as st
def cs_halfwidth(n, s, tau, alpha=0.05):
    r = (tau / s) ** 2
    return s * math.sqrt(2 * (1 + n * r) / (n * n * r) * math.log(math.sqrt(1 + n * r) / alpha))

def decide(deltas, s_floor, tau, margin, alpha=0.05, cap=24, min_n=3):
    n = len(deltas)
    if n < min_n: return "continue"
    s = max(st.stdev(deltas), s_floor)
    m, h = st.fmean(deltas), cs_halfwidth(n, s, tau, alpha)
    if abs(m) - h > 0:            return "effect"          # CI excludes 0
    if abs(m) + h < margin:       return "equivalent"      # inside +-margin
    return "continue" if n < cap else "inconclusive"
```

Choose tau ~ 2 x smallest effect of interest. The mixture bound is conservative by ~1.3-1.6x in half-width at n=4-10 versus a fixed-n t-interval, which eats part of the gain. Expected saving [est]: n scales as 1/delta^2, so large effects stop in 3-4 pairs instead of the fixed 12-23; mixed workloads (some obvious wins, some nulls) save 30-60%; a true null with a tight margin saves ~0. Combine with proposal 1 (small SD gives early stops at n=3).

## 4. Fixed-cost cuts

- Several scenes per launch: `run-u9-daily.py` launches a separate process for `ores` (warmup 5, static 5) and `cow`. One launch can do cow static, cow flight, then the ores fixture via `ctl command ...`. Each avoided launch saves ~85 s of ~165 s. Rotate scene order between launches so scene order effects average out. Saving: 35-45% for the ores runs, ~0 for pure cow runs [est].
- Shorter static: within-run sampling error is far below between-run error (static 936 frames, SE of mean frame time ~0.1-0.3% [est, iid] vs 3-10% between runs [data]). Dropping static 20 s -> 8 s and flight 16 s -> 12 s loses almost nothing in precision. Saves ~16 s/run = ~10%. Keep the flight path length distance constant by raising speed, or change it for all arms equally.
- Auto warmup: poll `stats reset` / `sleep 2` / `stats` windows until two consecutive windows are within 3% of each other and the swap delta is ~0; cap at 20 s. Typical 8 s instead of 15 s: saves ~7 s/run (4%). Together with `wait-ready` this also gives a clean "ready" timestamp.
- Cooldown 30-60 s: replace with a thermal/idle check only when the previous run ended hot; in proposal 2 it is not needed between blocks, only between launches. Not benchmarked here; do not shorten without an A/A comparison.

Combined: 15-35% wall time [est].

## 5. Save per-frame series and use cluster bootstrap

Works today with no source change: `bench` does not return raw, but `stats raw` does (control.rs:925-935; `frame_stats` is not cleared until the next reset), so:

```python
ctl("stats", "reset"); ctl("sleep", 20); s = ctl("stats", "raw")   # frame_ms, cpu_ms, gpu_ms lists
```

Flight already stores `flight_frame_ms`. Static does not (doc section 3, "Limits").

Analysis: the independent unit is the run (frame autocorrelation is only -0.23, and frames within a run share the process state). So:
- Tail metrics: pool frames by arm (or by pair), take p99/1%-low of the pool, bootstrap by resampling runs (cluster bootstrap), not frames. Per-run 1% lows have SD 2-7 FPS because each uses only ~10 worst frames of ~900; pooled over 8 runs the estimate rests on ~90 frames. Expected 1.5-2x fewer runs for tail questions [est]; no gain for means.
- Spike vs drift split: with the series, compare block means (4 blocks) to see drift (flight moves, so only for static) and flag spikes (e.g. max_ms 306 in a flight).
- Block bootstrap is only needed if a single run is analyzed by blocks (proposal 2): resample block pairs.

```python
import random, statistics as st
def pooled_low1(runs):                                  # runs: list of frame_ms lists
    x = sorted(f for r in runs for f in r); k = max(1, len(x)//100)
    return 1000 / st.fmean(x[-k:])
def cluster_boot(a_runs, b_runs, stat, B=10000):
    out = []
    for _ in range(B):
        a = [random.choice(a_runs) for _ in a_runs]; b = [random.choice(b_runs) for _ in b_runs]
        out.append(stat(b) - stat(a))
    out.sort(); return out[int(.025*B)], out[int(.975*B)]
```

## 6. CUPED and covariates

Paired delta regression: delta_i = mu + b1 * (run-index/time difference) + b2 * (swap_before_A - swap_before_B) + b3 * (warmup FPS_A - warmup FPS_B) + e_i. Covariates available today per run: `swap_before_M`, `thermal_before`, `index`, harness warmup bench (`ready_after_warmup`; the warmup `bench` summary is discarded by `ctl("bench", args.warmup)` at line 499, so capture its return value).
- Evidence [data]: run-index detrend alone cut variance by 52% (makeup) and 25% (packs) on unpaired runs; rotated arm order already removes most linear drift in pairs, so the extra gain on top of pairing is smaller: 10-30% [est].
- Warmup FPS in the same process is the strongest candidate: it captures process-level state before measuring (same idea as CUPED: pre-period metric of the same unit). Flight vs static correlation is only 0.48 (makeup) and 0.18 (packs), so do not expect more than r~0.5: variance x0.75, so 25% fewer runs [est].
- With n<12 pairs, fit one covariate at most (index or warmup); more would overfit. Report with and without.

## 7. GPU-ms

Not recommended as the primary metric for significance (see section 0). Keep `gpu-passes on` for attribution of a found effect. If GPU ms is used, use p50 of per-pass times and keep gpu-passes setting identical in both arms.

## Recommended order of work

1. (1 h) A/A pilot: 8 launches of one build; record flight CV, static CV, warmup summary, `stats raw` series. Positive control with `render-distance` and `gpu-culling` toggles. Decides proposals 1, 2, 6.
2. Switch analysis to flight primary + sequential stopping (3) + cluster bootstrap (5). No harness change.
3. Write the live A/B driver (2) for toggleable A/Bs; add `occlusion-cull` and `shader-pack` control commands if needed.
4. Multi-scene launches (4).

Expected combined effect for the "10 FPS shader-off" question: 114 runs (~5.2 h) -> ~6-10 runs (~25 min), if the flight metric validates. For a build-vs-build 3 FPS question: ~8-16 runs with flight + pairing + sequential stop, versus several hundred unpaired static runs per arm at 3 FPS (SD 19).

## Caveats

- n=4 per arm in the source data: all SD/CV/corr values are rough; the A/A pilot replaces them.
- Flight FPS may be insensitive to some changes (streaming-bound); verified only by the pilot.
- Single machine state: results are valid for AC power, 1280x720, RD 12/sim 8, the cow scene, and gates as in run-u9-daily.py.
