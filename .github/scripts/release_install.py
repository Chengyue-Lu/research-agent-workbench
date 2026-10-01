"""Diagnose a release candidate's installed package from a verified projection.

This source-owned check is release-only evidence, never merge authorization. The
candidate remains Git data; only the independently rebuilt projection is built.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

import portable_package_smoke as portable
import release_governance as governance
import release_preflight as preflight
import release_public as public
import release_source_ci as source_ci
import release_surface as surface


ROOT = Path(__file__).resolve().parents[2]
TOOL = '.github/scripts/release_install.py'
PACKAGE_TOOL = '.github/scripts/portable_package_smoke.py'


def check(root: Path, api, *, source: str, parent: str, policy_version: str,
          release_version: str, run_id: int, candidate: str, manifest_sha256: str,
          interpreter: str, pr_number: int) -> dict:
    source_ci.require(__debug__, 'optimized release checker is forbidden')
    # The live preflight must finish before any projected build backend is run.
    trusted = preflight.check(root, api, source=source, parent=parent,
                              policy_version=policy_version, release_version=release_version,
                              run_id=run_id, candidate=candidate, manifest_sha256=manifest_sha256)
    for path in (TOOL, PACKAGE_TOOL, governance.TOOL):
        source_ci.require(source_ci.git(root, 'show', f'{source}:{path}') == (root / path).read_bytes(),
                          f'trusted release install byte drift: {path}')
    governance_result = governance.check(api, number=pr_number, source=source, parent=parent,
        candidate=candidate, release_version=release_version, manifest_sha256=manifest_sha256,
        preflight=trusted)
    public_result = public.check(root, api.repository, source, candidate)
    expected = dict(repository=api.repository, source=source, parent=parent,
                    policy_version=policy_version, release_version=release_version,
                    source_ci=trusted['source_ci'])
    with tempfile.TemporaryDirectory(prefix='rwb-release-install-') as temporary:
        projection = Path(temporary).resolve() / 'projection'
        projection.mkdir()
        rebuilt = surface.export(root, expected, projection)
        source_ci.require(rebuilt == trusted['projection'], 'release install projection drift')
        source_ci.require(rebuilt['manifest_sha256'] == manifest_sha256,
                          'release install manifest pin drift')
        source_ci.require(surface.check(root, expected, candidate, directory=projection) == rebuilt,
                          'release install candidate drift')
        package = portable.check(projection, [interpreter])
    source_ci.require(preflight.current_refs(root, api, source, parent) == trusted['protected_refs'],
                      'protected refs changed during install')
    source_ci.require(source_ci.attest_contract(api, source, run_id,
                      source_ci.active_contract(root, source))['observation'] == trusted['observation'],
                      'source CI changed during install')
    governance.reobserve(api, governance_result, release_version=release_version,
                         repository_id=trusted['observation']['repository_id'])
    source_ci.require(trusted['merge_eligible'] is False and public_result['merge_eligible'] is False
                      and package['merge_eligible'] is False, 'diagnostic cannot grant merge authority')
    source_ci.require(package['runtime_resources_identical'] and
                      {(row['route'], row['isolated']) for row in package['installs']} == {
                          (route, isolated) for route in ('direct', 'sdist-wheel')
                          for isolated in (True, False)} and len(package['installs']) == 4,
                      'both clean-install routes and isolation modes required')
    return dict(repository=api.repository, source=source, parent=parent, candidate=candidate,
                policy_version=policy_version, release_version=release_version,
                preflight=trusted, projection=rebuilt, governance=governance_result,
                public=public_result, package=package,
                python=package['installs'][0]['python'], merge_eligible=False)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repository', 'source', 'parent', 'policy-version', 'release-version',
                 'candidate', 'manifest-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--python', required=True, help='exact interpreter used for fresh installs')
    parser.add_argument('--pr-number', type=int, required=True, help='live same-repository main PR')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    source_ci.require(not args.output.exists(), 'output already exists')
    result = check(ROOT, source_ci.GitHub(args.repository), source=args.source,
                   parent=args.parent, policy_version=args.policy_version,
                   release_version=args.release_version, run_id=args.run_id,
                   candidate=args.candidate, manifest_sha256=args.manifest_sha256,
                   interpreter=args.python, pr_number=args.pr_number)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'result': 'PASS', 'candidate': args.candidate,
                      'python': result['python'], 'merge_eligible': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
