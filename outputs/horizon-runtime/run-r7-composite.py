#!/usr/bin/env python3
"""Isolate guarded attachment-load elision from the other r4 changes."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

RUNTIME = Path(__file__).resolve().parent
PARENT = 'native-f42-m1-r3-6b039bd4b49f'


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--version', required=True)
    args, remaining = parser.parse_known_args()
    if not re.fullmatch(r'native-f42-m1-r7-[0-9a-f]{12}', args.version):
        parser.error('Expected an installed r7 candidate')
    metadata = json.loads((RUNTIME / 'launcher-data/versions' / args.version / 'native-mods.json').read_text())
    if metadata.get('parent_native_version') != PARENT or metadata.get('target') != 'client':
        parser.error('R7 parent/client metadata mismatch')
    spec = importlib.util.spec_from_file_location('r7_native_runner', RUNTIME / 'run-u12-native-packs.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.BUILDS = {'r3': PARENT, 'r7': args.version}
    runner.ARM_DEFS = {'b1-base': ('r3', 'v4', {}),
                       'b1-trial': ('r7', 'v4', {})}
    runner.CASES = {'makeup': ('makeup', 'cow', 'makeup', ['b1-base', 'b1-trial'], 1)}
    runner.PHASES = [['makeup']]
    original_review = runner.review_cow

    def review(result, profile, migration, shader_key):
        reviewed, status = original_review(result, profile, migration, shader_key)
        if re.search(r'-b1-trial-[0-9]+(?:-redo[0-9]+)?$', profile.name):
            matches = re.findall(r'overwrite attachment loads for ([0-9]+) of ([0-9]+) post passes',
                                 (profile / 'console.log').read_text(errors='replace'))
            runner.REVIEW.check(bool(matches) and 0 < int(matches[-1][0]) <= int(matches[-1][1]),
                                'No active attachment-load elision proof')
            reviewed['overwrite_activation'] = {'passes': int(matches[-1][0]), 'post_passes': int(matches[-1][1])}
        return reviewed, status

    runner.review_cow = review
    if not any(x == '--cases' or x.startswith('--cases=') for x in remaining):
        remaining.extend(['--cases', 'makeup'])
    sys.argv = [sys.argv[0], *remaining]
    return runner.main()


if __name__ == '__main__':
    sys.exit(main())
