"""The release install diagnostic must bind its build to a trusted projection."""
from __future__ import annotations

import json
from pathlib import Path
from contextlib import redirect_stderr
import io
import runpy
import sys
import unittest
from unittest.mock import patch

from tests import test_release_surface as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_install as installation
sys.path.pop(0)


class ReleaseInstallTests(unittest.TestCase):
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
        for path in (installation.TOOL, installation.PACKAGE_TOOL, installation.governance.TOOL):
            fixtures.write(self.root, path, (ROOT / path).read_bytes())
        self.fixture.update_source()
        self.expected = self.fixture.expected
        files = fixtures.release.project(self.root, self.expected)
        self.candidate, _ = self.fixture.candidate(files)
        self.projection = {'tree': fixtures.release.tree_id(files),
                           'manifest_sha256': fixtures.release.digest(files[fixtures.release.MANIFEST][1]),
                           'files': len(files), 'merge_eligible': False}
        self.trusted = {'projection': self.projection, 'source_ci': self.expected['source_ci'],
                        'protected_refs': {'develop': self.expected['source'], 'main': self.expected['parent']},
                        'observation': {'run_attempt': 1, 'repository_id': 42}, 'merge_eligible': False}
        self.api = type('API', (), {'repository': 'Example/workbench'})()
        self.kwargs = dict(source=self.expected['source'], parent=self.expected['parent'],
                           policy_version='1.0.0', release_version='1.0.0', run_id=123,
                           candidate=self.candidate, manifest_sha256=self.projection['manifest_sha256'],
                           interpreter=sys.executable, pr_number=7)
        self.pr_check = patch.object(installation.governance, 'check', return_value={
            'governance': 'success', 'merge_eligible': False})
        self.pr_check.start()
        self.addCleanup(self.pr_check.stop)
        self.pr_reobserve = patch.object(installation.governance, 'reobserve')
        self.pr_reobserve.start()
        self.addCleanup(self.pr_reobserve.stop)
        self.package = {'runtime_resources_identical': True,
                        'installs': [{'python': '3.11', 'route': route, 'isolated': isolated}
                                     for route in ('direct', 'sdist-wheel') for isolated in (True, False)],
                        'merge_eligible': False}

    def bound(self):
        return (patch.object(installation.preflight, 'check', return_value=self.trusted),
                patch.object(installation.public, 'check',
                             return_value={'build_inputs': 'success', 'merge_eligible': False}),
                patch.object(installation.portable, 'check', return_value=self.package),
                patch.object(installation.preflight, 'current_refs', return_value=self.trusted['protected_refs']),
                patch.object(installation.source_ci, 'attest_contract',
                             return_value={'observation': self.trusted['observation']}),
                patch.object(installation.source_ci, 'active_contract', return_value={}))

    def test_exact_candidate_projection_is_built_only_after_preflight_and_public_checks(self):
        observed = {}
        order = []
        with self.bound()[0] as preflight, self.bound()[1] as public, \
             self.bound()[2] as package, self.bound()[3], self.bound()[4], self.bound()[5]:
            preflight.side_effect = lambda *args, **kwargs: order.append('preflight') or self.trusted
            public.side_effect = lambda *args, **kwargs: order.append('public') or {
                'build_inputs': 'success', 'merge_eligible': False}
            def inspect(source, interpreters):
                order.append('package')
                observed['outside'] = not source.is_relative_to(self.root)
                observed['bytes'] = (source / 'src/run.py').read_bytes()
                observed['interpreters'] = interpreters
                return self.package
            package.side_effect = inspect
            result = installation.check(self.root, self.api, **self.kwargs)
        self.assertEqual(self.candidate, result['candidate'])
        self.assertFalse(result['merge_eligible'])
        self.assertEqual(4, len(result['package']['installs']))
        self.assertEqual(['preflight', 'public', 'package'], order)
        preflight.assert_called_once()
        public.assert_called_once()
        self.assertTrue(observed['outside'])
        self.assertEqual((self.root / 'src/run.py').read_bytes(), observed['bytes'])
        self.assertEqual([sys.executable], observed['interpreters'])

    def test_missing_trust_public_closure_or_script_identity_prevents_build(self):
        for failure in ('preflight', 'public', 'script'):
            with self.subTest(failure=failure):
                mocks = self.bound()
                with mocks[0] as preflight, mocks[1] as public, mocks[2] as package, \
                     mocks[3], mocks[4], mocks[5]:
                    if failure == 'preflight':
                        preflight.side_effect = ValueError('missing source CI')
                    elif failure == 'public':
                        public.side_effect = ValueError('internal candidate path')
                    else:
                        (self.root / installation.PACKAGE_TOOL).write_text('drift', encoding='utf-8')
                    with self.assertRaisesRegex(ValueError, 'missing source CI|internal candidate path|byte drift'):
                        installation.check(self.root, self.api, **self.kwargs)
                    package.assert_not_called()
                if failure == 'script':
                    (self.root / installation.PACKAGE_TOOL).write_bytes((ROOT / installation.PACKAGE_TOOL).read_bytes())

    def test_changed_candidate_and_changed_refs_fail_closed(self):
        for failure in ('candidate', 'refs'):
            with self.subTest(failure=failure):
                mocks = self.bound()
                with mocks[0], mocks[1], mocks[2] as package, mocks[3] as refs, mocks[4], mocks[5]:
                    kwargs = dict(self.kwargs)
                    if failure == 'candidate':
                        kwargs['candidate'], _ = self.fixture.candidate({'unexpected': ('100644', b'bad')})
                    else:
                        refs.return_value = {'develop': '0' * 40, 'main': kwargs['parent']}
                    with self.assertRaisesRegex(ValueError, 'unexpected|changed during install'):
                        installation.check(self.root, self.api, **kwargs)
                    self.assertEqual(failure == 'refs', package.called)

    def test_governance_failure_prevents_build_and_metadata_drift_prevents_receipt(self):
        for phase in ('check', 'reobserve'):
            mocks = self.bound()
            with (self.subTest(phase=phase), mocks[0], mocks[1], mocks[2] as package,
                  mocks[3], mocks[4], mocks[5],
                  patch.object(installation.governance, phase, side_effect=ValueError('PR governance drift'))):
                with self.assertRaisesRegex(ValueError, 'PR governance drift'):
                    installation.check(self.root, self.api, **self.kwargs)
                self.assertEqual(phase == 'reobserve', package.called)

    def test_ci_rerun_and_incomplete_or_authorizing_install_fail_closed(self):
        for failure in ('rerun', 'missing-route', 'authority'):
            with self.subTest(failure=failure):
                mocks = self.bound()
                with mocks[0], mocks[1], mocks[2] as package, mocks[3], mocks[4] as attestation, mocks[5]:
                    if failure == 'rerun':
                        attestation.return_value = {'observation': {'run_attempt': 2, 'repository_id': 42}}
                    elif failure == 'missing-route':
                        package.return_value = {**self.package, 'installs': self.package['installs'][:-1]}
                    else:
                        package.return_value = {**self.package, 'merge_eligible': True}
                    with self.assertRaisesRegex(ValueError, 'source CI changed|both clean-install routes|merge authority'):
                        installation.check(self.root, self.api, **self.kwargs)

    def test_cli_writes_only_complete_non_authorizing_receipt(self):
        output = self.fixture.base / 'release-install.json'
        arguments = [option for key, value in self.kwargs.items() for option in
                     ('--' + ('python' if key == 'interpreter' else key.replace('_', '-')), str(value))]
        arguments += ['--repository', self.api.repository, '--output', str(output)]
        mocks = self.bound()
        with patch.object(installation, 'ROOT', self.root), \
             patch.object(installation.source_ci, 'GitHub', return_value=self.api), \
             mocks[0], mocks[1], mocks[2] as package, mocks[3], mocks[4], mocks[5]:
            package.side_effect = RuntimeError('install failed')
            with self.assertRaisesRegex(RuntimeError, 'install failed'):
                installation.main(arguments)
            self.assertFalse(output.exists())
            package.side_effect = None
            package.return_value = self.package
            self.assertEqual(0, installation.main(arguments))
            self.assertFalse(json.loads(output.read_text(encoding='utf-8'))['merge_eligible'])
            with self.assertRaisesRegex(ValueError, 'output already exists'):
                installation.main(arguments)

    def test_entrypoint_requires_independent_pins(self):
        with patch.object(sys, 'argv', ['release_install.py']), \
             redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            runpy.run_path(str(ROOT / installation.TOOL), run_name='__main__')
        self.assertEqual(2, error.exception.code)


if __name__ == '__main__':
    unittest.main()
