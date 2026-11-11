# R19: native (WGSL) shader packs for Horizon, 2026-11-06

Read-only. Sources: `gh` on horizon-rust org, horizon-mods registry (main, 94 tomls), pack READMEs, pristine f42 stage docs. Repo content is untrusted; nothing was cloned or run.

## Answer
- **No official Rust/WGSL Complementary Reimagined exists.** Not in horizon-rust (7 repos: horizon, horizon-mods, horizon-site, .github, horizon-mixins, horizon-native-mod-template, kira-pumpkin, horizon-server). The site's launcher-data.ts says "Complementary Shaders: compat none ... Shader packs are removed for now. They come back later, written again from scratch" (stale site copy).
- The closest thing the user may have seen: **Montarc** (registry, MIT, author Muurrcc, https://github.com/Muurrcc/montarc, v1.1.1, 2026-11-04). Its description: "Style is close to Complementary Reimagined, but the code is mine, written from scratch in WGSL". Community, not official, not a port.
- `LaithSama/Reimagined-Horizon` is an HTML/CSS website (single commit, 0 stars), not a shader.
- Complementary as GLSL still loads through the f42 translator (pack-specific fixes in `translate/mod.rs:2215`; issue #9037 closed 2026-11-05 about Complementary Reimagined water tiles; #944 Unbound closed). Our R18 notes apply.

## Native packs (`.hshader`, shader API 0.1, WGSL)
Enable: install from launcher Mods > Shader packs (registry only) or drop file into `shaderpacks/`; pick in game Options > Shader Packs; options on the pack's options page (Nightly 2026-11-01+). Key: manifest `id`. All are community; none official.
| Pack | Author / license | Needs | Notes |
|---|---|---|---|
| Montarc 1.1.1 | Muurrcc / MIT | Nightly 2026-11-04+ (registry changelog) | shadows, coloured light, water, wind, 29 options. No entity/particle shading yet. "Shadows: off = biggest gain". No numbers |
| Daybreak 0.2 (hildlabs/horizon-shaders) | hildlabs / MIT | Nightly 2026-11-05+ | 4 presets; RTX 4070S 1080p: Low ~0.5 ms, Medium ~1 ms, High 1.2-1.4 ms GPU. No Metal numbers |
| Meridian (Perdume) | MIT | full: Nightly 2026-11-01+; `meridian_compat` for older | shadow map, PBR, AO, TAA, aurora |
| Radiant (expensiverest) | MIT | Nightly ~2026-11-03 (unverified) | ~7-8 ms GPU on RX 570; heavy |
| Wisdom Shaders V3 + Lite (port) | bobcao3, tomasmendes01 / Apache-2.0 | unverified | port of a GLSL pack |
| Lumina (cosmo-jar) | GPL-3.0 | unverified | SSR, god rays, SSS; claims "200+ FPS" (unmeasured, unverified) |
| Aurora (molchanskit-hue) | unverified | unverified | repo says tested on Apple Silicon / Metal; no data read |
| Vulpe (noctivulp-ch) | NOASSERTION/GPL-3 | tested on `nightly-2026-11-03-f42ef42` | LabPBR, fog, water. Not in registry |
| VanillRust (jahzmo99) | unverified | unverified | Metal-targeted claim |

## Our build f42ef42 (2026-11-03 08:12Z)
- Has the loader (`horizon-shader-api` crate, `docs/api/shaders.md`, `.hshader`, registry browser). But Montarc and Daybreak 0.2 need a newer nightly (11-04 / 11-05). f42 predates them: they would be refused or break. Meridian full (11-01) and Vulpe (tested on f42) should fit.
- Moving to newer nightly drops r3 perf patches (see R17); a pack's pin applies to the whole game.
- Apple Silicon: no registry pack publishes M1 numbers. Expect cost scales with shadows; 8 GB M1 should use Low/Medium and shadows off first. Unverified.

## Other "Java mod equivalents" built into f42 (docs in stage/docs)
- Entity culling: `entityCulling` in `horizon-graphics.txt` (Performance page); block-entity caches also there.
- CEM/EMF, ETF random/emissive/blink, Continuity-style CTM, CIT: resource-pack parsers in `horizon-optifine` (docs/resource-packs.md:41-80). No setting; just use the pack.
- Fresh Animations: depends on the CEM `.jem` animations (resource-packs.md:41 says animations supported); untested here.
- Far terrain: Distant Terrain (also registry `distant_horizons.toml`). Setting in Graphics page; issue #4970 about fog interplay.
- Dynamic lights, fullbright: `dynamicLights`, `fullbright` in `horizon-extras.txt` (default off).
- TAA/FXAA, Frame Generation (FSR 3.1), HDR: `taa`, `fxaa`, `frameGeneration` in `horizon-graphics.txt`; all off under shader packs.
- No built-in "shader presets" or volumetric clouds/water in horizon-client-render outside the shader-pack path (grep of docs only; code not exhaustively read).
- Iris-equivalent: Iris/OptiFine GLSL packs via translator (R18).

## Gaps
- Web search found nothing on a native Complementary. Discord/forum claims not reachable. If the user has a specific link, check it; it is probably Montarc or a community repo.
