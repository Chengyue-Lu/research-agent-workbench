import hashlib
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from research_workbench.capability import ResolvedTask
from research_workbench.execution.contracts import (
    EvidenceH2ExecutionContract,
    ExecutionContractError,
    ExecutionContractRegistry,
    default_execution_contract_registry,
)
from research_workbench.execution.tools import (
    BoundedComputeBoundaryError,
    DocumentReadBoundaryError,
    build_bounded_compute_tool,
    build_frozen_text_read_tool,
)
from research_workbench.io import load_document
from research_workbench.tasks import FileReference, TaskPacket


ROOT = Path(__file__).resolve().parents[1]


class AlternateEvidenceContract(EvidenceH2ExecutionContract):
    contract_id = "alternate-evidence-h2"


class ExecutionContractTests(unittest.TestCase):
    def test_registry_selects_only_exact_h1_and_h2_signatures(self) -> None:
        registry = default_execution_contract_registry()
        evidence_task = TaskPacket.from_mapping(
            load_document(ROOT / "examples/task-evidence.yaml")
        )
        evidence_assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/evidence-assignment.yaml")
        )
        simulation_task = TaskPacket.from_mapping(
            load_document(ROOT / "examples/task-simulation.yaml")
        )
        simulation_assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/simulation-assignment.yaml")
        )

        self.assertEqual(
            "evidence-h2@0.1.0",
            registry.require(evidence_task, evidence_assignment).identifier,
        )
        self.assertEqual(
            "simulation-h1@0.1.0",
            registry.require(simulation_task, simulation_assignment).identifier,
        )

        unsupported_task = replace(
            evidence_task,
            required_outputs=("unknown-research-contract", "handoff-packet"),
        )
        unsupported_assignment = replace(
            evidence_assignment,
            output_contracts=("unknown-research-contract", "handoff-packet"),
        )
        with self.assertRaises(ExecutionContractError) as raised:
            registry.require(unsupported_task, unsupported_assignment)
        self.assertEqual("OUTPUT-CONTRACT-UNSUPPORTED", raised.exception.code)

    def test_registry_rejects_ambiguous_exact_signature_without_ranking(self) -> None:
        task = TaskPacket.from_mapping(load_document(ROOT / "examples/task-evidence.yaml"))
        assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/evidence-assignment.yaml")
        )
        registry = ExecutionContractRegistry(
            (EvidenceH2ExecutionContract(), AlternateEvidenceContract())
        )

        with self.assertRaises(ExecutionContractError) as raised:
            registry.require(task, assignment)

        self.assertEqual("EXECUTION-CONTRACT-AMBIGUOUS", raised.exception.code)

    def test_frozen_file_read_allows_only_exact_hash_pinned_task_input(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "input.txt"
            payload = b"bounded input\n"
            path.write_bytes(payload)
            reference = FileReference("input.txt", hashlib.sha256(payload).hexdigest())
            task = SimpleNamespace(input_refs=(reference,))
            tool = build_frozen_text_read_tool("file-read", root, task, max_bytes=64)

            result = tool.execute({"path": "input.txt"})
            self.assertEqual("bounded input\n", result["content"])
            self.assertFalse(tool.trace_result)
            with self.assertRaises(DocumentReadBoundaryError) as denied:
                tool.execute({"path": "other.txt"})
            self.assertEqual("DOCUMENT-READ-DENIED", denied.exception.code)

            path.write_text("drifted", encoding="utf-8")
            with self.assertRaises(DocumentReadBoundaryError) as drifted:
                tool.execute({"path": "input.txt"})
            self.assertEqual("REF-HASH-MISMATCH", drifted.exception.code)

    def test_bounded_compute_is_finite_fixed_catalog_and_size_bounded(self) -> None:
        tool = build_bounded_compute_tool(max_values_per_call=3)
        result = tool.execute(
            {
                "operation": "normalized-sensitivity",
                "baseline": [2.0, 4.0],
                "comparison": [3.0, 2.0],
                "parameter_delta": 0.5,
            }
        )
        self.assertEqual("none", tool.side_effect)
        self.assertTrue(tool.trace_result)
        self.assertEqual(2, result["value_count"])
        self.assertAlmostEqual(1.0, result["max_normalized_sensitivity"])

        invalid_calls = (
            {
                "operation": "python",
                "baseline": [1.0],
                "comparison": [1.0],
            },
            {
                "operation": "relative-change",
                "baseline": [1.0, 2.0, 3.0, 4.0],
                "comparison": [1.0, 2.0, 3.0, 4.0],
            },
            {
                "operation": "relative-change",
                "baseline": [math.inf],
                "comparison": [1.0],
            },
            {
                "operation": "relative-change",
                "baseline": [1.0],
                "comparison": [1.0],
                "code": "open('secret')",
            },
        )
        for arguments in invalid_calls:
            with self.subTest(arguments=arguments):
                with self.assertRaises(BoundedComputeBoundaryError):
                    tool.execute(arguments)

    def test_bounded_compute_rejects_non_finite_arithmetic_results(self) -> None:
        tool = build_bounded_compute_tool(max_values_per_call=3)
        overflow_calls = (
            {
                "operation": "relative-change",
                "baseline": [1.0e308],
                "comparison": [-1.0e308],
            },
            {
                "operation": "relative-change",
                "baseline": [-1.0e308],
                "comparison": [1.0e308],
            },
            {
                "operation": "relative-change",
                "baseline": [1.0, 1.0],
                "comparison": [1.0e308, 1.0e308],
            },
            {
                "operation": "normalized-sensitivity",
                "baseline": [1.0],
                "comparison": [2.0],
                "parameter_delta": 5.0e-324,
            },
        )

        for arguments in overflow_calls:
            with self.subTest(arguments=arguments):
                with self.assertRaises(BoundedComputeBoundaryError) as raised:
                    tool.execute(arguments)
                self.assertEqual("BOUNDED-COMPUTE-OVERFLOW", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
