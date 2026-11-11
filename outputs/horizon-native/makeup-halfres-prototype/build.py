#!/usr/bin/env python3
"""Rebuild the isolated LGPL MakeUp M1 prototype; no engine or instance writes."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'instances/Tanush-26.3/minecraft/shaderpacks/MakeUp-UltraFast-9.6.zip'
OPTIONS = ROOT / 'outputs/horizon-runtime/u9c-trim-options/MakeUp-UltraFast-9.6.zip.txt'
OUT = ROOT / 'outputs/horizon-runtime/game/shaderpacks/MakeUp-M1-HalfRes.zip'


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def build(output=OUT, overrides=None, manifest_path=HERE / 'manifest.json'):
    original = SOURCE.read_bytes()
    with ZipFile(SOURCE) as z:
        files = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    changed = {}
    # Keep the original shader as the full-resolution fallback. Only expose its result.
    evaluate = files['shaders/common/deferred_fragment.glsl'].decode()
    evaluate = replace_once(evaluate, 'void main() {', 'vec4 m1Evaluate() {\n    m1Multiplier = 1.0;')
    evaluate = replace_once(evaluate, '#include "/lib/volumetric_clouds.glsl"', '#include "/lib/m1_volumetric_clouds.glsl"')
    evaluate = replace_once(evaluate, '        blockColor.rgb *= final_ao;',
                            '        blockColor.rgb *= final_ao;\n        m1Multiplier *= final_ao;')
    start = evaluate.index('    blockColor = clamp(blockColor, vec4(0.0), vec4(vec3(50.0), 1.0));')
    evaluate = 'float m1Multiplier;\n' + evaluate[:start] + '    return blockColor;\n}\n'
    changed['shaders/common/m1_evaluate.glsl'] = evaluate.encode()
    cloud = files['shaders/lib/volumetric_clouds.glsl'].decode()
    cloud = replace_once(cloud,
        '        blockColor.rgb *= clamp(bright + ((dither - .5) * .1), 0.0, 1.0) * .3 + 1.0;',
        '        float m1Boost = clamp(bright + ((dither - .5) * .1), 0.0, 1.0) * .3 + 1.0;\n'
        '        blockColor.rgb *= m1Boost;\n        m1Multiplier *= m1Boost;')
    line = '        blockColor = mix(blockColor, cloudColor, cloud_value * clamp((eyeDirection.y - 0.06) * 5.0, 0.0, 1.0));'
    cloud = replace_once(cloud, line,
        '        float m1Opacity = cloud_value * clamp((eyeDirection.y - 0.06) * 5.0, 0.0, 1.0);\n'
        '        blockColor = mix(blockColor, cloudColor, m1Opacity);\n'
        '        m1Multiplier *= 1.0 - m1Opacity;')
    changed['shaders/lib/m1_volumetric_clouds.glsl'] = cloud.encode()
    for name in ['m1_half_fragment.glsl', 'm1_upsample_fragment.glsl']:
        changed['shaders/common/' + name] = (HERE / name).read_bytes()
    header = files['shaders/world0/deferred.fsh'].decode().split('#include')[0]
    changed['shaders/world0/deferred.fsh'] = (header + '#include "/common/m1_half_fragment.glsl"\n').encode()
    changed['shaders/world0/deferred1.fsh'] = (header + '#include "/common/m1_upsample_fragment.glsl"\n').encode()
    changed['shaders/world0/deferred1.vsh'] = files['shaders/world0/deferred.vsh']
    changed['shaders/shaders.properties'] = files['shaders/shaders.properties'] + (
        '\n# Original M1 prototype: real, isolated half-size attachments.\n'
        'size.buffer.colortex8=0.5 0.5\nsize.buffer.colortex9=0.5 0.5\n').encode()
    changed['M1-PROTOTYPE.md'] = (HERE / 'README.md').read_bytes()
    changed.update(overrides or {})
    files.update(changed)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in sorted(files.items()):
            entry = ZipInfo(name, date_time=(2026, 11, 6, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            z.writestr(entry, data)
    output.with_suffix('.zip.txt').write_bytes(OPTIONS.read_bytes())
    assert SOURCE.read_bytes() == original
    result = dict(source_sha256=hashlib.sha256(original).hexdigest(),
                  output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                  output=str(output.relative_to(ROOT)), changed_entries=sorted(changed))
    manifest_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    build()
