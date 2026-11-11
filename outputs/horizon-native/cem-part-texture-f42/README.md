# Explicit textures on native CPU CEM mob parts

`cem-part-texture.patch` applies to the r8 build source at `outputs/horizon-runtime/m1-performance-r8/20261107-143005/source`. It changes the CEM parser, the mob layer's per-bone metadata, the CPU mob renderer, and block-entity load diagnostics.

The patch resolves explicit paths under `assets/minecraft/textures/entity/`, including the unqualified `textures/entity/…` form. A successfully looked-up sprite supplies the current bone and its descendants. A missing sprite inherits the closest available parent sprite or the original body sprite. An explicit subtree is skipped on the body emissive pass and secondary passes that reuse the exact custom body model. The existing atlas already walks Minecraft entity textures. The trader extension declares a 16×16 pouch texture and a matching 16×16 texture size, with the pouch boxes on child bones.

Scope is static texture selection on the base mob model. Part-level random texture rules, blinking, emissive companions, OptiFine sprites, block-entity rendering, alternate namespaces, and overlays using separately baked geometry remain outside this patch. The loaders warn when recognized part textures occur on secondary mob models or block entities. GPU skinning and shared Part constructors are unchanged.

Static verification passed with `git apply --check --whitespace=error` from the exact r8 source. The patch includes targeted Rust tests for parsed texture paths, inherited sprites, missing-sprite fallback and suppression of a spider's eyes overlay over explicitly painted geometry. These checks require a queued Rust run. The trader's two pouch boxes still require a full-stack visual comparison from a view that shows the pouches.
