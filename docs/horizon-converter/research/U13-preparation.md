# U13 native shader preparation — 2026-11-06

Prepared only; no device run, client launch, compiler, queue job, or daily shader change was performed by this unit. Native performance and visual parity remain unmeasured.

## Packs

`outputs/horizon-runtime/prepare-u13-packs.py` reproducibly copies the original ZIP entries and rewrites only `horizon-shaders.toml`:

| Variant | Manifest id | Shadow resolution / distance | Other change |
|---|---|---|---|
| `montarc-m1.hshader` | `montarcm1` | 1536 / 96 | `shadow_samples` default Low |
| `daybreak011-m1.hshader` | `daybreakm1` | 1536 / 80 | none |

Display names have an M1 suffix. Every non-manifest archive entry is preserved byte-for-byte. Montarc reflections and FXAA remain enabled. Originals remain unchanged.

## Runner and report

- `run-u12-native-packs.py --cases <comma-separated-list> --arm <arm> --rounds <positive-int>` selects only the required builds, migrations, shader files, and hashes. Omitted filters preserve the original all-case, one-round defaults, including the two new variants.
- `r3-v4-t` enables `HORIZON_SHADER_PACK_TIMING=1`. Matching per-pass console lines are retained in each result as `shader_pass_timings`.
- MakeUp always receives the measured U9c trim file through `--shader-options-file`; its effective override hash is checked against the harness result. Positive evidence of active MakeUp post programs is mandatory: missing/refused loader evidence invalidates the reference instead of accepting shader-off fallback FPS. No Java options sidecar is read or changed by the runner.
- Profile names include the fresh `--tag`, so separate batches do not collide. Tags accept 1–16 lowercase letters, digits, or hyphens. Resume requires identical plan, executable hashes, shader/override hashes, and selected migration identities (manifest hash, resource-pack selection, native-settings candidate hash). Migration identity is also rechecked before every run. Old summaries missing these identities require a fresh tag.
- Native refusal or missing positive load evidence produces an invalid result with no fallback FPS metrics. A native refusal, or any measured average below 15 FPS, stops that case/arm's later rounds. These omissions are recorded in `skipped`; refused packs are never retried.
- The analyzer groups by case and arm, retains independent rounds, displays median and minimum/maximum, and computes paired percentage changes against MakeUp from the same arm and round. Refused/unloaded native runs are excluded even when an older summary incorrectly marked them valid.
- Existing power, lock/display, thermal, process, disk and protected-profile gates remain intact. Builds and games must still be invoked through the shared device queue.

Suggested U13 arguments, after the coordinator has established normal system speed and acquired the shared queue:

```sh
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 outputs/horizon-runtime/run-u12-native-packs.py \
  --tag u13m1 --cases makeup,n-montarc,n-montarc-m1,n-daybreak011,n-daybreak011-m1 \
  --arm r3-v4-t --rounds 3
```

Read each completed run before continuing with the comparison. A faster pack is not a daily recommendation until its appearance has been reviewed against MakeUp trim.

## Checks

- `.../python3 outputs/horizon-runtime/prepare-u13-packs.py` → exit 0, both packs generated and archive contents verified.
- `.../python3 outputs/horizon-runtime/test-u13-native-packs.py -v` → 10 tests passed in 0.022 seconds after the review fixes. Covers selected inputs/arms/rounds, explicit trim hashing, tag separation, native refusal metrics, strict missing/refused MakeUp loader evidence, resume rejection after either migration file changes, the strict 15 FPS cutoff, paired multi-round aggregation and exact variant contents.
- `.../python3 outputs/horizon-runtime/run-u12-native-packs.py --dry-run --tag u13prep --cases makeup,n-montarc,n-montarc-m1,n-daybreak011,n-daybreak011-m1 --arm r3-v4-t --rounds 3` → exit 0, 15 planned runs, input check OK.
- Python AST parsing of runner, wrapper, analyzer, preparation script and focused tests → passed.
- Read-only aggregation of existing `u12-native-u12.json` → six case/arm groups, zero invalid native runs included.

The Python executable for all checks was `/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`. Pre-edit scripts are backed up under `outputs/horizon-runtime/checkpoints/codex-20261106/*.before-u13`.
