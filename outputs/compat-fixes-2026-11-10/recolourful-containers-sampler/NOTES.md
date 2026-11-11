# Recolourful Containers getCorner (bug 3)
Cause: pack include `shaders/include/interfaces.glsl` has functions taking `sampler2D Sampler0` (getCorner l.15/27, position_tex, animation, applyAnimation, rendertype_text). naga GLSL frontend rejects sampler2D params; horizon-shaders translate/image_parameters.rs only specialises `image` params (called at translate/mod.rs:1041). Error surfaces at hud/pack_text.rs:213.
Fix (pack side): `build.py` makes Horizon-Recolourful-Containers-Sampler-Fix.zip: global `uniform sampler2D Sampler0;` in the include, params/args dropped, vertex `texture()` -> `textureLod(..,0.0)`, text.vsh/position_tex_color.vsh lose their own uniform + arg. Place ABOVE Recolourful Containers.
UNVERIFIED against naga (no cargo). Other naga errors may follow (e.g. const int[] arrays, break in loops).
Client alternative (off-limits file translate/mod.rs): add sampler-param specialisation like image_parameters.rs for core shaders.
