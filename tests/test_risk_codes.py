import re
import unittest
from pathlib import Path

from research_workbench.contracts.risk_codes import (
    DOCUMENTED_GAP,
    NOT_YET_EMITTED,
    RISK_CODE_REGISTRY,
)

ROOT = Path(__file__).resolve().parents[1]
CODE_LITERAL = re.compile(r"[\"']([A-Z][A-Z0-9]+(?:-[A-Z0-9]+)+)[\"']")


def emitted_codes() -> set[str]:
    found: set[str] = set()
    for source in (ROOT / "src").rglob("*.py"):
        # The registry itself lists codes as data, not as emission sites.
        if source.name == "risk_codes.py":
            continue
        found.update(CODE_LITERAL.findall(source.read_text(encoding="utf-8")))
    return found


class RiskCodeRegistryTests(unittest.TestCase):
    def test_emitted_codes_are_registered(self) -> None:
        registered = {entry.code for entry in RISK_CODE_REGISTRY}
        registered.update(entry.code for entry in NOT_YET_EMITTED)
        self.assertEqual([], sorted(emitted_codes() - registered))

    def test_registry_codes_are_unique(self) -> None:
        codes = [entry.code for entry in (*RISK_CODE_REGISTRY, *NOT_YET_EMITTED)]
        self.assertEqual(len(codes), len(set(codes)))

    def test_documented_gap_lists_emitted_codes_without_doc_table(self) -> None:
        expected = {
            entry.code
            for entry in RISK_CODE_REGISTRY
            if entry.status == "emitted" and not entry.docs
        }
        self.assertEqual(expected, set(DOCUMENTED_GAP))

    def test_not_yet_emitted_codes_have_no_emission_site(self) -> None:
        documented = {entry.code for entry in NOT_YET_EMITTED}
        self.assertEqual([], sorted(emitted_codes() & documented))

    def test_emitted_entries_declare_severity_modules_and_summary(self) -> None:
        incomplete = [
            entry.code
            for entry in RISK_CODE_REGISTRY
            if entry.status == "emitted"
            and (not entry.severity or not entry.modules or not entry.summary)
        ]
        self.assertEqual([], incomplete)


if __name__ == "__main__":
    unittest.main()
