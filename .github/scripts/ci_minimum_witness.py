"""Recompute CI obligations with an externally pinned, isolated accepted planner.

This verifies a candidate plan against accepted Git inputs. A PASS does not
approve the checker, authorize activation, or attest that tests actually ran.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SELF = '.github/scripts/ci_minimum_witness.py'
HELPERS = ('.github/scripts/plan_ci.py', '.github/scripts/ci_dependencies.py',
           '.github/scripts/check_pr_governance.py', '.github/governance-policy.json')
LIMIT = 16 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n').encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'duplicate JSON key')
        value[key] = item
    return value


def read_json(raw):
    require(len(raw) <= LIMIT, 'oversized JSON input')
    return json.loads(raw, object_pairs_hook=unique)


def exact(value):
    require(isinstance(value, str) and re.fullmatch('[0-9a-f]{40}', value), 'exact Git SHA required')
    return value


def environment():
    # Neither Python injection nor Git replacement/config environment is input.
    result = {k: v for k, v in os.environ.items()
              if not k.upper().startswith(('PYTHON', 'GIT_'))}
    result.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                  GIT_NO_REPLACE_OBJECTS='1', GIT_TERMINAL_PROMPT='0')
    return result


def git(repo, *args):
    return subprocess.check_output(
        ['git', '--no-replace-objects', '-C', str(repo), *args],
        env=environment(), stderr=subprocess.PIPE)


def blob(repo, commit, path):
    records = git(repo, 'ls-tree', '-z', exact(commit), '--', path).split(b'\0')
    require(len(records) == 2 and records[-1] == b'', 'missing or ambiguous trusted blob: ' + path)
    meta, actual = records[0].split(b'\t')
    mode, kind, oid = meta.decode().split()
    require(actual.decode() == path and mode == '100644' and kind == 'blob',
            'unsupported trusted blob mode: ' + path)
    raw = git(repo, 'cat-file', 'blob', oid)
    require(len(raw) <= LIMIT, 'oversized trusted blob')
    require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == oid,
            'trusted Git blob identity mismatch: ' + path)
    return raw, {'mode': mode, 'git_blob': oid, 'sha256': digest(raw)}


def database_path(source):
    marker = source / '.git'
    require(not marker.is_symlink(), 'symlink Git directory marker')
    if marker.is_file():
        value = marker.read_text(encoding='utf-8').strip()
        require(value.startswith('gitdir: ') and '\n' not in value, 'invalid Git directory marker')
        location = (source / value[8:]).resolve()
    else:
        location = marker if marker.is_dir() else source
    common_path = location / 'commondir'
    common = (location / common_path.read_text(encoding='utf-8').strip()).resolve() if common_path.exists() else location
    require((common / 'objects').is_dir(), 'unavailable Git object database')
    for path in ('objects/info/alternates', 'info/grafts', 'shallow'):
        require(not (common / path).exists(), 'unsupported Git database input: ' + path)
    require(not list((common / 'objects/pack').glob('*.promisor')), 'promisor Git objects are unsupported')
    for path in (common / 'config', location / 'config.worktree'):
        if path.exists():
            require(not path.is_symlink(), 'symlink Git config')
            config = path.read_text(encoding='utf-8').lower()
            require(not re.search(r'^\s*\[(?:include|filter|fsck|uploadpack|receive|alias|diff|credential)', config, re.M)
                    and not re.search(r'^\s*(?:promisor|partialclone|alternaterefscommand|sshcommand|fsmonitor)\s*=', config, re.M),
                    'nonstandard Git configuration is unsupported')
    return common


def copy_database(source, destination):
    # Filesystem inspection precedes the first Git subprocess on source inputs.
    database_path(source)
    git(destination.parent, 'clone', '--bare', '--local', '--no-hardlinks', '-q', str(source.resolve()), str(destination))
    database_path(destination)
    # Use the clean clone's configuration; source fsck.skipList/ignore settings
    # cannot suppress corrupt ancestor commits, trees, or leaf objects.
    git(destination, 'fsck', '--full', '--strict', '--no-reflogs')


def authenticate_checkout(root, commit):
    sources = {}
    with tempfile.TemporaryDirectory(prefix='ci-witness-checker-') as directory:
        data = Path(directory) / 'checker.git'
        copy_database(root, data)
        require(git(data, 'rev-parse', 'HEAD').decode().strip() == exact(commit),
                'witness checkout differs from caller-pinned commit')
        for path in (SELF, *HELPERS):
            raw, record = blob(data, commit, path)
            local = root / path
            require(not local.is_symlink() and local.is_file() and local.resolve().is_relative_to(root.resolve())
                    and local.read_bytes() == raw and (os.name == 'nt' or not local.stat().st_mode & 0o111),
                    'witness checkout source drift: ' + path)
            sources[path] = record
    return sources


def input_commits(repo, base, head, target):
    """Validate identities and topology only in the clean, copied Git database."""
    require(not (repo / 'info/grafts').exists(), 'Git grafts cannot supply input topology')
    for commit in (base, head, target):
        raw = git(repo, 'cat-file', 'commit', exact(commit))
        require(hashlib.sha1(b'commit ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == commit,
                'input Git commit identity mismatch')
    if target != head:
        require(git(repo, 'show', '-s', '--format=%P', target).decode().split() == [base, head],
                'target is not exact PR merge candidate')


def worker(request):
    """Called only in a fresh interpreter with an authenticated temporary tree."""
    trusted = Path(request['trusted'])
    sys.path.insert(0, str(trusted / '.github/scripts'))
    import plan_ci as planner

    minimum = planner.make_plan(Path(request['repo']), **request['inputs'])
    candidate = request['plan']
    unsigned = dict(candidate)
    signature = unsigned.pop('plan_id')
    require(planner.digest(unsigned) == signature, 'candidate plan digest mismatch')
    require(set(candidate) == set(minimum), 'candidate plan shape mismatch')
    require(candidate['binding'] == minimum['binding'], 'candidate plan binding mismatch')
    result = {'kind': 'internal-planner-comparison', 'minimum_plan': minimum, 'comparison': 'BLOCK', 'reason': ''}
    try:
        planner.require_obligations(candidate, minimum)
        result['comparison'] = 'PASS'
    except (ValueError, KeyError, TypeError) as error:
        result['reason'] = str(error)
    loaded = {}
    for name in ('plan_ci', 'ci_dependencies', 'ci_governance'):
        module = sys.modules.get(name)
        require(module is not None, 'accepted project helper was not loaded: ' + name)
        path = Path(module.__file__).resolve()
        require(path.is_relative_to(trusted.resolve()), 'project helper escaped trusted tree')
        relative = path.relative_to(trusted.resolve()).as_posix()
        require(relative in HELPERS, 'unexpected project helper')
        loaded[relative] = digest(path.read_bytes())
    require(loaded == {p: record['sha256'] for p, record in request['sources'].items() if p.endswith('.py')},
            'loaded accepted helper identity mismatch')
    result['loaded_project_helpers'] = loaded
    import yaml
    result['yaml_runtime'] = {'version': yaml.__version__, 'origin': str(Path(yaml.__file__).resolve()),
                              'sha256': digest(Path(yaml.__file__).read_bytes())}
    return result


def witness(repo, *, repository, base, head, target, body, plan, expected_witness,
            base_ref='develop'):
    require(sys.flags.isolated, 'invoke witness with Python -I')
    root = Path(__file__).resolve().parents[2]
    sources = authenticate_checkout(root, expected_witness)
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository), 'invalid repository')
    require(isinstance(body, str) and len(body.encode()) <= LIMIT, 'invalid PR metadata body')
    require(base_ref in {'develop', 'main'}, 'invalid base ref')
    for commit in (base, head, target):
        exact(commit)
    inputs = dict(repository=repository, base=base, head=head, target=target, body=body, base_ref=base_ref)
    receipt = {'kind': 'ci-minimum-witness', 'status': 'BLOCK', 'scope': 'accepted planner minimum only',
               'witness_commit': expected_witness, 'witness_sources': sources,
               'accepted_planner_base': base, 'execution_authority': False,
               'checker_acceptance_proved': False, 'execution_checks_proved': False,
               'input_sha256': digest(canonical(inputs)), 'metadata_body_sha256': digest(body.encode()),
               'candidate_plan_sha256': digest(canonical(plan)), 'inputs': {k: v for k, v in inputs.items() if k != 'body'}}
    with tempfile.TemporaryDirectory(prefix='ci-minimum-witness-') as directory:
        temporary = Path(directory)
        data = temporary / 'data.git'
        # Local object copying avoids checkout, filters, hooks and candidate imports.
        copy_database(Path(repo), data)
        input_commits(data, base, head, target)
        trusted = temporary / 'trusted'
        accepted = {}
        for path in HELPERS:
            raw, record = blob(data, base, path)
            destination = trusted / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
            accepted[path] = record
        receipt['accepted_sources'] = accepted
        receipt['input_trees'] = {name: git(data, 'rev-parse', commit + '^{tree}').decode().strip()
                                  for name, commit in (('base', base), ('head', head), ('target', target))}
        runner = temporary / 'runner.py'
        runner_source = Path(__file__).read_bytes()
        require(digest(runner_source) == sources[SELF]['sha256'], 'witness source changed during verification')
        runner.write_bytes(runner_source)
        request = dict(trusted=str(trusted), repo=str(data), inputs=inputs, plan=plan, sources=accepted)
        process = subprocess.run([sys.executable, '-I', '-B', str(runner), '--worker'],
                                 input=canonical(request), capture_output=True, cwd=temporary,
                                 env=environment(), timeout=180)
        require(process.returncode == 0, 'isolated accepted planner failed: ' + process.stderr.decode(errors='replace')[-2000:])
        result = read_json(process.stdout)
        require(result.pop('kind') == 'internal-planner-comparison', 'invalid internal planner response')
        receipt.update(result)
        receipt['status'] = result['comparison']
    receipt['receipt_id'] = digest(canonical(receipt))
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repository', 'base', 'head', 'target', 'expected-witness'):
        parser.add_argument('--' + name, required=True)
    for name in ('repo', 'body', 'plan', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--base-ref', default='develop')
    args = parser.parse_args(argv)
    # Exclusive create refuses pre-existing evidence and input aliases before work.
    with args.output.open('xb') as output:
        receipt = {'kind': 'ci-minimum-witness', 'status': 'BLOCK', 'scope': 'accepted planner minimum only', 'execution_authority': False}
        try:
            receipt = witness(args.repo, repository=args.repository, base=args.base, head=args.head,
                              target=args.target, body=args.body.read_text(encoding='utf-8'),
                              plan=read_json(args.plan.read_bytes()), expected_witness=args.expected_witness,
                              base_ref=args.base_ref)
        except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
            receipt['reason'] = str(error)
        output.write(canonical(receipt))
    print(canonical(receipt).decode(), end='')
    return int(receipt['status'] != 'PASS')


def entrypoint():
    if sys.argv[1:] == ['--worker']:
        require(sys.flags.isolated, 'worker requires Python -I')
        print(canonical(worker(read_json(sys.stdin.buffer.read()))).decode(), end='')
        return 0
    else:
        return main()


if __name__ == '__main__':
    raise SystemExit(entrypoint())
