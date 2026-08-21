import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from research_workbench.validation.documents import (
    DOCUMENT_REQUIRED,
    SCHEMA_KINDS,
    Severity,
    load_and_validate,
    validate_documents,
)
from research_workbench.validation.schemas import SchemaCatalog


def _codes(issues):
    return {issue.code for issue in issues}


def _source(source_id):
    return {
        "source_id": source_id,
        "origin": "user-supplied-archive",
        "locator": "bundle.zip",
        "revision": "rev-1",
        "license_status": "unknown-mixed",
        "trust": "unknown",
    }


def _sources_document(sources):
    return {
        "schema_version": "0.1.0",
        "registry_kind": "skill_sources",
        "sources": sources,
    }


def _candidate(status="triage", source_id="src-1"):
    return {
        "candidate_id": "cand-1",
        "source_id": source_id,
        "source_path": "skills/cand-1",
        "status": status,
        "kind": "prompt",
        "capabilities": ["summarize"],
        "applicable_modes": ["survey"],
        "context_cost": "low",
        "risk_flags": [],
        "decision": "keep",
    }


def _candidates_document(candidates):
    return {
        "schema_version": "0.1.0",
        "registry_kind": "skill_candidates",
        "candidates": candidates,
    }


def _slot(**overrides):
    slot = {
        "slot_id": "main",
        "role": "primary",
        "provider_adapter": "mock",
        "model_env": "MOCK_MODEL",
        "enabled": True,
        "capabilities": ["text"],
    }
    slot.update(overrides)
    return slot


def _pool(slots, **overrides):
    document = {
        "schema_version": "0.1.0",
        "registry_kind": "model_pool",
        "pool_id": "pool-1",
        "selection_policy": "explicit-slot-only",
        "slots": slots,
    }
    document.update(overrides)
    return document


class KindDerivationTests(unittest.TestCase):
    def test_schema_kinds_are_derived_from_the_catalog(self) -> None:
        self.assertEqual(frozenset(SchemaCatalog().document_kinds), SCHEMA_KINDS)

    def test_required_table_only_covers_kinds_without_schemas(self) -> None:
        self.assertFalse(set(DOCUMENT_REQUIRED) & SCHEMA_KINDS)


class HashValidationTests(unittest.TestCase):
    def test_invalid_hash_values_are_errors(self) -> None:
        bad_hashes = ["not-a-hash", "abc123", "z" * 64, "sha256:" + "g" * 64]
        for bad_hash in bad_hashes:
            document = _sources_document([])
            document["pin"] = {"sha256": bad_hash}
            with self.subTest(bad_hash=bad_hash):
                issues = validate_documents({Path("sources.json"): document})
                self.assertEqual({"HASH-INVALID"}, _codes(issues))
                self.assertTrue(all(issue.severity == Severity.ERROR for issue in issues))


class ParseErrorTests(unittest.TestCase):
    def test_unparseable_documents_report_parse_error(self) -> None:
        cases = {"broken.json": "{ not json", "broken.yaml": "key: [unclosed"}
        for name, content in cases.items():
            with self.subTest(name=name), TemporaryDirectory() as tmp:
                path = Path(tmp) / name
                path.write_text(content, encoding="utf-8")
                _, issues = load_and_validate([path])
                self.assertEqual({"PARSE-ERROR"}, _codes(issues))


class UnknownDocumentTests(unittest.TestCase):
    def test_unrecognized_documents_report_document_unknown(self) -> None:
        documents = [
            {"schema_version": "0.1.0"},
            {"task_id": "T-1"},
            {"registry_kind": 42},
        ]
        for document in documents:
            with self.subTest(document=document):
                issues = validate_documents({Path("doc.json"): document})
                self.assertEqual({"DOCUMENT-UNKNOWN"}, _codes(issues))


class RegistryValidationTests(unittest.TestCase):
    def test_duplicate_source_ids_are_errors(self) -> None:
        variants = [
            [_source("src-1"), _source("src-1")],
            [_source("src-1"), _source("src-2"), _source("src-1")],
        ]
        for sources in variants:
            with self.subTest(sources=[source["source_id"] for source in sources]):
                issues = validate_documents({Path("sources.json"): _sources_document(sources)})
                self.assertEqual({"SOURCE-DUPLICATE"}, _codes(issues))

    def test_unknown_candidate_source_is_an_error(self) -> None:
        variants = ["src-missing", "src-2"]
        for source_id in variants:
            documents = {
                Path("sources.json"): _sources_document([_source("src-1")]),
                Path("candidates.json"): _candidates_document([_candidate(source_id=source_id)]),
            }
            with self.subTest(source_id=source_id):
                issues = validate_documents(documents)
                self.assertEqual({"SOURCE-UNKNOWN"}, _codes(issues))

    def test_accepted_candidate_without_content_hash_is_unpinned(self) -> None:
        variants = ["cand-1", "cand-2"]
        for candidate_id in variants:
            candidate = _candidate(status="accepted")
            candidate["candidate_id"] = candidate_id
            documents = {
                Path("sources.json"): _sources_document([_source("src-1")]),
                Path("candidates.json"): _candidates_document([candidate]),
            }
            with self.subTest(candidate_id=candidate_id):
                issues = validate_documents(documents)
                self.assertEqual({"CANDIDATE-UNPINNED"}, _codes(issues))

    def test_invalid_model_pools_are_errors(self) -> None:
        variants = {
            "empty slots": _pool([]),
            "unsupported policy": _pool([_slot()], selection_policy="auto-route"),
            "slot missing fields": _pool([{"slot_id": "main"}]),
            "unsupported role": _pool([_slot(role="chief")]),
            "duplicate slot id": _pool([_slot(), _slot()]),
        }
        for label, document in variants.items():
            with self.subTest(variant=label):
                issues = validate_documents({Path("pool.yaml"): document})
                self.assertEqual({"MODEL-POOL-INVALID"}, _codes(issues))

    def test_valid_registry_documents_have_no_issues(self) -> None:
        documents = {
            Path("sources.json"): _sources_document([_source("src-1")]),
            Path("candidates.json"): _candidates_document([_candidate()]),
            Path("pool.yaml"): _pool([_slot()]),
        }
        self.assertEqual([], validate_documents(documents))


if __name__ == "__main__":
    unittest.main()
