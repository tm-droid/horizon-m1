# gpu-e: skip start-of-frame B-to-A copies nothing reads

What: each frame starts by copying the B side back to A for every flipped buffer that has no clear. `a_unread(b)` now skips that copy when no reader can see the A side. That holds when, in program order:
- the first program touching `b` writes all of it (`overwrites`) and flips it;
- that program does not read, copy, mip or image-bind `b`, and no compute stage before it does either;
- no gbuffers program touching `b` has drawn before it;
- every later writer of `b` also writes all of it;
- no stage flip (`deferred_pre`, `composite_pre`) moves `b` back to the unwritten side.

Why safe: under those conditions the A contents are overwritten before anything samples them, so the copy only produced dead data. Buffers that carry history (TAA colortex3, exposure colortex6) are read first and keep their copy.

Gain: about 0.3-0.5 ms per skipped full-res copy. With MakeUp, colortex4 (gaux1, written only by deferred) is the likely candidate.

Risk: medium. The analysis models skipped passes (Setup after the first frame, `sizes_differ`) the way the frame loop does. A mismatch there would leave the previous frame's data visible.

Visual checks:
- No TAA ghosting or smearing when turning.
- No stale reflections or water artefacts.
- No flicker in effects that persist across frames.
- No exposure pumping.
- Compare one frame against the base build at the same spot.

## Review fix (2026-11-10)
Reviewer found a_unread never scanned shadow_terrain, shadow_water, shadow_comp or Entities::shadow, which can bind main buffers via Image::Color. Now any of those touching b keeps the copy.
