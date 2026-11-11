# audio-cache-f42

Status: UNBUILT / UNTESTED. Touches `audio.rs` only.

## What
`CACHE_BYTES` 64 -> 24 MiB (decoded f32 sound LRU). The unit test derives its sizes from the constant.

## Why / saving
R3: ~30-40 MiB at steady state (cache full of f32 samples).

## Look risk
No visual. Possible re-decode hitches/dropouts in busy areas (villages, caves) when evicted sounds replay.

## Verify
Build, `cargo test` audio cache test, then listen in a village / cave with many mobs; check for stutter on first replay.
