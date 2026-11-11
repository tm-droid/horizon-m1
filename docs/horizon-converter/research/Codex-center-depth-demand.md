# Original M1 candidate: skip unused center-depth readback

2026-11-07. This follows the user's broader optimization continuation. It is
prepared source code, not an adopted setting or a measured speed win.

The exact daily r3 source always creates `gfx::pack_center_depth::CenterDepth`
in `PackPost::run`, collects the latest raw value, and renders/copies a single
center texel at the end of the frame. Submission schedules asynchronous map
callbacks. `collect` calls `device.poll(Poll)` without waiting for the GPU.
MakeUp uses `centerDepthSmooth` under its DOF option; the current daily options
do not enable DOF. Removing the unused path can avoid a render pass, small GPU
readback and callback/poll bookkeeping without reducing image quality. The
size of the benefit remains unknown; this is not a claim of a blocking stall.

## Implementation and scope

Artifacts: `outputs/horizon-native/center-depth-demand-f42/` contains the patch,
three baseline hashes, sparse candidate sources and a preparation verifier.
Pristine source, daily configuration, installed binaries and Java files are
unchanged by this work.

- `horizon-shaders/src/custom.rs`: `Custom::references` recursively checks all
  parsed expressions/items for a name. This conservatively includes variable
  dependencies, nested calls, inactive branches and shadowed-name cases.
- `horizon-shaders/src/post.rs`: `Post::uses_uniform` checks custom references,
  all graphics/compute interfaces in `every_program`, and `lines` explicitly.
  It leaves the older iterator's other callers unchanged.
- `horizon-client-render/src/gfx/pack_post.rs`: store demand once per constructor
  and allocate/collect only if demanded or forced. With no allocation, existing
  conditional copies/submission callbacks skip themselves. Unused raw depth
  stays `None`; other frame uniforms retain their original update behavior.

Demand follows preprocessed stage declarations. The graphics interface merges
vertex/fragment uniforms, and supported geometry is folded into the vertex
program before translation. Compute stages have their own interfaces. A
uniform declaration that survives preprocessing conservatively keeps the path
on even if later compiler optimization could remove it. Custom expressions
are already evaluated each frame, so scanning every parsed item avoids
needing an uncertain reachability analysis.

`HORIZON_FORCE_CENTER_DEPTH=1` is the original-path A/B control. Constructor
logging records enabled, demand and force separately. A newly loaded pack /
options or dimension creates a new `PackPost`, so demand does not stay cached
across reloads.

## Prepared verification and required device acceptance

The framework-Python preparation verifier exited0: all three baseline hashes
unchanged, patch applies cleanly, disposable patched files exactly match the
candidate. Five Rust tests prefixed `center_depth_` cover:

1. Custom AST name/component, calls, unary and binary traversal, variable
   chains and inactive branches.
2. Exact names (not partial identifiers, left-hand declarations or call names).
3. Absent, vertex and fragment uniform demand through actual shader loading.
4. Line-only placement and actual compute-only uniform demand.
5. Demand recomputation for separately loaded posts/custom expressions.

Root owns the queued Rust tests, native build and device checks. Required:
matched MakeUp force1/default runs with decision logs; MakeUp DOF-on demand
and reload control; no shader/GPU errors; visual comparison and frame/memory
results. No Rust tests, compiler, device run, speed or visual-parity claim was
made by this implementation agent.

## Coordinator verification checkpoint
Fresh reviewer spawn/reuse was rejected by this session's agentthread limit. Independent peerworker reviewed the unrelated patch and found no demandcoverage/rawdepth gaps; root also checked every consumer and all4521daily source hashes. Ticket162 ran five actual Rust tests: fourpassed, reload/custom fixture failed at Pack::from_zip_bytes with NoShadersFolder because the no-program ZIP had no shaders directory. No engine workaround: the helper now adds an ignored shaders/fixture.txt for otherwiseempty packs, retaining all assertions. Original patch/testfile checkpointed under checkpoint-empty-zip-fixture; preparation verifier stillpasses. Full client build intentionally stopped beforestarting due failedtest. Rerun pending after the independent freshflight diagnostic.

Corrected fixture retry ticket164: actual `cargo test --offline --locked --profile fast --manifest-path <r6source>/Cargo.toml -p horizon-shaders --lib center_depth_` exit0, all5passed,170filtered. Fullclientcompile nowrunning under samequeuelease. No runtime/performance claim yet. Separateforce/demand comparison wrapper prepared as outputs/horizon-runtime/run-r6-center-depth.py, including a DOF-on demand positivecontrol.

Porter linkage: existing v4 porting-index.json entry `iris` is taskmod-0143 (983classes inspected; scan explicitlyincomplete due finding/reference limits, assets-only-runtime-unverified, native_key candidatehook). This engineoptimization builds on Horizon's existing Iris-compatible shadertranslation; it doesnot convert theJavaIris mod or turn the porter's assetcarry into behaviorparity. Keep generatedmigration/task provenance unchanged.

Root checked incidentaldevice.poll side effects: normal M1 frame timing is created unconditionally when the adapter supports timestamp queries (gfx.rs2178; timing.rs::GpuTimer::new), and polls every submitted/landed frame (gfx.rs9369/9842; timing.rs246). Culling/readback/dump paths also own their polling. Skipping unusedCenterDepthdoesnot remove the M1 renderer's onlycallbackdriver. Benchmark timing remains enabled; no GPUgain claim inferred from thisstaticcheck.

Build ticket164 passed: fivefocusedtests73.74s, fullclient793.77s, cleanup_verified:true; installedunselectednative-f42-m1-r6-32344a47f1e2, binarySHA256d9719bc6914fc42a1168de7c8c9f9f8c60ee46c275566e51e19e2275f71de45c. Exactr3sourceinventory unchangedbefore/after, inheritedCEMZoommetadata retained. Two-armdryrun/inputcheck passed. Beforebench, queue165removed11olderHorizon incrementalcachedirs/recovered1.95GiB (sources/installedbuilds/worlds untouched), restoring7.01GiBfree. Queue166/session18831 runs forcedoriginalvsdemandgatedscreen withsamebinary andtrim; no runtimegainclaimyet.

## Device screen completed; not promoted
Ticket166 forcedoriginalvsdemandgated both valid/exit0. Activationproof forced: enabled=true,demand=false,forced=true; automatic: allfalse. Static58.7→56.0FPS, flight45.3→44.5; staticlow33.5both, flightlow28.4→16.4; peakfootprint2734→2789MiB. Onepair doesnot establish a causalregression, but provides no benefitclaim or adoptionreason. Keptunselected.

Ticket167DOFpositivecontrol also valid/exit0, enabled=true,demand=true,forced=false.52.7static/41.6flightFPS is compatibilityonly because DOFchangesimage/work. NormalMakeUpstillselected; no shaderquality/resolution compromise. Nextcandidate isolates guardedcompositeoverwrite from other r4memory/allocatorchanges; R6code remains a tested optionaloptimization, not a verifiedspeedwin.
