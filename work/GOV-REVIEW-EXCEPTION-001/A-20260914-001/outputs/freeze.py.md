# Evidence helper source

```python
"""Freeze deployment receipts and verification for the governance Audit."""
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import yaml

ROOT = Path.cwd()
LOCAL = ROOT / '.rwb/review-exception'
SOURCE = LOCAL / 'evidence'
TASK = 'GOV-REVIEW-EXCEPTION-001'
ATTEMPT = 'A-20260914-001'
ARCHIVE = ROOT / 'work' / TASK / ATTEMPT
assert not ARCHIVE.exists(), 'Frozen Attempt already exists'
HEAD = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
BASE = subprocess.check_output(['git', 'rev-parse', 'origin/develop'], text=True).strip()
changed = subprocess.check_output(['git', 'diff', '--name-only', BASE, HEAD], text=True).splitlines()
assert 'docs/TASKS.md' not in changed and '.github/governance-policy.json' not in changed
coverage = json.loads((SOURCE / 'coverage.json').read_text(encoding='utf-8'))
execution = json.loads((SOURCE / 'execution-test-results.json').read_text(encoding='utf-8'))
assert execution['successful'] and execution['target'] == HEAD
governance_coverage = next(value['summary'] for name, value in coverage['files'].items()
                           if name.replace('\\', '/').endswith('.github/scripts/check_pr_governance.py'))
primary = ROOT.parent / 'research-agent-workbench'
assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=primary, text=True).strip() == ''
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=primary, text=True).strip() == '11c3b57dfbf8af0dc2587fc421d097e2544941c3'
for branch in ['develop', 'main']:
    assert json.loads((SOURCE / (branch + '-hard-before-review.json')).read_text(encoding='utf-8'))['response']['current_user_can_bypass'] == 'never'
    assert json.loads((SOURCE / (branch + '-review-readback.json')).read_text(encoding='utf-8'))['response']['current_user_can_bypass'] == 'pull_requests_only'

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')

def dump(path, data):
    write(path, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))

def ref(path):
    return {'path': path.relative_to(ARCHIVE).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

events = []
def event(kind, payload):
    n = len(events) + 1
    events.append(dict(schema_version='0.1.0', event_id=f'EVT-{n:04}', task_id=TASK, task_revision=1,
                       attempt_id=ATTEMPT, sequence=n, event_type=kind, actor_id='main-agent',
                       occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), payload=payload, redactions=[]))

read_scope = ['AGENTS.md', 'docs/README.md', 'docs/DEVELOPMENT.md', 'docs/DEVELOP_TO_MAIN_RELEASE.md',
              'docs/decisions/README.md', 'docs/workstreams/chengyue-lu/README.md',
              'docs/workstreams/chengyue-lu/GOV-REVIEW-EXCEPTION-001/**', '.github/**',
              'tests/test_documentation.py', 'tests/test_pr_governance.py', 'tests/test_governance_helper_branches.py',
              'tests/coverage_policy.yaml', 'tests/run_unittest_suite.py', 'schemas/**', 'examples/**', 'registry/**',
              'pyproject.toml', 'src/research_workbench/**', 'GitHub rules documentation and repository rules/identity/PR/CI APIs']
write_scope = [*changed, 'work/GOV-REVIEW-EXCEPTION-001/A-20260914-001/**',
               'GitHub exact main/develop hard/review rulesets', 'GitHub feature branch and review PR metadata']
dump(ARCHIVE / 'TASK.yaml', dict(task_id=TASK, revision=1, owner='Chengyue-Lu', risk='R2',
     agent_profile='bounded-governance-review-exception', required_skills=[], delegation=False, baseline=BASE,
     user_request='接受单次维护者例外；无默认等待或缩短为 6 小时，可人工确认另一 reviewer 暂无空闲后由自己一侧批准。',
     goal='Implement the accepted no-wait, single-PR maintainer exception and split remote hard/review gates.',
     read_allowlist=read_scope, write_scope=write_scope,
     stop_conditions=['Publish an independently reviewable R2 PR with exact-head CI and deployment evidence.',
                      'Do not merge any specific PR without its separate explicit maintainer decision.',
                      'Keep primary develop, Task definitions/statuses, dormant release authority and product inputs unchanged.']))
dump(ARCHIVE / 'ACTORS.yaml', dict(schema_version='0.1.0', task_id=TASK, task_revision=1, attempt_id=ATTEMPT,
     actors=[dict(actor_id='main-agent', actor_type='agent', role='governance implementation and remote rollout',
                  runtime_identity='Codex governance review exception', accountable_owner='Chengyue-Lu')]))
write(ARCHIVE / '.gitattributes', '** -text\n')
event('attempt-status', dict(from_status='planned', to_status='running', reason='Retain the accepted governance mechanism, staged remote rollout and verification.'))
gaps = []
for stream in ['events', 'tool-results', 'file-revisions', 'external-actions']:
    event('capture-gap', dict(affected_stream=stream, reason_category='capture-failure',
         reason='Native streams were not exhaustively captured. Material API receipts and check results are retained at freeze, not as a complete realtime transcript.'))
    gaps.append(dict(event_id=events[-1]['event_id'], affected_stream=stream))

tool_refs = []
paths = sorted(SOURCE.glob('*.json')) + [LOCAL / name for name in [
    'focused-final.log', 'repository.log', 'repository-after-setup.log', 'governance.log', 'coverage.log', 'coverage-policy.log']]
for source in paths:
    content = source.read_text(encoding='utf-8-sig')
    for prefix, label in [(str(ROOT), '<governance-worktree>'),
                          (str(ROOT.parent / 'research-agent-workbench-m14-readiness'), '<readiness-worktree>'),
                          (str(primary), '<primary-checkout>'), (tempfile.gettempdir(), '<temporary-root>')]:
        for value in sorted({prefix, prefix.replace('\\', '/'), prefix.replace('\\', '\\\\')}, key=len, reverse=True):
            content = content.replace(value, label)
    target = ARCHIVE / 'tool-events' / source.name
    write(target, content)
    item = ref(target)
    tool_refs.append(item)
    event('tool-call', dict(operation_id='retain-' + source.name, tool_name='gh' if 'response' in content and 'observed_at' in content else 'python',
          status='failed' if source.name == 'repository.log' else 'succeeded',
          arguments=dict(evidence=source.name, capture='Material receipt retained; machine paths redacted; actor readback retains login/id/type only.'),
          result_entered_context=True, result_origin='transient', result_ref=item))

write(ARCHIVE / 'outputs/AUTHORITY.md', '''# Named maintainer decision

On 2026-09-14, Chengyue-Lu accepted the proposed author-as-maintainer single-PR exception and stated:

> 可以接受，默认等待时间不要或者缩短到6小时，可以人工确认另一reviewer目前暂无空闲进行review，则由我这一侧批准单次例外。

Implementation selects no default wait. The authority is limited to Chengyue-Lu (GitHub user ID 140945476).
This accepts the mechanism and its remote configuration; it does not assert reviewer unavailability now or authorize any specific PR merge.
''')
summary = dict(implementation_head=HEAD, baseline=BASE, focused_passed=103,
               coverage_execution_tests=execution['test_count'], coverage_policy='PASS',
               coverage_execution_outcomes=dict(Counter(item['outcome'] for item in execution['tests'])),
               governance_coverage=governance_coverage,
               repository=dict(validated=186, errors=0, warnings=0), configuration_negative_checks=8,
               hard_rulesets={'develop':23305447, 'main':23305460}, review_rulesets={'develop':23192001, 'main':23192054},
               hard_bypass=[], review_bypass=[dict(actor_id=140945476, actor_type='User', bypass_mode='pull_request')],
               remote_tips_unchanged=True, primary_clean=True, primary_head='11c3b57dfbf8af0dc2587fc421d097e2544941c3',
               initial_repository_failure='New worktree had no generated _runtime_pin before editable build; installation in its own venv resolved setup, not a product change.',
               final_head_hosted_ci='Pending final evidence commit and PR push.',
               canonical_task_rows_unchanged=True, specific_pr_merge_authorized=False,
               remote_pr_merges=0, release_authority_changed=False)
write(ARCHIVE / 'outputs/VERIFICATION.json', json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
for name in ['deploy.py', 'prepare_checks.py', 'freeze.py']:
    write(ARCHIVE / 'outputs' / (name + '.md'), '# Evidence helper source\n\n```python\n' + (LOCAL / name).read_text(encoding='utf-8') + '\n```\n')
write(ARCHIVE / 'WORKLOG.md', f'''# Governance review-exception handoff

- Owner: Chengyue-Lu; Audit {TASK}; R2; implementation `{HEAD}`, base `{BASE}`.
- Accepted mechanism: no default wait, personal reviewer-unavailable confirmation and one explicit decision per exact base/head. The PR author may accept this named maintainer responsibility. Decisions do not become cross-owner approvals.
- Staged rollout completed: hard layers 23305447/23305460 have no bypass; review layers 23192001/23192054 retain review settings and grant only User 140945476 PR-only bypass. All requested fields/effective rules and unchanged main/develop tips verified.
- 103 focused checks, 8 negative configuration cases, governance, planned coverage and repository 186/0/0 PASS. Initial repository validation lacked this new worktree's generated runtime pin; its own editable installation resolved that setup failure. Both failure and pass are retained.
- Local primary develop stayed clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3. No specific PR was merged or authorized, and no release/runtime/Task boundary changed.
- Next: exact final-head hosted checks and review of this independent governance PR. A particular merge still needs its own explicit decision. Earlier M14 no-bypass snapshots remain historical; current hard/review configuration is recorded here.
- Native capture is explicitly gapped; material receipts are retained without secrets or hidden reasoning.
''')
event('attempt-status', dict(from_status='running', to_status='safe-paused', reason='Deployment and local evidence frozen; final-head PR CI and individual merge decisions remain separate.'))
write(ARCHIVE / 'events.jsonl', ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in events))
dump(ARCHIVE / 'INDEX.yaml', dict(schema_version='0.1.0', trace_id='TRACE-' + TASK + '-' + ATTEMPT,
     task_id=TASK, task_revision=1, attempt_id=ATTEMPT, archive_root=ATTEMPT, baseline=BASE,
     owner_actor_id='main-agent', owner='Chengyue-Lu', attempt_status='safe-paused', trace_status='frozen', completeness='gapped',
     task_ref=ref(ARCHIVE / 'TASK.yaml'), actors_ref=ref(ARCHIVE / 'ACTORS.yaml'), read_allowlist=read_scope, write_scope=write_scope,
     tool_allowlist=['git', 'gh', 'python', 'apply_patch'], messages=[],
     event_ledger={**ref(ARCHIVE / 'events.jsonl'), 'event_count':len(events)}, tool_event_refs=tool_refs,
     handoff_refs=[ref(ARCHIVE / 'WORKLOG.md')], decision_refs=[ref(ARCHIVE / 'outputs/AUTHORITY.md')],
     output_refs=[ref(path) for path in sorted((ARCHIVE / 'outputs').iterdir())],
     check_refs=[ref(ARCHIVE / '.gitattributes')], capture_gaps=gaps))
print(json.dumps({'archive': ARCHIVE.relative_to(ROOT).as_posix(), 'events': len(events), 'material_receipts': len(paths)}))

```
