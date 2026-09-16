# Evidence helper

```python
"""Retain and verify current read-only release protection observations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess

OUT = Path('.rwb/m14-rebase-20260916')
REPO = 'Chengyue-Lu/research-agent-workbench'
ENDPOINTS = {
    **{f'ruleset-{n}': f'rulesets/{n}' for n in (23305447, 23192001, 23305460, 23192054)},
    **{f'branch-{b}': f'branches/{b}' for b in ('develop', 'main')},
    **{f'effective-{b}': f'rules/branches/{b}' for b in ('develop', 'main')},
    'rulesets': 'rulesets?includes_parents=true&per_page=100',
    'pr80': 'pulls/80',
    'pr80-comments': 'issues/80/comments?per_page=100',
}

def fetch(item):
    name, endpoint = item
    result = subprocess.run(['gh', 'api', '--hostname', 'github.com', f'repos/{REPO}/{endpoint}'],
                            capture_output=True, check=True)
    path = OUT / f'{name}.json'
    assert not path.exists(), f'Receipt already exists: {name}'
    path.write_bytes(result.stdout)
    return name, json.loads(result.stdout)

observed_at = datetime.now(timezone.utc).isoformat()
with ThreadPoolExecutor(max_workers=4) as pool:
    data = dict(pool.map(fetch, ENDPOINTS.items()))
expected_checks = {'governance', 'test (3.11)', 'test (3.13)'}
summary = {'observed_at': observed_at, 'repository': REPO, 'branches': {}, 'mutations': False}
for branch, hard_id, review_id, method in [('develop',23305447,23192001,'squash'), ('main',23305460,23192054,'merge')]:
    hard, review = (data[f'ruleset-{n}'] for n in (hard_id, review_id))
    for rule in (hard, review):
        assert rule['enforcement'] == 'active' and rule['target'] == 'branch'
        assert rule['conditions']['ref_name'] == {'exclude': [], 'include': [f'refs/heads/{branch}']}
    assert hard['bypass_actors'] == []
    assert review['bypass_actors'] == [{'actor_id': 140945476, 'actor_type': 'User', 'bypass_mode': 'pull_request'}]
    hr = {x['type']: x for x in hard['rules']}
    assert {'deletion','non_fast_forward','pull_request','required_status_checks'} <= set(hr)
    hp = hr['pull_request']['parameters']
    assert hp['allowed_merge_methods'] == [method] and hp['required_review_thread_resolution']
    checks = hr['required_status_checks']['parameters']
    assert checks['strict_required_status_checks_policy']
    assert len(checks['required_status_checks']) == 3
    assert {x['context'] for x in checks['required_status_checks']} == expected_checks
    assert all(x['integration_id'] == 15368 for x in checks['required_status_checks'])
    rp = next(x['parameters'] for x in review['rules'] if x['type'] == 'pull_request')
    assert rp['required_approving_review_count'] == (0 if branch == 'develop' else 1)
    assert rp['require_code_owner_review'] and rp['dismiss_stale_reviews_on_push']
    assert rp['require_last_push_approval'] == (branch == 'main')
    assert data[f'branch-{branch}']['protected']
    effective = data[f'effective-{branch}']
    assert {hard_id, review_id} <= {x['ruleset_id'] for x in effective}
    for rule in hard['rules'] + review['rules']:
        origin = hard_id if rule in hard['rules'] else review_id
        assert any(x['ruleset_id'] == origin and x['type'] == rule['type'] and
                   x.get('parameters') == rule.get('parameters') for x in effective)
    summary['branches'][branch] = {'tip': data[f'branch-{branch}']['commit']['sha'],
        'hard_ruleset': hard_id, 'review_ruleset': review_id, 'protected': True,
        'required_checks': sorted(expected_checks), 'check_app_id': 15368,
        'strict_latest_base': True, 'merge_method': method, 'hard_bypass_actors': [],
        'review_bypass_actors': review['bypass_actors'], 'effective_rules_match': True}
summary['receipts'] = {name: {'path': f'{name}.json', 'sha256': hashlib.sha256((OUT / f'{name}.json').read_bytes()).hexdigest()}
                       for name in ENDPOINTS}
(OUT / 'remote-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
print(json.dumps({k:v for k,v in summary.items() if k != 'receipts'}, ensure_ascii=False, indent=2))

```
