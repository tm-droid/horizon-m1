# Horizon migration validation — 2026-11-04

Java performance tuning remains deferred. Work uses isolated native runtime/worlds; production Java files were not edited. The preferred official runtime is f42ef42ef6ceccb3c6a20bea2481d87949a51c81, API359. Older c9 remains available. Research pin/API153 is still recorded separately.

## Converter checks

`python3 -m unittest discover -s tests -p 'test_horizon*.py' -v` passed under the original device queue: **120 tests,119 passed,1 filesystem-case skip**. The actual extracted CEM resolver compiled and passed using the already installed Rust1.95. Full log: `outputs/horizon-runtime/final-v3-checks-2026-11-04.log`. This suite ran after converter/CEM/settings integration and source-patch regressions; it does not compile the full game or validate native mixin execution.

Fresh migration command, queue48 exit0:

```sh
python3 tools/horizon-convert.py --game-dir instances/Tanush-26.3/minecraft --output outputs/horizon-converter/2026-11-04-Tanush-f42-v3 --stage-packs --stage-mod-assets --runtime-manifest outputs/horizon-runtime/launcher-data/versions/nightly-2026-11-03-f42ef42/runtime-record.json
```

All666 source hashes matched before=after=current. The52 selected file ZIPs matched source SHA256. All210 asset exports were independently checked:12,717 assets,12,922 copied entries,184,377,117 bytes preserved. Generated metadata/provenance is structurally checked, not original pack bytes. Explicit omissions include30,642 code entries,99 data entries,276 nested JARs and2,109 overlay assets. Twelve archive analyses remain coverage-limited. Java logic is not automatically translated.

The new native CEM preflight records42 finding groups,164 coverage gaps and9 unresolved dependencies for the selected view. Its1,000,000-unit bound examined95 models and explicitly skipped139. This limit is visible, not a complete animation audit. The settings candidate carries audited source values, including95° FOV/cloudRange64; GammaUtils15 is source evidence requiring manual review, never silently converted to native gamma0..1.

## Combined-stack runtime smoke check

Queue49 ran `python3 outputs/horizon-runtime/run-full-stack-f42.py` with full52-pack selection, f42, native100%, auto workers, efficient pacing, cap60, source-derived settings and owned NoAI-cow test scene. The control readback confirmed all53 layers including vanilla in the captured order,637 terrain columns and2560×1440 surface. Cow identity/NoAI was verified through server data. The scene image was reviewed: world rendered across the full frame, with no right-half artifact in this shader-off scene. This is limited scene compatibility, not full pack/feature parity.

**Timing invalid:** the requested30-second measurement yielded only3.522 seconds/211 frames. Console logged mouse/motion input from a person while the agent drove. No performance regression, renderer hang or speedup can be inferred. Client quit normally with exit0; queue released. Raw data/image/log remain under `outputs/horizon-runtime/tests/f42-full-stack-sourceopts-r1/`.

There were160 CEM diagnostic lines versus133 for FA alone. The27 added lines comprise11 missing JPM animation references,11 per-part texture/sprite limitations,4 unknown-name reads and1 missing part. Shared alias corrections address only part of this evidence; no warning reduction has yet been demonstrated in a patched runtime. Other gaps remain agent-ready review work.

## Test policy

Test the combined stack first. Isolate a shader, pack group or native feature when an actionable failure/regression appears. Automated preflights and focused checks cover known risky changes; no exhaustive mod-by-mod runtime acceptance is required. User feedback later covers subjective appearance. Future shader candidates are MakeUp9.6 and Miniature2.19, retaining settings and native resolution; Complementary remains a demanding later reference. An earlier file named makeup-1x actually ran at50% scale and cannot establish full-quality performance.

Independent converter integration, source CEM patch and native-build supervisor reviews found no blocking issues. Full native compilation, native Zoom behavior, complete animation parity and shader acceptance remain separate checks. See source candidate/provenance docs for exact limits.


## Native-port build attempts and identified tool fix

Queue51 exited1 before work because the manually extracted/prepared f42 release had no empty `.installed` completion marker. Pinned official launcher backend source confirms that marker registers completed extraction; preparation and publisher hash verification are separate checks. Queue52 registered the already verified release and installed its isolated Rust1.99.1/toolchain, then compiled horizon-mixins0d6b103. The game itself did not compile: tool APPLY rejected f42's built-in `#![recursion_limit = "256"]` as an unexpanded attribute macro. This is a concrete upstream tool compatibility error, not unsupported native hook names.

The official upstream fix is horizon-mixins `e8cd0aa38cffef49cb2e088ef716baa107148c02`, which accepts compiler crate attributes while retaining unknown macro rejection. A new immutable `zoom-f42-fixed-tool` candidate changes only the selected tool pin; original helpers/engine pin and the previous candidate are preserved. The launcher default ddd pin is a fallback, not an automatically enforced minimum; actual tool selection must be checked. See `zoom-f42-planner-gap.md` and the preserved attempt2 logs.

A separate partial CEM native bundle uses cancellable HEAD and only returns audited aliases for exact model/part pairs, falling through to the original resolver otherwise. It deliberately omits the baby-villager fix that requires different source integration. Source review found no blockers, but planning, complete engine compilation and runtime warning/geometry acceptance remain pending. The combined input is staged only after actual helper tests and source/hash guards pass.

Queue59 resolved the partial CEM hook at the actual `horizon_client_lib::mobs::cem::vanilla_part` definition with the pinned e8 planner. Queue60 applied both native bundles and reached the shared client library compile. At 31:22 the measured free space fell to 3.10 GiB, below the 4 GiB active reserve. The cleanup probe returned EPERM before the guard could record its stop reason. A later process listing showed no members in the recorded build process group. No native executable was installed; C-key and guardian behavior remain unverified on the device.

The final queued verifier ran `python3 -m unittest discover -s tests -p 'test_horizon*.py' -v`: **128 tests, 127 passed and one filesystem case test skipped**. It also generated the private Better Lanterns overlay and verified all six relevant path winners across the 52 staged ZIPs. The overlay contains only three model overrides plus pack metadata; six texture keys were added, with model geometry, parents and original source bytes preserved. It was not activated, and the result still needs a visual check. Evidence: `outputs/horizon-runtime/lantern-final-tests-2026-11-04.log` and `outputs/horizon-native/lantern-compat-f42-r1/`.

For performance follow-up, the pinned client reports separate frame intervals, main-loop work with tracked waits subtracted, and GPU timestamps. Do not subtract those summaries to estimate compositor delay. A 60 Hz Immediate/FIFO comparison is useful if renderer work fits 16.7 ms but frame delivery is uneven. Native entity occlusion is gated on a vanilla-only active stack, so it is not a tuning option for these 52 packs. See [frame accounting](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game.rs#L18273) and [entity culling eligibility](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client/src/game/entity_culling.rs#L380).

## Native pilot tested with all 52 packs

Ticket 64 passed a queued Darwin observer probe using a disposable process, then `python3 outputs/horizon-runtime/build-zoom-f42-guarded.py --candidate outputs/horizon-native/zoom-f42-fixed-tool` installed `native-f42ef42-898af830522b` and exited 0 with process cleanup verified. Ticket 65 ran `python3 outputs/horizon-runtime/run-native-pilot-f42.py native-f42ef42-898af830522b`. The runner checked the exact f42 engine, e8 mixins tool, Rust 1.99.1, performance/client target, both reviewed bundles, and executable SHA256 `d96a7246310077b4794892e381da75a10902059cf7ec10b7d92a1fde37ebd069`. Both isolated clients exited 0.

The full-stack guardian fixture used the same known NoAI entity in each client. CEM diagnostic lines fell from **160 to 101**. Guardian and elder guardian diagnostics fell from 57 to one, an unresolved elder animation import. The reviewed native frame shows the guardian's spikes and a visible single eye where the official frame showed a largely bare body. That confirms a visible correction in the tested front pose. Other poses, animation parity and all remaining CEM gaps stay open.

The C-key smoke used the native input path via the control API. The held capture visibly zoomed into the guardian and the release capture restored the wide view. Scroll steps exercised both limits without moving the selected hotbar slot. Exact native zoom factors and physical keyboard input were not measured in this automated run. Source captures and results are in `outputs/horizon-runtime/tests/f42-guardian-{official,native}-r1/`. The custom performance build was checked for behavior only. It has a different build profile from the publisher binary.
