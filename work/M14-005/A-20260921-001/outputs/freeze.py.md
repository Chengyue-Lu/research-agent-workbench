# Evidence helper

```python
"""Freeze the scoped rebase checkpoint without modifying earlier Attempts."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import yaml

root = Path.cwd()
local = root / '.rwb/m14-rebase-20260921'
archive = root / 'work/M14-005/A-20260921-001'
assert not archive.exists()
scope = json.loads((local / 'scope.json').read_text(encoding='utf-8'))
remote = json.loads((local / 'remote-summary.json').read_text(encoding='utf-8'))
focused = (local / 'focused.log').read_text(encoding='utf-8')
match = re.search(r'Ran (\d+) tests in [\d.]+s\s+OK\b', focused)
assert match, 'Focused tests must finish successfully before freezing'
assert remote['branches']['develop']['tip'] == scope['baseline']
assert (local / 'repository.log').read_text(encoding='utf-8').strip() == 'validated=186 errors=0 warnings=0'
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == scope['head']

def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')

def dump(path, value):
    write(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False))

def ref(path):
    return dict(path=path.relative_to(archive).as_posix(), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

read_scope = ['AGENTS.md', 'docs/README.md', 'docs/DEVELOPMENT.md', 'docs/TASKS.md', 'docs/STATUS.md',
              'docs/ROADMAP.md', 'docs/M_SERIES_IMPLEMENTATION_MAP.md',
              'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/**', '.github/**', 'tests/**',
              'examples/**', 'registry/**', 'work/M14-005/**',
              'GitHub PR 80, Issue 57 and read-only CI/protection APIs']
write_scope = ['docs/STATUS.md', 'tests/coverage_policy.yaml',
               'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/SOURCE_CI.md',
               'work/M14-005/A-20260921-001/**', 'M14 feature branch rebase and PR 80 evidence/review request']
dump(archive / 'TASK.yaml', dict(task_id='M14-005', revision=1, owner='Chengyue-Lu', risk='R2',
    agent_profile='bounded-rebase-verification', required_skills=[], delegation=False, baseline=scope['baseline'],
    user_request='跟进到目前最新进度，M14-005有冲突待解决，然后说明下一步推进计划。',
    goal='Resolve PR 80 against current develop, preserve accepted M5 and CI obligations, validate the candidate and record staged next steps.',
    read_allowlist=read_scope, write_scope=write_scope,
    stop_conditions=['Current-head CI and renewed R2 review; no merge without specific authorization.',
                     'Preserve prior Attempts, Task definitions, source-CI implementation and primary develop.',
                     'No release ref/tag, topology activation, protection mutation or final release authorization.']))
dump(archive / 'ACTORS.yaml', dict(schema_version='0.1.0', task_id='M14-005', task_revision=1,
    attempt_id=archive.name, actors=[dict(actor_id='main-agent', actor_type='agent', role='rebase and verification',
    runtime_identity='Codex M14 rebase', accountable_owner='Chengyue-Lu')]))
write(archive / '.gitattributes', '** -text\ntool-events/* whitespace=cr-at-eol,-blank-at-eof\n')
events = []
def event(kind, payload):
    n = len(events) + 1
    events.append(dict(schema_version='0.1.0', event_id=f'EVT-{n:04}', task_id='M14-005', task_revision=1,
        attempt_id=archive.name, sequence=n, event_type=kind, actor_id='main-agent',
        occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), payload=payload, redactions=[]))

event('attempt-status', dict(from_status='planned', to_status='running', reason='Retain scoped rebase checkpoint.'))
gaps = []
for stream in ['events', 'tool-results', 'file-revisions', 'external-actions']:
    event('capture-gap', dict(affected_stream=stream, reason_category='capture-failure',
        reason='Material receipts retained at freeze; native events were not captured exhaustively or in realtime.'))
    gaps.append(dict(event_id=events[-1]['event_id'], affected_stream=stream))
names = ['scope.json', 'focused.log', 'repository.log', 'governance-plan.log', 'ci-plan.json',
         'range-diff.log', 'remote-summary.json', 'pr-before.json',
         *[value['path'] for value in remote['receipts'].values()]]
tool_refs = []
for name in names:
    target = archive / 'tool-events' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local / name, target)
    item = ref(target)
    tool_refs.append(item)
    event('tool-call', dict(operation_id='retain-' + name, tool_name='python', status='succeeded',
        arguments={'receipt': name, 'capture': 'Material result retained at freeze.'},
        result_entered_context=True, result_origin='transient', result_ref=item))

handoff = f'''# M14-005 current-base rebase and next steps

Owner: Chengyue-Lu. Date: 2026-09-21 (Asia/Shanghai).
User request: 跟进到目前最新进度，M14-005有冲突待解决，然后说明下一步推进计划。

PR 80 old head: 47f518a164c59bb123541bc8c0705f2106ee513e; old base: b041aeef8c32b74bc4399f90bf3fb49fbbb4fc22.
New base: {scope['baseline']}; rebased checkpoint: {scope['head']}.

All seven commits were replayed. STATUS conflicts retain the exact upstream Phase D row and the M14 READY
proposal. Coverage policy 2.3.0 includes every upstream 2.2.4 obligation plus the source-CI critical module,
test suite and independent positive/negative mapping. Removing only those additions reproduces the base
policy exactly. Removing only source_governance reproduces the base CI workflow exactly, including the
new diagnostic consumer-contract shadow job. Source-CI implementation/tests and witness maintenance
fixture repair match the prior reviewed head. All six existing M14 Attempts remain byte-identical.
Only M14-005 changes canonical Task status (BLOCKED to READY); definitions/dependencies remain unchanged.
Primary develop remains clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3.

Focused {match[1]} PASS covers source-CI, documentation/public links, coverage policy, CI planner,
consumer-contract shadow and witness fixtures. Repository validation: 186/0/0. Governance and semantic
preservation checks PASS. The plan requires full behavioral, impact+repository coverage and both package
smokes. Four protection layers and effective rules match at {remote['observed_at']}; no mutation.
This checkpoint is earlier than the evidence commit: final-head hosted CI and renewed review belong in PR 80.

M14-001 through M14-004, M0-007 and M1-009 are accepted. The existing named v0.1.0 preparation decision
authorizes this READY proposal; M14-005 is not DONE and the release topology remains dormant.

1. Obtain exact final-head/base hosted CI and renewed cross-owner R2 review, then specific PR 80 merge
   authorization. Old-head CI and technical review remain historical evidence.
2. After authorized squash integration, verify the actual protected develop push and source governance,
   then execute live attest from that exact integrated source. Download the producer receipt separately
   for audit; it is not an attestation input or authority token.
3. Once that chain is accepted, implement the release-only workflow/checks, exact policy include and
   atomic topology cutover preparation in a subsequent M14-005 slice.
4. With all gates ready, freeze exact source/current-main parent, prove deterministic projection and
   prospective merge-tree equality, dual-Python install and public-surface closure. Final release PR,
   tag and artifact/hash closure require a separate named approval.

Capture gaps remain explicit. No release branch, tag, topology switch, merge or remote policy change occurred.
'''
write(archive / 'outputs/REBASE_AND_NEXT_STEPS.md', handoff)
write(archive / 'WORKLOG.md', f'''# M14-005 rebase handoff

- Checkpoint {scope['head']} on {scope['baseline']}; owner Chengyue-Lu, R2.
- Conflicts resolved with upstream M5/CI requirements retained; prior source-CI code and frozen Attempts unchanged.
- Focused {match[1]} PASS; repository 186/0/0; governance/scope/protection readback PASS.
- Final-head hosted CI and renewed R2 review are retained in PR 80; merge authorization remains separate.
- See outputs/REBASE_AND_NEXT_STEPS.md. Capture gaps are indexed and truthful.
''')
write(archive / 'outputs/VERIFICATION.json', json.dumps(dict(checkpoint=scope['head'], baseline=scope['baseline'],
    focused_passed=int(match[1]), repository={'validated': 186, 'errors': 0, 'warnings': 0},
    governance='PASS', source_ci_bytes_unchanged=True, prior_attempts_unchanged=True,
    upstream_coverage_and_workflow_preserved=True, primary_develop_unchanged=True,
    final_head_ci='Pending; PR 80 owns final receipts', merge_authorized=False,
    real_source_push='Pending authorized integration'), ensure_ascii=False, indent=2) + '\n')
for name in ['verify_candidate.py', 'readback.py', 'freeze.py']:
    write(archive / 'outputs' / (name + '.md'), '# Evidence helper\n\n```python\n' +
          (local / name).read_text(encoding='utf-8') + '\n```\n')
event('attempt-status', dict(from_status='running', to_status='safe-paused', reason='Checkpoint frozen for final-head CI and R2 review.'))
write(archive / 'events.jsonl', ''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in events))
dump(archive / 'INDEX.yaml', dict(schema_version='0.1.0', trace_id='TRACE-M14-005-' + archive.name,
    task_id='M14-005', task_revision=1, attempt_id=archive.name, archive_root=archive.name,
    baseline=scope['baseline'], owner_actor_id='main-agent', owner='Chengyue-Lu', attempt_status='safe-paused',
    trace_status='frozen', completeness='gapped', task_ref=ref(archive / 'TASK.yaml'),
    actors_ref=ref(archive / 'ACTORS.yaml'), read_allowlist=read_scope, write_scope=write_scope,
    tool_allowlist=['git', 'gh', 'python', 'apply_patch'], messages=[],
    event_ledger={**ref(archive / 'events.jsonl'), 'event_count': len(events)}, tool_event_refs=tool_refs,
    handoff_refs=[ref(archive / 'WORKLOG.md')], decision_refs=[ref(archive / 'outputs/REBASE_AND_NEXT_STEPS.md')],
    output_refs=[ref(p) for p in sorted((archive / 'outputs').iterdir())],
    check_refs=[ref(archive / '.gitattributes')], capture_gaps=gaps))
print(json.dumps({'archive': str(archive.relative_to(root)), 'focused_passed': int(match[1])}))

```
