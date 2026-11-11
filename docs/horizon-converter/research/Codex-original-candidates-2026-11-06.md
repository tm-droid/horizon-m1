# Original M1 / Java-performance follow-up

User steering: write original beneficial optimizations as well as ports; think proactively across engine, shader, launcher and instance; use our own porter (tools/horizon-convert.py, v4 porting-index and per-mod tasks).

## Parked prototype: HUD depth-run batching
- f42 native/stage crates/horizon-client-render/src/hud.rs contains NUL: use rg -a or read_text. HudRenderer at2225, draw_range at2677.
- draw_range partitions each Blend::Depth([u32;4]) into a separate Load/Store color pass with a freshly cleared depth buffer. Normal alpha runs are already grouped; empty ranges return early.
- Original optimization: merge consecutive depth runs ONLY where their physical clipped scissors are pairwise disjoint. Clear depth once per group, preserve run order, set scissor for EVERY run. Overlapping scissors and intervening non-depth blends split groups. This preserves depth isolation where pixels can overlap while reducing Metal/TBDR attachment traffic.
- Preserve exact old scissor scaling/clamping. Introduce env HORIZON_HUD_DEPTH_BATCH=0 as control, default on only in an unselected trial binary. Unit tests for disjoint/touching/overlapping/clipped/zero clips and mixed blend boundaries. No pixel or speed claim until actual GPU/image tests.
- Make patch under outputs/horizon-native/hud-depth-batch-f42; pristine stage never edited. Build separate r6 by applying r4-stack17 + custom patch through queue; existing r4 builder can be reused via a small dedicated driver using build-nightly-6475f62 helper process supervisor. Preserve inherited CEM+Zoom metadata; no auto-selection.
- Cow fixture currently has empty hotbar, so add optional harness fixture filling nine hotbar slots with distinct single 3D block items, verifying inventory readback before timing. A/B same r6 binary env0/env1; inspect HUD GPU timings, frame lows, images. Existing harness cow review can still validate camera/packs/etc; fixture readback is an additional check.

## Java performance gap: block-entity occlusion
- Do not blindly add per-entity callbacks: nightly game.rs11479-83 says ordinary entity occlusion disables per-section GPU cache. Vanilla chests/signs/banners use visible_block_entities_in_frustum -> render_with_gpu_cache_options, separate from mod_block_entity_geometry.
- Relevant nightly paths: gfx.rs5747-5791 (BE section/distance/frustum); block_entity_render.rs1233-1247 (StaticSectionSnapshot); game.rs11456-11525,16368-16555 (publish/render cached geometry).
- A cache-preserving section visibility approach needs bounds/occluder audit and a chest-wall stress fixture. Existing entity_hidden_sync_camera_bounds accepts camera-relative AABBs but per-block use could lose more caching than it saves. No new port claimed yet.
- Worldgen density/noise already caches nodes/worker cells; no hit/miss counters found. Profile novel-terrain CPU before adding NEON or new caches; exact worldgen parity required.

## M1 shader trace
- gfx/pack_timing.rs env HORIZON_SHADER_PACK_TIMING stores15-sample medians and logs every30 timed frames. U13 runner captures lines.
- Buffer sizes can be relative/absolute; scale.program is viewport-only, not texture resize. Half-res AO/cloud requires identifying actual MakeUp outputs and upsampling consumers.
- HUD/screen-effect pass merging is scene-dependent; normal empty-hotbar frame is not evidence of many depth runs.

## Applicability correction after tracing callers
The HUD depth-batch patch was prepared and fresh-reviewed with no blocking correctness issues, but live depth_since calls are character/armor-stand previews, not item icons. Filling the hotbar would not exercise it. It is parked without a device build or performance claim. Its unused build driver was removed.

The BE cache trial likewise passed preparation/static review but is inapplicable to the current MakeUp/custom-model-pack profile: the existing culler is off, requires vanilla model packs, and shader shadows/pack_ids are bypassed. Keep it opt-in research; do not integrate it into the daily build or claim it improves this profile.

Current original-code priority is the measured MakeUp deferred pass (~4ms). Worker m1_shader_prototype is implementing an isolated half-resolution affine AO/cloud coefficient + depth-buffer pass and an original full-resolution depth-aware reconstruction, preserving original full-resolution scene buffers, with original-deferred fallback at mismatches/underwater. All speed/visual claims await device testing.

## Explicit user preference after the comparison image
User: "I like how makeup looks a lot more than daybreak from this image." Keep MakeUp as the daily visual target. Native Daybreak remains comparison/compatibility research only. Do not switch the daily shader away from MakeUp on FPS alone. Any custom M1 variant must preserve MakeUp appearance in device visual checks.

## Broader continuation after handoff checklist
User clarified the checklist was only continuation, not projectfinish. New bounded units: demand-gate unused centerDepthSmooth readback on dailyMakeUp; distinguish freshgeneration from disk/mesh/upload/GPU stalls with first-pass/revisit flight; verifyproperquad primarybackend semantics before newshadercode. Two halfresprototypes have since completedGPU screens without convincingoverallwins; earlier "workerimplementing" status is historical. Centerdepthproposal has concrete dailyapplicability: MakeUp only requests it withDOF, which isoff. Unused path currently still polls/render/copies/maps everyframe; no gain claimed untilcompiled A/B.
