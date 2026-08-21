from __future__ import annotations

import re
import unittest
from pathlib import Path

from research_workbench.contracts.risk_codes import TRACE_RISK_CODES

ROOT = Path(__file__).resolve().parents[1]


class TraceRiskCodeTests(unittest.TestCase):
    def test_every_emitted_trace_code_is_registered(self) -> None:
        source = (ROOT / "src/research_workbench/observability/trace.py").read_text(encoding="utf-8")
        emitted = frozenset(re.findall(r'"(TRACE-[A-Z0-9-]+)"', source))
        self.assertEqual(TRACE_RISK_CODES, emitted)

    def test_trace_core_has_no_method_or_skill_decision_semantics(self) -> None:
        paths = [
            ROOT / "src/research_workbench/observability/trace.py",
            *sorted((ROOT / "schemas/v0.1.0").glob("agent-trace-*.schema.json")),
        ]
        source = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for forbidden in (
            "MethodResolution",
            "ModeAction",
            "DecisionAuthority",
            "METHOD-RESOLUTION-REQUIRED",
            "skill_assignment_ref",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
