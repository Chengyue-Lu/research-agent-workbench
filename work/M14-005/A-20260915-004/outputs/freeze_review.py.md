# Evidence helper source

```python
"""Freeze review correction evidence once, preserving prior Attempts."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import yaml

ROOT = Path.cwd()
LOCAL = ROOT / '.rwb/m14-review-fix'
ARCHIVE = ROOT / 'work/M14-005/A-20260915-004'
ATTEMPT = ARCHIVE.name
assert not ARCHIVE.exists()
scope = json.loads((LOCAL / 'scope.json').read_text(encoding='utf-8'))
head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head == scope['head']
assert 'Ran 38 tests' in (LOCAL / 'focused.log').read_text(encoding='utf-8')
assert (LOCAL / 'focused.log').read_text(encoding='utf-8').rstrip().endswith('OK')
assert (LOCAL / 'repository.log').read_text(encoding='utf-8').strip() == 'validated=186 errors=0 warnings=0'

def write(path, text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')
def dump(path, value):
    write(path,yaml.safe_dump(value,allow_unicode=True,sort_keys=False))
def ref(path):
    return {'path':path.relative_to(ARCHIVE).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

read_scope = ['AGENTS.md','docs/README.md','docs/DEVELOPMENT.md','docs/TASKS.md','docs/STATUS.md',
    'docs/ROADMAP.md','docs/M_SERIES_IMPLEMENTATION_MAP.md','docs/decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md',
    'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/**','.github/**','tests/**','examples/**','registry/**',
    'pyproject.toml','work/M14-005/**','GitHub PR 80 comments and Issue 57; read-only protection and CI APIs']
write_scope = ['docs/TASKS.md','docs/STATUS.md','docs/ROADMAP.md','docs/M_SERIES_IMPLEMENTATION_MAP.md',
    'docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/**',f'work/M14-005/{ATTEMPT}/**',
    'GitHub feature/m14-005-source-ci and PR 80 body']
dump(ARCHIVE / 'TASK.yaml',dict(task_id='M14-005',revision=1,owner='Chengyue-Lu',risk='R2',
    agent_profile='bounded-review-correction',required_skills=[],delegation=False,baseline=scope['baseline'],
    user_request='根据comment解决问题。',
    goal='Resolve PR 80 P1 with named v0.1.0 preparation authority and fresh protection evidence; clarify P2 audit receipt semantics.',
    read_allowlist=read_scope,write_scope=write_scope,
    stop_conditions=['R2 review-ready PR 80 with exact-head validation; no self merge.',
        'Only M14-005 BLOCKED to READY; no Task definition or dependency changes.',
        'No actual cutover, release branch/tag, remote protection mutation or primary develop mutation.',
        'Final release PR merge and tag require a separate named approval.']))
dump(ARCHIVE / 'ACTORS.yaml',dict(schema_version='0.1.0',task_id='M14-005',task_revision=1,
    attempt_id=ATTEMPT,actors=[dict(actor_id='main-agent',actor_type='agent',role='review correction and verification',
    runtime_identity='Codex M14 review correction',accountable_owner='Chengyue-Lu')]))
write(ARCHIVE / '.gitattributes','** -text\ntool-events/* whitespace=cr-at-eol,-blank-at-eof\n')
events=[]
def event(kind,payload):
    n=len(events)+1
    events.append(dict(schema_version='0.1.0',event_id=f'EVT-{n:04}',task_id='M14-005',task_revision=1,
        attempt_id=ATTEMPT,sequence=n,event_type=kind,actor_id='main-agent',
        occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),payload=payload,redactions=[]))
event('attempt-status',dict(from_status='planned',to_status='running',reason='Retain named review correction and its checks.'))
gaps=[]
for stream in ['events','tool-results','file-revisions','external-actions']:
    event('capture-gap',dict(affected_stream=stream,reason_category='capture-failure',
        reason='Material receipts are retained at freeze; native streams were not captured exhaustively or as a realtime transcript.'))
    gaps.append(dict(event_id=events[-1]['event_id'],affected_stream=stream))
names=['pr80.json','pr80-comments.json','rulesets.json','remote-summary.json','rebase-before.json',
       'scope.json','focused.log','repository.log','governance-plan.log','ci-plan.json',
       *[f'ruleset-{n}.json' for n in (23305447,23192001,23305460,23192054)],
       'branch-develop.json','branch-main.json','effective-develop.json','effective-main.json']
tools=[]
for name in names:
    target=ARCHIVE/'tool-events'/name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(LOCAL/name,target)
    item=ref(target); tools.append(item)
    event('tool-call',dict(operation_id='retain-'+name,tool_name='python',status='succeeded',
        arguments={'receipt':name,'capture':'Material receipt retained at freeze.'},result_entered_context=True,
        result_origin='transient',result_ref=item))
write(ARCHIVE/'outputs/AUTHORITY.md','''# Named authority and review response

Source: current task user request “根据comment解决问题。”, followed by an explicit decision prompt and reply.
Accountable decision maker: 路诚钺 (Chengyue-Lu), 2026-09-15.

Prompt: 请确认 PR #80 的具名首发决定：由你（路诚钺）确定首个 curated release 为 v0.1.0，范围为届时冻结 develop 的完整源码、已发布 Schema、必需 Runtime Registry、MIT 许可、公开文档及离线 no-Skill Quickstart；接受当前 structural/bounded 成熟度、生产 Skill Projection 为空、无 live Provider 保证且无 M5 净收益实证。在远端保护回读通过后，授权 M14-005 转为 READY 并开展实现/cutover 准备；最终 release PR 合并及 tag 另行批准。

Reply: 确认上述 v0.1.0 范围与准备授权

This is preparation/Task activation authority, not authority to merge PR 80, create an actual release or
use a single-PR review exception. Fresh readback passed and all five canonical dependencies are DONE.
P2 is resolved by stating that the producer JSON is an audit attachment; attest trusts live run/job/check
evidence and does not download/hash/validate that attachment.

The rebase met a STATUS conflict between upstream M11 progress and M14 text. A local PowerShell conflict
resolution command used the automatic Matches variable accidentally; semantic inspection caught the
remaining markers and malformed heading before publication. The file was reconstructed from the prior
M14 snapshot plus the exact upstream Phase D row, then folded into the unpublished rebase commit.
Candidate checks verify the heading, absence of markers and exact preservation of the upstream row.
Native early outputs are incomplete; declared capture gaps remain. Frozen prior Attempts are unchanged.
''')
write(ARCHIVE/'outputs/VERIFICATION.json',json.dumps(dict(implementation_head=head,baseline=scope['baseline'],
    focused_passed=38,repository={'validated':186,'errors':0,'warnings':0},governance='PASS',
    task_transition='M14-005 BLOCKED -> READY',only_canonical_status_changed=True,
    source_ci_code_tests_workflow_unchanged=True,frozen_archives_unchanged=True,primary_clean_unchanged=True,
    protection_readback='PASS; four active layers and matching effective rules',
    final_head_hosted_ci='Pending archive commit and push; PR body owns final-head receipts.',
    real_protected_source_push='Pending R2 integration',release_authorization='Separate approval required'),
    ensure_ascii=False,indent=2)+'\n')
for name in ['readback.py','verify_candidate.py','freeze_review.py']:
    write(ARCHIVE/'outputs'/(name+'.md'),'# Evidence helper source\n\n```python\n'+(LOCAL/name).read_text(encoding='utf-8')+'\n```\n')
write(ARCHIVE/'WORKLOG.md',f'''# M14-005 PR 80 review correction

- Owner Chengyue-Lu; R2; baseline {scope['baseline']}; correction {head}.
- Named v0.1.0 preparation decision plus fresh protection readback supports BLOCKED → READY in this candidate.
- Only Task state changes; definition/dependencies and five DONE dependencies are verified.
- Producer JSON is an audit attachment, outside attest's live graph trust inputs; implementation unchanged.
- Rebase preserves upstream M11 state; focused 38 PASS, repository 186/0/0, governance and full CI plan PASS.
- Prior frozen Attempts and primary develop remain unchanged. Capture gaps are explicit.
- Next: final-head hosted CI and R2 review, then real protected source push acceptance after integration.
- This Attempt is frozen; later CI/review evidence belongs in PR 80. No merge, cutover or release performed.
''')
event('attempt-status',dict(from_status='running',to_status='safe-paused',reason='Freeze review correction for final-head hosted CI and R2 review.'))
write(ARCHIVE/'events.jsonl',''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in events))
dump(ARCHIVE/'INDEX.yaml',dict(schema_version='0.1.0',trace_id=f'TRACE-M14-005-{ATTEMPT}',task_id='M14-005',
    task_revision=1,attempt_id=ATTEMPT,archive_root=ATTEMPT,baseline=scope['baseline'],owner_actor_id='main-agent',
    owner='Chengyue-Lu',attempt_status='safe-paused',trace_status='frozen',completeness='gapped',
    task_ref=ref(ARCHIVE/'TASK.yaml'),actors_ref=ref(ARCHIVE/'ACTORS.yaml'),read_allowlist=read_scope,write_scope=write_scope,
    tool_allowlist=['git','gh','python','apply_patch'],messages=[],
    event_ledger={**ref(ARCHIVE/'events.jsonl'),'event_count':len(events)},tool_event_refs=tools,
    handoff_refs=[ref(ARCHIVE/'WORKLOG.md')],decision_refs=[ref(ARCHIVE/'outputs/AUTHORITY.md')],
    output_refs=[ref(p) for p in sorted((ARCHIVE/'outputs').iterdir())],
    check_refs=[ref(ARCHIVE/'.gitattributes')],capture_gaps=gaps))
print(json.dumps({'archive':ARCHIVE.relative_to(ROOT).as_posix(),'events':len(events),'head':head}))

```
