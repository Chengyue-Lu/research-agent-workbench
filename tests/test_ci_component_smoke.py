"""Bounded regression checks for the installed smoke runner's failure contract."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/ci_component_smoke.py"
SPEC = importlib.util.spec_from_file_location("ci_component_smoke", SCRIPT)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


class ComponentSmokeTests(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt', 'POSIX venv interpreter symlink regression')
    def test_cli_preserves_venv_interpreter_symlink(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            link = root / 'python'
            link.symlink_to(sys.executable)
            with patch.object(smoke, 'smoke', return_value={'status':'success','elapsed_seconds':0}) as probe:
                self.assertEqual(0, smoke.main(['--python', str(link), '--output', str(root/'report.json')]))
            probe.assert_called_once_with(link.absolute(), timeout=120)

    def step(self, code, **kwargs):
        return smoke.run_step("control", [sys.executable, "-I", "-c", code],
                              cwd=SCRIPT.parent, env=os.environ.copy(), timeout=5, **kwargs)

    def test_negative_requires_exact_exit_and_expected_diagnostic(self):
        self.assertEqual("success", self.step("print('timestamp');raise SystemExit(1)",
                         expected=1, needle="timestamp")["status"])
        for code in ("print('timestamp')", "print('timestamp');raise SystemExit(2)",
                     "raise SystemExit(1)"):
            with self.subTest(code=code):
                self.assertEqual("failure", self.step(code, expected=1, needle="timestamp")["status"])

    def test_timeout_is_failure(self):
        result = smoke.run_step("slow", [sys.executable, "-I", "-c", "import time;time.sleep(5)"],
                                cwd=SCRIPT.parent, env=os.environ.copy(), timeout=0.1)
        self.assertEqual("failure", result["status"])
        self.assertIn("budget", result["reason"])

    def test_missing_interpreter_writes_failure_and_stops_before_dependent_steps(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "report.json"
            self.assertEqual(1, smoke.main(["--python", str(root / "missing-python"),
                                           "--output", str(output)]))
            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual("failure", report["status"])
        self.assertEqual(1, len(report["steps"]))
        self.assertEqual("installed-import-and-schema", report["steps"][0]["name"])


if __name__ == "__main__":
    unittest.main()
