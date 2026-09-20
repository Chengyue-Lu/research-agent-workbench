"""Join live source CI and deterministic release checks in a trusted source checkout.

Caller pins are independent of the candidate manifest. No candidate code is run,
and this preparatory entry point never grants merge or publication authority.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import release_source_ci as source_ci
import release_surface as surface

ROOT = Path(__file__).resolve().parents[2]
TOOL = '.github/scripts/release_preflight.py'
TRUSTED_FILES = (TOOL, source_ci.TOOL, surface.TOOL, *surface.SCHEMAS.values(),
                 '.github/scripts/check_pr_governance.py', '.github/governance-policy.json')


def current_refs(root, api, source, parent):
    """Bind local refs to fresh protected remote observations, without mutating refs."""
    tips = {}
    for name in ('develop', 'main'):
        branch = api.get(f'branches/{name}')
        source_ci.require(branch['name'] == name and branch['protected'] is True,
                          f'protected {name} required')
        tip = source_ci.sha(branch['commit']['sha'])
        source_ci.require(source_ci.git(root, 'rev-parse', f'refs/remotes/origin/{name}').decode().strip() == tip,
                          f'fetch current {name} before preflight')
        tips[name] = tip
    source_ci.git(root, 'merge-base', '--is-ancestor', source, tips['develop'])
    source_ci.require(tips['main'] == parent, 'current main parent drift; regenerate')
    return tips


def check(root, api, *, source, parent, policy_version, release_version, run_id, candidate, manifest_sha256):
    source_ci.sha(parent)
    source_ci.sha(candidate)
    source_ci.require(isinstance(manifest_sha256, str) and
                      len(manifest_sha256) == 64 and all(c in '0123456789abcdef' for c in manifest_sha256),
                      'independent exact manifest SHA-256 required')
    source_ci.local_source(root, api.repository, source)
    for path in TRUSTED_FILES:
        source_ci.require(source_ci.git(root, 'show', f'{source}:{path}') == (ROOT / path).read_bytes(),
                          f'trusted source checker byte drift: {path}')
    before = current_refs(root, api, source, parent)
    observation = source_ci.attest(api, source, run_id)
    expected = dict(repository=api.repository, source=source, parent=parent,
                    policy_version=policy_version, release_version=release_version,
                    source_ci=observation['source_ci'])
    # Rebuild twice from Git blobs in independent directories outside the checkout.
    with tempfile.TemporaryDirectory(prefix='rwb-release-preflight-') as temporary:
        first, second = (Path(temporary) / name for name in ('first', 'second'))
        first.mkdir(); second.mkdir()
        result = surface.export(root, expected, first)
        repeated = surface.export(root, expected, second)
        source_ci.require(result == repeated, 'repeated projection differs')
        source_ci.require(result['manifest_sha256'] == manifest_sha256,
                          'projection differs from independent manifest pin')
        candidate_result = surface.check(root, expected, candidate, directory=first)
        source_ci.require(candidate_result == result, 'candidate differs from repeated projection')
    after = current_refs(root, api, source, parent)
    source_ci.require(before == after, 'protected refs changed during preflight')
    # A rerun/state change after the first observation invalidates this attempt.
    final_observation = source_ci.attest(api, source, run_id)
    source_ci.require(final_observation == observation, 'source CI changed during preflight')
    return dict(repository=api.repository, source=source, parent=parent, candidate=candidate,
                policy_version=policy_version, release_version=release_version,
                projection=result, source_ci=observation['source_ci'], observation=observation['observation'],
                protected_refs=after, merge_eligible=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repository', 'source', 'parent', 'policy-version', 'release-version', 'candidate', 'manifest-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    source_ci.require(not args.output.exists(), 'output already exists')
    result = check(ROOT, source_ci.GitHub(args.repository), source=args.source, parent=args.parent,
                   policy_version=args.policy_version, release_version=args.release_version,
                   run_id=args.run_id, candidate=args.candidate, manifest_sha256=args.manifest_sha256)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'result': 'PASS', 'source': args.source, 'candidate': args.candidate, 'merge_eligible': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
