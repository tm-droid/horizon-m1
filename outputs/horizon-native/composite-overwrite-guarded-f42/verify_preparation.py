#!/usr/bin/env python3
"""Verify sparse source/provenance and clean application; no Rust or device execution."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = ROOT / 'outputs/horizon-runtime/m1-performance-r3/candidate-source'
paths = json.loads((HERE / 'baseline-sha256.json').read_text())
for relative, expected in paths.items():
    assert hashlib.sha256((BASE / relative).read_bytes()).hexdigest() == expected, relative
print('PASS: both daily-r3 baseline source hashes unchanged')
patch = HERE / 'composite-overwrite-guarded.patch'
subprocess.run(['git', 'apply', '--check', str(patch)], cwd=BASE, check=True)
print('PASS: patch applies cleanly to read-only daily-r3 baseline')
with tempfile.TemporaryDirectory(prefix='composite-guard-patch-') as temporary:
    scratch = Path(temporary)
    for relative in paths:
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((BASE / relative).read_bytes())
    subprocess.run(['git', 'apply', str(patch)], cwd=scratch, check=True)
    for relative in paths:
        assert (scratch / relative).read_bytes() == (HERE / 'candidate-source' / relative).read_bytes(), relative
print('PASS: patched disposable files match prepared candidate exactly')
print('NOT RUN: Rust compilation/tests, GPU activation, shader controls, visuals or performance')
