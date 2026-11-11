# up-sky-octagon (upstream 89733192)
Base: nightly fdc87ae + daily7 stack (33 patches). Applies alone and after all earlier candidates (`git apply --check`). NOT compiled or run (benchmark in progress; no cargo allowed): build before benching.
Files: client-render/src/terrain.wgsl (clean cherry-pick, 25-line diff).

## What
`disc_distance` (terrain.wgsl: the sky disc at y=16 and the void disc at y=-4, per pixel) replaces atan2/floor/cos per pixel with the regular-octagon half-plane formula `max(|x|+tan(pi/8)|z|, |z|+tan(pi/8)|x|)/512` : mathematically the same edge parameter.

## Expected effect (M1 8 GB)
Fewer ALU ops (no transcendentals) per fragment on every pixel that runs the disc test; M1 GPU is ALU/bandwidth limited at high res so small but cheap win. Visually identical up to float rounding.

## Conflicts
None. Check: shader recompiles (terrain.wgsl) - any wgsl change busts the Metal pipeline cache once.
