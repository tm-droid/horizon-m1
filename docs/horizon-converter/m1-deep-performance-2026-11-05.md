# M1 performance investigation

This pass investigates the installed f42 engine at source level and measures original and modified clients on the M1 Air with 8 GiB RAM. The inherited Java options remain experimental evidence. The full 52-pack stack and recorded view define the initial comparison scene.

## Source findings and priorities

| Finding | Work avoided or cost | Planned check |
| --- | --- | --- |
| Iris explicitly disables vanilla clouds after their mesh has already been prepared and uploaded | Rebuilding a cloud mesh that the active shader never draws, especially while moving | Preserve real cloud-program inputs, native shader policy and title behavior. Compare native patch against a client from the same compiler/profile. |
| Shadow visibility creates a fresh temporary vector and deduplication set per frame | Repeated allocation and hashing setup on a render-thread path | Reuse cleared renderer-owned buffers with the same standard hash type, culling and ordering. Check repeated capacity and exact results, then real images and timings. |
| Pure CEM animation state takes a mutex even without persistent variables | A lock per eligible animation draw | Low priority for the current scene. A bounded real-pack scan found only eight effective variable-free assignment programs among95 examined models. Cow and chicken are stateful. |
| Post passes upload uniform blocks every bind | Potential duplicate writes and staging allocations | Low priority until hit-rate evidence exists. These packs declare changing time, random, camera and sky uniforms, including declarations not statically used by a pass. |
| Terrain upload scheduling | Automatic small-batch fast path or2/6 ms burst windows | The tested512 KiB limit gave no useful win and worsened recovery. Further scheduling experiments need distinct evidence and must count delayed geometry. |

Horizon already has reusable terrain staging belts and Metal-specific draw/submit policies. These existing measures are part of the baseline. This work uses original Rust code under Horizon's MIT terms. It does not copy Sodium implementation code.

## Measurement plan

Collect a separate native-client diagnostic with named CPU spans enabled. Its clock and logging overhead makes it a diagnostic run only.

Compile a fresh source copy containing the reviewed cloud and scratch transforms. Preserve the original injected source, original binaries, exact source hashes and a separate candidate identity. The existing Zoom/CEM native client is the initial control. Both sides use Rust1.99.1 and the Cargo fast profile. Publisher-release FPS is a separate comparison.

Run repeated original/patched/patched/original shader-heavy cases and reversed shader-off cases. Each case uses the same full-stack scene, native2560×1440, auto workers, Unlimited with VSync off, a20-second stationary window and the same16-second flight. Record CPU, GPU, frame tails, loading state, memory snapshots and full-frame captures. Keep the diagnostic instrumentation out of these timing runs.

New GPU-free tests verify the actual cloud predicate and shadow merge behavior. A full real build checks Rust integration. A fresh reviewer checks source changes and build ownership. The final table will record rejected candidates and remaining image or timing uncertainty.

## Implementation and verification checkpoint

The cloud transform in `outputs/horizon-native/cloud-prep-f42/` changes two guarded source files. It stores the explicit Iris `clouds=off` property separately from the existing “hides clouds” flag. The latter also includes packs that replace vanilla clouds with a real cloud program, which still needs cloud geometry. Title and native shader guards are retained.

The scratch transform in `outputs/horizon-native/shadow-scratch-f42/` adds renderer-owned vector and standard hash-set storage. Each pass clears them before use. It preserves the original merge order, duplicate filtering, hash algorithm and shadow sort. The combined renderer source SHA256 is `b6bfa796c0c3b72c4298a07aa3429c0042e1b14efc99c2864a6f94bfebdc0a61`.

Queued verifier ticket74 passed36 extracted cloud guard cases and2 real Rust shadow merge/capacity tests. The tests include repeated warmup capacity, camera/scene changes, and exact sequence equality. Python source transforms and compile checks passed. Independent review found no blocking patch/build issues after atomic installation and process observer fixes.

The build runner now compiles both the unmodified control and patched candidate from the same owned source path, command and toolchain. This addresses the incomplete historical full-source provenance of the previous native binary. Each installation records its entire source inventory and binary digest. Queue75 owns compilation. Queue76 is reserved for eight interleaved tests after successful builds.

The separate diagnostic found render waits as well as CPU work. Sample slow frames showed shadow visibility around0.6–1.2 ms wall time and0.1–0.3 ms thread CPU. Surface acquisition took around11–17 ms wall time with much lower thread CPU in several frames. These samples support investigating redundant work, with the shader GPU load still a major limit. Instrumentation changes clock/logging cost, so this run is excluded from speed comparisons.

The deeper scan demoted the pure-CEM mutex and UBO-copy ideas. Only8 variable-free models had effective assignments among95 examined records, and the tested cow is stateful. The active shaders declare changing time/random/camera data in their uniform blocks, reducing expected exact-copy-cache hit rate. Both ideas need workload evidence before implementation.
