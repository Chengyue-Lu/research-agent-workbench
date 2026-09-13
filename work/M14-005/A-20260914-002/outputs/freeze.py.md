# Evidence helper source

```python
"""Freeze the separate PR 78 review correction Attempt."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import subprocess
import yaml

ROOT = Path.cwd()
LOCAL = ROOT / '.rwb/m14-005/review-fix'
ARCHIVE = ROOT / 'work/M14-005/A-20260914-002'
assert not ARCHIVE.exists(), 'Existing Attempts are immutable'
HEAD = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
BASE = subprocess.check_output(['git', 'rev-parse', 'origin/develop'], text=True).strip()
SCOPE = json.loads((LOCAL / 'scope.json').read_text(encoding='utf-8'))
for name, blob in SCOPE['document_blob_ids'].items():
    assert subprocess.check_output(['git', 'rev-parse', HEAD + ':' + name], text=True).strip() == blob

def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8', newline='\n')

def dump(path, value):
    write(path, yaml.safe_dump(value, sort_keys=False, allow_unicode=True))

def ref(path):
    return {'path': path.relative_to(ARCHIVE).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

events = []
def event(kind, payload):
    n = len(events) + 1
    events.append(dict(schema_version='0.1.0', event_id=f'EVT-{n:04}', task_id='M14-005', task_revision=1,
                       attempt_id='A-20260914-002', sequence=n, event_type=kind, actor_id='main-agent',
                       occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                       payload=payload, redactions=[]))

read_scope = ['AGENTS.md', 'docs/README.md', 'docs/DEVELOPMENT.md', *SCOPE['changed_files'],
              'tests/test_documentation.py', 'tests/test_public_surface.py', '.github/**',
              'examples/**', 'registry/**', 'schemas/**', 'work/M14-005/A-20260914-001/**',
              'work/M14-005/A-20260914-002/**', 'GitHub PR 78 review, head/base and check APIs']
write_scope = [*SCOPE['changed_files'], 'work/M14-005/A-20260914-002/**',
               'GitHub PR 78 feature branch, body and cross-owner review request']
dump(ARCHIVE / 'TASK.yaml', dict(task_id='M14-005', revision=1, related_task_ids=['M0-007'],
     owner='Chengyue-Lu', risk='R2', agent_profile='bounded-release-readiness-review-correction',
     required_skills=[], delegation=False, baseline=BASE,
     user_request='根据审核问题进行修复。',
     review_ref='https://github.com/Chengyue-Lu/research-agent-workbench/pull/78#issuecomment-5655298378',
     goal='Correct stale risk/status summaries and separate external readiness from remaining M14-005 implementation.',
     read_allowlist=read_scope, write_scope=write_scope,
     stop_conditions=['Update the same PR 78 and request fresh exact-head cross-owner R2 review.',
                      'M14-005 remains BLOCKED; canonical Task definitions, dependencies and acceptance unchanged.',
                      'Keep primary local develop clean and unchanged; retain dormant topology and existing frozen archives.']))
dump(ARCHIVE / 'ACTORS.yaml', dict(schema_version='0.1.0', task_id='M14-005', task_revision=1,
     attempt_id='A-20260914-002', actors=[dict(actor_id='main-agent', actor_type='agent',
     role='readiness documentation review correction and verification', runtime_identity='Codex M14 readiness',
     accountable_owner='Chengyue-Lu')]))
write(ARCHIVE / '.gitattributes', '** -text\n')
event('attempt-status', dict(from_status='planned', to_status='running', reason='Retain the two owner P2 corrections and their scoped verification.'))
gaps = []
for stream in ['events', 'tool-results', 'file-revisions', 'external-actions']:
    event('capture-gap', dict(affected_stream=stream, reason_category='capture-failure',
         reason='Native streams were not exhaustively captured. Material review and check receipts are retained at archive freeze; this is not a complete realtime transcript.'))
    gaps.append(dict(event_id=events[-1]['event_id'], affected_stream=stream))

tool_refs = []
for name in ['review.json', 'pr-before.json', 'scope.json', 'documentation.json', 'documentation.log',
             'repository.json', 'repository.log', 'whitespace.json', 'whitespace.log', 'governance.log']:
    target = ARCHIVE / 'tool-events' / name
    write(target, (LOCAL / name).read_text(encoding='utf-8-sig'))
    item = ref(target)
    tool_refs.append(item)
    event('tool-call', dict(operation_id='retain-' + name,
          tool_name='gh' if name in ['review.json', 'pr-before.json'] else 'python', status='succeeded',
          arguments=dict(evidence=name, capture='Retained material result; command/time and target are in the paired receipt where available.'),
          result_entered_context=True, result_origin='transient', result_ref=item))

write(ARCHIVE / 'outputs/VERIFICATION.json', json.dumps(dict(
      reviewed_head=SCOPE['reviewed_head'], correction_head=HEAD, baseline=BASE,
      correction_commit_blobs_match_tested_working_tree=True, documentation_checks_passed=23,
      repository=dict(validated=186, errors=0, warnings=0), local_governance='PASS',
      governance_target=HEAD, canonical_task_rows_identical=True, m14_005_state='BLOCKED',
      product_policy_and_skill_files_unchanged=True, prior_frozen_archive_unchanged=True,
      primary_branch=SCOPE['primary_branch'], primary_head=SCOPE['primary_head'], primary_clean=True,
      findings_addressed=['Stale risk ledger and accepted-status navigation',
                          'External readiness separated from M14-005 implementation and first-release closure'],
      final_head_ci='Pending after archive commit and push; historical c328bbf CI is not new-head evidence.',
      fresh_cross_owner_review='Pending let778750-cpu exact-head review.',
      release_source_frozen=False, release_refs_created=False, release_authorized=False,
      remote_protection_mutated=False), ensure_ascii=False, indent=2) + '\n')
for name in ['checks.py', 'freeze.py']:
    write(ARCHIVE / 'outputs' / (name + '.md'), '# Evidence helper source\n\n```python\n' +
          (LOCAL / name).read_text(encoding='utf-8') + '\n```\n')
write(ARCHIVE / 'WORKLOG.md', f'''# M14 readiness review correction

- Owner: Chengyue-Lu; Task M14-005 readiness preparation with M0-007; risk R2.
- Review: PR 78 owner comment 5655298378 on `{SCOPE['reviewed_head']}`; substantive PASS with two nonblocking P2 findings. Fresh cross-owner review remains pending.
- Correction commit: `{HEAD}`; integration base: `{BASE}`.
- P2 risk/status correction: M14-002/004 accepted controls are current; MIT closes the license blocker while the production Projection index remains empty with no Skill-bearing release selection/admission.
- P2 sequencing correction: external readiness requires PR 78 R2 acceptance, fresh ruleset readback and a named Human release decision. Subsequent M14-005 implementation still must close protected source-CI attestation, release-only workflow/checks, atomic topology cutover, exact develop source/current main parent freeze, deterministic projection/prospective-tree equality, first release R2 review and tag/artifact/hash closure.
- 23 documentation/public-surface checks PASS; repository validation 186/0/0; whitespace and governance PASS. Recorded tested document Git blobs match the correction commit.
- Canonical Task rows are identical to the reviewed head. Product, package, policy, Skill identities and the prior frozen archive are unchanged. M14-005 remains BLOCKED.
- Primary local develop remains clean at `{SCOPE['primary_head']}`. No remote protection changes, real source freeze, release refs, topology activation or release occurred.
- Final-head hosted CI and fresh cross-owner review follow the archive commit. Historical hosted CI remains bound to its recorded older head.
- Native capture is explicitly gapped; material results are preserved. No hidden reasoning or secrets retained.
''')
event('attempt-status', dict(from_status='running', to_status='safe-paused', reason='Corrections and local evidence frozen for final-head CI and cross-owner R2 review.'))
write(ARCHIVE / 'events.jsonl', ''.join(json.dumps(item, ensure_ascii=False) + '\n' for item in events))
dump(ARCHIVE / 'INDEX.yaml', dict(schema_version='0.1.0', trace_id='TRACE-M14-005-A-20260914-002',
     task_id='M14-005', task_revision=1, attempt_id='A-20260914-002', archive_root='A-20260914-002',
     baseline=BASE, owner_actor_id='main-agent', owner='Chengyue-Lu', attempt_status='safe-paused',
     trace_status='frozen', completeness='gapped', task_ref=ref(ARCHIVE / 'TASK.yaml'),
     actors_ref=ref(ARCHIVE / 'ACTORS.yaml'), read_allowlist=read_scope, write_scope=write_scope,
     tool_allowlist=['git', 'gh', 'python', 'apply_patch'], messages=[],
     event_ledger={**ref(ARCHIVE / 'events.jsonl'), 'event_count':len(events)}, tool_event_refs=tool_refs,
     handoff_refs=[ref(ARCHIVE / 'WORKLOG.md')], decision_refs=[],
     output_refs=[ref(path) for path in sorted((ARCHIVE / 'outputs').iterdir())],
     check_refs=[ref(ARCHIVE / '.gitattributes')], capture_gaps=gaps))
print(json.dumps({'archive': ARCHIVE.relative_to(ROOT).as_posix(), 'events': len(events), 'correction_head': HEAD}))

```
