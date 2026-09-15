# Evidence helper source

```python
import json
from prepare_protection import OUT, REPO, capture, save

existing = capture('resume-before-rulesets.json', ['gh', 'api', f'repos/{REPO}/rulesets'])
assert [(row['id'], row['name']) for row in existing] == [(23192001, 'RWB develop protection')]

def normalize(rules):
    rules = json.loads(json.dumps(rules))
    for rule in rules:
        if rule['type'] == 'pull_request':
            params = rule['parameters']
            # GitHub adds these defaults to the request. Retain them in raw evidence;
            # require their observed values rather than discarding arbitrary extras.
            assert params.pop('required_reviewers', []) == []
            assert params.pop('require_extra_approval_for_unattributed_changes', True) is True
    return sorted(rules, key=lambda r: r['type'])
ids = {}
for branch in ['develop', 'main']:
    request = OUT / f'{branch}-ruleset-request.json'
    if branch == 'develop':
        result = json.loads((OUT / 'develop-create-response.json').read_bytes())['data']
    else:
        result = capture(f'{branch}-create-response.json', ['gh', 'api', '--method', 'POST',
                         f'repos/{REPO}/rulesets', '--input', request.relative_to(OUT.parents[2]).as_posix()])
    ids[branch] = result['id']
    actual = capture(f'{branch}-ruleset-readback.json', ['gh', 'api', f'repos/{REPO}/rulesets/{result["id"]}'])
    expected = json.loads(request.read_bytes())
    for field in ['name', 'target', 'enforcement', 'bypass_actors', 'conditions']:
        assert actual[field] == expected[field], (branch, field, actual[field], expected[field])
    assert normalize(actual['rules']) == normalize(expected['rules'])
    effective = capture(f'{branch}-effective-readback.json', ['gh', 'api', f'repos/{REPO}/rules/branches/{branch}'])
    normalized = [{k: v for k, v in rule.items() if k in ['type', 'parameters']} for rule in effective]
    assert normalize(normalized) == normalize(expected['rules'])
    branch_data = capture(f'after-{branch}.json', ['gh', 'api', f'repos/{REPO}/branches/{branch}'])
    assert branch_data['protected'] is True
    before = json.loads((OUT / f'before-{branch}.json').read_bytes())['data']
    assert branch_data['commit']['sha'] == before['commit']['sha']
    print(f'{branch}: ruleset {result["id"]} active; exact readback and effective rules PASS; tip unchanged')
capture('after-rulesets.json', ['gh', 'api', f'repos/{REPO}/rulesets'])
capture('develop-codeowners-errors.json', ['gh', 'api', f'repos/{REPO}/codeowners/errors?ref=develop'])
save('protection-verification.json', {'ruleset_ids': ids, 'requested_fields_readback_match': True,
    'server_added_pull_request_defaults': {'required_reviewers': [], 'require_extra_approval_for_unattributed_changes': True},
    'effective_rules_match': True, 'protected_both_branches': True, 'branch_tips_unchanged': True,
    'destructive_push_probes_performed': False, 'release_attestation_implemented': False})

```
