"""Generic no-Skill/direct-Tool execution-only closeout for M11 Core."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.execution.host import (
    ValidatedExecutionView,
    load_resolved_execution_view,
)
from research_workbench.execution.runtime_bundle import ValidatedRuntimeBundle
from research_workbench.io import load_document_bytes
from research_workbench.observability.trace import validate_attempt_trace
from research_workbench.validation.schemas import SchemaCatalog


@dataclass(frozen=True, slots=True)
class CloseoutPin:
    path: str
    sha256: str


@dataclass(frozen=True, slots=True)
class ValidatedGenericReceipt:
    project_root: Path
    receipt_path: Path
    receipt_sha256: str
    document: Mapping[str, Any]


class GenericCloseoutValidationError(ValueError):
    pass


def _normalized_hash(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.lower().removeprefix("sha256:")
    if len(normalized) != 64:
        return None
    try:
        int(normalized, 16)
    except ValueError:
        return None
    return normalized


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _load_pin(
    root: Path,
    pin: CloseoutPin,
    *,
    kind: str,
    catalog: SchemaCatalog,
) -> tuple[Path, Mapping[str, Any]]:
    path = resolve_within_root(root, pin.path)
    if path is None or not path.is_file():
        raise GenericCloseoutValidationError(f"{kind} input is missing or outside project root")
    content = path.read_bytes()
    if _normalized_hash(pin.sha256) != hash_bytes(content):
        raise GenericCloseoutValidationError(f"{kind} input hash mismatch")
    try:
        document = load_document_bytes(path, content)
    except Exception as exc:
        raise GenericCloseoutValidationError(f"{kind} input is not parseable") from exc
    errors = catalog.validate(kind, document)
    if errors:
        raise GenericCloseoutValidationError(f"{kind} input is schema-invalid")
    if not isinstance(document, Mapping):
        raise GenericCloseoutValidationError(f"{kind} input must be an object")
    return path, document


def _file_ref(root: Path, path: Path) -> dict[str, str]:
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": hash_bytes(path.read_bytes()),
    }


def _validate_artifact_refs(root: Path, artifacts: Sequence[Mapping[str, Any]]) -> None:
    for artifact in artifacts:
        path = resolve_within_root(root, artifact.get("path", ""))
        if path is None or not path.is_file():
            raise GenericCloseoutValidationError("Host artifact is missing or outside project root")
        if _normalized_hash(artifact.get("sha256")) != hash_bytes(path.read_bytes()):
            raise GenericCloseoutValidationError("Host artifact hash mismatch")


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise GenericCloseoutValidationError(f"{field} is not an RFC3339 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GenericCloseoutValidationError(f"{field} is not an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise GenericCloseoutValidationError(f"{field} lacks a timezone")
    return parsed


def _validate_host_view_closure(
    host: Mapping[str, Any], view: ValidatedExecutionView
) -> None:
    expected_view_ref = {
        "ref": f"{view.document['view_id']}@r{view.document['revision']}",
        "path": view.view_path.relative_to(view.project_root).as_posix(),
        "sha256": view.view_sha256,
    }
    if (
        host.get("view_ref") != expected_view_ref
        or host.get("runtime_bundle_ref") != view.document.get("runtime_bundle_ref")
        or host.get("task_ref") != view.document.get("task_ref")
    ):
        raise GenericCloseoutValidationError("Host report View/Bundle/Task lineage mismatch")
    if host.get("actual_binding") != _plain(view.document.get("binding")):
        raise GenericCloseoutValidationError("Host actual binding does not equal frozen View binding")
    if host.get("actual_supply_report_ref") != view.document.get(
        "selected_supply_report_ref", {}
    ).get("ref"):
        raise GenericCloseoutValidationError(
            "Host actual Supply does not equal frozen View selected Supply"
        )
    if _timestamp(host.get("completed_at"), "host.completed_at") < _timestamp(
        host.get("started_at"), "host.started_at"
    ):
        raise GenericCloseoutValidationError("Host report time interval is reversed")


def _trace_relative_pin(
    root: Path, trace_path: Path, reference: Mapping[str, Any]
) -> CloseoutPin:
    path = resolve_within_root(trace_path.parent, reference.get("path", ""))
    if path is None:
        raise GenericCloseoutValidationError("Execution Trace child reference escapes its archive")
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError as exc:
        raise GenericCloseoutValidationError(
            "Execution Trace child reference escapes project root"
        ) from exc
    return CloseoutPin(relative, str(reference.get("sha256", "")))


def _load_trace_events(
    root: Path, trace_path: Path, trace: Mapping[str, Any]
) -> tuple[Mapping[str, Any], ...]:
    ledger = trace.get("event_ledger", {})
    path = resolve_within_root(trace_path.parent, ledger.get("path", ""))
    if path is None or not path.is_file():
        raise GenericCloseoutValidationError("Execution Trace event ledger is missing")
    content = path.read_bytes()
    if _normalized_hash(ledger.get("sha256")) != hash_bytes(content):
        raise GenericCloseoutValidationError("Execution Trace event ledger hash mismatch")
    try:
        events = tuple(
            json.loads(line)
            for line in content.decode("utf-8").splitlines()
            if line.strip()
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GenericCloseoutValidationError("Execution Trace event ledger is not parseable") from exc
    if len(events) != ledger.get("event_count") or not all(
        isinstance(item, Mapping) for item in events
    ):
        raise GenericCloseoutValidationError("Execution Trace event ledger count/shape mismatch")
    return events


def _validate_host_trace_facts(
    root: Path,
    host: Mapping[str, Any],
    trace_path: Path,
    trace: Mapping[str, Any],
    supply: Mapping[str, Any],
    *,
    catalog: SchemaCatalog,
) -> None:
    actors_ref = trace.get("actors_ref", {})
    _, actors = _load_pin(
        root,
        _trace_relative_pin(root, trace_path, actors_ref),
        kind="agent_trace_actors",
        catalog=catalog,
    )
    provider_identities = [
        item.get("runtime_identity")
        for item in actors.get("actors", ())
        if isinstance(item, Mapping) and item.get("actor_type") == "model-provider"
    ]
    runtime_identities = [
        item.get("runtime_identity")
        for item in actors.get("actors", ())
        if isinstance(item, Mapping) and item.get("actor_type") == "runtime-adapter"
    ]
    actual_binding = host.get("actual_binding", {})
    expected_provider = (
        actual_binding.get("provider", {}).get("ref")
        if isinstance(actual_binding, Mapping)
        else None
    )
    expected_runtime = (
        actual_binding.get("runtime", {}).get("ref")
        if isinstance(actual_binding, Mapping)
        else None
    )
    if provider_identities != [expected_provider]:
        raise GenericCloseoutValidationError(
            "Execution Trace provider actor does not equal Host actual provider binding"
        )
    if runtime_identities != [expected_runtime]:
        raise GenericCloseoutValidationError(
            "Execution Trace runtime actor does not equal Host actual runtime binding"
        )

    events = _load_trace_events(root, trace_path, trace)
    provider_invocations = sum(
        1 for item in trace.get("messages", ()) if item.get("kind") == "provider-request"
    )
    tool_operations: dict[str, str] = {}
    for event in events:
        if event.get("event_type") != "tool-call":
            continue
        payload = event.get("payload", {})
        operation_id = payload.get("operation_id")
        tool_name = payload.get("tool_name")
        if isinstance(operation_id, str) and isinstance(tool_name, str):
            existing = tool_operations.get(operation_id)
            if existing is not None and existing != tool_name:
                raise GenericCloseoutValidationError(
                    "Execution Trace reuses one tool operation identity for different tools"
                )
            tool_operations[operation_id] = tool_name
    facts = host.get("actual_facts", {})
    if facts.get("provider_invocations") != provider_invocations:
        raise GenericCloseoutValidationError(
            "Host provider invocation count does not match Execution Trace"
        )
    if facts.get("tool_invocations") != len(tool_operations):
        raise GenericCloseoutValidationError(
            "Host tool invocation count does not match Execution Trace"
        )
    trace_tool_refs = set(tool_operations.values())
    if set(facts.get("tool_refs", ())) != trace_tool_refs:
        raise GenericCloseoutValidationError(
            "Host actual tool identities do not match Execution Trace"
        )
    selected_tool_refs = {
        item.get("component_ref")
        for item in supply.get("supply_identity", {}).get("components", ())
        if isinstance(item, Mapping) and item.get("component_kind") == "tool"
    }
    if not trace_tool_refs.issubset(selected_tool_refs):
        raise GenericCloseoutValidationError(
            "Execution Trace tool identity is outside the selected Supply"
        )


def build_generic_execution_receipt(
    view: ValidatedExecutionView,
    bundle: ValidatedRuntimeBundle,
    *,
    host_report: CloseoutPin,
    trace_index: CloseoutPin,
    validations: Sequence[CloseoutPin],
    receipt_id: str,
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build an execution-only Receipt from exact facts; never publish files."""

    root = bundle.project_root
    if root != view.project_root:
        raise GenericCloseoutValidationError("View and Runtime Bundle roots differ")
    catalog = SchemaCatalog(schema_root)
    host_path, host = _load_pin(root, host_report, kind="execution_host_report", catalog=catalog)
    host_status = host.get("status")
    if host_status not in {"completed", "failed", "blocked"}:
        raise GenericCloseoutValidationError("Host report has an unsupported lifecycle status")
    if host_status == "completed" and host.get("actual_facts", {}).get("complete") is not True:
        raise GenericCloseoutValidationError("a completed Host report must be fact-complete")
    expected_view_ref = {
        "ref": f"{view.document['view_id']}@r{view.document['revision']}",
        "path": view.view_path.relative_to(root).as_posix(),
        "sha256": view.view_sha256,
    }
    _validate_host_view_closure(host, view)

    trace_path, trace = _load_pin(root, trace_index, kind="agent_trace_index", catalog=catalog)
    trace_result = validate_attempt_trace(root, trace_path)
    if trace_result.blocked:
        details = "; ".join(
            f"{risk.code}:{risk.message}" for risk in trace_result.risks
        )
        raise GenericCloseoutValidationError("Execution Trace validation is blocked: " + details)
    task_ref = view.document["task_ref"]
    if (
        trace.get("task_id") != str(task_ref["ref"]).split("@r", 1)[0]
        or trace.get("task_revision") != int(str(task_ref["ref"]).rsplit("@r", 1)[1])
        or trace.get("attempt_id") != host.get("attempt_id")
        or trace.get("attempt_status") != host_status
        or trace.get("trace_status") != "frozen"
        or trace.get("completeness") != "complete"
    ):
        raise GenericCloseoutValidationError("Execution Trace identity/status/completeness mismatch")

    artifacts = host.get("artifacts", ())
    if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)):
        raise GenericCloseoutValidationError("Host artifacts must be an array")
    if host_status == "completed" and not artifacts:
        raise GenericCloseoutValidationError("completed Host report requires artifacts")
    _validate_artifact_refs(root, artifacts)
    expected_subjects = {
        (host_report.path, _normalized_hash(host_report.sha256)),
        (trace_index.path, _normalized_hash(trace_index.sha256)),
        *(
            (str(item["path"]), _normalized_hash(item["sha256"]))
            for item in artifacts
            if isinstance(item, Mapping)
        ),
    }
    actual_subjects: set[tuple[str, str | None]] = set()
    validation_refs: list[dict[str, str]] = []
    if not validations:
        raise GenericCloseoutValidationError("at least one deterministic validation report is required")
    for pin in validations:
        validation_path, validation = _load_pin(
            root, pin, kind="deterministic_check_report", catalog=catalog
        )
        if validation.get("status") != "pass":
            raise GenericCloseoutValidationError("deterministic validation did not pass")
        for subject in validation.get("subject_refs", ()):
            if isinstance(subject, Mapping):
                actual_subjects.add(
                    (str(subject.get("path")), _normalized_hash(subject.get("sha256")))
                )
        checker_ref = validation.get("checker", {}).get("source_ref", {})
        checker_path = resolve_within_root(root, checker_ref.get("path", ""))
        if (
            checker_path is None
            or not checker_path.is_file()
            or _normalized_hash(checker_ref.get("sha256")) != hash_bytes(checker_path.read_bytes())
        ):
            raise GenericCloseoutValidationError("deterministic checker source pin mismatch")
        validation_refs.append(_file_ref(root, validation_path))
    if actual_subjects != expected_subjects:
        raise GenericCloseoutValidationError("validation subjects must equal Host report + Trace + artifacts")

    supply = next(
        document
        for path, document in bundle.documents.items()
        if any(
            item["kind"] == "capability_supply_report"
            and (root / str(item["path"])).resolve() == path
            for item in bundle.manifest["documents"]
        )
    )
    supply_kind = supply["supply_identity"]["supply_kind"]
    execution_kind = {
        "procedure": "no-skill",
        "tool": "direct-tool",
        "adapter-provider": "adapter-provider",
    }.get(supply_kind)
    if execution_kind is None:
        raise GenericCloseoutValidationError("Skill Supply is outside M11 Core closeout")
    _validate_host_trace_facts(
        root, host, trace_path, trace, supply, catalog=catalog
    )
    receipt = {
        "schema_version": "0.1.0",
        "receipt_id": receipt_id,
        "attempt_id": host["attempt_id"],
        "execution_kind": execution_kind,
        "status": host_status,
        "completion_claim": "execution-only" if host_status == "completed" else "none",
        "task_ref": _plain(view.document["task_ref"]),
        "view_ref": expected_view_ref,
        "host_report_ref": _file_ref(root, host_path),
        "trace_ref": _file_ref(root, trace_path),
        "artifact_refs": _plain(artifacts),
        "validation_refs": validation_refs,
        "started_at": host["started_at"],
        "finished_at": host["completed_at"],
        "limitations": [
            "Execution completion does not promote a scientific Claim or satisfy a Human Gate."
        ],
        "boundaries": {
            "skill_assignment": "absent",
            "method_decision": False,
            "claim_effect": False,
            "human_decision": False,
            "topic5_recovery": False,
        },
    }
    if catalog.validate("generic_execution_receipt", receipt):
        raise GenericCloseoutValidationError("generated Generic Execution Receipt is schema-invalid")
    return receipt


def validate_generic_execution_receipt(
    receipt_path: str | Path,
    *,
    expected_sha256: str,
    bundle: ValidatedRuntimeBundle,
    schema_root: str | Path | None = None,
) -> ValidatedGenericReceipt:
    """Replay a Generic Receipt from exact files and deterministic builders."""

    root = bundle.project_root
    relative = Path(receipt_path)
    if relative.is_absolute():
        path = relative.resolve()
        relative_text = path.relative_to(root).as_posix()
    else:
        relative_text = relative.as_posix()
    path, receipt = _load_pin(
        root,
        CloseoutPin(relative_text, expected_sha256),
        kind="generic_execution_receipt",
        catalog=SchemaCatalog(schema_root),
    )
    view_ref = receipt["view_ref"]
    view = load_resolved_execution_view(
        view_ref["path"],
        expected_sha256=view_ref["sha256"],
        bundle=bundle,
        schema_root=schema_root,
    )
    rebuilt = build_generic_execution_receipt(
        view,
        bundle,
        host_report=CloseoutPin(
            receipt["host_report_ref"]["path"], receipt["host_report_ref"]["sha256"]
        ),
        trace_index=CloseoutPin(receipt["trace_ref"]["path"], receipt["trace_ref"]["sha256"]),
        validations=tuple(
            CloseoutPin(item["path"], item["sha256"])
            for item in receipt["validation_refs"]
        ),
        receipt_id=str(receipt["receipt_id"]),
        schema_root=schema_root,
    )
    if receipt != rebuilt:
        raise GenericCloseoutValidationError("Generic Execution Receipt deterministic replay drift")
    return ValidatedGenericReceipt(root, path, hash_bytes(path.read_bytes()), receipt)


def build_execution_core_gate(
    no_skill: ValidatedGenericReceipt,
    direct_tool: ValidatedGenericReceipt,
    *,
    gate_id: str,
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    for expected, receipt in (("no-skill", no_skill), ("direct-tool", direct_tool)):
        if receipt.document.get("execution_kind") != expected or receipt.document.get("status") != "completed":
            raise GenericCloseoutValidationError(f"Core Gate lacks a completed {expected} receipt")
        if receipt.document.get("boundaries", {}).get("skill_assignment") != "absent":
            raise GenericCloseoutValidationError("Core Gate receipt contains Skill Assignment semantics")
    gate = {
        "schema_version": "0.1.0",
        "gate_id": gate_id,
        "scope": "m11-core",
        "status": "pass",
        "paths": [
            {
                "path_kind": kind,
                "receipt_ref": _file_ref(receipt.project_root, receipt.receipt_path),
            }
            for kind, receipt in (("no-skill", no_skill), ("direct-tool", direct_tool))
        ],
        "invariants": {
            "exact_replay": True,
            "skill_assignment_absent": True,
            "execution_only": True,
            "legacy_receipt_unchanged": True,
        },
        "boundaries": {
            "claim_effect": False,
            "human_decision": False,
            "fallback": False,
            "topic5_recovery": False,
        },
    }
    if SchemaCatalog(schema_root).validate("execution_core_gate", gate):
        raise GenericCloseoutValidationError("generated Execution Core Gate is schema-invalid")
    return gate


__all__ = [
    "CloseoutPin",
    "GenericCloseoutValidationError",
    "ValidatedGenericReceipt",
    "build_execution_core_gate",
    "build_generic_execution_receipt",
    "validate_generic_execution_receipt",
]
