# Shared full-stack appearance gaps — 2026-11-04

Prioritize these shared pack/rendering issues before screening more shaders. They occur in the official f42 baseline and both queue53 shader profiles. No fix is installed, and no new tests/builds/runtime work were performed by this audit.

## 1. Emissive overlays: a real native capacity limit

`crates/horizon-client-render/src/native_emissive.rs` declares `MAX=128` at line8 and reserves `NATIVE=32` at line10. Its OptiFine loader sorts ordinary blocks before CTM tiles, then stops with the observed warning when96 pairs have been collected at lines83–88. This is an actual break, not a diagnostic-only warning. No config argument controls that bound in this path. The first omitted file in this stack is `assets/minecraft/optifine/ctm/ores/deepslate_diamond_ore/3_e.png`; subsequent eligible entries are not examined.

The effective selected ZIP directories contain286 possible block/CTM `_e.png` files, including160 CTM files, supplied by New Glowing Ores and RAYs3D Rails. This is an input upper bound, **not** an exact eligible/loaded pair count: native loading requires a loaded base sprite, an existing overlay, acceptable size, successful decode and a non-shared base layer. Native skips shared base layers to avoid making unrelated textures glow. Therefore a fix must retain those safeguards. [Pinned loader and order](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/native_emissive.rs#L38).

The frame table gives native requests priority, bounds them to32 and adds loaded OptiFine pairs. `mappings` also stops atMAX. CPU `Globals.emissive_layers` derives its size fromMAX, but **both** `terrain.wgsl` and `entity.wgsl` explicitly declare128 entries; terrain's vertex lookup explicitly clamps128. Raising only the96 loader allowance or only the Rust constant is not correct. A larger table must keep CPU/WGSL layouts, loop bounds, frame upload/truncation and device uniform limits consistent. The existing sorted lookup is linear with an early exit; more entries may increase vertex cost. [Pair table](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/native_emissive.rs#L112), [terrain layout](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/terrain.wgsl#L29), [terrain lookup](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/terrain.wgsl#L393), [CPU upload](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/gfx.rs#L6464).

Smallest evidence-backed engine task: instrument/count eligible pairs, choose a bounded capacity fitting those pairs and retained native reservation, synchronize the existing table consumers, and validate the WGSL/CPU contract. Reclaiming the unused32 native slots alone cannot guarantee this stack's coverage. A sorted binary lookup is a possible accompanying cost-control change, but requires exact equivalent-results checks and runtime timing; no benefit is assumed. There is no verified player setting or native request hook that makes unloaded overlays bypass this loader/table capacity. A full rebuild remains required and is currently blocked by the separate disk-space guard.

Appearance consequence: omitted native fullbright overlays can leave affected ore/rail surfaces without their intended glow. This is strongest for the native shader-off route; custom Iris shader emissive behavior still needs night comparison. A daytime wide landscape can miss the loss entirely. Do not equate unchanged ZIP bytes with complete rendering.

## 2. `minecraft:block/`: mismatched Better Lanterns texture keys

A bounded2.1MB inspection of the selected Minecraft block-model JSON inputs found three literal empty block texture placeholders, all in layer27 `Better Lanterns v1.4.0 - 26.2+26.3.zip`. Effective lookup against all52 ZIPs plus prepared vanilla assets confirms that no later pack overrides the following parent/child combinations:

| Pack template | Template texture keys | Effective vanilla children | Child texture keys |
| --- | --- | --- | --- |
| `template_chain.json` | `chain: block/`, `particle: #chain` | `iron_chain.json` | `texture: minecraft:block/iron_chain` |
| `template_hanging_lantern.json` | `hanging_lantern: block/`, `particle: block/` | `lantern_hanging.json`, `soul_lantern_hanging.json` | only `lantern: minecraft:block/lantern` or `.../soul_lantern` |
| `template_lantern.json` | `lantern: minecraft:block/`, `particle: #lantern` | `lantern.json`, `soul_lantern.json` | `lantern` correctly overridden |

Paths are under `assets/minecraft/models/block/`. The pack's25 copper chain/lantern child models provide the new expected keys and particle textures. The prepared vanilla iron-chain and hanging ordinary/soul-lantern children do not. Thus the empty texture is evidence of a concrete template/child compatibility gap, not simply an intentional unused template. Standing ordinary/soul lantern children override the correct key and do not need this repair. Missing-texture geometry/particles are predicted by this source path; the exact affected surfaces still need a focused rendered fixture.

Native model baking resolves particle material and face materials and calls `Sprites::insert`. A failed texture becomes a magenta/black missing texture and is logged; changing only the warning would hide the symptom. [Particle/face insertion](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/models/catalog.rs#L83), [visible fallback](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/sprites.rs#L307).

Smallest candidate: a separate private overlay containing only three vanilla child JSONs. Preserve their parent and existing keys, add correct `chain`/`particle` keys for iron_chain and `hanging_lantern`/`particle` keys for lantern_hanging and soul_lantern_hanging. This preserves the selected pack's custom geometry and copper models; no global native alias or pack disabling is justified. Hash-guard the exact source templates/children before adapting. Validate daylight/night views of those three blocks and representative copper/standing lantern controls; require no missing texture and no geometry change.

Source hashes:

- template_chain: `7d000a44fe4ecaa06ce61bf52ca9768be0b5c55eebc9fca424b3344ef06defd1`.
- template_hanging_lantern: `3a53bd00983f6621e54dd7a36b1132754e576a4296bfa7208924289708861c26`.
- template_lantern: `99130fee5affc4484099fe45a017a5ffd6e97020defb929bc33d760b49d49841`.
- vanilla iron_chain: `cd7a73bd8de9eab3524deca354c6efe8c04f892e91bf1e7631a8660e1b4d4003`.
- vanilla lantern_hanging: `ff097344ea76b118a25ea4c2e389d6c07933fca340775621a4860bcc92b94d28`.
- vanilla soul_lantern_hanging: `11bb739808c76200f3d0d30aa08e3cc6083fa3355b236879facc9c9e8a869e28`.

## 3. Container GUI text shader explicitly rejected

All three queue53 logs also state that the resource pack's text shader is not used: vertex line130 fails at `getCorner(sampler2D Sampler0, vec2 texCoord0)`. This is distinct from the selected Iris shader and was missed by a shader-pack-only error filter.

Layer41 `Recolourful Containers DARK 3.1.4 (1.19.4+).zip` provides the26.3 overlay's `assets/minecraft/shaders/core/text.vsh` and text.fsh. The vertex imports the base pack's `assets/minecraft/shaders/include/interfaces.glsl`; its getCorner functions take a sampler parameter at lines15/27. The native core-text loader tries translating the pack stages, logs the failure and returnsNone, so the GUI falls back to native text behavior. Bitmap font assets loading does not restore this shader's GUI positioning/color/effects. [Pinned core-text fallback](https://github.com/horizon-rust/horizon/blob/f42ef42ef6ceccb3c6a20bea2481d87949a51c81/crates/horizon-client-render/src/hud/pack_text.rs#L32).

Exact source evidence:26.3 text.vsh SHA256 `95ab5f6d0d6885b68cdbff8e98d7e2adc3bf5b21578455b5df5612918110b25b`; interfaces.glsl SHA256 `24db1ad7921f29523fe1c5b7dcbe58eef37933e8f097f00da225ef62a738c3cf`. The archive's26.3 overlay range is97–999. Its vertex declares the Sampler0 uniform after the interfaces include and passes it onward through helper functions. Therefore removing a single getCorner parameter alone is not a verified repair. A source-compatible sampler-argument translation improvement, or a hash-guarded specialization of all relevant helper parameters/calls with correct declaration ordering, needs translator checks first. No config/hook fix is verified here.

Acceptance: translate the actual effective vertex/fragment/includes with the exactf42 core-text pipeline, then compare representative container titles/labels at the user's GUI scale and selected font. Preserve shader-off and both candidate shader cases. Do not claim restored GUI appearance from absence of a warning alone.

## Source identity

All source paths above are the local immutable f42 checkout under `outputs/horizon-runtime/launcher-data/native/source/f42ef42ef6ceccb3c6a20bea2481d87949a51c81`. SHA256s of inspected native files:

- `crates/horizon-client-render/src/native_emissive.rs`: `b712963c7735a6225bf218058afb90ad750e8b645d1359fc2557c711c994fa71`.
- `crates/horizon-client-render/src/terrain.wgsl`: `4d8ebe0d73be8b47e882e8a0c830b7d8b63a32f20f271c1e02f031a974623426`.
- `crates/horizon-client-render/src/entity.wgsl`: `4b8e1be72cda743013e69626089b39e919d6d466663c2433c3c984a8fe57a475`.
- `crates/horizon-client-render/src/sprites.rs`: `b851a31863deb48498ddb714a5eff5ca88c2fcc75ea68c0bf04ea4f64fca430e`.
- `crates/horizon-client-render/src/models/catalog.rs`: `44d0cb8287afb956b1e4adc39b7139589b3e58f8e75060a8bd510308f08a51b0`.
- `crates/horizon-client-render/src/hud/pack_text.rs`: `1e545f76936621bf08625c6261bedbd9e203176a59c80dd739d10c3e8774587e`.

No appearance fixes are activated by this report. Existing originals remain unchanged.
