"""Prepare an exact, read-only main ruleset cutover payload.

The output is a review artifact, not permission to apply it. The eventual writer
must reobserve the complete prestate and use one ruleset update; any drift stops
the cutover. This command never sends a mutating GitHub request.
"""
from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

import release_source_ci as source_ci


ROOT = Path(__file__).resolve().parents[2]
TOOL = '.github/scripts/release_ruleset_cutover.py'
FIELDS = ('name', 'target', 'enforcement', 'bypass_actors', 'conditions', 'rules')
APP = 15368
OLD_MAIN = ('governance', 'test (3.11)', 'test (3.13)')
NEW_MAIN = ('release preflight (3.11)', 'release preflight (3.13)')
DEVELOP = ('governance', 'CI result')
OWNER_BYPASS = [{'actor_id': 140945476, 'actor_type': 'User', 'bypass_mode': 'pull_request'}]


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(',', ':')) + '\n').encode('utf-8')


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def checks(names: tuple[str, ...]) -> list[dict[str, object]]:
    return [{'context': name, 'integration_id': APP} for name in names]


def validate_ruleset(value: dict, *, repository: str, identity: int,
                     branch: str, layer: str) -> None:
    source_ci.require(value.get('id') == identity and value.get('source_type') == 'Repository'
                      and value.get('source') == repository, 'foreign ruleset')
    source_ci.require(value.get('target') == 'branch' and value.get('enforcement') == 'active',
                      'ruleset must be active on branches')
    source_ci.require(value.get('conditions') == {
        'ref_name': {'include': [f'refs/heads/{branch}'], 'exclude': []}},
        'ruleset must target the exact branch')
    expected_bypass = [] if layer == 'hard' else OWNER_BYPASS
    source_ci.require(value.get('bypass_actors') == expected_bypass,
                      'unexpected ruleset bypass')
    rules = value.get('rules')
    source_ci.require(isinstance(rules, list), 'ruleset rules missing')
    indexed = {rule['type']: rule for rule in rules}
    wanted = {'deletion', 'non_fast_forward', 'pull_request', 'required_status_checks'} \
        if layer == 'hard' else {'pull_request'}
    source_ci.require(len(indexed) == len(rules) and set(indexed) == wanted,
                      'unexpected or missing protection rule')
    method = 'merge' if branch == 'main' else 'squash'
    pr = indexed['pull_request']['parameters']
    source_ci.require(pr.get('allowed_merge_methods') == [method]
                      and pr.get('required_review_thread_resolution') is True,
                      'PR merge protection changed')
    if layer == 'review':
        source_ci.require(pr.get('required_approving_review_count') == (1 if branch == 'main' else 0)
                          and pr.get('require_code_owner_review') is True
                          and pr.get('dismiss_stale_reviews_on_push') is True
                          and pr.get('require_last_push_approval') is (branch == 'main'),
                          'review protection changed')
        return
    source_ci.require(pr.get('required_approving_review_count') == 0,
                      'hard PR approval layer changed')
    status = indexed['required_status_checks']['parameters']
    expected = OLD_MAIN if branch == 'main' else DEVELOP
    source_ci.require(status.get('required_status_checks') == checks(expected)
                      and status.get('strict_required_status_checks_policy') is True
                      and status.get('do_not_enforce_on_create') is False,
                      'hard required checks changed')


def payloads(main_hard: dict) -> tuple[dict, dict]:
    before = {field: copy.deepcopy(main_hard[field]) for field in FIELDS}
    after = copy.deepcopy(before)
    status = next(rule for rule in after['rules'] if rule['type'] == 'required_status_checks')
    status['parameters']['required_status_checks'] = checks(NEW_MAIN)
    return before, after


def same_effective(api: source_ci.GitHub, branch: str, hard: dict, review: dict) -> None:
    observed = api.get(f'rules/branches/{branch}')
    expected = []
    for layer in (hard, review):
        expected.extend({'type': rule['type'], 'parameters': rule.get('parameters'),
                         'ruleset_id': layer['id'], 'ruleset_source': api.repository,
                         'ruleset_source_type': 'Repository'} for rule in layer['rules'])
    source_ci.require(isinstance(observed, list) and
                      Counter(digest({key: rule.get(key) for key in expected[0]}) for rule in observed) ==
                      Counter(digest(rule) for rule in expected),
                      f'{branch} effective rules differ from reviewed layers')


def prepare(api: source_ci.GitHub, *, source: str, parent: str,
            run_id: int, ids: dict[str, dict[str, int]]) -> dict:
    source_ci.sha(source)
    source_ci.sha(parent)
    repo = api.get('')
    source_ci.require(repo.get('full_name') == api.repository and repo.get('default_branch') == 'main',
                      'repository identity/default branch changed')
    branches = {branch: api.get(f'branches/{branch}') for branch in ('develop', 'main')}
    source_ci.require(branches['develop']['protected'] is True and
                      branches['develop']['commit']['sha'] == source and
                      branches['main']['protected'] is True and
                      branches['main']['commit']['sha'] == parent,
                      'protected branch tip or flag changed')
    contract = source_ci.active_contract(ROOT, source)
    attestation = source_ci.attest_contract(api, source, run_id, contract)
    layers = {}
    for branch in ('develop', 'main'):
        layers[branch] = {}
        for layer in ('hard', 'review'):
            identity = source_ci.positive(ids[branch][layer])
            value = api.get(f'rulesets/{identity}')
            validate_ruleset(value, repository=api.repository, identity=identity,
                             branch=branch, layer=layer)
            layers[branch][layer] = value
        same_effective(api, branch, layers[branch]['hard'], layers[branch]['review'])
    source_ci.require(api.get('branches/develop')['commit']['sha'] == source and
                      api.get('branches/main')['commit']['sha'] == parent,
                      'branch tip drift during ruleset observation')
    source_ci.require(source_ci.attest_contract(api, source, run_id, contract)['observation'] ==
                      attestation['observation'], 'source CI changed during ruleset observation')
    before, after = payloads(layers['main']['hard'])
    return {'before': before, 'cutover': after, 'source_ci': attestation,
            'manifest': {'repository': api.repository, 'source': source, 'parent': parent,
                         'source_ci_run_id': run_id, 'ruleset_ids': ids,
                         'main_hard_readback_sha256': digest(layers['main']['hard']),
                         'main_hard_payload_sha256': digest(before),
                         'cutover_payload_sha256': digest(after),
                         'develop_hard_readback_sha256': digest(layers['develop']['hard']),
                         'main_review_readback_sha256': digest(layers['main']['review']),
                         'develop_review_readback_sha256': digest(layers['develop']['review']),
                         'applied': False, 'merge_eligible': False}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--parent', required=True)
    parser.add_argument('--run-id', required=True, type=int)
    for branch in ('develop', 'main'):
        for layer in ('hard', 'review'):
            parser.add_argument(f'--{branch}-{layer}-ruleset', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    source_ci.require(__debug__, 'optimized cutover preparation is forbidden')
    source_ci.require(not args.output.exists(), 'output directory already exists')
    source_ci.local_source(ROOT, args.repository, args.source)
    source_ci.require(source_ci.git(ROOT, 'show', f'{args.source}:{TOOL}') ==
                      (ROOT / TOOL).read_bytes(), 'cutover preparer byte drift')
    ids = {branch: {layer: getattr(args, f'{branch}_{layer}_ruleset')
                    for layer in ('hard', 'review')} for branch in ('develop', 'main')}
    result = prepare(source_ci.GitHub(args.repository), source=args.source,
                     parent=args.parent, run_id=args.run_id, ids=ids)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, value in result.items():
        (args.output / f'{name}.json').write_bytes(canonical(value))
    print(json.dumps({'result': 'PASS', 'source': args.source, 'parent': args.parent,
                      'applied': False, 'merge_eligible': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
