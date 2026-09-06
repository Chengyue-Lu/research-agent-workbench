"""Claim evidence localization, provenance consumption and read cost."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from contextlib import chdir, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.artifacts.admission import build_admission_mapping
from research_workbench.artifacts.claim_trace import localize_claim
from research_workbench.artifacts.integrity import hash_bytes, hash_file
from research_workbench.cli import main
from research_workbench.validation.document_kinds import infer_document_kind
from research_workbench.validation.schemas import SchemaCatalog
from tests.test_artifacts_promotion import PromotionFixture


TRAJECTORY = b"n,x\n0,0\n1,1\n2,0\n3,2\n4,0\n"


def write_document(root: Path, path: str, document: dict) -> dict:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(document, sort_keys=True), encoding="utf-8", newline="\n")
    return {"path": path, "sha256": hash_file(target)}


def evidence(identifier: str, source: str = "TRAJECTORY@1") -> dict:
    statement = "The declared integer trajectory returns to zero."
    locator = "CSV row n=4, column x"
    if identifier == "E-COUNTER":
        statement = "Intermediate states are nonzero despite the zero final state."
        locator = "line 1" if source == "NEGATIVE@1" else "CSV rows n=1,3, column x"
    return {
        "schema_version": "0.1.0", "object_type": "evidence",
        "object_id": identifier, "revision": 1, "status": "draft",
        "kind": "synthetic-simulation", "source_ref": source,
        "locator": locator, "statement": statement,
        "quality_flags": ["synthetic-engineering-fixture-only"],
        "content_hash": hash_bytes(statement.encode()),
    }


def claim() -> dict:
    return {
        "schema_version": "0.1.0", "object_type": "claim", "object_id": "CLAIM-M4",
        "revision": 1, "status": "draft", "statement": "The sampled trajectory stays at zero.",
        "strength": "simulation_supported", "support_refs": ["E-SUPPORT@1"],
        "counterevidence_refs": ["E-COUNTER@1"],
        "limitations": ["The intermediate states are nonzero; this is not evidence of general stability."],
    }


def evidence_map(root: Path, bindings: list[dict]) -> dict:
    return {
        "schema_version": "0.1.0", "document_kind": "claim_evidence_map",
        "claim_ref": write_document(root, "objects/claim.yaml", claim()),
        "evidence_refs": [
            write_document(root, "objects/support.yaml", evidence("E-SUPPORT")),
            write_document(root, "objects/counter.yaml", evidence("E-COUNTER")),
        ],
        "source_bindings": bindings,
    }


class ClaimTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        raw = self.root / "sources/raw/trajectory.csv"
        raw.parent.mkdir(parents=True)
        raw.write_bytes(TRAJECTORY)
        self.admission = build_admission_mapping(
            original_filename="trajectory.csv", admitted_path="sources/raw/trajectory.csv",
            content=TRAJECTORY, origin={"device": "deterministic-integer-fixture"},
            acquired_at="2026-09-06T00:00:00Z", operator="huangyi",
            license_or_data_use="synthetic fixture", parser_name="csv", parser_version="1.0.0",
            sensitivity="public-synthetic", egress_restriction="local test",
        )
        self.mapping = evidence_map(self.root, [{
            "source_ref": {"object_id": "TRAJECTORY", "revision": 1},
            "artifact_ref": {"path": "sources/raw/trajectory.csv", "sha256": hash_bytes(TRAJECTORY)},
            "provenance_ref": write_document(self.root, "sources/raw/trajectory.csv.admission.yaml", self.admission),
        }])

    def trace(self) -> dict:
        return localize_claim(self.root, self.mapping)

    def set_claim(self, document: dict) -> None:
        self.mapping["claim_ref"] = write_document(self.root, "objects/claim.yaml", document)

    def test_support_counterevidence_and_limits_locate_without_execution(self) -> None:
        with patch("research_workbench.artifacts.promotion.check_promotion", side_effect=AssertionError("must not replay")):
            result = self.trace()
        self.assertTrue(result["complete"], result["problems"])
        self.assertFalse(result["claim_acceptance"])
        self.assertFalse(result["scientific_correctness"])
        for relation in ("support", "counterevidence"):
            item = result["localization"][relation][0]
            self.assertEqual("located", item["status"])
            self.assertEqual("sources/raw/trajectory.csv", item["artifact_ref"]["path"])
            self.assertEqual("source_admission", item["provenance"]["kind"])
        limit = result["localization"]["limitations"][0]
        self.assertEqual("/limitations/0", limit["pointer"])
        self.assertEqual(self.mapping["claim_ref"], limit["file_ref"])
        self.assertEqual(claim()["limitations"][0], limit["text"])
        self.assertEqual(5, result["captured_file_count"])

    def test_bytes_are_read_once_for_shared_evidence_source(self) -> None:
        reads: list[Path] = []
        original = Path.open

        def read(path: Path, *args, **kwargs):
            reads.append(path.resolve())
            return original(path, *args, **kwargs)

        with chdir(self.root), patch.object(Path, "open", read):
            self.assertTrue(self.trace()["complete"])
        project_reads = [path for path in reads if path.is_relative_to(self.root)]
        self.assertEqual(len(set(project_reads)), len(project_reads))

    def test_live_byte_drift_is_independent_of_declared_object_hash(self) -> None:
        for relative in ("objects/claim.yaml", "objects/support.yaml", "sources/raw/trajectory.csv", "sources/raw/trajectory.csv.admission.yaml"):
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b"\n")
                try:
                    if relative.startswith("objects/"):
                        with self.assertRaisesRegex(ValueError, "REF-HASH-MISMATCH"):
                            self.trace()
                    else:
                        result = self.trace()
                        self.assertFalse(result["complete"])
                        self.assertIn("REF-HASH-MISMATCH", str(result["problems"]))
                finally:
                    path.write_bytes(original)

    def test_missing_revision_unversioned_and_missing_evidence_are_unresolved(self) -> None:
        for reference in ("E-MISSING@1", "E-SUPPORT@2", "E-SUPPORT", "E-SUPPORT@0"):
            with self.subTest(reference=reference):
                document = claim()
                document["support_refs"] = [reference]
                self.set_claim(document)
                result = self.trace()
                self.assertFalse(result["complete"])
                self.assertEqual("located", result["localization"]["counterevidence"][0]["status"])

    def test_object_hash_pin_and_source_identity_are_checked(self) -> None:
        document = claim()
        document["support_refs"] = [{"object_id": "E-SUPPORT", "revision": 1, "sha256": evidence("E-SUPPORT")["content_hash"]}]
        self.set_claim(document)
        self.assertTrue(self.trace()["complete"])
        document["support_refs"][0]["sha256"] = "0" * 64
        self.set_claim(document)
        self.assertFalse(self.trace()["complete"])
        self.set_claim(claim())
        self.mapping["source_bindings"][0]["source_ref"]["revision"] = 2
        self.assertIn("missing source binding", str(self.trace()["problems"]))

    def test_source_declared_hash_needs_explicit_matching_binding(self) -> None:
        document = evidence("E-SUPPORT")
        document["source_ref"] = {"object_id": "TRAJECTORY", "revision": 1, "sha256": "a" * 64}
        self.mapping["evidence_refs"][0] = write_document(self.root, "objects/support.yaml", document)
        self.assertFalse(self.trace()["complete"])
        self.mapping["source_bindings"][0]["source_ref"]["sha256"] = "b" * 64
        self.assertFalse(self.trace()["complete"])
        self.mapping["source_bindings"][0]["source_ref"]["sha256"] = "a" * 64
        self.assertTrue(self.trace()["complete"])

    def test_duplicate_identity_and_wrong_document_type_are_rejected(self) -> None:
        original = copy.deepcopy(self.mapping)
        self.mapping["evidence_refs"].append(write_document(self.root, "objects/duplicate.yaml", evidence("E-SUPPORT")))
        with self.assertRaisesRegex(ValueError, "ambiguous Evidence"):
            self.trace()
        self.mapping = copy.deepcopy(original)
        binding = copy.deepcopy(self.mapping["source_bindings"][0])
        binding["source_ref"]["sha256"] = "a" * 64
        self.mapping["source_bindings"].append(binding)
        with self.assertRaisesRegex(ValueError, "ambiguous source"):
            self.trace()
        self.mapping = original
        self.mapping["evidence_refs"][0] = self.mapping["claim_ref"]
        with self.assertRaisesRegex(ValueError, "OBJECT-NOT-EVIDENCE"):
            self.trace()

    def test_missing_and_wrong_raw_admission_do_not_yield_complete_trace(self) -> None:
        binding = self.mapping["source_bindings"][0]
        provenance = binding["provenance_ref"]
        path = self.root / provenance["path"]
        content = path.read_bytes()
        path.unlink()
        self.assertIn("REF-MISSING", str(self.trace()["problems"]))
        path.write_bytes(content)
        self.admission["sha256"] = "a" * 64
        binding["provenance_ref"] = write_document(self.root, provenance["path"], self.admission)
        self.assertIn("does not bind", str(self.trace()["problems"]))
        binding["provenance_ref"]["path"] = "objects/wrong-sidecar.yaml"
        self.assertIn("exact admission sidecar", str(self.trace()["problems"]))

    def test_invalid_source_admission_is_reported(self) -> None:
        self.admission["acquisition"]["acquired_at"] = "not-a-timestamp"
        binding = self.mapping["source_bindings"][0]
        binding["provenance_ref"] = write_document(self.root, binding["provenance_ref"]["path"], self.admission)
        self.assertFalse(self.trace()["complete"])

    def test_inbox_and_outside_root_are_rejected(self) -> None:
        inbox = self.root / "sources/inbox/trajectory.csv"
        inbox.parent.mkdir(parents=True)
        inbox.write_bytes(TRAJECTORY)
        binding = self.mapping["source_bindings"][0]
        binding["artifact_ref"]["path"] = "sources/inbox/trajectory.csv"
        self.assertIn("INBOX-CITATION", str(self.trace()["problems"]))
        binding["artifact_ref"]["path"] = "../outside.csv"
        with self.assertRaisesRegex(ValueError, "SCHEMA-INVALID"):
            self.trace()

    def test_empty_relations_preserve_limits_without_inventing_evidence(self) -> None:
        document = claim()
        document["support_refs"] = []
        document["counterevidence_refs"] = []
        self.set_claim(document)
        self.mapping["evidence_refs"] = []
        self.mapping["source_bindings"] = []
        result = self.trace()
        self.assertTrue(result["complete"])
        self.assertEqual([], result["localization"]["support"])
        self.assertEqual(1, len(result["localization"]["limitations"]))

    def test_missing_malformed_and_non_claim_inputs_fail_with_diagnostics(self) -> None:
        original = copy.deepcopy(self.mapping)
        self.mapping["claim_ref"] = self.mapping["evidence_refs"][0]
        with self.assertRaisesRegex(ValueError, "OBJECT-NOT-CLAIM"):
            self.trace()
        self.mapping = original
        path = self.root / "objects/claim.yaml"
        path.write_bytes(b"[unfinished yaml\n")
        self.mapping["claim_ref"]["sha256"] = hash_file(path)
        with self.assertRaisesRegex(ValueError, "DOCUMENT-INVALID"):
            self.trace()
        self.set_claim({"schema_version": "0.1.0"})
        with self.assertRaisesRegex(ValueError, "SCHEMA-INVALID"):
            self.trace()
        path.unlink()
        with self.assertRaisesRegex(ValueError, "REF-MISSING"):
            self.trace()
        self.mapping = {}
        with self.assertRaisesRegex(ValueError, "SCHEMA-INVALID"):
            self.trace()

    def test_schema_kind_claim_pin_and_cli_generic_validation(self) -> None:
        self.assertEqual("claim_evidence_map", infer_document_kind(self.mapping))
        self.assertEqual([], SchemaCatalog().validate("claim_evidence_map", self.mapping))
        map_ref = write_document(self.root, "trace-map.yaml", self.mapping)
        output = StringIO()
        with redirect_stdout(output):
            code = main(["claim", "trace", str(self.root / "objects/claim.yaml"), "--evidence-map", str(self.root / map_ref["path"]), "--root", str(self.root)])
        self.assertEqual(0, code, output.getvalue())
        self.assertTrue(json.loads(output.getvalue())["complete"])
        with redirect_stdout(StringIO()):
            self.assertEqual(0, main(["validate", str(self.root / map_ref["path"]), "--root", str(self.root)]))
            self.assertEqual(2, main(["claim", "trace", "wrong.yaml", "--evidence-map", str(self.root / map_ref["path"]), "--root", str(self.root)]))
        protocol = yaml.safe_load((Path(__file__).resolve().parents[1] / "examples/project-protocol.yaml").read_bytes())
        protocol["claim_ceiling"] = ["source_reported"]
        protocol_ref = write_document(self.root, "protocol.yaml", protocol)
        with redirect_stdout(StringIO()):
            self.assertEqual(1, main([
                "claim", "trace", str(self.root / "objects/claim.yaml"),
                "--evidence-map", str(self.root / map_ref["path"]),
                "--root", str(self.root), "--protocol", str(self.root / protocol_ref["path"]),
            ]))
        (self.root / "sources/raw/trajectory.csv").write_bytes(b"changed\n")
        with redirect_stdout(StringIO()):
            self.assertEqual(1, main(["validate", str(self.root / map_ref["path"]), "--root", str(self.root)]))


class PromotedClaimTraceTests(PromotionFixture):
    def run_host(self, **kwargs):
        self.output.write_bytes(TRAJECTORY)
        self.negative.write_bytes(b"No net change; nonzero intermediate states remain.\n")
        return super().run_host(**kwargs)

    def test_real_promotion_and_retained_negative_are_consumed_without_replay(self) -> None:
        result = self.execute()
        receipt_ref = self.ref(self.root / result.receipt)
        mapping = evidence_map(self.root, [
            {"source_ref": {"object_id": "TRAJECTORY", "revision": 1},
             "artifact_ref": self.ref(self.root / result.targets[0]), "provenance_ref": receipt_ref},
            {"source_ref": {"object_id": "NEGATIVE", "revision": 1},
             "artifact_ref": self.ref(self.negative), "provenance_ref": receipt_ref},
        ])
        mapping["evidence_refs"][1] = write_document(self.root, "objects/counter.yaml", evidence("E-COUNTER", "NEGATIVE@1"))
        with patch("research_workbench.artifacts.promotion.check_promotion", side_effect=AssertionError("no validation replay")):
            trace = localize_claim(self.root, mapping)
        self.assertTrue(trace["complete"], trace["problems"])
        self.assertEqual("promote", trace["localization"]["support"][0]["provenance"]["disposition"])
        negative = trace["localization"]["counterevidence"][0]["provenance"]
        self.assertEqual("retain-in-work", negative["disposition"])
        self.assertTrue(negative["negative_result"])
        self.assertTrue(self.negative.exists())
        receipt_path = self.root / result.receipt
        receipt = json.loads(receipt_path.read_bytes())
        original_receipt = copy.deepcopy(receipt)
        for mutation in ("promotion-id", "target", "source", "record-target"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(original_receipt)
                if mutation == "promotion-id":
                    changed["promotion_id"] = "OTHER-PROMOTION"
                elif mutation == "target":
                    changed["target_artifact_refs"][0]["target_ref"]["path"] = "objects/another.txt"
                elif mutation == "source":
                    changed["target_artifact_refs"][0]["source_ref"]["sha256"] = "a" * 64
                else:
                    record = copy.deepcopy(self.record)
                    record["entries"][0]["target"] = "objects/another.txt"
                    changed["promotion_record_ref"] = write_document(self.root, "work/M4-002/A-001/changed-record.yaml", record)
                receipt_path.write_text(json.dumps(changed), encoding="utf-8", newline="\n")
                for binding in mapping["source_bindings"]:
                    binding["provenance_ref"] = self.ref(receipt_path)
                self.assertFalse(localize_claim(self.root, mapping)["complete"])
        receipt_path.write_text(json.dumps(original_receipt), encoding="utf-8", newline="\n")
        for binding in mapping["source_bindings"]:
            binding["provenance_ref"] = self.ref(receipt_path)
        target = self.root / result.targets[0]
        target.write_bytes(b"changed trajectory\n")
        self.assertFalse(localize_claim(self.root, mapping)["complete"])


if __name__ == "__main__":
    unittest.main()
