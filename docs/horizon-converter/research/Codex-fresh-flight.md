# Fresh-terrain flight diagnostic

2026-11-07. Diagnostic harness preparation only; no game, compiler or queue job
was run by this worker. Daily/Java settings and original/protected saves were
not changed.

The old128-block flight mixes previously stored columns and frontier work.
`generated_chunks` counts arriving disk/server columns, not world-generation
completions. Do not label its delta as generated terrain.

## Added opt-in probe

`tools/horizon-offline-test.py --fresh-flight` requires a timed on-screen f42
MakeUp case at100% world resolution and rejects `--flight`, offscreen,
compatibility-only, other runtimes/cases and reduced-resolution combinations.
Existing default/`--flight` behavior is unchanged.

Before launch, the existing harness clones the protected seed world into the
new disposable profile. Read-only validation checks the corridor's Anvil
location-table entries in both supported Overworld storage layouts, including
32chunks of margin (radius12 plus20prefetch/generation margin). Existing
corridor chunks, external `.mcc` data, truncated/non-sector-sized files,
invalid/overlapping offsets and symlink region paths are rejected. An absent
region file is acceptable; a present empty location table is also acceptable.
Header hashes and checked paths are recorded. Nothing is pruned or rewritten
to force freshness.

The probe teleports to(4096,95,4096), uses an unmeasured0.1-second zero-length
flight to establish creative hover, and settles the origin's radius12 terrain.
It then measures one32-second raw flight to(4608,95,4096), pitch10, facing+x.
The origin's view necessarily preloads the beginning of this route; the first
pass is a frontier diagnostic, not a claim that every frame sees virgin land.
After returning by teleport and settling the origin again, it measures the
same forward route as an immediate revisit. Both reset day time to1000 and
record camera, packs, window/system state and raw frame/CPU/GPU series.
If the first pass is below15FPS, it is final: no revisit and no retry. An
incomplete presented interval or user input fails without retry.

## Concurrent status proof and interpretation

f42 `crates/horizon-client/src/control.rs:264` creates a separate thread per
control connection. `game/control.rs::poll_control` continues receiving
requests while `fly` retains its deferred reply channel; `status` reads state
without resetting frame statistics. Therefore the probe can keep a fly RPC
on one worker thread and issue independent status RPCs every0.5seconds.

`result.json.fresh_flight` contains:

- `prelaunch`: corridor absence proof and region-header hashes.
- `shader_archive_sha256`, `shader_options_sha256`: actual staged inputs.
- `phases`: `first-pass`, then `revisit` unless hopeless; each holds `before`,
  `after`, `origin_settle`, `system_before/after`, `window_before/after`,
  `pack_selection`, `screenshot`, `measurement` and `hopeless`.
- Each `measurement` is the unchanged raw `fly` summary with `frame_ms`,
  `cpu_ms`, `gpu_ms` and tick summaries.
- Each `status_timeline` row brackets a status reply with
  `requested_seconds`/`received_seconds` relative to the phase's monotonic
  start and retains the full raw status (including generation-stage backlogs,
  meshed totals, renderer/upload counters and camera).
- `request_started_seconds` and `wall_seconds` bound the fly RPC; these are
  host-side spans, not exact GPU timestamps. Sampling adds profiling load.

This can rank stage/backlog/frame correlations between first pass and revisit.
It does not identify disk versus completed world-generation counts, establish
causality by itself, or prove a performance gain. Keep raw console spike lines
and full logs; positive shader-loader evidence may age out of the harness's
last300diagnostic lines, so outer validation must scan the full `console.log`.
Root owns the shared-queue run, gates, loader/frame/input validation and result
interpretation.

## Checks

```sh
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m unittest discover -s tests -p 'test_horizon_fresh_flight.py' -v
```

Exit0,7tests passed: negative region coordinates, absent/empty/stored terrain,
malformed/overlapping tables, both storage layouts/external chunks, concurrent
status/raw-series preservation and the15FPS boundary. No Rust compiler or
runtime check was performed.

Example root-owned queued command (choose a fresh label, wrap with shared queue
and normal gates):

```sh
env HORIZON_TEST_QUEUE=1 HORIZON_SPIKES=25 HORIZON_SHADER_PACK_TIMING=1 \
  /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 tools/horizon-offline-test.py \
  --case makeup --runtime nightly-2026-11-03-f42ef42 \
  --native-version native-f42-m1-r3-6b039bd4b49f \
  --migration outputs/horizon-converter/2026-11-05-Tanush-f42-v4 \
  --native-options-candidate outputs/horizon-converter/2026-11-05-Tanush-f42-v4/native-settings-candidate.json \
  --shader-options-file outputs/horizon-runtime/u9c-trim-options/MakeUp-UltraFast-9.6.zip.txt \
  --scene cow --label fresh-flight-1107 --seconds 20 --warmup 15 --fresh-flight
```

The native-options candidate path exists in the captured v4 migration. This
is a prepared invocation, not an executed device command.

## First device result (ticket163)
Queue-only r3+v4+MakeUptrim diagnostic passed, harness/client exit0 and outervalidationvalid:true. Saved result outputs/horizon-runtime/tests/fp-fresh1107/result.json; summary fresh-flight-fresh1107.json. Regionheaders verified6305corridor/marginchunks had no stored terrain beforelaunch; full shaderloader proof, pack/options/binary hashes, foreground/input and rawseries checks passed.

Firstpass42.46FPS/14.20low1,p99frame53.42ms; revisit41.97/15.07,p99 55.14ms. CPUmean7.33→5.82ms,p99 14.52→10.91; GPUmean22.46→22.90ms,p99 48.48→56.55. No CPUframe exceeded25ms, but20/32presentedframes exceeded50ms (first/revisit). Generation/proto/decorating/finishing/lighting stagebacklogs were0 in all63halfsecond samples perphase; this doesnot prove no generation or ruleout shortbursts. Meshingpeaks81/602; pendinguploadpeaks75/87; cumulativeuploadedbytes deltas2.530GB/0.722GB, meshedsectiondeltas27985/20560. Firstpass substantially moreupload/meshwork, yet similarFPS and lowerGPUtail thanrevisit.

Inference limited tothisroute: visibleframecost is primarilyGPU/presentation, while warmrevisit reducesCPUcost. Do not claim newworldgen algorithm/NEON wouldfixthis or that generationneveroccurred. Statussamplingandspikeprofiling addoverhead; one sequential first/revisit comparison is diagnostic, not a randomized performancewin. Fullconsole retains HORIZON_SPIKES spans but no phasebyteoffset markers, so setup/control slowframes mustnot be attributed to flightwithout rawphaseevidence. Next originalengine trial is unusedcenterdepthreadback gating, not worldgenrewrite.

Endpointimages reviewed: both show the same aboveground forest/water scene with MakeUpclouds, not blank/occluded/underground rendering. Peakfootprint3073MiB; swappeak3185MiB. Effective12/8distances,FOV95,cloudRange64,Unlimited260/Vsyncoff manuallyrevalidated from savedresult with updatedouter EXPECTED_OPTIONS. Newfutureprobes record console_start_offset/console_end_offset around eachmeasuredflight to allow exactflight-only slowspan extraction; thosemarkers were addedafter thisfirstresult and mustnot be assumedpresent in it. Seven puretests rerun aftermarkeraddition: exit0,7passed0.012s.

Further sourcecheck: adaptive_upload::note_frame receives max(CPUms,lastGPUms) at game.rs17862, notCPUalone; Tracker::scale returns1 when EMA busytime>=14ms (game.rs21976ff). WarmedprobeGPU~22ms therefore makes a sustained unnecessaryboost a weak hypothesis. No extra disabled-adaptive benchmark was queued without stronger evidence. Brief initialization/lowGPUperiods are not ruledout by thissourcecheck.
