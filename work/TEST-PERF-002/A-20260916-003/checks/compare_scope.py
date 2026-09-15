import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
# All worktrees share this repository's Git object store; never read M6 worktree files.
M6 = ROOT
BASE = '7b1323f5e9d91c304b6d5cfc89b7ea0e87f7c5ba'
HEAD = '34cc426e9c08d837ffc2e6dc58732c08a659291e'
OLD = '3fe8b1d97559465786640381d11754dce9ff4d65'
raw = subprocess.check_output(['git', 'show', OLD + ':.github/scripts/ci_dependencies.py'], cwd=ROOT)
(OUT / 'before_dependencies.py').write_bytes(raw)
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
before = load('before_deps', OUT / 'before_dependencies.py')
after = load('after_deps', ROOT / '.github/scripts/ci_dependencies.py')
sys.path.insert(0, str(ROOT))
from tests import test_ci_dependencies as regression
regression.deps = before
log = io.StringIO()
suite = unittest.TestSuite(regression.DependencyTests(name) for name in (
    'test_rooted_resource_inputs_exclude_unrelated_schema_and_follow_inventory',
    'test_rooted_run_path_follows_script_imports_and_rejects_uncertain_execution',
    'test_rooted_consumers_remain_selected_when_actual_input_breaks'))
result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
assert result.failures and not result.errors
(OUT / 'before-failures.log').write_text(log.getvalue(), encoding='utf-8')
regression.deps = after
seeds = set(subprocess.check_output(['git', 'diff', '--name-only', BASE, HEAD], cwd=M6).decode().splitlines())
seeds = {p for p in seeds if not p.startswith('work/') and p != 'tests/coverage_policy.yaml'}
rows = {}
for label, module in [('before', before), ('after', after)]:
    readers, opaque = set(), set()
    for commit in (BASE, HEAD):
        _, dynamic, resources, _ = module.commit_graph(M6, commit)
        readers.update(resources)
        opaque.update(dynamic)
    selected = module.select(M6, BASE, HEAD, seeds)[0]
    rows[label] = {'test_modules': len(selected['selected']), 'unbounded_resource_consumers': sorted(readers),
                   'opaque_consumers': sorted(opaque), 'selected_edge_kinds': selected['selected_edge_kinds']}
removed = sorted(set(rows['before']['unbounded_resource_consumers']) - set(rows['after']['unbounded_resource_consumers']))
report = {'m6_base': BASE, 'm6_head': HEAD, 'pr83_before': OLD, 'before_failures': len(result.failures),
          'scope': rows, 'resource_consumers_now_bounded': removed,
          'interpretation': 'M6 still has shared validation and unresolved helper inputs. Fixed roots remove direct fallback edges, not the complete independent paths. These are Git graph comparisons, not hosted time savings.'}
(OUT / 'scope-comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'before_failures': len(result.failures), 'counts': {k: (v['test_modules'],len(v['unbounded_resource_consumers'])) for k,v in rows.items()},
                  'resource_consumers_now_bounded': removed}, indent=2))
