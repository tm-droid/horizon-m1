# R16: resolution scale and upscaling (Horizon f42ef42, M1 Air 8 GB, 2560x1600)

Paths below are under `outputs/horizon-runtime/m1-performance/candidate-source/crates/`.
R8/R2 only listed the knobs. This note covers the mechanism, the shader-pack path and upstream.

## 1. Options and filter
File `horizon-graphics.txt` (next to options.txt), `key:value` lines (`graphics.rs:11`, serialize `:832`).
- `resolutionScale:<int>` percent, clamp 50..200, default 100. Parsed `horizon-client-render/src/graphics.rs:787`, default `:672`. UI slider is 50..200 in 5% steps (`graphics_ui.rs:836`). Applied as `scale/100` (`horizon-client/src/game/options.rs:494`). `set_world_post` clamps it again to 0.25..2.0 (`gfx.rs:5625`).
- `taa:true|false` (`graphics.rs:788`), `fxaa:true|false` (`:788`). `set_world_post` makes FXAA off whenever TAA is on (`gfx.rs:5626`).
- `upscaling:native|quality|balanced|performance|ultraPerformance` (`graphics.rs:790`, names `:404-410`). Ratios per axis: 1.0 / 1.5 / 1.7 / 2.0 / 3.0 (`:423-429`). The world renders at `window*scale/ratio` (`world_post.rs:262-269`). It only applies when TAA is on (`gfx.rs:5628`).
- Filter:
  - TAA off (scale < 1 only): `fs_copy` through a Linear/Linear sampler, so plain bilinear (`world_post.rs:233-234`, `world_post.wgsl:20`).
  - TAA on: custom Halton(2,3) jittered temporal accumulation (`world_post.rs:282`), 3x3 neighbourhood clamp, Rgba16Float history at output size, Catmull-Rom history sample (`world_post.wgsl:71-130`). It is FSR-like in its jitter and ratios but not FSR2. There is no MetalFX, no FSR spatial and no sharpen pass (rg found none). "FSR 3.1" in the source is frame generation only (`frameGeneration`, `graphics.rs:1042`), not upscaling.
- Shader packs (Iris-style): `pack_reads_world = pack_post || native_post` forces the scaled target (`gfx.rs:7772`, `:7826-7830`). The pack's buffers use `world_post.size()` (the scaled size). So MakeUp renders at the scaled resolution, not native.
- TAA is off under a shader pack: `taa` requires no pack post (`gfx.rs:6350-6352`, doc `world_post.rs:68`). With a pack, `upscaling` does nothing and only `resolutionScale` plus bilinear applies.
- Bug in this checkout: `final` is drawn straight to the full window, so packs whose final uses `gl_FragCoord` (Photon) show the picture in one quarter (issue 9291). The fix PR 9927 (commit bd340bf, merged 2026-11-05) adds an offscreen scaled `final` plus a stretch copy. f42ef42 lacks it (`rg vs_screen` finds nothing in `gfx/pack_post*`). Check MakeUp at 75% for a shrunken or black picture. If it happens, cherry-pick 9927 (see R4).

## 2. HUD
The HUD stays native. The doc says the scaled world is drawn "under the hand and HUD" (`world_post.rs:1-3`). `world_post.finish` writes the world to the swapchain view, then `draw_overlay` draws the HUD, hand and crosshair at full size (`gfx.rs:9201`, `:9453`). `hand_in_world` is only true when `scaled.is_none()` (`gfx.rs:7838`), so a scaled world draws the hand natively too. `hud.zoom` only changes for scaled screenshots (`:6140`). Text and UI stay crisp.

## 3. Upstream (horizon-rust/horizon, after 2026-11-03, via `gh`)
- Issue 9291 "Resolution scale with shaders" (closed 2026-11-05): Photon at 50% on an M2 Air showed the image in 1/4 of the screen. Fixed by 9927 (above). It has no FPS numbers.
- No PR or issue about MetalFX, FSR upscaling or dynamic resolution (searched upscal/fsr/metalfx/TAA/dynamic resolution). Dynamic resolution and thermal scaling stay unimplemented (R8 point 3).
- Upstream main is far ahead of f42ef42 (compare shows thousands of commits).

## 4. Recommendation
The user's shader (MakeUp Ultra Fast) means TAA and `upscaling` are inactive, so the only lever is `resolutionScale` with a bilinear stretch. Pixel count falls with scale squared: 0.8 = 64%, 0.75 = 56%, 0.67 = 45%.
Benchmark in this order, in the usual way (R10), with everything else fixed:
```
resolutionScale:100   (baseline)
resolutionScale:80
resolutionScale:75
resolutionScale:67 is impossible from the slider (5% steps); use 65 or 70
```
Lines to set for each run (edit only with the game closed, keep the other keys as they are):
```
resolutionScale:80
taa:false
upscaling:native
```
Run 100, 80, 75 and 70 first (about 20 s overlay reads each). The 5% UI steps run 50..200, so 80/75/70/65 are all valid. Expect softness on foliage and distant detail from the bilinear stretch. 80% is the likely best look-for-FPS point. Do not expect TAA upscaling to work with MakeUp. If a no-shader test is wanted, `taa:true` + `upscaling:quality` at `resolutionScale:100` gives about 0.44x the pixels (1/1.5 per axis) with a TAA look.
Check first that MakeUp's final is not shrunk (see section 1).
macOS "scaled display": the drawable follows the window's backing size (`config.width/height`, `gfx.rs:7828`). I did not verify where the backing size is read (wgpu/winit). R8 notes `NSHighResolutionCapable` gives a 2x drawable. The in-game scale multiplies whatever backing size macOS gives. The default Air mode "looks like 1440x900" has a 2880x1800 backing, which is more than 2560x1600. A "More Space" mode (1680x1050, backing 3360x2100) costs more pixels still. So the display mode matters as the base: pick the default or a smaller "looks like" mode first, then apply scale. Check the real drawable size from the Horizon log or an overlay before trusting these numbers.
