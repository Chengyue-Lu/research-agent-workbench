import copy
import json
import unittest
from pathlib import Path

from research_workbench.capability import SkillLifecycleRecord, SkillLifecycleSet
from research_workbench.capability.lifecycle import SkillLifecycleEntry
from research_workbench.io import iter_documents, load_document
from research_workbench.validation import SchemaCatalog, validate_documents
from research_workbench.validation import documents as document_validation


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "registry/skills/lifecycle-v2.json"
LIFECYCLE_ROOT = ROOT / "registry/skills/lifecycle"
MIGRATION_PATH = (
    ROOT / "registry/skills/lifecycle-migrations/accepted-v1-to-lifecycle-v2.yaml"
)
ACCEPTED_PATH = ROOT / "registry/skills/accepted.json"


class SkillLifecycleV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        cls.records = {
            path: load_document(path) for path in sorted(LIFECYCLE_ROOT.glob("*.yaml"))
        }
        cls.migration = load_document(MIGRATION_PATH)
        cls.accepted = json.loads(ACCEPTED_PATH.read_text(encoding="utf-8"))
        cls.registry_documents = {
            path: load_document(path) for path in iter_documents([ROOT / "registry"])
        }

    def test_three_legacy_records_are_schema_valid_and_historical_only(self) -> None:
        self.assertEqual(3, len(self.records))
        for path, document in self.records.items():
            with self.subTest(path=path.name):
                self.assertEqual([], self.catalog.validate("skill_lifecycle_record", document))
                record = SkillLifecycleRecord.from_mapping(document)
                self.assertEqual("migrated-legacy", record.record_scope)
                self.assertEqual("legacy-imported", record.admission.state)
                self.assertEqual("historical-replay-only", record.runtime_eligibility.state)
                self.assertFalse(record.eligible_for_new_binding())

    def test_index_migration_and_registry_relationships_are_closed(self) -> None:
        self.assertEqual([], self.catalog.validate("skill_lifecycle_index", self.index))
        self.assertEqual(
            [], self.catalog.validate("skill_lifecycle_migration", self.migration)
        )
        self.assertEqual([], validate_documents(self.registry_documents))
        lifecycle_set = SkillLifecycleSet.load(project_root=ROOT)
        self.assertEqual(
            {entry["lifecycle_ref"] for entry in self.index["entries"]},
            {entry.lifecycle_ref for entry in lifecycle_set.entries},
        )
        self.assertTrue(
            all(
                not lifecycle_set.runtime_eligible(
                    entry.lifecycle_ref,
                    entry.record.runtime_eligibility.eligibility_ref,
                )
                for entry in lifecycle_set.entries
            )
        )

    def test_lifecycle_references_evidence_without_storing_results_or_metrics(self) -> None:
        forbidden = {
            "trial_result",
            "trial_results",
            "evaluation_result",
            "evaluation_results",
            "benchmark",
            "metrics",
            "scores",
            "provider",
            "model",
        }

        def keys(value):
            if isinstance(value, dict):
                yield from value.keys()
                for nested in value.values():
                    yield from keys(nested)
            elif isinstance(value, list):
                for nested in value:
                    yield from keys(nested)

        for path, document in self.records.items():
            with self.subTest(path=path.name):
                self.assertFalse(forbidden.intersection(keys(document)))
                self.assertFalse(document["boundaries"]["stores_trial_results"])
                self.assertFalse(document["boundaries"]["stores_evaluation_results"])
                self.assertFalse(document["boundaries"]["defines_benchmark_metrics"])

    def test_trial_accepted_superseded_and_retired_states_are_expressible(self) -> None:
        base = copy.deepcopy(next(iter(self.records.values())))
        base["lifecycle_id"] = "synthetic-skill"
        base["lifecycle_version"] = "1.0.0"
        base["record_scope"] = "synthetic-fixture"
        base["skill_ref"].update(
            {
                "skill_id": "synthetic-skill",
                "version": "1.0.0",
                "manifest_path": "fixtures/synthetic-skill.yaml",
                "content_hash": "sha256:" + "1" * 64,
                "package_hash": "sha256:" + "2" * 64,
            }
        )
        base["need_refs"] = ["NEED-ES-SEARCH-PLAN"]
        base["intake"] = {
            "state": "candidate",
            "source_refs": ["candidate:synthetic-skill"],
            "reason": "Synthetic lifecycle state-machine fixture.",
        }

        trial = copy.deepcopy(base)
        trial["evaluation"] = {
            "state": "in-progress",
            "baseline_ref": "BASELINE-SYNTHETIC",
            "trial_ref": "TRIAL-SYNTHETIC",
            "promotion_evidence_refs": [],
            "reason": "Trial evidence is produced outside the lifecycle record.",
        }
        trial["admission"] = {
            "state": "trial",
            "decision_owner": "human",
            "decision_ref": "DECISION-TRIAL-SYNTHETIC",
            "reason": "Human authorized a bounded trial only.",
        }
        trial["runtime_eligibility"] = {
            "state": "trial-only",
            "eligibility_ref": "RTE-TRIAL-SYNTHETIC",
            "scopes": ["isolated-trial"],
            "reason": "Not eligible for production binding.",
        }
        trial["lifecycle"] = {
            "state": "current",
            "superseded_by_refs": [],
            "reason": "Bounded trial is current.",
        }
        self.assertEqual([], self.catalog.validate("skill_lifecycle_record", trial))
        self.assertFalse(SkillLifecycleRecord.from_mapping(trial).eligible_for_new_binding())

        accepted = copy.deepcopy(base)
        accepted["record_scope"] = "current"
        accepted["evaluation"] = {
            "state": "evidence-ready",
            "baseline_ref": "BASELINE-SYNTHETIC",
            "trial_ref": "TRIAL-SYNTHETIC",
            "evaluation_record_ref": "EVAL-SYNTHETIC",
            "promotion_evidence_refs": ["EVAL-SYNTHETIC", "TRIAL-SYNTHETIC"],
            "reason": "External records meet the declared evidence requirement.",
        }
        accepted["admission"] = {
            "state": "accepted",
            "decision_owner": "human",
            "decision_ref": "DECISION-ACCEPT-SYNTHETIC",
            "reason": "Human accepted the pinned evidence package.",
        }
        accepted["runtime_eligibility"] = {
            "state": "eligible",
            "eligibility_ref": "RTE-ACCEPTED-SYNTHETIC",
            "scopes": ["new-binding"],
            "reason": "Runtime eligibility is explicit and separately addressable.",
        }
        accepted["lifecycle"] = {
            "state": "current",
            "superseded_by_refs": [],
            "reason": "The accepted version is current.",
        }
        self.assertEqual([], self.catalog.validate("skill_lifecycle_record", accepted))
        accepted_record = SkillLifecycleRecord.from_mapping(accepted)
        self.assertTrue(accepted_record.eligible_for_new_binding())

        lifecycle_set = SkillLifecycleSet(
            index_path=INDEX_PATH,
            project_root=ROOT,
            entries=(
                SkillLifecycleEntry(
                    lifecycle_ref=accepted_record.reference,
                    lifecycle_id=accepted_record.lifecycle_id,
                    lifecycle_version=accepted_record.lifecycle_version,
                    document_path="fixtures/synthetic-skill-lifecycle.yaml",
                    content_hash="1" * 64,
                    record=accepted_record,
                ),
            ),
        )
        eligibility_ref = accepted_record.runtime_eligibility.eligibility_ref
        self.assertFalse(
            lifecycle_set.runtime_eligible(accepted_record.reference, eligibility_ref)
        )
        verified_evidence = {
            "BASELINE-SYNTHETIC",
            "TRIAL-SYNTHETIC",
            "EVAL-SYNTHETIC",
        }
        self.assertTrue(
            lifecycle_set.runtime_eligible(
                accepted_record.reference,
                eligibility_ref,
                evidence_resolver=lambda reference: reference in verified_evidence,
                decision_resolver=lambda reference: (
                    reference == "DECISION-ACCEPT-SYNTHETIC"
                ),
            )
        )
        self.assertFalse(
            lifecycle_set.runtime_eligible(
                accepted_record.reference,
                eligibility_ref,
                evidence_resolver=lambda reference: reference != "TRIAL-SYNTHETIC",
                decision_resolver=lambda reference: (
                    reference == "DECISION-ACCEPT-SYNTHETIC"
                ),
            )
        )
        self.assertFalse(
            lifecycle_set.runtime_eligible(
                accepted_record.reference,
                eligibility_ref,
                evidence_resolver=lambda reference: reference in verified_evidence,
                decision_resolver=lambda reference: False,
            )
        )

        new_binding_failures = (
            (
                "wrong-scope",
                lambda document: document["runtime_eligibility"].__setitem__(
                    "scopes", ["isolated-trial"]
                ),
            ),
            (
                "missing-trial",
                lambda document: document["evaluation"].pop("trial_ref"),
            ),
            (
                "missing-evaluation",
                lambda document: document["evaluation"].pop("evaluation_record_ref"),
            ),
            (
                "missing-promotion-evidence",
                lambda document: document["evaluation"].__setitem__(
                    "promotion_evidence_refs", []
                ),
            ),
            (
                "missing-human-decision",
                lambda document: document["admission"].pop("decision_ref"),
            ),
        )
        for name, mutate in new_binding_failures:
            with self.subTest(new_binding_failure=name):
                invalid = copy.deepcopy(accepted)
                mutate(invalid)
                errors = self.catalog.validate("skill_lifecycle_record", invalid)
                if not errors:
                    self.assertFalse(
                        SkillLifecycleRecord.from_mapping(invalid).eligible_for_new_binding()
                    )
                self.assertFalse(
                    SkillLifecycleRecord.from_mapping(invalid).eligible_for_new_binding()
                )

        superseded = copy.deepcopy(accepted)
        superseded["runtime_eligibility"]["state"] = "ineligible"
        superseded["runtime_eligibility"]["scopes"] = []
        superseded["lifecycle"] = {
            "state": "superseded",
            "superseded_by_refs": ["synthetic-skill@2.0.0"],
            "reason": "A new semantic version replaced this version for new work.",
        }
        self.assertEqual([], self.catalog.validate("skill_lifecycle_record", superseded))

        retired = copy.deepcopy(superseded)
        retired["lifecycle"] = {
            "state": "retired",
            "superseded_by_refs": [],
            "reason": "No future binding is allowed.",
        }
        self.assertEqual([], self.catalog.validate("skill_lifecycle_record", retired))

    def test_append_to_accepted_registry_does_not_break_old_migration(self) -> None:
        documents = copy.deepcopy(self.registry_documents)
        documents[ACCEPTED_PATH]["entries"].append(
            {
                "skill_id": "future-skill",
                "version": "1.0.0",
                "lifecycle": "active",
                "manifest_path": "registry/skills/accepted/future-skill.yaml",
                "content_hash": "sha256:" + "3" * 64,
                "package_hash": "sha256:" + "4" * 64,
            }
        )
        codes = {
            issue.code
            for issue in document_validation._validate_skill_lifecycle_v2(documents)
        }
        self.assertNotIn("SKILL-LIFECYCLE-MIGRATION-SOURCE-DRIFT", codes)

    def test_index_source_target_and_disposition_drift_are_blocking(self) -> None:
        mutations = (
            (
                lambda documents: documents[INDEX_PATH]["entries"][0].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "SKILL-LIFECYCLE-HASH-MISMATCH",
            ),
            (
                lambda documents: documents[MIGRATION_PATH]["entries"][0]["source"].__setitem__(
                    "package_hash", "sha256:" + "0" * 64
                ),
                "SKILL-LIFECYCLE-MIGRATION-SOURCE-DRIFT",
            ),
            (
                lambda documents: documents[MIGRATION_PATH]["entries"][0]["target"].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "SKILL-LIFECYCLE-MIGRATION-TARGET-DRIFT",
            ),
            (
                lambda documents: documents[MIGRATION_PATH]["entries"][0].__setitem__(
                    "disposition", "retired"
                ),
                "SKILL-LIFECYCLE-MIGRATION-DISPOSITION-DRIFT",
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.registry_documents)
                mutate(documents)
                self.assertIn(
                    expected,
                    {
                        issue.code
                        for issue in document_validation._validate_skill_lifecycle_v2(
                            documents
                        )
                    },
                )

    def test_runtime_state_does_not_itself_authorize_new_binding(self) -> None:
        source_path = LIFECYCLE_ROOT / "literature-evidence-extraction-0.1.0-lifecycle-1.0.0.yaml"
        documents = copy.deepcopy(self.registry_documents)
        record = documents[source_path]
        record["runtime_eligibility"]["state"] = "eligible"
        record["runtime_eligibility"]["scopes"] = ["new-binding"]
        self.assertNotIn(
            "SKILL-LIFECYCLE-RUNTIME-ELIGIBILITY-INCONSISTENT",
            {
                issue.code
                for issue in document_validation._validate_skill_lifecycle_v2(documents)
            },
        )
        self.assertFalse(SkillLifecycleRecord.from_mapping(record).eligible_for_new_binding())


if __name__ == "__main__":
    unittest.main()
