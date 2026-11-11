"""Stage the immutable Nov3 official ARM64 runtime; never overwrite a version."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'outputs/horizon-runtime'
REVISION = 'f42ef42ef6ceccb3c6a20bea2481d87949a51c81'
TAG = 'nightly-2026-11-03-f42ef42'
DIGEST = '58432a760b6af8195a543b520daea89be9396a76633753db61eae3553b762593'
ASSET = 705039399
archive = RUNTIME / 'downloads/horizon-macos-arm64-f42ef42.zip'
release = RUNTIME / 'launcher-data/versions' / TAG
if release.exists():
    raise SystemExit('Refusing to overwrite a staged runtime')
if not archive.exists():
    with archive.open('xb') as output:
        subprocess.run(['gh', 'api', f'repos/horizon-rust/horizon/releases/assets/{ASSET}', '-H', 'Accept: application/octet-stream'], stdout=output, check=True)
with archive.open('rb') as source:
    actual = hashlib.file_digest(source, 'sha256').hexdigest()
if actual != DIGEST or archive.stat().st_size != 37240120:
    raise SystemExit('Publisher size/digest verification failed; no extraction or execution')
print(json.dumps({'event': 'publisher-digest-verified', 'sha256': actual}), flush=True)
spec = importlib.util.spec_from_file_location('prepare_horizon', ROOT / 'tools/prepare-horizon.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.extract_archive(archive, release)
payload = release / 'horizon-macos-arm64'
if set(item.name for item in release.iterdir()) != {'horizon-macos-arm64'} or not payload.is_dir():
    raise SystemExit('Unexpected archive payload layout')
for item in list(payload.iterdir()):
    item.rename(release / item.name)
payload.rmdir()
architecture = subprocess.check_output(['/usr/bin/file', '-b', str(release / 'horizon-client')], text=True).strip()
if 'Mach-O' not in architecture or 'arm64' not in architecture:
    raise SystemExit('Unexpected executable architecture')
record = {'status': 'staged-not-prepared', 'runtime_release': TAG, 'runtime_revision': REVISION,
          'native_hooks_api': 359, 'hook_api_evidence': {'url': f'https://github.com/horizon-rust/horizon/blob/{REVISION}/crates/horizon-client/src/game/native_hooks.rs#L1050', 'verification': 'verified'},
          'asset_id': ASSET, 'asset_sha256': actual, 'asset_size': archive.stat().st_size,
          'publisher_digest_url': f'https://api.github.com/repos/horizon-rust/horizon/releases/assets/{ASSET}',
          'archive_payload_prefix': 'horizon-macos-arm64',
          'architecture': architecture, 'executed_game': False, 'hook_runtime_compatibility_verified': False}
(release / 'runtime-record.json').write_text(json.dumps(record, indent=2) + '\n')
for binary in ['horizon-client', 'horizon-prepare', 'horizon-ctl']:
    result = subprocess.run([str(release / binary), '--help'], capture_output=True, text=True, check=True)
    (release / f'{binary}-help.txt').write_text(result.stdout + result.stderr)
print(json.dumps({'event': 'runtime-staged', 'release': str(release), 'architecture': architecture}), flush=True)
