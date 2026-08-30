import copy
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.artifacts.integrity import hash_directory, hash_file
from research_workbench.capability import (
    SkillReleaseProjectionSet,
    build_skill_release_projection,
)
from research_workbench.io import iter_documents, load_document
from research_workbench.validation import SchemaCatalog, validate_documents


ROOT = Path(__file__).resolve().parents[1]


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

    evidence_refs = {"BASELINE-SYNTHETIC", "TRIAL-SYNTHETIC", "EVAL-SYNTHETIC"}
    decision_ref = "DECISION-ACCEPT-SYNTHETIC"
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
            "baseline_ref": "BASELINE-SYNTHETIC",
            "trial_ref": "TRIAL-SYNTHETIC",
            "evaluation_record_ref": "EVAL-SYNTHETIC",
            "promotion_evidence_refs": ["EVAL-SYNTHETIC", "TRIAL-SYNTHETIC"],
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
                {"BASELINE-SYNTHETIC", "TRIAL-SYNTHETIC", "EVAL-SYNTHETIC"},
                "DECISION-ACCEPT-SYNTHETIC",
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
            documents = {
                path: load_document(path)
                for path in iter_documents([root / "registry"])
            }
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


if __name__ == "__main__":
    unittest.main()
