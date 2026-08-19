import unittest
from pathlib import Path

from research_workbench.adapters.models import (
    Capability,
    ModelPool,
    load_model_pool,
    load_provider_adapter_configs,
    validate_pool_adapters,
)


ROOT = Path(__file__).resolve().parents[1]


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


class PoolAdapterCrossValidationTests(unittest.TestCase):
    def adapters(self) -> tuple:
        return load_provider_adapter_configs(ROOT / "registry" / "providers" / "adapters.yaml")

    def test_example_pool_is_consistent_with_provider_adapter_registry(self) -> None:
        pool = load_model_pool(
            ROOT / "registry" / "models" / "pool.example.yaml",
            adapters_path=ROOT / "registry" / "providers" / "adapters.yaml",
        )
        self.assertEqual("local-explicit-pool", pool.pool_id)

    def test_slot_referencing_unknown_adapter_is_rejected(self) -> None:
        document = pool_document()
        document["slots"][0]["provider_adapter"] = "missing-adapter"
        pool = ModelPool.from_mapping(document)
        with self.assertRaisesRegex(ValueError, "unknown provider adapter"):
            validate_pool_adapters(pool, self.adapters())

    def test_slot_cannot_claim_capabilities_the_adapter_does_not_implement(self) -> None:
        document = pool_document()
        # The google-generate-content adapter does not implement images.
        document["slots"][2]["capabilities"] = ["text", "images"]
        pool = ModelPool.from_mapping(document)
        with self.assertRaisesRegex(ValueError, "not implemented"):
            validate_pool_adapters(pool, self.adapters())

    def test_cross_validation_is_opt_in(self) -> None:
        pool = load_model_pool(ROOT / "registry" / "models" / "pool.example.yaml")
        self.assertEqual("local-explicit-pool", pool.pool_id)


if __name__ == "__main__":
    unittest.main()
