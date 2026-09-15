# Evidence helper source

```python
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path.cwd() / '.github/scripts'))
from release_source_ci import GitHub, attest

OUT = Path('.rwb/m14-source-ci')
observations = []

class Recorder(GitHub):
    def get(self, path):
        value = super().get(path)
        keys = ['id', 'full_name', 'name', 'path', 'state', 'event', 'head_sha', 'head_branch',
                'status', 'conclusion', 'run_attempt', 'workflow_id', 'check_suite_id', 'total_count']
        summary = {key: value[key] for key in keys if key in value}
        for name in ('repository', 'head_repository'):
            if name in value:
                summary[name] = {key: value[name][key] for key in ('id', 'full_name')}
        if 'jobs' in value:
            summary['jobs'] = [{key: job[key] for key in [*keys, 'run_id', 'check_run_url'] if key in job}
                               for job in value['jobs']]
        observations.append({'path': path, 'observed_at': datetime.now(timezone.utc).isoformat(), 'response': summary})
        return value

try:
    attest(Recorder('Chengyue-Lu/research-agent-workbench'), '0bebafd81f0116a8269c63ac97378038a1eb2a5d', 34939526577)
except ValueError as error:
    assert str(error) == 'missing or ambiguous source job: governance', str(error)
    result = {'control': 'live historical green develop push', 'expected_rejection': str(error),
              'result': 'PASS', 'release_eligible': False, 'observations': observations}
else:
    raise AssertionError('Historical run without governance was accepted')
(OUT / 'live-negative.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps({key: value for key, value in result.items() if key != 'observations'}))

```
