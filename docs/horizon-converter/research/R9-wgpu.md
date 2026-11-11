# R9 wgpu/Metal research (2026-11-06)

## Pinned (candidate-source Cargo.lock / Cargo.toml)
- wgpu 30.0.1, wgpu-core 30.0.1, wgpu-hal 30.0.1 (vendored+patched: third_party/wgpu-hal, Cargo.toml:70), naga 30.0.1 (vendored, GLSL-frontend patches, Cargo.toml:73), winit 0.30.13, objc2-metal 0.3.2 (0.2.2 also present, transitive). `metal` crate not used.
- wgpu features: ["std","parking_lot","vulkan","metal","wgsl","naga-ir"] (crates/horizon-client-render/Cargo.toml:59).
- Upstream horizon-rust/horizon main Cargo.toml: same (wgpu-hal/naga path patches; Cargo.lock wgpu/naga 30.0.1, winit 0.30.13). Not newer.
- 30.0.1 (2026-08-21) IS the latest wgpu release. Nothing newer released; only CHANGELOG "Unreleased" (trunk) is newer. Trunk items need git dep, not crates.io.

## Trunk (unreleased) Metal/naga items, ranked for M1 8GB (value / backport risk)
1. Metal: render pipeline switch no longer allocates per vertex buffer (#10630). Frame-time/CPU win for many pipeline switches. Risk low (internal), but needs trunk git dep.
2. Metal: fixed-count multi-draw >=512 draws goes through GPU-generated ICB instead of CPU per-draw indirect (off with STRICT_WEBGPU_COMPLIANCE). Possible CPU win if Horizon uses multi_draw_indirect; ICB memory is reported. Risk medium (new path). Unverified whether Horizon uses it.
3. Queue::write_buffer/write_texture coalesce barriers into one per batch (#1xxxx, JMS55). General; Metal has little barrier cost, so small benefit on M1.
4. naga MSL: textureSampleGrad emitted metal::gradient2d for 3D/cube (#10573) - correctness (shader fail), only if packs use it. Also MSL loop `continuing` wrong-code fix, storage-texture-as-fn-arg crash (#9867). Correctness, low risk.
5. Metal surface: new-window Occluded status fix (#10302), CoreGraphics color-space hang fix (#10175, only Bt2100/P3 spaces), sRGB wide-gamut oversaturation fix (#10286), texture-view creation error not panic (#10145). Low value, low risk.
6. BREAKING: CompositeAlphaMode PostMultiplied -> PreMultiplied on Metal (#9922). Horizon uses Opaque (gfx.rs:2160, compositor.rs:88): unaffected.
- NOT present anywhere in changelog: Metal PipelineCache (PipelineCache is Vulkan-only, #5319), argument buffers/bindless perf, heap/residency work, command-buffer poll hang fixes, MSL bounds-check codegen perf, shader compile-time work. Metal compile stutter is not addressed upstream.
- Recommendation: stay on 30.0.1; backporting trunk = git dep + patching vendored wgpu-hal copy; gain small. Cherry-pick #10630 and #10573 into third_party/wgpu-hal / naga only if profiling shows pipeline-switch CPU cost or those shaders.

## Horizon settings (file:line, crates/horizon-client-render/src)
- MemoryHints::MemoryUsage already set: gfx.rs:1875 (comment says Vulkan/DX12; no-op effect on Metal). Device request on macOS skips horizon_hdr (gfx.rs:1879-1887).
- Present mode: gfx.rs:2122-2130 prefers previous, else Mailbox, else Fifo (Mailbox unsupported on Metal -> Fifo). Offscreen path Immediate: gfx.rs:2157. Splitscreen Fifo: gfx/compositor.rs:86; vsync off -> Mailbox/Immediate: compositor.rs:105.
- desired_maximum_frame_latency: 2 at gfx.rs:2158 and compositor.rs:87; main surface uses get_default_config (default 2). Cheap win: try 1 for lower input latency (costs throughput/hitch tolerance; not a memory win; Metal nextDrawable limit is 2-3 so keep 2 for hitching). No change recommended.
- Bounds checks: grep found no ShaderRuntimeChecks / create_shader_module_trusted / runtime_checks anywhere -> defaults (full checks) on all create_shader_module calls (oit.rs:192, pack_post.rs:812, terrain etc). Cheap win candidate: unchecked shader modules for the trusted built-in terrain/OIT shaders (NOT user shader packs) via create_shader_module_trusted(ShaderRuntimeChecks::unchecked()). Gain on M1 unmeasured/unverified; API existence in 30.0.1 not verified (check wgpu docs before use).
- No pipeline-cache code for Metal. Instance flags: VALIDATION_INDIRECT_CALL removed in release for non-DX12 (gfx.rs:1522-1527) already good.
- Only DX12 has a disk shader cache (gfx.rs:1519, third_party/wgpu-hal/src/dx12/disk_cache.rs). Metal analogue (MTLBinaryArchive / on-disk MSL cache) would be a new vendored-hal feature: highest potential for compile stutter, high effort.
