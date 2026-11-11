#!/usr/bin/env python3
"""Build original one-pass cloud sharing prototype from immutable MakeUp input."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = ROOT / 'instances/Tanush-26.3/minecraft/shaderpacks/MakeUp-UltraFast-9.6.zip'
OPTIONS = ROOT / 'outputs/horizon-runtime/u9c-trim-options/MakeUp-UltraFast-9.6.zip.txt'
OUT = ROOT / 'outputs/horizon-runtime/game/shaderpacks/MakeUp-M1-Quad.zip'


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old,new)


def build():
    raise SystemExit('BLOCKED: subgroupBallot(true) does not prove non-helper shuffle sources; frontend lacks gl_HelperInvocation. Draft must not be packaged or run.')
    # Unreachable design draft retained for an explicit helper-safe engine follow-up.
    before = SOURCE.read_bytes()
    with ZipFile(SOURCE) as z:
        files = {n:z.read(n) for n in z.namelist() if not n.endswith('/')}
    cloud = files['shaders/lib/volumetric_clouds.glsl'].decode()
    cloud = replace_once(cloud,'vec3 get_cloud(', 'vec3 m1CloudForCoefficients(')
    boost = '        blockColor.rgb *= clamp(bright + ((dither - .5) * .1), 0.0, 1.0) * .3 + 1.0;'
    cloud = replace_once(cloud,boost,boost+'\n        m1QuadTransmittance *= clamp(bright + ((dither - .5) * .1), 0.0, 1.0) * .3 + 1.0;')
    blend = '        blockColor = mix(blockColor, cloudColor, cloud_value * clamp((eyeDirection.y - 0.06) * 5.0, 0.0, 1.0));'
    cloud = replace_once(cloud,blend,blend+'\n        m1QuadTransmittance *= 1.0 - cloud_value * clamp((eyeDirection.y - 0.06) * 5.0, 0.0, 1.0);')
    cloud = 'float m1QuadTransmittance;\n'+cloud
    deferred = files['shaders/common/deferred_fragment.glsl'].decode()
    original_include = '#include "/lib/volumetric_clouds.glsl"'
    deferred = replace_once(deferred,original_include,original_include+'\n        #include "/lib/m1_quad_cloud.glsl"')
    deferred = replace_once(deferred,'blockColor.rgb = get_cloud(', 'blockColor.rgb = m1QuadCloud(')
    clamp = '    blockColor = clamp(blockColor, vec4(0.0), vec4(vec3(50.0), 1.0));'
    deferred = replace_once(deferred,clamp,'    #if M1_QUAD_DIAGNOSTIC == 1\n        blockColor.rgb = mix(blockColor.rgb, m1QuadShared ? vec3(0.0,1.0,0.0) : vec3(1.0,0.0,0.0), 0.6);\n    #endif\n'+clamp)
    wrapper = files['shaders/world0/deferred.fsh'].decode()
    extension = '#extension GL_ARB_shader_texture_lod : enable'
    wrapper = replace_once(wrapper,extension,extension+'\n#if defined MC_GL_KHR_shader_subgroup_basic && defined MC_GL_KHR_shader_subgroup_ballot && defined MC_GL_KHR_shader_subgroup_shuffle\n#extension GL_KHR_shader_subgroup_basic : enable\n#extension GL_KHR_shader_subgroup_ballot : enable\n#extension GL_KHR_shader_subgroup_shuffle : enable\n#endif')
    wrapper = replace_once(wrapper,'/common/deferred_fragment.glsl','/common/m1_quad_deferred.glsl')
    changed = {
        'shaders/world0/deferred.fsh':wrapper.encode(),
        'shaders/common/m1_quad_deferred.glsl':deferred.encode(),
        'shaders/lib/m1_quad_cloud_coeff.glsl':cloud.encode(),
        'shaders/lib/m1_quad_cloud.glsl':(HERE/'quad_cloud.glsl').read_bytes(),
        'M1-QUAD-PROTOTYPE.md':(HERE/'README.md').read_bytes(),
    }
    files.update(changed)
    with ZipFile(OUT,'w',compression=ZIP_DEFLATED,compresslevel=9) as z:
        for name,data in sorted(files.items()):
            entry=ZipInfo(name,date_time=(2026,11,7,0,0,0))
            entry.compress_type=ZIP_DEFLATED
            entry.external_attr=0o644<<16
            z.writestr(entry,data)
    options = OPTIONS.read_text()
    OUT.with_suffix('.zip.txt').write_text(options+'M1_QUAD_DIAGNOSTIC=0\n')
    (HERE/'diagnostic-options.txt').write_text(options+'M1_QUAD_DIAGNOSTIC=1\n')
    assert SOURCE.read_bytes()==before
    result=dict(source_sha256=hashlib.sha256(before).hexdigest(),
                output_sha256=hashlib.sha256(OUT.read_bytes()).hexdigest(),
                changed_entries=sorted(changed), diagnostic='M1_QUAD_DIAGNOSTIC=1: green shared, red fallback')
    (HERE/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    build()
