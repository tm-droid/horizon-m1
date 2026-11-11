#!/usr/bin/env python3
"""Lightweight artifact integrity checks; never compile or touch the baseline."""
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
print('PASS: all three baseline source hashes unchanged')
subprocess.run(['git', 'apply', '--check', str(HERE / 'be-occlusion-cache.patch')], cwd=BASE, check=True)
print('PASS: patch applies cleanly to read-only r3 baseline')
with tempfile.TemporaryDirectory(prefix='be-cache-patch-') as temporary:
    scratch = Path(temporary)
    for relative in paths:
        target = scratch / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((BASE / relative).read_bytes())
    subprocess.run(['git', 'apply', str(HERE / 'be-occlusion-cache.patch')], cwd=scratch, check=True)
    for relative in paths:
        assert (scratch / relative).read_bytes() == (HERE / 'candidate-source' / relative).read_bytes(), relative
print('PASS: patched disposable files exactly match prepared candidate')
render = (HERE / 'candidate-source/crates/horizon-client-render/src/block_entity_render.rs').read_text()
base_render = (BASE / 'crates/horizon-client-render/src/block_entity_render.rs').read_text()
start = '    pub fn render_with_gpu_cache_options'
end = '    /// Draws block entities in one section-grouped pass'
assert render[render.index(start):render.index(end)] == base_render[base_render.index(start):base_render.index(end)]
assert 'fn includes_overhangs_and_negative_section_origins()' in render
assert 'fn invalid_or_empty_geometry_has_no_occlusion_proof()' in render
print('PASS: cache warming/publication API unchanged; two Rust bounds tests prepared')
print('NOT RUN: Rust type/format checks, Rust tests, visual parity, performance benchmark')
