"""M4-003 claim trace one-shot localization tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.cli import main

EVIDENCE = """schema_version: 0.1.0
object_type: evidence
object_id: EVID-001-01
revision: 1
status: admitted-fixture
content_hash: 5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a
kind: bounded-text-excerpt
source_ref: INPUT-SYNTHETIC-001@1
locator: lines 1-2
statement: The source identifies itself as a synthetic fixture.
quality_flags: [synthetic_fixture]
"""

COUNTER = """schema_version: 0.1.0
object_type: evidence
object_id: EVID-001-02
revision: 1
status: admitted-fixture
kind: bounded-text-excerpt
source_ref: INPUT-SYNTHETIC-001@1
locator: lines 3-4
statement: The fixture states its output must not support causal claims.
quality_flags: [synthetic_fixture]
"""

CLAIM = """schema_version: 0.1.0
object_type: claim
object_id: CLAIM-M4-003
revision: 1
status: proposed-fixture
statement: The fixture supports only a bounded structural reading.
strength: unresolved
support_refs: [EVID-001-01@1]
counterevidence_refs: [EVID-001-02@1]
limitations:
  - Fixture-only evidence.
"""


class ClaimTraceLocalizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        objects = self.root / "examples" / "objects"
        (objects / "evidence").mkdir(parents=True, exist_ok=True)
        (objects / "claim").mkdir(parents=True, exist_ok=True)
        (objects / "evidence" / "EVID-001-01.yaml").write_text(EVIDENCE, encoding="utf-8")
        (objects / "evidence" / "EVID-001-02.yaml").write_text(COUNTER, encoding="utf-8")
        self.claim_path = objects / "claim" / "CLAIM-M4-003.yaml"
        self.claim_path.write_text(CLAIM, encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *extra: str) -> tuple[int, str]:
        import contextlib
        import io

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(
                [
                    "claim",
                    "trace",
                    str(self.claim_path),
                    "--root",
                    str(self.root),
                    "--objects",
                    str(self.root / "examples" / "objects"),
                    *extra,
                ]
            )
        return code, stdout.getvalue()

    @staticmethod
    def _extract_json(output: str) -> dict:
        decoder = json.JSONDecoder()
        payload, _ = decoder.raw_decode(output.lstrip())
        return payload

    def test_localizes_support_counterevidence_and_limitations(self) -> None:
        code, output = self._run()
        self.assertEqual(code, 0)
        payload = self._extract_json(output)
        self.assertEqual(payload["claim_id"], "CLAIM-M4-003")
        self.assertEqual(len(payload["support"]), 1)
        self.assertEqual(len(payload["counterevidence"]), 1)
        support = payload["support"][0]
        self.assertEqual(support["object_id"], "EVID-001-01")
        self.assertEqual(support["revision"], 1)
        self.assertEqual(support["status"], "ok")
        self.assertTrue(support["path"].endswith("EVID-001-01.yaml"))
        counter = payload["counterevidence"][0]
        self.assertEqual(counter["object_id"], "EVID-001-02")
        self.assertEqual(payload["limitations"], ["Fixture-only evidence."])

    def test_missing_object_blocks(self) -> None:
        (self.root / "examples" / "objects" / "evidence" / "EVID-001-02.yaml").unlink()
        code, output = self._run()
        self.assertEqual(code, 1)
        self.assertIn("REF-MISSING", output)

    def test_unversioned_ref_warns(self) -> None:
        self.claim_path.write_text(
            CLAIM.replace("support_refs: [EVID-001-01@1]", "support_refs: [EVID-001-01]"),
            encoding="utf-8",
        )
        code, output = self._run()
        self.assertEqual(code, 0)
        self.assertIn("ARTIFACT-UNVERSIONED-REF", output)

    def test_ref_pin_drift_blocks(self) -> None:
        # the claim pins the evidence with a ref-level sha256 that differs
        # from the object's declared content_hash pin
        self.claim_path.write_text(
            CLAIM.replace(
                "support_refs: [EVID-001-01@1]",
                "support_refs: [{object_id: EVID-001-01, revision: 1, sha256: " + "cd" * 32 + "}]",
            ),
            encoding="utf-8",
        )
        code, output = self._run()
        self.assertEqual(code, 1)
        self.assertIn("ARTIFACT-HASH-MISMATCH", output)

    def test_matching_ref_pin_passes(self) -> None:
        self.claim_path.write_text(
            CLAIM.replace(
                "support_refs: [EVID-001-01@1]",
                "support_refs: [{object_id: EVID-001-01, revision: 1, sha256: 5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a5d1a}]",
            ),
            encoding="utf-8",
        )
        code, output = self._run()
        self.assertEqual(code, 0)
        payload = self._extract_json(output)
        self.assertEqual(payload["support"][0]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
