"""Independent behavioral-floor witness. Never import or execute candidate code."""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

import yaml

AUTHORITY = ('.github/scripts/plan_ci.py', '.github/scripts/ci_dependencies.py',
             '.github/scripts/ci_checks.py', 'tests/run_unittest_suite.py', '.github/workflows/ci.yml',
             '.github/scripts/selection_witness.py')
LIMIT = 4 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value), 'invalid exact Git SHA')
    return value


def git(repo, *args):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(repo), *args], stderr=subprocess.PIPE)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def read_json(raw):
    require(len(raw) <= LIMIT, 'oversized JSON input')
    return json.loads(raw, object_pairs_hook=unique)


def canonical(data):
    return (json.dumps(data, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n').encode()


def blob(repo, commit, path):
    entry = git(repo, 'ls-tree', commit, '--', path).decode().strip()
    if not entry:
        return '', b''
    mode = entry.split()[0]
    require(mode in {'100644', '100755'}, 'unsupported authority file mode')
    raw = git(repo, 'show', commit + ':' + path)
    require(len(raw) <= LIMIT, 'oversized authority source')
    return mode, raw


def semantic(path, raw):
    if path.endswith('.py'):
        return ast.dump(ast.parse(raw))
    node = yaml.compose(raw)
    return yaml.serialize(node, canonical=True) if node is not None else None


def witness(repo, repository, base, head, plan):
    """Inputs base/head/repository come from the reviewer or GitHub API, never the plan."""
    for commit in (base, head):
        require(git(repo, 'rev-parse', sha(commit) + '^{commit}').decode().strip() == commit, 'unavailable exact commit')
    merge_base = git(repo, 'merge-base', base, head).decode().strip()
    binding = plan['binding']
    require({k: binding[k] for k in ('repository', 'base', 'head', 'merge_base')} ==
            dict(repository=repository, base=base, head=head, merge_base=merge_base), 'plan binding mismatch')
    target = sha(binding['target'])
    if target != head:
        require(git(repo, 'show', '-s', '--format=%P', target).decode().split() == [base, head], 'wrong merge candidate')
    unsigned = dict(plan); signature = unsigned.pop('plan_id')
    require(hashlib.sha256(canonical(unsigned)).hexdigest() == signature, 'plan digest mismatch')
    require(plan.get('version') == 4, 'unsupported plan version')
    require(plan.get('behavioral_scope') in {'none', 'focused', 'full'}, 'invalid behavioral scope')
    changed = []
    for path in AUTHORITY:
        before_mode, before = blob(repo, merge_base, path)
        after_mode, after = blob(repo, head, path)
        try:
            differs = before_mode != after_mode or semantic(path, before) != semantic(path, after)
        except (SyntaxError, UnicodeError, yaml.YAMLError, RecursionError):
            differs = True
        if differs:
            changed.append(path)
    required = bool(changed or merge_base != base)
    if required:
        require(plan['behavioral_scope'] == 'full' and plan.get('change_class') == 'full',
                'selection authority requires FULL independently of candidate self-verification')
        require(plan.get('python_versions') == ['3.11', '3.13'], 'FULL must retain both Python versions')
    return {'status': 'PASS', 'scope': 'selection-authority floor only', 'repository': repository,
            'base': base, 'head': head, 'target': target, 'authority_changes': changed,
            'required_behavioral': 'full' if required else 'none', 'observed_behavioral': plan['behavioral_scope'],
            'plan_id': signature, 'execution_checks_proved': False}


def api(repository, suffix):
    return subprocess.check_output(['gh', 'api', 'repos/' + repository + suffix])


def hosted_inputs(repository, pr_number, run_id):
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository), 'invalid repository')
    require(pr_number > 0 and run_id > 0, 'positive PR and run IDs required')
    pr = read_json(api(repository, '/pulls/' + str(pr_number)))
    run = read_json(api(repository, '/actions/runs/' + str(run_id)))
    require(pr['state'] == 'open' and pr['base']['repo']['full_name'] == repository, 'wrong PR state or repository')
    require(run['head_sha'] == pr['head']['sha'] and run['path'] == '.github/workflows/ci.yml'
            and run['event'] in {'pull_request', 'workflow_dispatch'}, 'unrelated content run')
    require(run['head_repository']['full_name'] == pr['head']['repo']['full_name'], 'wrong run source repository')
    artifacts = read_json(api(repository, '/actions/runs/' + str(run_id) + '/artifacts'))['artifacts']
    artifacts = [a for a in artifacts if a['name'] == 'ci-plan' and not a['expired']]
    require(len(artifacts) == 1, 'missing or ambiguous plan artifact')
    archive = api(repository, '/actions/artifacts/' + str(artifacts[0]['id']) + '/zip')
    require(len(archive) <= LIMIT, 'oversized plan archive')
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        require(bundle.namelist() == ['ci-plan.json'], 'unexpected archive members')
        require(bundle.getinfo('ci-plan.json').file_size <= LIMIT, 'oversized plan member')
        plan = read_json(bundle.read('ci-plan.json'))
    return pr, run, plan


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--repository', required=True)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--base')
    parser.add_argument('--head')
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--pr', type=int)
    parser.add_argument('--run', type=int)
    parser.add_argument('--expected-witness', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    receipt = {'status': 'BLOCK', 'witness_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    try:
        trusted = git(root, 'rev-parse', 'HEAD').decode().strip()
        require(trusted == sha(args.expected_witness), 'witness checkout differs from reviewer-pinned commit')
        pinned = git(root, 'show', trusted + ':.github/scripts/selection_witness.py')
        require(hashlib.sha256(pinned).hexdigest() == receipt['witness_source_sha256'], 'witness source drift')
        receipt['witness_commit'] = trusted
        if args.pr is not None:
            pr, run, plan = hosted_inputs(args.repository, args.pr, args.run)
            with tempfile.TemporaryDirectory(prefix='selection-witness-data-') as directory:
                git(directory, 'init', '--bare', '-q')
                refs = [sha(v) for v in (pr['base']['sha'], pr['head']['sha'], plan['binding']['target'])]
                git(directory, 'fetch', '--no-tags', 'https://github.com/' + args.repository + '.git', *refs)
                receipt.update(witness(directory, args.repository, refs[0], refs[1], plan))
            receipt.update(content_run=run['id'], content_status=run['status'], content_conclusion=run['conclusion'])
        else:
            receipt.update(witness(args.repo, args.repository, args.base, args.head, read_json(args.plan.read_bytes())))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        receipt.update(status='BLOCK', reason=str(error))
    args.output.write_bytes(canonical(receipt))
    print(canonical(receipt).decode())
    return int(receipt['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
