# Original MakeUp M1 half-resolution prototype — 2026-11-06

Implemented an isolated, unselected GLSL prototype in
`outputs/horizon-runtime/game/shaderpacks/MakeUp-M1-HalfRes.zip` with matching
`.zip.txt` sidecar. Source/builder/tests/manifest are in
`outputs/horizon-native/makeup-halfres-prototype/`. No Java instance, original
pack, native engine source, harness, runner, selected pack or game settings were
changed. No game, compiler, Cargo, GPU test or external download was run.

This addresses U13's measured roughly 4ms deferred pass. It does not claim a
speedup: M1 timestamps rank work but do not predict frame-time savings, and
the extra pass and conservative fallbacks may cost more than they save.

## Graph and renderer evidence

Original MakeUp `common/deferred_fragment.glsl` computes clouds on sky pixels,
AO, underwater sky correction and clamp, then writes `DRAWBUFFERS:14`:
colortex1 scene colour and gaux1/colortex4 SSR source. Those existing attachments
must stay full resolution: geometry and later translucent SSR use them.
No packed gbuffer or full-resolution scene colour is interpolated by this fork.

Horizon f42 pristine `horizon-shaders/src/post.rs:237-275,641-681` supports actual
`size.buffer` dimensions and ordered deferred/deferred1 through deferred99.
`config.rs:14` supports 16 buffers. `horizon-client-render/src/gfx/pack_post.rs`
checks matching output sizes (`1930-1947`), allocates each target at its own size
(`3563-3612`), and selects the output attachment size for the pass (`4182-4189`).
This is real reduced texture allocation/work, not `scale.program` viewport-only
rendering. The numbered deferred pass runs before translucent geometry
(`4154-4158`), so gaux1 is ready for SSR at the same graph boundary as before.

Only `world0` (overworld) changes:

| Stage | Inputs | Outputs | Resolution |
|---|---|---|---|
| existing opaque world | original | original MRT 0–7 | unchanged/full |
| deferred, modified | original full scene/depth and cloud texture | colortex8 RGBA16F affine RGB offset + scalar multiplier; colortex9 R32F raw guide depth | 0.5 × 0.5 |
| deferred1, new | full scene/depth + 8/9 | original 1/4, with original output meanings | full |
| translucent/composite/composite1/composite2/final | original | original | unchanged |

The half pass expresses the effect as `result = source * multiplier + offset`.
Overworld clouds are affine in source colour (optional boost, then cloud mix);
AO multiplies that expression. Tracking the scalar exactly permits full-size
sharp stars, sky, terrain and other source colour to survive reconstruction.
RGB offset is signed HDR and the multiplier can exceed one, hence RGBA16F;
an unsigned packed RGB format would be incorrect. Raw depth uses R32F so it
does not lose precision to half-float. Clamp remains after reconstruction.
The upstream volumetric cloud loop itself remains unchanged.

Upsampling uses four explicit low-resolution texel centres, bilinear weights
attenuated by linear-depth difference, and full-size original source colour.
All four guide samples must agree with the full-size sky classification and
hand cutoff, and lie within max(2cm,1% of view distance). Otherwise the pixel
executes the original deferred computation at full resolution. Underwater and
Distant Horizons always use that full-size fallback because their sky/depth
paths require additional per-pixel treatment. Odd/tiny dimensions follow
Horizon's floor-and-at-least-one buffer sizing. All new pixels are written
each frame, so no temporal auxiliary history is assumed.

Nether, End and root/custom-dimension shader sources remain byte-identical.
The half pass's underwater values are unused; they do not approximate
underwater effects. Production uses no Distant Horizons, but its fallback is
explicit rather than silently sampling its depth with half-size coordinates.

## Correctness limits and next validation

AO and clouds intentionally change spatial sampling and dither. Depth gating
protects silhouettes conservatively, but small depth changes inside the gate
can soften AO. Coefficients can smooth cloud detail. Motion, foliage, thin
geometry, horizon/sky edges, high-contrast stars/sun, water and near-hand views
need matched images. AO's existing 0.56 hand cutoff is preserved. Float16 effect
storage adds quantization. No visual parity or speed claim is made.

Extra cost: two ping-pong low-size attachments, four coefficient/depth samples
per full-size pixel, a full-size MRT pass, and duplicated shader fallback code.
At 2560×1600, the new 12B/pixel low-size pair is about 12.3MB per side, before
driver overhead. Any detailed scene may trigger many fallbacks. A GPU compiler
could flatten divergent work; only real timing can settle the result.

Parent's next controlled device slot should verify pack translation/load (no
skipped `deferred`/`deferred1`), whole-screen output, guide-size behavior, the
listed image cases and all eight inherited trim options. Then compare matched
u9c trim versus this pack on the same binary, world, resolution and camera.
Capture `deferred` plus `deferred1` timings and frame time, not just one pass.
The prototype is not selected automatically.

## Reproduction and checks

`python3 outputs/horizon-native/makeup-halfres-prototype/build.py` → exit 0.
Builder uses stable ZIP timestamps/order, preserves upstream LICENSE/source,
copies the complete u9c trim sidecar byte-for-byte, and asserts the source ZIP
remains byte-identical. Source SHA256:
`71319ea5d0ad114143ef1c334890e315dbf1eeb2318d6bc35f3e5021fb3c8ba8`.
Output hash and exact changed ZIP entries are in `manifest.json`.

`python3 -m unittest discover -s outputs/horizon-native/makeup-halfres-prototype -p test_prototype.py -v`
→ exit 0, 3 tests passed. Checks cover deterministic rebuild/source immutability,
sidecar identity, ZIP CRCs, preservation of all unmodified source entries,
include closure, isolated output sizes/formats and output routing, plus 2,000
randomized independent comparisons of the original boost/cloud/AO expression
against affine reconstruction applied to a different full-size source colour.
These are static/numerical checks, not GLSL translation or GPU validation.

## First device screen and bounded r2 follow-up

Parent subsequently ran the controlled GPU screen: r1 loaded seven programs
with strict validity, but averaged 54.2FPS versus 57.3FPS baseline (-5.5%).
Reported footprint was 2789 versus 2733MB. Baseline deferred was 3.643ms;
r1 half deferred 1.260ms plus reconstruction 2.458ms totaled 3.718ms. Other
pass times drifted slightly, so this supports rejecting r1 as a speed winner,
not attributing every frame difference to reconstruction. Parent owns run logs
and image inspection. This agent performed no device test.

Source diagnosis: r1 performs four guide reads, four coefficient reads and
their weighted accumulation before checking `compatible`; even rejected
pixels and underwater/DH pixels then execute the full original shader.
Its all-four depth gate conservatively rejects sloping or detailed geometry,
but no fallback-coverage measurement exists, so fallback frequency is still
unknown. Standard/renderer macro definitions inspected do not define
DISTANT_HORIZONS; there is no evidence it forced the whole scene to fallback.
The extra full-size MRT write/read and duplicated pass still impose bandwidth
cost, which this shader-only follow-up cannot eliminate while keeping original
SSR/translucent pass ordering and outputs.

Created separate `MakeUp-M1-HalfRes-r2.zip` plus complete trim sidecar, retaining
r1's exact ZIP hash and source. Source is `m1_upsample_fragment_r2.glsl`, builder
`build_r2.py`, provenance `manifest-r2.json`, all under the same prototype
directory. Only the reconstruction GLSL and embedded prototype README differ
between r1 and r2 archives; auxiliary textures, half pass, graph and options
are identical.

R2 changes:

- Return original full-size evaluation before auxiliary work for underwater/DH.
- Read and classify four guides before any coefficient fetch; rejected pixels
  return original evaluation immediately.
- Explicitly express the four taps and vector gate arithmetic, avoiding loops
  and redundant current-depth conversion.
- When all four raw guides equal current raw depth exactly, r1 depth weights
  are exactly one. Use one hardware-bilinear coefficient read instead of four
  manual weighted reads. Horizon `pack_post.rs:89-124` binds filterable colour
  targets linearly; RGBA16F is filterable. Retain all four guide reads/checks.
- Other accepted pixels retain four original depth-weighted coefficient reads.

All sky/hand/depth classifications, 2cm/1% thresholds, full-resolution source
and edge fallbacks remain. No gate is relaxed. Hardware filtering can round
differently from explicit arithmetic; spatial/temporal quality still needs
parent review. Divergent GPU execution or compiler flattening can erase the
source-level work reduction. R2 has no performance claim and is unselected.

`python3 outputs/horizon-native/makeup-halfres-prototype/build_r2.py` → exit 0.
`python3 -m unittest discover -s outputs/horizon-native/makeup-halfres-prototype -p 'test_*.py' -v`
→ exit 0, 6 passed. Added deterministic r2 rebuild and r1 pinned-hash retention,
exact two-entry archive delta and sidecar identity, 10,000 random gate
equivalence cases, and manual-versus-filtered bilinear numerical comparisons
including clamp borders, odd framebuffer sizes and one-pixel targets.
Fresh read-only source review found no blocking correctness gaps. No compiler,
GPU run, harness or runner change was made for r2.

## Coordinator R2 device screen (2026-11-07)
Queue156 completed2/2valid single-screen cases, retained in outputs/horizon-runtime/u12-native-m1r2.json. MakeUp58.5static/48.1flightFPS, flight1%low29.8; R2 59.8/47.2, flight1%low19.5, footprint+54MB. All seven programs loaded; no GLvalidation/refusal. This weak static gain with weaker flight/lows and added memory is insufficient for promotion.

Across all saved world-pass timing lines (32reference/37candidate, mixing measured phases), medians were originaldeferred3.623ms; R2halfdeferred1.301ms and reconstruction1.514ms. Sum-of-pass-medians2.815ms suggests reconstruction work improved, but is not a synchronized end-to-end frame measurement or a repeated performance confirmation. Keep original MakeUp selected; no further confirmation batch is justified by this screen alone.
