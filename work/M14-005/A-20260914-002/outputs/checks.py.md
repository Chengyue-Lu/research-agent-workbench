# Evidence helper source

```python
"""Retain scoped review-repair evidence; no remote mutations."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / '.rwb/m14-005/review-fix'
START = 'c328bbf1bc4084caeeabad613afda8ca00539e46'
PRIMARY = ROOT.parent / 'research-agent-workbench'
FILES = [
    'docs/STATUS.md', 'docs/ROADMAP.md', 'docs/TASKS.md',
    'docs/M_SERIES_IMPLEMENTATION_MAP.md',
    'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/README.md',
    'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/RISK_LEDGER.md',
    'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/READINESS_PREPARATION.md',
]

def now():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def git(*args, cwd=ROOT):
    return subprocess.check_output(['git', *args], cwd=cwd, text=True, encoding='utf-8').strip()

review = json.loads(subprocess.check_output([
    'gh', 'api', 'repos/Chengyue-Lu/research-agent-workbench/issues/comments/5655298378'
], text=True, encoding='utf-8'))
write('review.json', {'observed_at': now(), 'response': review})
pr = json.loads(subprocess.check_output([
    'gh', 'pr', 'view', '78', '--json',
    'url,state,headRefOid,baseRefOid,reviewRequests,reviews,statusCheckRollup'
], text=True, encoding='utf-8'))
write('pr-before.json', {'observed_at': now(), 'response': pr})

before = git('show', START + ':docs/TASKS.md')
after = (ROOT / 'docs/TASKS.md').read_text(encoding='utf-8')
rows = lambda text: '\n'.join(line for line in text.splitlines() if re.match(r'^\| M\d+-\d+ \|', line))
assert rows(before) == rows(after), 'Canonical Task rows changed'
assert '| M14-005 | BLOCKED |' in after
changed = git('diff', '--name-only', START).splitlines()
assert sorted(changed) == sorted(FILES), changed
assert git('rev-parse', 'HEAD', cwd=PRIMARY) == '11c3b57dfbf8af0dc2587fc421d097e2544941c3'
assert git('branch', '--show-current', cwd=PRIMARY) == 'develop'
assert git('status', '--porcelain', cwd=PRIMARY) == ''
assert git('status', '--porcelain', '--', 'work/M14-005/A-20260914-001') == ''
write('scope.json', {
    'observed_at': now(), 'reviewed_head': START, 'base': git('rev-parse', 'origin/develop'),
    'changed_files': changed, 'canonical_task_rows_identical': True,
    'canonical_task_rows_sha256': hashlib.sha256(rows(after).encode()).hexdigest(),
    'm14_005_state': 'BLOCKED', 'product_policy_and_skill_files_unchanged': True,
    'prior_frozen_archive_unchanged': True, 'primary_branch': 'develop',
    'primary_head': git('rev-parse', 'HEAD', cwd=PRIMARY), 'primary_clean': True,
    'document_blob_ids': {name: git('hash-object', '--path=' + name, name) for name in FILES},
})
for name, command in [
    ('documentation', [sys.executable, '-m', 'unittest', 'tests.test_documentation', 'tests.test_public_surface']),
    ('repository', [str(Path(sys.executable).with_name('rwb.exe')), 'validate', 'examples', 'registry', '--root', '.']),
    ('whitespace', ['git', 'diff', '--check']),
]:
    started = now()
    result = subprocess.run(command, text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout.replace(str(ROOT), '<readiness-worktree>')
    (OUT / (name + '.log')).write_text(output, encoding='utf-8', newline='\n')
    write(name + '.json', {'started_at': started, 'finished_at': now(), 'exit_code': result.returncode,
                           'command': [Path(command[0]).name, *command[1:]], 'reviewed_head': START,
                           'target': 'working tree document blobs recorded in scope.json'})
    print(name, 'exit', result.returncode, '\n' + '\n'.join(output.splitlines()[-7:]), flush=True)
    if result.returncode:
        sys.exit(result.returncode)

```
