#!/usr/bin/env python3
"""One queued MakeUp fresh-terrain/revisit diagnostic, never a speedup claim."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
VERSION = 'native-f42-m1-r3-6b039bd4b49f'
EXPECTED_OPTIONS = {'renderDistance': 12, 'simulationDistance': 8, 'fov': 95, 'cloudRange': 64,
                    'maxFps': 260, 'enableVsync': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default='fresh1107')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9-]{1,16}', args.tag):
        parser.error('Use1–16lowercase letters/digits/hyphens')
    spec = importlib.util.spec_from_file_location('fresh_probe_gates', RUNTIME / 'run-codex-continuation.py')
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    u9 = gates.U9
    migration = u9.MIGRATIONS['v4']
    manifest = migration / 'manifest.json'
    selection = json.loads(manifest.read_text())['resourcepack_selection']
    options = u9.TRIM_FILE
    binary = u9.VERSIONS / VERSION / 'horizon-client'
    label = 'fp-' + args.tag
    profile = RUNTIME / 'tests' / label
    summary_path = RUNTIME / ('fresh-flight-' + args.tag + '.json')
    if profile.exists() or summary_path.exists():
        parser.error('Fresh profile/summary required')
    hashes = {'binary': u9.R3.digest(binary), 'options': u9.R3.digest(options), 'manifest': u9.R3.digest(manifest)}
    command = [sys.executable, str(ROOT / 'tools/horizon-offline-test.py'), '--runtime', u9.REVIEW.RELEASE,
               '--native-version', VERSION, '--case', 'makeup', '--label', label,
               '--migration', str(migration), '--native-options-candidate', str(migration / 'native-settings-candidate.json'),
               '--shader-options-file', str(options), '--scene', 'cow', '--width', '1280', '--height', '720',
               '--fps-cap', '260', '--resolution-scale', '100', '--workers', '0', '--frame-pacing', 'efficient',
               '--warmup', '15', '--seconds', '20', '--fresh-flight']
    if args.dry_run:
        print(json.dumps({'command': command, 'hashes': hashes, 'diagnostic_only': True}, indent=2))
        return
    if os.environ.get('HORIZON_TEST_QUEUE') != '1':
        parser.error('Run inside the device queue')
    ok, problems = u9.wait_gates(print, probe=gates.gate_problems)
    if not ok:
        raise SystemExit('Gates failed: ' + str(problems))
    summary = {'valid': False, 'diagnostic_only': True, 'command': command, 'hashes': hashes,
               'profile': str(profile), 'result': str(profile / 'result.json')}
    env = dict(os.environ, HORIZON_TEST_QUEUE='1', HORIZON_SPIKES='25', HORIZON_SHADER_PACK_TIMING='1')
    sampler = u9.R3.Sampler()
    awake = subprocess.Popen(['caffeinate', '-d', '-t', '3600'])
    try:
        sampler.start()
        summary['exit_code'] = subprocess.run(command, cwd=ROOT, env=env).returncode
        result = json.loads((profile / 'result.json').read_text())
        check = u9.REVIEW.check
        check(summary['exit_code'] == 0 and result.get('complete') and result.get('exit_code') == 0,
              'Probe/client did not complete cleanly')
        check(result['native_executable_sha256'] == hashes['binary'] == u9.R3.digest(binary), 'Binary changed')
        check(result['runtime_revision'] == u9.REVIEW.REVISION and result['fps_cap'] == 260 and
              result['world_resolution_scale_percent'] == 100 and result['render_mode'] == 'onscreen', 'Runtime/settings changed')
        check(result['migration_manifest_sha256'] == hashes['manifest'] == u9.R3.digest(manifest) and
              result['pack_selection'] == selection and result['active_resourcepacks']['options']['resourcePacks']['value'] == selection,
              'Pack selection/manifest changed')
        live_options = result['effective_visual_options']['options']
        check(all(live_options[key]['value'] == value for key, value in EXPECTED_OPTIONS.items()),
              'Effective visual options changed')
        text = (profile / 'console.log').read_text(errors='replace')
        check(not u9.R3.TAINT.search(text), 'User input tainted diagnostic')
        check(not re.search(r'panicked at|Validation Error|shader pack .*refused|Error in Device::', text), 'Render/runtime error')
        check(re.search(r'shader pack MakeUp-UltraFast-9\.6\.zip: folder `[^`]*`, [1-9][0-9]* programs \(', text),
              'No active MakeUp post programs')
        probe = result['fresh_flight']
        check(probe.get('complete') and probe['prelaunch']['stored_corridor_absent_before_launch'], 'Fresh corridor not verified')
        check(probe['shader_options_sha256'] == hashes['options'] == u9.R3.digest(options), 'Trim changed')
        phases = probe['phases']
        check([p['name'] for p in phases] in (['first-pass', 'revisit'], ['first-pass']), 'Unknown probe phases')
        if len(phases) == 1:
            check(phases[0].get('hopeless') and probe.get('stopped'), 'Missing revisit without terminal result')
        for phase in phases:
            m = phase['measurement']
            check(m.get('frames', 0) > 0 and 31 <= m.get('seconds', 0) <= 33 and
                  all(m.get(key) for key in ['frame_ms', 'cpu_ms', 'gpu_ms']), 'Incomplete raw flight data')
            check(phase['pack_selection'] == selection and phase['status_timeline'], 'Missing pack/status evidence')
            for state in [phase['before'], phase['after'], *[s['status'] for s in phase['status_timeline']]]:
                renderer = state['renderer']
                check(state['dimension'] == 'minecraft:overworld' and state['render_distance'] == 12 and
                      renderer['backend'] == 'Metal' and renderer['gpu'] == 'Apple M1' and renderer['size'] == [2560, 1440] and
                      renderer['present_mode'] == 'Immediate' and state['input']['counts']['user'] == phase['before']['input']['counts']['user'],
                      'Renderer/world/user-input changed during flight')
            check(phase['window_before'].get('horizon_is_front') and phase['window_after'].get('horizon_is_front'),
                  'Probe was not foreground')
        summary.update(valid=True, phases=[{'name': p['name'], 'measurement': p['measurement'], 'wall_seconds': p['wall_seconds'],
                       'status_samples': len(p['status_timeline'])} for p in phases],
                       counter_limit=probe['counter_limit'])
    except Exception as error:
        summary['error'] = str(error)
    finally:
        sampler.stop.set()
        sampler.join(timeout=40)
        summary['memory'] = sampler.summary()
        awake.terminate()
        summary_path.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: summary.get(k) for k in ['valid', 'error', 'exit_code']}), flush=True)
    return 0 if summary['valid'] else 1


if __name__ == '__main__':
    sys.exit(main())
