#!/usr/bin/env python3
"""Build the original center-depth demand patch on the exact daily r3 source.

Queue-only. --dry-run verifies/stages source without Cargo or installation.
Never changes daily selection. Inherits r3's CEM/Zoom source and metadata.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
DATA = RUNTIME / 'launcher-data'
BASE_VERSION = 'native-f42-m1-r3-6b039bd4b49f'
BASE = DATA / 'versions' / BASE_VERSION
SOURCE = RUNTIME / 'm1-performance-r3/candidate-source'
PATCH = ROOT / 'outputs/horizon-native/center-depth-demand-f42/center-depth-demand.patch'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if os.environ.get('HORIZON_TEST_QUEUE') != '1':
        parser.error('Run inside the shared device queue')
    build = load('r6_build_helpers', RUNTIME / 'build-nightly-6475f62.py')
    original = json.loads((BASE / 'source-patches.json').read_text())
    expected = original['candidate_files']
    if build.inventory(SOURCE) != expected:
        raise SystemExit('Daily r3 source differs from its installed build inventory')
    if not PATCH.is_file():
        raise SystemExit('Missing center-depth patch')
    if not args.dry_run:
        gates = load('r6_gates', RUNTIME / 'run-codex-continuation.py')
        problems = gates.gate_problems(check_idle=False)
        if problems:
            raise SystemExit('Build gates failed: ' + '; '.join(problems))
        build.preflight(5)
    lab = RUNTIME / 'm1-performance-r6' / time.strftime('%Y%m%d-%H%M%S')
    lab.mkdir(parents=True, exist_ok=False)
    work = lab / 'source'
    run(['/bin/cp', '-cR', str(SOURCE), str(work)])
    run(['git', 'apply', '--check', str(PATCH)], cwd=work)
    run(['git', 'apply', '--whitespace=nowarn', str(PATCH)], cwd=work)
    # Shared target artifacts may come from a different revision despite older
    # imported source mtimes. Force all local inputs fresh, not just this patch.
    for path in work.rglob('*'):
        if path.is_file() and not path.is_symlink():
            path.touch()
    files = build.inventory(work)
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    version = 'native-f42-m1-r6-' + identity[:12]
    destination = DATA / 'versions' / version
    if destination.exists():
        raise SystemExit('Already installed: ' + version)
    build.LAB = lab
    build.STATUS = lab / 'build-status.json'
    command = [str(build.TOOLCHAIN / 'bin/cargo'), 'build', '--offline', '--locked', '--profile', 'fast',
               '--manifest-path', str(work / 'Cargo.toml'), '-p', 'horizon-client', '--bin', 'horizon-client']
    record = {'complete': False, 'runtime_verified': False, 'base_version': BASE_VERSION,
              'source_revision': original['source_revision'], 'candidate_version': version,
              'source_digest': identity, 'source': str(work), 'candidate_files': files,
              'patch_sha256': build.digest(PATCH), 'command': command, 'samples': [],
              'profile': 'fast', 'rust': '1.99.1'}
    build.save(record)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'version': version, 'source': str(work)}))
        return
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, build.cancellation)
    env = build.cargo_env()
    env['DYLD_FALLBACK_LIBRARY_PATH'] = str(build.TOOLCHAIN / 'lib')
    tests = [str(build.TOOLCHAIN / 'bin/cargo'), 'test', '--offline', '--locked', '--profile', 'fast',
             '--manifest-path', str(work / 'Cargo.toml'), '-p', 'horizon-shaders', '--lib', 'center_depth_']
    record['test_command'] = tests
    build.compile_client(tests, env, record, 'center-depth-tests')
    result = re.search(r'test result: ok\. (\d+) passed; 0 failed;',
                       (lab / 'cargo-center-depth-tests.log').read_text())
    if not result or int(result[1]) == 0:
        raise SystemExit('Focused tests did not run; refusing client build')
    record['focused_tests_passed'] = int(result[1])
    build.compile_client(command, env, record, 'r6')
    if build.inventory(work) != files or build.inventory(SOURCE) != expected:
        raise SystemExit('Source changed during build; refusing installation')
    staging = destination.with_name(destination.name + '.new')
    if destination.exists() or staging.exists():
        raise SystemExit('Installation destination already exists')
    run(['/bin/cp', '-cR', str(BASE), str(staging)])
    import shutil
    shutil.copy2(build.CARGO_TARGET / 'fast/horizon-client', staging / 'horizon-client')
    record.update(complete=True, binary_sha256=build.digest(staging / 'horizon-client'))
    metadata = json.loads((BASE / 'native-mods.json').read_text())
    metadata.update(source_patch_digest=identity, parent_native_version=BASE_VERSION,
                    build_method='direct-cargo-source-patches')
    (staging / 'native-mods.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (staging / 'source-patches.json').write_text(json.dumps(record, indent=2) + '\n')
    os.rename(staging, destination)
    build.save(record)
    print(json.dumps({'installed': str(destination), 'selected': False}), flush=True)


if __name__ == '__main__':
    main()
