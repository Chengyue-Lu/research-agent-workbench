"""Retain and verify the complete immutable proof bytes without deep Windows checkout paths."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[2]
proof = root / 'work/h5-proof'
attempt = root / 'docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-007-H5-001'
def sha(raw): return hashlib.sha256(raw).hexdigest()
inventory_path = proof / 'proof-inventory.json'
inventory = json.loads(inventory_path.read_bytes())
files = [*inventory['files'], {'path': 'proof-inventory.json', 'sha256': sha(inventory_path.read_bytes())}]
assert len({r['path'] for r in files}) == len(files)
for r in files:
    assert sha((proof / r['path']).read_bytes()) == r['sha256']
archive = attempt / 'vertical-proof.zip'
assert not archive.exists(), 'preserve existing archive'
with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
    for r in sorted(files, key=lambda r: r['path']):
        z.write(proof / r['path'], r['path'])
destination = root / '.rwb/h5-archived-proof'
assert not destination.exists(), 'cold replay destination must be new'
with zipfile.ZipFile(archive) as z:
    assert sorted(z.namelist()) == sorted(r['path'] for r in files)
    for r in files:
        assert sha(z.read(r['path'])) == r['sha256']
        assert (destination / r['path']).resolve().is_relative_to(destination.resolve())
    z.extractall(destination)
(attempt / 'proof-inventory.json').write_bytes(inventory_path.read_bytes())
refs = {'purpose': 'synthetic-contract-proof', 'observed_at': datetime.now(timezone.utc).isoformat(),
    'archive_ref': {'path': 'vertical-proof.zip', 'sha256': sha(archive.read_bytes())},
    'inventory_ref': files[-1], 'retained_files': len(files), 'uncompressed_bytes': sum((proof / r['path']).stat().st_size for r in files),
    'archive_bytes': archive.stat().st_size,
    'source_binding': 'Embedded validators pin production sources and all schemas; inventory pins repository replay helper and synthetic authority code.',
    'extraction': 'Verify archive_ref first, extract into an empty short directory, then pass the unchanged inventory_ref to tests.harness_proof replay.'}
(attempt / 'proof-refs.json').write_bytes(json.dumps(refs, ensure_ascii=False, indent=2).encode() + b'\n')
print(json.dumps(refs, sort_keys=True))
