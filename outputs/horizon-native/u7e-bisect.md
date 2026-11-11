# U7e: which daily7 patches cost the shaders-off FPS (BLOCKED, benches not run)

Status: builds done, benches NOT run. Screen session was locked (CGSSessionScreenIsLocked=Yes, HID idle > 6 h, user
away) from 2026-11-12 05:02 until at least 07:53. A locked session presents no frames: the dragon gallery shot
timed out ("screenshot timed out ... a screenshot is already pending") and a packs run came back
`valid=False static 0.0/0.0, "presented only Nones"`. Unlocking needs the user password, so it was not attempted.
`bench.py` now honours `BENCH_ALLOW_LOCKED=1` to skip the lock gate (useful only for verifying the gate itself).

## Part 1 (U7c) check not done
Dragon shot on u7cfix pending. Source tree of u7cfix is byte-identical to the retained daily7 tree
(see u7c-rebuild-diff.md), so it is expected to render dark.

## Builds ready in $L/versions (not benched, not deleted)
Built with `HORIZON_MIN_FREE_GIB=5 HORIZON_TEST_QUEUE=u4 python3 outputs/horizon-runtime/build-fast-fdc87ae.py
--stack bisect-<tag>.txt --tag <tag> --only $(cat outputs/horizon-native/daily8-mods-only.txt)` (disk was 7.7 GiB,
guard is 8; now env-tunable via HORIZON_MIN_FREE_GIB). All rc 0, each incremental build took a few minutes.

| BUILDS key | version dir | stack | delta vs daily7 (33 patches) |
|---|---|---|---|
| STK | native-fdc87ae-m1-stk-228142bc218e | bisect-stk.txt | empty: stock + 16 mods |
| NOP | native-fdc87ae-m1-nop-5cfd12c893ea | bisect-nop.txt | minus 13 perf patches (cloud-prep kept: up-rain-depth hunks depend on it) |
| NOV | native-fdc87ae-m1-nov-22999b24ac5f | bisect-nov.txt | minus 11 visual/compat (cem-binding .. fix-cem-ravager-ghast) |
| NOU | native-fdc87ae-m1-nou-964b2370a847 | bisect-nou.txt | minus 8 up-* backports |

Stack applicability was checked with a throwaway apply-checker; a first NOP attempt (all 14 perf dropped) failed
with `up-rain-depth ... pack_post.rs:2911 does not apply` (depends on cloud-prep).

## Resume commands (display unlocked, `pgrep -x horizon-client` empty)
```
cd ~/Developer/Horizon
python3 outputs/bench-2026-11-10/bench.py run --scenarios packs --order D7F,STK,D7F,STK,D7F,STK --tag u7ea --start 301
# gap >= 8% -> continue:
python3 outputs/bench-2026-11-10/bench.py run --scenarios packs --order D7F,NOP,NOV,NOU,D7F,NOP,NOV,NOU,D7F,NOP,NOV,NOU --tag u7eb --start 320
```
Then narrow inside the worst group, `--scenarios makeup` for the culprit variant, delete unused version dirs.

## Hypothesis (unverified)
Unpatched dragon is a flat silhouette, so unpatched drew less entity geometry in the packs scene. The likeliest
cost is correctness fixes in the visual/compat group (fix-cem-part-texture draws per-part textures, fix-pack-swirl,
cem-binding), i.e. legit cost; NOV vs D7F will confirm.
