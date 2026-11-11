# Demand-gated center-depth readback (daily f42/r3 trial)

Prepared against the exact daily `outputs/horizon-runtime/m1-performance-r3/candidate-source`.
The three immutable input hashes are in `baseline-sha256.json`; sparse changed
files are in `candidate-source/`. Apply `center-depth-demand.patch` to a full
verified r3 source copy, never to the source baseline or Java instance.

The old `PackPost::run` unconditionally creates the center-depth renderer and
calls its `collect` method. That does a nonblocking device poll. Each frame
then renders one depth texel, copies it to a staging buffer and schedules an
asynchronous map after submission, whether a program uses the result or not.
This patch removes that work only when no loaded stage or evaluated custom
expression declares/reads `centerDepthSmooth`. It does not remove a blocking
GPU wait: the original path is already asynchronous.

Demand includes every `Post::every_program` path, plus the separately omitted
line program, each graphics interface (including folded geometry) and every
compute interface. Interfaces come from preprocessed shader declarations,
so an option-disabled declaration does not create demand. Unused declarations
conservatively retain the readback. Custom dependency detection recursively
walks every parsed item's expression, including variable items, call arguments,
unary/binary expressions and inactive branches. False positives are safe.
`every_program` itself is unchanged; unrelated buffer sizing behavior is intact.

Demand and the force control are evaluated once when a new `PackPost` is made,
before its loaded programs move out. Shader/options/dimension reload creates a
new object and recomputes demand. Without demand, `center_depth_raw` remains
`None` and the renderer is never allocated; the existing conditional copy and
submission paths therefore have no resource to process. `FrameUniforms`' other
values and smoothing are unchanged. A used center-depth value follows the
original path exactly.

`HORIZON_FORCE_CENTER_DEPTH=1` forces the old always-on path for matched A/B.
Other values do not override detected demand. Each constructor logs one line:

```
shader pack center depth readback: enabled=false demand=false forced=false
```

The control must show `enabled=true demand=false forced=true` for the same
MakeUp options. DOF enabled must show `demand=true` even without force. A log
line proves a decision, not a speed gain or successful readback.

Preparation check (no compiler or device execution):

```
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 outputs/horizon-native/center-depth-demand-f42/verify_preparation.py
```

Passed: all baseline hashes unchanged, clean `git apply --check`, and patch
application in a disposable directory exactly matches the prepared files.
Five Rust tests have the prefix `center_depth_` and exercise actual parsing /
loaded shader interfaces, not source-string matching. After root stages the
full workspace, run its queue-supervised equivalent of:

```
cargo test --offline --locked --profile fast -p horizon-shaders --lib center_depth_
```

Rust compilation/tests, MakeUp force A/B, DOF-on control/reload, GPU validation,
visual parity and performance are NOT RUN by this agent. No candidate binary
is built or selected here; retain the current daily build until those checks.
