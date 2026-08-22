"""Regression coverage answering the K-API-2 rework review checklist.

Six families, one per review item:
1. publication atomicity: duplicate publishes are refused; verify flags gaps;
2. ``--from-state`` preflight, pinning, and drift replay;
3. evidence provenance bound to the frozen input set (multi-input safe);
4. reasoning_effort propagation into the request and attempt sensitivity;
5. oversized tool results counting their invocation is already pinned by
   ``test_api_session_runner.test_oversized_tool_result_is_not_silently_truncated``
   (asserts tool_calls == 1 after a real invocation under the size budget);
6. fixture regeneration is covered by the merged suite and CI, not here.
"""

from __future__ import annotations

import contextlib
import unittest
from dataclasses import replace
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.contracts import to_plain
from research_workbench.execution import RECEIPT_FILENAME, ExecutionPlanError
from research_workbench.execution.closeout import _check_evidence_provenance
from research_workbench.execution.compiler import compile_execution
from research_workbench.tasks import FileReference

from support import ROOT, temporary_workspace
from test_execution_closeout import ATTEMPT_DIR, CloseoutWorkspace
from test_execution_compiler import (
    ADAPTERS_DOCUMENT,
    MODEL_ENV,
    MODEL_VALUE,
    STARTED_AT,
    TASK_PATH,
    pool_document,
    resolve_assignment,
)

# The reasoning-effort slot needs the one adapter family that implements
# the reasoning capability.
REASONING_ADAPTERS_DOCUMENT = {
    "schema_version": "0.1.0",
    "registry_kind": "provider_adapters",
    "adapters": [
        {
            "adapter_id": "openai-responses",
            "provider": "openai",
            "enabled": True,
            "base_url": "https://api.openai.com/v1",
            "credential_env": "OPENAI_API_KEY",
            "model_env": "RWB_OPENAI_MODEL",
            "capabilities": ["text", "tools", "structured_output", "reasoning"],
            "live_conformance": "pending",
        }
    ],
}

MAIN_STATE_PATH = ROOT / "examples/main-state.yaml"


def _block_codes(risks) -> set[str]:
    return {risk.code for risk in risks}


class FromStatePreflightTests(unittest.TestCase):
    """--from-state is a validated execution input, checked before the provider."""

    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        self.workspace = self._stack.enter_context(temporary_workspace())
        self.assignment_path = self._write_yaml("assignment.yaml", to_plain(resolve_assignment()))
        self.pool_path = self._write_yaml("pool.yaml", pool_document())
        self.adapters_path = self._write_yaml("adapters.yaml", ADAPTERS_DOCUMENT)

    def _write_yaml(self, name: str, document: object) -> Path:
        path = self.workspace / name
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return path

    def _compile(self, **overrides: object):
        arguments = {
            "task_path": TASK_PATH,
            "assignment_path": self.assignment_path,
            "slot": "worker",
            "pool_path": self.pool_path,
            "adapters_path": self.adapters_path,
            "root": ROOT,
            "environment": {MODEL_ENV: MODEL_VALUE},
            "started_at": STARTED_AT,
        }
        arguments.update(overrides)
        return compile_execution(**arguments)  # type: ignore[arg-type]

    def test_missing_base_state_blocks_at_compile(self) -> None:
        with self.assertRaises(ExecutionPlanError) as caught:
            self._compile(base_state_path="examples/does-not-exist.yaml")
        self.assertIn("EXEC-BASE-STATE-INVALID", _block_codes(caught.exception.risks))

    def test_schema_invalid_base_state_blocks_at_compile(self) -> None:
        broken = {"schema_version": "0.1.0", "checkpoint_id": "CS-BAD"}
        broken_path = self._write_yaml("broken-state.yaml", broken)
        with self.assertRaises(ExecutionPlanError) as caught:
            self._compile(base_state_path=broken_path)
        self.assertIn("EXEC-BASE-STATE-INVALID", _block_codes(caught.exception.risks))

    def test_valid_base_state_is_hashed_pinned_and_readable(self) -> None:
        plan = self._compile(base_state_path=MAIN_STATE_PATH)
        assert plan.base_state is not None
        self.assertEqual("examples/main-state.yaml", plan.base_state.path)
        self.assertEqual(hash_file(MAIN_STATE_PATH), plan.base_state.sha256)
        self.assertIn("examples/main-state.yaml", plan.readable_inputs)
        mapping = plan.to_mapping()
        self.assertEqual("examples/main-state.yaml", mapping["base_state"]["path"])


class FromStateDriftTests(unittest.TestCase):
    """The pinned base state must still hash identically at verify time."""

    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        root = self._stack.enter_context(temporary_workspace())
        self.root = root
        self.workspace = CloseoutWorkspace(root)
        self.state_path = root / "continuity/state.yaml"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            (ROOT / "examples/main-state.yaml").read_text(encoding="utf-8"), encoding="utf-8"
        )

    def _plan(self):
        return replace(
            self.workspace.plan(),
            base_state=FileReference(
                path="continuity/state.yaml", sha256=hash_file(self.state_path)
            ),
        )

    def test_closeout_publishes_the_pinned_base_state(self) -> None:
        from research_workbench.execution.closeout import PLAN_FILENAME, closeout

        self.workspace.write_output()
        result = closeout(self._plan(), self.workspace.run(), root=self.root)
        self.assertEqual("completed", result.status, [str(risk) for risk in result.risks])
        import yaml as _yaml

        published = _yaml.safe_load(
            (self.root / ATTEMPT_DIR / PLAN_FILENAME).read_text(encoding="utf-8")
        )
        self.assertEqual("continuity/state.yaml", published["base_state"]["path"])

    def test_drifted_base_state_is_flagged_on_replay(self) -> None:
        from research_workbench.execution.closeout import closeout, verify_attempt

        self.workspace.write_output()
        closeout(self._plan(), self.workspace.run(), root=self.root)
        self.state_path.write_text("tampered state\n", encoding="utf-8")
        risks = verify_attempt(self.root / ATTEMPT_DIR, root=self.root)
        self.assertIn("EXEC-BASE-STATE-STALE", _block_codes(risks))


class EvidenceProvenanceTests(unittest.TestCase):
    """Evidence outputs must quote material inside the frozen input set."""

    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        root = self._stack.enter_context(temporary_workspace())
        self.root = root
        self.workspace = CloseoutWorkspace(root)

    def test_multi_input_selection_is_free_within_the_frozen_set(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "evidence-record.yaml"
            second_input_hash = "b" * 64
            output.write_text(
                "object_type: evidence\n"
                f"content_hash: {second_input_hash}\n"
                "source_ref: INPUT-SECOND@2\n"
                "locator: line 3\n",
                encoding="utf-8",
            )
            frozen = frozenset({"a" * 64, second_input_hash})
            self.assertEqual((), _check_evidence_provenance(frozen, (output,)))

    def test_foreign_hash_is_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "evidence-record.yaml"
            output.write_text(
                "object_type: evidence\n"
                f"content_hash: {'c' * 64}\n"
                "source_ref: INPUT-UNKNOWN@1\n"
                "locator: line 1\n",
                encoding="utf-8",
            )
            risks = _check_evidence_provenance(frozenset({"a" * 64}), (output,))
            self.assertEqual({"EXEC-EVIDENCE-SOURCE-UNFROZEN"}, _block_codes(risks))

    def test_malformed_reference_and_locator_are_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as raw:
            malformed = Path(raw) / "malformed.yaml"
            malformed.write_text(
                "object_type: evidence\n"
                f"content_hash: {'a' * 64}\n"
                "source_ref: not-an-object-reference\n"
                "locator: ''\n",
                encoding="utf-8",
            )
            risks = _check_evidence_provenance(frozenset({"a" * 64}), (malformed,))
            self.assertIn("EXEC-EVIDENCE-SOURCE-MALFORMED", _block_codes(risks))

    def test_unfrozen_evidence_degrades_completion_and_replays(self) -> None:
        from research_workbench.execution.closeout import closeout, verify_attempt

        self.workspace.write_output(
            content=(
                "schema_version: 0.1.0\n"
                "object_type: evidence\n"
                "object_id: EVID-T-001-01\n"
                "revision: 1\n"
                "status: drafted\n"
                f"content_hash: {'e' * 64}\n"
                "kind: bounded-text-excerpt\n"
                "source_ref: INPUT-FOREIGN@1\n"
                "locator: lines 1-2\n"
                "statement: Quoted from outside the frozen input set.\n"
                "quality_flags: [synthetic_fixture]\n"
            )
        )
        result = closeout(self.workspace.plan(), self.workspace.run(), root=self.root)
        self.assertEqual("incomplete", result.status)
        self.assertIn("EXEC-EVIDENCE-SOURCE-UNFROZEN", _block_codes(result.risks))
        replayed = verify_attempt(self.root / ATTEMPT_DIR, root=self.root)
        self.assertIn("EXEC-EVIDENCE-SOURCE-UNFROZEN", _block_codes(replayed))


class ReasoningEffortTests(unittest.TestCase):
    """The bound effort reaches the ModelRequest and pins attempt identity."""

    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        self.workspace = self._stack.enter_context(temporary_workspace())
        self.assignment_path = self._write_yaml(
            "assignment.yaml", to_plain(resolve_assignment())
        )
        self.adapters_path = self._write_yaml("adapters.yaml", REASONING_ADAPTERS_DOCUMENT)

    def _write_yaml(self, name: str, document: object) -> Path:
        path = self.workspace / name
        path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        return path

    def _compile(self, reasoning_effort: str | None):
        pool_path = self._write_yaml(
            "pool.yaml",
            pool_document(
                reasoning_effort=reasoning_effort,
                provider_adapter="openai-responses",
                capabilities=["text", "tools", "structured_output", "reasoning"],
            ),
        )
        return compile_execution(
            task_path=TASK_PATH,
            assignment_path=self.assignment_path,
            slot="worker",
            pool_path=pool_path,
            adapters_path=self.adapters_path,
            root=ROOT,
            environment={MODEL_ENV: MODEL_VALUE},
            started_at=STARTED_AT,
            attempt_id="A-EFFORT",
        )

    def test_effort_propagates_into_binding_and_request(self) -> None:
        plan = self._compile("high")
        self.assertEqual("high", plan.model_binding.reasoning_effort)
        self.assertEqual("high", plan.request.reasoning_effort)
        mapping = plan.to_mapping()
        self.assertEqual("high", mapping["model_binding"]["reasoning_effort"])

    def test_changed_effort_cannot_reuse_a_published_attempt(self) -> None:
        from research_workbench.execution.closeout import closeout

        root = self.workspace
        workspace = CloseoutWorkspace(root)
        workspace.write_output()
        high = replace(workspace.plan(), request=replace(workspace.plan().request, reasoning_effort="high"))
        first = closeout(high, workspace.run(), root=root)
        self.assertEqual("completed", first.status, [str(risk) for risk in first.risks])
        low = replace(high, request=replace(high.request, reasoning_effort="low"))
        with self.assertRaises(FileExistsError):
            closeout(low, workspace.run(), root=root)


class PublicationAtomicityTests(unittest.TestCase):
    """Partial or duplicated publication never reads as a committed attempt."""

    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        root = self._stack.enter_context(temporary_workspace())
        self.root = root
        self.workspace = CloseoutWorkspace(root)

    def test_verify_flags_missing_closeout_artifact(self) -> None:
        from research_workbench.execution.closeout import closeout, verify_attempt

        self.workspace.write_output()
        closeout(self.workspace.plan(), self.workspace.run(), root=self.root)
        (self.root / ATTEMPT_DIR / RECEIPT_FILENAME).unlink()
        risks = verify_attempt(self.root / ATTEMPT_DIR, root=self.root)
        self.assertIn("EXEC-CLOSEOUT-INVALID", _block_codes(risks))
        self.assertTrue(
            any("execution-receipt.yaml" in risk.message for risk in risks), list(risks)
        )


if __name__ == "__main__":
    unittest.main()
