"""Explicit application bridge from published intake facts to frozen role slices.

The supplied Provider and factory retain authorization and qualification
ownership. This caller neither supplies credentials nor admits a draft as
project truth, and it does not automatically invoke Guide or a State writer.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from research_workbench.contracts.common import to_plain
from research_workbench.entry.executor import FrozenRoleExecutor
from research_workbench.entry.factory import ApiRoleBindingFactory
from research_workbench.entry.intake_call import IntakeCallResult
from research_workbench.entry.roles import EntryInputError, read_pinned_inputs
from research_workbench.entry.workflow import WorkflowBudget, WorkflowResult, run_research_workflow
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog


@dataclass(frozen=True)
class IntakeWorkflowResult:
    intake: IntakeCallResult
    workflow: WorkflowResult | None
    reason: str
    artifact_refs: tuple[FileReference, ...]
    external_control_refs: tuple[FileReference, ...] = ()
    intake_report_verified: bool = False
    task_completion: bool = False
    human_acceptance: bool = False
    handoff_ref: FileReference | None = None


def _ref(pin: Any) -> FileReference:
    return FileReference(pin.path, pin.sha256.removeprefix("sha256:"),
                         getattr(pin, "revision", None))


def _key(ref: FileReference) -> tuple[str, str, int | None]:
    return ref.path, ref.sha256.removeprefix("sha256:"), ref.revision


def _unique_refs(refs) -> tuple[FileReference, ...]:
    result, seen = [], set()
    for ref in refs:
        key = _key(ref)
        if key not in seen:
            seen.add(key)
            result.append(ref)
    return tuple(result)


def _read(root: Path, reference: FileReference) -> Mapping[str, Any]:
    snapshot = read_pinned_inputs(root, (reference,))[0]
    document = load_document_bytes(Path(reference.path), snapshot["text"].encode("utf-8"))
    if not isinstance(document, Mapping):
        raise EntryInputError("pinned control/report must be an object")
    return document


def _verify_report(root: Path, intake: IntakeCallResult) -> None:
    if intake.report_ref is None:
        raise EntryInputError("INTAKE-REPORT-UNAVAILABLE")
    report = _read(root, intake.report_ref)
    fields = ("status", "reason", "details", "model_calls", "input_tokens", "output_tokens",
              "reserved_tokens", "held_tokens", "session_status", "stop_reason", "draft_refs")
    for field in fields:
        if field not in report or report[field] != to_plain(getattr(intake, field)):
            raise EntryInputError("INTAKE-REPORT-RESULT-MISMATCH: " + field)
    if (report.get("qualification") != "intake-control-draft-only"
            or report.get("human_acceptance") is not False):
        raise EntryInputError("INTAKE-REPORT-BOUNDARY-MISMATCH")
    recorded = tuple(FileReference.from_mapping(ref) for ref in report.get("artifact_refs", ()))
    returned = tuple(intake.artifact_refs)
    if len({_key(ref) for ref in returned}) != len(returned):
        raise EntryInputError("INTAKE-ARTIFACT-REFS-DUPLICATE")
    # The intake publisher forms the JSON payload before writing its readable
    # report and result.json. Those two actual outputs are the only additions.
    returned_keys, recorded_keys = {_key(ref) for ref in returned}, {_key(ref) for ref in recorded}
    report_key = _key(intake.report_ref)
    readable = (Path(intake.report_ref.path).parent / "REPORT.md").as_posix()
    extras = [ref for ref in returned if _key(ref) not in recorded_keys]
    if (not recorded_keys.issubset(returned_keys) or report_key not in returned_keys
            or len(extras) != 2 or not any(_key(ref) == report_key for ref in extras)
            or not any(ref.path == readable for ref in extras)):
        raise EntryInputError("INTAKE-ARTIFACT-REFS-MISMATCH")
    if any(_key(ref) not in recorded_keys for ref in intake.draft_refs):
        raise EntryInputError("INTAKE-DRAFT-REFS-NOT-RECORDED")
    read_pinned_inputs(root, returned)


def _verify_controls(root: Path, intake: IntakeCallResult,
                     factory: ApiRoleBindingFactory) -> tuple[Mapping[str, Any], tuple[FileReference, ...]]:
    catalog = SchemaCatalog(factory.catalog_root)
    published = {_key(ref) for ref in intake.draft_refs}
    task_ref, method_ref, requirement_ref = (_ref(factory.task_pin), _ref(factory.method_pin),
                                            _ref(factory.requirement_pin))
    if _key(task_ref) not in published or _key(method_ref) not in published:
        raise EntryInputError("INTAKE-TASK-METHOD-NOT-ACTUAL-PRODUCTS")
    task, method, requirement = (_read(root, ref) for ref in (task_ref, method_ref, requirement_ref))
    for kind, document in (("task_packet", task), ("method_resolution", method),
                           ("capability_requirement", requirement)):
        if catalog.validate(kind, document):
            raise EntryInputError("INTAKE-CONTROL-SCHEMA-INVALID: " + kind)
    expected = {"task_id": task["task_id"], "revision": task.get("revision", 1), "sha256": task_ref.sha256}
    actual = dict(method["task_ref"])
    actual["sha256"] = actual["sha256"].removeprefix("sha256:")
    if actual != expected:
        raise EntryInputError("INTAKE-METHOD-TASK-PIN-MISMATCH")
    capabilities = {item for decision in method["action_decisions"]
                    for item in decision["capability_requirements"]}
    if capabilities != set(task.get("required_capabilities", ())):
        raise EntryInputError("INTAKE-METHOD-TASK-CAPABILITY-MISMATCH")
    if requirement["requirement_id"] not in capabilities:
        raise EntryInputError("INTAKE-REQUIREMENT-NOT-DECLARED")
    if method["resolution_status"] != "proceed":
        raise EntryInputError("INTAKE-METHOD-NOT-PROCEED")
    external = () if _key(requirement_ref) in published else (requirement_ref,)
    # An external pin is explicit factory configuration, checked from its own
    # bytes and actual Task/Method demand. It is never added to intake outputs.
    return task, external


def run_frozen_intake_workflow(
    root: str | Path, *, intake_result: IntakeCallResult,
    binding_factory: ApiRoleBindingFactory, directory: str, budget: WorkflowBudget,
    accountable_owner: str, deadline_monotonic: float, clock=time.monotonic,
    cancel_requested: Callable[[], bool] | None = None,
) -> IntakeWorkflowResult:
    """Consume actual published intake; charge it once within the same deadline.

    The deadline is the original admitted request's monotonic deadline. Budget
    ceilings are whole-request values, rather than a fresh post-intake grant.
    Failed, rejected, incomplete or unknown intake never dispatches a workflow.
    """
    if not isinstance(intake_result, IntakeCallResult):
        raise TypeError("an actual IntakeCallResult is required")
    project = Path(root).resolve()
    verified, external = False, ()
    retained = _unique_refs((*intake_result.artifact_refs,
                            *((intake_result.report_ref,) if intake_result.report_ref else ())))
    try:
        if not isinstance(binding_factory, ApiRoleBindingFactory) or binding_factory.root != project:
            raise EntryInputError("INTAKE-FACTORY-ROOT-MISMATCH")
        if not isinstance(budget, WorkflowBudget):
            raise EntryInputError("an explicit WorkflowBudget is required")
        _verify_report(project, intake_result)
        verified = True
        if intake_result.status != "success":
            return IntakeWorkflowResult(intake_result, None,
                "INTAKE-NOT-SUCCESS: " + intake_result.reason, retained, intake_report_verified=True)
        if (intake_result.model_calls != 1 or type(intake_result.model_calls) is not int
                or any(type(value) is not int or value < 0
                       for value in (intake_result.input_tokens, intake_result.output_tokens))
                or type(intake_result.held_tokens) is not int or intake_result.held_tokens != 0
                or type(intake_result.reserved_tokens) is not int or intake_result.reserved_tokens <= 0
                or intake_result.input_tokens + intake_result.output_tokens > intake_result.reserved_tokens
                or not intake_result.draft_refs):
            raise EntryInputError("INTAKE-SUCCESS-USAGE-OR-PUBLICATION-INVALID")
        task, external = _verify_controls(project, intake_result, binding_factory)
        if binding_factory.record_refs:
            raise EntryInputError("INTAKE-FACTORY-ALREADY-USED")
        if (isinstance(deadline_monotonic, bool) or not isinstance(deadline_monotonic, (int, float))
                or not math.isfinite(deadline_monotonic)):
            raise EntryInputError("INTAKE-WORKFLOW-DEADLINE-INVALID")
        if cancel_requested and cancel_requested():
            raise EntryInputError("INTAKE-WORKFLOW-CANCELLED")
        anchor = clock()
        if isinstance(anchor, bool) or not isinstance(anchor, (int, float)) or not math.isfinite(anchor):
            raise EntryInputError("INTAKE-WORKFLOW-CLOCK-INVALID")
        remaining = min(budget.max_seconds, deadline_monotonic - anchor)
        if remaining <= 0:
            raise EntryInputError("INTAKE-WORKFLOW-DEADLINE-EXHAUSTED")
        if (intake_result.model_calls >= budget.max_model_calls
                or intake_result.input_tokens + intake_result.output_tokens >= budget.max_total_tokens):
            raise EntryInputError("INTAKE-WORKFLOW-BUDGET-EXHAUSTED")
        if not isinstance(accountable_owner, str) or not accountable_owner.strip():
            raise EntryInputError("explicit accountable_owner is required")
    except (EntryInputError, ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        reason = str(exc) if isinstance(exc, EntryInputError) else "INTAKE-WORKFLOW-PREFLIGHT-REJECTED: " + type(exc).__name__
        return IntakeWorkflowResult(intake_result, None, reason, retained, external, verified)

    # Preserve the preflight clock anchor as workflow.start. Subsequent readings
    # use the original clock, so construction/dispatch cannot restart wall time.
    first = True
    def workflow_clock():
        nonlocal first
        if first:
            first = False
            return anchor
        value = clock()
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("workflow clock became unavailable")
        return value

    executor = FrozenRoleExecutor(project, binding_factory=binding_factory,
        accountable_owner=accountable_owner, cancel_requested=cancel_requested)
    workflow = run_research_workflow(project, directory=directory, task=task, executor=executor,
        budget=replace(budget, max_seconds=remaining), catalog=SchemaCatalog(binding_factory.catalog_root),
        clock=workflow_clock, cancel_requested=cancel_requested,
        prior_usage=(intake_result.as_role_observation(),))
    from research_workbench.entry.handoff import EntryHandoffError, publish_workflow_handoff
    handoff_ref = None
    reason = "INTAKE-WORKFLOW-" + workflow.status.upper()
    try:
        handoff_ref = publish_workflow_handoff(project, result=workflow,
            catalog=SchemaCatalog(binding_factory.catalog_root))
    except (EntryHandoffError, ValueError, OSError) as exc:
        # Paid execution/accounting remains observable even when formal transfer
        # is blocked. Missing H2 prerequisites never fabricate a successful ref.
        reason = "INTAKE-WORKFLOW-HANDOFF-BLOCKED: " + str(exc)
    refs = _unique_refs((*retained, *external, *(_ref(ref) for ref in binding_factory.record_refs),
                        FileReference.from_mapping(workflow.report_ref),
                        *((handoff_ref,) if handoff_ref else ())))
    return IntakeWorkflowResult(intake_result, workflow, reason,
                                refs, external, True, handoff_ref=handoff_ref)


__all__ = ["IntakeWorkflowResult", "run_frozen_intake_workflow"]
