from __future__ import annotations

import re
import unittest
from pathlib import Path

from research_workbench.contracts.risk_codes import (
    EXECUTION_ARCHIVE_RISK_CODES,
    EXECUTION_TRACE_RISK_CODES,
    RECOVERY_RISK_CODES,
    TRACE_RISK_CODES,
)

ROOT = Path(__file__).resolve().parents[1]


class TraceRiskCodeTests(unittest.TestCase):
    def test_every_emitted_trace_code_is_registered(self) -> None:
        source = (ROOT / "src/research_workbench/observability/trace.py").read_text(encoding="utf-8")
        emitted = frozenset(re.findall(r'"(TRACE-[A-Z0-9-]+)"', source))
        self.assertEqual(TRACE_RISK_CODES, emitted)

    def test_registry_exactly_matches_canonical_module_vocabulary(self) -> None:
        module = (ROOT / "docs/modules/07-ARTIFACTS_AND_PROVENANCE.md").read_text(encoding="utf-8")
        warning_section = module.split("## 9. 预警", 1)[1].split("## 10. 验收条件", 1)[0]
        documented = frozenset(re.findall(r"`(TRACE-[A-Z0-9-]+)`", warning_section))
        self.assertEqual(documented, TRACE_RISK_CODES)

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

    def test_every_execution_trace_link_code_is_registered_separately(self) -> None:
        source = (ROOT / "src/research_workbench/observability/models.py").read_text(
            encoding="utf-8"
        )
        emitted = frozenset(re.findall(r'"(RECEIPT-TRACE-[A-Z0-9-]+)"', source))
        self.assertEqual(EXECUTION_TRACE_RISK_CODES, emitted)

    def test_every_execution_archive_code_is_registered_separately(self) -> None:
        source = (ROOT / "src/research_workbench/execution/archive.py").read_text(
            encoding="utf-8"
        )
        emitted = frozenset(re.findall(r'"(EXEC-[A-Z0-9-]+)"', source))
        self.assertEqual(EXECUTION_ARCHIVE_RISK_CODES, emitted)

    def test_every_recovery_code_is_registered_separately(self) -> None:
        source = (ROOT / "src/research_workbench/execution/recovery.py").read_text(
            encoding="utf-8"
        )
        emitted = frozenset(re.findall(r'"(RECOVERY-[A-Z0-9-]+)"', source))
        self.assertEqual(RECOVERY_RISK_CODES, emitted)


if __name__ == "__main__":
    unittest.main()
