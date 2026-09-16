# Evidence helper

```python
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / '.rwb/m14-rebase-20260916'
BASE = 'b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22'
OLD = 'f1ee42f34b69ee1ec346e818b2170935e7c6d162'
def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, encoding='utf-8').strip()

head = git('rev-parse','HEAD')
assert git('rev-parse','origin/develop') == BASE
rows = lambda text: {x.split('|')[1].strip():x for x in text.splitlines() if re.match(r'^\| M\d+-\d+ \|',x)}
before = rows(git('show',BASE+':docs/TASKS.md'))
after = rows(git('show',head+':docs/TASKS.md'))
assert set(before) == set(after)
assert [task for task in before if before[task] != after[task]] == ['M14-005']
assert after['M14-005'] == before['M14-005'].replace('| BLOCKED |','| READY |',1)
deps = re.findall(r'M\d+-\d+',before['M14-005'].split('|')[7])
assert len(deps) == 5 and all('| DONE |' in before[x] for x in deps)
assert not git('diff',OLD,head,'--','.github/scripts/release_source_ci.py','tests/test_release_source_ci.py',
               '.github/workflows/ci.yml','work/M14-005/A-20260915-003','work/M14-005/A-20260915-004')
assert not git('diff',BASE,head,'--','src','schemas','registry','pyproject.toml','.github/release-surface.yml',
               '.github/governance-policy.json','work/M14-005/A-20260914-001','work/M14-005/A-20260914-002')
status = git('show',head+':docs/STATUS.md')
base_status = git('show',BASE+':docs/STATUS.md')
assert status.startswith('# 实现状态\n') and not re.search(r'^(<<<<<<<|=======|>>>>>>>)',status,re.M)
phase = lambda text: [x for x in text.splitlines() if x.startswith('| Phase D evaluation entry |')]
assert len(phase(status)) == 1 and phase(status) == phase(base_status)
import yaml
base_policy = yaml.safe_load(git('show', BASE + ':tests/coverage_policy.yaml'))
merged_policy = yaml.safe_load(git('show', head + ':tests/coverage_policy.yaml'))
merged_policy['version'] = base_policy['version']
merged_policy['suites']['coverage-quality']['modules'].remove('test_release_source_ci')
merged_policy['critical_modules'].remove('.github/scripts/release_source_ci.py')
merged_policy['negative_acceptance'] = [item for item in merged_policy['negative_acceptance'] if item['surface'] != 'protected-release-source-ci']
assert merged_policy == base_policy, 'Upstream coverage entries must remain exact'
primary = Path(git('rev-parse', '--git-common-dir')).resolve().parent
assert git('rev-parse','HEAD',cwd=primary) == '11c3b57dfbf8af0dc2587fc421d097e2544941c3'
assert git('branch','--show-current',cwd=primary) == 'develop' and not git('status','--porcelain',cwd=primary)
sys.path.insert(0,str(ROOT / '.github/scripts'))
from check_pr_governance import check_pull_request
from plan_ci import make_plan, canonical
body = (OUT / 'PR_BODY.md').read_text(encoding='utf-8')
repo = 'Chengyue-Lu/research-agent-workbench'
event = {'repository':{'full_name':repo}, 'pull_request':{
    'base':{'ref':'develop','sha':BASE,'repo':{'full_name':repo}},
    'head':{'ref':'feature/m14-005-source-ci','sha':head,'repo':{'full_name':repo}},
    'body':body,'mergeable':True}}
report = check_pull_request(event)
report.emit()
assert not report.has_errors
plan = make_plan(ROOT,base=BASE,head=head,target=head,repository=repo,body=body)
assert not plan['blocked_reasons']
assert plan['behavioral_scope'] == 'full' and plan['coverage_scope'] == 'impact+repository' and plan['package_smoke']
assert not git('diff', BASE, head, '--', '.github/scripts/plan_ci.py', '.github/scripts/ci_dependencies.py', 'tests/ci_impact_policy.yaml')
(OUT / 'ci-plan.json').write_bytes(canonical(plan))
scope = dict(observed_at=datetime.now(timezone.utc).isoformat(),baseline=BASE,head=head,
             task_transition={'M14-005':'BLOCKED -> READY'},dependencies_done=deps,
             other_canonical_rows_unchanged=True,task_definition_unchanged=True,
             implementation_tests_workflow_unchanged_from_reviewed_head=True,
             product_schema_registry_policy_unchanged=True,frozen_archives_unchanged=True,
             upstream_m11_status_preserved=True,primary_clean_unchanged=True,
             behavioral=plan['behavioral_scope'],coverage=plan['coverage_scope'],package=plan['package_smoke'],
             changed_paths=git('diff','--name-only',BASE,head).splitlines(),plan_id=plan['plan_id'])
(OUT / 'scope.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(scope,ensure_ascii=False))

```
