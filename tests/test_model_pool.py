import copy
import unittest

from research_workbench.adapters.models import (
    ApiSessionLimits,
    Capability,
    DataPolicy,
    ModelAssignment,
    ModelPool,
)
from research_workbench.tasks import FileReference
from research_workbench.validation import SchemaCatalog


def pool_document() -> dict:
    return {
        "schema_version": "0.1.0",
        "registry_kind": "model_pool",
        "pool_id": "test-pool",
        "selection_policy": "explicit-slot-only",
        "slots": [
            {
                "slot_id": "primary",
                "role": "primary",
                "provider_adapter": "openai-responses",
                "model_env": "RWB_PRIMARY_MODEL",
                "enabled": True,
                "capabilities": ["text", "tools", "reasoning"],
                "reasoning_effort": "high",
            },
            {
                "slot_id": "worker",
                "role": "worker",
                "provider_adapter": "anthropic-messages",
                "model_env": "RWB_WORKER_MODEL",
                "enabled": True,
                "capabilities": ["text", "tools"],
            },
            {
                "slot_id": "vision",
                "role": "specialist",
                "provider_adapter": "google-generate-content",
                "model_env": "RWB_VISION_MODEL",
                "enabled": False,
                "capabilities": ["text", "images"],
                "specialties": ["images"],
            },
        ],
    }


class ModelPoolTests(unittest.TestCase):
    def _assignment(
        self, pool: ModelPool | None = None, **overrides: object
    ) -> ModelAssignment:
        pool = pool or ModelPool.from_mapping(pool_document())
        values = {
            "attempt_id": "A-001",
            "task_id": "TASK-001",
            "task_revision": 1,
            "agent_profile_ref": FileReference(
                "registry/agents/tester.yaml", "a" * 64
            ),
            "selection_reason": "The Profile explicitly pins the primary slot.",
            "effective_data_policy": DataPolicy(
                zero_data_retention_required=True,
                training_opt_out_required=True,
                allowed_regions=("us",),
            ),
            "execution_limits": ApiSessionLimits(
                max_model_turns=2,
                max_tool_calls=3,
                max_parallel_tool_calls=1,
                max_tool_result_chars=4096,
                max_output_tokens_per_turn=1024,
                max_seconds=30.0,
                max_total_tokens=4096,
                max_provider_reported_cost=1.25,
                allowed_tool_side_effects=frozenset({"read-only"}),
                max_compute_values_per_call=64,
            ),
        }
        values.update(overrides)
        return pool.assign(
            "primary",
            environment={"RWB_PRIMARY_MODEL": "reasoning-model"},
            **values,
        )

    def test_selection_is_explicit_and_pins_one_binding(self) -> None:
        pool = ModelPool.from_mapping(pool_document())
        binding = pool.bind("worker", environment={"RWB_WORKER_MODEL": "economy-model"})
        self.assertEqual("worker", binding.slot_id)
        self.assertEqual("anthropic-messages", binding.provider_adapter)
        self.assertEqual("economy-model", binding.model)
        self.assertEqual({Capability.TEXT, Capability.TOOLS}, set(binding.capabilities))

    def test_unknown_slot_does_not_fall_back(self) -> None:
        pool = ModelPool.from_mapping(pool_document())
        with self.assertRaises(KeyError):
            pool.bind("cheap-ish", environment={"RWB_WORKER_MODEL": "economy-model"})

    def test_missing_selected_model_does_not_fall_back_to_another_slot(self) -> None:
        pool = ModelPool.from_mapping(pool_document())

        with self.assertRaisesRegex(ValueError, "RWB_PRIMARY_MODEL"):
            pool.bind("primary", environment={"RWB_WORKER_MODEL": "economy-model"})

    def test_disabled_specialist_cannot_be_selected(self) -> None:
        pool = ModelPool.from_mapping(pool_document())
        with self.assertRaisesRegex(ValueError, "disabled"):
            pool.bind("vision", environment={"RWB_VISION_MODEL": "vision-model"})

    def test_probe_never_reads_environment_implicitly(self) -> None:
        pool = ModelPool.from_mapping(pool_document())
        report = pool.probe()
        self.assertFalse(report["environment_checked"])
        self.assertTrue(all(slot["model_status"] == "unchecked" for slot in report["slots"]))

    def test_reasoning_effort_requires_declared_capability(self) -> None:
        document = pool_document()
        document["slots"][1]["reasoning_effort"] = "low"
        with self.assertRaisesRegex(ValueError, "without reasoning capability"):
            ModelPool.from_mapping(document)

    def test_config_hash_normalizes_defaults_and_covers_all_slot_controls(self) -> None:
        baseline_document = pool_document()
        baseline_hash = ModelPool.from_mapping(baseline_document).config_hash
        equivalent = copy.deepcopy(baseline_document)
        equivalent["warning"] = "Informational text does not affect execution."
        equivalent["slots"].reverse()
        worker = next(slot for slot in equivalent["slots"] if slot["slot_id"] == "worker")
        worker["reasoning_effort"] = None
        worker["specialties"] = []
        worker["capabilities"].reverse()

        self.assertEqual(64, len(baseline_hash))
        self.assertEqual(baseline_hash, ModelPool.from_mapping(equivalent).config_hash)

        mutations = (
            ("pool", lambda value: value.__setitem__("pool_id", "drifted-pool")),
            ("slot", lambda value: value["slots"][0].__setitem__("slot_id", "main")),
            ("role", lambda value: value["slots"][0].__setitem__("role", "worker")),
            (
                "adapter",
                lambda value: value["slots"][0].__setitem__(
                    "provider_adapter", "other-adapter"
                ),
            ),
            (
                "model-env",
                lambda value: value["slots"][0].__setitem__(
                    "model_env", "RWB_OTHER_MODEL"
                ),
            ),
            ("enabled", lambda value: value["slots"][0].__setitem__("enabled", False)),
            (
                "disabled",
                lambda value: value["slots"][2].__setitem__("enabled", True),
            ),
            (
                "reasoning",
                lambda value: value["slots"][0].__setitem__(
                    "reasoning_effort", "medium"
                ),
            ),
            (
                "capabilities",
                lambda value: value["slots"][0]["capabilities"].append("streaming"),
            ),
            (
                "specialties",
                lambda value: value["slots"][2].__setitem__(
                    "specialties", ["scientific-images"]
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                drifted = copy.deepcopy(baseline_document)
                mutate(drifted)
                self.assertNotEqual(
                    baseline_hash,
                    ModelPool.from_mapping(drifted).config_hash,
                )

        policy_drift = copy.deepcopy(baseline_document)
        policy_drift["selection_policy"] = "automatic"
        with self.assertRaisesRegex(ValueError, "unsupported model selection policy"):
            ModelPool.from_mapping(policy_drift)

    def test_assign_uses_internal_hash_and_rejects_forged_or_drifted_hash(self) -> None:
        pool = ModelPool.from_mapping(pool_document())
        assignment = self._assignment(pool)
        compatible = self._assignment(
            pool,
            pool_config_hash=f"sha256:{pool.config_hash.upper()}",
        )

        self.assertEqual(pool.config_hash, assignment.pool_config_hash)
        self.assertEqual(pool.config_hash, compatible.pool_config_hash)
        with self.assertRaisesRegex(ValueError, "does not match the canonical ModelPool"):
            self._assignment(pool, pool_config_hash="b" * 64)

        drifted_document = pool_document()
        drifted_document["slots"][0]["reasoning_effort"] = "medium"
        drifted_pool = ModelPool.from_mapping(drifted_document)
        with self.assertRaisesRegex(ValueError, "does not match the canonical ModelPool"):
            self._assignment(drifted_pool, pool_config_hash=pool.config_hash)

    def test_assignment_is_canonical_schema_valid_and_round_trips(self) -> None:
        assignment = self._assignment()
        document = assignment.to_mapping()
        self.assertEqual("profile-default", document["selection_source"])
        self.assertEqual(False, document["automatic_fallback"])
        self.assertEqual("a" * 64, document["agent_profile_ref"]["sha256"])
        self.assertEqual(
            ModelPool.from_mapping(pool_document()).config_hash,
            document["pool_config_hash"],
        )
        self.assertFalse(SchemaCatalog().validate("model_assignment", document))
        self.assertEqual(assignment, ModelAssignment.from_mapping(document))

    def test_assignment_identifier_rejects_tampering_in_every_authoritative_group(self) -> None:
        baseline = self._assignment().to_mapping()
        mutations = (
            ("attempt", lambda value: value.__setitem__("attempt_id", "A-002")),
            ("profile", lambda value: value["agent_profile_ref"].__setitem__("sha256", "c" * 64)),
            ("pool", lambda value: value.__setitem__("pool_config_hash", "d" * 64)),
            ("source", lambda value: value.__setitem__("selection_source", "task-override")),
            ("reason", lambda value: value.__setitem__("selection_reason", "Different reason")),
            ("provider", lambda value: value.__setitem__("provider_adapter_id", "other")),
            ("model", lambda value: value.__setitem__("requested_model", "other-model")),
            ("reasoning", lambda value: value.__setitem__("reasoning_effort", "low")),
            ("capability", lambda value: value["capabilities"].append("streaming")),
            ("policy", lambda value: value["effective_data_policy"].__setitem__("local_only", True)),
            ("limits", lambda value: value["execution_limits"].__setitem__("max_seconds", 29.0)),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                changed = copy.deepcopy(baseline)
                mutate(changed)
                with self.assertRaises(ValueError):
                    ModelAssignment.from_mapping(changed)

    def test_override_requires_explicit_task_or_decision_reference(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires an explicit selection_ref"):
            self._assignment(selection_source="task-override")
        assignment = self._assignment(
            selection_source="human-override",
            selection_ref=FileReference("decisions/DEC-001.yaml", "e" * 64),
        )
        self.assertEqual("decisions/DEC-001.yaml", assignment.selection_ref.path)
        tampered = assignment.to_mapping()
        tampered["selection_ref"]["sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            ModelAssignment.from_mapping(tampered)

    def test_legacy_selection_sources_and_fallback_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported.*selection source"):
            self._assignment(selection_source="legacy-explicit")
        document = self._assignment().to_mapping()
        document["automatic_fallback"] = True
        with self.assertRaisesRegex(ValueError, "automatic_fallback must be false"):
            ModelAssignment.from_mapping(document)

        pool_with_fallback = pool_document()
        pool_with_fallback["automatic_fallback"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields: automatic_fallback"):
            ModelPool.from_mapping(pool_with_fallback)


if __name__ == "__main__":
    unittest.main()
