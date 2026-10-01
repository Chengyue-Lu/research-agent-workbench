"""Check the complete audit files using the clean accepted source's validator."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-root', type=Path, required=True)
args = parser.parse_args()
sys.dont_write_bytecode = True
sys.path.insert(0, str(args.source_root / '.github/scripts'))
import release_source_ci as source_ci
import release_ruleset_cutover as checker

data = Path(__file__).resolve().parent
load = lambda name: json.loads((data / name).read_text(encoding='utf-8'))
binding = load('candidate-binding.json')
source_ci.require(__debug__, 'optimized audit validation forbidden')
source_ci.local_source(args.source_root, 'Chengyue-Lu/research-agent-workbench', binding['source'])
source_ci.require(source_ci.git(args.source_root, 'show', binding['source'] + ':' + checker.TOOL) == (args.source_root / checker.TOOL).read_bytes(), 'source validator byte drift')
index = load('evidence-index.json')
source_ci.require(set(index) == {p.name for p in data.iterdir() if p.is_file() and p.name != 'evidence-index.json'}, 'audit file closure mismatch')
for name, pin in index.items():
    raw = (data / name).read_bytes()
    source_ci.require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256'], 'audit file hash/size mismatch: ' + name)
manifest = load('manifest.json')
for branch, identities in manifest['ruleset_ids'].items():
    expected_effective = []
    for layer, identity in identities.items():
        raw = load(branch + '-' + layer + '.json')
        checker.validate_ruleset(raw, repository=manifest['repository'], identity=identity, branch=branch, layer=layer)
        source_ci.require(checker.digest(raw) == manifest[branch + '_' + layer + '_readback_sha256'], 'raw ruleset identity/hash mismatch')
        for rule in raw['rules']:
            expected_effective.append(dict(type=rule['type'], parameters=rule.get('parameters'), ruleset_id=identity, ruleset_source=manifest['repository'], ruleset_source_type='Repository'))
    actual_effective = load(branch + '-effective.json')
    keys = expected_effective[0].keys()
    source_ci.require(Counter(checker.digest({key: row.get(key) for key in keys}) for row in actual_effective) == Counter(checker.digest(row) for row in expected_effective), 'effective rule union mismatch')
before, after = checker.payloads(load('main-hard.json'))
source_ci.require(before == load('before.json') and after == load('cutover.json'), 'complete payload mismatch')
source_ci.require(checker.digest(before) == manifest['main_hard_payload_sha256'] and checker.digest(after) == manifest['cutover_payload_sha256'], 'payload hash mismatch')
source_ci.require(manifest['applied'] is False and binding['complete_cutover_acceptance'] is False, 'audit authority changed')
print(json.dumps(dict(result='PASS', audit_files=len(index), full_fields=True,
    before_payload_sha256=checker.digest(before), cutover_payload_sha256=checker.digest(after),
    remote_request_made=False, applied=False, independent_live_bypass_certification=False)))
