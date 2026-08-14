"""Regenerate the static offline closeout fixtures under examples/api-execution.

Run from the repository root:

    python examples/api-execution/regenerate.py

The script deletes and rebuilds the completed / tool-failed / safe-paused
chains by replaying scripted offline providers through the real compiler,
session runner, and closeout transaction. The stale-input path writes no
files by design; it is proven by
``tests/test_execution_e2e.py::test_stale_input_blocks_before_session_with_zero_writes``.

These fixtures are offline contract evidence only. They are not real API
executions and carry no scientific correctness claim. Re-run this script
whenever the pinned checker source (``execution/checks.py``) or any input
hash changes; ``tests/test_api_execution_fixtures.py`` fails until you do.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from research_workbench.adapters.models import (
    ApiSessionStatus,
    Capability,
    ContentBlock,
    FinishReason,
    IsolatedApiSessionRunner,
    ModelBinding,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderRegistry,
    ToolCall,
    Usage,
)
from research_workbench.capability.models import AgentProfile
from research_workbench.capability.resolver import ResolvedTask
from research_workbench.execution import (
    ExecutionPolicy,
    build_closeout_documents,
    compile_session,
    run_closeout,
)
from research_workbench.execution.artifacts import outcome_from_result
from research_workbench.io import load_document
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = Path(__file__).resolve().parent

TASK_PATH = "examples/task-evidence.yaml"
PROFILE_PATH = "registry/agents/evidence-scout.yaml"
ASSIGNMENT_PATH = "examples/vertical-slice/evidence-assignment.yaml"
PROTOCOL_PATH = "examples/project-protocol.yaml"

STARTED_AT = "2026-08-14T00:00:00Z"
FINISHED_AT = "2026-08-14T00:01:00Z"

STRUCTURED_OUTPUT = {
    "statement": "The source explicitly identifies itself as a synthetic structural fixture.",
    "source_locator": "lines 1-2",
    "quality_flags": ["synthetic_fixture", "not_scientific_evidence"],
    "summary": "One bounded extraction from the admitted fixture source.",
    "facts": ["The source identifies itself as synthetic and not scientific evidence."],
    "inferences": ["The fixture cannot support a causal claim about Q-001."],
    "recommendations": ["Keep the claim boundary at source_reported strength."],
    "limitations": ["Only the approved synthetic fixture source was reviewed."],
    "unresolved": [],
}


class OfflineProvider:
    def __init__(self, name: str, *responses: ModelResponse) -> None:
        self.name = name
        self.responses = list(responses)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.name,
            adapter_version="0",
            supported=frozenset({Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}),
            models=("worker-model",),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not self.responses:
            raise AssertionError("unexpected provider call")
        return self.responses.pop(0)


def text_response(name: str, text: str, reason: FinishReason = FinishReason.COMPLETE, usage: Usage | None = None) -> ModelResponse:
    return ModelResponse(
        response_id="r-final",
        provider=name,
        model="worker-model",
        output=(ContentBlock(kind="text", text=text),),
        finish_reason=reason,
        usage=usage or Usage(input_tokens=5, output_tokens=2),
    )


def tool_response(name: str, path: str) -> ModelResponse:
    return ModelResponse(
        response_id="r-1",
        provider=name,
        model="worker-model",
        output=(),
        finish_reason=FinishReason.TOOL_CALL,
        tool_calls=(ToolCall("call-1", "document-read", {"path": path}),),
        usage=Usage(input_tokens=5, output_tokens=2),
    )


def scenario_response(name: str, scenario: str) -> list[ModelResponse]:
    if scenario == "completed":
        return [
            tool_response(name, "examples/fixtures/paper-001.txt"),
            text_response(name, json.dumps(STRUCTURED_OUTPUT)),
        ]
    if scenario == "tool-failed":
        return [
            tool_response(name, "registry/agents/evidence-scout.yaml"),
            text_response(name, "cannot complete: required document is unreadable", FinishReason.ERROR),
        ]
    return [tool_response(name, "examples/fixtures/paper-001.txt")]


def generate(scenario: str) -> None:
    provider_name = f"offline-{scenario}"
    provider = OfflineProvider(provider_name, *scenario_response(provider_name, scenario))
    registry = ProviderRegistry()
    registry.register(provider_name, provider)
    binding = ModelBinding(
        slot_id="worker",
        role="worker",
        provider_adapter=provider_name,
        model="worker-model",
        capabilities=frozenset({Capability.TEXT, Capability.TOOLS, Capability.STRUCTURED_OUTPUT}),
        reasoning_effort=None,
        specialties=(),
    )
    task = TaskPacket.from_mapping(load_document(REPO_ROOT / TASK_PATH))
    profile = AgentProfile.from_mapping(load_document(REPO_ROOT / PROFILE_PATH))
    assignment = ResolvedTask.from_mapping(load_document(REPO_ROOT / ASSIGNMENT_PATH))
    protocol = ProjectProtocol.from_mapping(load_document(REPO_ROOT / PROTOCOL_PATH))
    policy = ExecutionPolicy(max_total_tokens=6) if scenario == "safe-paused" else ExecutionPolicy()

    compiled = compile_session(task, profile, assignment, binding, root=REPO_ROOT, policy=policy)
    runner = IsolatedApiSessionRunner(registry, tools=compiled.tools)
    result = runner.run(provider_name=provider_name, request=compiled.request, limits=compiled.limits)
    outcome = outcome_from_result(
        result,
        structured_output=STRUCTURED_OUTPUT if result.status == ApiSessionStatus.COMPLETED else None,
    )

    prefix = f"examples/api-execution/{scenario}/"
    destination = REPO_ROOT / prefix
    if destination.exists():
        shutil.rmtree(destination)
    plan = build_closeout_documents(
        task,
        assignment,
        binding,
        compiled,
        outcome,
        root=REPO_ROOT,
        protocol=protocol,
        protocol_path=PROTOCOL_PATH,
        profile_path=PROFILE_PATH,
        task_path=TASK_PATH,
        started_at=STARTED_AT,
        finished_at=FINISHED_AT,
        batch_prefix=prefix,
        checkpoint_prefix=prefix,
    )
    closeout = run_closeout(plan, root=REPO_ROOT, protocol=protocol, task=task, assignment=assignment)
    print(f"{scenario}: attempt {compiled.attempt_id} status {result.status.value} published {len(closeout.published)}")


def main() -> int:
    for scenario in ("completed", "tool-failed", "safe-paused"):
        generate(scenario)
    print("fixtures regenerated under examples/api-execution/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
