# Issue 3: Recolourful Containers DARK text shader rejected

Warning: text core shader rejected at `getCorner(sampler2D ...)`.

Root cause: Recolourful's `assets/minecraft/shaders/include/interfaces.glsl` takes `sampler2D Sampler0` as a function parameter in six functions (lines 15, 27, 49, 126, 146, 156), and `rendertype_text.vsh` passes the global `Sampler0` into them. The translator (`crates/horizon-shaders/src/core_shader.rs`, `rewrite`, lines 359 to 371) turns `uniform sampler2D Sampler0;` into a split texture2D plus sampler and `#define Sampler0 sampler2D(hz_tex_Sampler0, hz_smp_Sampler0)`. That define also expands inside the parameter list (`sampler2D sampler2D(...)`), and Naga's Vulkan GLSL front end does not accept sampler2D function parameters anyway. The shader is rejected and the vanilla text shader is used; the only loss is Recolourful's container text colouring.

Why not pack-side: the include is imported before the vertex shader declares `uniform sampler2D Sampler0`, so removing the parameters means reordering the include in every overlay directory (`26.1-26.2`, `26.3`, etc.). That cannot be checked without a build, so no candidate zip was made.

Patch sketch (core_shader.rs, in `rewrite`, before the per-line loop at about line 340):
1. Scan the source for function definitions whose parameter list contains `sampler2D <name>`; record `<name>` and the position.
2. Drop that parameter from the definition, and drop the argument `<name>` from every call of the same function (all call sites in this pack pass the global `Sampler0` literally, lines 52, 162, 200 to 394 of interfaces.glsl).
3. Emit the include body after the global sampler declaration (the existing `declaration_lines` pass already sees both; hoist the `#define` and the two layout lines to the top of the stage when a parameter was removed).
4. Add a unit test next to the existing ones (about line 623) with a minimal `float f(sampler2D S, vec2 t) { return texture(S, t).r; }` shader.
Unverified, not built.
