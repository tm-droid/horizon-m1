# MakeUp M1 HalfRes r2 — experimental reconstruction revision

An independently named LGPL-3.0 source fork of Javier Garduño's MakeUp Ultra
Fast 9.6. The upstream LICENSE and source files remain in the ZIP. Original
M1 additions are LGPL-3.0. Source, builder and tests accompany the artifact at
`outputs/horizon-native/makeup-halfres-prototype/`.

Rebuild: `python3 outputs/horizon-native/makeup-halfres-prototype/build_r2.py`.
This writes only MakeUp-M1-HalfRes-r2.zip, its complete u9c options sidecar and
manifest-r2.json. The first prototype and real Java instance remain unchanged.

Same half-size cloud/AO affine coefficients and depth buffers as r1, same
full-size original scene, same four depth/sky/hand gates and original fallback.
Reconstruction now checks guides before reading any coefficients. Underwater
and Distant Horizons return the original shader before all auxiliary work.
Exactly equal-depth neighborhoods use one hardware-bilinear coefficient sample
instead of four manual taps. All other accepted pixels retain four weighted
coefficient samples. No tolerance or sample rejection rule is loosened.

R1's first device screen was slower than baseline: the added reconstruction
erased half-pass savings. This revision has no GPU timing or visual result yet.
Hardware interpolation can differ slightly in rounding from manual arithmetic;
no speed or pixel-identical claim is made. All r1 spatial sampling, quantization
and temporal-quality limits remain. Nether, End and custom dimensions are
unchanged. Nothing selects this pack automatically.
