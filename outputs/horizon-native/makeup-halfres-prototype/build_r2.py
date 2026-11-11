#!/usr/bin/env python3
"""Revision two: preserve r1 archive/source and change reconstruction only."""
from pathlib import Path
import build as base

HERE = Path(__file__).resolve().parent
OUT = base.OUT.with_name('MakeUp-M1-HalfRes-r2.zip')


def build():
    base.build(output=OUT, manifest_path=HERE / 'manifest-r2.json', overrides={
        'shaders/common/m1_upsample_fragment.glsl': (HERE / 'm1_upsample_fragment_r2.glsl').read_bytes(),
        'M1-PROTOTYPE.md': (HERE / 'README-r2.md').read_bytes(),
    })


if __name__ == '__main__':
    build()
