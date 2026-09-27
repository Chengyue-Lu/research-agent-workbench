"""Checkpoint scheduling and production trigger contracts."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import ci_checkpoint as checkpoint


class CheckpointTests(unittest.TestCase):
    def test_git_content_changes_not_document_commits_drive_nightly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args]).decode().strip()
            git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'ci@example.invalid')
            (root/'src').mkdir(); (root/'src/a.py').write_text('x = 1\n')
            (root/'README.md').write_text('docs\n')
            def fingerprint():
                git('add', '.'); git('commit', '-qm', 'fixture')
                return checkpoint.content_fingerprint(root, git('rev-parse', 'HEAD'))
            first = fingerprint()
            (root/'README.md').write_text('more docs\n')
            self.assertEqual(first, fingerprint())
            (root/'src/a.py').write_text('x = 2\n')
            second = fingerprint(); self.assertNotEqual(first, second)
            (root/'requirements.txt').write_text('dependency==1\n')
            self.assertNotEqual(second, fingerprint())

    def test_only_successful_schedule_marker_suppresses_execution(self):
        run = dict(id=10, event='schedule', status='completed', conclusion='success',
                   path=checkpoint.WORKFLOW, repository={'full_name': 'Example/repo'})
        artifact = dict(name='nightly-content-abc', expired=False)
        class API:
            repository = 'Example/repo'
            def get(self, path): return {'workflow_runs': [run]}
            def pages(self, path, key): return [artifact]
        api = API()
        self.assertEqual(10, checkpoint.already_checked(api, 'abc'))
        self.assertIsNone(checkpoint.already_checked(api, 'other'))
        for field, bad in [('event', 'workflow_dispatch'), ('status', 'in_progress'),
                           ('conclusion', 'failure'), ('path', 'foreign.yml')]:
            old = run[field]; run[field] = bad
            with self.subTest(field=field): self.assertIsNone(checkpoint.already_checked(api, 'abc'))
            run[field] = old
        artifact['expired'] = True
        self.assertIsNone(checkpoint.already_checked(api, 'abc'))

    def test_workflows_separate_content_metadata_and_full_checkpoints(self):
        daily = yaml.load((ROOT/'.github/workflows/ci_components.yml').read_text(), Loader=yaml.BaseLoader)
        full = yaml.load((ROOT/checkpoint.WORKFLOW).read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(['develop'], daily['on']['pull_request']['branches'])
        self.assertNotIn('edited', daily['on']['pull_request']['types'])
        self.assertNotIn('ready_for_review', daily['on']['pull_request']['types'])
        self.assertNotIn('paths', daily['on']['pull_request'])
        self.assertEqual(['develop'], daily['on']['push']['branches'])
        self.assertEqual(['component', 'integration-smoke'], daily['on']['workflow_dispatch']['inputs']['profile']['options'])
        self.assertEqual('always()', daily['jobs']['result']['if'])
        self.assertEqual('CI result', daily['jobs']['result']['name'])
        self.assertNotIn('pull_request', full['on'])
        self.assertEqual('30 18 * * 0-4', full['on']['schedule'][0]['cron'])
        self.assertEqual('CI checkpoint result', full['jobs']['result']['name'])
        self.assertEqual('always()', full['jobs']['result']['if'])
        legacy = yaml.load((ROOT/'.github/workflows/ci.yml').read_text(), Loader=yaml.BaseLoader)
        governance = yaml.load((ROOT/'.github/workflows/ci-governance.yml').read_text(), Loader=yaml.BaseLoader)
        self.assertEqual(['main'], legacy['on']['pull_request']['branches'])
        self.assertEqual(['main', 'develop'], legacy['on']['push']['branches'])
        steps = {step.get('name'): step for step in governance['jobs']['governance']['steps'] if 'name' in step}
        component = steps['Bind develop metadata to the component content plan']
        self.assertIn("github.base_ref == 'develop'", component['if'])
        self.assertIn('ready_for_review', component['if'])
        self.assertIn('ci_component_metadata.py', component['run'])
        for name in ('Recompute legacy release obligations', 'Release metadata must retain a matching legacy content plan'):
            self.assertIn("github.base_ref != 'develop'", steps[name]['if'])
