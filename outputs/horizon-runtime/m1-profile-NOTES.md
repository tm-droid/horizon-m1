# M1 build profile (U4)

## What
`build-fast-fdc87ae.py` gained `--profile NAME` (default `fast`, unchanged) and `--rustflags STR`.
Profile `m1` is defined via cargo `--config` (no source edit): inherits release, lto="thin", codegen-units=1
(env `HORIZON_M1_CGU` overrides), incremental=false, opt-level=3; panic/debug stay as release. For m1 the script
also sets CARGO_INCREMENTAL=0 (clean_env forces 1, which would override the profile). Binary is copied from
`target/<profile>/`; source-patches.json records profile and rustflags.
Note: pristine `[profile.release]` already has lto=thin, cgu=1; the real differences vs `fast` are
incremental=false and target-cpu=apple-m1.

Build: `HORIZON_TEST_QUEUE=u4 python3 outputs/horizon-runtime/build-fast-fdc87ae.py --stack daily7-stack.txt --tag m1prof --profile m1 --rustflags "-C target-cpu=apple-m1"`
Result: rc 0, 726 s (daily7 fast: 339 s), no OOM at cgu=1. Version native-fdc87ae-m1-m1prof-f5241bf55d1c.
Binary 77.1 MB vs daily7 89.7 MB (-14%).

## Bench (3 runs each, medians; runs/u4-46..51 vs u1-01..06)
| scenario | metric | daily7 | m1prof |
|---|---|---|---|
| makeup static | avg / 1% low / CPU ms / GPU ms | 44.1 / 27.7 / 5.96 / 20.65 | 44.2 / 26.8 / 5.97 / 20.36 |
| makeup flight | avg / 1% low / CPU / GPU | 41.3 / 25.2 / 6.02 / 22.67 | 39.5 / 19.8 / 6.37 / 22.8 |
| packs static | avg / 1% low / CPU / GPU | 85.6 / 32.5 / 3.35 / 13.42 | 101.5 / 34.3 / 2.92 / 11.12 |
| packs flight | avg / 1% low / CPU / GPU | 85.8 / 31.5 / 2.35 / 13.25 | 99.6 / 31.5 / 2.42 / 11.54 |
RSS: makeup 1335 vs 1480 MB, packs 1468 vs 1510 MB. Gates passed (all valid). Game logs: no panics/errors (only the existing missing-texture WARN).

## Verdict: REJECT (by the stated rule), rerun advised
Packs gains are large (+18% static, +16% flight avg, CPU/GPU ms down). But makeup flight median is
-4.3% avg, -21% 1% low, +5.8% CPU ms: breaks the ">2% worse" veto. Caveat: makeup flight 1% low was
19.8/19.7/25.5 across the three runs (run 3 matches daily7) and the first runs had ~1.4 GB swap in use after
the 12-minute build, so this is likely noise. Recommend rerunning makeup x3 on m1prof vs daily7 interleaved
before final rejection; if confirmed noise, ADOPT (packs +16-18%).
