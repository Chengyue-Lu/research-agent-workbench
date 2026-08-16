import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research_workbench.adapters.models import ApiSessionLimits
from research_workbench.capability import ResolvedTask
from research_workbench.execution import (
    DocumentReadBoundaryError,
    ExecutionToolRegistry,
    ExecutionToolRegistryError,
    default_execution_tool_registry,
)
from research_workbench.execution.contracts import default_execution_contract_registry
from research_workbench.io import load_document
from research_workbench.tasks import TaskPacket


ROOT = Path(__file__).resolve().parents[1]


class ExecutionToolRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.evidence_task = TaskPacket.from_mapping(
            load_document(ROOT / "examples/task-evidence.yaml")
        )
        cls.simulation_task = TaskPacket.from_mapping(
            load_document(ROOT / "examples/task-simulation.yaml")
        )
        cls.evidence_assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/evidence-assignment.yaml")
        )
        cls.simulation_assignment = ResolvedTask.from_mapping(
            load_document(ROOT / "examples/vertical-slice/simulation-assignment.yaml")
        )

    @staticmethod
    def limits() -> ApiSessionLimits:
        return ApiSessionLimits(
            max_model_turns=2,
            max_tool_calls=2,
            max_parallel_tool_calls=1,
            max_tool_result_chars=4096,
            max_output_tokens_per_turn=512,
            max_seconds=10,
            max_total_tokens=2048,
            allowed_tool_side_effects=frozenset({"none", "read-only"}),
            max_compute_values_per_call=2,
        )

    def test_registry_surface_is_closed_to_three_trusted_factories(self) -> None:
        registry = ExecutionToolRegistry()

        self.assertEqual(
            frozenset({"document-read", "file-read", "bounded-compute"}),
            registry.trusted_tool_names,
        )
        self.assertFalse(hasattr(registry, "register"))
        with self.assertRaises(AttributeError):
            registry.factories = {"shell": object()}
        self.assertIs(
            default_execution_tool_registry(),
            default_execution_tool_registry(),
        )

    def test_exact_evidence_contract_builds_only_document_read(self) -> None:
        contract = default_execution_contract_registry().require(
            self.evidence_task, self.evidence_assignment
        )
        tools = ExecutionToolRegistry().build_tools(
            root=ROOT,
            task=self.evidence_task,
            limits=self.limits(),
            contract=contract,
            assignment=self.evidence_assignment,
        )

        self.assertEqual(("document-read",), tuple(tool.definition.name for tool in tools))
        self.assertEqual("read-only", tools[0].side_effect)
        self.assertFalse(tools[0].trace_result)
        result = tools[0].execute({"path": "examples/fixtures/paper-001.txt"})
        self.assertEqual(self.evidence_task.input_refs[0].sha256, result["sha256"])

    def test_exact_simulation_contract_builds_in_assignment_order(self) -> None:
        contract = default_execution_contract_registry().require(
            self.simulation_task, self.simulation_assignment
        )
        tools = ExecutionToolRegistry().build_tools(
            root=ROOT,
            task=self.simulation_task,
            limits=self.limits(),
            contract=contract,
            assignment=self.simulation_assignment,
        )

        self.assertEqual(
            ("bounded-compute", "file-read"),
            tuple(tool.definition.name for tool in tools),
        )
        self.assertEqual("none", tools[0].side_effect)
        self.assertTrue(tools[0].trace_result)
        compute_result = tools[0].execute(
            {
                "operation": "relative-change",
                "baseline": [1.0],
                "comparison": [2.0],
            }
        )
        self.assertEqual(1.0, compute_result["max_relative_change"])
        read_result = tools[1].execute({"path": "examples/fixtures/run-manifest.txt"})
        self.assertEqual(self.simulation_task.input_refs[0].sha256, read_result["sha256"])

    def test_evidence_and_simulation_reads_reject_oversize_before_opening(self) -> None:
        cases = (
            (
                "evidence",
                self.evidence_task,
                self.evidence_assignment,
                "document-read",
                "examples/fixtures/paper-001.txt",
            ),
            (
                "simulation",
                self.simulation_task,
                self.simulation_assignment,
                "file-read",
                "examples/fixtures/run-manifest.txt",
            ),
        )
        limits = replace(self.limits(), max_tool_result_chars=1)

        for label, task, assignment, tool_name, path in cases:
            with self.subTest(label=label):
                contract = default_execution_contract_registry().require(task, assignment)
                tools = ExecutionToolRegistry().build_tools(
                    root=ROOT,
                    task=task,
                    limits=limits,
                    contract=contract,
                    assignment=assignment,
                )
                read_tool = next(
                    tool for tool in tools if tool.definition.name == tool_name
                )
                with patch.object(
                    Path,
                    "open",
                    side_effect=AssertionError("oversize input must fail before open"),
                ), self.assertRaises(DocumentReadBoundaryError) as raised:
                    read_tool.execute({"path": path})
                self.assertEqual("DOCUMENT-READ-SIZE", raised.exception.code)

    def test_empty_unknown_duplicate_and_extra_tools_fail_before_construction(self) -> None:
        cases = (
            ("empty", (), (), "EXECUTION-TOOL-EMPTY"),
            (
                "contract-empty",
                (),
                ("document-read",),
                "EXECUTION-TOOL-EMPTY",
            ),
            (
                "assignment-empty",
                ("document-read",),
                (),
                "EXECUTION-TOOL-EMPTY",
            ),
            ("unknown", ("shell",), ("shell",), "EXECUTION-TOOL-UNKNOWN"),
            (
                "assignment-duplicate",
                ("document-read",),
                ("document-read", "document-read"),
                "EXECUTION-TOOL-DUPLICATE",
            ),
            (
                "contract-duplicate",
                ("file-read", "file-read"),
                ("file-read",),
                "EXECUTION-TOOL-DUPLICATE",
            ),
            (
                "assignment-extra",
                ("document-read",),
                ("document-read", "file-read"),
                "EXECUTION-TOOL-MISMATCH",
            ),
            (
                "contract-extra",
                ("document-read", "file-read"),
                ("document-read",),
                "EXECUTION-TOOL-MISMATCH",
            ),
        )

        for label, contract_names, assignment_names, expected_code in cases:
            with self.subTest(label=label):
                with self.assertRaises(ExecutionToolRegistryError) as raised:
                    ExecutionToolRegistry().build_tools(
                        root=ROOT,
                        task=self.evidence_task,
                        limits=self.limits(),
                        contract=SimpleNamespace(tool_names=contract_names),
                        assignment=SimpleNamespace(resolved_tools=assignment_names),
                    )
                self.assertEqual(expected_code, raised.exception.code)


if __name__ == "__main__":
    unittest.main()
