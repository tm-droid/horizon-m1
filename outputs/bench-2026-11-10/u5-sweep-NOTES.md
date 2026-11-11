# U5 runtime knob sweep (daily7 base, makeup scenario)

Harness: `bench.py` (tags u5a..u5d, runs 52-106), summary: `u5-analyze.py SCENARIO 'glob'...`. Medians of 3 runs unless noted. Flight = fly window; 1% low and p99 matter most. All gates passed; one run invalid (chunkUpdates=6).

## Part A: base build
Makeup, F7 (DAILY7) vs F8M (m1prof), interleaved x3 (runs 52-57) plus earlier runs (F7 u1-01..03, F8M u4-46..48), n=6 each:

| | static avg | static 1%low | flight avg | flight 1%low | flight p99 ms | RSS MB |
|---|---|---|---|---|---|---|
| F7 | 43.9 | 27.5 | 41.1 | 23.8 | 38.7 | 1519 |
| F8M | 44.2 | 26.9 | 40.3 | 22.1 | 44.4 | 1460 |
| delta | +0.7% | -2.2% | -1.9% | -7.1% | +14.8% | -3.9% |

The u5a block alone (n=3 each) favoured F8M (flight 1%low +14.7%), so the gap is run-to-run noise on flight 1%low (range 19-26 fps for the same build). Rule (>2% worse on avg or 1% low in static or flight, pooled): F8M fails static 1%low (-2.2%) and flight 1%low (-7.1%). **Base = F7 (DAILY7).** F8M packs +16-18% avg (U4) is not enough on its own; revisit with more makeup runs if wanted.

## Part B: sweep (makeup, F7, 3 interleaved rounds, runs 58-82)
Deltas vs interleaved base (static avg/1%low, flight avg/1%low/p99, RSS):

| knob | st avg | st 1%low | fl avg | fl 1%low | fl p99 | RSS | verdict |
|---|---|---|---|---|---|---|---|
| gfx.workers=3 | +0.8% | +4.5% | +1.1% | +8.6% | -10.8% | +13.8% | reject (RSS >5%; vs pooled F7 base flight 1%low -2.2%) |
| gfx.workers=4 | +1.1% | +7.5% | +0.9% | +6.1% | -12.1% | -1.6% | marginal win, not robust (one 34 fps run); combo with upl was worse |
| gfx.workers=5 | +0.3% | +8.4% | -7.3% | -6.8% | +11.2% | +0.2% | reject |
| env HORIZON_WORKER_THREADS=6 | +0.9% | +4.3% | -10.0% | -6.3% | +11.5% | -1.6% | reject |
| gfx.uploadBudgetKiB=4096 | +0.9% | +6.1% | +1.1% | +13.8% | -14.5% | -0.4% | WIN |
| gfx.chunkUpdates=6 | | | | | | | reject: run invalid (flight presented 9.8 s, 20 fps), static avg 41.8 (-4%) |
| env HORIZON_MEMORY_LIMIT_MB=4800 | +0.4% | +6.7% | -0.4% | -3.9% | +3.6% | +6.5% | reject |
| gfx.particleCulling=async | +1.2% | +2.0% | -8.0% | -5.8% | +11.5% | -4.5% | reject |
| MIMALLOC_PURGE_DELAY=0 | | | | | | | skipped: client uses mimalloc but `horizon-threads::configure_allocator()` already calls `mi_option_set(purge_delay, 0)` first thing in main, which overrides the env var (no-op) |

Key names confirmed in `crates/horizon-client-render/src/graphics.rs` (workers, chunkUpdates, uploadBudgetKiB, particleCulling) and `horizon-threads/src/lib.rs:25` (HORIZON_WORKER_THREADS). `particleCulling` takes off|sync|async: "on" is not a value (parses to off), so async was tested. The key exists only in the newer build source (`native/build-src.noindex`), not in the f42 source copy.

Noise note: the same F7 base gave flight 1%low 20.9 (interleaved u5b), 22.4 (u5c), 23.2 (all 9 pooled): +-2 fps is noise, so only effects well above that count.

## Combo confirm (runs 83-106, interleaved)
Candidate combo = workers=4 + uploadBudgetKiB=4096.

Makeup (n=3): combo flight 1%low -12.5%, flight avg -4.8%, p99 +22.7%, RSS +13% vs base: **worse; workers=4 dropped.**
upl alone: flight avg 41.3 vs 40.2 (+2.6%), 1%low 23.6 vs 22.4 (+5.3%), p99 -5.3%.
Pooled makeup upl vs base (u5b+u5c, n=6 each): static avg +0.3%, static 1%low +0.2%, flight avg +1.7%, flight 1%low +9.5% (23.7 vs 21.7), flight p99 -10.1% (38.9 vs 43.3 ms), RSS +3.1%. **Confirmed on makeup.**

Packs (shader off): combo flight 1%low -6.5% (n=3). upl alone n=6 pooled vs base n=6: static avg +0.1%, static 1%low +2.5%, flight avg -0.1%, flight 1%low -7.9% (29.2 vs 31.8), p99 +4.4%. Two of six upl packs flights hitched (1%low 18.5 and 19.9, avg 64 and 79) while base had none. This breaks the "no metric >2% worse" rule in packs.

## Winners
| knob | makeup | packs | call |
|---|---|---|---|
| gfx.uploadBudgetKiB=4096 | flight 1%low +9.5%, p99 -10%, avg +1.7% | flight 1%low -7.9% (2/6 hitches) | conditional: improves the makeup play case; packs has a possible hitch. Not applied; if adopted, test packs again or accept the risk since MakeUp is the daily setup |
| everything else | no robust gain | | do not adopt |

## Env persistence mechanism (no live settings changed)
- `horizon-launcher instance launch <INSTANCE> --env "NAME=value NAME2=value"` stores `launch.env` in that instance in `~/Library/Application Support/horizon-launcher/instances.json`; the game gets them on every Play (also INST_* vars). Empty value clears. Default instance id: `horizon`.
- RAM slider (Launch page) saves `launch.memory_limit_mb` on the instance (`launch_page.rs save_memory` -> `Launch::set_memory_limit`); at start `launch.rs limit_memory()` sets `HORIZON_MEMORY_LIMIT_MB` only if the player's own env var is not already set (it runs before wrapper/env; player's variable wins). None = no limit.
- `horizon-launcher game-args [ARGS]` sets extra game CLI args (e.g. --server-thread), not env. `settings` has no env key.
- Graphics knobs (gfx.*) live in the instance's `horizon-graphics.txt` (written by the in-game Graphics screen), not the launcher.
