# Evidence helper

```python
"""Retain bounded rebase evidence once; never rewrite existing Attempts."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, re, shutil, subprocess, yaml

ROOT=Path.cwd()
LOCAL=ROOT/'.rwb/m14-rebase-20260916'
ARCHIVE=ROOT/'work/M14-005/A-20260916-001'
ATTEMPT=ARCHIVE.name
assert not ARCHIVE.exists()
scope=json.loads((LOCAL/'scope.json').read_text(encoding='utf-8'))
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert scope['head']==head
focused=(LOCAL/'focused.log').read_text(encoding='utf-8')
match=re.search(r'Ran (\d+) tests in [\d.]+s\n\nOK\n',focused)
assert match
assert (LOCAL/'repository.log').read_text(encoding='utf-8').strip()=='validated=186 errors=0 warnings=0'
remote=json.loads((LOCAL/'remote-summary.json').read_text(encoding='utf-8'))
assert remote['branches']['develop']['tip']==scope['baseline'] and not remote['mutations']

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')
def dump(path,value):
    write(path,yaml.safe_dump(value,allow_unicode=True,sort_keys=False))
def ref(path):
    return dict(path=path.relative_to(ARCHIVE).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
read_scope=['AGENTS.md','docs/README.md','docs/DEVELOPMENT.md','docs/TASKS.md','docs/STATUS.md','docs/ROADMAP.md',
    'docs/M_SERIES_IMPLEMENTATION_MAP.md','docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/**',
    '.github/**','tests/**','examples/**','registry/**','work/M14-005/**',
    'GitHub PR 80, Issue 57 and read-only CI/protection APIs']
write_scope=['docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/SOURCE_CI.md',f'work/M14-005/{ATTEMPT}/**',
    'M14 feature branch rebase; PR 80 body and final-head evidence']
dump(ARCHIVE/'TASK.yaml',dict(task_id='M14-005',revision=1,owner='Chengyue-Lu',risk='R2',
    agent_profile='bounded-rebase-verification',required_skills=[],delegation=False,baseline=scope['baseline'],
    user_request='rebase到最新develop，并确认下一步计划。',
    goal='Rebase PR 80 onto current develop, retain accepted M11 and CI planner changes, verify exact head, and confirm gated next steps.',
    read_allowlist=read_scope,write_scope=write_scope,
    stop_conditions=['PR 80 rebased and verified; no merge without current candidate approval and authorization.',
        'Preserve source-CI implementation, Task definition/dependencies, prior archives and primary develop.',
        'Do not start release-only implementation before real protected source-CI acceptance after PR integration.',
        'No release ref/tag, topology cutover, remote policy mutation or new release authorization.']))
dump(ARCHIVE/'ACTORS.yaml',dict(schema_version='0.1.0',task_id='M14-005',task_revision=1,attempt_id=ATTEMPT,
    actors=[dict(actor_id='main-agent',actor_type='agent',role='rebase and verification',runtime_identity='Codex M14 rebase',accountable_owner='Chengyue-Lu')]))
write(ARCHIVE/'.gitattributes','** -text\ntool-events/* whitespace=cr-at-eol,-blank-at-eof\n')
events=[]
def event(kind,payload):
    n=len(events)+1
    events.append(dict(schema_version='0.1.0',event_id=f'EVT-{n:04}',task_id='M14-005',task_revision=1,
        attempt_id=ATTEMPT,sequence=n,event_type=kind,actor_id='main-agent',
        occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),payload=payload,redactions=[]))
event('attempt-status',dict(from_status='planned',to_status='running',reason='Retain rebase and current-base verification.'))
gaps=[]
for stream in ['events','tool-results','file-revisions','external-actions']:
    event('capture-gap',dict(affected_stream=stream,reason_category='capture-failure',
        reason='Material results retained at freeze; native events were not captured exhaustively or in realtime.'))
    gaps.append(dict(event_id=events[-1]['event_id'],affected_stream=stream))
names=['pr-before.json','issue57.json','conflict.json','conflict-ready.json','scope.json','focused.log',
    'repository.log','governance-plan.log','ci-plan.json','remote-summary.json','conflict-latest.json','conflict-latest-ready.json','focused-first-base.log','scope-first-base.json','ci-plan-first-base.json','governance-plan-first-base.log',
    *[item['path'] for item in remote['receipts'].values()]]
tool_refs=[]
for name in names:
    target=ARCHIVE/'tool-events'/name; target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(LOCAL/name,target); item=ref(target); tool_refs.append(item)
    event('tool-call',dict(operation_id='retain-'+name,tool_name='python',status='succeeded',
        arguments={'receipt':name,'capture':'Material result retained at freeze.'},result_entered_context=True,
        result_origin='transient',result_ref=item))
write(ARCHIVE/'outputs/REBASE_AND_NEXT_STEPS.md',f'''# Rebase verification and gated next steps

Owner: Chengyue-Lu. User requested: “rebase到最新develop，并确认下一步计划。”
Old head: f1ee42f34b69ee1ec346e818b2170935e7c6d162; old base: 7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba.
New base: {scope['baseline']}; rebased checkpoint: {head}.

Four M14 commits were replayed twice after develop advanced during verification. STATUS conflicts represented adjacent Phase D/release rows;
resolution retained the upstream Gate B SATISFIED row and each incoming M14 row, ending at READY.
Canonical Task rows differ from new base only by M14-005 BLOCKED → READY; definitions/dependencies remain
unchanged. Source-CI code/tests/workflow and earlier M14 Attempts match the prior reviewed candidate.
Upstream PR 82 Task/Gate closeout, PR 83 planner/dependency/impact policy and PR 75 baseline implementation remain intact. The M6 and M14 independent coverage acceptance blocks are both retained; removing only the M14 additions reproduces the exact base coverage policy.

First-base focused 111 PASS included CI planner regression. Final-base focused {match[1]} PASS covers source-CI, docs/public surface and coverage policy; repository 186/0/0;
governance PASS; current-base plan requires full + impact/repository coverage + package.
Four active remote protection layers match effective rules at {remote['observed_at']}; no policy mutation.
Primary develop remains clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3.

The named v0.1.0 preparation decision remains the authority for READY. PR 80 owner review closed P1/P2
on the old exact head; it is not current-head cross-owner approval or merge authorization.

1. Verify the final evidence head on hosted CI; retain fresh R2 approval or an explicitly authorized
   exact-candidate maintainer exception before merging PR 80.
2. After authorized squash integration, observe the actual protected develop push and successful
   source_governance job; run live attest from the exact integrated source checkout. Producer JSON is audit only.
3. Only after that source-CI chain is accepted, start release-only checks/policy include and atomic cutover preparation.
4. Freeze source/parent only with complete gates; verify deterministic projection, prospective-tree equality,
   dual-Python installation and public surface. Final release PR/tag require separate named approval.

This frozen checkpoint does not claim hosted CI for its later evidence commit or a real protected source push.
PR 80 retains final-head CI receipts. Capture gaps remain explicit; no hidden reasoning or secrets retained.
''')
write(ARCHIVE/'outputs/VERIFICATION.json',json.dumps(dict(rebased_checkpoint=head,baseline=scope['baseline'],
    focused_passed=int(match[1]),first_base_planner_focused_passed=111,repository={'validated':186,'errors':0,'warnings':0},governance='PASS',
    ci_plan='full + impact/repository coverage + package',source_ci_bytes_unchanged=True,
    prior_attempts_unchanged=True,primary_develop_unchanged=True,final_head_ci='Pending; PR 80 owns receipts',
    merge_authorized=False,real_source_push='Pending authorized integration'),ensure_ascii=False,indent=2)+'\n')
for name in ['verify_candidate.py','readback.py','freeze_rebase.py']:
    write(ARCHIVE/'outputs'/(name+'.md'),'# Evidence helper\n\n```python\n'+(LOCAL/name).read_text(encoding='utf-8')+'\n```\n')
write(ARCHIVE/'WORKLOG.md',f'''# M14 rebase handoff

- Owner Chengyue-Lu; R2; rebase checkpoint {head} on {scope['baseline']}.
- Upstream Gate B and CI planner changes preserved; source-CI implementation and old Attempts unchanged.
- Focused {match[1]} PASS; repository 186/0/0; governance and full plan PASS; fresh protection readback PASS.
- Next: exact final-head CI and R2 approval, then authorized integration and real protected source-CI acceptance.
- Later release-only preparation and final release approval remain separate steps.
- Evidence and capture gaps are indexed; later hosted/review receipts belong in PR 80.
''')
event('attempt-status',dict(from_status='running',to_status='safe-paused',reason='Frozen checkpoint for final-head CI and R2 review.'))
write(ARCHIVE/'events.jsonl',''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in events))
dump(ARCHIVE/'INDEX.yaml',dict(schema_version='0.1.0',trace_id=f'TRACE-M14-005-{ATTEMPT}',task_id='M14-005',
    task_revision=1,attempt_id=ATTEMPT,archive_root=ATTEMPT,baseline=scope['baseline'],owner_actor_id='main-agent',
    owner='Chengyue-Lu',attempt_status='safe-paused',trace_status='frozen',completeness='gapped',
    task_ref=ref(ARCHIVE/'TASK.yaml'),actors_ref=ref(ARCHIVE/'ACTORS.yaml'),read_allowlist=read_scope,write_scope=write_scope,
    tool_allowlist=['git','gh','python','apply_patch'],messages=[],event_ledger={**ref(ARCHIVE/'events.jsonl'),'event_count':len(events)},
    tool_event_refs=tool_refs,handoff_refs=[ref(ARCHIVE/'WORKLOG.md')],
    decision_refs=[ref(ARCHIVE/'outputs/REBASE_AND_NEXT_STEPS.md')],
    output_refs=[ref(p) for p in sorted((ARCHIVE/'outputs').iterdir())],check_refs=[ref(ARCHIVE/'.gitattributes')],capture_gaps=gaps))
print(json.dumps({'archive':str(ARCHIVE.relative_to(ROOT)),'checkpoint':head,'focused_passed':int(match[1])}))

```
