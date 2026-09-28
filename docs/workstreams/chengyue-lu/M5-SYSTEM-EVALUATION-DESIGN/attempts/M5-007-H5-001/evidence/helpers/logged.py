"""Local command evidence recorder; no credentials/environment capture."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

p = argparse.ArgumentParser()
p.add_argument('name')
p.add_argument('command', nargs=argparse.REMAINDER)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
dest = root / 'docs/workstreams/chengyue-lu/M5-SYSTEM-EVALUATION-DESIGN/attempts/M5-007-H5-001/evidence'
dest.mkdir(parents=True, exist_ok=True)
if (dest / (a.name + '.command.json')).exists():
    raise SystemExit('evidence name already exists')
start = datetime.now(timezone.utc).isoformat()
begin = time.monotonic()
sys_environment = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
result = subprocess.run(a.command, cwd=root, env=sys_environment, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(dest / (a.name + '.log')).write_bytes(result.stdout)
(dest / (a.name + '.command.json')).write_text(json.dumps({
    'command': a.command, 'cwd': '.', 'started_at': start,
    'ended_at': datetime.now(timezone.utc).isoformat(),
    'elapsed_seconds': time.monotonic() - begin, 'exit_code': result.returncode,
    'output_path': a.name + '.log', 'capture': 'native-command-only',
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
print(result.stdout.decode('utf-8', errors='replace'))
raise SystemExit(result.returncode)
