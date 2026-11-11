# MakeUp M1 HalfRes — experimental source fork

Based on Javier Garduño's MakeUp Ultra Fast 9.6; upstream LICENSE and every
unmodified source entry remain in the ZIP. Original M1 additions and modified
MakeUp sources are LGPL-3.0. This is an independently named prototype,
not an upstream release. Rebuild with `python3 outputs/horizon-native/makeup-halfres-prototype/build.py`
from the ElyPrismLauncher data root. Builder and GLSL source are distributed
together; generated GLSL sources are also readable inside the ZIP.

Overworld deferred computes AO and cloud affine coefficients into isolated
half-size colortex8 (signed RGBA16F) and depth into colortex9 (R32F). Added
full-size deferred1 reconstructs coefficients with depth/sky/hand gates, applies
them to the original full-size scene, and writes original colortex1/gaux1.
Underwater, Distant Horizons, and depth discontinuities recompute the original
full-resolution deferred shader. Nether, End, custom dimensions, geometry,
translucency, SSR, bloom, TAA and final remain on their original graph.

This changes AO/cloud spatial sampling and noise; visual parity is not claimed.
Depth-compatible thin effects, cloud boundaries and fast motion require image
review. Small depth detail inside the 1%/2cm gate can receive interpolated AO.
The fallback may erase savings in detailed scenes. Extra textures, a full-size
reconstruction pass and fallback code can make this slower. No shader compiler,
GPU run, speed claim, or device validation has been performed.

The sidecar is the complete u9c trim sidecar copied byte-for-byte. The real
Tanush instance and original pack are read-only inputs and are never modified.
