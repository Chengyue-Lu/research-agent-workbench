"""Nightly scheduling suppression; never reuse a previous test result as evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from release_source_ci import GitHub
from run_component_ci import commit, git, save

WORKFLOW = '.github/workflows/ci_checkpoint.yml'
# Include test/CI inputs too: changing a test must allow the nightly to run again.
PREFIXES = ('src/', 'schemas/', 'registry/', '.agents/', 'templates/', 'tests/', '.github/', 'tools/')
FILES = {'pyproject.toml', 'setup.py', 'setup.cfg', 'MANIFEST.in', 'runtime-resources.json',
         'requirements.txt', 'requirements-dev.txt', 'uv.lock', 'poetry.lock', '.python-version'}


def content_fingerprint(repo, source):
    commit(repo, source)
    rows = git(repo, 'ls-tree', '-rz', '--full-tree', source).split(b'\0')
    selected = []
    for row in rows:
        if not row:
            continue
        _, name = row.split(b'\t', 1)
        path = name.decode('utf-8')
        if (path.startswith(PREFIXES) or path in FILES or path.startswith('requirements')
                or '/' not in path and path.endswith(('.py', '.toml', '.lock'))):
            selected.append(row)
    if not selected:
        raise ValueError('no checkpoint inputs')
    return hashlib.sha256(b'\0'.join(sorted(selected))).hexdigest()


def already_checked(api, fingerprint):
    """Only our recent successful scheduled runs can suppress another nightly.

    The marker is uploaded after all producers succeed. No receipt is downloaded,
    re-signed or reported for the new commit. Missing history means run again.
    """
    rows = api.get('actions/workflows/ci_checkpoint.yml/runs?event=schedule&status=success&per_page=30')['workflow_runs']
    for run in rows:
        if (run.get('event') != 'schedule' or run.get('status') != 'completed'
                or run.get('conclusion') != 'success' or run.get('path') != WORKFLOW
                or run.get('repository', {}).get('full_name') != api.repository):
            continue
        artifacts = api.pages(f"actions/runs/{run['id']}/artifacts", 'artifacts')
        if any(a.get('name') == 'nightly-content-' + fingerprint and not a.get('expired') for a in artifacts):
            return run['id']
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--scheduled', action='store_true')
    parser.add_argument('--output', required=True)
    parser.add_argument('--github-output', required=True)
    args = parser.parse_args(argv)
    fingerprint = content_fingerprint(Path.cwd(), args.source)
    previous = already_checked(GitHub(args.repository), fingerprint) if args.scheduled else None
    value = dict(source=args.source, fingerprint=fingerprint, execute=previous is None,
                 previous_scheduled_run=previous, result_reused=False,
                 reason='unchanged nightly inputs' if previous else 'new inputs or explicit checkpoint')
    save(args.output, value)
    with open(args.github_output, 'a', encoding='utf-8', newline='\n') as stream:
        stream.write(f"execute={str(value['execute']).lower()}\nfingerprint={fingerprint}\n")
    print(json.dumps(value))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
