# arena-thresholds-f42

Status: UNBUILT / UNTESTED. Touches `gfx/arena.rs` only.

## What
`COMPACT_MIN_FREE` 128 -> 32 MiB, `SHRINK_MIN_BYTES` 64 -> 32 MiB. Test `large_pages_shrink_when_...` computed `least` from a
hardcoded 64 MiB; it now uses `SHRINK_MIN_BYTES` so its "smaller page stays" assert follows the constant.

## Why / saving
Section arena compacts/shrinks sooner, so less free space sits resident. R3 estimate 30-100 MiB at RD12.

## Look risk
None visual. Risk is perf: more compaction copies, possible frame hitches while flying into new chunks. Test at line ~1327
(`big = 64 MiB`) still exceeds the new threshold but was not run.

## Verify
Build, run arena unit tests, then bench flight-heavy route; watch 1% lows and `horizon-ctl memory` arena free bytes.
