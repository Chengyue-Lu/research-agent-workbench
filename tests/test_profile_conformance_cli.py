"""Public v2 preparation entry stays offline and never replaces an output."""

from __future__ import annotations

from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research_workbench.cli import main

ROOT = Path(__file__).resolve().parents[1]


class ProfileConformanceCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'plan.json'
        self.config = ROOT / 'registry/providers/adapters-v2.disabled.json'
        # Discover only the already-declared disabled local configuration.
        from research_workbench.adapters.models.profile_configuration import load_profile_configurations
        configs = load_profile_configurations(self.config)
        self.adapter = next(config.adapter_id for config in configs if 'deepseek' in config.adapter_id)
        document = json.loads(self.config.read_text(encoding='utf-8'))
        selected = next(item for item in document['adapters'] if item['adapter_id'] == self.adapter)
        selected['capabilities'] = ['text', 'tools', 'structured_output']
        selected['enabled'] = True
        self.full_config = Path(self.temp.name) / 'explicit-capabilities.json'
        self.full_config.write_text(json.dumps(document), encoding='utf-8')

    def args(self):
        return ['providers', 'profile-conformance', '--config', str(self.config),
                '--adapter', self.adapter, '--root', str(ROOT)]

    def invoke(self, extra=(), *, full_capabilities=False):
        out = io.StringIO()
        args = self.args()
        if full_capabilities:
            args[args.index('--config') + 1] = str(self.full_config)
        with redirect_stdout(out), patch('research_workbench.adapters.models.http.EnvironmentCredential.resolve', side_effect=AssertionError('no secret read')), patch('research_workbench.adapters.models.http.EnvironmentCredential.available', side_effect=AssertionError('no presence probe')), patch('research_workbench.adapters.models.http.UrllibTransport.send', side_effect=AssertionError('no provider request')):
            code = main([*args, *extra])
        return code, out.getvalue()

    def test_disabled_template_has_offline_plan_without_execution_authority(self):
        code, output = self.invoke()
        self.assertEqual(code, 1)
        plan = json.loads(output)
        self.assertFalse(plan['config_enabled'])
        self.assertFalse(plan['live_qualified'])
        self.assertEqual(plan['max_provider_invocations'], 3)
        self.assertEqual(plan['max_tool_executions'], 1)
        self.assertEqual(plan['readiness'], 'blocked')
        self.assertEqual(set(plan['missing_capabilities']), {'tools', 'structured_output'})

    def test_explicit_enabled_capabilities_plan_still_has_no_live_qualification(self):
        code, output = self.invoke(full_capabilities=True)
        self.assertEqual(code, 0)
        plan = json.loads(output)
        self.assertEqual(plan['readiness'], 'ready')
        self.assertTrue(plan['config_enabled'])
        self.assertFalse(plan['live_qualified'])

    def test_writes_only_fresh_json_plan(self):
        code, output = self.invoke(['--output', str(self.output)], full_capabilities=True)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.output.read_text(encoding='utf-8')), json.loads(output))
        original = self.output.read_bytes()
        code, _ = self.invoke(['--output', str(self.output)], full_capabilities=True)
        self.assertEqual(code, 2)
        self.assertEqual(self.output.read_bytes(), original)

    def test_unknown_adapter_does_not_create_output(self):
        args = self.args()
        args[args.index('--adapter') + 1] = 'undeclared-adapter'
        with redirect_stdout(io.StringIO()):
            code = main([*args, '--output', str(self.output)])
        self.assertEqual(code, 2)
        self.assertFalse(self.output.exists())

    def test_bad_limit_does_not_create_output(self):
        code, _ = self.invoke(['--max-output-tokens', '257', '--output', str(self.output)])
        self.assertEqual(code, 2)
        self.assertFalse(self.output.exists())

    def test_no_execute_switch(self):
        with self.assertRaises(SystemExit) as raised, redirect_stdout(io.StringIO()), patch('sys.stderr', io.StringIO()):
            main([*self.args(), '--execute'])
        self.assertEqual(raised.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
