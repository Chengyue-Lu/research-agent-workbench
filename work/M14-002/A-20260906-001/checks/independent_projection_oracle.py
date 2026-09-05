"""Independent source/provenance checks in a synthetic Git repository only."""
import copy
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]))
import hashlib
import json
from tests.test_release_surface import ReleaseSurfaceTests, command, release, write

ReleaseSurfaceTests.setUpClass()
case=ReleaseSurfaceTests()
case.setUp()
try:
    pinned=copy.deepcopy(case.expected)
    write(case.repo,'src/run.py',b"print('newer clean checkout')\n")
    case.update_source()
    files=release.project(case.repo,pinned)
    assert files['src/run.py'][1]==b"print('frozen source')\n"
    assert (case.repo/'src/run.py').read_bytes()!=files['src/run.py'][1]
    manifest=json.loads(files[release.MANIFEST][1])
    assert release.MANIFEST not in {item['path'] for item in manifest['outputs']}
    observed=set()
    for item in manifest['outputs']:
        path=item['path']
        mode,data=files[path]
        assert item['sha256']==hashlib.sha256(data).hexdigest()
        assert item['size']==len(data)
        assert item['mode']==mode
        if item['origin']=='source_blob':
            source_data=command(case.repo,'show',pinned['source']+':'+path)
            assert data==source_data
            oid=command(case.repo,'rev-parse',pinned['source']+':'+path).decode().strip()
            assert item['blob']==oid
        else:
            generated=json.loads(data)
            assert generated==item['generator']['inputs']
            for field in ('repository','source','parent','release_version','policy_version'):
                assert generated[field]==pinned[field]
            assert item['generator']['sha256']==hashlib.sha256((release.ROOT/release.TOOL).read_bytes()).hexdigest()
        observed.add(path)
    all_source=set(command(case.repo,'ls-tree','-r','--name-only',pinned['source']).decode().splitlines())
    chosen={row['path'] for row in manifest['outputs'] if row['origin']=='source_blob'}
    assert set(manifest['excluded'])==all_source-chosen
    assert observed|{release.MANIFEST}==set(files)
    candidate,tree=case.candidate(files)
    result=release.check(case.repo,pinned,candidate)
    assert result['tree']==tree
    print(json.dumps({'result':'PASS','source_pin':'older synthetic commit with newer clean checkout',
                      'source_blob_and_generated_outputs_verified':len(observed),
                      'manifest_last_and_excluded_closure':'PASS','git_tree_oracle':'PASS',
                      'merge_eligible':result['merge_eligible']},indent=2))
finally:
    case.doCleanups()
    ReleaseSurfaceTests.tearDownClass()
