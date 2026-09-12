"""Public, exact-pinned verifier and CLI registration."""

import contextlib
import io
import json
import unittest

from research_workbench.cli import main
from research_workbench.evaluation.contracts import verify_evaluation_record
from research_workbench.evaluation.pins import EvaluationValidationError
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.documents import validate_documents
from tests.system_evaluation_fixtures import AT, ROOT, OverlayFixtureMixin, record


class EvaluationContractTests(OverlayFixtureMixin, unittest.TestCase):
    def verify(self, document, **kwargs):
        reference = self.f.write("evaluation/verify.json", document)
        if document.get("record_kind") in {
            "a4_execution_qualification",
            "a3_a4_pairwise_comparability",
        }:
            kwargs.setdefault("expected_case_closure_ref", self.f.case_closure_ref)
            kwargs.setdefault("case_selection_frozen_at", AT)
        return verify_evaluation_record(
            self.f.root,
            reference,
            expected_protocol_ref=self.f.protocol_ref,
            schema_root=ROOT / "schemas",
            **kwargs,
        )

    def test_main_record_types_are_known_and_schema_validated(self):
        docs = [
            self.f.protocol,
            self.f.qualification(),
            self.f.assessment(),
            self.f.overlay,
            self.f.pairwise,
            self.f.case_closure,
            self.f.doc(self.f.bindings["plain-agent-tool"]["interface_ref"]["path"]),
        ]
        for document in docs:
            with self.subTest(kind=document["record_kind"]):
                self.assertEqual(infer_document_kind(document), document["record_kind"])
                self.assertEqual(
                    validate_documents({ROOT / "tests/fixtures/m5-006.json": document}),
                    [],
                )

    def test_public_verifier_preserves_non_authority_result(self):
        for document in (self.f.qualification(), self.f.overlay, self.f.pairwise):
            result = self.verify(document, admission_verifier=lambda _evidence: True)
            self.assertEqual(result["validation"], "valid")
            self.assertFalse(result["execution_authority"])
        result = self.verify(
            self.f.assessment(),
            expected_case_closure_ref=self.f.case_closure_ref,
            case_selection_frozen_at=AT,
        )
        self.assertTrue(result["result"]["primary_confirmatory_eligible"])
        result = verify_evaluation_record(
            self.f.root, self.f.protocol_ref, schema_root=ROOT / "schemas"
        )
        self.assertEqual(result["result"]["primary"], "A4-A2")

    def test_public_verifier_requires_external_protocol_case_and_admission_inputs(self):
        ref = self.f.write("evaluation/qualification.json", self.f.qualification())
        with self.assertRaisesRegex(EvaluationValidationError, "Protocol reference"):
            verify_evaluation_record(self.f.root, ref, schema_root=ROOT / "schemas")
        with self.assertRaisesRegex(EvaluationValidationError, "frozen case"):
            self.verify(self.f.assessment())
        with self.assertRaisesRegex(EvaluationValidationError, "external admission"):
            self.verify(self.f.overlay)
        with self.assertRaisesRegex(EvaluationValidationError, "unsupported"):
            self.verify({"record_kind": "unrecognized"})

    def test_cli_reloads_external_pins_and_returns_nonzero_on_substitution(self):
        args = [
            "eval",
            "verify",
            self.f.protocol_ref["path"],
            "--root",
            str(self.f.root),
            "--sha256",
            self.f.protocol_ref["sha256"],
        ]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exit_code = main(args)
        self.assertEqual(exit_code, 0, out.getvalue())
        self.assertFalse(json.loads(out.getvalue())["execution_authority"])
        for tail in (
            ["--protocol", "missing"],
            ["--case-closure", "missing"],
            ["--sha256", "0" * 64],
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(args + tail), 1)

    def test_cli_qualification_and_overlap_use_separately_selected_protocol_and_case_pins(
        self,
    ):
        protocol_args = [
            "--protocol",
            self.f.protocol_ref["path"],
            "--protocol-sha256",
            self.f.protocol_ref["sha256"],
        ]
        for document, extra in (
            (self.f.qualification(), []),
            (
                self.f.assessment(),
                [
                    "--case-closure",
                    self.f.case_closure_ref["path"],
                    "--case-closure-sha256",
                    self.f.case_closure_ref["sha256"],
                    "--case-selection-frozen-at",
                    AT,
                ],
            ),
        ):
            reference = self.f.write("evaluation/cli-record.json", document)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(
                    [
                        "eval",
                        "verify",
                        reference["path"],
                        "--root",
                        str(self.f.root),
                        "--sha256",
                        reference["sha256"],
                        *protocol_args,
                        *extra,
                    ]
                )
            self.assertEqual(code, 0, out.getvalue())

    def test_measurement_public_entrypoint_and_schema(self):
        document = record(
            "evaluation_measurement",
            "measurement_id",
            "M5-UNAVAILABLE",
            protocol_ref=self.f.protocol_ref,
            case_id="CASE",
            arm_id="plain-agent",
            metric_id="completion-time",
            status="unavailable",
            unit="minutes",
            value=None,
            reason="No execution occurred.",
            evidence_refs=[],
            estimation_method=None,
        )
        self.assertEqual(infer_document_kind(document), "evaluation_measurement")
        self.assertEqual(
            self.verify(document)["result"]["measurement_status"], "unavailable"
        )
