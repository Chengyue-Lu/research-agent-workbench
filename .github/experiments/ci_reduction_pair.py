"""One fresh hosted pair of synthetic policy bases; never official CI authority."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

POLICY = 'tests/ci_impact_policy.yaml'
SUBJECT = '.github/scripts/ci_consumer_shadow.py'
GROUPS = ['diagnostic-' + name + '-local-function' for name in
          ('consumer-shadow', 'shadow-pair', 'domain-audit')]
BODY = '- **Risk tier**: R2\n- **Shared contract**: no\n- **Authority impact**: no'


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def environment(repo):
    # The actual hosted run identity is saved separately. Synthetic plans are
    # offline experiments and must not inherit the outer official event binding.
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith(('GIT_', 'PYTHON', 'GITHUB_'))}
    env.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               PYTHONPATH=os.pathsep.join(map(str, (repo/'src', repo, repo/'.github/scripts'))),
               GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull)
    return env


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=' + os.devnull,
        '-c', 'commit.gpgsign=false', '-c', 'user.name=CI paired experiment',
        '-c', 'user.email=probe@example.invalid', '-C', str(repo), *args],
        env=environment(repo), stderr=subprocess.PIPE).decode().strip()


def command(repo, out, name, args):
    begin = time.perf_counter()
    env = environment(repo)
    env['COVERAGE_FILE'] = str(out/'.coverage')
    with (out/(name+'.log')).open('xb') as log:
        result = subprocess.run(args, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    record = dict(argv=args, returncode=result.returncode, wall_seconds=time.perf_counter()-begin)
    save(out/(name+'-command.json'), record)
    if result.returncode:
        raise RuntimeError(name + ' failed; original log retained')
    return record


def prepare(source, source_head, workspace, label):
    repo = workspace/label
    git(workspace, 'clone', '--no-hardlinks', '--no-checkout', '-q', str(source), str(repo))
    git(repo, 'checkout', '-q', '--detach', source_head)
    # Identical current contracts, source and tests. Only the base's authority
    # anchor differs: missing proof must restore the ordinary consumer closure.
    # Neither synthetic root is labelled production-accepted.
    policy = json.loads((repo/POLICY).read_bytes())
    assert all(name in policy['groups'] and name in policy['surfaces'] for name in GROUPS)
    (repo/POLICY).write_text(json.dumps(policy, sort_keys=True, indent=2)+'\n', encoding='utf-8')
    git(repo, 'add', POLICY)
    tree = git(repo, 'write-tree')
    # Fresh process from this root, so planner imports cannot leak from the other arm.
    expression = ('import json,sys; from pathlib import Path; sys.path.insert(0,".github/scripts"); '
        'import plan_ci as p; f=Path(p.POLICY); v=json.loads(f.read_bytes()); '
        'leaves={x for g in v["groups"].values() for x in g["coverage"]}; '
        'v["consumer_fingerprint"]=("0"*64 if sys.argv[2]=="baseline" else '
        'p.consumer_fingerprint(Path.cwd(),sys.argv[1],leaves)); '
        'f.write_bytes(p.canonical(v))')
    subprocess.run([sys.executable, '-c', expression, tree, label], cwd=repo, env=environment(repo), check=True)
    git(repo, 'add', POLICY)
    git(repo, 'commit', '--allow-empty', '-qm', 'EXPERIMENT ONLY: ' + label + ' policy fixture')
    base = git(repo, 'rev-parse', 'HEAD')
    file = repo/SUBJECT
    old = file.read_text(encoding='utf-8')
    before, after = 'if identity not in seen]', 'if not identity in seen]'
    assert old.count(before) == 1
    file.write_text(old.replace(before, after), encoding='utf-8')
    git(repo, 'add', SUBJECT)
    git(repo, 'commit', '-qm', 'EXPERIMENT ONLY: equivalent bounded union condition')
    head = git(repo, 'rev-parse', 'HEAD')
    # Retain only the two synthetic commits; prerequisite source_head stays explicit.
    git(repo, 'bundle', 'create', str(workspace.parent/(label+'.bundle')), 'HEAD', '^'+source_head)
    save(workspace.parent/(label+'-policy.json'), json.loads((repo/POLICY).read_bytes()))
    rows = git(repo, 'ls-tree', '-r', head).splitlines()
    records = [r for r in rows if r.split('\t', 1)[1] != POLICY]
    return repo, dict(base=base, head=head, target=head,
        tree_without_policy_sha256=hashlib.sha256(('\n'.join(records)+'\n').encode()).hexdigest())


def execute(repo, binding, out):
    out.mkdir()
    plan_path = out/'plan.json'
    expression = ('import json,sys; from pathlib import Path; sys.path.insert(0,".github/scripts"); '
        'import plan_ci as p; v=p.make_plan(Path.cwd(),base=sys.argv[1],head=sys.argv[2],target=sys.argv[2],'
        'repository="Chengyue-Lu/research-agent-workbench",body=sys.argv[3]); '
        'assert not v["blocked_reasons"],v["blocked_reasons"]; Path(sys.argv[4]).write_bytes(p.canonical(v))')
    steps = {}
    origin_expression = ('import json,sys; from pathlib import Path; import plan_ci, research_workbench, yaml, coverage; '
        'mods=[plan_ci,research_workbench,yaml,coverage]; '
        'v={m.__name__:str(Path(m.__file__).resolve()) for m in mods}; '
        'root=Path.cwd().resolve(); assert Path(v["plan_ci"]).is_relative_to(root); '
        'assert Path(v["research_workbench"]).is_relative_to(root); '
        'Path(sys.argv[1]).write_text(json.dumps(v),encoding="utf-8")')
    steps['imports'] = command(repo, out, 'imports', [sys.executable, '-c', origin_expression, str(out/'origins.json')])
    # Editable installation generated only the outer checkout's resources. Each
    # isolated source root needs its own fresh build outputs before execution.
    runtime_paths = ('src/research_workbench/_runtime_data', 'src/research_workbench/_runtime_pin.py')
    for relative in runtime_paths:
        path = repo/relative
        assert path.resolve().is_relative_to(repo.resolve()) and not path.exists() and not path.is_symlink()
        assert not git(repo, 'ls-files', '--', relative)
    runtime_expression = '''from pathlib import Path
import hashlib,json,sys
import build_backend
root=Path.cwd().resolve()
assert Path(build_backend.__file__).resolve()==root/'build_backend.py'
assert build_backend.ROOT.resolve()==root
pin=build_backend.generate(root)
resources=root/'src/research_workbench/_runtime_data'
files=[*resources.rglob('*'),root/'src/research_workbench/_runtime_pin.py']
rows=[]
for path in sorted(files):
    assert not path.is_symlink() and path.resolve().is_relative_to(root)
    if path.is_file():
        rows.append([path.relative_to(root).as_posix(),hashlib.sha256(path.read_bytes()).hexdigest()])
assert pin==hashlib.sha256((resources/'manifest.json').read_bytes()).hexdigest()
Path(sys.argv[1]).write_text(json.dumps({'manifest_pin':pin,'files':rows},sort_keys=True),encoding='utf-8')
'''
    steps['runtime_setup'] = command(repo, out, 'runtime-setup', [sys.executable, '-c', runtime_expression,
        str(out/'runtime-identity.json')])
    steps['plan'] = command(repo, out, 'plan', [sys.executable, '-c', expression,
        binding['base'], binding['head'], BODY, str(plan_path)])
    plan = json.loads(plan_path.read_bytes())
    boundary = plan['selection']['reviewed_opaque_boundary']
    if out.name == 'baseline':
        assert SUBJECT not in boundary
        assert plan['selection']['reviewed_contract_anchor'] == ''
    else:
        assert boundary == [SUBJECT]
        assert plan['selection']['reviewed_contract_anchor'] == binding['base']
        assert plan['behavioral_scope'] == 'focused' and plan['coverage_scope'] == 'impact'
        assert not plan['package_smoke'] and not plan['repository_smoke']
    config = out/'coverage.ini'
    steps['configure'] = command(repo, out, 'configure', [sys.executable,
        '.github/scripts/ci_checks.py', 'configure', '--plan', str(plan_path), '--config', str(config)])
    steps['producer'] = command(repo, out, 'producer', [sys.executable, '-m', 'coverage', 'run',
        '--rcfile='+str(config), '-m', 'tests.run_unittest_suite', '--suite', 'coverage-execution',
        '--plan', str(plan_path), '--json-output', str(out/'execution.json'),
        '--coverage-results', str(out/'coverage-results.json'), '--verbosity', '1'])
    steps['export'] = command(repo, out, 'coverage-json', [sys.executable, '-m', 'coverage', 'json',
        '--rcfile='+str(config), '-o', str(out/'coverage.json')])
    steps['quality'] = command(repo, out, 'quality', [sys.executable, '.github/scripts/ci_checks.py',
        'coverage', '--plan', str(plan_path), '--coverage', str(out/'coverage.json'),
        '--results', str(out/'coverage-results.json')])
    steps['behavioral_projection'] = command(repo, out, 'behavioral-projection', [sys.executable,
        'tests/run_unittest_suite.py', '--suite', 'behavioral-evidence', '--plan', str(plan_path),
        '--execution-results', str(out/'execution.json'), '--json-output', str(out/'behavioral.json')])
    receipts = {name: json.loads((out/file).read_bytes()) for name, file in (
        ('U', 'execution.json'), ('B', 'behavioral.json'), ('C', 'coverage-results.json'))}
    ids = {name: [row['id'] for row in value['tests']] for name, value in receipts.items()}
    for name, value in receipts.items():
        assert value['successful'] and all(row['outcome'] == 'passed' for row in value['tests'])
        assert len(ids[name]) == len(set(ids[name]))
    assert set(ids['U']) == set(ids['B']) | set(ids['C'])
    plan = json.loads(plan_path.read_bytes())
    result = dict(binding=binding, plan_id=plan['plan_id'], steps=steps,
        counts={name: len(rows) for name, rows in ids.items()}, ids=ids,
        production_authority=False, smokes_executed=False,
        scope='ordered 3.11 coverage producer plus exact B/C projections; synthetic bases')
    save(out/'summary.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--pair', type=int, choices=(1, 2, 3), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert len(args.head) == 40 and all(c in '0123456789abcdef' for c in args.head)
    out = args.output.resolve()
    out.mkdir()
    workspace = out/'repositories'
    workspace.mkdir()
    freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze', '--all'], text=True)
    # Editable checkout location is shared within each pair and recorded verbatim.
    (out/'pip-freeze.txt').write_text(freeze, encoding='utf-8')
    save(out/'environment.json', dict(python=sys.version, platform=platform.platform(),
        dependencies_sha256=hashlib.sha256(freeze.encode()).hexdigest(),
        source=args.head, pair=args.pair, pid=os.getpid(),
        github={k: os.environ.get(k) for k in ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA',
            'RUNNER_OS', 'RUNNER_ARCH', 'ImageOS', 'ImageVersion')}))
    prepared = {label: prepare(args.source.resolve(), args.head, workspace, label)
                for label in ('baseline', 'reduced')}
    assert prepared['baseline'][1]['tree_without_policy_sha256'] == prepared['reduced'][1]['tree_without_policy_sha256']
    save(out/'prepared.json', {k: v[1] for k, v in prepared.items()})
    # Alternate arm order to expose simple warm-cache/order bias. Both arms run on
    # the same fresh hosted machine; retain raw times, never subtract stale runs.
    order = ['baseline', 'reduced'] if args.pair % 2 else ['reduced', 'baseline']
    results = {label: execute(*prepared[label], out/label) for label in order}
    assert (out/'baseline/runtime-identity.json').read_bytes() == (out/'reduced/runtime-identity.json').read_bytes()
    assert results['reduced']['counts']['U'] < results['baseline']['counts']['U']
    assert set(results['reduced']['ids']['U']) <= set(results['baseline']['ids']['U'])
    save(out/'pair.json', dict(status='PASS', pair=args.pair, order=order,
        counts={k: v['counts'] for k, v in results.items()},
        producer_seconds={k: v['steps']['producer']['wall_seconds'] for k, v in results.items()},
        source=args.head, production_authority=False,
        comparison='ordinary missing-anchor closure versus matching-anchor contract; not a replay of historical policy',
        scope='fresh hosted ordered coverage producer pair; excludes setup and smokes'))


if __name__ == '__main__':
    main()
