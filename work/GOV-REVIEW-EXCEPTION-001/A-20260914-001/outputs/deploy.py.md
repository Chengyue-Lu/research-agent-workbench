# Evidence helper source

```python
"""One-shot, staged ruleset split with retained REST requests/readbacks."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path.cwd()
OUT = ROOT / '.rwb/review-exception/evidence'
OUT.mkdir(parents=True, exist_ok=True)
REPO = 'Chengyue-Lu/research-agent-workbench'
IDS = {'develop': 23192001, 'main': 23192054}
ACTOR = {'actor_id': 140945476, 'actor_type': 'User', 'bypass_mode': 'pull_request'}
REVIEW_FIELDS = {'dismiss_stale_reviews_on_push': False, 'required_approving_review_count': 0,
                 'require_code_owner_review': False, 'require_last_push_approval': False,
                 'required_reviewers': [], 'require_extra_approval_for_unattributed_changes': False}

def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))

def api(name, route, *, method='GET', payload=None):
    assert not (OUT / (name + '.json')).exists(), 'Retained API receipt already exists: ' + name
    args = ['gh', 'api', route, '-H', 'X-GitHub-Api-Version: 2026-03-10', '--method', method]
    if payload is not None:
        save(name + '-request.json', payload)
        args += ['--input', str(OUT / (name + '-request.json'))]
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        response = result.stdout
    if route == 'user' and isinstance(response, dict) and result.returncode == 0:
        response = {key: response[key] for key in ['login', 'id', 'type']}
    save(name + '.json', {'observed_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                         'method': method, 'route': route, 'exit_code': result.returncode,
                         'response': response, 'stderr': result.stderr})
    if result.returncode:
        raise RuntimeError(f'{name} failed; retained response: {response}')
    return response

def request(raw):
    return {key: deepcopy(raw[key]) for key in ['name', 'target', 'enforcement', 'bypass_actors', 'conditions', 'rules']}

def rules(value):
    result = {rule['type']: rule for rule in value['rules']}
    assert len(result) == len(value['rules'])
    return result

def validate(branch, original, hard, review):
    for value in [hard, review]:
        assert value['target'] == 'branch' and value['enforcement'] == 'active'
        assert value['conditions'] == {'ref_name': {'include': ['refs/heads/' + branch], 'exclude': []}}
    old_rules, hard_rules, review_rules = rules(original), rules(hard), rules(review)
    assert set(old_rules) == set(hard_rules) == {'deletion', 'non_fast_forward', 'pull_request', 'required_status_checks'}
    assert set(review_rules) == {'pull_request'}
    assert hard['bypass_actors'] == [] and review['bypass_actors'] == [ACTOR]
    for kind in ['deletion', 'non_fast_forward', 'required_status_checks']:
        assert hard_rules[kind] == old_rules[kind]
    checks = hard_rules['required_status_checks']['parameters']
    assert checks['strict_required_status_checks_policy'] is True
    assert checks['do_not_enforce_on_create'] is False
    assert checks['required_status_checks'] == [
        {'context': name, 'integration_id': 15368} for name in ['governance', 'test (3.11)', 'test (3.13)']]
    old_pr = old_rules['pull_request']['parameters']
    hard_pr = hard_rules['pull_request']['parameters']
    assert hard_pr == {**old_pr, **REVIEW_FIELDS}
    assert hard_pr['required_review_thread_resolution'] is True
    assert hard_pr['allowed_merge_methods'] == (['squash'] if branch == 'develop' else ['merge'])
    assert review_rules['pull_request'] == old_rules['pull_request']

def prepare():
    actor = api('actor', 'user')
    assert (actor['login'], actor['id']) == ('Chengyue-Lu', ACTOR['actor_id'])
    collaborators = api('collaborators', f'repos/{REPO}/collaborators?per_page=100')
    assert [item['login'] for item in collaborators if item['permissions']['admin']] == ['Chengyue-Lu']
    listing = api('rulesets-before', f'repos/{REPO}/rulesets')
    assert {item['id'] for item in listing} == set(IDS.values())
    for branch, ident in IDS.items():
        api(branch + '-tip-before', f'repos/{REPO}/branches/{branch}')
        api(branch + '-effective-before', f'repos/{REPO}/rules/branches/{branch}')
        original = request(api(branch + '-before', f'repos/{REPO}/rulesets/{ident}'))
        assert original['bypass_actors'] == []
        hard = deepcopy(original)
        hard['name'] = 'RWB ' + branch + ' hard gates'
        rules(hard)['pull_request']['parameters'].update(REVIEW_FIELDS)
        review = deepcopy(original)
        review['name'] = 'RWB ' + branch + ' review'
        review['rules'] = [rules(original)['pull_request']]
        review['bypass_actors'] = [ACTOR]
        validate(branch, original, hard, review)
        save(branch + '-hard-plan.json', hard)
        save(branch + '-review-plan.json', review)
    negatives = []
    for title, mutation in [
        ('hard bypass', lambda h, r: h.update(bypass_actors=[ACTOR])),
        ('wrong actor', lambda h, r: r['bypass_actors'][0].update(actor_id=240712654)),
        ('always mode', lambda h, r: r['bypass_actors'][0].update(bypass_mode='always')),
        ('exempt mode', lambda h, r: r['bypass_actors'][0].update(bypass_mode='exempt')),
        ('missing checks', lambda h, r: rules(h)['required_status_checks']['parameters']['required_status_checks'].pop()),
        ('merge method drift', lambda h, r: rules(h)['pull_request']['parameters'].update(allowed_merge_methods=['merge'])),
        ('review drift', lambda h, r: rules(r)['pull_request']['parameters'].update(require_code_owner_review=False)),
        ('latent hard approval', lambda h, r: rules(h)['pull_request']['parameters'].update(require_extra_approval_for_unattributed_changes=True)),
    ]:
        original = request(read('develop-before.json')['response'])
        hard, review = read('develop-hard-plan.json'), read('develop-review-plan.json')
        mutation(hard, review)
        try:
            validate('develop', original, hard, review)
        except AssertionError:
            negatives.append({'mutation': title, 'rejected': True})
        else:
            raise AssertionError('Mutation accepted: ' + title)
    save('negative-checks.json', negatives)
    print(json.dumps({'prepared': list(IDS), 'negative_checks_rejected': len(negatives)}))

def hard_layers():
    for branch, ident in IDS.items():
        original = request(read(branch + '-before.json')['response'])
        current = request(api(branch + '-before-create', f'repos/{REPO}/rulesets/{ident}'))
        assert current == original, 'Unexpected remote drift'
        payload = read(branch + '-hard-plan.json')
        created = api(branch + '-hard-create', f'repos/{REPO}/rulesets', method='POST', payload=payload)
        checked = api(branch + '-hard-readback', f'repos/{REPO}/rulesets/{created["id"]}')
        assert request(checked) == payload, 'Hard readback drift; review layer remains unchanged'
        api(branch + '-effective-layered', f'repos/{REPO}/rules/branches/{branch}')
    print('Hard layers created and read back; original protections remain.')

def review_layers():
    # Both no-bypass hard layers must exist and match before either review change.
    for branch in IDS:
        hard_id = read(branch + '-hard-create.json')['response']['id']
        fresh = api(branch + '-hard-before-review', f'repos/{REPO}/rulesets/{hard_id}')
        assert request(fresh) == read(branch + '-hard-plan.json')
    for branch, ident in IDS.items():
        current = api(branch + '-review-before-update', f'repos/{REPO}/rulesets/{ident}')
        assert request(current) == request(read(branch + '-before.json')['response'])
        payload = read(branch + '-review-plan.json')
        api(branch + '-review-update', f'repos/{REPO}/rulesets/{ident}', method='PUT', payload=payload)
        review = api(branch + '-review-readback', f'repos/{REPO}/rulesets/{ident}')
        assert request(review) == payload
        hard = read(branch + '-hard-before-review.json')['response']
        validate(branch, request(read(branch + '-before.json')['response']), request(hard), request(review))
        effective = api(branch + '-effective-after', f'repos/{REPO}/rules/branches/{branch}')
        for layer in [hard, review]:
            observed = [{key: val for key, val in item.items() if not key.startswith('ruleset_')}
                        for item in effective if item['ruleset_id'] == layer['id']]
            assert sorted(observed, key=lambda item:item['type']) == sorted(layer['rules'], key=lambda item:item['type'])
        after = api(branch + '-tip-after', f'repos/{REPO}/branches/{branch}')
        before = read(branch + '-tip-before.json')['response']
        assert after['protected'] and after['commit']['sha'] == before['commit']['sha']
    api('rulesets-after', f'repos/{REPO}/rulesets')
    print(json.dumps({branch: {'hard': read(branch+'-hard-create.json')['response']['id'],
          'review': ident, 'hard_bypass': [], 'review_bypass': [ACTOR]} for branch, ident in IDS.items()}))

{'prepare': prepare, 'hard': hard_layers, 'review': review_layers}[sys.argv[1]]()

```
