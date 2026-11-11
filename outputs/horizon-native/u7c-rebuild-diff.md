# U7c: why the rebuilt daily7 differed from the installed daily7

## Root cause
`build-fast-fdc87ae.py` copies the nightly source into `outputs/horizon-runtime/builds.noindex/<stamp>/source`
(inside the Horizon git repo) and runs `git apply <patch>` there. Inside a repo, git treats patch paths as
repo-root relative, so every hunk (paths like `crates/...`) was reported `Skipped patch ...` and git exited 0.
The script saw success and printed `patch X: ok` for all 33 patches while applying none. Silent since the
build dir moved under the repo (2026-11-11 15:05); the build at 2026-11-11 02:38 (retained daily7 tree) ran
before that and is correct.

## Evidence
- `diff -rq` retained daily7 source (`builds.noindex/20261111-023803/source`) vs the unpatched rebuild
  (`20261111-225807/source`): 41 entries (40 differing files + `crates/horizon-shaders/src/translate/varyings.rs`
  missing; created by `up-varying-struct`), ignoring `.DS_Store`.
- Same diff vs the fixed rebuild (`20261112-045432/source`): empty. Fixed rebuild = `native-fdc87ae-m1-u7cfix-73decc0fdc30`
  (same digest suffix as the installed daily7, `73decc0fdc30`).
- Unpatched builds drew the ender dragon as a flat light-blue silhouette (missing fix-cem-*/pack patches).

## Fix (build-fast-fdc87ae.py)
- `git apply` runs with `GIT_CEILING_DIRECTORIES=<repo root>` so git does not discover the outer repo.
- Abort when `Skipped` appears in git stderr or the exit code is non-zero.
- rsync excludes `.DS_Store` (was the only remaining tree difference).

## Consequence
Every result built with the broken script is invalid for patch-stack questions:
- U4 m1prof build (M1 profile bench, +16-18% packs) was unpatched stock + mods.
- U7b d8cand/d8shadow/d8near/d8up/d8off/d8nogpua/d7n/d7r results ("D8C vs F7 packs +17%", "D7N control +17%")
  compared an unpatched tree against patched daily7; the +17% is the cost of the patch stack, not a candidate effect.
- Redo U4 m1prof and U7b on fixed builds. U7e bisects which daily7 patches cost the shaders-off FPS.
