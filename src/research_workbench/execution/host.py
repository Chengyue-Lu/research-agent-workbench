"""Thin, single-binding Execution Host for M11 Core."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.execution.execution_view import (
    PinnedExecutionInput,
    produce_resolved_execution_view,
)
from research_workbench.execution.runtime_bundle import ValidatedRuntimeBundle
from research_workbench.io import load_document_bytes
from research_workbench.validation.schemas import SchemaCatalog


_DIAGNOSTIC_CODE = re.compile(r"^[A-Z][A-Z0-9-]*$")


@dataclass(frozen=True, slots=True)
class ValidatedExecutionView:
    project_root: Path
    view_path: Path
    view_sha256: str
    document: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class FrozenExecutionRequest:
    view: Mapping[str, Any]
    bundle_documents: Mapping[Path, Mapping[str, Any]]


@dataclass(frozen=True, slots=True)
class ExecutionDriverResult:
    status: str
    actual_binding: Mapping[str, Any]
    turns: int = 0
    output_tokens: int = 0
    elapsed_seconds: float = 0.0
    provider_invocations: int = 0
    tool_invocations: int = 0
    external_write: bool = False
    data_egress_payloads: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    artifacts: tuple[Mapping[str, str], ...] = ()
    facts_complete: bool = True
    capture_gaps: tuple[str, ...] = ()
    failure_code: str | None = None
    re_resolution_required: bool = False


class FrozenExecutionDriver(Protocol):
    @property
    def binding(self) -> Mapping[str, Any]: ...

    def execute(self, request: FrozenExecutionRequest) -> ExecutionDriverResult: ...


class ExecutionHostValidationError(ValueError):
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


def _read_only(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _read_only(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_read_only(item) for item in value)
    return value


def _timestamp(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutionHostValidationError(f"{field} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise ExecutionHostValidationError(f"{field} must include a timezone")
    return parsed


def load_resolved_execution_view(
    view_path: str | Path,
    *,
    expected_sha256: str,
    bundle: ValidatedRuntimeBundle,
    schema_root: str | Path | None = None,
) -> ValidatedExecutionView:
    """Load, externally pin, and deterministically recompute one View."""

    root = bundle.project_root
    path = Path(view_path)
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ExecutionHostValidationError("Resolved Execution View escapes project root") from exc
    if not path.is_file():
        if path.is_dir():
            raise ExecutionHostValidationError("Resolved Execution View input must be one file")
        raise FileNotFoundError(path)
    content = path.read_bytes()
    digest = hash_bytes(content)
    if _normalized_hash(expected_sha256) != digest:
        raise ExecutionHostValidationError("Resolved Execution View external pin mismatch")
    try:
        document = load_document_bytes(path, content)
    except Exception as exc:
        raise ExecutionHostValidationError("Resolved Execution View is not parseable") from exc
    catalog = SchemaCatalog(schema_root)
    errors = catalog.validate("resolved_execution_view", document)
    if errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in errors)
        raise ExecutionHostValidationError("Resolved Execution View schema invalid: " + detail)
    if not isinstance(document, Mapping):
        raise ExecutionHostValidationError("Resolved Execution View must be an object")
    bundle_ref = document["runtime_bundle_ref"]
    if (
        bundle_ref["ref"] != f"{bundle.manifest['bundle_id']}@r{bundle.manifest['revision']}"
        or bundle_ref["path"] != bundle.manifest_path.relative_to(root).as_posix()
        or _normalized_hash(bundle_ref["sha256"]) != bundle.manifest_sha256
    ):
        raise ExecutionHostValidationError("Resolved Execution View Runtime Bundle lineage mismatch")
    pins = {
        "agent_profile": PinnedExecutionInput(
            document["agent_profile_ref"]["path"], document["agent_profile_ref"]["sha256"]
        ),
        "data_policy": PinnedExecutionInput(
            document["data_policy_ref"]["path"], document["data_policy_ref"]["sha256"]
        ),
        "host_policy": PinnedExecutionInput(
            document["host_policy_ref"]["path"], document["host_policy_ref"]["sha256"]
        ),
        "execution_binding": PinnedExecutionInput(
            document["execution_binding_ref"]["path"],
            document["execution_binding_ref"]["sha256"],
        ),
    }
    recomputed = produce_resolved_execution_view(
        bundle,
        **pins,
        execution_at=str(document["execution_at"]),
        view_id=str(document["view_id"]),
        revision=int(document["revision"]),
        expected_bundle_sha256=str(bundle_ref["sha256"]),
        schema_root=schema_root,
    )
    if document != recomputed:
        raise ExecutionHostValidationError("Resolved Execution View deterministic recomputation drift")
    frozen = _read_only(document)
    assert isinstance(frozen, Mapping)
    return ValidatedExecutionView(root, path, digest, frozen)


def _zero_facts(*, complete: bool, capture_gaps: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "complete": complete,
        "capture_gaps": list(capture_gaps),
        "turns": 0,
        "output_tokens": 0,
        "elapsed_seconds": 0.0,
        "provider_invocations": 0,
        "tool_invocations": 0,
        "external_write": False,
        "data_egress_payloads": [],
        "side_effects": [],
    }


def _view_ref(view: ValidatedExecutionView) -> dict[str, str]:
    document = view.document
    return {
        "ref": f"{document['view_id']}@r{document['revision']}",
        "path": view.view_path.relative_to(view.project_root).as_posix(),
        "sha256": view.view_sha256,
    }


def _base_report(
    view: ValidatedExecutionView,
    *,
    report_id: str,
    attempt_id: str,
    started_at: str,
    completed_at: str,
    status: str,
    actual_binding: Mapping[str, Any],
    facts: Mapping[str, Any],
    artifacts: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return {
        "schema_version": "0.1.0",
        "report_id": report_id,
        "attempt_id": attempt_id,
        "view_ref": _view_ref(view),
        "task_ref": _plain(view.document["task_ref"]),
        "started_at": started_at,
        "completed_at": completed_at,
        "status": status,
        "actual_binding": _plain(actual_binding),
        "actual_facts": _plain(facts),
        "artifacts": _plain(artifacts),
        "boundaries": {
            "actual_facts_only": True,
            "supply_selection": False,
            "rebinding": False,
            "automatic_fallback": False,
            "method_decision": False,
            "claim_effect": False,
            "human_decision": False,
            "topic5_recovery": False,
        },
    }


def _add_diagnostic(
    report: dict[str, Any],
    view: ValidatedExecutionView,
    *,
    code: str,
    category: str,
    re_resolution: bool,
) -> None:
    report["diagnostic"] = {
        "code": code,
        "category": category,
        "recommended_next": "re-resolution" if re_resolution else "stop",
    }
    if re_resolution:
        report["re_resolution_request"] = {
            "required": True,
            "reason_code": code,
            "snapshot_ref": _plain(view.document["snapshot_ref"]),
            "view_ref": _view_ref(view),
        }


def _validate_artifacts(
    root: Path,
    artifacts: Sequence[Mapping[str, str]],
    permissions: Mapping[str, Any],
) -> str | None:
    if artifacts and permissions.get("filesystem") in {"forbidden", "read-only"}:
        return "HOST-ARTIFACT-WRITE-FORBIDDEN"
    allowed_roots = [resolve_within_root(root, item) for item in permissions.get("allowed_roots", ())]
    for artifact in artifacts:
        path = resolve_within_root(root, artifact.get("path", ""))
        if path is None or not path.is_file():
            return "HOST-ARTIFACT-MISSING"
        if not any(
            allowed is not None
            and (path == allowed or allowed in path.parents)
            for allowed in allowed_roots
        ):
            return "HOST-ARTIFACT-WRITE-SCOPE"
        if _normalized_hash(artifact.get("sha256")) != hash_bytes(path.read_bytes()):
            return "HOST-ARTIFACT-HASH-MISMATCH"
    return None


def _required_outputs_satisfied(
    required: Sequence[Any], artifacts: Sequence[Mapping[str, str]]
) -> bool:
    counts: dict[str, int] = {}
    for artifact in artifacts:
        contract = artifact.get("contract")
        if isinstance(contract, str):
            counts[contract] = counts.get(contract, 0) + 1
    for requirement in required:
        if isinstance(requirement, str):
            contract, minimum = requirement, 1
        elif isinstance(requirement, Mapping):
            contract = requirement.get("contract")
            minimum = requirement.get("min_count", 1)
        else:
            return False
        if not isinstance(contract, str) or not isinstance(minimum, int) or counts.get(contract, 0) < minimum:
            return False
    return True


def _result_violation(view: Mapping[str, Any], result: ExecutionDriverResult) -> str | None:
    if result.status not in {"completed", "failed"}:
        return "HOST-DRIVER-STATUS-INVALID"
    if result.actual_binding != view["binding"]:
        return "HOST-ACTUAL-BINDING-DRIFT"
    if not result.facts_complete or result.capture_gaps:
        return "HOST-FACT-CAPTURE-GAP"
    constraints = view["effective_constraints"]
    permissions = constraints["permissions"]
    if result.external_write and not permissions["external_write"]:
        return "HOST-EXTERNAL-WRITE-VIOLATION"
    egress = constraints["data_egress"]
    actual_egress = set(result.data_egress_payloads)
    if egress["policy"] == "forbidden" and actual_egress:
        return "HOST-DATA-EGRESS-VIOLATION"
    if egress["policy"] == "allowlisted-only" and not actual_egress.issubset(
        set(egress["allowed_payloads"])
    ):
        return "HOST-DATA-EGRESS-VIOLATION"
    if actual_egress.intersection(egress["forbidden_payloads"]):
        return "HOST-DATA-EGRESS-VIOLATION"
    effects = constraints["side_effects"]
    actual_effects = set(result.side_effects)
    if effects["policy"] == "none" and actual_effects:
        return "HOST-SIDE-EFFECT-VIOLATION"
    if effects["policy"] == "allowlisted-only" and not actual_effects.issubset(
        set(effects["allowed_effects"])
    ):
        return "HOST-SIDE-EFFECT-VIOLATION"
    budget = constraints["budget"]
    actual_budget = {
        "max_turns": result.turns,
        "max_output_tokens": result.output_tokens,
        "max_seconds": result.elapsed_seconds,
    }
    if any(key in budget and value > budget[key] for key, value in actual_budget.items()):
        return "HOST-BUDGET-VIOLATION"
    return None


def execute_frozen_view(
    view: ValidatedExecutionView,
    bundle: ValidatedRuntimeBundle,
    driver: FrozenExecutionDriver,
    *,
    report_id: str,
    attempt_id: str,
    started_at: str,
    completed_at: str,
    schema_root: str | Path | None = None,
) -> dict[str, Any]:
    """Execute exactly once through one pre-bound driver and report facts."""

    if _timestamp(completed_at, "completed_at") < _timestamp(started_at, "started_at"):
        raise ExecutionHostValidationError("completed_at precedes started_at")
    declared_binding = _plain(driver.binding)
    expected_binding = _plain(view.document["binding"])
    if declared_binding != expected_binding:
        report = _base_report(
            view,
            report_id=report_id,
            attempt_id=attempt_id,
            started_at=started_at,
            completed_at=completed_at,
            status="blocked",
            actual_binding=declared_binding,
            facts=_zero_facts(complete=True),
            artifacts=(),
        )
        _add_diagnostic(
            report,
            view,
            code="HOST-BINDING-MISMATCH",
            category="preflight",
            re_resolution=True,
        )
    else:
        request = FrozenExecutionRequest(view.document, bundle.documents)
        try:
            result = driver.execute(request)
        except Exception:
            report = _base_report(
                view,
                report_id=report_id,
                attempt_id=attempt_id,
                started_at=started_at,
                completed_at=completed_at,
                status="failed",
                actual_binding=declared_binding,
                facts=_zero_facts(complete=False, capture_gaps=("driver-exception",)),
                artifacts=(),
            )
            _add_diagnostic(
                report,
                view,
                code="HOST-DRIVER-EXCEPTION",
                category="driver",
                re_resolution=False,
            )
        else:
            facts = {
                "complete": result.facts_complete,
                "capture_gaps": list(result.capture_gaps),
                "turns": result.turns,
                "output_tokens": result.output_tokens,
                "elapsed_seconds": result.elapsed_seconds,
                "provider_invocations": result.provider_invocations,
                "tool_invocations": result.tool_invocations,
                "external_write": result.external_write,
                "data_egress_payloads": list(result.data_egress_payloads),
                "side_effects": list(result.side_effects),
            }
            violation = _result_violation(view.document, result)
            if violation is None:
                violation = _validate_artifacts(
                    view.project_root,
                    result.artifacts,
                    view.document["effective_constraints"]["permissions"],
                )
            if (
                violation is None
                and result.status == "completed"
                and not _required_outputs_satisfied(view.document["required_outputs"], result.artifacts)
            ):
                violation = "HOST-REQUIRED-OUTPUT-MISSING"
            status = "completed" if result.status == "completed" and violation is None else "failed"
            report = _base_report(
                view,
                report_id=report_id,
                attempt_id=attempt_id,
                started_at=started_at,
                completed_at=completed_at,
                status=status,
                actual_binding=result.actual_binding,
                facts=facts,
                artifacts=result.artifacts,
            )
            if status != "completed":
                proposed_code = violation or result.failure_code or "HOST-DRIVER-FAILED"
                code = proposed_code if _DIAGNOSTIC_CODE.fullmatch(proposed_code) else "HOST-DRIVER-FAILED"
                re_resolution = result.re_resolution_required or code in {
                    "HOST-ACTUAL-BINDING-DRIFT",
                    "HOST-BINDING-MISMATCH",
                }
                _add_diagnostic(
                    report,
                    view,
                    code=code,
                    category="boundary" if violation else "driver",
                    re_resolution=re_resolution,
                )
    errors = SchemaCatalog(schema_root).validate("execution_host_report", report)
    if errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in errors)
        raise ExecutionHostValidationError("Execution Host report schema invalid: " + detail)
    return report


__all__ = [
    "ExecutionDriverResult",
    "ExecutionHostValidationError",
    "FrozenExecutionDriver",
    "FrozenExecutionRequest",
    "ValidatedExecutionView",
    "execute_frozen_view",
    "load_resolved_execution_view",
]
