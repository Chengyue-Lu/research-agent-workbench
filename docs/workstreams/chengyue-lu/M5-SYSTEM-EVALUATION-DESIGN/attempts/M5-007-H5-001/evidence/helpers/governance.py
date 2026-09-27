import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
body = (root / 'work/m5-h5/PR_BODY.md').read_text(encoding='utf-8')
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root).decode().strip()
repo = {'full_name': 'Chengyue-Lu/research-agent-workbench', 'owner': {'login': 'Chengyue-Lu'}}
event = {'pull_request': {'body': body, 'number': 0, 'user': {'login': 'Chengyue-Lu'}, 'draft': True,
    'base': {'ref': 'develop', 'sha': '24e1a3eb5d503e56868a10d5222b79ad544e3f86', 'repo': repo},
    'head': {'ref': 'feature/m5-007-harness-proof', 'sha': sha, 'repo': repo}, 'mergeable': True},
    'repository': repo}
spec = importlib.util.spec_from_file_location('h5_governance', root / '.github/scripts/check_pr_governance.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
os.chdir(root)
report = module.check_pull_request(event)
report.emit()
raise SystemExit(1 if report.has_errors else 0)
