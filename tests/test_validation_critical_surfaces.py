from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.validation import capability as consumer
from research_workbench.validation.capability_registry import (
    capability_requirement_entries,
    capability_requirement_indices,
    validate_capability_requirement_set,
)
from research_workbench.validation.document_core import (
    LoadedDocuments,
    ValidationIssue,
    document_has_loaded_bytes,
    document_hash,
    loaded_document_at,
    matches_repository_path,
)


def requirement(requirement_id: str = "document-read") -> dict[str, object]:
    return {
        "requirement_id": requirement_id,
        "constraints": {},
        "unsatisfied_requirement": {},
    }


def method(*refs: object) -> dict[str, object]:
    return {
        "resolution_id": "METHOD-001",
        "mode_resolution": {},
        "action_decisions": [{"capability_requirements": list(refs)}, "ignored"],
    }


def index(*entries: object) -> dict[str, object]:
    return {"registry_kind": "capability_requirement_index", "entries": list(entries)}


def entry(
    requirement_id: object = "document-read",
    document_path: object = "registry/requirements/document-read.yaml",
    content_hash: object = "a" * 64,
) -> dict[str, object]:
    return {
        "requirement_id": requirement_id,
        "document_path": document_path,
        "content_hash": content_hash,
    }


class CapabilityRequirementRegistryCriticalTests(unittest.TestCase):
    def _loaded(self, *items: tuple[str, object, str]) -> LoadedDocuments:
        documents = LoadedDocuments()
        for path, document, digest in items:
            documents.add(Path(path), document, sha256=digest)
        return documents

    def test_positive_closed_registry_and_method_reference_pass(self) -> None:
        documents = self._loaded(
            ("registry/requirements/index.yaml", index(entry()), "b" * 64),
            ("registry/requirements/document-read.yaml", requirement(), "a" * 64),
            ("examples/method.yaml", method("document-read", 7), "c" * 64),
            ("examples/ignored.yaml", [], "d" * 64),
        )
        self.assertEqual([], validate_capability_requirement_set(documents))
        self.assertEqual(1, len(capability_requirement_indices(documents)))
        self.assertEqual(
            "registry/requirements/document-read.yaml",
            capability_requirement_entries(documents)["document-read"]["document_path"],
        )
        malformed_entries = {
            Path("index.yaml"): index(
                "bad", {"requirement_id": 4}, entry()
            )
        }
        self.assertEqual(
            {"document-read"}, set(capability_requirement_entries(malformed_entries))
        )

    def test_missing_and_duplicate_index_fail_closed(self) -> None:
        self.assertEqual([], validate_capability_requirement_set({}))
        for documents in (
            {Path("requirement.yaml"): requirement()},
            {Path("method.yaml"): method("document-read")},
        ):
            self.assertEqual(
                {"CAPABILITY-REQUIREMENT-INDEX-MISSING"},
                {issue.code for issue in validate_capability_requirement_set(documents)},
            )
        duplicate = {
            Path("one.yaml"): index(),
            Path("two.yaml"): index(),
        }
        self.assertEqual({}, capability_requirement_entries(duplicate))
        self.assertEqual(
            {"CAPABILITY-REQUIREMENT-INDEX-DUPLICATE"},
            {issue.code for issue in validate_capability_requirement_set(duplicate)},
        )

    def test_entry_identity_path_kind_and_hash_guards_fail_closed(self) -> None:
        cases = (
            (
                index(entry(), entry()),
                [("registry/requirements/document-read.yaml", requirement(), "a" * 64)],
                "CAPABILITY-REQUIREMENT-IDENTITY-DUPLICATE",
            ),
            (
                index(entry(), entry("other", "registry/requirements/document-read.yaml")),
                [("registry/requirements/document-read.yaml", requirement(), "a" * 64)],
                "CAPABILITY-REQUIREMENT-PATH-DUPLICATE",
            ),
            (index(entry()), [], "CAPABILITY-REQUIREMENT-DOCUMENT-MISSING"),
            (
                index(entry()),
                [("registry/requirements/document-read.yaml", {"other": True}, "a" * 64)],
                "CAPABILITY-REQUIREMENT-DOCUMENT-KIND",
            ),
            (
                index(entry()),
                [("registry/requirements/document-read.yaml", requirement("other"), "a" * 64)],
                "CAPABILITY-REQUIREMENT-IDENTITY-MISMATCH",
            ),
            (
                index(entry(content_hash="0" * 64)),
                [("registry/requirements/document-read.yaml", requirement(), "a" * 64)],
                "CAPABILITY-REQUIREMENT-HASH-MISMATCH",
            ),
        )
        for registry, loaded, expected in cases:
            with self.subTest(code=expected):
                documents = self._loaded(
                    ("registry/requirements/index.yaml", registry, "b" * 64),
                    *loaded,
                )
                self.assertIn(
                    expected,
                    {issue.code for issue in validate_capability_requirement_set(documents)},
                )

    def test_malformed_unindexed_and_relocated_requirements_cannot_bypass_closure(self) -> None:
        registry = index(
            "not-an-entry",
            entry(requirement_id=4),
            entry("document-read", document_path=4),
            entry(content_hash=None),
        )
        documents = self._loaded(
            ("registry/requirements/index.yaml", registry, "b" * 64),
            ("registry/requirements/document-read.yaml", requirement(), "a" * 64),
            ("archive/other.yaml", requirement("unindexed"), "c" * 64),
        )
        self.assertIn(
            "CAPABILITY-REQUIREMENT-UNINDEXED",
            {issue.code for issue in validate_capability_requirement_set(documents)},
        )

        relocated = self._loaded(
            ("registry/requirements/index.yaml", index(entry()), "b" * 64),
            ("base/registry/requirements/document-read.yaml", requirement(), "a" * 64),
            ("archive/document-read.yaml", requirement(), "a" * 64),
        )
        self.assertIn(
            "CAPABILITY-REQUIREMENT-PATH-MISMATCH",
            {issue.code for issue in validate_capability_requirement_set(relocated)},
        )

        unloaded_bytes = {
            Path("index.yaml"): index(entry(document_path="missing.yaml")),
            Path("missing.yaml"): requirement(),
        }
        self.assertNotIn(
            "CAPABILITY-REQUIREMENT-HASH-MISMATCH",
            {issue.code for issue in validate_capability_requirement_set(unloaded_bytes)},
        )


class DocumentCoreCriticalTests(unittest.TestCase):
    def test_byte_binding_and_repository_path_helpers_cover_all_storage_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "registry/requirements/document-read.yaml"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"requirement")
            digest = hash_bytes(b"requirement")

            plain_documents = {path: requirement()}
            self.assertEqual(digest, document_hash(plain_documents, path))
            self.assertTrue(document_has_loaded_bytes(plain_documents, path))
            self.assertFalse(
                document_has_loaded_bytes(plain_documents, root / "missing.yaml")
            )

            loaded = LoadedDocuments()
            loaded.add(path, requirement(), sha256=digest)
            self.assertEqual(digest, loaded.sha256_for(path))
            self.assertIsNone(loaded.sha256_for(root / "missing.yaml"))
            self.assertEqual(digest, document_hash(loaded, path))
            self.assertEqual("", document_hash(loaded, root / "missing.yaml"))
            self.assertTrue(document_has_loaded_bytes(loaded, path))
            self.assertFalse(document_has_loaded_bytes(loaded, root / "missing.yaml"))

            self.assertTrue(matches_repository_path(Path("exact.yaml"), "exact.yaml"))
            self.assertTrue(matches_repository_path(path, "registry/requirements/document-read.yaml"))
            self.assertFalse(matches_repository_path(path, "other.yaml"))
            self.assertIsNone(loaded_document_at(loaded, 7))
            self.assertEqual((path, requirement()), loaded_document_at(loaded, "document-read.yaml"))
            self.assertIsNone(loaded_document_at({Path("value.yaml"): []}, "value.yaml"))
            self.assertIsNone(loaded_document_at(loaded, "missing.yaml"))


class CapabilitySnapshotConsumerCriticalTests(unittest.TestCase):
    def _candidate(self, root: Path) -> Path:
        candidate = root / "snapshot.yaml"
        candidate.write_text("snapshot: true\n", encoding="utf-8")
        return candidate

    def _snapshot(self, *, runtime: bool = True) -> dict[str, object]:
        return {
            "snapshot_id": "SNAPSHOT-001",
            "qualification": "runtime-execution" if runtime else "structural-replay",
            "selected_supply_report_ref": {},
            "boundaries": {"execution_input": runtime},
            "nested": [{"value": 1}],
        }

    def _documents(
        self, candidate: Path, document: object, digest: str = "a" * 64
    ) -> LoadedDocuments:
        documents = LoadedDocuments()
        documents.add(candidate, document, sha256=digest)
        return documents

    def test_positive_runtime_snapshot_is_hash_pinned_and_deep_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = self._candidate(root)
            documents = self._documents(candidate, self._snapshot())
            with mock.patch.object(
                consumer, "load_and_validate", return_value=(documents, [])
            ):
                validated = consumer.load_validated_capability_snapshot(
                    candidate,
                    project_root=root,
                    document_roots=(),
                    require_runtime_execution=True,
                    expected_sha256="sha256:" + "A" * 64,
                )
            self.assertTrue(validated.runtime_execution_input)
            with self.assertRaises(TypeError):
                validated.document["nested"][0]["value"] = 2

    def test_hash_input_and_validator_digest_fail_closed(self) -> None:
        self.assertIsNone(consumer._normalized_sha256(None))
        self.assertIsNone(consumer._normalized_sha256("short"))
        self.assertIsNone(consumer._normalized_sha256("z" * 64))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = self._candidate(root)
            cases = (
                ({candidate: self._snapshot()}, [], "a" * 64, "HASH-UNAVAILABLE"),
                (LoadedDocuments(), [ValidationIssue(candidate, "BROKEN", "broken")], "a" * 64, "BROKEN"),
                (LoadedDocuments(), [], "a" * 64, "HASH-UNAVAILABLE"),
                (self._documents(candidate, self._snapshot(), "b" * 64), [], "a" * 64, "HASH-MISMATCH"),
            )
            for documents, issues, expected, code in cases:
                with self.subTest(code=code), mock.patch.object(
                    consumer, "load_and_validate", return_value=(documents, issues)
                ):
                    with self.assertRaises(consumer.CapabilitySnapshotValidationError) as raised:
                        consumer.load_validated_capability_snapshot(
                            candidate,
                            project_root=root,
                            document_roots=(),
                            expected_sha256=expected,
                        )
                    self.assertTrue(any(code in issue.code for issue in raised.exception.issues))
            with self.assertRaises(consumer.CapabilitySnapshotValidationError):
                consumer.load_validated_capability_snapshot(
                    candidate,
                    project_root=root,
                    document_roots=(),
                    expected_sha256="bad",
                )

    def test_paths_roots_kind_and_runtime_eligibility_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as outside:
            root = Path(temporary)
            candidate = self._candidate(root)
            with self.assertRaisesRegex(ValueError, "escapes project root"):
                consumer.load_validated_capability_snapshot(
                    Path(outside) / "outside.yaml", project_root=root
                )
            with self.assertRaisesRegex(ValueError, "missing"):
                consumer.load_validated_capability_snapshot("missing.yaml", project_root=root)
            with mock.patch.object(
                consumer, "resolve_within_root", return_value=root / "different.yaml"
            ):
                with self.assertRaisesRegex(ValueError, "escapes project root"):
                    consumer.load_validated_capability_snapshot(
                        candidate, project_root=root
                    )
            with self.assertRaisesRegex(ValueError, "document root escapes"):
                consumer.load_validated_capability_snapshot(
                    candidate, project_root=root, document_roots=(outside,)
                )

            for document, issues, runtime, code in (
                ({"other": True}, [], False, "CONSUMER-KIND"),
                (self._snapshot(runtime=False), [], True, "NOT-RUNTIME-ELIGIBLE"),
                (self._snapshot(), [ValidationIssue(candidate, "BROKEN", "broken")], False, "BROKEN"),
            ):
                documents = self._documents(candidate, document)
                with self.subTest(code=code), mock.patch.object(
                    consumer, "load_and_validate", return_value=(documents, issues)
                ):
                    with self.assertRaises(consumer.CapabilitySnapshotValidationError) as raised:
                        consumer.load_validated_capability_snapshot(
                            candidate,
                            project_root=root,
                            document_roots=("absent",),
                            require_runtime_execution=runtime,
                        )
                    self.assertTrue(any(code in issue.code for issue in raised.exception.issues))

    def test_document_root_file_and_directory_collection_is_bounded_by_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = self._candidate(root)
            documents_root = root / "documents"
            documents_root.mkdir()
            included = documents_root / "included.yaml"
            included.write_text("included: true\n", encoding="utf-8")
            (documents_root / "ignored.txt").write_text("ignored", encoding="utf-8")
            documents = self._documents(candidate, self._snapshot())
            captured: list[Path] = []

            def load(paths):
                captured.extend(paths)
                return documents, []

            with mock.patch.object(consumer, "load_and_validate", side_effect=load):
                consumer.load_validated_capability_snapshot(
                    candidate,
                    project_root=root,
                    document_roots=(documents_root, included, documents_root / "ignored.txt"),
                )
            self.assertIn(included, captured)
            self.assertNotIn(documents_root / "ignored.txt", captured)


if __name__ == "__main__":
    unittest.main()
