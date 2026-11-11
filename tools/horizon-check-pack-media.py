#!/usr/bin/env python3
"""Decode each PNG and Ogg member from an immutable daily pack snapshot."""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile

from PIL import Image


def check_media(pack, expected_hash):
    with pack.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != expected_hash:
            raise ValueError(f'Snapshot archive changed: {pack}')
    counts = Counter()
    failures = []
    with zipfile.ZipFile(pack) as archive:
        for entry in archive.infolist():
            extension = Path(entry.filename).suffix.lower()
            if entry.is_dir() or extension not in ('.png', '.ogg'):
                continue
            data = archive.read(entry)
            try:
                if extension == '.png':
                    with Image.open(io.BytesIO(data), formats=['PNG']) as texture:
                        texture.verify()
                    with Image.open(io.BytesIO(data), formats=['PNG']) as texture:
                        texture.load()
                else:
                    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-xerror',
                                    '-i', 'pipe:0', '-map', '0:a:0', '-f', 'null', '-'],
                                   input=data, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                   check=True, timeout=30)
            except (OSError, ValueError, SyntaxError, subprocess.SubprocessError) as error:
                detail = (error.stderr.decode(errors='replace').strip() if isinstance(error, subprocess.CalledProcessError)
                          else str(error))
                failures.append({'path': entry.filename, 'error': detail})
            else:
                counts[extension[1:]] += 1
    return {'pack': pack.name, 'sha256': expected_hash, 'decoded': dict(counts), 'failures': failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    manifest = json.loads((args.snapshot / 'manifest.json').read_text())
    packs = [check_media(args.snapshot / 'resourcepacks' / name, sha)
             for name, sha in manifest['snapshot_sha256'].items()]
    decoded = Counter()
    for pack in packs:
        decoded.update(pack['decoded'])
    totals = {'packs': len(packs), 'decoded': dict(decoded),
              'failures': sum(len(pack['failures']) for pack in packs)}
    args.output.write_text(json.dumps({'totals': totals, 'packs': packs}, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(totals))
    return bool(totals['failures'])


if __name__ == '__main__':
    raise SystemExit(main())
