"""Bind release PR governance to a fresh source-owned preflight in the same call.

Only release_install calls this helper, after live preflight. Saved receipts,
candidate metadata and process environment cannot supply governance expectations.
The result is machine evidence; human review and release approval remain separate.
"""
from __future__ import annotations

import hashlib
import json

import check_pr_governance as governance
import release_source_ci as source_ci


TOOL = '.github/scripts/release_governance.py'


def observe(api, *, number: int, candidate: str, parent: str,
            release_version: str, repository_id: int) -> dict:
    source_ci.positive(number)
    pr = api.get(f'pulls/{number}')
    source_ci.require(pr['number'] == number and pr['state'] == 'open' and
                      pr['merged'] is False, 'open release PR required')
    for ref in ('base', 'head'):
        source_ci.same_repository(pr[ref]['repo'], api.repository, repository_id)
    source_ci.require(pr['base']['ref'] == 'main' and pr['base']['sha'] == parent and
                      pr['head']['ref'] == f'release/v{release_version}' and
                      pr['head']['sha'] == candidate, 'release PR ref binding mismatch')
    source_ci.require(pr.get('mergeable') is not False, 'release PR has merge conflicts')
    # Compare governance inputs, not volatile repository timestamps or counters.
    result = {key: pr[key] for key in ('number', 'state', 'merged', 'body')}
    for ref in ('base', 'head'):
        result[ref] = {key: pr[ref][key] for key in ('ref', 'sha')}
        result[ref]['repo'] = {key: pr[ref]['repo'][key] for key in ('full_name', 'id')}
    return result


def check(api, *, number: int, source: str, parent: str, candidate: str,
          release_version: str, manifest_sha256: str, preflight: dict) -> dict:
    source_ci.require(governance.CURATED_RELEASE_TOPOLOGY['activation_state'] == 'active',
                      'curated release governance is dormant')
    ci = preflight['source_ci']
    source_ci.require(ci['repository'] == api.repository and ci['sha'] == source and
                      ci['conclusion'] == 'success' and preflight['source'] == source and
                      preflight['parent'] == parent and preflight['candidate'] == candidate and
                      preflight['projection']['manifest_sha256'] == manifest_sha256,
                      'fresh preflight governance binding mismatch')
    repository_id = source_ci.positive(preflight['observation']['repository_id'])
    pr = observe(api, number=number, candidate=candidate, parent=parent,
                 release_version=release_version, repository_id=repository_id)
    expectations = {
        'expected_source_repository': api.repository, 'expected_source_ref': 'develop',
        'expected_source_sha': source, 'expected_parent_sha': parent,
        'expected_manifest_sha256': manifest_sha256,
        'source_ci_run_id': str(ci['run_id']), 'source_ci_workflow': ci['workflow'],
        'source_ci_repository': ci['repository'], 'source_ci_ref': 'develop',
        'source_ci_sha': ci['sha'], 'source_ci_conclusion': ci['conclusion'],
        'source_ci_required_checks': json.dumps({name: 'success' for name in ci['required_checks']},
                                               sort_keys=True),
    }
    report = governance.check_pull_request({'pull_request': pr}, release_expectations=expectations)
    report.emit()
    source_ci.require(not report.has_errors and report.effective_risk == 'R2',
                      'trusted release PR governance rejected')
    metadata = governance.parse_metadata(str(pr['body'] or ''))
    source_ci.require('M14-005' in governance.task_ids_from_metadata(metadata.get('Task ID(s)', '')),
                      'release PR must declare activation Task M14-005')
    return {'pull_request': number, 'source': source, 'parent': parent, 'candidate': candidate,
            'governance': 'success', 'effective_risk': report.effective_risk,
            'body_sha256': hashlib.sha256(str(pr['body'] or '').encode('utf-8')).hexdigest(),
            'pr_observation': pr, 'merge_eligible': False}


def reobserve(api, receipt: dict, *, release_version: str, repository_id: int) -> None:
    final = observe(api, number=receipt['pull_request'], candidate=receipt['candidate'],
                    parent=receipt['parent'], release_version=release_version,
                    repository_id=repository_id)
    source_ci.require(final == receipt['pr_observation'], 'release PR changed during install')
