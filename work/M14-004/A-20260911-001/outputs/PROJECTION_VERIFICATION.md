# Projected-source verification record

This is the source snapshot of the local verification experiment recorded in checks/projection.json and
checks/projection-package.json. It is archival documentation, not a maintained executable or a CI entrypoint.
The maintained public-surface checks run with `python -m unittest tests.test_documentation tests.test_public_surface`.
The package harness is `.github/scripts/portable_package_smoke.py`; the experiment supplied the exported fixture tree
as its source and used both accepted Python interpreters. Its synthetic source-CI expectations confer no release authority.

The original experiment source is retained below for review. Local paths, interpreter selection and fixture source identity
must be chosen explicitly when repeating the experiment; the archived result is bound to its recorded implementation head.

```python
from pathlib import Path
import argparse,importlib.util,json,subprocess,sys,tempfile,hashlib
ROOT=Path.cwd();sys.path.insert(0,str(ROOT))
from tests.public_surface_helpers import documentation_errors,build_input_errors
parser=argparse.ArgumentParser()
parser.add_argument('--with-package',action='store_true')
parser.add_argument('--python',action='append')
args=parser.parse_args()
OUT=ROOT/'.rwb/m14-004';OUT.mkdir(parents=True,exist_ok=True)
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);sys.modules[name]=value;spec.loader.exec_module(value);return value
release=module('m14_surface',ROOT/'.github/scripts/release_surface.py')
portable=module('m14_portable',ROOT/'.github/scripts/portable_package_smoke.py')
def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE).decode().strip()
source=git(ROOT,'rev-parse','HEAD');parent=git(ROOT,'rev-parse','origin/main')
assert not git(ROOT,'status','--porcelain')
with tempfile.TemporaryDirectory(prefix='rwb-public-surface-fixture-') as tmp:
 work=Path(tmp).resolve();repo=work/'repo'
 subprocess.run(['git','clone','--quiet','--shared','--no-checkout',str(ROOT),str(repo)],check=True)
 git(repo,'config','core.autocrlf','false');git(repo,'checkout','--quiet','--detach',source)
 git(repo,'remote','set-url','origin','https://github.com/Example/m14-docs-fixture.git')
 git(repo,'update-ref','refs/remotes/origin/develop',source);git(repo,'update-ref','refs/remotes/origin/main',parent)
 expected={'repository':'Example/m14-docs-fixture','source':source,'parent':parent,'policy_version':'1.1.0','release_version':'0.1.0','source_ci':{'repository':'Example/m14-docs-fixture','sha':source,'workflow':'CI','run_id':123,'conclusion':'success','required_checks':release.REQUIRED_CHECKS}}
 first,second=work/'projection-a',work/'projection-b';first.mkdir();second.mkdir()
 a=release.export(repo,expected,first);b=release.export(repo,expected,second);assert a==b
 files={p.relative_to(first).as_posix():p.read_bytes() for p in first.rglob('*') if p.is_file()}
 again={p.relative_to(second).as_posix():p.read_bytes() for p in second.rglob('*') if p.is_file()};assert files==again
 assert not documentation_errors(files),documentation_errors(files)
 assert not build_input_errors(files),build_input_errors(files)
 source_entries=release.entries(repo,source)
 for path in source_entries:
  if path.startswith(('src/research_workbench/','schemas/')):
   assert path in files and files[path]==release.blob(repo,source_entries[path][1])
 report={'purpose':'synthetic local projection/package acceptance only; not release source freeze or hosted CI attestation','implementation_head':source,'policy_version':'1.1.0','projection':a,'repeated_bytes_identical':True,'file_count':len(files),'public_doc_count':sum(p.endswith('.md') for p in files),'public_links':'PASS','build_inputs':'PASS','source_classes_complete':True,'merge_eligible':False}
 (OUT/'projection.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(report),flush=True)
 # Invoke the accepted package harness over the exported source tree when requested.
 if args.with_package:
  portable.ROOT=first
  sys.argv=['portable_package_smoke','--output',str(OUT/'projection-package.json')]
  for interpreter in args.python or [sys.executable]:sys.argv+=['--python',interpreter]
  portable.main()
```
