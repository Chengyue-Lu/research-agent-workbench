"""One bounded intake Model call followed by the existing control-draft compiler.

This application port records normalized, sanitized evidence. It does not issue
Host/Receipt records, qualify a provider, or authorize a research execution.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from research_workbench.adapters.models import (
    ApiSessionLimits, ApiSessionStatus, CapabilityGap, DataPolicy, DataPolicyGap, FinishReason,
    ModelNotSupported,
    IsolatedApiSessionRunner, ModelProvider, ModelRequest, ProviderRegistry,
)
from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.capability.resolver import permission_policy_covers
from research_workbench.contracts.common import PermissionPolicy, require_relative_path, to_plain
from research_workbench.entry.intake import compile_control_draft, persist_control_draft
from research_workbench.entry.roles import EntryInputError, build_role_request, document_bytes, read_pinned_inputs
from research_workbench.entry.workflow import RoleObservation
from research_workbench.observability.trace import sanitize_trace_value
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog


@dataclass(frozen=True, slots=True)
class IntakeCallBudget:
    input_reservation_tokens: int
    max_output_tokens: int
    max_total_tokens: int
    max_seconds: float

    def __post_init__(self):
        for name in ("input_reservation_tokens", "max_output_tokens", "max_total_tokens"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(name + " must be a positive integer")
        if (isinstance(self.max_seconds, bool) or not isinstance(self.max_seconds, (int, float))
                or not math.isfinite(self.max_seconds) or self.max_seconds <= 0):
            raise ValueError("max_seconds must be positive and finite")
        if self.reserved_tokens > self.max_total_tokens:
            raise ValueError("intake reservation exceeds the supplied token ceiling")

    @property
    def reserved_tokens(self) -> int:
        return self.input_reservation_tokens + self.max_output_tokens


@dataclass(frozen=True, slots=True)
class IntakeCallResult:
    status: str
    reason: str
    model_calls: int
    input_tokens: int | None
    output_tokens: int | None
    reserved_tokens: int
    held_tokens: int
    session_status: str | None
    stop_reason: str | None
    draft_refs: tuple[FileReference, ...]
    artifact_refs: tuple[FileReference, ...]
    report_ref: FileReference | None
    details: Mapping[str, Any] | None = None

    def as_role_observation(self) -> RoleObservation:
        """Pass actual intake usage to the same Run's prior_usage, without reset."""
        return RoleObservation("completed" if self.status == "success" else self.status,
            "", self.model_calls, self.input_tokens, self.output_tokens,
            tuple({"path": ref.path, "sha256": ref.sha256} for ref in self.artifact_refs),
            () if self.status == "success" else (self.reason,))


def _copy(value: Any) -> Any:
    return json.loads(document_bytes(value))


def _safe(value: Any) -> tuple[Any, tuple[dict[str, str], ...]]:
    # Convert dataclasses before redaction so every nested field is inspected.
    return sanitize_trace_value(to_plain(value))


def _scope_path(root: Path, directory: str, task: Mapping[str, Any]) -> Path:
    require_relative_path(directory, "intake output directory")
    path = resolve_within_root(root, directory)
    if path is None or path == root or task["permissions"]["filesystem"] != "worktree-write":
        raise EntryInputError("intake output requires a project child in authorized worktree-write scope")
    allowed = [resolve_within_root(root, item) for item in task["permissions"]["allowed_roots"]]
    relative = path.relative_to(root).as_posix()
    if not any(item is not None and (path == item or item in path.parents) for item in allowed):
        raise EntryInputError("intake output exceeds permission roots")
    if not any(relative == scope.removesuffix("/**").rstrip("/")
               or relative.startswith(scope.removesuffix("/**").rstrip("/") + "/")
               for scope in task["write_scope"]):
        raise EntryInputError("intake output exceeds Task write scope")
    return path


class _Capture:
    def __init__(self, root, directory, *, model, task, clock, deadline, cancel, guard):
        self.root, self.directory = root, directory
        self.model, self.task = model, task
        self.clock, self.deadline, self.cancel, self.guard = clock, deadline, cancel, guard
        self.calls = 0
        self.refs = []
        self.blocked_reason = None
        self.capture_failed = False
        self.response = None
        self.body_redacted = False
        self.provider_name = None

    def save(self, name, value):
        _scope_path(self.root, self.directory.relative_to(self.root).as_posix(), self.task)
        path = self.directory / name
        raw = document_bytes(value)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        ref = FileReference(path.relative_to(self.root).as_posix(), hashlib.sha256(raw).hexdigest())
        self.refs.append(ref)
        return ref

    def event(self, kind, payload):
        cleaned, redactions = _safe(payload)
        with (self.directory / "events.jsonl").open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"kind": kind, "payload": cleaned, "redactions": redactions},
                                    ensure_ascii=False, allow_nan=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def check(self):
        now = self.clock()
        if isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
            self.blocked_reason = "INTAKE-CLOCK-UNAVAILABLE"
        elif self.cancel and self.cancel():
            self.blocked_reason = "INTAKE-CANCELLED"
        elif now >= self.deadline:
            self.blocked_reason = "INTAKE-DEADLINE"
        if self.blocked_reason:
            raise EntryInputError(self.blocked_reason)

    def record(self, kind, payload):
        if kind == "provider-request":
            self.check()
            request = payload["request"]
            if self.calls or request.model != self.model or request.tools:
                raise EntryInputError("intake permits only one request to its explicit model, without Tools")
            read_pinned_inputs(self.root, self.task["input_refs"])
            if self.guard is not None and self.guard(request) is not True:
                self.blocked_reason = "INTAKE-DISPATCH-NOT-ADMITTED"
                raise EntryInputError(self.blocked_reason)
            cleaned, redactions = _safe(request)
            if redactions:
                self.blocked_reason = "INTAKE-REQUEST-REDACTED"
                raise EntryInputError(self.blocked_reason)
            self.save("request.json", {"request": cleaned, "redactions": []})
        # Full responses are captured at the actual provider boundary, including
        # responses which the Session response-contract validator then rejects.
        if kind == "provider-response":
            self.event(kind, {"retained_response": "response.json"})
        else:
            self.event(kind, payload)


class _CapturedProvider:
    def __init__(self, provider, capture):
        self.provider, self.capture = provider, capture

    def capabilities(self):
        return self.provider.capabilities()

    def generate(self, request):
        capture = self.capture
        capture.check()
        capture.event("provider-invocation-started", {"model_calls": capture.calls + 1,
            "configured_provider": capture.provider_name, "model": request.model})
        capture.calls += 1
        try:
            response = self.provider.generate(request)
        except Exception as exc:
            # Provider error messages can contain transport credentials.
            capture.event("provider-invocation-failed", {"error_type": type(exc).__name__})
            raise
        capture.response = response
        try:
            cleaned, redactions = _safe(response)
            _, body_redactions = _safe(getattr(response, "output", ()))
            capture.body_redacted = bool(body_redactions)
            capture.save("response.json", {"response": cleaned, "redactions": redactions})
        except Exception:
            capture.capture_failed = True
            raise
        return response


def call_intake(
    root: str | Path, *, intake_task: Mapping[str, Any], intake_profile: Mapping[str, Any],
    protocol_ceiling: Mapping[str, Any], task_ceiling: Mapping[str, Any],
    provider: ModelProvider, model: str, directory: str, budget: IntakeCallBudget,
    context: Mapping[str, Any] | None = None, data_policy: DataPolicy | None = None,
    external_upload_authorized: bool = False,
    before_dispatch: Callable[[ModelRequest], bool] | None = None,
    cancel_requested: Callable[[], bool] | None = None, clock=time.monotonic,
) -> IntakeCallResult:
    """Record one intake attempt and publish only a complete, bounded draft.

    ``before_dispatch`` belongs to the trusted caller's current authorization.
    This function does not open keys/ledgers, retry, or establish qualifications.
    A denied write scope returns a rejection with no on-disk report; the caller
    must retain that returned result in its already authorized parent record.
    """
    project = Path(root).resolve()
    started = None
    capture = session = None
    status, reason, draft_refs = "rejected", "INTAKE-PREFLIGHT-REJECTED", ()
    details = None
    stage = "preflight"
    try:
        started = clock()
        if isinstance(started, bool) or not isinstance(started, (int, float)) or not math.isfinite(started):
            raise EntryInputError("intake clock must provide a finite monotonic reading")
        if not isinstance(budget, IntakeCallBudget):
            raise EntryInputError("an explicit IntakeCallBudget is required")
        task, profile = _copy(intake_task), _copy(intake_profile)
        protocol, ceiling = _copy(protocol_ceiling), _copy(task_ceiling)
        catalog = SchemaCatalog()
        for kind, document in (("task_packet", task), ("agent_profile", profile)):
            if catalog.validate(kind, document):
                raise EntryInputError("invalid intake " + kind)
        if (task["permissions"].get("network", "unspecified") == "unspecified"
                or any(profile["permission_ceiling"].get(key, "unspecified") == "unspecified"
                       for key in ("filesystem", "network"))):
            raise EntryInputError("intake Task/Profile permissions must be explicit")
        if not permission_policy_covers(PermissionPolicy.from_mapping(profile["permission_ceiling"]),
                                        PermissionPolicy.from_mapping(task["permissions"])):
            raise EntryInputError("independent intake Task permissions exceed Profile ceiling")
        destination = _scope_path(project, directory, task)
        destination.mkdir(parents=True, exist_ok=False)
        capture = _Capture(project, destination, model=model, task=task, clock=clock,
            deadline=started + min(budget.max_seconds, task["budget"].get("max_seconds", budget.max_seconds)),
            cancel=cancel_requested, guard=before_dispatch)
        for kind, document in (("project_protocol", protocol), ("task_packet", ceiling)):
            if catalog.validate(kind, document):
                raise EntryInputError("invalid human " + kind + " ceiling")
        if context is not None and not isinstance(context, Mapping):
            raise EntryInputError("intake context must be an explicit mapping")
        if type(external_upload_authorized) is not bool:
            raise EntryInputError("external upload authorization must be explicit boolean")
        if (task["budget"].get("max_turns", 1) < 1
                or budget.max_output_tokens > task["budget"].get("max_output_tokens", budget.max_output_tokens)
                or budget.max_seconds > task["budget"].get("max_seconds", budget.max_seconds)):
            raise EntryInputError("intake call exceeds its independent Task budget")
        declared = {document_bytes(ref) for ref in task["input_refs"]}
        if any(document_bytes(ref) not in declared for ref in ceiling["input_refs"]):
            raise EntryInputError("compiler input pins must be in the independent intake Task read set")
        inputs = {"intake_task": task, "intake_profile": profile, "protocol_ceiling": protocol,
                  "task_ceiling": ceiling, "context": _copy(context), "budget": to_plain(budget),
                  "external_upload_authorized": external_upload_authorized}
        cleaned, redactions = _safe(inputs)
        if redactions:
            raise EntryInputError("intake configuration contains forbidden secret/reasoning-shaped material")
        capture.save("inputs.json", cleaned)
        boundary = protocol["data_boundary"]
        if data_policy is not None and not isinstance(data_policy, DataPolicy):
            raise EntryInputError("data_policy must be a provider-neutral DataPolicy")
        policy = data_policy or DataPolicy()
        regions = set(boundary.get("allowed_regions", ()))
        if regions and policy.allowed_regions:
            regions.intersection_update(policy.allowed_regions)
            if not regions:
                raise EntryInputError("data policy regions do not intersect the human boundary")
        policy = replace(policy, local_only=policy.local_only or boundary.get("local_only", False),
            zero_data_retention_required=policy.zero_data_retention_required
                or boundary.get("zero_data_retention_required", False),
            allowed_regions=tuple(sorted(regions)) if regions else tuple(policy.allowed_regions))
        if policy.allow_provider_server_tools:
            raise EntryInputError("intake does not authorize provider server Tools")
        request = build_role_request(project, role="intake", task=task, profile=profile, model=model,
            input_refs=task["input_refs"], tools=(), max_output_tokens=budget.max_output_tokens,
            context={"control_ceilings": {"protocol": protocol, "task": ceiling}, "context": _copy(context)},
            data_policy=policy)
        capabilities = provider.capabilities()
        capture.provider_name = capabilities.provider
        binding, redactions = _safe({"configured_provider": capabilities.provider,
            "adapter_version": capabilities.adapter_version, "deployment": capabilities.deployment,
            "model": model, "data_policy": to_plain(policy)})
        if redactions:
            raise EntryInputError("configured provider/model/policy contains forbidden material")
        capture.save("binding.json", binding)
        if (capabilities.deployment != "local" and boundary.get("external_upload_requires_approval", False)
                and not external_upload_authorized):
            raise EntryInputError("remote intake upload requires explicit caller authorization")
        registry = ProviderRegistry()
        registry.register(capabilities.provider, _CapturedProvider(provider, capture))
        registry.require(capabilities.provider, request)
        capture.check()
        remaining = capture.deadline-clock()
        if remaining <= 0:
            capture.blocked_reason = "INTAKE-DEADLINE"
            raise EntryInputError(capture.blocked_reason)
        limits = ApiSessionLimits(max_model_turns=1, max_tool_calls=0, max_parallel_tool_calls=0,
            max_tool_result_chars=1, max_output_tokens_per_turn=budget.max_output_tokens,
            max_total_tokens=budget.reserved_tokens, max_seconds=remaining)
        stage = "model-call"
        session = IsolatedApiSessionRunner(registry, clock=clock).run(
            provider_name=capabilities.provider, request=request, limits=limits,
            cancel_requested=cancel_requested, event_sink=capture)
        capture.save("session.json", {"status": str(session.status), "stop_reason": session.stop_reason,
            "model_turns": session.model_turns, "tool_calls": session.tool_calls, "usage": to_plain(session.usage)})
        known = session.model_turns == capture.calls == 1 and all(
            type(value) is int and value >= 0 for value in (session.usage.input_tokens, session.usage.output_tokens))
        response = session.final_response
        if capture.calls == 0:
            status, reason = "not-started", capture.blocked_reason or "INTAKE-SESSION-NOT-STARTED"
        elif not known or capture.capture_failed:
            status, reason = "failed", "INTAKE-USAGE-OR-CAPTURE-UNKNOWN"
        elif session.usage.output_tokens > budget.max_output_tokens:
            status, reason = "failed", "INTAKE-OUTPUT-TOKEN-BUDGET"
        elif session.status == ApiSessionStatus.BLOCKED:
            status, reason = "rejected", "INTAKE-MODEL-REFUSED"
        elif session.status != ApiSessionStatus.COMPLETED:
            status, reason = "failed", "INTAKE-SESSION-NOT-COMPLETED"
        elif response is None or response.finish_reason != FinishReason.COMPLETE or capture.body_redacted:
            status, reason = "rejected", "INTAKE-OUTPUT-NOT-COMPLETE-AND-PUBLISHABLE"
        else:
            capture.check()
            text = "\n".join(block.text for block in response.output if block.kind == "text" and block.text is not None)
            stage = "compile"
            draft = compile_control_draft(project, response=text, protocol_ceiling=protocol, task_ceiling=ceiling)
            capture.check()
            draft_directory = (destination / "draft").relative_to(project).as_posix()
            stage = "publish"
            draft_refs = persist_control_draft(project, directory=draft_directory, draft=draft)
            capture.check()
            status, reason = "success", "INTAKE-DRAFT-PUBLISHED"
    except Exception as exc:
        if capture is not None and capture.blocked_reason:
            status = "not-started" if capture.calls == 0 else "failed"
            reason = capture.blocked_reason
        elif isinstance(exc, FileExistsError):
            status, reason = "rejected", "INTAKE-OUTPUT-EXISTS"
        elif isinstance(exc, (EntryInputError, ValueError, TypeError)):
            status = "failed" if stage == "model-call" else "rejected"
            reason = {"compile": "INTAKE-COMPILER-REJECTED", "publish": "INTAKE-PUBLICATION-REJECTED",
                      "model-call": "INTAKE-SESSION-FAILED"}.get(stage, "INTAKE-PREFLIGHT-REJECTED")
        else:
            status, reason = "failed", "INTAKE-CALL-OR-PUBLICATION-FAILED"
        # Do not retain arbitrary provider/transport exception messages.
        details = {"error_type": type(exc).__name__}
        if isinstance(exc, (EntryInputError, CapabilityGap, DataPolicyGap, ModelNotSupported)):
            details["detail"] = _safe(str(exc))[0]

    calls = capture.calls if capture is not None else 0
    known = calls == 0 or (session is not None and session.model_turns == calls
        and all(type(value) is int and value >= 0 for value in (session.usage.input_tokens, session.usage.output_tokens)))
    input_tokens = 0 if calls == 0 else session.usage.input_tokens if known else None
    output_tokens = 0 if calls == 0 else session.usage.output_tokens if known else None
    reserved = budget.reserved_tokens if isinstance(budget, IntakeCallBudget) else 0
    held = reserved if calls and not known else 0
    refs = list(capture.refs) if capture is not None else []
    report_ref = None
    if capture is not None:
        # Discover only this publisher's known output filenames, including a
        # retained partial publication. Never traverse arbitrary workspace refs.
        try:
            draft_directory = capture.directory / "draft"
            if draft_directory.is_dir():
                for path in sorted(draft_directory.iterdir()):
                    if path.is_file() and not path.is_symlink() and (path.name in {"project-protocol.json", "task.json", "method.json", "draft.json"}
                            or path.name.startswith("requirement-") and path.suffix == ".json"):
                        refs.append(FileReference(path.relative_to(project).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
            journal = capture.directory / "events.jsonl"
            if journal.is_file():
                refs.append(FileReference(journal.relative_to(project).as_posix(), hashlib.sha256(journal.read_bytes()).hexdigest()))
        except OSError:
            status, reason = "failed", "INTAKE-ARTIFACT-CAPTURE-FAILED"
        payload = {"status": status, "reason": reason, "details": details, "model_calls": calls,
            "configured_provider": capture.provider_name, "requested_model": model,
            "input_tokens": input_tokens, "output_tokens": output_tokens, "reserved_tokens": reserved,
            "held_tokens": held, "session_status": str(session.status) if session else None,
            "stop_reason": session.stop_reason if session else None,
            "draft_refs": to_plain(draft_refs), "artifact_refs": to_plain(refs),
            "qualification": "intake-control-draft-only", "human_acceptance": False,
            "limitations": ["Normalized evidence is sanitized; no transport headers or hidden reasoning.",
                            "No Host, Receipt, source/live qualification, or research execution acceptance."]}
        try:
            readable = capture.directory / "REPORT.md"
            _scope_path(project, capture.directory.relative_to(project).as_posix(), capture.task)
            with readable.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(f"# Intake result\n\nStatus: {status}\n\nReason: {reason}\n\n"
                    + f"Details: {json.dumps(details, ensure_ascii=False)}\n\n"
                    + f"Session status: {str(session.status) if session else None}; "
                    f"stop reason: {session.stop_reason if session else None}.\n\n"
                    +
                    f"Model calls: {calls}; input tokens: {input_tokens}; output tokens: {output_tokens}; "
                    f"unknown usage holds: {held}.\n\nDraft files: {len(draft_refs)}.\n\n"
                    + "".join(f"- {ref.path}; sha256={ref.sha256}\n" for ref in draft_refs)
                    + "\n"
                    +
                    "Caller must account for this usage in the same Run. Human acceptance remains separate.\n")
            refs.append(FileReference(readable.relative_to(project).as_posix(), hashlib.sha256(readable.read_bytes()).hexdigest()))
            report_ref = capture.save("result.json", payload)
            refs.append(report_ref)
        except (OSError, ValueError, TypeError):
            status, reason = "failed", "INTAKE-RESULT-CAPTURE-FAILED"
            report_ref = None
    return IntakeCallResult(status, reason, calls, input_tokens, output_tokens, reserved, held,
        str(session.status) if session else None, session.stop_reason if session else None,
        tuple(draft_refs) if status == "success" else (), tuple(refs), report_ref, details)


__all__ = ["IntakeCallBudget", "IntakeCallResult", "call_intake"]
