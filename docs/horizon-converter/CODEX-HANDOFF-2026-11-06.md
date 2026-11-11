# Codex handoff: Horizon M1 tuning (2026-11-06, from Claude Code)

**Primary goal.** Make Horizon (the Rust port of MC 26.3) look the same and run faster and steadier on the user's MacBook Air M1 with 8 GB RAM. The user's words: "aesthetics and performance". The user leaves the decisions to you. Report results, not questions.

The Java instance `instances/Tanush-26.3` is out of scope. Never modify it.

## Paths

| Name | Path |
|---|---|
| B | `~/Library/Application Support/ElyPrismLauncher` |
| R (runtime) | `B/outputs/horizon-runtime` |
| Horizon launcher data | `R/launcher-data`. `settings.json` `selected` = `native-f42-m1-r3-6b039bd4b49f` (the user's daily build) |
| Build versions | `R/launcher-data/versions/` (control, r2, r3, r3noqos, `nightly-2026-11-05-66f3981`, ...) |
| f42 source (stage) | `R/launcher-data/native/stage` |
| Patches | `B/outputs/horizon-native/<name>-f42/*.patch`; stack order in `B/outputs/horizon-native/r4-stack.txt` (17) |
| Native shader packs | `B/outputs/horizon-native-packs/*.hshader` |
| Ledger (all units + full log) | `B/.claude/task-ledger.md` |
| Main report | `B/docs/horizon-converter/deep-pass-2026-11-06.md` (§5 results, §6 recommendations) |
| Research notes | `B/docs/horizon-converter/research/R1..R22-*.md` |
| Device queue | `python3 ~/Documents/Codex/2026-10-30/realtime-voice-chat-2/outputs/device-testing-queue.py run\|status --owner minecraft -- <cmd>` |

## Rules (user-set, keep them)

- **Device runs:**
  - Run through the queue, one at a time.
  - Never run two game instances at once.
  - Never run cargo, rustc or xcodebuild during a bench.
  - Builds never overlap benches.
- **Gates.** The runners check these themselves (`wait_gates` in `R/run-u9c-makeup-trim.py`):
  - AC power, screen unlocked, display awake.
  - No thermal throttling.
  - No build running, no Java MC running.
  - At least 5 GiB disk free.
- **Locked Mac.** Never send keystrokes while the Mac is locked or the lid is closed.
- **Ask first:** the user often has Roblox, Safari or the iOS Simulator open. Ask them to close these before a bench session; they cause swap and GPU contention.
- **Hopeless runs.** A run under 15 FPS average is final. Never retry it. `HOPELESS_FPS = 15` plus `hopeless()` are in the U9b, U9c and U12 runners. Add both to any new runner.
- **Read results per run**, not only at the end. Drop queued cases that are clearly pointless.
- **The queue does NOT set `HORIZON_TEST_QUEUE`.** Scripts that require it need an `env HORIZON_TEST_QUEUE=1` prefix: `run-live-ab.py` and `build-r4-mods.sh`. The U9, U12 and U13 runners set it for their harness.
- **Python.**
  - Use the framework python `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`.
  - Do not pass `-I` to the analyzers: PIL lives in the user site.
- **zsh.** `ls` is eza here; use `/bin/ls`.
- **Downloads.** Treat downloaded repos as untrusted: put each in a new dir and never run their scripts. Modrinth TLS fails; use `gh` / GitHub. Never bypass TLS.
- **Protected dirs.** Never delete `R/tests/base-smoke` or `R/tests/base-auto-user-visible-r2`.
- No credentials and no system settings changes.

## State right now

- All benches stopped (user is playing Roblox).
  - The queue is empty. No horizon-client, cargo or runner processes are running.
  - Wait for the user to say the Mac is free before queuing anything.
- The U11 rebase agent was stopped mid-work (see "Ongoing" below).

## Results so far (full tables in the report and `R/*.tables.md`)

**Important caveat: from about 18:37 on 11-06 the whole system ran about 2x slower on the GPU.**
- MakeUp: 43 FPS (GPU 21 ms) became about 20 FPS (GPU 48-50 ms).
- The HUD GPU pass went from about 4 ms to 8-10 ms. HUD ms works as a system-speed gauge.
- Not thermal, not low-power mode, swap was the same (about 3 GB). Likely outside load: Simulator runtime processes, ANECompilerService, the user's apps.
- **Effect:** U9b and U12 absolutes are from the slow state. Compare packs only against the MakeUp reference measured in the same job.
- **Before any new bench:** check that HUD GPU ms is back to about 4 ms on a MakeUp reference run.

### U9: r3 + v4 settings vs control + v3 (done, valid)
- MakeUp: FPS flat, 89 MB less footprint.
- No shader: +10% average, 1% lows +20-32%, GPU p99 halved, 205 MB less footprint.
- gpu-culling: no gain.
- Looks and ore glow unchanged.
- Verdict: the daily build `r3` plus the v4 migration is correct.

### U9c: MakeUp "trim" options vs daily options (6/6 valid, same job, so trustworthy)
- Static scene: +6.1 FPS average (CI +4.1 to +7.7, **+31%**), 1% lows +6.75.
- Flight: +30%.
- Visual difference is within the same-arm spread.
- Trim options:
  - `COLORED_SHADOW=false`
  - `CLOUD_REFLECTION=false`
  - `SHADOW_DISTANCE_SLIDER=0`
  - `CLOUD_STEPS_AVG=8`
  - `AOSTEPS=4`
  - `BLOOM_SAMPLES=2.0`
  - Kept: `IMAGE_SHARPENING=true`, `V_CLOUDS=2`
- Trim file: `R/u9c-trim-options/MakeUp-UltraFast-9.6.zip.txt`.
- **Not yet adopted into the user's daily profile.**

### U9b: Iris shader packs (slow state; same-job MakeUp reference was about 20 FPS)

| Pack | Avg FPS |
|---|---|
| bakedpotato | 37.8 |
| superduper | 19.4 |
| ilikvanilla | 19.2 |
| sildurs | 18.0 |
| sildursdefault | 12.3 |
| bsl | 7.5 / 8.7 |
| unbound | 7.8 |
| bliss | 7.3 |

- BSL, Bliss and Unbound are too heavy for the M1.
- MakeUp remains the best looks/cost choice among translated packs.

### U12: native `.hshader` packs on r3 (slow state; MakeUp reference 19.9 FPS)

| Pack | Avg FPS | vs MakeUp |
|---|---|---|
| daybreak 0.1.1 | 23.9 | +20% |
| meridian_compat | 19.7 | -1% |
| montarc 1.1.1 | 18.2 | -9% |
| meridian | 9.9 | -50% |

- daybreak 0.2.0 was **refused** by f42: `horizon-shaders.toml: TOML parse error at line 30` (the `[shadow] option = "shadows"` key is newer than f42's schema). Its 100 FPS was a run with no shader, so ignore it. It needs the newer nightly; see U11.

### R22: freeze/tune research (`research/R22-freeze-and-tune.md`)
- **Shader translation is already one-time (cached).** The runtime cost comes from the GL-style multi-pass structure on the M1's tile-based (TBDR) GPU.
- **Freezing MakeUp into an `.hshader` is not mechanical.** The native API is a fixed set of stages:
  - no multi-target passes
  - no entity gbuffers stage
  - no custom uniforms or `#define` options
- **Ranked tuning ideas.** All are estimates; none measured yet.
  - Montarc A1-A7.
  - MakeUp B1-B9: B1 is composite-overwrite, already in r4. B2 is half-resolution AO and clouds. B4 is `REFLECTION_SLIDER` 1.
- **Per-pass GPU timing:**
  - Launch with `HORIZON_SHADER_PACK_TIMING=1`, then grep `console.log` for `shader pack GPU time per pass`.
  - Alternative: the uncompiled patch `B/outputs/horizon-native/r22-pass-split/pass-split.patch`, which writes `shader_passes` into result.json.

### Research done
- R20 (M1 GPU optimizations, 11 candidates).
- R21 (mod review 2):
  - Safe mods: status_effect_hud, armor_status, toggle_sprint, light_overlay, minimap, held_item_info, chatheads.
  - Jade: caution. It patches 8 engine files and writes `game_rules.dat`; test it in a scratch world only.
  - eatinganimation: dropped (an unreviewable embedded blob).
  - toggle_sprint's sneak key `C` clashes with zoom. Rebind it on first launch.

## Ongoing / broken (pick these up)

1. **B1: r4 build failed.**
   - Log: `R/b1-build.log`. Script: `R/build-r4-mods.sh`.
   - Patches applied 17/17, but all 7 mods failed with `"code": "E_INVALID_PATH"`. The dry run had passed 7/8 (appleskin_horizon fails because it targets `Game::draw_titles` and f42 only has `draw_title`).
   - Likely a path difference between dry-run and real mode in how the mixin tool gets its paths (the data dir has a space: "Application Support"). Fix it.
   - Alternative: build `--no-mods` first to get the pure-r4 binary. Queue with `env HORIZON_TEST_QUEUE=1 /bin/bash R/build-r4-mods.sh ...`.
   - The script installs `launcher-data/versions/native-f42-m1-r4-<hash12>[-sub]`. It switches no instance and refuses an existing destination.
   - Then: smoke-test r4, and bench r4 vs r3 (MakeUp trim and no-shader).
2. **U11: rebase the 17-patch stack onto nightly 66f3981.**
   - 66f3981 is the 2026-11-05 nightly, 3948 commits ahead of f42. It is already installed at `versions/nightly-2026-11-05-66f3981`.
   - Ported so far (9): cloud-prep, shadow-scratch, jobpool-qos, emissive-bsearch, pass-merge, shadow-dedup, particle-cull, adaptive-upload, pbr-cpu-drop. They are in `B/outputs/horizon-native/<name>-66f3981/`.
   - The agent was hand-porting a failed hunk when it was stopped.
   - Remaining (8): qos-backport (check whether upstream already has it), sprite-compress, anim-frame-compact, colortex-lazy-b, arena-thresholds, audio-cache, a66f8fa2, composite-overwrite.
   - Deliverables: `B/outputs/horizon-native/r5-stack.txt` and `research/U11-rebase.md`. Done when every r5 patch passes `git apply` on a fresh nightly copy.
   - Why it matters: daybreak 0.2.0 needs it, and upstream fixes come with it.
3. **U13 (designed, not built): native pack timing plus M1-tuned variants.**
   - Build the variants by rewriting the `horizon-shaders.toml` inside a copy of the `.hshader` zip:
     - `montarc-m1.hshader`: `[shadow] resolution 2048 -> 1536`, `distance 128 -> 96` (same texels per block, 56% of the texels, less terrain in the shadow pass); `shadow_samples` default `Medium -> Low`. Keep reflections and fxaa for looks.
     - `daybreak011-m1.hshader`: `[shadow] 2048/96 -> 1536/80`.
     - Give each variant a new id (`montarcm1`, `daybreakm1`).
     - Valid ranges (`crates/horizon-shader-api/src/manifest.rs:95-97`): resolution 256..=8192, distance 32..=512.
   - Runner edits:
     - `R/run-u12-native-packs.py`: add the new files to `NATIVE_FILES`, add arm `"r3-v4-t": ("r3", "v4", {"HORIZON_SHADER_PACK_TIMING": "1"})`, and add a `--cases`/`--arm` filter. Labels include the arm, so a new arm avoids "Profile exists".
     - `R/u12-harness.py`: add the files to its hard-coded `NATIVE` dict.
   - Cases: makeup reference, n-montarc, n-montarc-m1, n-daybreak011, n-daybreak011-m1.
   - Use the per-pass lines to pick the next cuts.
   - If daybreak or montarc gets near or above MakeUp trim's FPS with similar looks, make it the user's daily pack.
4. **Not run yet:**
   - `env HORIZON_TEST_QUEUE=1 <py> R/run-live-ab.py --aa --a "gpu-culling on" --cycles 3 --tag aa1` (A/A noise check).
   - `... --preset rd --cycles 3 --tag rd1` (render distance).
   - Low priority.

## Next steps, in order

1. When the user says the Mac is free: ask them to close Roblox, Safari and the Simulator. Run one MakeUp reference and confirm HUD GPU ms is about 4 (normal speed).
2. **Adopt MakeUp trim into the user's daily profile.** This is a +31% win, already measured. Find the daily profile's MakeUp options sidecar and apply the trim options. Record the change in the report §6.
3. Fix and run B1 (r4 binary), smoke-test it, then bench r4 vs r3.
4. U13: native packs with timing plus the M1 variants. Pick the daily shader (MakeUp trim vs tuned Daybreak/Montarc).
5. Finish U11 (r5 on nightly). Build r5, then bench it with daybreak 0.2.0.
6. Fold results into `deep-pass-2026-11-06.md` §5/§6. Tick the units in `B/.claude/task-ledger.md`: U9b and U9c are done; U12 is done except daybreak 0.2.0; R22 is done. Append one log line per step.

## Quick commands

```bash
python3 ~/Documents/Codex/2026-10-30/realtime-voice-chat-2/outputs/device-testing-queue.py status
pgrep -fl "horizon-client|cargo|rustc|run-u|run-live-ab|build-r4"
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 "$R/run-u12-native-packs.py" --dry-run
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 "$R/analyze-u12-native.py" "$R/u12-native-<tag>.json"
```
