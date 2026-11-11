#!/usr/bin/env python3
"""Make the disposable Horizon dynamic-light variant of the pinned MakeUp 9.6 ZIP."""

import argparse
import hashlib
import io
from pathlib import Path
import zipfile

SOURCE_SHA256 = "71319ea5d0ad114143ef1c334890e315dbf1eeb2318d6bc35f3e5021fb3c8ba8"
CANDIDATE = "MakeUp-UltraFast-9.6-Horizon-Dropped-Light.zip"
UNIFORMS = b"""uniform int horizonDynamicLightCount;
uniform mat4 horizonDynamicLights;
"""
LIGHT = b"""#if defined GBUFFER_TERRAIN || defined HORIZON_WATER_DYNAMIC_LIGHT
    float horizonLevel = 0.0;
    for (int i = 0; i < horizonDynamicLightCount; ++i) {
        vec4 light = horizonDynamicLights[i];
        horizonLevel = max(horizonLevel, light.w - distance(gl_Vertex.xyz, light.xyz));
    }
    if (horizonLevel > 0.0) {
        // Match MakeUp's existing block-light coordinate scale.
        float horizonCoord = ((horizonLevel * 16.0 + 8.0) / 256.0) * 1.0323886639676114;
        illumination.x = max(illumination.x, horizonCoord);
    }
#endif
"""
EDITS = {
    "shaders/common/solid_blocks_vertex.glsl": (
        b"uniform float viewWidth;",
        b"#ifdef GBUFFER_TERRAIN\n" + UNIFORMS + b"#endif\n\nuniform float viewWidth;",
    ),
    "shaders/common/water_blocks_vertex.glsl": (
        b"uniform vec3 sunPosition;",
        b"#define HORIZON_WATER_DYNAMIC_LIGHT\n" + UNIFORMS + b"\nuniform vec3 sunPosition;",
    ),
    "shaders/src/light_vertex.glsl": (
        b"vec2 illumination = lmcoord;",
        b"vec2 illumination = lmcoord;\n" + LIGHT.rstrip(b"\n"),
    ),
}


def build(source: Path, output_dir: Path) -> Path:
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError(f"Unexpected MakeUp ZIP bytes: {source}")
    candidate = output_dir / CANDIDATE
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as original, zipfile.ZipFile(output, "w") as generated:
        names = original.namelist()
        if len(names) != len(set(names)) or not EDITS.keys() <= set(names):
            raise ValueError("Unexpected MakeUp ZIP members")
        for name in sorted(names):
            content = original.read(name)
            if name in EDITS:
                before, after = EDITS[name]
                if content.count(before) != 1:
                    raise ValueError(f"Expected one anchor in {name}")
                content = content.replace(before, after)
            item = zipfile.ZipInfo(name)
            item.compress_type = zipfile.ZIP_DEFLATED
            generated.writestr(item, content)
    with zipfile.ZipFile(output) as check:
        if check.testzip() is not None:
            raise ValueError("Generated ZIP failed CRC verification")
    with candidate.open("xb") as stream:
        stream.write(output.getbuffer())
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output_dir", type=Path, help="Existing disposable directory")
    args = parser.parse_args()
    print(build(args.source, args.output_dir))


if __name__ == "__main__":
    main()
