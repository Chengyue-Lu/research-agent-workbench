import copy
import unittest
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog, validate_documents
from research_workbench.validation.documents import _validate_phase_b_evolution_gates


ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "examples/capability-resolution/phase-b-evolution-gate.yaml"
SNAPSHOT_A_PATH = ROOT / "examples/capability-resolution/snapshots/document-read-a.yaml"
SNAPSHOT_B_PATH = ROOT / "examples/capability-resolution/snapshots/document-read-b.yaml"


def repository_documents() -> dict[Path, object]:
    paths = sorted(
        path
        for root in (ROOT / "examples", ROOT / "registry")
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".yaml", ".yml"}
    )
    return {path: load_document(path) for path in paths}


class PhaseBEvolutionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = SchemaCatalog(ROOT / "schemas")
        cls.documents = repository_documents()
        cls.gate = cls.documents[GATE_PATH]

    def test_gate_is_schema_valid_and_repository_closed(self) -> None:
        self.assertEqual([], self.catalog.validate("phase_b_evolution_gate", self.gate))
        self.assertEqual([], validate_documents(self.documents))

    def test_gate_pins_the_stable_contract_chain(self) -> None:
        refs = self.gate["stable_contract_refs"]
        by_kind: dict[str, list[str]] = {}
        for reference in refs:
            by_kind.setdefault(reference["kind"], []).append(reference["ref"])
        self.assertEqual(["TASK-MR-ES-FROZEN-001@r1"], by_kind["task-packet"])
        self.assertEqual(["evidence-synthesis@0.1.0"], by_kind["research-mode"])
        self.assertEqual(
            {"ES-A3@1.0.0", "ES-A4@1.0.0"}, set(by_kind["mode-action"])
        )
        self.assertEqual(
            ["MR-ROUTE-ES-FROZEN-001@r1"], by_kind["method-resolution"]
        )
        self.assertEqual(["document-read"], by_kind["capability-requirement"])

    def test_supply_replacement_changes_only_exact_supply(self) -> None:
        snapshot_a = self.documents[SNAPSHOT_A_PATH]
        snapshot_b = self.documents[SNAPSHOT_B_PATH]
        self.assertNotEqual(
            snapshot_a["selected_supply_report_ref"],
            snapshot_b["selected_supply_report_ref"],
        )
        self.assertNotEqual(snapshot_a["supply_identity"], snapshot_b["supply_identity"])
        self.assertEqual(
            snapshot_a["method_resolution_ref"], snapshot_b["method_resolution_ref"]
        )
        self.assertEqual(snapshot_a["requirement_ref"], snapshot_b["requirement_ref"])
        for field in ("effective_permissions", "data_egress", "side_effects"):
            self.assertEqual(snapshot_a[field], snapshot_b[field])

    def test_stable_contract_and_snapshot_hash_drift_are_blocking(self) -> None:
        for mutate, expected in (
            (
                lambda gate: gate["stable_contract_refs"][0].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "PHASE-B-GATE-CONTRACT-HASH-DRIFT",
            ),
            (
                lambda gate: gate["replacement"]["snapshot_refs"][0].__setitem__(
                    "content_hash", "sha256:" + "0" * 64
                ),
                "PHASE-B-GATE-SNAPSHOT-HASH-DRIFT",
            ),
        ):
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.documents)
                mutate(documents[GATE_PATH])
                codes = {issue.code for issue in _validate_phase_b_evolution_gates(documents)}
                self.assertIn(expected, codes)

    def test_supply_must_actually_be_replaced(self) -> None:
        documents = copy.deepcopy(self.documents)
        snapshot_a = documents[SNAPSHOT_A_PATH]
        snapshot_b = documents[SNAPSHOT_B_PATH]
        snapshot_b["selected_supply_report_ref"] = snapshot_a["selected_supply_report_ref"]
        snapshot_b["supply_identity"] = copy.deepcopy(snapshot_a["supply_identity"])
        codes = {issue.code for issue in _validate_phase_b_evolution_gates(documents)}
        self.assertIn("PHASE-B-GATE-SUPPLY-NOT-REPLACED", codes)

    def test_permission_data_and_side_effect_boundary_drift_are_blocking(self) -> None:
        mutations = (
            (
                lambda snapshot: snapshot["effective_permissions"].__setitem__(
                    "network", "approved-external-read"
                ),
                "PHASE-B-GATE-PERMISSION-RELAXED",
            ),
            (
                lambda snapshot: snapshot["data_egress"].__setitem__(
                    "policy", "allowlisted"
                ),
                "PHASE-B-GATE-DATA-EGRESS-RELAXED",
            ),
            (
                lambda snapshot: snapshot["side_effects"]["allowed_effects"].append(
                    "external-write"
                ),
                "PHASE-B-GATE-SIDE-EFFECT-RELAXED",
            ),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected):
                documents = copy.deepcopy(self.documents)
                mutate(documents[SNAPSHOT_B_PATH])
                codes = {issue.code for issue in _validate_phase_b_evolution_gates(documents)}
                self.assertIn(expected, codes)

    def test_replay_migrations_are_exact_and_hash_bound(self) -> None:
        migration_kinds = {
            reference["migration_kind"]
            for reference in self.gate["replay_migration_refs"]
        }
        self.assertEqual(
            {"research-mode-migration", "skill-lifecycle-migration"}, migration_kinds
        )
        documents = copy.deepcopy(self.documents)
        documents[GATE_PATH]["replay_migration_refs"][0]["content_hash"] = (
            "sha256:" + "0" * 64
        )
        codes = {issue.code for issue in _validate_phase_b_evolution_gates(documents)}
        self.assertIn("PHASE-B-GATE-MIGRATION-HASH-DRIFT", codes)

    def test_gate_cannot_claim_runtime_authority_or_scientific_value(self) -> None:
        for field in (
            "runtime_method_authority",
            "automatic_fallback",
            "claim_or_gate_effect",
            "execution_performed",
            "live_provider_conformance_proven",
            "skill_net_benefit_proven",
        ):
            with self.subTest(field=field):
                gate = copy.deepcopy(self.gate)
                gate["boundary_assertions"][field] = True
                self.assertTrue(self.catalog.validate("phase_b_evolution_gate", gate))


if __name__ == "__main__":
    unittest.main()
