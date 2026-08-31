import contextlib
import copy
import json
import shutil
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_workbench.artifacts.integrity import hash_directory, hash_file
from research_workbench.capability import (
    SkillReleaseProjectionSet,
    build_skill_release_projection,
)
from research_workbench.capability import release_projection as release_projection_module
from research_workbench.capability.catalog import AcceptedSkillRegistry
from research_workbench.capability.lifecycle import SkillLifecycleSet
from research_workbench.capability.release_projection import (
    projection_from_verified_release,
)
from research_workbench.contracts.common import ContractError
from research_workbench.io import iter_documents, load_document
from research_workbench.validation import SchemaCatalog, validate_documents
from research_workbench.validation.documents import load_and_validate
from research_workbench.validation import (
    skill_release_projection_registry as projection_registry_module,
)
from research_workbench.validation.skill_release_projection_registry import (
    validate_skill_release_projections,
)
from tests.test_skill_evaluation import _live_evaluation


ROOT = Path(__file__).resolve().parents[1]

PUBLICATION_AUTHORITY_DOCUMENTS = (
    "baseline-receipt.json",
    "with-skill-receipt.json",
    "baseline-validation.json",
    "skill-validation.json",
    "evaluation.json",
    "decision.json",
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _synthetic_project(root: Path) -> tuple[str, set[str], str]:
    source_path = root / ".agents/skills/synthetic-skill/SKILL.md"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text("# Synthetic Skill\n\nBounded contract fixture.\n", encoding="utf-8")
    source_hash = hash_file(source_path)
    package_hash = hash_directory(source_path.parent)

    manifest_path = root / "registry/skills/accepted/synthetic-skill.yaml"
    manifest = {
        "schema_version": "0.1.0",
        "skill_id": "synthetic-skill",
        "version": "1.0.0",
        "kind": "method",
        "description": "Synthetic bounded release for projection contract tests.",
        "capabilities": ["document-read"],
        "applies_to_modes": ["evidence-synthesis"],
        "excludes": ["final-claim-promotion"],
        "required_tools": ["document-read"],
        "optional_tools": [],
        "permission_ceiling": {
            "filesystem": "read-only",
            "network": "forbidden",
            "external_write": False,
            "allowed_roots": [],
        },
        "runtime_boundaries": {
            "data_egress_ceiling": {
                "policy": "forbidden",
                "allowed_payloads": [],
                "forbidden_payloads": ["source-content"],
            },
            "side_effect_ceiling": {"policy": "none", "allowed_effects": []},
        },
        "input_contracts": ["bounded-document"],
        "output_contracts": ["evidence-record"],
        "context_cost": {
            "metadata": "low",
            "instructions": "low",
            "references": "on-demand",
        },
        "incompatible_with": ["unbounded-crawl"],
        "verification": {"deterministic": ["projection-contract"]},
        "source": {
            "origin": "synthetic-bounded-fixture",
            "locator": ".agents/skills/synthetic-skill/SKILL.md",
            "content_hash": f"sha256:{source_hash}",
            "package_hash": f"sha256:{package_hash}",
        },
    }
    _write_json(manifest_path, manifest)

    accepted = {
        "schema_version": "0.1.0",
        "registry_kind": "skill_accepted",
        "generated_at": "2026-08-31",
        "policy": {"new_assignment_lifecycle": "active-only"},
        "entries": [
            {
                "skill_id": "synthetic-skill",
                "version": "1.0.0",
                "status": "accepted",
                "lifecycle": "active",
                "manifest_path": "registry/skills/accepted/synthetic-skill.yaml",
                "source_path": ".agents/skills/synthetic-skill/SKILL.md",
                "content_hash": f"sha256:{source_hash}",
                "package_hash": f"sha256:{package_hash}",
                "license_status": "synthetic-fixture",
                "admission": {"scientific_correctness_claimed": False},
            }
        ],
    }
    _write_json(root / "registry/skills/accepted.json", accepted)

    evaluation = _live_evaluation(
        root, skill_id="synthetic-skill", skill_version="1.0.0"
    )
    decision_ref = "decision.json"
    decision = {
        "schema_version": "0.1.0",
        "object_type": "decision",
        "object_id": "D-SYNTHETIC-SKILL-001",
        "revision": 1,
        "status": "accepted",
        "decision": "Admit the synthetic Skill release.",
        "scope": ["fixture-candidate"],
        "reason_refs": ["SE-LIVE-001"],
        "actor": "human-reviewer",
        "timestamp": "2026-08-31T00:00:00Z",
        "metadata": {
            "skill_evaluation_id": "SE-LIVE-001",
            "skill_candidate_id": "fixture-candidate",
            "decision_owner": "human",
            "skill_admission_outcome": "accept",
        },
    }
    _write_json(root / decision_ref, decision)
    evaluation["admission"] = {
        "status": "human-decided",
        "outcome": "accept",
        "decision_ref": decision_ref,
        "rationale": "A named Human admitted the synthetic release.",
    }
    evaluation_ref = "evaluation.json"
    _write_json(root / evaluation_ref, evaluation)
    baseline_ref = "baseline-receipt.json"
    trial_ref = "with-skill-receipt.json"
    promotion_refs = ["baseline-validation.json", "skill-validation.json"]
    evidence_refs = {baseline_ref, trial_ref, evaluation_ref, *promotion_refs}
    lifecycle_ref = "synthetic-skill@1.0.0/lifecycle@1.0.0"
    lifecycle_path = root / "registry/skills/lifecycle/synthetic-skill-1.0.0.yaml"
    lifecycle = {
        "schema_version": "0.1.0",
        "lifecycle_id": "synthetic-skill",
        "lifecycle_version": "1.0.0",
        "record_scope": "current",
        "skill_ref": {
            "skill_id": "synthetic-skill",
            "version": "1.0.0",
            "manifest_path": "registry/skills/accepted/synthetic-skill.yaml",
            "content_hash": f"sha256:{source_hash}",
            "package_hash": f"sha256:{package_hash}",
        },
        "need_refs": ["NEED-SYNTHETIC"],
        "intake": {
            "state": "candidate",
            "source_refs": ["synthetic:fixture"],
            "reason": "Bounded synthetic intake.",
        },
        "evaluation": {
            "state": "evidence-ready",
            "baseline_ref": baseline_ref,
            "trial_ref": trial_ref,
            "evaluation_record_ref": evaluation_ref,
            "promotion_evidence_refs": promotion_refs,
            "reason": "Synthetic external evidence references are complete.",
        },
        "admission": {
            "state": "accepted",
            "decision_owner": "human",
            "decision_ref": decision_ref,
            "reason": "Synthetic named Human decision reference.",
        },
        "runtime_eligibility": {
            "state": "eligible",
            "eligibility_ref": "RTE-SYNTHETIC-1",
            "scopes": ["new-binding"],
            "reason": "Synthetic new-binding scope.",
        },
        "lifecycle": {
            "state": "current",
            "superseded_by_refs": [],
            "reason": "Synthetic release is current inside this fixture only.",
        },
        "boundaries": {
            "stores_trial_results": False,
            "stores_evaluation_results": False,
            "defines_benchmark_metrics": False,
            "grants_permission": False,
            "promotes_claim": False,
        },
    }
    _write_json(lifecycle_path, lifecycle)
    lifecycle_hash = hash_file(lifecycle_path)
    lifecycle_index = {
        "schema_version": "0.1.0",
        "registry_kind": "skill_lifecycle_index",
        "generated_at": "2026-08-31",
        "entries": [
            {
                "lifecycle_ref": lifecycle_ref,
                "lifecycle_id": "synthetic-skill",
                "lifecycle_version": "1.0.0",
                "document_path": "registry/skills/lifecycle/synthetic-skill-1.0.0.yaml",
                "content_hash": f"sha256:{lifecycle_hash}",
            }
        ],
    }
    _write_json(root / "registry/skills/lifecycle-v2.json", lifecycle_index)
    return lifecycle_ref, evidence_refs, decision_ref


def _publication_documents(root: Path) -> dict[Path, object]:
    paths = iter_documents([root / "registry"])
    paths.extend(
        root / relative
        for relative in PUBLICATION_AUTHORITY_DOCUMENTS
    )
    return {path: load_document(path) for path in paths}


def _loaded_publication_documents(
    root: Path, *authority_roots: Path
) -> tuple[object, list[object]]:
    paths = iter_documents([root / "registry"])
    for authority_root in authority_roots:
        paths.extend(
            authority_root / relative
            for relative in PUBLICATION_AUTHORITY_DOCUMENTS
        )
    return load_and_validate(paths)


def _copy_or_move_evaluation_closure(
    root: Path, destinations: tuple[Path, ...], *, remove_original: bool
) -> None:
    sources = [
        path
        for path in root.iterdir()
        if path.name not in {"registry", ".agents"}
    ]
    for destination in destinations:
        destination.mkdir(parents=True)
        for source in sources:
            target = destination / source.name
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
    if remove_original:
        for source in sources:
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()


def _publish_synthetic(root: Path) -> dict:
    lifecycle_ref, evidence_refs, decision_ref = _synthetic_project(root)
    projection = build_skill_release_projection(
        lifecycle_ref,
        projection_version="1.0.0",
        evidence_resolver=lambda reference: reference in evidence_refs,
        decision_resolver=lambda reference: reference == decision_ref,
        project_root=root,
    )
    projection_path = root / "registry/skills/release-projections/synthetic-skill-1.0.0.yaml"
    _write_json(projection_path, projection)
    projection_index = {
        "schema_version": "0.1.0",
        "registry_kind": "skill_release_projection_index",
        "generated_at": "2026-08-31",
        "entries": [
            {
                "projection_ref": "synthetic-skill-1.0.0@1.0.0",
                "projection_id": "synthetic-skill-1.0.0",
                "projection_version": "1.0.0",
                "release_ref": "synthetic-skill@1.0.0",
                "document_path": "registry/skills/release-projections/synthetic-skill-1.0.0.yaml",
                "content_hash": f"sha256:{hash_file(projection_path)}",
            }
        ],
    }
    _write_json(root / "registry/skills/release-projections.json", projection_index)
    return projection


class SkillReleaseProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")

    def test_empty_production_index_preserves_zero_skill_core(self) -> None:
        projection_set = SkillReleaseProjectionSet.load(project_root=ROOT)
        self.assertEqual((), projection_set.entries)
        self.assertEqual(
            [],
            self.catalog.validate(
                "skill_release_projection_index",
                load_document(ROOT / "registry/skills/release-projections.json"),
            ),
        )

    def test_verified_release_produces_narrow_deterministic_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = _publish_synthetic(root)
            lifecycle_ref, evidence_refs, decision_ref = (
                "synthetic-skill@1.0.0/lifecycle@1.0.0",
                {
                    "baseline-receipt.json",
                    "with-skill-receipt.json",
                    "evaluation.json",
                    "baseline-validation.json",
                    "skill-validation.json",
                },
                "decision.json",
            )
            second = build_skill_release_projection(
                lifecycle_ref,
                projection_version="1.0.0",
                evidence_resolver=lambda reference: reference in evidence_refs,
                decision_resolver=lambda reference: reference == decision_ref,
                project_root=root,
            )
            self.assertEqual(first, second)
            self.assertEqual([], self.catalog.validate("skill_release_projection", first))
            self.assertEqual(
                "synthetic-skill@1.0.0", first["release"]["release_ref"]
            )
            self.assertEqual(
                ["document-read"], first["runtime_contract"]["provided_capabilities"]
            )
            forbidden = {
                "need_refs",
                "evaluation",
                "trial_ref",
                "evaluation_record_ref",
                "promotion_evidence_refs",
                "metrics",
                "scores",
                "private_score",
                "need_text",
                "trial_results",
                "reason",
                "deliberation",
            }

            def keys(value):
                if isinstance(value, dict):
                    yield from value
                    for nested in value.values():
                        yield from keys(nested)
                elif isinstance(value, list):
                    for nested in value:
                        yield from keys(nested)

            self.assertFalse(forbidden.intersection(keys(first)))
            self.assertTrue(all(value is False for value in first["boundaries"].values()))
            loaded = SkillReleaseProjectionSet.load(project_root=root)
            parsed = loaded.require(("synthetic-skill-1.0.0@1.0.0",))[0]
            self.assertEqual("synthetic-skill-1.0.0@1.0.0", parsed.reference)
            self.assertEqual(first["runtime_contract"], parsed.runtime_contract)

    def test_publisher_requires_external_evidence_human_decision_and_runtime_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lifecycle_ref, evidence_refs, decision_ref = _synthetic_project(root)
            cases = (
                (lambda _reference: False, lambda reference: reference == decision_ref),
                (lambda reference: reference in evidence_refs, lambda _reference: False),
            )
            for index, (evidence_resolver, decision_resolver) in enumerate(cases):
                with self.subTest(case=index):
                    with self.assertRaisesRegex(ValueError, "not verified"):
                        build_skill_release_projection(
                            lifecycle_ref,
                            projection_version="1.0.0",
                            evidence_resolver=evidence_resolver,
                            decision_resolver=decision_resolver,
                            project_root=root,
                        )

            manifest_path = root / "registry/skills/accepted/synthetic-skill.yaml"
            manifest = load_document(manifest_path)
            manifest.pop("runtime_boundaries")
            _write_json(manifest_path, manifest)
            with self.assertRaisesRegex(ValueError, "runtime_boundaries"):
                build_skill_release_projection(
                    lifecycle_ref,
                    projection_version="1.0.0",
                    evidence_resolver=lambda reference: reference in evidence_refs,
                    decision_resolver=lambda reference: reference == decision_ref,
                    project_root=root,
                )

    def test_legacy_repository_skills_cannot_be_projected(self) -> None:
        with self.assertRaisesRegex(ValueError, "not verified"):
            build_skill_release_projection(
                "literature-evidence-extraction@0.1.0/lifecycle@1.0.0",
                projection_version="1.0.0",
                evidence_resolver=lambda _reference: True,
                decision_resolver=lambda _reference: True,
                project_root=ROOT,
            )

    def test_projection_registry_and_derivation_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            documents = _publication_documents(root)
            self.assertEqual([], validate_documents(documents))

            projection_path = root / "registry/skills/release-projections/synthetic-skill-1.0.0.yaml"
            index_path = root / "registry/skills/release-projections.json"
            mutations = (
                (
                    lambda values: values[index_path]["entries"][0].__setitem__(
                        "content_hash", "sha256:" + "0" * 64
                    ),
                    "SKILL-RELEASE-PROJECTION-HASH-MISMATCH",
                ),
                (
                    lambda values: values[projection_path]["runtime_contract"].__setitem__(
                        "provided_capabilities", ["rewritten-capability"]
                    ),
                    "SKILL-RELEASE-PROJECTION-DERIVATION-DRIFT",
                ),
                (
                    lambda values: values[projection_path]["admission_provenance"].__setitem__(
                        "decision_ref", "DECISION-SUBSTITUTED"
                    ),
                    "SKILL-RELEASE-PROJECTION-PROVENANCE-DRIFT",
                ),
                (
                    lambda values: values[projection_path]["release"].__setitem__(
                        "manifest_sha256", "sha256:" + "0" * 64
                    ),
                    "SKILL-RELEASE-PROJECTION-MANIFEST-HASH-MISMATCH",
                ),
            )
            with patch.object(
                projection_registry_module,
                "_publication_authority_verified",
                return_value=True,
            ):
                for mutate, expected in mutations:
                    with self.subTest(expected=expected):
                        changed = copy.deepcopy(documents)
                        mutate(changed)
                        self.assertIn(
                            expected,
                            {issue.code for issue in validate_documents(changed)},
                        )

            injected = copy.deepcopy(documents[projection_path])
            injected["trial_results"] = {"score": 1}
            self.assertTrue(self.catalog.validate("skill_release_projection", injected))

    def test_repository_projection_revalidates_external_evidence_and_human_decision(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            self.assertEqual([], validate_documents(_publication_documents(root)))

            lifecycle_path = (
                root / "registry/skills/lifecycle/synthetic-skill-1.0.0.yaml"
            )
            lifecycle = load_document(lifecycle_path)
            lifecycle["evaluation"].update(
                {
                    "baseline_ref": "MISSING-BASELINE",
                    "trial_ref": "MISSING-TRIAL",
                    "evaluation_record_ref": "MISSING-EVALUATION",
                    "promotion_evidence_refs": ["MISSING-PROMOTION"],
                }
            )
            lifecycle["admission"]["decision_ref"] = "MISSING-DECISION"
            _write_json(lifecycle_path, lifecycle)

            lifecycle_index_path = root / "registry/skills/lifecycle-v2.json"
            lifecycle_index = load_document(lifecycle_index_path)
            lifecycle_index["entries"][0]["content_hash"] = (
                f"sha256:{hash_file(lifecycle_path)}"
            )
            _write_json(lifecycle_index_path, lifecycle_index)

            projection_path = (
                root
                / "registry/skills/release-projections/synthetic-skill-1.0.0.yaml"
            )
            projection = load_document(projection_path)
            projection["admission_provenance"].update(
                {
                    "lifecycle_content_hash": lifecycle_index["entries"][0][
                        "content_hash"
                    ],
                    "decision_ref": "MISSING-DECISION",
                }
            )
            _write_json(projection_path, projection)

            projection_index_path = root / "registry/skills/release-projections.json"
            projection_index = load_document(projection_index_path)
            projection_index["entries"][0]["content_hash"] = (
                f"sha256:{hash_file(projection_path)}"
            )
            _write_json(projection_index_path, projection_index)

            codes = {
                issue.code
                for issue in validate_documents(_publication_documents(root))
            }
            self.assertIn("SKILL-RELEASE-PROJECTION-AUTHORITY-UNVERIFIED", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-HASH-MISMATCH", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-PROVENANCE-DRIFT", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-DERIVATION-DRIFT", codes)

    def test_repository_projection_rejects_shadow_only_authority_closure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            _, initial_issues = _loaded_publication_documents(root, root)
            self.assertEqual([], initial_issues)

            shadow = root / "shadow"
            _copy_or_move_evaluation_closure(
                root, (shadow,), remove_original=True
            )
            _, issues = _loaded_publication_documents(root, shadow)
            codes = {issue.code for issue in issues}
            self.assertIn("SKILL-RELEASE-PROJECTION-AUTHORITY-UNVERIFIED", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-HASH-MISMATCH", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-PROVENANCE-DRIFT", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-DERIVATION-DRIFT", codes)

    def test_repository_projection_rejects_ambiguous_shadow_authority_closure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            shadow_a = root / "shadow-a"
            shadow_b = root / "shadow-b"
            _copy_or_move_evaluation_closure(
                root, (shadow_a, shadow_b), remove_original=True
            )

            _, issues = _loaded_publication_documents(root, shadow_a, shadow_b)
            codes = {issue.code for issue in issues}
            self.assertIn("SKILL-RELEASE-PROJECTION-AUTHORITY-UNVERIFIED", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-HASH-MISMATCH", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-PROVENANCE-DRIFT", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-DERIVATION-DRIFT", codes)

    def test_repository_projection_rejects_cross_root_stitched_publication(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            shadow = root / "shadow"
            _copy_or_move_evaluation_closure(
                root, (shadow,), remove_original=False
            )

            projection_index = root / "registry/skills/release-projections.json"
            shadow_index = shadow / "registry/skills/release-projections.json"
            shadow_index.parent.mkdir(parents=True)
            shutil.move(projection_index, shadow_index)
            paths = iter_documents([root / "registry", shadow / "registry"])
            paths.extend(
                shadow / relative
                for relative in PUBLICATION_AUTHORITY_DOCUMENTS
            )

            _, issues = load_and_validate(paths)
            codes = {issue.code for issue in issues}
            self.assertIn("SKILL-RELEASE-PROJECTION-DOCUMENT-MISSING", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-HASH-MISMATCH", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-PROVENANCE-DRIFT", codes)
            self.assertNotIn("SKILL-RELEASE-PROJECTION-DERIVATION-DRIFT", codes)

    def test_repository_publication_authority_helpers_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            documents = _publication_documents(root)
            record = next(
                iter(
                    projection_registry_module._lifecycle_entries(
                        documents, root=root
                    ).values()
                )
            )[1].record
            evaluation_path = root / "evaluation.json"

            self.assertEqual(
                root,
                projection_registry_module._repository_root_for(
                    evaluation_path, "evaluation.json"
                ),
            )
            self.assertIsNone(
                projection_registry_module._repository_root_for(
                    evaluation_path, "../evaluation.json"
                )
            )
            self.assertIsNone(
                projection_registry_module._repository_root_for(
                    evaluation_path, "/evaluation.json"
                )
            )
            self.assertIsNone(
                projection_registry_module._loaded_document_at_root(
                    documents, root, "../evaluation.json"
                )
            )
            self.assertIsNone(
                projection_registry_module._loaded_document_at_root(
                    documents, root, str(evaluation_path)
                )
            )
            ambiguous_documents = dict(documents)
            ambiguous_documents[
                root / "alias" / ".." / "evaluation.json"
            ] = documents[evaluation_path]
            self.assertIsNone(
                projection_registry_module._loaded_document_at_root(
                    ambiguous_documents, root, "evaluation.json"
                )
            )
            self.assertEqual(
                set(),
                projection_registry_module._arm_evidence_paths(
                    {
                        "cases": [
                            None,
                            {"arms": []},
                            {"arms": {"baseline": []}},
                            {"arms": {"baseline": {"output_ref": [], "receipt": 1}}},
                        ]
                    },
                    "baseline",
                ),
            )

            no_evaluation = replace(
                record,
                evaluation=replace(record.evaluation, evaluation_record_ref=None),
            )
            no_decision = replace(
                record,
                admission=replace(record.admission, decision_ref=None),
            )
            self.assertFalse(
                projection_registry_module._publication_authority_verified(
                    documents, no_evaluation, root=root
                )
            )
            self.assertFalse(
                projection_registry_module._publication_authority_verified(
                    documents, no_decision, root=root
                )
            )

            def assert_rejected(mutate_documents, changed_record=record) -> None:
                changed = copy.deepcopy(documents)
                mutate_documents(changed)
                self.assertFalse(
                    projection_registry_module._publication_authority_verified(
                        changed, changed_record, root=root
                    )
                )

            evaluation_ref = root / "evaluation.json"
            decision_ref = root / "decision.json"
            assert_rejected(lambda values: values.pop(evaluation_ref))
            assert_rejected(
                lambda values: values[evaluation_ref].pop("skill_version")
            )
            assert_rejected(
                lambda values: values[evaluation_ref].update(
                    {"skill_id": "other-skill"}
                )
            )
            assert_rejected(
                lambda values: values[evaluation_ref].update({"admission": []})
            )
            assert_rejected(lambda values: values.pop(decision_ref))
            assert_rejected(
                lambda values: values[decision_ref].update({"object_type": "claim"})
            )

            accepted_assessment = SimpleNamespace(
                verdict="human-decision-recorded"
            )
            rejected_assessment = SimpleNamespace(verdict="not-eligible")
            with patch(
                "research_workbench.evaluation.skill_evaluation.assess_skill_evaluation",
                return_value=rejected_assessment,
            ):
                self.assertFalse(
                    projection_registry_module._publication_authority_verified(
                        documents, record, root=root
                    )
                )

            wrong_baseline = replace(
                record,
                evaluation=replace(
                    record.evaluation, baseline_ref="skill-validation.json"
                ),
            )
            no_promotion = replace(
                record,
                evaluation=replace(
                    record.evaluation, promotion_evidence_refs=()
                ),
            )
            ineligible = replace(
                record,
                runtime_eligibility=replace(
                    record.runtime_eligibility, state="ineligible"
                ),
            )
            with patch(
                "research_workbench.evaluation.skill_evaluation.assess_skill_evaluation",
                return_value=accepted_assessment,
            ):
                for changed_record in (wrong_baseline, no_promotion, ineligible):
                    with self.subTest(record=changed_record):
                        self.assertFalse(
                            projection_registry_module._publication_authority_verified(
                                documents, changed_record, root=root
                            )
                        )
                missing_evidence = copy.deepcopy(documents)
                missing_evidence.pop(root / "baseline-receipt.json")
                self.assertFalse(
                    projection_registry_module._publication_authority_verified(
                        missing_evidence, record, root=root
                    )
                )

    def test_projection_set_schema_boundary_is_fail_closed(self) -> None:
        def mutate_projection(root: Path, index: dict, mutate) -> None:
            projection_path = (
                root
                / "registry/skills/release-projections/synthetic-skill-1.0.0.yaml"
            )
            projection = load_document(projection_path)
            mutate(projection)
            _write_json(projection_path, projection)
            index["entries"][0]["content_hash"] = (
                f"sha256:{hash_file(projection_path)}"
            )

        cases = (
            (
                "index schema invalid",
                lambda _root, index: index.__setitem__("private_score", 1),
            ),
            (
                "index schema invalid",
                lambda _root, index: index["entries"][0].__setitem__(
                    "need_text", "must not enter Runtime"
                ),
            ),
            (
                "Projection schema invalid",
                lambda root, index: mutate_projection(
                    root, index, lambda value: value.__setitem__("evaluation", {})
                ),
            ),
            (
                "Projection schema invalid",
                lambda root, index: mutate_projection(
                    root,
                    index,
                    lambda value: value["runtime_contract"].__setitem__(
                        "evaluation", {}
                    ),
                ),
            ),
            (
                "Projection schema invalid",
                lambda root, index: mutate_projection(
                    root,
                    index,
                    lambda value: value["eligibility"].__setitem__(
                        "private_score", 1
                    ),
                ),
            ),
            (
                "Projection schema invalid",
                lambda root, index: mutate_projection(
                    root,
                    index,
                    lambda value: value["release"].__setitem__(
                        "need_text", "must not enter Runtime"
                    ),
                ),
            ),
            (
                "Projection schema invalid",
                lambda root, index: mutate_projection(
                    root,
                    index,
                    lambda value: value["boundaries"].pop(
                        "stores_lifecycle_history"
                    ),
                ),
            ),
        )
        for expected, mutate in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _publish_synthetic(root)
                index_path = root / "registry/skills/release-projections.json"
                index = load_document(index_path)
                mutate(root, index)
                _write_json(index_path, index)
                with self.assertRaisesRegex(ValueError, expected):
                    SkillReleaseProjectionSet.load(project_root=root)

    def test_projection_set_rejects_malformed_or_ambiguous_publication(self) -> None:
        def duplicate_entry(index: dict, **changes: object) -> None:
            added = copy.deepcopy(index["entries"][0])
            added.update(changes)
            index["entries"].append(added)

        def non_object_projection(root: Path, index: dict) -> None:
            projection_path = (
                root
                / "registry/skills/release-projections/synthetic-skill-1.0.0.yaml"
            )
            _write_json(projection_path, [])
            index["entries"][0]["content_hash"] = f"sha256:{hash_file(projection_path)}"

        cases = (
            (
                "index schema invalid",
                lambda _root, index: index.update({"entries": [None]}),
            ),
            (
                "index schema invalid",
                lambda _root, index: index["entries"][0].update(
                    {"content_hash": "sha256:short"}
                ),
            ),
            (
                "index schema invalid",
                lambda _root, index: index["entries"][0].update(
                    {"content_hash": "sha256:" + "z" * 64}
                ),
            ),
            (
                "duplicate Skill Release Projection identity",
                lambda _root, index: duplicate_entry(index),
            ),
            (
                "duplicate Skill Release Projection path",
                lambda _root, index: duplicate_entry(
                    index,
                    projection_ref="other@1.0.0",
                    projection_id="other",
                    release_ref="other-skill@1.0.0",
                ),
            ),
            (
                "multiple current projections",
                lambda _root, index: duplicate_entry(
                    index,
                    projection_ref="other@1.0.0",
                    projection_id="other",
                    document_path="registry/skills/release-projections/other.yaml",
                ),
            ),
            (
                "index schema invalid",
                lambda _root, index: index["entries"][0].update(
                    {"document_path": "../outside.yaml"}
                ),
            ),
            (
                "path is missing or escapes root",
                lambda _root, index: index["entries"][0].update(
                    {"document_path": "registry/skills/release-projections/missing.yaml"}
                ),
            ),
            (
                "content drift",
                lambda _root, index: index["entries"][0].update(
                    {"content_hash": "sha256:" + "0" * 64}
                ),
            ),
            ("is not an object", non_object_projection),
            (
                "identity mismatch",
                lambda _root, index: index["entries"][0].update(
                    {
                        "projection_ref": "substituted@1.0.0",
                        "projection_id": "substituted",
                    }
                ),
            ),
        )
        for expected, mutate in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _publish_synthetic(root)
                index_path = root / "registry/skills/release-projections.json"
                index = load_document(index_path)
                mutate(root, index)
                _write_json(index_path, index)
                with self.assertRaisesRegex(ValueError, expected):
                    SkillReleaseProjectionSet.load(project_root=root)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            index_path = root / "registry/skills/release-projections.json"
            absolute = SkillReleaseProjectionSet.load(index_path, project_root=root)
            reference = "synthetic-skill-1.0.0@1.0.0"
            self.assertEqual(reference, absolute.require(reference)[0].reference)
            with self.assertRaisesRegex(ValueError, "selected more than once"):
                absolute.require((reference, reference))
            with self.assertRaisesRegex(ValueError, "is not indexed"):
                absolute.require(("missing@1.0.0",))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            index_path = root / "registry/skills/release-projections.json"
            for invalid in (
                [],
                {"registry_kind": "not-a-projection-index", "entries": []},
                {"registry_kind": "skill_release_projection_index", "entries": {}},
            ):
                with self.subTest(invalid=invalid):
                    _write_json(index_path, invalid)
                    with self.assertRaises(ValueError):
                        SkillReleaseProjectionSet.load(project_root=root)

    def test_publisher_defensive_guards_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lifecycle_ref, evidence_refs, decision_ref = _synthetic_project(root)
            common = {
                "projection_version": "1.0.0",
                "evidence_resolver": lambda reference: reference in evidence_refs,
                "decision_resolver": lambda reference: reference == decision_ref,
                "project_root": root,
            }
            with self.assertRaisesRegex(ValueError, "Lifecycle is not indexed"):
                build_skill_release_projection("missing/lifecycle@1.0.0", **common)

            accepted_path = root / "registry/skills/accepted.json"
            accepted_document = load_document(accepted_path)
            accepted_document["entries"][0]["lifecycle"] = "deprecated"
            _write_json(accepted_path, accepted_document)
            with self.assertRaisesRegex(ValueError, "active accepted"):
                build_skill_release_projection(lifecycle_ref, **common)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lifecycle_ref, evidence_refs, decision_ref = _synthetic_project(root)
            lifecycle_path = (
                root / "registry/skills/lifecycle/synthetic-skill-1.0.0.yaml"
            )
            lifecycle_document = load_document(lifecycle_path)
            lifecycle_document["skill_ref"]["content_hash"] = "sha256:" + "0" * 64
            _write_json(lifecycle_path, lifecycle_document)
            lifecycle_index_path = root / "registry/skills/lifecycle-v2.json"
            lifecycle_index = load_document(lifecycle_index_path)
            lifecycle_index["entries"][0]["content_hash"] = (
                f"sha256:{hash_file(lifecycle_path)}"
            )
            _write_json(lifecycle_index_path, lifecycle_index)
            with self.assertRaisesRegex(ValueError, "identity/hash disagree"):
                build_skill_release_projection(
                    lifecycle_ref,
                    projection_version="1.0.0",
                    evidence_resolver=lambda reference: reference in evidence_refs,
                    decision_resolver=lambda reference: reference == decision_ref,
                    project_root=root,
                )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lifecycle_ref, evidence_refs, decision_ref = _synthetic_project(root)
            lifecycle_entry = SkillLifecycleSet.load(project_root=root).entries[0]
            accepted_entry = AcceptedSkillRegistry.load(project_root=root).entries[0]
            no_decision = replace(
                lifecycle_entry,
                record=replace(
                    lifecycle_entry.record,
                    admission=replace(
                        lifecycle_entry.record.admission,
                        decision_ref=None,
                    ),
                ),
            )
            with self.assertRaisesRegex(ValueError, "no Human admission decision"):
                projection_from_verified_release(
                    lifecycle_entry=no_decision,
                    manifest=accepted_entry.manifest,
                    manifest_sha256="a" * 64,
                    projection_version="1.0.0",
                )

            for invalid_hash in ("short", "z" * 64):
                with self.subTest(invalid_hash=invalid_hash), self.assertRaisesRegex(
                    ValueError, "expected a SHA-256 digest"
                ):
                    projection_from_verified_release(
                        lifecycle_entry=lifecycle_entry,
                        manifest=accepted_entry.manifest,
                        manifest_sha256=invalid_hash,
                        projection_version="1.0.0",
                    )

            def call_with_paths(
                manifest_path: str,
                *,
                manifest_document: object | None,
            ) -> None:
                changed_record = replace(
                    lifecycle_entry.record,
                    skill_ref=replace(
                        lifecycle_entry.record.skill_ref,
                        manifest_path=manifest_path,
                    ),
                )
                changed_lifecycle = replace(lifecycle_entry, record=changed_record)
                changed_release = replace(accepted_entry, manifest_path=manifest_path)
                if manifest_document is not None:
                    _write_json(root / manifest_path, manifest_document)
                with (
                    patch.object(
                        release_projection_module.AcceptedSkillRegistry,
                        "load",
                        return_value=SimpleNamespace(entries=(changed_release,)),
                    ),
                    patch.object(
                        release_projection_module.SkillLifecycleSet,
                        "load",
                        return_value=SimpleNamespace(entries=(changed_lifecycle,)),
                    ),
                ):
                    build_skill_release_projection(
                        lifecycle_ref,
                        projection_version="1.0.0",
                        evidence_resolver=lambda reference: reference in evidence_refs,
                        decision_resolver=lambda reference: reference == decision_ref,
                        project_root=root,
                    )

            with self.assertRaisesRegex(ValueError, "manifest is missing"):
                call_with_paths("registry/skills/accepted/missing.yaml", manifest_document=None)
            with self.assertRaisesRegex(ContractError, "must be an object"):
                call_with_paths("registry/skills/accepted/not-object.yaml", manifest_document=[])
            mismatched_manifest = load_document(
                root / "registry/skills/accepted/synthetic-skill.yaml"
            )
            mismatched_manifest["skill_id"] = "substituted-skill"
            with self.assertRaisesRegex(ValueError, "manifest identity disagrees"):
                call_with_paths(
                    "registry/skills/accepted/substituted.yaml",
                    manifest_document=mismatched_manifest,
                )

    def test_projection_registry_adversarial_surface_is_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _publish_synthetic(root)
            documents = _publication_documents(root)
            index_path = root / "registry/skills/release-projections.json"
            projection_path = (
                root
                / "registry/skills/release-projections/synthetic-skill-1.0.0.yaml"
            )
            accepted_path = root / "registry/skills/accepted.json"
            lifecycle_index_path = root / "registry/skills/lifecycle-v2.json"
            lifecycle_path = (
                root / "registry/skills/lifecycle/synthetic-skill-1.0.0.yaml"
            )
            manifest_path = root / "registry/skills/accepted/synthetic-skill.yaml"

            self.assertEqual([], validate_skill_release_projections({}))

            noise = copy.deepcopy(documents)
            noise[accepted_path]["entries"].insert(0, [])
            invalid_lifecycle_path = root / "registry/skills/lifecycle/invalid.yaml"
            noise[invalid_lifecycle_path] = {"lifecycle_id": "invalid"}
            noise[lifecycle_index_path]["entries"] = [
                [],
                {
                    "lifecycle_ref": 1,
                    "document_path": 2,
                    "content_hash": 3,
                },
                {
                    "lifecycle_ref": "missing/lifecycle@1.0.0",
                    "lifecycle_id": "missing",
                    "lifecycle_version": "1.0.0",
                    "document_path": "registry/skills/lifecycle/missing.yaml",
                    "content_hash": "sha256:" + "0" * 64,
                },
                {
                    "lifecycle_ref": "invalid/lifecycle@1.0.0",
                    "lifecycle_id": "invalid",
                    "lifecycle_version": "1.0.0",
                    "document_path": "registry/skills/lifecycle/invalid.yaml",
                    "content_hash": "sha256:" + "0" * 64,
                },
                *noise[lifecycle_index_path]["entries"],
            ]
            noise[index_path]["entries"] = [
                [],
                {
                    "projection_ref": 1,
                    "projection_id": 2,
                    "projection_version": 3,
                    "release_ref": 4,
                    "document_path": 5,
                },
                *noise[index_path]["entries"],
            ]
            with patch.object(
                projection_registry_module,
                "_publication_authority_verified",
                return_value=True,
            ):
                self.assertEqual([], validate_skill_release_projections(noise))

            def assert_issue(expected: str, mutate, *, verify_authority: bool = False) -> None:
                changed = copy.deepcopy(documents)
                mutate(changed)
                authority = (
                    patch.object(
                        projection_registry_module,
                        "_publication_authority_verified",
                        return_value=True,
                    )
                    if not verify_authority
                    else contextlib.nullcontext()
                )
                with authority:
                    self.assertIn(
                        expected,
                        {issue.code for issue in validate_skill_release_projections(changed)},
                    )

            assert_issue(
                "SKILL-RELEASE-PROJECTION-INDEX-MISSING",
                lambda values: values.pop(index_path),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-INDEX-DUPLICATE",
                lambda values: values.__setitem__(
                    root / "registry/skills/release-projections-copy.json",
                    copy.deepcopy(values[index_path]),
                ),
            )

            def add_index_entry(values: dict, **changes: object) -> None:
                entry = copy.deepcopy(values[index_path]["entries"][0])
                entry.update(changes)
                values[index_path]["entries"].append(entry)

            assert_issue(
                "SKILL-RELEASE-PROJECTION-IDENTITY-DUPLICATE",
                lambda values: add_index_entry(values),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-PATH-DUPLICATE",
                lambda values: add_index_entry(
                    values,
                    projection_ref="other@1.0.0",
                    projection_id="other",
                    release_ref="other@1.0.0",
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-RELEASE-DUPLICATE",
                lambda values: add_index_entry(
                    values,
                    projection_ref="other@1.0.0",
                    projection_id="other",
                    document_path="registry/skills/release-projections/other.yaml",
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-DOCUMENT-MISSING",
                lambda values: values[index_path]["entries"][0].update(
                    {"document_path": "registry/skills/release-projections/missing.yaml"}
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-DOCUMENT-KIND",
                lambda values: values[index_path]["entries"][0].update(
                    {"document_path": "registry/skills/accepted/synthetic-skill.yaml"}
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-CONTRACT",
                lambda values: values[projection_path].pop("projection_version"),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-IDENTITY-MISMATCH",
                lambda values: values[index_path]["entries"][0].update(
                    {"release_ref": "substituted@1.0.0"}
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-UNINDEXED",
                lambda values: values[index_path].update({"entries": []}),
            )

            def relocate_projection(values: dict) -> None:
                relocated = root / "archive/synthetic-projection.yaml"
                values[relocated] = copy.deepcopy(values[projection_path])
                values[index_path]["entries"][0]["document_path"] = (
                    "archive/synthetic-projection.yaml"
                )

            assert_issue("SKILL-RELEASE-PROJECTION-PATH-MISMATCH", relocate_projection)
            assert_issue(
                "SKILL-RELEASE-PROJECTION-RELEASE-INELIGIBLE",
                lambda values: values[accepted_path]["entries"][0].update(
                    {"lifecycle": "deprecated"}
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-LIFECYCLE-MISSING",
                lambda values: values[projection_path]["admission_provenance"].update(
                    {"lifecycle_ref": "missing/lifecycle@1.0.0"}
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-AUTHORITY-UNVERIFIED",
                lambda values: values[lifecycle_path]["runtime_eligibility"].update(
                    {"state": "ineligible"}
                ),
                verify_authority=True,
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-RELEASE-DRIFT",
                lambda values: values[projection_path]["release"].update(
                    {"skill_id": "substituted-skill"}
                ),
            )

            def remove_manifest(values: dict) -> None:
                missing = "registry/skills/accepted/missing.yaml"
                values[projection_path]["release"]["manifest_path"] = missing
                values[accepted_path]["entries"][0]["manifest_path"] = missing

            assert_issue("SKILL-RELEASE-PROJECTION-MANIFEST-MISSING", remove_manifest)
            assert_issue(
                "SKILL-RELEASE-PROJECTION-DERIVATION-BLOCKED",
                lambda values: values.__setitem__(
                    manifest_path,
                    {"skill_id": "synthetic-skill"},
                ),
            )
            assert_issue(
                "SKILL-RELEASE-PROJECTION-CONTRACT",
                lambda values: values[projection_path].update({"release": []}),
            )


if __name__ == "__main__":
    unittest.main()
