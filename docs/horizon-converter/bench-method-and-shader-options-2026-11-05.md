# Bench method and shader options, 2026-11-05

Research only; no game runs. Local evidence: `tools/horizon-offline-test.py`, `outputs/horizon-runtime/run-m1-performance-matrix.py`, `docs/horizon-converter/ab-cloud-shadow-2026-11-05.md`, settings-audit and shader-screen docs of 2026-11-04/05, shader ZIPs in `instances/Tanush-26.3/minecraft/shaderpacks` (MakeUp ZIP copy: `outputs/horizon-runtime/tests/f42-makeup-shader-onscreen-r2/shaderpacks/`).

## Q1. Benchmark noise

### What the harness does today
- `horizon-offline-test.py`: `--warmup` default 30 s (max 60), warmup is `ctl("bench", warmup)` then `wait-ready`. `system_snapshot()` records `ps`, `vm_stat`, `sysctl vm.swapusage`, `pmset -g therm` but only as a record. No gate, no cooldown, no repeat logic.
- `run-m1-performance-matrix.py`: `safety_gate()` checks AC, unlocked, no xcodebuild/cargo/rustc, no PineconeMC. Records `swap()` before/after. No thermal or memory-pressure gate, no inter-run cooldown (grep: no `cooldown`, no `thermal`).
- Observed: swap 2.5-3.0 GB used every run (ab-cloud-shadow doc). Shader-off avg FPS range 40 (115-155), MakeUp range ~3 (n=2).

### Findings (confidence noted)
- Fanless M1 Air throttles under sustained load. Community reports put onset at several minutes (5-10 min cited) and total loss 15-22% over 30 min; no controlled primary source found. A run is ~15 s warmup + 20 s static + 16 s flight (~1 min) plus launch, so back-to-back runs of ~1.5 min accumulate heat across the matrix even if a single run does not throttle. Treat as a drift across run index, not a per-run cliff. (secondary sources, medium-low confidence)
- Detection without sudo:
  - `pmset -g therm`: on Apple Silicon often prints only "No thermal warning level has been recorded"; `CPU_Speed_Limit` line may be absent. Coarse; absence is not proof of no throttling. Already logged, keep.
  - `ProcessInfo.processInfo.thermalState` (nominal/fair/serious/critical; Apple docs). Reported to collapse finer macOS levels into "fair", so it is a lagging, coarse signal (stanislas.blog, MacThrottle; community, not Apple).
  - `notifyutil -g com.apple.system.thermalpressurelevel` (0 nominal, 1 moderate, 2 heavy, 3 trapping, 4 sleeping) is the finer signal those tools read. From memory, UNVERIFIED here; test it once at idle before relying on it.
  - `powermetrics --samplers thermal,gpu_power` gives GPU frequency/residency but needs sudo; skip.
  - Best no-sudo throttle detector is behavioral: run a fixed 10 s calibration scene (shader-off, uncapped, same camera) before each run and compare GPU ms/frame to a cold-start baseline; abort/cool if >5% slower.
- Memory: Apple guidance and community say memory pressure (green/yellow/red; `memory_pressure -Q` free %) matters more than swap size. No rigorous frame-time-vs-swap data found. Rising `vm_stat` pageouts/swapouts during the measured window is the direct contamination signal. With 8 GB and 2.5-3 GB swap already used, page-ins of game data are plausible variance source for shader-off (CPU/IO-sensitive, 130 FPS) but not for GPU-bound MakeUp (consistent with the observed spreads). Hypothesis, not proven.
- GPU DVFS ramp, Low Power Mode, App Nap: no primary source fetched. General knowledge (UNVERIFIED): GPU clocks ramp within ~100s of ms but governors settle over seconds; 15 s warmup is enough for ramp, not for heat soak. Low Power Mode lowers CPU/GPU clocks on Macs, so verify `pmset -g | grep lowpowermode` = 0. App Nap/occlusion: occluded or unfocused windows get paced/paused (the harness already checks frontmost and `front_error`); keep that and add a post-run check that Horizon was visible the whole window.

### Proposed harness changes (smallest set)
1. Pre-run gate (matrix runner, next to `safety_gate()`):
   - `memory_pressure -Q` free % >= 40 and not yellow/red; record `vm_stat` pageouts+swapouts; require swap used <= value at session start + 200 MB (do not require 0; user cannot reach 0 on 8 GB).
   - Thermal: `thermalState == nominal` via a tiny swift one-liner, `pmset -g therm` has no speed-limit line below 100, plus optional `thermalpressurelevel == 0`. Also `pmset -g | grep lowpowermode` must be 0.
   - Wait loop: poll every 15 s, up to 10 min, then log `gate_waited_s`; fail the run (do not silently proceed) on timeout.
2. Cooldown: fixed 60 s idle between runs plus the gate above; after every 6 runs force a 5 min rest. Record start/end thermal state and `vm_stat` deltas in each entry; flag a run `tainted` if state rose to fair+ or swapouts grew > N pages during the measured window.
3. Warmup: keep 15 s for shader-on; use 30 s for shader-off (more time to reach steady GPU/CPU state; also lets terrain upload finish). Add a within-run drift check: compare mean FPS of first and last third of the static window; flag if differs > 10%.
4. Design: ABBA blocks interleaved (already), randomize block order, and report paired per-block differences (blocks control for slow thermal drift), median + bootstrap CI on log-FPS, not min-max "noise".
5. Calibration run at start and end of every session (see above) to quantify drift.
6. Prefer GPU ms and 1% low over avg FPS for shader-off; at 130-160 FPS with Immediate present the number is CPU/present-bound and the most variable. Consider cap 120 for A/B of CPU-side patches so frame pacing, not peak, is compared.

### Repeats needed (two-sided alpha 0.05, power 0.8; n per arm = 15.7 * SD^2 / d^2)
SD estimated from observed ranges: shader-off range 40 at n=4 gives SD ~ range/2.06 ~ 19 FPS; MakeUp range 3.1 at n=2 gives SD ~ range/1.13 ~ 2.7 FPS (n=2, very unreliable, probably an underestimate).

| detectable delta | shader-off n/arm (SD 19) | MakeUp n/arm (SD 2.7) |
|---|---|---|
| 20 FPS | 14 | 1 |
| 10 FPS | 57 | 2 |
| 5 FPS | 227 | 5 |
| 3 FPS | not feasible | 13 |
| 2 FPS | not feasible | 29 |

Meaning: shader-off avg FPS cannot resolve a patch of ~10% (13 FPS) without ~25-30 runs/arm; either cut the variance (gates above; paired blocks typically remove the shared drift component) or measure shader-on / GPU ms instead. MakeUp: 8-10 runs/arm resolves ~3 FPS (~8%), assuming the n=2 SD holds; re-estimate SD after 6 runs. If thermal drift is a shared slow trend, paired ABBA block differences can need substantially fewer; verify by computing SD of the paired differences.

## Q2. Shader options: expensive, near-invisible at 1440p / 13"

Context: 2560x1440 on a 13" panel (~227 ppi, viewed close), GPU-bound packs (MakeUp 42.8 ms, Miniature 24 ms, Complementary 95 ms GPU in ticket 67). Option names verified in the local ZIPs; cost judgments are general (UNVERIFIED by measurement; each needs an A/B). "Pure-perf" = same look intended, only quality of an invisible-ish approximation. "Visible" = changes the look.

### Sidecars found
- `.zip.txt` sidecars exist only for MakeUp (`IMAGE_SHARPENING=true`, `V_CLOUDS=2`) and Mellow (all under `outputs/horizon-converter/*/shader-source/` and test shaderpacks dirs). Miniature and Complementary have no sidecar (pack defaults). Prior results: V_CLOUDS 2->1 plus sharpening off combined was ~+2 FPS static (44.4 vs 42.1), unresolved individually (settings-audit, ticket 72).

### MakeUp 9.6 (`shaders/lib/config.glsl`) - priority order
1. `AOSTEPS 5` (range 2-11, "high performance cost"): try 3. Pure-perf (AO noise slightly higher). `AO 1` off = visible (contact darkening).
2. `V_CLOUDS 2` (dynamic) -> 1 (static): pure-perf-ish, cloud shape stops evolving (visible only over minutes). Already tested combined with sharpening.
3. `SHADOW_BLUR 2.0`: lower to ~1.0; softness slightly visible, small gain. Shadow map is only 840 (from `shaders.properties`), so resolution is already low; do not lower further.
4. `VOL_LIGHT` 1 (volumetric) -> 0/2: 2 depth-based godrays; visible in forests/dawn, test only if cost shows.
5. `REFLECTION_SLIDER 2` (raymarched SSR) -> 1 (flipped image): visible on water only on close look; on 13" mostly invisible except calm water. `CLOUD_REFLECTION` define: off-screen cloud reflection, near-invisible, pure-perf.
6. `AA_TYPE 2` (TAA) is the default and cheap; TAA+ (3) adds FXAA; 0 would be visible shimmer at 1440p. Keep TAA. Leave `DOF`, `MOTION_BLUR_SAMPLES 4->3`, `BLOOM_SAMPLES 3->2` (already off/tiny; motion blur samples pure-perf).
7. `IMAGE_SHARPENING`/`SHARPENING 0.5`: cheap pass, visible-only; turn off to match defaults.

### Miniature 2.19 (`shaders/shader.h`)
- `SSR_MAX_STEPS 10`, `SSR_BINARY_STEPS 4`, `SSR_STEP_SIZE 1.6`: try 6 / 2; pure-perf, slight reflection noise.
- `REFLECTIONS 10`, `BLOCK_REFLECTIONS 5`: lowering is visible on water/glass/blocks; BLOCK_REFLECTIONS 5->2 is cheap to try and subtle.
- `SHADOW_PIXEL 16` (pixelated shadow grid, 16 px per block, higher = finer): shadow is deliberately stylized; 8 reduces map detail, visible only as blockier shadow edges. Shadow map already 1024 over 128 blocks (shader-screen doc); `SHADOW_ENTITY 0` already skips entity shadows.
- `ENABLE_FOG`, water wave/glint params: low cost; skip. Few heavy options overall; its cost is mostly fixed pipeline plus 1% low spikes (p99 up to 101 ms), so investigate spikes before options.

### Complementary Reimagined r5.9.3 (names from `shaders.properties` and `lang/en_US.lang`)
- `SHADOW_QUALITY` (-1 off, 0 Very Low ... 3 High, 4 Very High, 5 Ultra): 2048 shadow map is the biggest lever; Medium/High is near-invisible at 13". Related `shadowDistance` slider (192 blocks active): 192 -> 128 invisible when render distance is 12 and fog hides far shadows; pure-perf mostly. `SHADOW_SMOOTHING` slider.
- `LIGHTSHAFT_QUALI_DEFINE` (0 off, 1 Low ... 4 Very High): Low/Medium, pure-perf noise tradeoff. Needs Real-Time Shadows on.
- `SSAO_QUALI_DEFINE` and `SSAO_I`: lower quality tier; subtle AO noise, near-invisible. `VANILLAAO_I` untouched.
- `WATER_REFLECT_QUALITY` (-1 off, 0 sky only, 1 potato, 2 medium=SSR): potato is a visible downgrade only on water close-ups; try 1. `REFLECTION_RES` (reflection resolution) lower is pure-perf.
- `CLOUD_QUALITY` (0-3) and `CLOUD_STYLE_DEFINE`: Medium/Low near-invisible; Unbound/Reimagined style differs visibly.
- `TAA_DEFINE` (TAA on) vs `FXAA_DEFINE`: FXAA is cheaper but visibly softer/shimmer at motion; keep TAA. Not tested: Complementary has no explicit render-scale option here (`PIXEL_SCALE` is a stylization option, not resolution); resolution scaling would come from Horizon's own native scale (settings-audit says keep native 100%).
- Given 95 ms GPU, expect Complementary to need several tiers lowered together; test as one profile (shadow Medium + distance 128 + lightshaft Low + SSAO low + cloud Medium) then ablate.

## Sources
- Apple, ProcessInfo.ThermalState: https://developer.apple.com/documentation/foundation/processinfo/thermalstate-swift.enum.md
- Apple legacy guidance: https://developer.apple.com/library/prerelease/mac/documentation/Performance/Conceptual/power_efficiency_guidelines_osx/RespondToThermalStateChanges.html
- macOS thermal throttling detection (secondary): https://stanislas.blog/2025/12/macos-thermal-throttling-app/ and https://github.com/angristan/MacThrottle
- pmset man page copy: https://sudo.is/docs/macos/man_pmset.html ; Apple Community, no thermal level on Apple Silicon: https://discussions.apple.com/thread/253135819
- M1 Air sustained throttling (forum, low confidence): https://forums.macrumors.com/threads/how-does-the-air-manage-throttling-and-performance-loss-in-games.2269457/page-2 ; https://spy.macrumors.com/threads/m2-fan-to-fanless-takes-32-performance-hit-on-30-minute-sustained-load-vs-22-for-m1.2351748
- Memory pressure guides: https://mole.fit/blog/mac-memory-pressure-explained ; https://blog.greggant.com/posts/2024/07/03/macos-memory-management.html
- MakeUp Ultra Fast: https://modrinth.com/shader/makeup-ultra-fast-shaders ; source https://github.com/javiergcim/MakeUpUltraFast
- Complementary guides (community): https://deltiasgaming.com/?p=204009
