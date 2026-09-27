"""Verify that the existing isolated smoke environment has exact candidate production bytes."""
import hashlib
import json
from pathlib import Path
import sys
import research_workbench
from research_workbench.evaluation.pins import EvaluationInputs

root = Path(__file__).resolve().parents[2]
installed = Path(research_workbench.__file__).parent
assert not installed.is_relative_to(root / 'src'), 'an isolated installed package is required'
count = 0
for source in (root / 'src/research_workbench').rglob('*.py'):
    name = source.relative_to(root / 'src/research_workbench')
    if str(name) == '_runtime_pin.py' or '_runtime_data' in name.parts: continue
    assert (installed / name).read_bytes() == source.read_bytes(), str(name)
    count += 1
assert EvaluationInputs(root).schema_hashes == EvaluationInputs(root, root / 'schemas').schema_hashes
print(json.dumps({'python': sys.version.split()[0], 'production_modules_equal': count,
    'schemas_equal': len(EvaluationInputs(root).schema_hashes), 'environment': 'existing isolated wheel environment',
    'new_product_sources': False, 'scope': 'production byte equality and short installed smoke; not a new wheel build'}))
