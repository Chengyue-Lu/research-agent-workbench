# Evidence helper source

```python
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / '.github/scripts'))
from plan_ci import make_plan, canonical
from check_pr_governance import check_pull_request

head = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
base = 'f7a9715ed35787d3326283c22f834b1514c5c88c'
body = (ROOT / '.rwb/m14-005/PR_BODY.md').read_text(encoding='utf-8')
repo = 'Chengyue-Lu/research-agent-workbench'
event = {'repository': {'full_name':repo}, 'pull_request': {
    'base': {'ref':'develop','sha':base,'repo':{'full_name':repo}},
    'head': {'ref':'feature/m14-005-readiness','sha':head,'repo':{'full_name':repo}},
    'body':body,'mergeable':True}}
out=ROOT / '.rwb/m14-005/evidence'
(out/'local-pr-event.json').write_bytes(canonical(event))
report = check_pull_request(event)
report.emit()
assert not report.has_errors
plan = make_plan(ROOT, base=base, head=head, target=head, repository=repo, body=body)
(out/'ci-plan.json').write_bytes(canonical(plan))
print(json.dumps({'head':head,'plan_id':plan['plan_id'],'behavioral':plan['behavioral_scope'],
                  'coverage':plan['coverage_scope'],'package':plan['package_smoke']}))

```
