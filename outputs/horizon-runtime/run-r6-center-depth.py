#!/usr/bin/env python3
"""Compare forced/original vs demand-gated center-depth work in the same R6 binary."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

RUNTIME = Path(__file__).resolve().parent
PARENT = 'native-f42-m1-r3-6b039bd4b49f'
DECISION = re.compile(r'shader pack center depth readback: enabled=(true|false) demand=(true|false) forced=(true|false)')


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--version', required=True)
    parser.add_argument('--dof-control', action='store_true', help='one demand-enabled positive control, not a speed comparison')
    args, remaining = parser.parse_known_args()
    if not re.fullmatch(r'native-f42-m1-r6-[0-9a-f]{12}', args.version):
        parser.error('Expected an installed r6 candidate')
    version = RUNTIME / 'launcher-data/versions' / args.version
    metadata = json.loads((version / 'native-mods.json').read_text())
    if metadata.get('parent_native_version') != PARENT or metadata.get('target') != 'client':
        parser.error('R6 parent/client metadata mismatch')
    spec = importlib.util.spec_from_file_location('r6_native_runner', RUNTIME / 'run-u12-native-packs.py')
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.BUILDS = {'r6': args.version}
    runner.ARM_DEFS = {
        'cd-force': ('r6', 'v4', {'HORIZON_SHADER_PACK_TIMING': '1', 'HORIZON_FORCE_CENTER_DEPTH': '1'}),
        'cd-demand': ('r6', 'v4', {'HORIZON_SHADER_PACK_TIMING': '1', 'HORIZON_FORCE_CENTER_DEPTH': '0'}),
    }
    selected = ['cd-demand'] if args.dof_control else ['cd-force', 'cd-demand']
    runner.CASES = {'makeup': ('makeup', 'cow', 'makeup', selected, 1)}
    runner.PHASES = [['makeup']]
    if args.dof_control:
        if '--dry-run' not in remaining and os.environ.get('HORIZON_TEST_QUEUE') != '1':
            parser.error('Stage/run the DOF control inside the device queue')
        # An immutable separate sidecar; never change the normal trim input.
        options = RUNTIME / 'm1-performance-r6/dof-control/MakeUp-UltraFast-9.6.zip.txt'
        content = runner.TRIM_FILE.read_text().rstrip() + '\nDOF=true\n'
        if options.exists():
            if options.read_text() != content:
                parser.error('Existing DOF control options differ')
        elif '--dry-run' not in remaining:
            options.parent.mkdir(parents=True, exist_ok=True)
            options.write_text(content)
        if '--dry-run' in remaining and not options.exists():
            parser.error('DOF control options not staged; use the normal comparison dry run first')
        runner.TRIM_FILE = options
    original_review = runner.review_cow

    def review(result, profile, migration, shader_key):
        reviewed, status = original_review(result, profile, migration, shader_key)
        arm = re.search(r'-(cd-force|cd-demand)-[0-9]+(?:-redo[0-9]+)?$', profile.name)
        runner.REVIEW.check(arm is not None, 'Unknown center-depth test arm')
        forced = arm[1] == 'cd-force'
        decisions = list(DECISION.finditer((profile / 'console.log').read_text(errors='replace')))
        runner.REVIEW.check(bool(decisions), 'No center-depth activation evidence')
        enabled, demand, actual_force = (v == 'true' for v in decisions[-1].groups())
        runner.REVIEW.check((enabled, demand, actual_force) ==
                            (args.dof_control or forced, args.dof_control, forced),
                            'Center-depth branch does not match the requested control')
        reviewed['center_depth_activation'] = dict(enabled=enabled, demand=demand, forced=actual_force)
        return reviewed, status

    runner.review_cow = review
    if not any(x == '--cases' or x.startswith('--cases=') for x in remaining):
        remaining.extend(['--cases', 'makeup'])
    sys.argv = [sys.argv[0], *remaining]
    return runner.main()


if __name__ == '__main__':
    sys.exit(main())
