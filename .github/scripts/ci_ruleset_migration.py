"""Prepare reviewable develop required-check payloads; never modify GitHub."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from release_source_ci import GitHub, positive, require
from run_component_ci import canonical, save

FIELDS = ('name', 'target', 'enforcement', 'bypass_actors', 'conditions', 'rules')
OLD = ['governance', 'test (3.11)', 'test (3.13)']
NEW = ['governance', 'CI result']
APP = 15368


def payloads(current):
    require(current['target'] == 'branch' and current['enforcement'] == 'active', 'inactive or non-branch ruleset')
    require(current['bypass_actors'] == [], 'hard ruleset must have no bypass actors')
    require(current['conditions'] == {'ref_name': {'include': ['refs/heads/develop'], 'exclude': []}},
            'ruleset must target only develop')
    kinds = [rule['type'] for rule in current['rules']]
    require(len(kinds) == len(set(kinds)), 'duplicate rule type')
    require({'required_status_checks', 'pull_request', 'deletion', 'non_fast_forward'} <= set(kinds),
            'missing hard protection')
    index = kinds.index('required_status_checks')
    parameters = current['rules'][index]['parameters']
    require(parameters['strict_required_status_checks_policy'] is True
            and parameters['do_not_enforce_on_create'] is False, 'strict required checks must be enabled')
    checks = parameters['required_status_checks']
    require(checks == [{'context': name, 'integration_id': APP} for name in OLD], 'unexpected current required checks')
    result = {}
    for stage, names in [('rollback', OLD), ('intersection', OLD + ['CI result']), ('components', NEW)]:
        value = copy.deepcopy({name: current[name] for name in FIELDS})
        value['rules'][index]['parameters']['required_status_checks'] = [
            {'context': name, 'integration_id': APP} for name in names]
        result[stage] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--ruleset', required=True, type=int)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    api = GitHub(args.repository)
    current = api.get(f'rulesets/{positive(args.ruleset)}')
    require(current['source_type'] == 'Repository' and current['source'] == args.repository
            and current['id'] == args.ruleset, 'foreign ruleset')
    values = payloads(current)
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output/'before.json', current)
    for name, value in values.items():
        save(args.output/(name+'.json'), value)
    save(args.output/'manifest.json', dict(repository=args.repository, ruleset_id=args.ruleset,
         before_sha256=hashlib.sha256(canonical(current)).hexdigest(),
         payload_sha256={name: hashlib.sha256(canonical(value)).hexdigest() for name, value in values.items()},
         applied=False, approval_granted=False))
    print('Read-only payload preparation complete; review and explicit cutover are still required.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
