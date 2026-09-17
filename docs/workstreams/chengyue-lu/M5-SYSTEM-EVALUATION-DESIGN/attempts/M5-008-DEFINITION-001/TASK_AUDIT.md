# Task-definition audit

Executed with Python 3.14 from the repository root; output is in `CHECKS.md` (task-definition-check.json).
This is a bounded documentation/governance probe, not a new product test or live evidence.

```python
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

root = Path.cwd()
sys.path.insert(0, str(root / '.github/scripts'))
import check_pr_governance as governance

base = '0d4a1d00a4c32ca9b822df6482a95920e7c21b1b'
before = subprocess.check_output(['git', 'show', base + ':docs/TASKS.md']).decode('utf-8')
after = (root / 'docs/TASKS.md').read_text(encoding='utf-8')
old = governance.parse_task_rows(before)
new = governance.parse_task_rows(after)
changed = {key for key in old if (old[key].status, old[key].remainder) != (new[key].status, new[key].remainder)}
assert set(new) - set(old) == {'M5-008'}
assert changed == {'M5-004'}
assert all((v.status, v.remainder) == (new[k].status, new[k].remainder) for k, v in old.items() if v.status == 'DONE')
assert new['M5-004'].status == new['M5-008'].status == 'BLOCKED'
deps = lambda row: governance._dependency_ids(row.dependencies)
assert deps(new['M5-004']) == deps(old['M5-004']) | {'M5-008'}
assert deps(new['M5-008']) == {'M5-007', 'M6-004'}
def reachable(start):
    seen, pending = set(), list(deps(new[start]))
    while pending:
        key = pending.pop()
        assert key in new, (start, key)
        if key not in seen:
            seen.add(key)
            pending.extend(deps(new[key]))
    return seen
# Audit cycles introduced by this change; historical completed-task cycles are outside this PR.
assert 'M5-008' not in reachable('M5-008')
assert 'M5-004' not in reachable('M5-008')
paths = subprocess.check_output(['git', 'diff', '--name-only', base]).decode().splitlines()
paths += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', 'docs']).decode().splitlines()
def check(text, declared={'M5-004', 'M5-008'}, changed_paths=paths):
    report = governance.GovernanceReport()
    governance.validate_task_changes(base_text=before, head_text=text, pr_class='task-definition', changed_paths=changed_paths,
                                    declared_task_ids=declared, effective_risk='R2', verification_evidence='Task-definition audit', report=report)
    return report
assert not check(after).has_errors
assert check(after.replace('| M5-008 | BLOCKED |', '| M5-008 | DONE |')).has_errors
assert check(after, declared={'M5-008'}).has_errors
assert check(after, changed_paths=paths + ['src/research_workbench/evaluation/live.py']).has_errors
done_row = next(line for line in after.splitlines() if line.startswith('| M5-006 | DONE |'))
assert check(after.replace(done_row, done_row.replace('冻结 System-Level', '改写 System-Level', 1))).has_errors
result = {
    'base': base, 'kind': 'task-definition working-tree audit',
    'source_task_sha256': hashlib.sha256(before.encode()).hexdigest(),
    'candidate_task_sha256': hashlib.sha256((root / 'docs/TASKS.md').read_bytes()).hexdigest(),
    'added': ['M5-008'], 'revised': sorted(changed), 'unchanged_done_tasks': sum(v.status == 'DONE' for v in old.values()),
    'm5_007_unchanged': True, 'dependencies_preserved_no_new_cycle': True,
    'governance_task_check': 'PASS',
    'negative_probes': {'premature_DONE': 'rejected', 'undeclared_M5_004_change': 'rejected',
                        'implementation_in_task_definition': 'rejected', 'DONE_definition_rewrite': 'rejected'},
}
print(json.dumps(result, ensure_ascii=False, indent=2))
```
