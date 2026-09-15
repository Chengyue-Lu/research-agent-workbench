# Evidence helper source

```python
"""Freeze material implementation/check receipts; explicitly retain capture gaps."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import yaml

ROOT = Path.cwd()
LOCAL = ROOT / '.rwb/m14-source-ci'
ARCHIVE = ROOT / 'work/M14-005/A-20260915-003'
assert not ARCHIVE.exists(), 'Never rewrite an existing Attempt'
scope = json.loads((LOCAL / 'scope.json').read_text(encoding='utf-8'))
HEAD = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
assert scope['head'] == HEAD
focused = (LOCAL / 'focused.log').read_text(encoding='utf-8')
assert re.search(r'Ran 247 tests in [0-9.]+s\n\nOK\n', focused)
source_checks = (LOCAL / 'source-focused.log').read_text(encoding='utf-8')
assert re.search(r'Ran 15 tests in [0-9.]+s\n\nOK\n', source_checks)
coverage = json.loads((LOCAL / 'source-coverage.json').read_text(encoding='utf-8'))
entry = next(value for path, value in coverage['files'].items() if path.replace('\\', '/') == '.github/scripts/release_source_ci.py')
assert entry['missing_lines'] == [] and entry['missing_branches'] == []
for rule_id in [23305447, 23305460]:
    rule = json.loads((LOCAL / f'ruleset-{rule_id}.json').read_text(encoding='utf-8-sig'))
    assert rule['enforcement'] == 'active' and rule['bypass_actors'] == []
for rule_id in [23192001, 23192054]:
    rule = json.loads((LOCAL / f'ruleset-{rule_id}.json').read_text(encoding='utf-8-sig'))
    assert rule['enforcement'] == 'active' and rule['bypass_actors'] == [
        {'actor_id': 140945476, 'actor_type': 'User', 'bypass_mode': 'pull_request'}]

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')

def dump(path, value):
    write(path, yaml.safe_dump(value, allow_unicode=True, sort_keys=False))

def ref(path):
    return {'path': path.relative_to(ARCHIVE).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

read_scope = ['AGENTS.md', 'docs/README.md', 'docs/DEVELOPMENT.md', 'docs/DEVELOP_TO_MAIN_RELEASE.md',
              'docs/decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md', *scope['changed_paths'],
              '.github/**', 'tests/**', 'schemas/v0.1.0/release-manifest.schema.json',
              'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/**', 'examples/**', 'registry/**',
              'GitHub Issue 57, PR 78/79 and read-only CI/ruleset APIs']
write_scope = [*scope['changed_paths'], 'work/M14-005/A-20260915-003/**',
               'GitHub feature/m14-005-source-ci, implementation PR body and review request']
dump(ARCHIVE / 'TASK.yaml', dict(task_id='M14-005', revision=1, owner='Chengyue-Lu', risk='R2',
     agent_profile='bounded-source-ci-preparation', required_skills=[], delegation=False, baseline=scope['baseline'],
     user_request='继续推进M14-005', goal='Implement merged-source governance and live source-CI observation while keeping release authority dormant.',
     read_allowlist=read_scope, write_scope=write_scope,
     stop_conditions=['R2 implementation PR to develop with exact-head CI and cross-owner review request.',
                      'Do not merge this new implementation PR without acceptance and authorization.',
                      'M14-005 stays BLOCKED pending first-release decision and readiness closure.',
                      'No release refs, tag, real release, topology change or primary develop mutation.']))
dump(ARCHIVE / 'ACTORS.yaml', dict(schema_version='0.1.0', task_id='M14-005', task_revision=1,
     attempt_id='A-20260915-003', actors=[dict(actor_id='main-agent', actor_type='agent',
     role='source CI implementation and verification', runtime_identity='Codex M14 source CI', accountable_owner='Chengyue-Lu')]))
write(ARCHIVE / '.gitattributes', '** -text\ntool-events/* whitespace=cr-at-eol,-blank-at-eof\n')
events = []
def event(kind, payload):
    sequence = len(events) + 1
    events.append(dict(schema_version='0.1.0', event_id=f'EVT-{sequence:04}', task_id='M14-005', task_revision=1,
         attempt_id='A-20260915-003', sequence=sequence, event_type=kind, actor_id='main-agent',
         occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'), payload=payload, redactions=[]))

event('attempt-status', dict(from_status='planned', to_status='running', reason='Retain the source-CI implementation and material validation receipts.'))
gaps = []
for stream in ['events', 'tool-results', 'file-revisions', 'external-actions']:
    event('capture-gap', dict(affected_stream=stream, reason_category='capture-failure',
        reason='Native streams were not exhaustively captured. Material retained receipts are indexed at freeze, not represented as a complete realtime transcript.'))
    gaps.append(dict(event_id=events[-1]['event_id'], affected_stream=stream))

(LOCAL / 'source-coverage-summary.json').write_text(json.dumps(dict(
    implementation_head=HEAD, path='.github/scripts/release_source_ci.py', coverage=entry,
    native_report_sha256=hashlib.sha256((LOCAL / 'source-coverage.json').read_bytes()).hexdigest(),
    boundary='Focused source observer coverage only; not repository-global coverage.'), indent=2) + '\n', encoding='utf-8', newline='\n')
names = ['whitespace-initial.log', 'rejected-archive-crlf.json', 'trace-initial.log', 'rejected-archive.json', 'scope.json', 'focused.log', 'source-focused.log', 'source-coverage-summary.json', 'repository.log',
         'governance-plan.log', 'ci-plan.json', 'live-negative.json', 'issue57.json', 'pr78.json', 'pr79.json',
         *[f'ruleset-{i}.json' for i in [23305447, 23192001, 23305460, 23192054]]]
tool_refs = []
for name in names:
    target = ARCHIVE / 'tool-events' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(LOCAL / name, target)
    item = ref(target); tool_refs.append(item)
    event('tool-call', dict(operation_id='retain-' + name, tool_name='python', status='succeeded',
        arguments={'receipt': name, 'capture': 'Material result retained at archive freeze.'},
        result_entered_context=True, result_origin='transient', result_ref=item))

write(ARCHIVE / 'outputs/AUTHORITY.md', '''# Authority and capture boundary

Chengyue-Lu instructed: “继续推进M14-005”. Prior PR #78 accepted MIT/readiness preparation;
PR #79 accepted the independent review-exception mechanism. This slice implements source-CI preparation
under ADR-0021. It does not create a named first-release decision or authorize merge of its own new PR.

An initial fixture assertion compared six expected gh arguments with a seven-element slice; it was corrected.
A live API probe showed the repository endpoint rejects a trailing slash; the transport now emits the canonical
repository path and has a regression check. Final focused/native observer checks pass. Early transient outputs
were not all retained; the capture-gap declarations remain explicit.
''')
write(ARCHIVE / 'outputs/VERIFICATION.json', json.dumps(dict(implementation_head=HEAD,
      baseline=scope['baseline'], focused_passed=247, source_fixture_checks_passed=15,
      source_observer_coverage={'lines': '150/150', 'branches': '18/18'}, repository={'validated':186,'errors':0,'warnings':0},
      governance='PASS', ci_plan={'behavioral':'full','coverage':'impact+repository','package':True},
      live_negative='Green develop CI 34939526577 rejected: missing governance',
      live_positive_protected_push='Pending R2 integration; current PR checks cannot substitute this evidence.',
      canonical_tasks_unchanged=True, m14_005_state='BLOCKED', primary_clean_unchanged=True,
      topology_changed=False, release_refs_created=False, remote_protection_mutated=False,
      final_head_hosted_ci='Pending evidence commit/push; PR body will retain run and artifact bindings.'), indent=2) + '\n')
for name in ['live_negative.py', 'prepare_checks.py', 'freeze.py']:
    write(ARCHIVE / 'outputs' / (name + '.md'), '# Evidence helper source\n\n```python\n' +
          (LOCAL / name).read_text(encoding='utf-8') + '\n```\n')
write(ARCHIVE / 'WORKLOG.md', f'''# M14-005 source-CI preparation

- Owner Chengyue-Lu; R2; user requested continued M14-005 implementation.
- Baseline `{scope['baseline']}`; implementation `{HEAD}`.
- Producer rechecks the exact merged PR and actual squash delta; consumer binds authentic GitHub run/attempt/job/check identities and catches rerun races. The inactive producer never shares the PR governance check name.
- 247 joint focused tests PASS; 15 source tests PASS; observer coverage 150/150 lines and 18/18 branches; repository 186/0/0; governance/plan PASS.
- Historical green develop CI is a live negative control: absence of governance fails closed. Real protected-push positive evidence follows acceptance of this implementation.
- Existing source/product/Schema/Registry/Skill/release-policy/topology and frozen Attempts are unchanged. Canonical Task rows remain unchanged; M14-005 is BLOCKED. Primary develop stays clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3.
- Next: final-head hosted CI and R2 review; then validate the integrated protected push before release-only checks/policy include. Named first-release decision and remaining readiness precede cutover/freeze/release.
- Capture gaps are explicit; no hidden reasoning or secrets retained. The PR body owns subsequent CI/review/merge receipts; this Attempt remains frozen.
''')
event('attempt-status', dict(from_status='running', to_status='safe-paused', reason='Implementation and local evidence frozen for final-head hosted CI and R2 review.'))
write(ARCHIVE / 'events.jsonl', ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in events))
dump(ARCHIVE / 'INDEX.yaml', dict(schema_version='0.1.0', trace_id='TRACE-M14-005-A-20260915-003',
    task_id='M14-005', task_revision=1, attempt_id='A-20260915-003', archive_root='A-20260915-003',
    baseline=scope['baseline'], owner_actor_id='main-agent', owner='Chengyue-Lu', attempt_status='safe-paused',
    trace_status='frozen', completeness='gapped', task_ref=ref(ARCHIVE/'TASK.yaml'), actors_ref=ref(ARCHIVE/'ACTORS.yaml'),
    read_allowlist=read_scope, write_scope=write_scope, tool_allowlist=['git','gh','python','apply_patch'], messages=[],
    event_ledger={**ref(ARCHIVE/'events.jsonl'),'event_count':len(events)}, tool_event_refs=tool_refs,
    handoff_refs=[ref(ARCHIVE/'WORKLOG.md')], decision_refs=[ref(ARCHIVE/'outputs/AUTHORITY.md')],
    output_refs=[ref(path) for path in sorted((ARCHIVE/'outputs').iterdir())],
    check_refs=[ref(ARCHIVE/'.gitattributes')], capture_gaps=gaps))
print(json.dumps({'archive': ARCHIVE.relative_to(ROOT).as_posix(), 'events':len(events), 'implementation_head':HEAD}))

```
