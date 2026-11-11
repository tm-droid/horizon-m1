#!/usr/bin/env python3
"""Run one disposable daily-stack compatibility arm inside the shared device queue."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
AUDIT = ROOT / 'outputs/horizon-compatibility/daily-20261107'
R8 = 'native-f42-m1-r8-903e75d76f09'
R11 = 'native-f42-m1-r11-ef12b7f4368d'
R12 = 'native-f42-m1-r12-2d42b3732401'
VERSIONS = {'baseline': 'native-f42-m1-r3-6b039bd4b49f', 'fixed': R8, 'mobs-base': R8, 'mobs-fix': R8,
            'gui-base': R8, 'gui-fix': R8, 'render-profile': R8, 'family-base': R8, 'family-fix': R8,
            'world': R8, 'world-fix': R8, 'world-control': R8, 'charge-base': R8,
            'charge-fix': 'native-f42-m1-r9-e0877984e252', 'light-native': R8, 'light-makeup': R8, 'sound': R8,
            'parts-base': R8, 'parts-fix': 'native-f42-m1-r10-e8c108dbd1dc',
            'charge-native-base': R8, 'charge-native-fix': 'native-f42-m1-r9-e0877984e252',
            'bogged-base': R8, 'bogged-fix': R8, 'charge-stock': R8,
            'parts-variants': R11, 'ghast-body-base': R11, 'ghast-body-fix': R11,
            'ghast-body-align': R11, 'render-current': R11, 'render-ao': R11,
            'build-surfaces': R11, 'build-control': R11, 'build-beds-base': R11, 'build-beds-fix': R11,
            'light-bridge-base': R11, 'light-bridge-fix': R12, 'light-bridge-off': R12}
BUILD_PACKS = {"Fancy Crops v1.3.zip", "VanillaTweaks 3D Fungi.zip", "§3Fresh §bFlower Pots.zip",
               "§3Fresh §bFlower Pots 3D.zip", "§aRemodeled-Doors§8_§62.3.1.zip",
               "§l3D§f Ladders v1.2.2 - 26.3.zip", "Weskerson's Torches.zip", "§lBetter Beds.zip",
               "Better Lanterns v1.4.0 - 26.2+26.3.zip"}
GHAST_ALIGNMENT = 'Horizon-Ghast-Alignment-Compatibility.zip'
BED_GEOMETRY = 'Horizon-Better-Beds-Compatibility.zip'


def timing_summary(result, console):
    measurement = result['measurement']
    renderer = result['before']['renderer']
    if (renderer['backend'] != 'Metal' or renderer['gpu'] != 'Apple M1' or
            measurement['frames'] <= 0 or measurement['seconds'] < 19 or
            measurement['cpu']['avg_ms'] <= 0 or measurement['gpu']['avg_ms'] <= 0 or
            not result['window_before_bench']['horizon_is_front'] or
            not result['window_after_bench']['horizon_is_front'] or
            'shader pack GPU time per pass' not in console):
        raise RuntimeError('Incomplete foreground Metal timing sample')
    return {'size': renderer['size'], 'fps': measurement['avg_fps'], 'frames': measurement['frames'],
            'cpu_ms': measurement['cpu']['avg_ms'], 'gpu_ms': measurement['gpu']['avg_ms']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('arm', choices=VERSIONS)
    parser.add_argument('tag')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{1,20}', args.tag):
        parser.error('tag must be 1–20 lowercase letters, digits, or hyphens')
    label = f'daily-compat-{args.arm}-{args.tag}'
    profile = RUNTIME / 'tests' / label
    if profile.exists():
        parser.error('choose a fresh test tag')
    spec = importlib.util.spec_from_file_location('daily_gates', RUNTIME / 'run-codex-continuation.py')
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    u9 = gates.U9
    digest = u9.R3.digest
    migration = AUDIT / 'snapshot'
    manifest_path = migration / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    selection = manifest['resourcepack_selection']
    sources = {migration / 'resourcepacks' / name: sha for name, sha in manifest['snapshot_sha256'].items()}
    options = RUNTIME / 'game/shaderpacks/MakeUp-UltraFast-9.6.zip.txt'
    binary = u9.VERSIONS / VERSIONS[args.arm] / 'horizon-client'
    mobs = args.arm.startswith('mobs-')
    gui = args.arm.startswith('gui-')
    family = args.arm.startswith('family-')
    world = args.arm.startswith('world')
    charge = args.arm.startswith('charge-')
    light = args.arm.startswith('light-')
    light_bridge = args.arm.startswith('light-bridge-')
    sound = args.arm == 'sound'
    parts = args.arm.startswith('parts-')
    ghast = args.arm.startswith('ghast-body-')
    bogged = args.arm.startswith('bogged-') or ghast
    build = args.arm.startswith('build-')
    beds = args.arm.startswith('build-beds-')
    current_timing = args.arm in ('render-current', 'render-ao')
    current_stack = current_timing or build or light_bridge
    full_overlays = args.arm == 'parts-variants' or current_stack or ghast
    shader = args.arm != 'light-native' and not args.arm.startswith('charge-native-')
    timing = args.arm == 'render-profile' or current_timing
    scene = ('cow' if timing else 'daily-compat-build' if build else 'daily-compat-world' if world else 'daily-compat-charge' if charge else
             'daily-compat-light' if light else 'daily-compat-sound' if sound else
             'daily-compat-parts' if parts else 'daily-compat-ghast' if ghast else 'daily-compat-bogged' if bogged else
             'daily-compat-gui' if gui else 'daily-compat-family' if family else
             'daily-compat-mobs' if mobs else 'daily-compat')
    command = [sys.executable, str(ROOT / 'tools/horizon-offline-test.py'), '--runtime', u9.REVIEW.RELEASE,
               '--native-version', VERSIONS[args.arm], '--case', 'makeup' if shader else 'packs', '--label', label,
               '--migration', str(migration),
               '--scene', scene, '--width', '1440', '--height', '900']
    if shader:
        command.extend(['--shader-options-file', str(options)])
    makeup_source = None
    if current_timing or light_bridge:
        makeup_source = RUNTIME / 'game/shaderpacks/MakeUp-UltraFast-9.6.zip'
        if args.arm == 'render-ao':
            makeup_source = ROOT / 'outputs/horizon-native/makeup-deferred-m1-screen-20261108/MakeUp-UltraFast-9.6-AO-Screen.zip'
            if (digest(makeup_source) != '2cb1fd83d65e41610922b35401c30de3fcac85de1efe266f5b3b64fc571ed662' or
                    digest(options) != 'c2f2629116d6d6f5efe6f59c7f003064061ad495fcfcb004fd181447a9cba975'):
                raise RuntimeError('Unexpected AO shader candidate or options')
        if args.arm in ('light-bridge-fix', 'light-bridge-off'):
            makeup_source = ROOT / 'outputs/horizon-native/makeup-dropped-light-r11/MakeUp-UltraFast-9.6-Horizon-Dropped-Light.zip'
            if digest(makeup_source) != '172412da8acae03f65c78f6ca90864f6a872425762832350dd4e7e10c294e910':
                raise RuntimeError('Unexpected dropped-light shader candidate')
        sources[makeup_source] = digest(makeup_source)
        command.extend(['--makeup-source', str(makeup_source)])
    if args.arm in ('world-control', 'build-control'):
        excluded = (BUILD_PACKS if build else
                    {'Connected-Bricks 26.2-26.3 v3.1.1.zip', 'Connected-Rocks 26.2-26.3 v3.1.1.zip'})
        if not all('file/' + name in selection for name in excluded):
            raise RuntimeError('Excluded packs differ from the test fixture')
        selection = [entry for entry in selection if entry.removeprefix('file/') not in excluded]
        for entry in selection:
            if entry != 'vanilla':
                command.extend(['--pack-name', entry.removeprefix('file/')])
    if timing:
        command.extend(['--fps-cap', '260', '--warmup', '15', '--seconds', '20', '--frame-pacing', 'efficient'])
    else:
        command.extend(['--compatibility-only', '--fps-cap', '60', '--warmup', '0', '--seconds', '5'])
    if scene == 'daily-compat':
        command.append('--zoom-smoke')
    if args.arm == 'parts-variants':
        command.append('--part-variants')
    if beds:
        command.append('--beds-only')
    if light_bridge:
        command.append('--dynamic-light-extended')
    if args.arm == 'light-bridge-off':
        command.append('--disable-extras-dynamic-lights')
    overlays = []
    if args.arm != 'baseline':
        overlays.append('Horizon-Daily-Compatibility.zip')
    if args.arm == 'mobs-fix' or gui or family or world or charge or light or sound or parts or bogged or timing or full_overlays:
        overlays.append('Horizon-Animation-Compatibility.zip')
    if args.arm == 'gui-fix' or family or world or charge or light or sound or parts or bogged or timing or full_overlays:
        overlays.append('Horizon-GUI-Compatibility.zip')
    if args.arm in ('family-fix', 'world-fix', 'world-control') or charge or light or sound or parts or bogged or full_overlays:
        overlays.append('Horizon-Mob-Compatibility.zip')
    if args.arm in ('world-fix', 'world-control') or parts or bogged or full_overlays:
        overlays.append('Horizon-Trim-Compatibility.zip')
    if args.arm in ('charge-fix', 'charge-native-fix'):
        overlays.append('Horizon-Charged-Creeper.zip')
    if args.arm == 'charge-stock':
        overlays.extend(['Horizon-Trim-Compatibility.zip', 'Horizon-Charge-Texture-Control.zip'])
    if args.arm == 'bogged-fix' or full_overlays:
        overlays.append('Horizon-Bogged-Compatibility.zip')
        overlays.append('Horizon-Skeleton-Horse-Compatibility.zip')
        overlays.append('Horizon-Ghast-Harness-Compatibility.zip')
    if args.arm == 'ghast-body-fix':
        overlays.append('Horizon-Ghast-Body-Compatibility.zip')
    if args.arm == 'ghast-body-align':
        overlays.append(GHAST_ALIGNMENT)
    if current_stack:
        daily_line = next(line for line in (RUNTIME / 'game/options.txt').read_text().splitlines()
                          if line.startswith('resourcePacks:'))
        daily = json.loads(daily_line.removeprefix('resourcePacks:'))
        if 'file/' + GHAST_ALIGNMENT in daily:
            overlays.append(GHAST_ALIGNMENT)
        if 'file/' + BED_GEOMETRY in daily and args.arm != 'build-control':
            overlays.append(BED_GEOMETRY)
        if args.arm == 'build-beds-fix':
            if 'file/' + BED_GEOMETRY in daily:
                raise RuntimeError('Bed candidate already selected; cannot construct this control pair')
            overlays.append(BED_GEOMETRY)
            daily = daily + ['file/' + BED_GEOMETRY]
    for name in overlays:
        overlay = AUDIT / name
        command.extend(['--extra-pack', str(overlay)])
        sources[overlay] = digest(overlay)
        selection.append('file/' + overlay.name)
    if current_stack:
        if args.arm == 'build-control':
            daily = [entry for entry in daily if entry.removeprefix('file/') not in (BUILD_PACKS | {BED_GEOMETRY})]
        if selection != daily:
            raise RuntimeError('Test pack order does not match the daily stack with the intended exclusions')
    if args.dry_run:
        print(json.dumps(command, indent=2))
        return 0
    if os.environ.get('HORIZON_TEST_QUEUE') != '1':
        parser.error('run inside the shared device queue')
    sources.update({path: digest(path) for path in (binary, options, manifest_path)})
    ok, problems = u9.wait_gates(lambda message: print(message, flush=True), max_wait=180, probe=gates.gate_problems)
    if not ok:
        raise RuntimeError(f'device gates failed: {problems}')
    if any(digest(path) != sha for path, sha in sources.items()):
        raise RuntimeError('compatibility inputs changed')
    awake = subprocess.Popen(['caffeinate', '-di', '-t', '1200'])
    try:
        env = dict(os.environ, HORIZON_SHADER_PACK_TIMING='1') if timing else None
        process = subprocess.run(command, cwd=ROOT, env=env)
    finally:
        awake.terminate()
        awake.wait()
    result = json.loads((profile / 'result.json').read_text())
    if result.get('exit_code') == 0:
        shutil.rmtree(profile / '.horizon-cache', ignore_errors=True)
    console = (profile / 'console.log').read_text(errors='replace')
    makeup_loaded = bool(re.search(r'shader pack MakeUp-UltraFast-9\.6\.zip: folder `[^`]*`, [1-9][0-9]* programs \(', console))
    if (process.returncode or not result.get('complete') or result.get('exit_code') != 0 or
            result.get('native_executable_sha256') != sources[binary] or
            result.get('migration_manifest_sha256') != sources[manifest_path] or
            result.get('pack_selection') != selection or
            u9.R3.TAINT.search(console) or makeup_loaded != shader):
        raise RuntimeError(f'compatibility run setup or execution failed, see {profile}')
    if makeup_source is not None and result['shader_archive_sha256'] != sources[makeup_source]:
        raise RuntimeError('Staged shader bytes differ from the requested archive')
    if timing:
        if args.arm == 'render-ao' and not re.search(r'timed frames\): world .*deferred [1-9][0-9]*\.\d+', console):
            raise RuntimeError('No active deferred timing in the AO candidate')
        print(json.dumps({'result': str(profile / 'result.json'), **timing_summary(result, console)}), flush=True)
        return 0
    cases = result['gui_compat' if gui else 'world_compat' if world or sound or build else 'daily_compat']
    print(json.dumps({name: {k: data[k] for k in ('complete', 'error') if k in data}
                      for name, data in cases.items()}), flush=True)
    return 0 if cases and all(case['complete'] for case in cases.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
