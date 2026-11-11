# MakeUp M1 Quad — blocked design draft, do not run

LGPL-3.0 draft based on Javier Garduño’s MakeUp Ultra Fast9.6.
No runnable pack is delivered. Builder always exits with the blocker;
GLSL has a compile-time error guard. No shader compiler/device was run.

Ballot(true) does not establish non-helper shuffle sources. Helpers may
participate in ballot while being treated inactive by other operations.
The frontend lacks gl_HelperInvocation and the Metal backend injects no
helper exclusion. Coordinate/depth checks cannot exclude triangle-edge
helper leaders. A shared result could therefore read undefined values.

Next prerequisite: verified helper-status frontend/IR/Metal support, then
ballot(nonHelper) with all four source bits required before every shuffle.
This requires engine changes outside the bounded shader-only ownership.
Alternatively expose quad builtins with checked helper semantics.

Unreachable builder and guarded GLSL preserve the cloud-only affine
sharing draft for that follow-up. No activation/quality/speed claim exists.
See docs/horizon-converter/research/Codex-m1-makeup-quad.md for exact
source evidence, normative specification link and future diagnostic plan.
