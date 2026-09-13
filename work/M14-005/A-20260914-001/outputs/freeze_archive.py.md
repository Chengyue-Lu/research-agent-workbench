# Evidence helper source

```python
"""Retain material readiness evidence; native streams are explicitly incomplete."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import subprocess
import tempfile
import yaml

ROOT=Path.cwd()
LOCAL=ROOT/'.rwb/m14-005'
EVIDENCE=LOCAL/'evidence'
ARCHIVE=ROOT/'work/M14-005/A-20260914-001'
assert not (ARCHIVE/'INDEX.yaml').exists(), 'Frozen archives cannot be rewritten'
BASE='f7a9715ed35787d3326283c22f834b1514c5c88c'
HEAD=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')

def ref(path):
    return {'path':path.relative_to(ARCHIVE).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def dump(path,data):
    write(path,yaml.safe_dump(data,sort_keys=False,allow_unicode=True))

def event(kind,payload):
    n=len(events)+1
    events.append(dict(schema_version='0.1.0',event_id=f'EVT-{n:04}',task_id='M14-005',task_revision=1,
                       attempt_id='A-20260914-001',sequence=n,event_type=kind,actor_id='main-agent',
                       occurred_at=datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
                       payload=payload,redactions=[]))

read_scope=['AGENTS.md','docs/**','README.md','LICENSE','MANIFEST.in','pyproject.toml',
            '.github/**','tests/**','src/research_workbench/resources.py','build_backend.py',
            'runtime-resources.json','registry/skills/**','schemas/**','work/M14-004/**',
            'work/M14-005/A-20260914-001/**','GitHub Issue 57 and PR 77/current branch/ruleset/CI APIs',
            'GitHub rules REST documentation','MIT and setuptools license metadata documentation']
write_scope=['LICENSE','MANIFEST.in','pyproject.toml','README.md','registry/skills/accepted.json',
             'registry/skills/candidates.json','registry/skills/sources.json','.github/release-surface.yml',
             '.github/scripts/portable_package_smoke.py','tests/public_surface_helpers.py',
             'tests/test_public_surface.py','tests/test_portable_build.py','tests/test_ci_plan.py','docs/TASKS.md',
             'docs/STATUS.md','docs/ROADMAP.md','docs/M_SERIES_IMPLEMENTATION_MAP.md',
             'docs/SUPPORTED_FEATURES.md','docs/workstreams/chengyue-lu/M14-CURATED-RELEASE/**',
             'work/M14-005/A-20260914-001/**','GitHub exact main/develop protection rulesets']
task=dict(task_id='M14-005',revision=1,related_task_ids=['M0-007'],owner='Chengyue-Lu',risk='R2',
          agent_profile='bounded-release-readiness',required_skills=[],delegation=False,baseline=BASE,
          user_request='M14-004 merge -> license/protection/evidence readiness -> all external gates -> READY -> first release',
          goal='Prepare MIT license closure, enforce accepted remote protections, and retain synthetic readiness evidence.',
          read_allowlist=read_scope,write_scope=write_scope,
          stop_conditions=['Publish readiness PR for cross-owner R2 review.',
                           'M14-005 remains BLOCKED pending accepted readiness and named first-release decision.',
                           'Primary local develop, dormant topology, real release refs/tags and Skill admission unchanged.'])
dump(ARCHIVE/'TASK.yaml',task)
dump(ARCHIVE/'ACTORS.yaml',dict(schema_version='0.1.0',task_id='M14-005',task_revision=1,
     attempt_id='A-20260914-001',actors=[dict(actor_id='main-agent',actor_type='agent',
     role='readiness implementation and verification',runtime_identity='Codex M14 readiness',accountable_owner='Chengyue-Lu')]))
write(ARCHIVE/'.gitattributes','** -text\n')
events=[]
event('attempt-status',dict(from_status='planned',to_status='running',reason='Retain material license/protection/readiness evidence; preceding native activity is explicitly gapped.'))
gaps=[]
for stream in ['events','tool-results','file-revisions','external-actions']:
    event('capture-gap',dict(affected_stream=stream,reason_category='capture-failure',
         reason='Native streams were not exhaustively captured. These records retain material evidence, not a complete realtime transcript.'))
    gaps.append(dict(event_id=events[-1]['event_id'],affected_stream=stream))
tool_refs=[]
# Test case receipts and measured coverage are retained. Ignore the redundant noisy
# setup/build logs; summaries reference them by hash without claiming their contents.
names=sorted(p.name for p in EVIDENCE.glob('*.json'))+['governance.log','repository.log','focused-precommit.log',
      'ci-fixture-before-fix.log','focused-after-fix.log','full-coverage.log']
for name in names:
    source=EVIDENCE/name
    text=source.read_text(encoding='utf-8-sig')
    # The failing unittest traceback contains interpreter and temporary fixture paths.
    for prefix, label in [(str(ROOT),'<readiness-worktree>'),
                          (str(ROOT.parent/'research-agent-workbench'),'<primary-checkout>'),
                          (tempfile.gettempdir(),'<temporary-root>')]:
        variants=[prefix,prefix.replace('\\','/'),prefix.replace('\\','\\\\'),prefix.replace('\\','\\\\\\\\')]
        for value in sorted(variants,key=len,reverse=True):
            text=text.replace(value,label)
    target=ARCHIVE/'tool-events'/name
    write(target,text)
    item=ref(target); tool_refs.append(item)
    event('tool-call',dict(operation_id='retain-'+name,tool_name='gh' if any(x in name for x in ['ruleset','response','readback','source-run','source-jobs','source-checks','before-','after-','pr77','app-identity']) else 'python',
          status='succeeded',arguments=dict(evidence=name,capture='retained UTF-8/LF material result; workspace paths redacted'),
          result_entered_context=True,result_origin='transient',result_ref=item))
package=json.loads((EVIDENCE/'package.json').read_bytes())
projection=json.loads((EVIDENCE/'projection.json').read_bytes())
assert len(package['installs'])==8 and package['runtime_resources_identical']
assert projection['merge_eligible'] is False
changed=subprocess.check_output(['git','diff','--name-only',projection['implementation_head'],HEAD],text=True).splitlines()
assert changed==['tests/test_ci_plan.py'],changed
summary=dict(implementation_head=HEAD,baseline=BASE,focused_passed=32,
             local_full_status='interrupted after reproduced CI planner fixture failure on e8d7e33',
             local_full_completed=False,local_full_failure_fixed=True,
             full_and_coverage_acceptance='Require fresh exact PR head GitHub CI; not yet observed at archive freeze',
             tested_package_source=projection['implementation_head'],package_inputs_unchanged_by_fixture_fix=True,
             repository={'validated':186,'errors':0,'warnings':0},
             package_installs=8,projection_file_count=projection['file_count'],license='MIT',
             remote_rulesets={'develop':23192001,'main':23192054},m14_005_state='BLOCKED',
             source_ci_gap='develop push CI lacks governance job required by dormant source policy',
             release_source_frozen=False,release_refs_created=False,release_authorized=False,
             omitted_redundant_logs={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in EVIDENCE.glob('*.log') if p.name not in names})
write(ARCHIVE/'outputs/VERIFICATION.json',json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
for name in ['verify_projection.py','prepare_checks.py','prepare_protection.py','apply_protection.py','freeze_archive.py']:
    write(ARCHIVE/'outputs'/f'{name}.md','# Evidence helper source\n\n```python\n'+(LOCAL/name).read_text(encoding='utf-8')+'\n```\n')
write(ARCHIVE/'WORKLOG.md',f'''# M14 readiness compact handoff

- Owner: Chengyue-Lu; Task M14-005 readiness preparation and M0-007 closure; risk R2.
- Baseline: `{BASE}`; tested implementation: `{HEAD}`.
- Human chose MIT and confirmed all relevant contributor rights. Three original accepted Skill license entries and one original candidate source are MIT; original bytes, hashes and lifecycle remain pinned.
- GitHub main/develop active rulesets were created and read back; source branch tips unchanged. The first strict readback comparison stopped on server-added default fields; inspection preserved those defaults and resumed using the existing develop ruleset ID, without duplicate creation.
- 32 focused checks, repository validation, synthetic repeat projection and eight dual-Python install profiles passed. The local full/coverage run on e8d7e33 found a stale setuptools>=69 fixture replacement; the failure was independently reproduced and the known-failed run was stopped. The fixture now derives its dependency mutation from current metadata and its focused check passes. Full/coverage acceptance requires the fresh exact PR head hosted CI; no local full PASS is claimed.
- Current develop push CI lacks governance in the source required-check set. Protected source attestation and release-only workflow remain M14-005 implementation work after readiness acceptance and named first-release decision.
- M14-005 remains BLOCKED. Next: exact PR head CI plus cross-owner R2 review; then refresh gates and obtain named release scope/version decision.
- Primary local develop stayed clean at 11c3b57dfbf8af0dc2587fc421d097e2544941c3. No release branch, tag, topology activation or Skill publication occurred.
- Capture is gapped: API receipts and material check results are preserved with hashes; exhaustive native streams and preceding compacted activity were not captured. No hidden reasoning or secrets retained.
''')
event('attempt-status',dict(from_status='running',to_status='safe-paused',reason='Readiness implementation and local validation retained for PR and cross-owner review; release authority remains gated.'))
write(ARCHIVE/'events.jsonl',''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events))
index=dict(schema_version='0.1.0',trace_id='TRACE-M14-005-A-20260914-001',task_id='M14-005',task_revision=1,
           attempt_id='A-20260914-001',archive_root='A-20260914-001',baseline=BASE,owner_actor_id='main-agent',owner='Chengyue-Lu',
           attempt_status='safe-paused',trace_status='frozen',completeness='gapped',task_ref=ref(ARCHIVE/'TASK.yaml'),
           actors_ref=ref(ARCHIVE/'ACTORS.yaml'),read_allowlist=read_scope,write_scope=write_scope,
           tool_allowlist=['git','gh','python','apply_patch'],messages=[],
           event_ledger={**ref(ARCHIVE/'events.jsonl'),'event_count':len(events)},tool_event_refs=tool_refs,
           handoff_refs=[ref(ARCHIVE/'WORKLOG.md')],decision_refs=[],
           output_refs=[ref(p) for p in sorted((ARCHIVE/'outputs').iterdir())],
           check_refs=[ref(ARCHIVE/'.gitattributes')],capture_gaps=gaps)
dump(ARCHIVE/'INDEX.yaml',index)
print(json.dumps({'archive':ARCHIVE.relative_to(ROOT).as_posix(),'events':len(events),'evidence_files':len(names)},ensure_ascii=False))

```
