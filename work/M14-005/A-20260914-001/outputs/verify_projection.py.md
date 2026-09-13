# Evidence helper source

```python
"""Readiness experiment only; does not create a repository release ref or attestation."""
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / '.rwb/m14-005/evidence'
sys.path.insert(0, str(ROOT))
from tests.public_surface_helpers import documentation_errors, build_input_errors

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result

def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode().strip()

parser = argparse.ArgumentParser()
parser.add_argument('--python', action='append', required=True)
args = parser.parse_args()
release = module('readiness_release', ROOT / '.github/scripts/release_surface.py')
portable = module('readiness_portable', ROOT / '.github/scripts/portable_package_smoke.py')
source = git(ROOT, 'rev-parse', 'HEAD')
parent = git(ROOT, 'rev-parse', 'origin/main')
assert not git(ROOT, 'status', '--porcelain')
baseline = 'f7a9715ed35787d3326283c22f834b1514c5c88c'
old_policy = json.loads(git(ROOT, 'show', baseline + ':.github/release-surface.yml'))
policy = json.loads((ROOT / '.github/release-surface.yml').read_bytes())
assert policy['policies'][:-1] == old_policy['policies']
last = copy.deepcopy(policy['policies'][-1]); last['version'] = '1.1.0'
last['include'].remove({'path':'LICENSE', 'kind':'file'})
assert last == old_policy['policies'][-1]
for path in ['registry/skills/accepted.json', 'registry/skills/sources.json']:
    old = git(ROOT, 'show', baseline + ':' + path)
    new = (ROOT / path).read_text(encoding='utf-8')
    assert json.loads(old.replace('"license_status": "project-original-unlicensed"', '"license_status": "MIT"')) == json.loads(new)
assert not git(ROOT, 'diff', baseline, source, '--', '.agents/skills', 'skill-lab', 'registry/skills/accepted',
               'registry/skills/release-projections.json', 'src', 'schemas', 'work/M14-004')

with tempfile.TemporaryDirectory(prefix='rwb-readiness-fixture-') as temporary:
    work = Path(temporary).resolve()
    repo = work / 'repo'
    subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(ROOT),str(repo)],check=True)
    git(repo,'config','core.autocrlf','false')
    git(repo,'checkout','--quiet','--detach',source)
    git(repo,'remote','set-url','origin','https://github.com/Example/m14-readiness-fixture.git')
    git(repo,'update-ref','refs/remotes/origin/develop',source)
    git(repo,'update-ref','refs/remotes/origin/main',parent)
    expected = dict(repository='Example/m14-readiness-fixture', source=source,parent=parent,
                    policy_version='1.2.0',release_version='0.1.0',source_ci=dict(
                        repository='Example/m14-readiness-fixture',sha=source,workflow='CI',run_id=123,
                        conclusion='success',required_checks=release.REQUIRED_CHECKS))
    first,second = work/'projection-a',work/'projection-b'
    first.mkdir(); second.mkdir()
    a,b=release.export(repo,expected,first),release.export(repo,expected,second)
    assert a==b
    files={p.relative_to(first).as_posix():p.read_bytes() for p in first.rglob('*') if p.is_file()}
    again={p.relative_to(second).as_posix():p.read_bytes() for p in second.rglob('*') if p.is_file()}
    assert files==again
    assert not documentation_errors(files),documentation_errors(files)
    assert not build_input_errors(files),build_input_errors(files)
    entries=release.entries(repo,source)
    for path in entries:
        if path.startswith(('src/research_workbench/','schemas/')) or path=='LICENSE':
            assert files[path]==release.blob(repo,entries[path][1])
    assert json.loads(files['registry/skills/release-projections.json'])['entries']==[]
    assert not any(p.startswith(('work/','tests/','.agents/','.codex/','docs/workstreams/')) for p in files)
    report=dict(purpose='synthetic readiness projection and package experiment',implementation_head=source,
                source_tree=git(ROOT,'rev-parse','HEAD^{tree}'),parent_fixture=parent,policy_version='1.2.0',
                synthetic_repository=expected['repository'],synthetic_ci=True,release_source_frozen=False,
                merge_eligible=False,repeated_bytes_identical=True,file_count=len(files),public_links='PASS',
                build_inputs='PASS',source_classes_complete=True,production_projection_entries=0,
                historical_policy_versions_unchanged=True,original_skill_content_and_identity_unchanged=True,
                original_external_source_license_records_unchanged=True,
                license_sha256=hashlib.sha256(files['LICENSE']).hexdigest(),
                fixture_manifest_sha256=hashlib.sha256(files['RELEASE_MANIFEST.json']).hexdigest())
    (OUT/'projection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report),flush=True)
    portable.ROOT=first
    sys.argv=['portable-smoke','--output',str(OUT/'package.json')]
    for interpreter in args.python:
        sys.argv.extend(['--python',interpreter])
    portable.main()

```
