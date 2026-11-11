# Keep shader-pack entity bodies separate from the native energy swirl

`pack-energy-swirl-split.patch` applies to `crates/horizon-client-render/src/gfx/pack_entities.rs` in exact r8. Both r11 build source copies had identical bytes in that file and also passed the apply check.

The baseline's pack eligibility test examines a whole entity span. A charged creeper or powered wither appends its additive energy swirl to the body span, so tag 34 sends both the shell and the body to native fallback and excludes the span from pack shadows. The candidate splits aligned CPU entity spans containing only ordinary and swirl quads into consecutive runs. Ordinary runs use the same entity pass availability, visibility, shadow eligibility, uniform metadata and offset code as other pack runs. The swirl remains on the native additive path and casts no pack shadow. Order is stable inside each output. Spans with any other fallback-only material, including mixtures with the swirl, keep the existing whole-span behavior. Destroy projection, non-entity stages and the GPU-skinned route are unchanged.

`git apply --check --whitespace=error` passed in r8 and both r11 copies. The added pure routing test covers interleaved ordinary and swirl quads, unsupported tags, a non-entity stage, malformed quad alignment and destroy projection eligibility. No Rust build or game launch was run.

The whole-span fallback is a hypothesis for the MakeUp appearance difference. If the shader pack has no applicable entity gbuffers pass, the body still falls back natively. The patch does not change the shell's blend, exposure, texture, timing or target. An active MakeUp comparison of fixed-view powered and ordinary creepers is needed to see whether the white shell changes.
