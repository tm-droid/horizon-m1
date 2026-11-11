# thread-cap
Base: fdc87ae + daily4-stack (28 patches, applied in order). NOT compiled or run (no cargo allowed; reasoned only).
Files: horizon-threads/src/lib.rs (+51), lan/chunks.rs, lan/io_pool.rs, lan/mod.rs, vanillagen/lod.rs, client-render/src/lod.rs, save.rs.

## What
- `horizon_threads::fast_cores()` = worker_count() capped at Apple performance cores (M1: 4). Unchanged on non-Apple/Intel.
- `set_network_open` / `network_open`: true while a TCP listener runs (set in `Lan::listen_on`, cleared in `stop_listening`).
- LAN encode pool (`warm_pool`): still spawns worker_count()-1 threads, but threads with index >= default_workers() (3 on M1)
  skip every job unless `network_open()`. Single player: 3 pool threads + the calling tick thread = 4 = P-cores (was 7+1).
- Network pool (`io_pool::run`): each thread sets utility QoS (`network_current(false)`) until a listener opens, then default QoS;
  re-checked every loop pass (poll wakes at least every 100 ms). macOS only; no-op elsewhere. Thread COUNT unchanged (idle threads are free).
- Far decoration (vanillagen/lod.rs:75), far LOD sampling+meshing (client-render/lod.rs:1339), region compression helpers (save.rs:2148)
  size from fast_cores(): M1 far decoration 3->2 threads, far LOD 5 samplers+2 meshers -> 1+2 (cores=4), region compress helpers 4->2.

## Why safe
- Skipped threads only ever did optional parallel help: `warm`/`bodies_with` run the job on the caller too and never wait for the pool
  (comments at chunks.rs:850, 'it never waits for the other threads'). A skipped job is just done by fewer threads.
- LAN/dedicated: `listen_on` flips the flag, so all 7 threads work and net threads use default QoS, as before. Dedicated server on
  non-Apple CPU: fast_cores()==worker_count(), default_workers()==worker_count()-1, so nothing changes.
- `HORIZON_WORKER_THREADS` still caps everything (fast_cores is min of it).

## Expected gain
Less runnable-thread contention during chunk burst on 4 P-cores: render/server thread less often preempted (jobpool-qos already put the
helpers at USER_INITIATED; this removes 4 of 7 of them and moves the net threads to E-cores). Estimate: p99 frame time while flying
into new chunks lower by a few ms; chunk arrival 5-15% slower in the worst case. NOT measured.

## Risks / things to check
- `small: cores <= 4` in client-render/lod.rs:1643 now becomes true on an M1 (cores=fast_cores()=4): far-LOD sampling is throttled to one
  job per 500 ms while the near terrain loads (HELD_SAMPLE_STEP) and far LOD builds slower. Intended (that regime exists for 4-thread
  machines), but if far terrain pop-in gets worse revert only that line (client-render/src/lod.rs `let cores = ...`).
- Utility QoS net threads: loopback chunk packets are framed/compressed on E-cores; if the integrated client's chunk delivery lags,
  drop the `network_current` call in io_pool.rs. Benchmark with the existing flight bench.
- `stop_listening` clears the flag even if two Lan instances exist (tests only); effect is scheduling only.
