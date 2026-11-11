# R15 patch stack apply order (2026-11-06)

## Root cause
- `candidate-source` is NOT pure f42. Its `gfx.rs` (sha b6bfa796, 11316 lines) and `gfx/pack_post.rs` (sha e4177510) already equal pristine + cloud-prep + shadow-scratch (verified with git apply on the pristine files, byte-identical). So re-applying them fails: `gfx.rs:1045`, `gfx.rs:7328`, `pack_post.rs:517`.
- Pristine f42 = `outputs/horizon-runtime/launcher-data/native/stage` (gfx.rs sha 322fd525, 11302 lines; pack_post.rs sha a9b38e30). These match `before_sha256` in `cloud-prep-f42/patch-spec.json`.
- The other 10 patches apply to candidate-source because it holds none of their files' changes.

## Working order (git apply --check and apply, all 12 OK on pristine stage)
cloud-prep, shadow-scratch, qos-backport, jobpool-qos, sprite-compress, emissive-bsearch, pass-merge, shadow-dedup, particle-cull, adaptive-upload, pbr-cpu-drop, anim-frame-compact
This is exactly the r3 order (`build-m1-performance-r3.py`: cloud-prep and shadow-scratch first, then PERF_MODS, then R3_MODS).

## Order constraints / overlaps
- shadow-dedup after shadow-scratch: gfx.rs hunks @1046 and @4156 sit on shadow-scratch's @1045 and @4153 hunks (same lines).
- pass-merge after cloud-prep: pack_post.rs pass-merge @386/@3015/@4663 sits around cloud-prep's @517/@2080/@2414/@3351 (line offsets shift +2, context touches).
- pbr-cpu-drop after sprite-compress: assets.rs (503). In the task's listed order (pbr before sprite) pbr-cpu-drop fails `assets.rs:503`. The script comment says sprite-compress needs pristine assets.rs, so sprite-compress goes before the u6 patches.
- Listed order on pristine stage: only pbr-cpu-drop fails; cloud-prep and shadow-scratch apply fine.
- gfx.rs is also touched by anim-frame-compact and emissive-bsearch; no conflict in r3 order.

## Did r3 include cloud-prep and shadow-scratch?
Yes. r3 = r2 + 4 (particle-cull, adaptive-upload, pbr-cpu-drop, anim-frame-compact); r2 = stage + cloud-prep + shadow-scratch + 6 mods (deep-pass-2026-11-06.md section 2a). Build `native-f42-m1-r3-6b039bd4b49f`. The r3 script applies them through `prepare.py` render/transform calls (not git apply), cloud-prep then shadow-scratch, in the order above. The `native-f42-m1-r3noqos` build is the same minus qos-backport and jobpool-qos. Neutrality of the two patches: A/B `ab-cloud-shadow`.

## Rebased patches
None needed. No `.rebased.patch` written. Fix is to apply to the pristine stage in the order above (or to apply only the 10 other patches to candidate-source).
Scratch: /private/tmp/claude-503/r15/{ordered,listed,cs}. No cargo run, no originals modified.
