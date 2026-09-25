from __future__ import annotations

from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

from tests import test_release_surface as fixtures

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.github/scripts'))
import release_preflight as preflight
sys.path.pop(0)


class ReleasePreflightTests(unittest.TestCase):
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
        for path in preflight.TRUSTED_FILES:
            fixtures.write(self.root, path, (ROOT / path).read_bytes())
        self.fixture.update_source()
        self.expected = self.fixture.expected
        self.source = self.expected['source']
        self.parent = self.expected['parent']
        files = fixtures.release.project(self.root, self.expected)
        self.candidate, self.tree = self.fixture.candidate(files)
        self.manifest = fixtures.release.digest(files[fixtures.release.MANIFEST][1])
        self.observation = dict(source_ci=self.expected['source_ci'], observation={'run_attempt': 1}, merge_eligible=False)
        rows = {f'branches/{name}': dict(name=name, protected=True, commit={'sha': tip})
                for name, tip in [('main', self.parent), ('develop', self.source)]}
        self.rows = rows
        class API:
            repository = 'Example/workbench'
            def get(self, path):
                return deepcopy(rows[path])
        self.api = API()
        self.kwargs = dict(source=self.source, parent=self.parent, policy_version='1.0.0',
                           release_version='1.0.0', run_id=123, candidate=self.candidate,
                           manifest_sha256=self.manifest)

    def check(self, **changes):
        with patch.object(preflight.source_ci, 'attest', return_value=deepcopy(self.observation)) as live:
            result = preflight.check(self.root, self.api, **{**self.kwargs, **changes})
        return result, live

    def test_live_source_and_repeated_projection_bind_exact_candidate_without_authority(self):
        result, live = self.check()
        self.assertEqual(self.tree, result['projection']['tree'])
        self.assertEqual(self.manifest, result['projection']['manifest_sha256'])
        self.assertEqual(self.candidate, result['candidate'])
        self.assertFalse(result['merge_eligible'])
        self.assertEqual(2, live.call_count)
        self.assertEqual(self.source, fixtures.command(self.root, 'rev-parse', 'HEAD').decode().strip())
        self.assertEqual(b'', fixtures.command(self.root, 'status', '--porcelain'))

    def test_missing_live_success_blocks_before_any_projection(self):
        with patch.object(preflight.source_ci, 'attest', side_effect=ValueError('failed live CI')), \
             patch.object(preflight.surface, 'export') as export, self.assertRaisesRegex(ValueError, 'failed live CI'):
            preflight.check(self.root, self.api, **self.kwargs)
        export.assert_not_called()

    def test_independent_pins_reject_manifest_self_claims_and_wrong_candidate(self):
        for changes, message in [({'manifest_sha256': 'f' * 64}, 'independent manifest'),
                                  ({'candidate': self.source}, 'expected current main parent'),
                                  ({'parent': self.source}, 'current main parent drift'),
                                  ({'manifest_sha256': 'F' * 64}, 'exact manifest'),
                                  ({'manifest_sha256': None}, 'exact manifest'),
                                  ({'manifest_sha256': 'ab'}, 'exact manifest')]:
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, message):
                self.check(**changes)

    def test_missing_protection_wrong_name_or_stale_refs_block(self):
        for name in ('develop', 'main'):
            for change in ({'protected': False}, {'name': 'foreign'}, {'commit': {'sha': 'f' * 40}}):
                with self.subTest(name=name, change=change), patch.dict(self.rows[f'branches/{name}'], change), \
                     self.assertRaises(ValueError):
                    self.check()

    def test_dirty_checkout_or_checker_drift_cannot_provide_trust(self):
        path = self.root / preflight.TOOL
        path.write_bytes(path.read_bytes() + b'# drift\n')
        with self.assertRaisesRegex(ValueError, 'clean'):
            self.check()
        self.fixture.update_source()
        self.rows['branches/develop']['commit']['sha'] = self.fixture.expected['source']
        with self.assertRaisesRegex(ValueError, 'checker byte drift'):
            self.check(source=self.fixture.expected['source'])

    def test_projection_mismatch_and_candidate_mismatch_are_rejected(self):
        real_export = preflight.surface.export
        calls = []
        def changed_export(*args):
            result = real_export(*args)
            calls.append(result)
            return {**result, 'tree': 'f' * 40} if len(calls) == 2 else result
        with patch.object(preflight.surface, 'export', side_effect=changed_export), \
             self.assertRaisesRegex(ValueError, 'repeated projection'):
            self.check()
        with patch.object(preflight.surface, 'check', return_value={}), \
             self.assertRaisesRegex(ValueError, 'candidate differs'):
            self.check()

    def test_ref_and_ci_races_cannot_publish_a_success(self):
        real_refs = preflight.current_refs
        calls = []
        def changed_refs(*args):
            result = real_refs(*args)
            calls.append(result)
            return {**result, 'develop': 'f' * 40} if len(calls) == 2 else result
        with patch.object(preflight, 'current_refs', side_effect=changed_refs), \
             self.assertRaisesRegex(ValueError, 'refs changed'):
            self.check()
        changed = deepcopy(self.observation); changed['observation']['run_attempt'] = 2
        with patch.object(preflight.source_ci, 'attest', side_effect=[self.observation, changed]), \
             self.assertRaisesRegex(ValueError, 'CI changed'):
            preflight.check(self.root, self.api, **self.kwargs)

    def test_cli_publishes_only_after_success_and_never_overwrites(self):
        output = self.fixture.base / 'report.json'
        args = ['--repository', self.api.repository, '--output', str(output)]
        for key, value in self.kwargs.items():
            args += ['--' + key.replace('_', '-'), str(value)]
        with patch.object(preflight, 'ROOT', self.root), \
             patch.object(preflight.source_ci, 'GitHub', return_value=self.api), \
             patch.object(preflight.source_ci, 'attest', side_effect=ValueError('blocked')), \
             self.assertRaisesRegex(ValueError, 'blocked'):
            preflight.main(args)
        self.assertFalse(output.exists())
        with patch.object(preflight, 'ROOT', self.root), \
             patch.object(preflight.source_ci, 'GitHub', return_value=self.api), \
             patch.object(preflight.source_ci, 'attest', return_value=self.observation), redirect_stdout(io.StringIO()):
            self.assertEqual(0, preflight.main(args))
        self.assertFalse(json.loads(output.read_text())['merge_eligible'])
        with self.assertRaisesRegex(ValueError, 'already exists'):
            preflight.main(args)

    def test_script_entrypoint_exposes_required_independent_pins(self):
        with patch.object(sys, 'argv', [preflight.TOOL, '--help']), redirect_stdout(io.StringIO()) as output, \
             self.assertRaises(SystemExit) as result:
            runpy.run_path(str(ROOT / preflight.TOOL), run_name='__main__')
        self.assertEqual(0, result.exception.code)
        self.assertIn('--manifest-sha256', output.getvalue())
        self.assertIn('--run-id', output.getvalue())


if __name__ == '__main__':
    unittest.main()
