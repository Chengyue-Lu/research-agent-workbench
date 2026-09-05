"""Deterministic validation pipeline runner for fail-closed artifact promotion (M4-002).

Promotion eligibility is a validity fact established at promotion time:
``check_promotion`` deterministically re-executes the accepted, hash-pinned
runner/checker over the exact pinned subject bytes and requires byte-exact
reproduction of the recorded PASS report and run transcript
(rebuild-and-compare; no signing keys).  The report / execution / host-receipt
triple produced here is provenance metadata: it durably records one claimed
run -- its pinned inputs, transcript, operator, and timestamps.  Those
self-declared fields are not independently verifiable and never confer
eligibility on their own.  A hand-written triple whose report and transcript
are byte-exactly what the pinned pipeline would produce can pass promotion
validation only because re-execution independently confirms the underlying
claim; any false claim (bytes that do not actually pass) is refuted by the
same re-execution.

The registry's ``host`` pin identifies the claimed producer implementation as
metadata; the actual producer is always this installed ``rwb`` package, which
is part of the promotion TCB.  The host executes nothing beyond the
runner/checker exact-pinned by the frozen Task Packet, the authority registry,
and the accepted policy.  It never accepts a Claim, records a Human Decision,
publishes a deliverable, or judges scientific correctness.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import yaml

from research_workbench.artifacts.integrity import (
    check_file_reference,
    hash_bytes,
    hash_file,
    resolve_within_root,
)
from research_workbench.artifacts.promotion import (
    TASK_AUTHORITY_ZONE,
    VALIDATION_AUTHORITY_REGISTRY_PATH,
    VALIDATION_EXECUTION_ZONE,
    PromotionRecord,
    _component_binding,
    _file_reference,
    _normalized_path,
    _parse_referenced_document,
    _parts,
    _reference_key,
    _reference_keys,
    _reference_mapping,
    _reference_risks,
    _risk,
    _schema_catalog,
    _strictly_within,
    _timestamp,
    _trusted_validation_source,
)
from research_workbench.contracts.common import ContractError
from research_workbench.contracts.risks import ContractRisk
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference

VALIDATION_RUNNER_CONTRACT = "rwb-validation-runner-contract/1"
VALIDATION_RUN_TIMEOUT_SECONDS = 90

UNPROVEN_RISK_CODE = "VALIDATION-EXECUTION-UNPROVEN"


@dataclass(frozen=True, slots=True)
class ValidationRunResult:
    outcome: str
    report_path: str
    execution_path: str
    receipt_path: str


@dataclass(frozen=True, slots=True)
class _RunnerOutcome:
    outcome: str
    report_bytes: bytes
    report_produced_by: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json_bytes(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _canonical_yaml_bytes(data: Mapping[str, Any]) -> bytes:
    return yaml.safe_dump(data, sort_keys=True, allow_unicode=True).encode("utf-8")


_SCRUBBED_ENV_ALLOWLIST = frozenset(
    {
        # Windows process essentials
        "APPDATA", "COMSPEC", "HOMEDRIVE", "HOMEPATH", "LOCALAPPDATA",
        "NUMBER_OF_PROCESSORS", "OS", "PATH", "PATHEXT", "PROGRAMDATA",
        "SYSTEMDRIVE", "SYSTEMROOT", "TEMP", "TMP", "USERPROFILE",
        # POSIX essentials
        "HOME", "LANG", "LC_ALL", "TMPDIR", "USER",
    }
)


def _scrubbed_environment() -> dict[str, str]:
    """Minimal environment for the pinned runner subprocess.

    Only OS-essential variables are inherited (matched case-insensitively so
    Windows case variants collapse); session- or agent-injected variables,
    credentials, and interpreter-poisoning knobs (``PYTHONPATH``,
    ``PYTHONHOME``, ``PYTHONSTARTUP``, ...) are dropped.  Hash randomisation,
    user site-packages, bytecode writes, and timezone are pinned so the run is
    reproducible and isolated from the caller's shell.
    """

    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.upper() in _SCRUBBED_ENV_ALLOWLIST:
            env[key] = value
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONNOUSERSITE"] = "1"
    env["TZ"] = "UTC"
    return env


def _path_token(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(field, "must be a non-empty string")
    token = value.strip()
    if "\\" in token or PurePosixPath(token).parts != (token,) or token in {".", ".."}:
        raise ContractError(field, f"must be a single safe path segment: {value}")
    return token


def _load_file_bound_document(
    root: Path,
    document_path: str | Path,
    kind: str,
    label: str,
) -> tuple[Mapping[str, Any], FileReference]:
    if isinstance(document_path, Mapping):
        raise ContractError(label, f"{label} must be file-bound, not an in-memory mapping")
    raw_path = Path(document_path)
    lexical = raw_path if raw_path.is_absolute() else root / raw_path
    lexical = Path(os.path.abspath(lexical))
    resolved = lexical.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as exc:
        raise ContractError(label, f"{label} is outside the project root") from exc
    if os.path.normcase(str(lexical)) != os.path.normcase(str(resolved)):
        raise ContractError(label, f"{label} traverses a symbolic-link boundary")
    if not resolved.is_file():
        raise ContractError(label, f"{label} is missing: {relative}")
    content = resolved.read_bytes()
    try:
        document = load_document_bytes(resolved, content)
    except Exception as exc:
        raise ContractError(label, f"{label} cannot be parsed: {exc}") from exc
    if not isinstance(document, Mapping):
        raise ContractError(label, f"{label} must be an object")
    errors = _schema_catalog().validate(kind, document)
    if errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in errors[:4])
        raise ContractError(label, f"{label} is schema-invalid: {detail}")
    return document, FileReference(relative, hash_bytes(content))


def _exclusive_target(root: Path, relative: str) -> Path:
    target = resolve_within_root(root, relative)
    lexical = root.joinpath(*_parts(relative))
    if target is None or target != lexical:
        raise ContractError("validation run", f"validation fact target escapes project root: {relative}")
    if target.exists():
        raise ContractError("validation run", f"validation fact already exists: {relative}")
    return target


def _write_exclusive(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def _best_effort_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def _component_mapping(kind: str, binding: tuple[str, str, FileReference]) -> dict[str, Any]:
    identity_field = {"checker": "checker_id", "runner": "runner_id", "host": "host_id"}[kind]
    return {
        identity_field: binding[0],
        "version": binding[1],
        "source_ref": _reference_mapping(binding[2]),
    }


def _run_inputs_sha256(
    *,
    execution_id: str,
    report_id: str,
    task_ref: FileReference,
    registry_ref: FileReference,
    policy_ref: FileReference,
    checker: tuple[str, str, FileReference],
    runner: tuple[str, str, FileReference],
    host: tuple[str, str, FileReference],
    subjects: Sequence[FileReference],
) -> str:
    closure = {
        "contract": VALIDATION_RUNNER_CONTRACT,
        "execution_id": execution_id,
        "report_id": report_id,
        "task_ref": _reference_mapping(task_ref),
        "authority_registry_ref": _reference_mapping(registry_ref),
        "policy_ref": _reference_mapping(policy_ref),
        "checker": _component_mapping("checker", checker),
        "runner": _component_mapping("runner", runner),
        "host": _component_mapping("host", host),
        "subjects": [
            _reference_mapping(item) for item in sorted(subjects, key=lambda ref: ref.path)
        ],
    }
    return hash_bytes(_canonical_json_bytes(closure))


def _evaluate_report(
    report_bytes: bytes,
    *,
    report_id: str,
    checker: tuple[str, str, FileReference],
    subjects: Sequence[FileReference],
) -> str | None:
    """Return ``None`` only when the bytes are the exact pinned PASS report."""

    try:
        document = yaml.safe_load(report_bytes.decode("utf-8"))
    except Exception:
        return "validation report cannot be parsed"
    if not isinstance(document, Mapping):
        return "validation report is not an object"
    errors = _schema_catalog().validate("deterministic_check_report", document)
    if errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in errors[:2])
        return f"validation report is schema-invalid: {detail}"
    if document.get("report_id") != report_id:
        return "validation report id differs from the run"
    if _component_binding(document["checker"], "checker") != checker:
        return "validation report checker differs from the accepted pin"
    try:
        report_keys = _reference_keys(document.get("subject_refs"), "subject_refs")
    except ContractError:
        return "validation report subjects are malformed"
    subject_keys = {_reference_key(item) for item in subjects}
    if set(report_keys) != subject_keys or len(report_keys) != len(subject_keys):
        return "validation report subjects differ from the accepted pins"
    if document.get("status") != "pass":
        return "checker reported fail"
    return None


def _synthesize_failure_report(
    *,
    report_id: str,
    checker: tuple[str, str, FileReference],
    subjects: Sequence[FileReference],
    detail: str,
) -> bytes:
    document = {
        "schema_version": "0.1.0",
        "report_id": report_id,
        "checker": _component_mapping("checker", checker),
        "subject_refs": [_reference_mapping(item) for item in subjects],
        "status": "fail",
        "checks": [
            {
                "code": "VALIDATION-RUNNER-EXECUTION",
                "status": "fail",
                "detail": detail,
            }
        ],
        "scope": "Trusted validation host runner execution.",
        "limitations": [
            "Host-synthesized failure fact: the pinned runner did not produce a PASS report.",
            "Does not establish scientific correctness.",
        ],
    }
    return _canonical_yaml_bytes(document)


def _execute_runner(
    root: Path,
    *,
    report_id: str,
    checker: tuple[str, str, FileReference],
    runner: tuple[str, str, FileReference],
    subjects: Sequence[FileReference],
) -> _RunnerOutcome:
    checker_path = resolve_within_root(root, checker[2].path)
    runner_path = resolve_within_root(root, runner[2].path)
    if checker_path is None or runner_path is None:
        raise ContractError("validation run", "pinned runner/checker source escapes project root")
    with tempfile.TemporaryDirectory(prefix="rwb-validation-") as temporary:
        temp_root = Path(temporary).resolve()
        report_out = temp_root / "report.yaml"
        manifest = {
            "contract": VALIDATION_RUNNER_CONTRACT,
            "report_id": report_id,
            "checker": {
                "checker_id": checker[0],
                "version": checker[1],
                "source_ref": _reference_mapping(checker[2]),
                "source_path": str(checker_path),
            },
            "subjects": [
                {
                    "path": str(resolve_within_root(root, item.path)),
                    "relative_path": item.path,
                    "sha256": item.sha256,
                }
                for item in subjects
            ],
            "report_out": str(report_out),
        }
        manifest_path = temp_root / "manifest.json"
        manifest_path.write_bytes(_canonical_json_bytes(manifest))
        environment = _scrubbed_environment()
        timed_out = False
        try:
            completed = subprocess.run(
                [sys.executable, str(runner_path), str(manifest_path)],
                cwd=temp_root,
                env=environment,
                capture_output=True,
                timeout=VALIDATION_RUN_TIMEOUT_SECONDS,
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout
            stderr = completed.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            exit_code = -1
            stdout = exc.stdout or b""
            stderr = exc.stderr or b""
        report_bytes = report_out.read_bytes() if report_out.is_file() else None
    if timed_out:
        failure = f"validation runner exceeded {VALIDATION_RUN_TIMEOUT_SECONDS}s"
    elif report_bytes is None:
        failure = f"validation runner produced no report (exit code {exit_code})"
    else:
        failure = _evaluate_report(
            report_bytes, report_id=report_id, checker=checker, subjects=subjects
        )
        if failure is None and exit_code != 0:
            failure = f"validation runner reported pass but exited with code {exit_code}"
    if failure is None:
        assert report_bytes is not None
        return _RunnerOutcome(
            "pass", report_bytes, "runner", exit_code, hash_bytes(stdout), hash_bytes(stderr)
        )
    if report_bytes is None:
        report_bytes = _synthesize_failure_report(
            report_id=report_id, checker=checker, subjects=subjects, detail=failure
        )
        produced_by = "host-failure-synthesis"
    else:
        produced_by = "runner"
    return _RunnerOutcome(
        "fail", report_bytes, produced_by, exit_code, hash_bytes(stdout), hash_bytes(stderr)
    )


def run_validation_execution(
    root: str | Path,
    task_path: str | Path,
    *,
    attempt_id: str,
    subjects: Sequence[str],
    operator: str,
    report_path: str | None = None,
) -> ValidationRunResult:
    """Actually run the accepted validation pipeline and persist its record.

    The persisted report/execution/host-receipt triple is provenance metadata
    describing one claimed run; it never confers promotion eligibility by
    itself.  Eligibility is established later, at promotion time, by
    deterministic re-execution of the pinned pipeline (``reexecute_validation``).

    Authority or boundary faults raise ``ContractError`` before anything is
    executed or written.  A runner/checker failure is itself a durable fact:
    the host then persists an ``outcome=fail`` execution, receipt, and report
    (host-synthesized when the runner produced none).
    """

    root_path = Path(root).resolve()
    task, task_ref = _load_file_bound_document(root_path, task_path, "task_packet", "Task Packet")
    task_id = _path_token(task.get("task_id"), "task_id")
    attempt = _path_token(attempt_id, "attempt_id")
    revision = task.get("revision")
    if not isinstance(revision, int) or revision < 1:
        raise ContractError("task.revision", "must be a positive integer")
    canonical_task = f"{TASK_AUTHORITY_ZONE}/{task_id}/r{revision}/TASK.yaml"
    if task_ref.path != canonical_task:
        raise ContractError(
            "task", f"Task Packet must be revision-pinned at its canonical path: {canonical_task}"
        )
    task_ref = FileReference(task_ref.path, task_ref.sha256, revision)
    if not isinstance(operator, str) or not operator.strip():
        raise ContractError("operator", "must name the accountable operator")
    operator = operator.strip()

    workspace = f"work/{task_id}/{attempt}"
    write_scope = task.get("write_scope")
    if not isinstance(write_scope, list) or workspace not in write_scope:
        raise ContractError(
            "task.write_scope", "Task Packet does not bind the exact validation workspace"
        )
    workspace_path = resolve_within_root(root_path, workspace)
    if (
        workspace_path is None
        or workspace_path != root_path.joinpath(*_parts(workspace))
        or not workspace_path.is_dir()
    ):
        raise ContractError("workspace", f"validation workspace is missing or escapes root: {workspace}")

    if not subjects:
        raise ContractError("subjects", "at least one validation subject is required")
    subject_refs: list[FileReference] = []
    for raw in subjects:
        normalized = _normalized_path(raw, "subjects")
        if not _strictly_within(normalized, workspace):
            raise ContractError(
                "subjects", f"subject is outside the exact validation workspace: {normalized}"
            )
        resolved = resolve_within_root(root_path, normalized)
        lexical = root_path.joinpath(*_parts(normalized))
        if resolved is None or resolved != lexical or not resolved.is_file():
            raise ContractError("subjects", f"subject is missing or escapes root: {normalized}")
        subject_refs.append(FileReference(normalized, hash_file(resolved)))
    if len({item.path for item in subject_refs}) != len(subject_refs):
        raise ContractError("subjects", "duplicate validation subject path")
    subject_refs.sort(key=lambda item: item.path)

    registry_resolved = resolve_within_root(root_path, VALIDATION_AUTHORITY_REGISTRY_PATH)
    registry_lexical = root_path.joinpath(*_parts(VALIDATION_AUTHORITY_REGISTRY_PATH))
    if (
        registry_resolved is None
        or registry_resolved != registry_lexical
        or not registry_resolved.is_file()
    ):
        raise ContractError(
            "validation authority registry",
            f"missing or escapes root: {VALIDATION_AUTHORITY_REGISTRY_PATH}",
        )
    registry_ref = FileReference(VALIDATION_AUTHORITY_REGISTRY_PATH, hash_file(registry_resolved))
    registry, registry_risks = _parse_referenced_document(
        root_path,
        registry_ref,
        "promotion_validation_authority_registry",
        "accepted validation authority registry",
    )
    if registry is None:
        raise ContractError(
            "validation authority registry", "; ".join(item.message for item in registry_risks)
        )
    input_keys = set(_reference_keys(task.get("input_refs"), "task.input_refs"))
    if _reference_key(registry_ref) not in input_keys:
        raise ContractError(
            "task.input_refs", "Task Packet does not exact-pin the authority registry"
        )
    matching = [
        entry
        for entry in registry.get("accepted_policies", [])
        if isinstance(entry, Mapping)
        and entry.get("task_id") == task_id
        and entry.get("task_revision") == revision
    ]
    if len(matching) != 1:
        raise ContractError(
            "authority registry",
            "must contain exactly one accepted policy for the Task revision",
        )
    registry_entry = matching[0]
    policy_ref = _file_reference(registry_entry["policy_ref"], "policy_ref")
    if _reference_key(policy_ref) not in input_keys:
        raise ContractError("task.input_refs", "Task Packet does not exact-pin the accepted policy")
    policy, policy_risks = _parse_referenced_document(
        root_path, policy_ref, "promotion_validation_policy", "accepted validation policy"
    )
    if policy is None:
        raise ContractError(
            "accepted validation policy", "; ".join(item.message for item in policy_risks)
        )
    if policy.get("task_id") != task_id:
        raise ContractError("accepted validation policy", "policy is for another Task")

    checker = _component_binding(registry_entry["checker"], "checker")
    runner = _component_binding(registry_entry["runner"], "runner")
    host = _component_binding(registry_entry["host"], "host")
    if _component_binding(policy["checker"], "checker") != checker:
        raise ContractError("accepted validation policy", "policy checker differs from registry")
    if _component_binding(policy["runner"], "runner") != runner:
        raise ContractError("accepted validation policy", "policy runner differs from registry")
    for binding, label in (
        (checker, "validation checker"),
        (runner, "validation runner"),
        (host, "validation host"),
    ):
        component_risks = _reference_risks(root_path, binding[2], label)
        if component_risks:
            raise ContractError(label, "; ".join(item.message for item in component_risks))
        if not _trusted_validation_source(binding[2].path):
            raise ContractError(
                label, "must be exact-pinned from a repository-governed source zone"
            )
    accepted_at = _timestamp(str(registry_entry["accepted_at"]), "accepted_at")

    report_relative = (
        _normalized_path(report_path, "report_path")
        if report_path is not None
        else f"{workspace}/checks/validation.yaml"
    )
    if not _strictly_within(report_relative, workspace):
        raise ContractError(
            "report_path", "validation report must live inside the exact validation workspace"
        )
    execution_relative = f"{VALIDATION_EXECUTION_ZONE}/{task_id}/{attempt}/execution.yaml"
    receipt_relative = f"{VALIDATION_EXECUTION_ZONE}/{task_id}/{attempt}/receipt.json"
    report_target = _exclusive_target(root_path, report_relative)
    execution_target = _exclusive_target(root_path, execution_relative)
    receipt_target = _exclusive_target(root_path, receipt_relative)

    execution_id = f"{task_id}-VALIDATION-EXEC-{attempt}"
    report_id = f"{task_id}-VALIDATION-{attempt}"
    started_at = _now()
    if accepted_at > _timestamp(started_at, "started_at"):
        raise ContractError(
            "authority registry", "validation authority was not accepted before execution started"
        )
    outcome = _execute_runner(
        root_path,
        report_id=report_id,
        checker=checker,
        runner=runner,
        subjects=subject_refs,
    )
    finished_at = _now()

    report_bytes = outcome.report_bytes
    report_ref = FileReference(report_relative, hash_bytes(report_bytes))
    run_inputs = _run_inputs_sha256(
        execution_id=execution_id,
        report_id=report_id,
        task_ref=task_ref,
        registry_ref=registry_ref,
        policy_ref=policy_ref,
        checker=checker,
        runner=runner,
        host=host,
        subjects=subject_refs,
    )
    receipt = {
        "schema_version": "0.1.0",
        "receipt_id": f"{execution_id}-HOST-RECEIPT",
        "execution_id": execution_id,
        "task_id": task_id,
        "attempt_id": attempt,
        "task_ref": _reference_mapping(task_ref),
        "authority_registry_ref": _reference_mapping(registry_ref),
        "policy_ref": _reference_mapping(policy_ref),
        "checker": _component_mapping("checker", checker),
        "runner": _component_mapping("runner", runner),
        "host": _component_mapping("host", host),
        "report_ref": _reference_mapping(report_ref),
        "subject_refs": [_reference_mapping(item) for item in subject_refs],
        "run_inputs_sha256": run_inputs,
        "transcript": {
            "exit_code": outcome.exit_code,
            "stdout_sha256": outcome.stdout_sha256,
            "stderr_sha256": outcome.stderr_sha256,
            "report_sha256": hash_bytes(report_bytes),
        },
        "report_produced_by": outcome.report_produced_by,
        "operator": operator,
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": outcome.outcome,
        "authority_boundaries": {
            # Provenance metadata only: promotion eligibility (the actual
            # execution fact) is established by promotion-time deterministic
            # re-execution, never by this receipt.
            "validation_execution_fact": False,
            "promotion_execution": False,
            "claim_acceptance": False,
            "human_decision": False,
            "scientific_correctness": False,
        },
    }
    receipt_errors = _schema_catalog().validate("promotion_validation_host_receipt", receipt)
    if receipt_errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in receipt_errors[:4])
        raise ContractError("validation run", f"generated host receipt is schema-invalid: {detail}")
    receipt_bytes = (json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    receipt_ref = FileReference(receipt_relative, hash_bytes(receipt_bytes))
    execution = {
        "schema_version": "0.1.0",
        "execution_id": execution_id,
        "task_id": task_id,
        "attempt_id": attempt,
        "task_ref": _reference_mapping(task_ref),
        "authority_registry_ref": _reference_mapping(registry_ref),
        "policy_ref": _reference_mapping(policy_ref),
        "checker": _component_mapping("checker", checker),
        "runner": _component_mapping("runner", runner),
        "host": _component_mapping("host", host),
        "report_ref": _reference_mapping(report_ref),
        "subject_refs": [_reference_mapping(item) for item in subject_refs],
        "executor": host[0],
        "host_receipt_ref": _reference_mapping(receipt_ref),
        "started_at": started_at,
        "finished_at": finished_at,
        "outcome": outcome.outcome,
        "authority_boundaries": {
            # Provenance metadata only: promotion eligibility (the actual
            # execution fact) is established by promotion-time deterministic
            # re-execution, never by this record alone.
            "validation_execution_fact": False,
            "promotion_execution": False,
            "claim_acceptance": False,
            "human_decision": False,
            "scientific_correctness": False,
        },
    }
    execution_errors = _schema_catalog().validate("promotion_validation_execution", execution)
    if execution_errors:
        detail = "; ".join(f"{item.pointer}: {item.message}" for item in execution_errors[:4])
        raise ContractError("validation run", f"generated execution is schema-invalid: {detail}")
    execution_bytes = _canonical_yaml_bytes(execution)

    written: list[Path] = []
    try:
        _write_exclusive(report_target, report_bytes)
        written.append(report_target)
        _write_exclusive(receipt_target, receipt_bytes)
        written.append(receipt_target)
        _write_exclusive(execution_target, execution_bytes)
        written.append(execution_target)
    except OSError as exc:
        for path in written:
            _best_effort_unlink(path)
        raise ContractError(
            "validation run", f"could not persist validation facts: {exc}"
        ) from exc
    return ValidationRunResult(outcome.outcome, report_relative, execution_relative, receipt_relative)


def check_host_receipt_closure(
    root: Path,
    record: PromotionRecord,
    report: Mapping[str, Any],
    execution: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> list[ContractRisk]:
    """Cross-check that the receipt, execution, and record pin one claimed run.

    This is a structural metadata closure: it proves the triple is internally
    consistent and bound to the frozen authority chain.  It does not prove the
    claimed run ever happened; that validity question is answered only by
    ``reexecute_validation`` at promotion time.
    """

    risks: list[ContractRisk] = []
    if receipt.get("execution_id") != execution.get("execution_id"):
        risks.append(_risk(UNPROVEN_RISK_CODE, "host receipt does not name its validation execution"))
    if receipt.get("task_id") != execution.get("task_id") or receipt.get(
        "attempt_id"
    ) != execution.get("attempt_id"):
        risks.append(
            _risk(UNPROVEN_RISK_CODE, "host receipt Task/Attempt identity differs from the execution")
        )
    for field, expected in (
        ("task_ref", record.task_ref),
        ("authority_registry_ref", record.validation_authority_registry),
        ("policy_ref", record.validation_policy),
        ("report_ref", record.validation_report),
    ):
        if _file_reference(receipt[field], field) != expected:
            risks.append(
                _risk(UNPROVEN_RISK_CODE, f"host receipt does not exact-pin the record's {field}")
            )
    execution_checker = _component_binding(execution["checker"], "checker")
    execution_runner = _component_binding(execution["runner"], "runner")
    execution_host = _component_binding(execution["host"], "host")
    for kind, binding in (
        ("checker", execution_checker),
        ("runner", execution_runner),
        ("host", execution_host),
    ):
        if _component_binding(receipt[kind], kind) != binding:
            risks.append(
                _risk(UNPROVEN_RISK_CODE, f"host receipt {kind} differs from the execution")
            )
    receipt_subjects = _reference_keys(receipt.get("subject_refs"), "subject_refs")
    execution_subjects = _reference_keys(execution.get("subject_refs"), "subject_refs")
    if set(receipt_subjects) != set(execution_subjects) or len(receipt_subjects) != len(
        execution_subjects
    ):
        risks.append(
            _risk(UNPROVEN_RISK_CODE, "host receipt subjects differ from the execution subjects")
        )
    transcript = receipt["transcript"]
    transcript_report = str(transcript["report_sha256"]).lower().removeprefix("sha256:")
    if transcript_report != record.validation_report.sha256:
        risks.append(
            _risk(UNPROVEN_RISK_CODE, "host receipt transcript does not pin the PASS report bytes")
        )
    if receipt.get("report_produced_by") != "runner":
        risks.append(
            _risk(UNPROVEN_RISK_CODE, "PASS eligibility requires a runner-produced report")
        )
    if receipt.get("outcome") != "pass":
        risks.append(_risk(UNPROVEN_RISK_CODE, "host receipt outcome must be pass"))
    if receipt.get("started_at") != execution.get("started_at") or receipt.get(
        "finished_at"
    ) != execution.get("finished_at"):
        risks.append(
            _risk(UNPROVEN_RISK_CODE, "host receipt timestamps differ from the execution")
        )
    expected_inputs = _run_inputs_sha256(
        execution_id=str(execution["execution_id"]),
        report_id=str(report["report_id"]),
        task_ref=record.task_ref,
        registry_ref=record.validation_authority_registry,
        policy_ref=record.validation_policy,
        checker=execution_checker,
        runner=execution_runner,
        host=execution_host,
        subjects=[_file_reference(item, "subject_refs") for item in execution["subject_refs"]],
    )
    declared_inputs = str(receipt.get("run_inputs_sha256", "")).lower().removeprefix("sha256:")
    if declared_inputs != expected_inputs:
        risks.append(
            _risk(
                UNPROVEN_RISK_CODE,
                "host receipt run-inputs closure cannot be reproduced from the pinned authority chain",
            )
        )
    return risks


def reexecute_validation(
    root: Path,
    record: PromotionRecord,
    report: Mapping[str, Any],
    execution: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> list[ContractRisk]:
    """Re-run the pinned pipeline and demand byte-exact transcript equivalence.

    This is the authoritative validity check behind promotion eligibility: it
    -- not the recorded report/execution/receipt triple -- establishes that the
    accepted runner/checker passes on the exact pinned subject bytes right now.
    """

    checker = _component_binding(execution["checker"], "checker")
    runner = _component_binding(execution["runner"], "runner")
    subjects = [_file_reference(item, "subject_refs") for item in execution["subject_refs"]]
    risks: list[ContractRisk] = []
    for item in subjects:
        if not check_file_reference(root, item).valid:
            risks.append(
                _risk(UNPROVEN_RISK_CODE, f"validation subject drifted before re-execution: {item.path}")
            )
    for binding, label in ((checker, "checker"), (runner, "runner")):
        if not check_file_reference(root, binding[2]).valid:
            risks.append(
                _risk(UNPROVEN_RISK_CODE, f"validation {label} source drifted before re-execution")
            )
    if risks:
        return risks
    outcome = _execute_runner(
        root,
        report_id=str(report["report_id"]),
        checker=checker,
        runner=runner,
        subjects=subjects,
    )
    if outcome.outcome != "pass":
        return [
            _risk(
                UNPROVEN_RISK_CODE,
                "deterministic re-execution of the accepted validation did not reproduce a PASS",
            )
        ]
    transcript = receipt["transcript"]
    actual = {
        "exit_code": outcome.exit_code,
        "stdout_sha256": outcome.stdout_sha256,
        "stderr_sha256": outcome.stderr_sha256,
        "report_sha256": hash_bytes(outcome.report_bytes),
    }
    mismatches = [
        name
        for name, actual_value in actual.items()
        if str(transcript[name]).lower().removeprefix("sha256:") != str(actual_value)
    ]
    if actual["report_sha256"] != record.validation_report.sha256:
        mismatches.append("report_bytes")
    if mismatches:
        risks.append(
            _risk(
                UNPROVEN_RISK_CODE,
                "deterministic re-execution transcript differs: " + ", ".join(sorted(mismatches)),
            )
        )
    return risks


__all__ = [
    "UNPROVEN_RISK_CODE",
    "VALIDATION_RUNNER_CONTRACT",
    "VALIDATION_RUN_TIMEOUT_SECONDS",
    "ValidationRunResult",
    "check_host_receipt_closure",
    "reexecute_validation",
    "run_validation_execution",
]
