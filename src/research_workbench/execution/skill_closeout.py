"""Skill execution closeout 1.0.0 and independent, provider-free file replay."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from research_workbench.artifacts.integrity import resolve_within_root

from research_workbench.execution.generic_closeout import (
    CloseoutPin, GenericCloseoutValidationError, _build_execution_receipt,
    _load_pin, _load_trace_events, _plain,
)
from research_workbench.execution.host import load_resolved_execution_view
from research_workbench.execution.runtime_bundle import load_runtime_bundle
from research_workbench.execution.skill_facts import (
    SkillExecutionFactError, _frozen, selected_skill_consumption,
    validate_skill_consumption,
)
from research_workbench.validation.schemas import SchemaCatalog


@dataclass(frozen=True, slots=True)
class ValidatedSkillReceipt:
    project_root: Path
    receipt_path: Path
    receipt_sha256: str
    document: Mapping[str, Any]


def _validate_skill_closure(view, host, trace_path, trace, *, fact_pin, schema_root=None):
    root = view.project_root
    try:
        requested = _plain(selected_skill_consumption(view, schema_root=schema_root))
        actual = host.get("actual_skill_consumption")
        if host["execution_phase"] == "post-call":
            observed = validate_skill_consumption(root, actual, schema_root=schema_root)
            if actual["supply_report_ref"]["ref"] != host["actual_supply_report_ref"]:
                raise SkillExecutionFactError("Host actual Supply differs from consumed Supply")
            if host["status"] == "completed" and actual != requested:
                raise SkillExecutionFactError("completed Skill consumption differs from selected View")
            if (host.get("diagnostic", {}).get("code") == "HOST-ACTUAL-SKILL-DRIFT"
                    and actual == requested):
                raise SkillExecutionFactError("Skill drift diagnostic lacks actual drift")
            events = _load_trace_events(root, trace_path, trace)
            reads = {}
            for position, event in enumerate(events):
                payload = event.get("payload", {})
                if event.get("event_type") == "content-read":
                    path = resolve_within_root(root, payload.get("path", ""))
                    reads.setdefault(path, []).append((payload.get("content_sha256"), position))
            for key in ("supply_report_ref", "projection_ref"):
                ref = actual[key]
                observed_reads = reads.get(resolve_within_root(root, ref["path"]), [])
                if len(observed_reads) != 1 or observed_reads[0][0] != ref["sha256"]:
                    raise SkillExecutionFactError("Skill actual input requires exactly one hash-pinned Trace read")
            # Reuse the independently validated pre-use and post-call fact pins.
            assert fact_pin is not None
            consumption_pin, binding_pin = fact_pin
            writes = [position for position, event in enumerate(events)
                      if event.get("event_type") == "file-revision"
                      and event.get("payload", {}).get("path") == consumption_pin.path
                      and event["payload"].get("action") == "created"
                      and event["payload"].get("new_sha256") == consumption_pin.sha256]
            if len(writes) != 1 or any(
                reads[resolve_within_root(root, actual[key]["path"])][0][1] >= writes[0]
                for key in ("supply_report_ref", "projection_ref")
            ):
                raise SkillExecutionFactError("Skill fact must be captured after its exact input reads")
            provider_ids = {item["message_id"] for item in trace["messages"]
                            if item["kind"] == "provider-request"}
            invocations = [position for position, event in enumerate(events)
                           if event.get("event_type") == "tool-call"
                           or (event.get("event_type") == "message-capture"
                               and event.get("payload", {}).get("message_id") in provider_ids)]
            if any(position <= writes[0] for position in invocations):
                raise SkillExecutionFactError("Skill input capture occurred after an execution invocation")
            post_writes = [position for position, event in enumerate(events)
                           if event.get("event_type") == "file-revision"
                           and event.get("payload", {}).get("path") == binding_pin.path
                           and event["payload"].get("action") == "created"
                           and event["payload"].get("new_sha256") == binding_pin.sha256]
            provider_messages = {item["message_id"] for item in trace["messages"]
                                 if item["kind"] in {"provider-request", "provider-response"}}
            activity = [position for position, event in enumerate(events)
                        if event.get("event_type") == "tool-call"
                        or (event.get("event_type") == "message-capture"
                            and event.get("payload", {}).get("message_id") in provider_messages)]
            if (len(post_writes) != 1 or post_writes[0] <= writes[0]
                    or any(position >= post_writes[0] for position in activity)):
                raise SkillExecutionFactError("Actual binding fact must be captured after execution activity")
            supply = observed.supply
        else:
            # The versioned Host schema has already excluded preflight actual facts.
            supply = validate_skill_consumption(root, requested, schema_root=schema_root).supply
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise GenericCloseoutValidationError("Skill execution closure invalid: " + str(exc)) from exc
    bundle = view.runtime_bundle
    snapshot_ref = _plain(view.document["snapshot_ref"])
    snapshot = bundle.documents[(root / snapshot_ref["path"]).resolve()]
    resolution = snapshot["resolution_ref"]
    fields = {
        "contract_version": "1.0.0",
        "record_kind": "skill_execution_receipt",
        "runtime_bundle_ref": _plain(view.document["runtime_bundle_ref"]),
        "snapshot_ref": snapshot_ref,
        "resolution_ref": {"ref": resolution["ref"], "path": resolution["document_path"],
                           "sha256": resolution["content_hash"].removeprefix("sha256:").lower()},
        "requested_skill_consumption": requested,
    }
    if actual is not None:
        fields.update(actual_skill_consumption=_plain(actual), actual_binding=_plain(host["actual_binding"]),
                      actual_supply_report_ref=host["actual_supply_report_ref"])
    return fields, supply


def build_skill_execution_receipt(
    view, bundle, *, host_report: CloseoutPin, trace_index: CloseoutPin,
    validations: Sequence[CloseoutPin], receipt_id: str, schema_root=None,
) -> dict[str, Any]:
    """Consume frozen evidence under Skill closeout 1.0.0; never create Trace."""
    return _build_execution_receipt(
        view, bundle, host_report=host_report, trace_index=trace_index,
        validations=validations, receipt_id=receipt_id, schema_root=schema_root,
        skill_extension=True,
    )


def validate_skill_execution_receipt(
    receipt_path: str | Path, *, expected_sha256: str,
    project_root: str | Path, schema_root=None,
) -> ValidatedSkillReceipt:
    """Reload the Receipt's own Bundle/View and all evidence in a fresh process."""
    root = Path(project_root).resolve()
    relative = Path(receipt_path)
    if relative.is_absolute():
        try:
            relative = relative.resolve().relative_to(root)
        except ValueError as exc:
            raise GenericCloseoutValidationError("Skill Receipt is outside project root") from exc
    path, receipt = _load_pin(
        root, CloseoutPin(relative.as_posix(), expected_sha256),
        kind="skill_execution_receipt", catalog=SchemaCatalog(schema_root),
    )
    bundle_ref = receipt["runtime_bundle_ref"]
    bundle = load_runtime_bundle(bundle_ref["path"], project_root=root, schema_root=schema_root)
    if bundle.manifest_sha256 != bundle_ref["sha256"]:
        raise GenericCloseoutValidationError("Skill Receipt Runtime Bundle pin mismatch")
    view_ref = receipt["view_ref"]
    view = load_resolved_execution_view(
        view_ref["path"], expected_sha256=view_ref["sha256"], bundle=bundle, schema_root=schema_root,
    )
    rebuilt = build_skill_execution_receipt(
        view, bundle,
        host_report=CloseoutPin(**receipt["host_report_ref"]),
        trace_index=CloseoutPin(**receipt["trace_ref"]),
        validations=tuple(CloseoutPin(**item) for item in receipt["validation_refs"]),
        receipt_id=receipt["receipt_id"], schema_root=schema_root,
    )
    if rebuilt != receipt:
        raise GenericCloseoutValidationError("Skill Receipt deterministic replay drift")
    return ValidatedSkillReceipt(root, path, expected_sha256.removeprefix("sha256:").lower(), _frozen(receipt))
