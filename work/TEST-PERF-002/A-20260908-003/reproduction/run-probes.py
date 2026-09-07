import ast,json,os,subprocess,sys,time
from pathlib import Path
repo=Path(sys.argv[1]).resolve()
assert repo.name == 'rwb-precision-probe'
base='cbda9c2c78da3cc647f5e73da160053fca2d6a4e'
output=Path(__file__).resolve().parent/'real-probes';output.mkdir(exist_ok=True)
python=repo/'.rwb/probe-venv311/Scripts/python.exe'
sys.path.insert(0,str(repo/'.github/scripts'))
import plan_ci as planner

def git(*args):
    return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE).decode().strip()
def commit(paths,label):
    git('add',*paths);git('commit','-qm',label);return git('rev-parse','HEAD')
def plan(head):
    return planner.make_plan(repo,base=base,head=head,target=head,repository='Chengyue-Lu/research-agent-workbench',
        body='- **Risk tier**: R2\n- **Shared contract**: no\n- **Authority impact**: no')
def run(label,args,directory):
    env={**os.environ,'PYTHONPATH':str(repo/'src')+os.pathsep+str(repo/'tests'),
         'PYTHONDONTWRITEBYTECODE':'1','PYTHONPYCACHEPREFIX':str(repo/'.rwb/pycache'/directory.name/label)}
    env.pop('GITHUB_EVENT_PATH',None);env.pop('GITHUB_EVENT_NAME',None)
    env['COVERAGE_FILE']=str(directory/'coverage-data')
    start=time.perf_counter()
    with (directory/(label+'.log')).open('wb') as stream:
        result=subprocess.run([str(python),*args],cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT)
    return {'exit_code':result.returncode,'wall_seconds':round(time.perf_counter()-start,3)}

cases=[('claim','src/research_workbench/artifacts/claim_trace.py',
        'return value.lower().removeprefix("sha256:")','return value.lower().removeprefix("sha256:")[0:]',
        'src/research_workbench/cli.py','_claim_trace'),
       ('projection','src/research_workbench/capability/release_projection.py',
        'return normalized','return normalized[0:]',
        'src/research_workbench/validation/skill_release_projection_registry.py','validate_skill_release_projections'),
       ('release','.github/scripts/release_surface.py',
        'return hashlib.sha256(data).hexdigest()','return hashlib.sha256(data).hexdigest()[0:]',
        '.github/scripts/release_surface.py','export')]
summary={'authority_status':'isolated proposed accepted-contract baseline; not formal develop acceptance',
         'base':base,'python':'3.11.16','cases':[]}
for name,path,before,after,downstream,function in cases:
    directory=output/name;directory.mkdir(exist_ok=True)
    assert not git('status','--porcelain','--untracked-files=no')
    git('reset','--hard',base)
    original=(repo/path).read_bytes();assert original.count(before.encode()) == 1
    (repo/path).write_bytes(original.replace(before.encode(),after.encode()))
    head=commit([path],'test(ci): '+name+' equivalent local function probe')
    p=plan(head);plan_path=directory/'plan.json';plan_path.write_bytes(planner.canonical(p))
    row={'name':name,'path':path,'head':head,'behavioral_scope':p['behavioral_scope'],
         'coverage_scope':p['coverage_scope'],'tests':p['tests'],'coverage_tests':p['coverage_tests'],
         'smokes':[p['package_smoke'],p['repository_smoke']],'runs':{}}
    summary['cases'].append(row)
    assert p['behavioral_scope']=='focused' and p['coverage_obligations']==['impact'],p['reasons']
    assert len(p['tests'])<=4,p['tests']
    git('branch','test/precision-2390-'+name,head)
    row['runs']['behavioral']=run('behavioral',['-m','tests.run_unittest_suite','--suite','focused','--plan',str(plan_path),
        '--json-output',str(directory/'behavioral-results.json'),'--verbosity','0'],directory)
    config=directory/'coverage.ini'
    row['runs']['configure']=run('configure',['.github/scripts/ci_checks.py','configure','--plan',str(plan_path),'--config',str(config)],directory)
    row['runs']['coverage']=run('coverage',['-m','coverage','run','--rcfile='+str(config),'-m','tests.run_unittest_suite',
        '--suite','coverage-plan','--plan',str(plan_path),'--json-output',str(directory/'coverage-results.json'),'--verbosity','0'],directory)
    row['runs']['coverage-export']=run('coverage-export',['-m','coverage','json','--rcfile='+str(config),'-o',str(directory/'coverage.json')],directory)
    row['runs']['impact-gate']=run('impact-gate',['.github/scripts/ci_checks.py','coverage','--plan',str(plan_path),
        '--coverage',str(directory/'coverage.json'),'--results',str(directory/'coverage-results.json')],directory)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(row),flush=True)
    if any(r['exit_code'] for r in row['runs'].values()):
        raise SystemExit('Positive control or impact proof failed: '+name)
    (repo/path).write_bytes(original.replace(before.encode(),after.replace('[0:]','[1:]').encode()))
    mutant=commit([path],'test(ci): '+name+' source fault probe')
    mutated_plan=plan(mutant);assert mutated_plan['tests']==p['tests']
    row['source_mutant_head']=mutant
    row['runs']['source-mutant']=run('source-mutant',['-m','unittest',*p['tests']],directory)
    assert row['runs']['source-mutant']['exit_code'] != 0
    git('branch','test/precision-2390-'+name+'-source-fault',mutant)
    git('reset','--hard',head)
    raw=(repo/downstream).read_text(encoding='utf-8');tree=ast.parse(raw)
    node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==function)
    lines=raw.splitlines(keepends=True)
    lines.insert(node.body[0].lineno-1,' ' * node.body[0].col_offset+'raise RuntimeError("intentional downstream probe")\n')
    (repo/downstream).write_bytes(''.join(lines).encode())
    mutant=commit([downstream],'test(ci): '+name+' downstream fault probe')
    row['downstream_mutant']={'head':mutant,'path':downstream,'function':function,'scope':'frozen positive behavioral suite'}
    row['runs']['downstream-mutant']=run('downstream-mutant',['-m','unittest',*p['tests']],directory)
    assert row['runs']['downstream-mutant']['exit_code'] != 0
    git('branch','test/precision-2390-'+name+'-downstream-fault',mutant)
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'name':name,'source_fault_rejected':True,'downstream_fault_rejected':True}),flush=True)
git('reset','--hard',base)
