"""Hosted cost experiment on explicit hypothetical future-develop Git bases.

This produces benchmark evidence only, never required PR aggregate identities.
"""
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

import yaml

root = Path.cwd()
manifest = json.loads(Path(sys.argv[1]).read_bytes())
case = next(c for c in manifest['cases'] if c['name'] == os.environ['PROBE_CASE'])
kind = os.environ['PROBE_KIND']
started = time.time()
receipt = {'case': case['name'], 'kind': kind, 'base': case['base'], 'head': case['head'],
           'python': platform.python_version(), 'authority_status': manifest['authority_status'],
           'shared_baseline': manifest['shared_baseline'], 'phases': {}, 'successful': False}
# The experiment supplies a proposed future-develop base, rather than using a PR
# or dispatch event to assert it has already become accepted repository authority.
os.environ.pop('GITHUB_EVENT_PATH', None)
os.environ['GITHUB_EVENT_NAME'] = 'pull_request'
sys.path.insert(0, str(root / '.github/scripts'))
import plan_ci as planner

def run(label, command):
    begin = time.perf_counter()
    result = subprocess.run(command, cwd=root)
    receipt['phases'][label] = {'seconds': round(time.perf_counter() - begin, 3), 'exit_code': result.returncode}
    result.check_returncode()

try:
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == case['head']
    plan = planner.make_plan(root, base=case['base'], head=case['head'], target=case['head'],
                            repository='Chengyue-Lu/research-agent-workbench',
                            body='- **Risk tier**: R2\n- **Shared contract**: no\n- **Authority impact**: no')
    assert plan['tests'] == case['tests'] and plan['coverage_tests'] == case['coverage_tests'], 'selection drift from frozen manifest'
    assert plan['coverage_obligations'] == ['impact'] and not plan['blocked_reasons']
    (root / 'ci-plan.json').write_bytes(planner.canonical(plan))
    receipt.update(plan_id=plan['plan_id'], behavioral_scope=plan['behavioral_scope'], coverage_scope=plan['coverage_scope'],
                   package_smoke=plan['package_smoke'], repository_smoke=plan['repository_smoke'])
    if kind == 'behavioral':
        suite = 'full' if plan['behavioral_scope'] == 'full' else 'focused'
        run('behavioral', [sys.executable, 'tests/run_unittest_suite.py', '--suite', suite,
                          '--plan', 'ci-plan.json', '--json-output', 'benchmark-test-results.json', '--verbosity', '0'])
        result = json.loads((root / 'benchmark-test-results.json').read_bytes())
    else:
        assert kind == 'coverage'
        workflow = yaml.safe_load((root / '.github/workflows/ci.yml').read_bytes())
        steps = workflow['jobs']['coverage_quality']['steps']
        for name in ('Run required coverage test union', 'Export coverage evidence'):
            step = next(s for s in steps if s.get('name') == name)
            run(name, ['bash', '-e', '-o', 'pipefail', '-c', step['run']])
        run('impact gate', [sys.executable, '.github/scripts/ci_checks.py', 'coverage', '--plan', 'ci-plan.json',
                            '--coverage', 'coverage.json', '--results', 'coverage-test-results.json'])
        result = json.loads((root / 'coverage-test-results.json').read_bytes())
    assert result['successful'] and result['target'] == case['head'] and result['plan_id'] == plan['plan_id']
    receipt.update(test_count=result['test_count'], suite_wall_seconds=result['wall_seconds'], successful=True)
finally:
    receipt['harness_seconds'] = round(time.time() - started, 3)
    receipt['job_until_receipt_seconds'] = round(time.time() - int(os.environ['PROBE_STARTED_AT']), 3)
    (root / 'benchmark.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)
