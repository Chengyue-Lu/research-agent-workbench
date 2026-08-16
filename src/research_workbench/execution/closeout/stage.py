"""Stage-tree persistence: execution intent, stage plans, and cleanup."""

from __future__ import annotations

import hashlib
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts import is_path_safe_identifier
from research_workbench.io import load_document, write_bytes_exclusive, write_yaml_exclusive
from research_workbench.tasks import FileReference, TaskPacket

from .errors import CloseoutError
from .paths import _attempt_intent_path, _stage_locations, _stage_path
from .verify import _verify_staged_hash

def staged_closeout_exists(*, root: str | Path, attempt_id: str) -> bool:
    """Return whether a path-safe Attempt has any fail-closed closeout stage."""

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    stage_parent, _stage_root = _stage_locations(project_root, attempt_id, create=False)
    return stage_parent.exists()


def record_api_attempt_intent(
    *,
    root: str | Path,
    attempt_id: str,
    task_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    model_assignment_id: str,
    model_assignment_ref: FileReference,
    execution_contract: str,
    started_at: str,
    previous_main_state_ref: str | None,
) -> bool:
    """Exclusively record execution intent before the first Provider call.

    An intent without a validated closeout plan is deliberately indeterminate:
    a later invocation must never guess that Provider/tool execution was absent.
    """

    project_root = Path(root).resolve()
    if not is_path_safe_identifier(attempt_id):
        raise CloseoutError("CLOSEOUT-ATTEMPT-ID", "attempt_id is not path-safe")
    if not is_path_safe_identifier(task_id):
        raise CloseoutError("CLOSEOUT-TASK-ID", "task_id must be one path-safe segment")
    intent_path = _attempt_intent_path(project_root, attempt_id, create=True)
    return write_yaml_exclusive(
        intent_path,
        {
            "version": 4,
            "attempt_id": attempt_id,
            "task_id": task_id,
            "protocol_ref": protocol_ref,
            "task_ref": task_ref,
            "profile_ref": profile_ref,
            "assignment_ref": assignment_ref,
            "provider_adapter_id": provider_adapter_id,
            "requested_model": requested_model,
            "model_assignment_id": model_assignment_id,
            "model_assignment_ref": {
                "path": model_assignment_ref.path,
                "sha256": model_assignment_ref.sha256,
                **(
                    {"revision": model_assignment_ref.revision}
                    if model_assignment_ref.revision is not None
                    else {}
                ),
            },
            "execution_contract": execution_contract,
            "started_at": started_at,
            "previous_main_state_ref": previous_main_state_ref,
        },
    )


def fail_if_api_attempt_intent_exists(
    *,
    root: str | Path,
    attempt_id: str,
    task_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    model_assignment_id: str,
    model_assignment_ref: FileReference,
    execution_contract: str,
    previous_main_state_ref: str | None,
) -> None:
    """Reject an uncommitted retry after execution may already have started."""

    _raise_if_execution_intent_is_incomplete(
        Path(root).resolve(),
        attempt_id=attempt_id,
        task_id=task_id,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        provider_adapter_id=provider_adapter_id,
        requested_model=requested_model,
        model_assignment_id=model_assignment_id,
        model_assignment_ref=model_assignment_ref,
        execution_contract=execution_contract,
        previous_main_state_ref=previous_main_state_ref,
    )


def _stage_task_inputs(
    *,
    project_root: Path,
    stage_root: Path,
    task: TaskPacket,
    frozen_input_payloads: Mapping[str, bytes] | None,
    allow_stale: bool,
) -> None:
    expected_paths = {reference.path for reference in task.input_refs}
    supplied = dict(frozen_input_payloads or {})
    if frozen_input_payloads is not None and set(supplied) != expected_paths:
        raise CloseoutError(
            "CLOSEOUT-INPUT-SNAPSHOT",
            "frozen Task input payloads do not exactly match Task input_refs",
        )
    for reference in task.input_refs:
        if reference.path in supplied:
            payload = supplied[reference.path]
            if not isinstance(payload, bytes):
                raise CloseoutError(
                    "CLOSEOUT-INPUT-SNAPSHOT", f"frozen input is not bytes: {reference.path}"
                )
        else:
            resolved = resolve_within_root(project_root, reference.path)
            if resolved is None or not resolved.is_file():
                if allow_stale:
                    continue
                raise CloseoutError("REF-MISSING", f"Task input does not exist: {reference.path}")
            payload = resolved.read_bytes()
        expected_hash = reference.sha256.removeprefix("sha256:").lower()
        if hashlib.sha256(payload).hexdigest() != expected_hash and not allow_stale:
            raise CloseoutError("TASK-STALE-INPUT", f"Task input hash differs: {reference.path}")
        write_bytes_exclusive(_stage_path(stage_root, reference.path), payload)


def _write_stage_plan(
    *,
    stage_parent: Path,
    stage_root: Path,
    attempt_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    model_assignment_id: str,
    model_assignment_ref: FileReference | None,
    execution_contract: str,
    attempt_ref: str,
    main_state_ref: str,
    publication_refs: tuple[str, ...],
    execution_material_status: str,
    previous_main_state_ref: str | None,
) -> dict[str, str]:
    attempt_path = _stage_path(stage_root, attempt_ref)
    main_state_path = _stage_path(stage_root, main_state_ref)
    publication_hashes = {
        relative: hash_file(_stage_path(stage_root, relative)) for relative in publication_refs
    }
    write_yaml_exclusive(
        stage_parent / "plan.yaml",
        {
            "version": 4,
            "attempt_id": attempt_id,
            "protocol_ref": protocol_ref,
            "task_ref": task_ref,
            "profile_ref": profile_ref,
            "assignment_ref": assignment_ref,
            "provider_adapter_id": provider_adapter_id,
            "requested_model": requested_model,
            "model_assignment_id": model_assignment_id,
            "model_assignment_ref": (
                {
                    "path": model_assignment_ref.path,
                    "sha256": model_assignment_ref.sha256,
                    **(
                        {"revision": model_assignment_ref.revision}
                        if model_assignment_ref.revision is not None
                        else {}
                    ),
                }
                if model_assignment_ref is not None
                else None
            ),
            "execution_contract": execution_contract,
            "attempt_ref": attempt_ref,
            "attempt_sha256": hash_file(attempt_path),
            "main_state_ref": main_state_ref,
            "main_state_sha256": hash_file(main_state_path),
            "execution_material_status": execution_material_status,
            "previous_main_state_ref": previous_main_state_ref,
            "publication_hashes": publication_hashes,
        },
    )
    return publication_hashes


def _load_stage_plan(stage_parent: Path, stage_root: Path, attempt_id: str) -> dict[str, Any]:
    plan_path = stage_parent / "plan.yaml"
    if not plan_path.is_file():
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "staged closeout has no validated publication plan",
        )
    value = load_document(plan_path)
    required_strings = (
        "attempt_id",
        "protocol_ref",
        "task_ref",
        "profile_ref",
        "assignment_ref",
        "provider_adapter_id",
        "requested_model",
        "model_assignment_id",
        "execution_contract",
        "attempt_ref",
        "attempt_sha256",
        "main_state_ref",
        "main_state_sha256",
        "execution_material_status",
    )
    if not isinstance(value, Mapping) or value.get("version") != 4:
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "stage plan version is invalid")
    if any(not isinstance(value.get(key), str) or not value[key] for key in required_strings):
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "stage plan fields are invalid")
    plan: dict[str, Any] = {key: str(value[key]) for key in required_strings}
    if "model_assignment_ref" not in value:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage Model Assignment reference is missing",
        )
    raw_model_assignment_ref = value.get("model_assignment_ref")
    if raw_model_assignment_ref is None:
        plan["model_assignment_ref"] = None
    elif isinstance(raw_model_assignment_ref, Mapping):
        try:
            model_assignment_ref = FileReference.from_mapping(raw_model_assignment_ref)
        except Exception as exc:
            raise CloseoutError(
                "CLOSEOUT-STAGE-INCOMPLETE",
                "stage Model Assignment reference is invalid",
            ) from exc
        _verify_staged_hash(
            stage_root,
            model_assignment_ref.path,
            model_assignment_ref.sha256,
        )
        plan["model_assignment_ref"] = model_assignment_ref
    else:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage Model Assignment reference is invalid",
        )
    if "previous_main_state_ref" not in value:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage previous Main State identity is missing",
        )
    previous_main_state_ref = value.get("previous_main_state_ref")
    if previous_main_state_ref is not None and (
        not isinstance(previous_main_state_ref, str) or not previous_main_state_ref
    ):
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE",
            "stage previous Main State reference is invalid",
        )
    plan["previous_main_state_ref"] = previous_main_state_ref
    if plan["execution_material_status"] not in {"locked", "unavailable"}:
        raise CloseoutError(
            "CLOSEOUT-STAGE-INCOMPLETE", "stage execution material status is invalid"
        )
    raw_hashes = value.get("publication_hashes")
    if not isinstance(raw_hashes, Mapping) or not raw_hashes:
        raise CloseoutError("CLOSEOUT-STAGE-INCOMPLETE", "stage publication hashes are missing")
    publication_hashes: dict[str, str] = {}
    for ref, digest in raw_hashes.items():
        if not isinstance(ref, str) or not ref or not isinstance(digest, str) or not digest:
            raise CloseoutError(
                "CLOSEOUT-STAGE-INCOMPLETE", "stage publication hashes are invalid"
            )
        publication_hashes[ref] = digest.removeprefix("sha256:").lower()
    plan["publication_hashes"] = publication_hashes
    if plan["attempt_id"] != attempt_id:
        raise CloseoutError("CLOSEOUT-STAGE-IDENTITY", "stage plan Attempt ID differs")
    for ref_key, hash_key in (
        ("attempt_ref", "attempt_sha256"),
        ("main_state_ref", "main_state_sha256"),
    ):
        path = _stage_path(stage_root, plan[ref_key])
        if not path.is_file() or hash_file(path) != plan[hash_key].removeprefix("sha256:").lower():
            raise CloseoutError("CLOSEOUT-STAGE-DRIFT", f"stage plan hash differs: {ref_key}")
    for relative, digest in publication_hashes.items():
        _verify_staged_hash(stage_root, relative, digest)
    return plan


def _raise_if_execution_intent_is_incomplete(
    project_root: Path,
    *,
    attempt_id: str,
    task_id: str,
    protocol_ref: str,
    task_ref: str,
    profile_ref: str,
    assignment_ref: str,
    provider_adapter_id: str,
    requested_model: str,
    model_assignment_id: str,
    model_assignment_ref: FileReference | None = None,
    execution_contract: str,
    previous_main_state_ref: str | None,
) -> None:
    intent_path = _attempt_intent_path(project_root, attempt_id, create=False)
    if not intent_path.is_file():
        return
    value = load_document(intent_path)
    expected: dict[str, Any] = {
        "version": 4,
        "attempt_id": attempt_id,
        "task_id": task_id,
        "protocol_ref": protocol_ref,
        "task_ref": task_ref,
        "profile_ref": profile_ref,
        "assignment_ref": assignment_ref,
        "provider_adapter_id": provider_adapter_id,
        "requested_model": requested_model,
        "model_assignment_id": model_assignment_id,
        "execution_contract": execution_contract,
        "previous_main_state_ref": previous_main_state_ref,
    }
    if model_assignment_ref is not None:
        expected["model_assignment_ref"] = {
            "path": model_assignment_ref.path,
            "sha256": model_assignment_ref.sha256,
            **(
                {"revision": model_assignment_ref.revision}
                if model_assignment_ref.revision is not None
                else {}
            ),
        }
    if not isinstance(value, Mapping) or any(value.get(key) != item for key, item in expected.items()):
        raise CloseoutError(
            "CLOSEOUT-STAGE-IDENTITY",
            "execution intent belongs to different Task or runtime contracts",
        )
    raise CloseoutError(
        "API-ATTEMPT-RESULT-UNKNOWN",
        "execution intent exists without a validated closeout plan; automatic replay is forbidden",
    )


def _remove_stage(project_root: Path, stage_parent: Path) -> None:
    resolved_project = project_root.resolve()
    resolved_stage = stage_parent.resolve()
    expected_parent = (resolved_project / ".rwb" / "closeout").resolve()
    try:
        resolved_stage.relative_to(expected_parent)
    except ValueError as exc:
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "refusing to remove an unexpected stage path") from exc
    if resolved_stage == expected_parent:
        raise CloseoutError("CLOSEOUT-STAGE-PATH", "refusing to remove the closeout root")
    shutil.rmtree(resolved_stage, ignore_errors=False)
