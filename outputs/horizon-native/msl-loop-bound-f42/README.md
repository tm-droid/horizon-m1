# msl-loop-bound-f42

Not compiled. Written 2026-11-06 (R20). Touches only the vendored `third_party/wgpu-hal/src/metal/device.rs`, which no r3 patch touches. It applies to the stage with or without r3.

## What
wgpu's safe `create_shader_module` sets `ShaderRuntimeChecks::force_loop_bounding = true`, and on Metal naga's MSL writer then adds this to every loop (`third_party/naga/src/back/msl/writer.rs:1079-1093`):
```
uint2 loop_bound = uint2(4294967295u);
... if (metal::all(loop_bound == uint2(0u))) { break; }
loop_bound -= uint2(loop_bound.y == 0u, 1u);
```
This patch turns that off for every Metal shader unless `HORIZON_MSL_LOOP_BOUNDING=1` is set. Bounds checks (`Restrict`) stay on.

Horizon cannot use the per-module opt-out (`create_shader_module_trusted`): it is `unsafe`, and `horizon-client-render/src/lib.rs:3` has `#![forbid(unsafe_code)]`. So the switch lives in the vendored hal.

## Why (M1)
MakeUp's GPU-heavy passes loop on every pixel: deferred AO and volumetric clouds, composite volumetric light, and the composite1 bloom/DoF taps. The counter adds about 5 ALU ops plus a branch per iteration, and it may stop Metal's compiler from fully unrolling fixed-count loops. Expected gain: 0-5% of the loop-heavy passes' time. This is not measured, and it may be ~0.

## Risk
- Look: none. The bound only changes behaviour for a loop that would never end.
- Stability: a shader that really loops forever would hang the GPU until Metal's command-buffer timeout (device lost) instead of breaking out. GL (Iris on macOS) runs the same packs with no bound. `HORIZON_MSL_LOOP_BOUNDING=1` restores the old behaviour.

## Verify
A/B MakeUp with and without `HORIZON_MSL_LOOP_BOUNDING=1` on the same build: it needs no rebuild between arms, and it is the cleanest A/B available. Add `HORIZON_SHADER_PACK_TIMING=1` to compare per-pass GPU times.
