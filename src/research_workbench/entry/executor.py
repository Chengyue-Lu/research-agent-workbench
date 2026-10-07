"""Optional API implementation of the application's RoleExecutor port."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from research_workbench.adapters.models import ApiSessionLimits, ClientTool, ModelProvider
from research_workbench.entry.driver import ObservedExecutionBinding, execute_role_slice
from research_workbench.entry.roles import build_role_request
from research_workbench.entry.workflow import RoleInvocation, RoleObservation
from research_workbench.execution.generic_closeout import CloseoutPin
from research_workbench.execution.host import load_resolved_execution_view
from research_workbench.execution.runtime_bundle import load_runtime_bundle


@dataclass(frozen=True)
class FrozenRoleBinding:
    bundle_ref: CloseoutPin
    view_ref: CloseoutPin
    provider: ModelProvider
    binding_observer: Callable[[ModelProvider], ObservedExecutionBinding]
    output_dir: str
    output_path: str
    output_contract: str
    attempt_id: str
    schema_root: str | Path | None = None
    host_clock: Any = None
    session_clock: Any = None
    tools: tuple[ClientTool, ...] = ()
    tool_refs: Mapping[str, str] = field(default_factory=dict)
    session_limits: ApiSessionLimits | None = None


class FrozenRoleExecutor:
    """Bind each actual Task through a trusted, explicit binding factory.

    The factory is application-owned Research Control. It must freeze the exact
    Task/Method/Supply via existing producers; this class never chooses Supply
    or rewrites a frozen View. Native adapters can implement RoleExecutor without
    importing this optional API implementation.
    """
    def __init__(self, root, *, binding_factory: Callable[[RoleInvocation], FrozenRoleBinding],
                 accountable_owner: str, cancel_requested=None):
        self.root = Path(root).resolve()
        self.factory = binding_factory
        self.owner = accountable_owner
        self.cancel = cancel_requested
        self.results = []

    def __call__(self, invocation: RoleInvocation) -> RoleObservation:
        binding = self.factory(invocation)
        bundle = load_runtime_bundle(binding.bundle_ref.path, project_root=self.root,
                                     schema_root=binding.schema_root)
        if bundle.manifest_sha256 != binding.bundle_ref.sha256:
            raise ValueError("binding factory returned a drifted Bundle")
        view = load_resolved_execution_view(binding.view_ref.path, expected_sha256=binding.view_ref.sha256,
                                           bundle=bundle, schema_root=binding.schema_root)
        task_path = (self.root/view.document["task_ref"]["path"]).resolve()
        frozen_task = bundle.documents[task_path]

        def plain(value):
            if isinstance(value, Mapping):
                return {k: plain(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [plain(v) for v in value]
            return value

        if plain(frozen_task) != plain(invocation.task):
            raise ValueError("binding factory substituted a different role Task")

        supply_pin = view.document["selected_supply_report_ref"]
        supply = bundle.documents[(self.root / supply_pin["path"]).resolve()]
        context = plain(invocation.context)
        context["execution_adapter_constraints"] = {
            "supply_ref": plain(supply_pin),
            "required_permissions": plain(supply["required_permissions"]),
            "data_egress_behavior": plain(supply["data_egress_behavior"]),
            "purpose": "Execution prerequisites only; no additional permission or selection authority.",
        }
        context["driver_output_publication"] = {
            "publisher": "SessionExecutionDriver",
            "status": "pending",
            "output_path": binding.output_path,
            "output_contract": binding.output_contract,
            "boundaries": {"permission_grant": False, "publication_complete": False},
        }

        def builder(*args, **kwargs):
            return build_role_request(*args, **kwargs, context=context,
                                      instructions=invocation.instructions)

        limits = binding.session_limits or ApiSessionLimits(
            max_model_turns=invocation.max_model_calls, max_tool_calls=0,
            max_parallel_tool_calls=0, max_tool_result_chars=1,
            max_output_tokens_per_turn=invocation.max_output_tokens,
            max_total_tokens=invocation.max_total_tokens, max_seconds=invocation.max_seconds)
        if binding.tools and binding.session_limits is None:
            raise ValueError("Tools require explicit bounded Session limits")
        if (limits.max_model_turns > invocation.max_model_calls
                or limits.max_output_tokens_per_turn > invocation.max_output_tokens
                or limits.max_seconds > invocation.max_seconds
                or (limits.max_total_tokens is not None
                    and limits.max_total_tokens > invocation.max_total_tokens)):
            raise ValueError("Session limits exceed the caller's reserved slice")
        limits = replace(limits, max_total_tokens=(limits.max_total_tokens
            if limits.max_total_tokens is not None else invocation.max_total_tokens),
            allowed_tool_side_effects=frozenset(limits.allowed_tool_side_effects))
        options = dict(bundle_ref=binding.bundle_ref, view_ref=binding.view_ref, role=invocation.role,
                       provider=binding.provider, binding_observer=binding.binding_observer,
                       output_dir=binding.output_dir, output_path=binding.output_path,
                       output_contract=binding.output_contract, attempt_id=binding.attempt_id,
                       report_id="HOST-"+binding.attempt_id, receipt_id="RECEIPT-"+binding.attempt_id,
                       accountable_owner=self.owner, request_builder=builder, cancel_requested=self.cancel,
                       limits=limits, tools=tuple(binding.tools), tool_refs=dict(binding.tool_refs),
                       schema_root=binding.schema_root)
        if binding.host_clock is not None:
            options["host_clock"] = binding.host_clock
        if binding.session_clock is not None:
            options["session_clock"] = binding.session_clock
        result = execute_role_slice(self.root, **options)
        self.results.append(result)
        session = result.session
        text = ""
        if session is not None and session.final_response is not None:
            text = "\n".join(i.text for i in session.final_response.output if i.text is not None)
        pins = [result.host_report_ref, result.trace_ref]
        if result.validation_ref:
            pins.append(result.validation_ref)
        if result.receipt_ref:
            pins.append(result.receipt_ref)
        status = result.host_report["status"]
        limitations = () if result.closeout_error is None else (result.closeout_error,)
        if status != "completed":
            limitations += tuple(str(item["code"]) for item in result.host_report.get("diagnostics", ())
                                 if isinstance(item, Mapping) and item.get("code"))
            if session is not None:
                limitations += ("Session stopped: " + session.stop_reason,)
        if status == "completed" and result.receipt_ref is None:
            status = "post-call-failed"
        facts = result.host_report["actual_facts"]
        attempted = facts.get("provider_invocations")
        if isinstance(attempted, bool) or not isinstance(attempted, int) or attempted < 0:
            raise ValueError("actual attempted Provider calls are unavailable; usage requires review")
        if attempted == 0 and facts.get("complete") is not True:
            # Host's driver-exception report uses incomplete zero placeholders.
            # They cannot establish that no outbound request occurred.
            raise ValueError("incomplete execution facts cannot prove zero Provider calls")
        # A failed send can have one attempted request and zero responses. Never
        # replace that outbound fact with Session's completed-response count.
        usage_known = attempted == 0 or (session is not None
            and session.model_turns == attempted
            and session.usage.input_tokens is not None and session.usage.output_tokens is not None)
        input_tokens = session.usage.input_tokens if session is not None and usage_known else None
        output_tokens = session.usage.output_tokens if session is not None and usage_known else None
        if attempted == 0:
            input_tokens = output_tokens = 0
        tool_calls = facts.get("tool_invocations", 0)
        if isinstance(tool_calls, bool) or not isinstance(tool_calls, int) or tool_calls < 0:
            raise ValueError("actual Tool calls are unavailable; execution requires review")
        artifact_refs = [{"path": p.path, "sha256": p.sha256} for p in pins]
        artifact_refs.extend({"path": item["path"], "sha256": item["sha256"]}
                             for item in result.host_report.get("artifacts", ()))
        return RoleObservation(status, text, attempted, input_tokens, output_tokens,
             tuple(artifact_refs), limitations, tool_calls,
             () if result.receipt_ref is None else ({"path": result.receipt_ref.path,
                                                    "sha256": result.receipt_ref.sha256},))


__all__ = ["FrozenRoleBinding", "FrozenRoleExecutor"]
