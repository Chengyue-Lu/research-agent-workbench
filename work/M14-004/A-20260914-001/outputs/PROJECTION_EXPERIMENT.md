# Review-fix projection experiment

Archival source only; fixture CI assertions confer no release authority.

```python
"""Local acceptance experiment; source retained as Markdown in the review archive."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, re, subprocess, sys, tempfile

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from tests.public_surface_helpers import documentation_errors, build_input_errors

OUT = ROOT / '.rwb/m14-004/review-20260914'
parser = argparse.ArgumentParser()
parser.add_argument('--python', action='append', required=True)
args = parser.parse_args()

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()

release = module('quickstart_release', ROOT / '.github/scripts/release_surface.py')
portable = module('quickstart_portable', ROOT / '.github/scripts/portable_package_smoke.py')
source = git(ROOT, 'rev-parse', 'HEAD')
parent = git(ROOT, 'rev-parse', 'origin/main')
assert not git(ROOT, 'status', '--porcelain')

with tempfile.TemporaryDirectory(prefix='rwb-quickstart-acceptance-') as temporary:
    work = Path(temporary).resolve()
    repo = work / 'repo'
    subprocess.run(['git', 'clone', '--quiet', '--shared', '--no-checkout', str(ROOT), str(repo)], check=True)
    git(repo, 'config', 'core.autocrlf', 'false')
    git(repo, 'checkout', '--quiet', '--detach', source)
    git(repo, 'remote', 'set-url', 'origin', 'https://github.com/Example/m14-docs-fixture.git')
    git(repo, 'update-ref', 'refs/remotes/origin/develop', source)
    git(repo, 'update-ref', 'refs/remotes/origin/main', parent)
    expected = dict(repository='Example/m14-docs-fixture', source=source, parent=parent,
                    policy_version='1.1.0', release_version='0.1.0', source_ci=dict(
                        repository='Example/m14-docs-fixture', sha=source, workflow='CI', run_id=123,
                        conclusion='success', required_checks=release.REQUIRED_CHECKS))
    first, second = work / 'projection-a', work / 'projection-b'
    first.mkdir(); second.mkdir()
    a, b = release.export(repo, expected, first), release.export(repo, expected, second)
    assert a == b
    files = {p.relative_to(first).as_posix(): p.read_bytes() for p in first.rglob('*') if p.is_file()}
    again = {p.relative_to(second).as_posix(): p.read_bytes() for p in second.rglob('*') if p.is_file()}
    assert files == again
    assert not documentation_errors(files), documentation_errors(files)
    assert not build_input_errors(files), build_input_errors(files)
    source_entries = release.entries(repo, source)
    for path in source_entries:
        if path.startswith(('src/research_workbench/', 'schemas/')):
            assert files[path] == release.blob(repo, source_entries[path][1])
    text = files['docs/GETTING_STARTED.md'].decode()
    commands = []
    for section in re.split(r'^## ', text, flags=re.M)[1:]:
        if section[0] not in '234':
            continue
        for block in re.findall(r'```shell\n(.*?)```', section, flags=re.S):
            for line in block.splitlines():
                if line.startswith('rwb ') or line == 'cd offline-project':
                    commands.append(line)
    assert len(commands) == 13, commands
    report = dict(purpose='synthetic projection/link acceptance; no current installed walkthrough or release authority',
                  implementation_head=source, source_tree=git(ROOT, 'rev-parse', 'HEAD^{tree}'),
                  parent_fixture=parent, policy_version='1.1.0', merge_eligible=False,
                  repeated_bytes_identical=True, file_count=len(files), public_links='PASS',
                  build_inputs='PASS', source_classes_complete=True, commands=commands,
                  quickstart_sha256=hashlib.sha256(files['docs/GETTING_STARTED.md']).hexdigest())
    (OUT / 'projection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)
```
