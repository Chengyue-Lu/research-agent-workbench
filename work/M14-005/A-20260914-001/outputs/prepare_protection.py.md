# Evidence helper source

```python
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / '.rwb/m14-005/evidence'
OUT.mkdir(parents=True, exist_ok=True)
REPO = 'Chengyue-Lu/research-agent-workbench'

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def capture(name, args):
    result = subprocess.run(args, cwd=ROOT, text=True, encoding='utf-8', capture_output=True)
    try:
        data = json.loads(result.stdout)
    except ValueError:
        data = result.stdout
    save(name, {'observed_at': datetime.now(timezone.utc).isoformat(), 'command': args,
                'exit_code': result.returncode, 'data': data, 'stderr': result.stderr})
    if result.returncode:
        raise RuntimeError(f'{name}: {result.stderr}')
    return data

if __name__ == '__main__':
    capture('before-rulesets.json', ['gh', 'api', f'repos/{REPO}/rulesets'])
    capture('repository.json', ['gh', 'api', f'repos/{REPO}', '--jq',
            '{full_name,visibility,default_branch,permissions,allow_squash_merge,allow_merge_commit,allow_rebase_merge}'])
    capture('pr77-merge.json', ['gh', 'pr', 'view', '77', '--repo', REPO, '--json',
            'url,state,headRefOid,baseRefName,mergedAt,mergeCommit,reviews,comments'])
    capture('check-app-identity.json', ['gh', 'api',
            f'repos/{REPO}/commits/cbf646d1d4139da249277615a88f54d9cdf5586d/check-runs'])
    for branch, approvals, method in [('develop', 0, 'squash'), ('main', 1, 'merge')]:
        capture(f'before-{branch}.json', ['gh', 'api', f'repos/{REPO}/branches/{branch}'])
        capture(f'before-{branch}-effective.json', ['gh', 'api', f'repos/{REPO}/rules/branches/{branch}'])
        ruleset = {
            'name': f'RWB {branch} protection', 'target': 'branch', 'enforcement': 'active',
            'bypass_actors': [],
            'conditions': {'ref_name': {'include': [f'refs/heads/{branch}'], 'exclude': []}},
            'rules': [
                {'type': 'deletion'}, {'type': 'non_fast_forward'},
                {'type': 'pull_request', 'parameters': {
                    'allowed_merge_methods': [method],
                    'dismiss_stale_reviews_on_push': True,
                    'require_code_owner_review': True,
                    'require_last_push_approval': branch == 'main',
                    'required_approving_review_count': approvals,
                    'required_review_thread_resolution': True}},
                {'type': 'required_status_checks', 'parameters': {
                    'required_status_checks': [{'context': context, 'integration_id': 15368}
                                               for context in ['governance', 'test (3.11)', 'test (3.13)']],
                    'strict_required_status_checks_policy': True,
                    'do_not_enforce_on_create': False}}
            ]
        }
        save(f'{branch}-ruleset-request.json', ruleset)
    print('Saved prestate and two exact-ref ruleset requests; no mutation performed.')

```
