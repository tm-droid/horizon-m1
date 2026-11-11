#!/usr/bin/env python3
"""Builds Horizon-Recolourful-Containers-Sampler-Fix.zip from the user's Recolourful Containers DARK pack
(read only). naga rejects `sampler2D` function parameters (getCorner etc.); the pack's include gets a
global Sampler0 instead, vertex-stage texture() becomes textureLod(...,0.0). Run: python3 -I build.py"""
import re, sys, zipfile, pathlib
SRC = pathlib.Path.home()/"Library/Application Support/horizon/resourcepacks/Recolourful Containers DARK 3.1.4 (1.19.4+).zip"
OUT = pathlib.Path(__file__).with_name("Horizon-Recolourful-Containers-Sampler-Fix.zip")
z = zipfile.ZipFile(SRC)
inc = z.read("assets/minecraft/shaders/include/interfaces.glsl").decode()
n0 = inc.count("sampler2D Sampler0")
inc = re.sub(r"sampler2D Sampler0,\s*", "", inc)
inc = re.sub(r"\b(getCorner|animation|applyAnimation|position_tex|rendertype_text)\(((?:GameTime, )?)Sampler0,\s*", r"\1(\2", inc)
inc = re.sub(r"texture\(Sampler0, ([^;]*?)\)(\s*\*\s*255\.0|\*255\.0)\)", r"textureLod(Sampler0, \1, 0.0)\2)", inc)
assert "texture(Sampler0" not in inc, "unconverted texture()"
assert not re.search(r"sampler2D Sampler0", inc)
inc = inc.replace("struct Data", "uniform sampler2D Sampler0;\n\nstruct Data", 1)
files = {"assets/minecraft/shaders/include/interfaces.glsl": inc}
for f in ("text.vsh", "position_tex_color.vsh"):
    p = "26.3/assets/minecraft/shaders/core/" + f
    t = z.read(p).decode()
    t = t.replace("uniform sampler2D Sampler0;\n", "")
    t = re.sub(r"(position_tex|rendertype_text)\(ProjMat, GameTime, Sampler0, ", r"\1(ProjMat, GameTime, ", t)
    files["assets/minecraft/shaders/core/" + f] = t
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as o:
    o.writestr("pack.mcmeta", '{"pack":{"pack_format":84,"description":"Recolourful Containers sampler-parameter fix for Horizon (naga)"}}')
    for k, v in files.items(): o.writestr(k, v)
print("wrote", OUT, "replaced decl count", n0)
