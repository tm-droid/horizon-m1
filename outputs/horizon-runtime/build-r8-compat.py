#!/usr/bin/env python3
"""Build isolated daily compatibility patches from verified installed sources.

Queue-only. --dry-run verifies/stages source without Cargo or installation.
Never changes daily selection. Inherits r3's CEM/Zoom source and metadata.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

RUNTIME = Path(__file__).resolve().parent
ROOT = RUNTIME.parents[1]
DATA = RUNTIME / 'launcher-data'
BASE_VERSION = 'native-f42-m1-r3-6b039bd4b49f'
SOURCE = RUNTIME / 'm1-performance-r3/candidate-source'
PATCH = ROOT / 'outputs/horizon-native/daily-compat-f42/daily-compat.patch'


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
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--charged-creeper', action='store_true')
    mode.add_argument('--cem-part-textures', action='store_true')
    mode.add_argument('--cem-part-variants', action='store_true')
    mode.add_argument('--makeup-dropped-light', action='store_true')
    args = parser.parse_args()
    if os.environ.get('HORIZON_TEST_QUEUE') != '1':
        parser.error('Run inside the shared device queue')
    build_id, base_version, source, patch = 'r8', BASE_VERSION, SOURCE, PATCH
    if args.charged_creeper:
        build_id = 'r9'
        base_version = 'native-f42-m1-r8-903e75d76f09'
        source = RUNTIME / 'm1-performance-r8/20261107-143005/source'
        patch = ROOT / 'outputs/horizon-native/charged-creeper-f42/charged-creeper.patch'
    elif args.cem_part_textures:
        build_id = 'r10'
        base_version = 'native-f42-m1-r8-903e75d76f09'
        source = RUNTIME / 'm1-performance-r8/20261107-143005/source'
        patch = ROOT / 'outputs/horizon-native/cem-part-texture-f42/cem-part-texture.patch'
    elif args.cem_part_variants:
        build_id = 'r11'
        base_version = 'native-f42-m1-r10-e8c108dbd1dc'
        source = RUNTIME / 'm1-performance-r10/20261108-084936/source'
        patch = ROOT / 'outputs/horizon-native/cem-part-variants-f42/cem-part-variants.patch'
    elif args.makeup_dropped_light:
        build_id = 'r12'
        base_version = 'native-f42-m1-r11-ef12b7f4368d'
        source = RUNTIME / 'm1-performance-r11/20261108-091244/source'
        patch = ROOT / 'outputs/horizon-native/makeup-dropped-light-r11/makeup-dropped-light.patch'
    base = DATA / 'versions' / base_version
    build = load('r8_build_helpers', RUNTIME / 'build-nightly-6475f62.py')
    original = json.loads((base / 'source-patches.json').read_text())
    expected = original['candidate_files']
    if build.inventory(source) != expected:
        raise SystemExit(f'{base_version} source differs from its installed build inventory')
    if not patch.is_file():
        raise SystemExit('Missing daily compatibility patch')
    if not args.dry_run:
        gates = load('r8_gates', RUNTIME / 'run-codex-continuation.py')
        problems = gates.gate_problems(check_idle=False)
        if problems:
            raise SystemExit('Build gates failed: ' + '; '.join(problems))
        build.preflight(5)
    lab = RUNTIME / f'm1-performance-{build_id}' / time.strftime('%Y%m%d-%H%M%S')
    lab.mkdir(parents=True, exist_ok=False)
    work = lab / 'source'
    run(['/bin/cp', '-cR', str(source), str(work)])
    run(['git', 'apply', '--check', str(patch)], cwd=work)
    run(['git', 'apply', '--whitespace=nowarn', str(patch)], cwd=work)
    # Shared target artifacts may come from a different revision despite older
    # imported source mtimes. Force all local inputs fresh, not just this patch.
    for path in work.rglob('*'):
        if path.is_file() and not path.is_symlink():
            path.touch()
    files = build.inventory(work)
    identity = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    version = f'native-f42-m1-{build_id}-' + identity[:12]
    destination = DATA / 'versions' / version
    if destination.exists():
        raise SystemExit('Already installed: ' + version)
    build.LAB = lab
    build.STATUS = lab / 'build-status.json'
    command = [str(build.TOOLCHAIN / 'bin/cargo'), 'build', '--offline', '--locked', '--profile', 'fast',
               '--manifest-path', str(work / 'Cargo.toml'), '-p', 'horizon-client', '--bin', 'horizon-client']
    record = {'complete': False, 'runtime_verified': False, 'base_version': base_version,
              'source_revision': original['source_revision'], 'candidate_version': version,
              'source_digest': identity, 'source': str(work), 'candidate_files': files,
              'patch_sha256': build.digest(patch), 'command': command, 'samples': [],
              'profile': 'fast', 'rust': '1.99.1'}
    build.save(record)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'version': version, 'source': str(work)}))
        return
    for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
        signal.signal(signum, build.cancellation)
    env = build.cargo_env()
    env['DYLD_FALLBACK_LIBRARY_PATH'] = str(build.TOOLCHAIN / 'lib')
    build.compile_client(command, env, record, build_id)
    if build.inventory(work) != files or build.inventory(source) != expected:
        raise SystemExit('Source changed during build; refusing installation')
    staging = destination.with_name(destination.name + '.new')
    if destination.exists() or staging.exists():
        raise SystemExit('Installation destination already exists')
    run(['/bin/cp', '-cR', str(base), str(staging)])
    import shutil
    shutil.copy2(build.CARGO_TARGET / 'fast/horizon-client', staging / 'horizon-client')
    record.update(complete=True, binary_sha256=build.digest(staging / 'horizon-client'))
    metadata = json.loads((base / 'native-mods.json').read_text())
    metadata.update(source_patch_digest=identity, parent_native_version=base_version,
                    build_method='direct-cargo-source-patches')
    (staging / 'native-mods.json').write_text(json.dumps(metadata, indent=2) + '\n')
    (staging / 'source-patches.json').write_text(json.dumps(record, indent=2) + '\n')
    os.rename(staging, destination)
    build.save(record)
    print(json.dumps({'installed': str(destination), 'selected': False}), flush=True)


if __name__ == '__main__':
    main()
