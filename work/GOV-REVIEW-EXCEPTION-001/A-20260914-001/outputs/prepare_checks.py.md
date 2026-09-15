# Evidence helper source

```python
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / '.rwb/review-exception/evidence'
sys.path.insert(0, str(ROOT / '.github/scripts'))
from check_pr_governance import check_pull_request
from plan_ci import make_plan, canonical

base = subprocess.check_output(['git', 'rev-parse', 'origin/develop'], text=True).strip()
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
body = (ROOT / '.rwb/review-exception/PR_BODY.md').read_text(encoding='utf-8')
repo = 'Chengyue-Lu/research-agent-workbench'
event = {'repository': {'full_name': repo}, 'pull_request': {
    'base': {'ref': 'develop', 'sha': base, 'repo': {'full_name': repo}},
    'head': {'ref': 'feature/review-maintainer-exception', 'sha': head, 'repo': {'full_name': repo}},
    'body': body, 'mergeable': True}}
(OUT / 'local-pr-event.json').write_bytes(canonical(event))
report = check_pull_request(event)
report.emit()
assert not report.has_errors
plan = make_plan(ROOT, base=base, head=head, target=head, repository=repo, body=body)
(OUT / 'ci-plan.json').write_bytes(canonical(plan))
print(json.dumps({'head': head, 'base': base, 'plan_id': plan['plan_id'],
                  'behavioral': plan['behavioral_scope'], 'coverage': plan['coverage_scope'],
                  'package': plan['package_smoke']}))

```
