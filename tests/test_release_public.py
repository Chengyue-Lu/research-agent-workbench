from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import yaml

from tests import test_release_surface as fixtures


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_public as public
sys.path.pop(0)


class ReleasePublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.ReleaseSurfaceTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        fixtures.ReleaseSurfaceTests.tearDownClass()

    def setUp(self):
        self.fixture = fixtures.ReleaseSurfaceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.repo
        fixtures.write(self.root, public.TOOL, (ROOT / public.TOOL).read_bytes())
        self.fixture.update_source()
        self.source = self.fixture.expected['source']
        self.files = {name: ('100644', b'# Public page\n') for name in public.PUBLIC_PAGES}
        self.files['README.md'] = ('100644', b'# Public page\n\n[Guide](docs/GETTING_STARTED.md#public-page)\n')
        for name in ('pyproject.toml', 'MANIFEST.in', 'LICENSE', 'build_backend.py'):
            self.files[name] = ('100644', b'public build input\n')
        self.files['runtime-resources.json'] = ('100644', b'{"catalogs": [], "release_assets": []}\n')
        self.files['src/never-run.py'] = ('100644', b'raise RuntimeError("candidate executed")\n')

    def run_check(self, files=None):
        candidate, _ = self.fixture.candidate(files or self.files)
        with patch.object(public, 'ROOT', self.root):
            return public.check(self.root, 'Example/workbench', self.source, candidate)

    def test_exact_candidate_blobs_pass_without_execution_or_merge_authority(self):
        result = self.run_check()
        self.assertEqual(self.source, result['source'])
        self.assertEqual(len(self.files), result['files_checked'])
        self.assertFalse(result['merge_eligible'])
        self.assertFalse((self.root / 'src/never-run.py').exists())

    def test_links_build_inputs_and_internal_paths_fail_closed(self):
        for mutate, message in [
            (lambda f: f.__setitem__('README.md', ('100644', b'[broken](missing.md)\n')), 'missing link'),
            (lambda f: f.__setitem__('README.md', ('100644', b'[internal](docs/TASKS.md)\n')), 'internal'),
            (lambda f: f.pop('LICENSE'), 'missing build input'),
            (lambda f: f.__setitem__('tests/private.py', ('100644', b'pass\n')), 'internal candidate path'),
        ]:
            with self.subTest(message=message):
                files = copy.deepcopy(self.files)
                mutate(files)
                with self.assertRaisesRegex(ValueError, message):
                    self.run_check(files)

    def test_dirty_source_and_checker_drift_block(self):
        (self.root / 'untracked.txt').write_text('dirty', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'clean'):
            self.run_check()
        (self.root / 'untracked.txt').unlink()
        real_git = public.surface.git
        def drift(root, *args):
            if args == ('show', f'{self.source}:{public.TOOL}'):
                return b'# different checker\n'
            return real_git(root, *args)
        with patch.object(public.surface, 'git', side_effect=drift), \
             self.assertRaisesRegex(ValueError, 'byte drift'):
            self.run_check()

    def test_cli_creates_only_a_success_receipt_and_refuses_overwrite(self):
        output = self.fixture.base / 'public-result.json'
        bad = copy.deepcopy(self.files)
        bad['README.md'] = ('100644', b'[missing](absent.md)\n')
        bad_candidate, _ = self.fixture.candidate(bad)
        def args(candidate):
            return ['--repository', 'Example/workbench', '--source', self.source,
                    '--candidate', candidate, '--output', str(output)]
        with patch.object(public, 'ROOT', self.root), self.assertRaisesRegex(ValueError, 'missing link'):
            public.main(args(bad_candidate))
        self.assertFalse(output.exists())
        good_candidate, _ = self.fixture.candidate(self.files)
        with patch.object(public, 'ROOT', self.root):
            self.assertEqual(0, public.main(args(good_candidate)))
            self.assertFalse(json.loads(output.read_text(encoding='utf-8'))['merge_eligible'])
            with self.assertRaisesRegex(ValueError, 'output already exists'):
                public.main(args(good_candidate))

    def test_policy_adds_exact_release_files_without_rewriting_old_versions(self):
        policy = json.loads((ROOT / '.github/release-surface.yml').read_text(encoding='utf-8'))
        self.assertEqual(['1.0.0', '1.1.0', '1.2.0', '1.3.0'],
                         [item['version'] for item in policy['policies']])
        old = json.dumps(policy['policies'][:3], sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
        self.assertEqual('3f5dc8637765ca2567427c31d26dc046c08d2577a8c4f87401977091f51b2156',
                         hashlib.sha256(old).hexdigest())
        additions = {item['path'] for item in policy['policies'][-1]['include']} - {
            item['path'] for item in policy['policies'][-2]['include']}
        self.assertEqual({'.github/workflows/release.yml', public.TOOL}, additions)

    def test_first_main_workflow_keeps_candidate_as_data_and_has_no_required_gate_name(self):
        workflow = yaml.load((ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8'),
                             Loader=yaml.BaseLoader)
        self.assertEqual(['main'], workflow['on']['pull_request']['branches'])
        self.assertNotIn('pull_request_target', workflow['on'])
        job = workflow['jobs']['preflight']
        self.assertEqual('release preflight (diagnostic)', job['name'])
        checkout = next(step for step in job['steps'] if step.get('uses', '').startswith('actions/checkout@'))
        self.assertEqual('${{ vars.RWB_RELEASE_SOURCE_SHA }}', checkout['with']['ref'])
        self.assertEqual('false', checkout['with']['persist-credentials'])
        runs = '\n'.join(step['run'] for step in job['steps'] if 'run' in step)
        self.assertIn('refs/pull/${PR_NUMBER}/head:refs/remotes/origin/rwb-release-candidate', runs)
        self.assertIn('release_preflight.py', runs)
        self.assertIn('release_public.py', runs)
        self.assertNotIn('checkout@', runs)


if __name__ == '__main__':
    unittest.main()
