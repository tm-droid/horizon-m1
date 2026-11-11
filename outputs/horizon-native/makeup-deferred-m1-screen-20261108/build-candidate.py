#!/usr/bin/env python3
"""Build a private candidate from the exact active MakeUp 9.6 archive."""

from copy import copy
from hashlib import sha256
from pathlib import Path
from shutil import copyfile
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
SHADER_DIR = HERE.parents[1] / "horizon-runtime/game/shaderpacks"
NAME = "MakeUp-UltraFast-9.6.zip"
SOURCE = SHADER_DIR / NAME
OPTIONS = SHADER_DIR / (NAME + ".txt")
OUTPUT = HERE / "MakeUp-UltraFast-9.6-AO-Screen.zip"
PINNED = {
    SOURCE: "71319ea5d0ad114143ef1c334890e315dbf1eeb2318d6bc35f3e5021fb3c8ba8",
    OPTIONS: "c2f2629116d6d6f5efe6f59c7f003064061ad495fcfcb004fd181447a9cba975",
}
DEFERRED = "shaders/common/deferred_fragment.glsl"
AO = "shaders/lib/ao.glsl"


def edit(data, before, after):
    if data.count(before) != 1:
        raise ValueError("Expected exactly one edit site in the pinned shader")
    return data.replace(before, after)


def main():
    for path, expected in PINNED.items():
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Active source changed: {path}")

    with ZipFile(SOURCE) as original:
        ao = edit(original.read(AO), b"float dbao(float dither) {",
                  b"float dbao(float dither, float depth, float linearDepth) {")
        ao = edit(ao, b"""    float linearDepth = texture2DLod(depthtex0, texcoord.xy, 0.0).r;
    float handCheck = linearDepth < 0.56 ? 1024.0 : 1.0;
    linearDepth = ld(linearDepth);
""", b"""    float handCheck = depth < 0.56 ? 1024.0 : 1.0;
""")
        deferred = edit(original.read(DEFERRED), b"""        // AO distance attenuation
""", b"""        // Keep the center depth before dimension-specific fog adjustment.
        float ao_center_depth = linearDepth;
        // AO distance attenuation
""")
        deferred = edit(deferred, b"""        float final_ao = mix(dbao(dither), 1.0, ao_att);
        blockColor.rgb *= final_ao;
""", b"""        // Fully attenuated AO is neutral, so no depth taps are needed.
        if (ao_att != 1.0) {
            float final_ao = mix(dbao(dither, depth, ao_center_depth), 1.0, ao_att);
            blockColor.rgb *= final_ao;
        }
""")
        changes = {AO: ao, DEFERRED: deferred}

        with ZipFile(OUTPUT, "w") as candidate:
            for member in original.infolist():
                data = changes.get(member.filename)
                candidate.writestr(copy(member), original.read(member) if data is None else data)

        with ZipFile(OUTPUT) as candidate:
            if candidate.testzip() or candidate.namelist() != original.namelist():
                raise ValueError("Candidate archive inventory or CRC changed")
            actual = {name for name in original.namelist()
                      if original.read(name) != candidate.read(name)}
            if actual != set(changes):
                raise ValueError(f"Unexpected changed shader members: {actual}")

    sidecar = OUTPUT.with_name(OUTPUT.name + ".txt")
    copyfile(OPTIONS, sidecar)
    print(f"{sha256(OUTPUT.read_bytes()).hexdigest()}  {OUTPUT}")
    print(f"{sha256(sidecar.read_bytes()).hexdigest()}  {sidecar}")


if __name__ == "__main__":
    main()
