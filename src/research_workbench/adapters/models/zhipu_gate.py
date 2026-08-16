"""Bounded project-level readiness Gate for the Zhipu standard Model API."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_workbench.adapters.models.conformance import run_provider_conformance
from research_workbench.adapters.models.http import EnvironmentCredential
from research_workbench.adapters.models.port import (
    Capability,
    ModelProvider,
    ProviderError,
    ToolChoice,
)
from research_workbench.adapters.models.session import ApiSessionLimits
from research_workbench.adapters.models.zhipu_chat import (
    ZHIPU_STANDARD_BASE_URL,
    ZhipuChatCompletionsProvider,
)
from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.contracts import is_path_safe_identifier
from research_workbench.io import load_document, write_text_exclusive, write_yaml_exclusive
from research_workbench.tasks import FileReference
from research_workbench.validation import SchemaCatalog


ZHIPU_GATE_ADAPTER_ID = "zhipu-chat-completions"
ZHIPU_GATE_CREDENTIAL_ENV = "ZHIPU_API_KEY"
ZHIPU_GATE_MODEL_ENV = "RWB_ZHIPU_MODEL"
ZHIPU_GATE_CHECKS = ("text", "structured", "tools")
ZHIPU_GATE_MAX_OUTPUT_TOKENS = 64
ZHIPU_GATE_LIMITS = ApiSessionLimits(
    max_model_turns=3,
    max_tool_calls=2,
    max_parallel_tool_calls=1,
    max_tool_result_chars=1_024,
    max_output_tokens_per_turn=256,
    max_seconds=120.0,
    max_total_tokens=5_000,
    max_provider_reported_cost=0.50,
    allowed_tool_side_effects=frozenset({"read-only"}),
)


ProviderFactory = Callable[[str], ModelProvider]


def zhipu_gate_plan() -> dict[str, object]:
    """Return the fixed readiness policy without reading host state."""

    return {
        "provider": "zhipu",
        "adapter_id": ZHIPU_GATE_ADAPTER_ID,
        "api_surface": "standard-chat-completions",
        "base_url": ZHIPU_STANDARD_BASE_URL,
        "credential_source": f"env:{ZHIPU_GATE_CREDENTIAL_ENV}",
        "model_source": f"env:{ZHIPU_GATE_MODEL_ENV}",
        "conformance": {
            "checks": list(ZHIPU_GATE_CHECKS),
            "tool_choice": "auto",
            "reasoning_effort": "low",
            "max_provider_invocations": 3,
            "max_output_tokens_per_invocation": ZHIPU_GATE_MAX_OUTPUT_TOKENS,
            "automatic_retries": 0,
        },
        "e2e": {
            "max_model_turns": ZHIPU_GATE_LIMITS.max_model_turns,
            "max_tool_calls": ZHIPU_GATE_LIMITS.max_tool_calls,
            "max_parallel_tool_calls": ZHIPU_GATE_LIMITS.max_parallel_tool_calls,
            "tool_allowlist": ["document-read"],
            "reasoning_effort": "low",
            "allowed_tool_side_effects": sorted(
                ZHIPU_GATE_LIMITS.allowed_tool_side_effects
            ),
            "max_total_tokens": ZHIPU_GATE_LIMITS.max_total_tokens,
            "max_provider_reported_cost": (
                ZHIPU_GATE_LIMITS.max_provider_reported_cost
            ),
            "automatic_retries": 0,
            "automatic_fallback": False,
            "task_fixture": "examples/task-evidence.yaml",
            "handoff_tier": "H2",
        },
    }


def run_zhipu_gate(
    *,
    execute: bool,
    environment: Mapping[str, str] | None = None,
    provider_factory: ProviderFactory | None = None,
    root: str | Path | None = None,
    attempt_id: str | None = None,
    accountable_owner: str | None = None,
    report_path: str | Path | None = None,
    now: Callable[[], datetime] | None = None,
) -> dict[str, object]:
    """Run one fixed Gate or emit deterministic zero-network not-run evidence."""

    if execute and report_path is None:
        raise ValueError("--execute requires --report before any Provider call")
    if not execute:
        return _not_run_report("explicit-execution-required", environment_checked=False)
    if root is None:
        raise ValueError("--execute requires --root")
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise ValueError("--execute requires --attempt-id")
    if not is_path_safe_identifier(attempt_id.strip()):
        raise ValueError("--attempt-id must be a portable path-safe identifier")
    if not isinstance(accountable_owner, str) or not accountable_owner.strip():
        raise ValueError("--execute requires --accountable-owner")

    project_root = Path(root).resolve()
    if not project_root.is_dir():
        raise ValueError("--root must be an existing project directory")
    report_target = Path(report_path).resolve()
    report_relative = _relative_to_root(project_root, report_target, "--report")
    decision_target = _decision_path(report_target)
    _relative_to_root(project_root, decision_target, "Gate Decision")
    if report_target.exists() or decision_target.exists():
        raise ValueError("--report and its derived Gate Decision must both be new")
    gate_id = attempt_id.strip()

    values = os.environ if environment is None else environment
    missing = [
        name
        for name in (ZHIPU_GATE_CREDENTIAL_ENV, ZHIPU_GATE_MODEL_ENV)
        if not values.get(name)
    ]
    if missing:
        report = _not_run_report(
            "required-environment-missing",
            environment_checked=True,
            gate_id=gate_id,
        )
        report["missing_environment"] = missing
        return _persist_gate_outcome(
            project_root,
            report_target,
            report_relative,
            decision_target,
            report,
            conformance_ref=None,
        )

    model = str(values[ZHIPU_GATE_MODEL_ENV])
    model_assignment = _build_gate_model_assignment(
        project_root, model=model, attempt_id=gate_id
    )
    archive = _preflight_project_gate(
        project_root,
        gate_id,
        report_target=report_target,
        decision_target=decision_target,
    )
    archive_refs = _persist_gate_intent(
        project_root,
        archive=archive,
        gate_id=gate_id,
        model=model,
        accountable_owner=accountable_owner.strip(),
        model_assignment=model_assignment,
    )
    factory = provider_factory or _build_provider
    conformance_ref: FileReference | None = None
    try:
        conformance_provider = factory(model)
        try:
            conformance = run_provider_conformance(
                conformance_provider,
                adapter_id=ZHIPU_GATE_ADAPTER_ID,
                execution_context="zhipu-live-readiness-gate",
                checks=ZHIPU_GATE_CHECKS,
                max_provider_invocations=3,
                max_output_tokens=ZHIPU_GATE_MAX_OUTPUT_TOKENS,
                tool_choice_override=ToolChoice(kind="auto"),
            )
        finally:
            _discard_ephemeral_continuation(conformance_provider)
        conformance_document = conformance.to_mapping()
        conformance_ref = _persist_conformance(
            project_root, archive, conformance_document, requested_model=model
        )
        archive_refs["conformance_check_ref"] = _ref_mapping(conformance_ref)
        if conformance.status != "passed":
            gate_status, reason = _conformance_failure_status(conformance_document)
            report = _report(
                status=gate_status,
                reason=reason,
                environment_checked=True,
                requested_model=model,
                gate_id=gate_id,
                archive=archive_refs,
                conformance={
                    "status": "failed",
                    "reason": reason,
                    "check_ref": _ref_mapping(conformance_ref),
                },
                e2e={"status": "not-run", "reason": reason},
            )
            return _persist_gate_outcome(
                project_root,
                report_target,
                report_relative,
                decision_target,
                report,
                conformance_ref=conformance_ref,
            )

        project_provider = factory(model)
        if project_provider is conformance_provider:
            _discard_ephemeral_continuation(project_provider)
            raise ValueError("Zhipu Gate phases require distinct Provider instances")
        e2e = _run_project_e2e(
            project_provider,
            model=model,
            root=project_root,
            attempt_id=gate_id,
            accountable_owner=accountable_owner.strip(),
            now=now,
            model_assignment=model_assignment,
            conformance_document=conformance_document,
            conformance_sha256=conformance_ref.sha256,
        )
        e2e_status = str(e2e["status"])
        if e2e_status == "passed":
            gate_status, reason = "passed", "all-checks-passed"
        elif e2e_status in {"safe-paused", "blocked"}:
            gate_status = "safe-paused"
            reason = str(e2e.get("reason", "project-readiness-safe-paused"))
        else:
            gate_status = "failed"
            reason = str(e2e.get("reason", "project-e2e-failed"))
        report = _report(
            status=gate_status,
            reason=reason,
            environment_checked=True,
            requested_model=model,
            gate_id=gate_id,
            archive=archive_refs,
            conformance={
                "status": "passed",
                "reason": "all-conformance-checks-passed",
                "check_ref": _ref_mapping(conformance_ref),
            },
            e2e=e2e,
        )
        return _persist_gate_outcome(
            project_root,
            report_target,
            report_relative,
            decision_target,
            report,
            conformance_ref=conformance_ref,
        )
    except ProviderError:
        conformance_outcome = (
            {
                "status": "passed",
                "reason": "all-conformance-checks-passed",
                "check_ref": _ref_mapping(conformance_ref),
            }
            if conformance_ref is not None
            else {"status": "failed", "reason": "provider-error"}
        )
        report = _report(
            status="failed",
            reason="provider-error",
            environment_checked=True,
            requested_model=model,
            gate_id=gate_id,
            archive=archive_refs,
            conformance=conformance_outcome,
            e2e={"status": "not-run", "reason": "provider-error"},
        )
        return _persist_gate_outcome(
            project_root,
            report_target,
            report_relative,
            decision_target,
            report,
            conformance_ref=conformance_ref,
        )
    except Exception:
        conformance_outcome = (
            {
                "status": "passed",
                "reason": "all-conformance-checks-passed",
                "check_ref": _ref_mapping(conformance_ref),
            }
            if conformance_ref is not None
            else {"status": "failed", "reason": "gate-internal-error"}
        )
        report = _report(
            status="failed",
            reason="gate-internal-error",
            environment_checked=True,
            requested_model=model,
            gate_id=gate_id,
            archive=archive_refs,
            conformance=conformance_outcome,
            e2e={"status": "not-run", "reason": "gate-internal-error"},
        )
        return _persist_gate_outcome(
            project_root,
            report_target,
            report_relative,
            decision_target,
            report,
            conformance_ref=conformance_ref,
        )


def _build_provider(model: str) -> ModelProvider:
    return ZhipuChatCompletionsProvider(
        model=model,
        credential=EnvironmentCredential(ZHIPU_GATE_CREDENTIAL_ENV),
        supported=frozenset(
            {
                Capability.TEXT,
                Capability.STRUCTURED_OUTPUT,
                Capability.TOOLS,
                Capability.REASONING,
            }
        ),
        base_url=ZHIPU_STANDARD_BASE_URL,
        max_retries=0,
    )


def _discard_ephemeral_continuation(provider: ModelProvider) -> None:
    discard = getattr(provider, "discard_ephemeral_continuation", None)
    if callable(discard):
        discard()


def _preflight_project_gate(
    root: Path,
    attempt_id: str,
    *,
    report_target: Path,
    decision_target: Path,
) -> Path:
    required = (
        "examples/zhipu-live-gate/project-protocol.yaml",
        "examples/task-evidence.yaml",
        "examples/profiles/evidence-scout.yaml",
        "examples/vertical-slice/evidence-assignment.yaml",
        "examples/fixtures/paper-001.txt",
        ".agents/skills/literature-evidence-extraction/SKILL.md",
    )
    missing = [relative for relative in required if not (root / relative).is_file()]
    if missing:
        raise ValueError("Gate project root lacks required public fixtures: " + ", ".join(missing))
    conflicts = (
        root / "work" / "EVID-001" / attempt_id,
        root / ".rwb" / "attempt-intents" / f"{attempt_id}.yaml",
        root / ".rwb" / "closeout" / attempt_id,
        root / ".rwb" / "zhipu-gates" / attempt_id,
        report_target,
        decision_target,
    )
    if any(path.exists() for path in conflicts):
        raise ValueError("--attempt-id must identify a new Gate Attempt")
    return root / ".rwb" / "zhipu-gates" / attempt_id


def _build_gate_model_assignment(root: Path, *, model: str, attempt_id: str) -> Any:
    from research_workbench.adapters.models.pool import ModelPool
    from research_workbench.capability import ResolvedTask
    from research_workbench.execution.compiler import derive_execution_controls
    from research_workbench.execution.contracts import default_execution_contract_registry
    from research_workbench.protocol import ProjectProtocol
    from research_workbench.tasks import TaskPacket

    protocol = ProjectProtocol.from_mapping(
        load_document(root / "examples/zhipu-live-gate/project-protocol.yaml")
    )
    task = TaskPacket.from_mapping(load_document(root / "examples/task-evidence.yaml"))
    assignment = ResolvedTask.from_mapping(
        load_document(root / "examples/vertical-slice/evidence-assignment.yaml")
    )
    contract = default_execution_contract_registry().require(task, assignment)
    effective_policy, effective_limits = derive_execution_controls(
        protocol=protocol,
        task=task,
        runtime_limits=ZHIPU_GATE_LIMITS,
        execution_contract=contract,
    )
    pool = ModelPool.from_mapping(
        {
            "schema_version": "0.1.0",
            "registry_kind": "model_pool",
            "pool_id": "zhipu-live-gate-pool",
            "selection_policy": "explicit-slot-only",
            "slots": [
                {
                    "slot_id": "worker",
                    "role": "worker",
                    "provider_adapter": ZHIPU_GATE_ADAPTER_ID,
                    "model_env": ZHIPU_GATE_MODEL_ENV,
                    "enabled": True,
                    "capabilities": [
                        "text",
                        "tools",
                        "structured_output",
                        "reasoning",
                    ],
                    "reasoning_effort": "low",
                }
            ],
        }
    )
    return pool.assign(
        "worker",
        environment={ZHIPU_GATE_MODEL_ENV: model},
        attempt_id=attempt_id,
        task_id=task.task_id,
        task_revision=task.revision,
        agent_profile_ref=FileReference(
            "examples/profiles/evidence-scout.yaml",
            hash_file(root / "examples/profiles/evidence-scout.yaml"),
        ),
        selection_reason=(
            "The Zhipu readiness Gate explicitly selects one worker slot; no fallback exists."
        ),
        effective_data_policy=effective_policy,
        execution_limits=effective_limits,
    )


def _persist_gate_intent(
    root: Path,
    *,
    archive: Path,
    gate_id: str,
    model: str,
    accountable_owner: str,
    model_assignment: Any,
) -> dict[str, object]:
    assignment_path = archive / "model-assignment.yaml"
    write_yaml_exclusive(assignment_path, model_assignment.to_mapping())
    assignment_ref = _file_ref(root, assignment_path)
    intent = {
        "schema_version": "0.1.0",
        "intent_kind": "zhipu_live_gate",
        "gate_id": gate_id,
        "provider": "zhipu",
        "adapter_id": ZHIPU_GATE_ADAPTER_ID,
        "requested_model": model,
        "accountable_owner": accountable_owner,
        "automatic_fallback": False,
        "model_assignment_ref": _ref_mapping(assignment_ref),
        "policy": zhipu_gate_plan(),
    }
    intent_path = archive / "intent.yaml"
    write_yaml_exclusive(intent_path, intent)
    return {
        "intent_ref": _ref_mapping(_file_ref(root, intent_path)),
        "model_assignment_ref": _ref_mapping(assignment_ref),
    }


def _persist_conformance(
    root: Path,
    archive: Path,
    document: Mapping[str, Any],
    *,
    requested_model: str,
) -> FileReference:
    errors = SchemaCatalog().validate("provider_conformance_report", document)
    if errors:
        raise ValueError("Provider conformance report is schema-invalid")
    if (
        document.get("provider") != "zhipu"
        or document.get("adapter_id") != ZHIPU_GATE_ADAPTER_ID
        or document.get("requested_model") != requested_model
    ):
        raise ValueError("Provider conformance report differs from the Gate binding")
    path = archive / "provider-conformance.yaml"
    write_yaml_exclusive(path, document)
    return _file_ref(root, path)


def _run_project_e2e(
    provider: ModelProvider,
    *,
    model: str,
    root: Path,
    attempt_id: str,
    accountable_owner: str,
    now: Callable[[], datetime] | None,
    model_assignment: Any,
    conformance_document: Mapping[str, Any],
    conformance_sha256: str,
) -> dict[str, object]:
    from research_workbench.adapters.models.port import ProviderRegistry
    from research_workbench.execution.pipeline import run_task_api_attempt

    protocol_ref = "examples/zhipu-live-gate/project-protocol.yaml"
    task_ref = "examples/task-evidence.yaml"
    profile_ref = "examples/profiles/evidence-scout.yaml"
    assignment_ref = "examples/vertical-slice/evidence-assignment.yaml"
    task_id = model_assignment.task_id
    providers = ProviderRegistry()
    providers.register(ZHIPU_GATE_ADAPTER_ID, provider)
    current_time = now or (lambda: datetime.now(timezone.utc))
    started_at = _timestamp(current_time())
    publication = run_task_api_attempt(
        root=root,
        protocol_ref=protocol_ref,
        task_ref=task_ref,
        profile_ref=profile_ref,
        assignment_ref=assignment_ref,
        model_assignment=model_assignment,
        providers=providers,
        runtime_limits=ZHIPU_GATE_LIMITS,
        attempt_id=attempt_id,
        started_at=started_at,
        finished_at=started_at,
        next_actions=_gate_next_actions(),
        trace_accountable_owner=accountable_owner,
        extra_limitations=(
            "Zhipu live readiness Gate over a public synthetic fixture; no scientific claim was evaluated.",
            "Offline implementation of the adapter tool protocol is not live capability or cost evidence.",
        ),
        event_clock=lambda: _timestamp(current_time()),
        provider_conformance_document=conformance_document,
        provider_conformance_expected_sha256=conformance_sha256,
    )
    main_state = _file_ref_mapping(root, publication.main_state_ref)
    receipt = _file_ref_mapping(
        root, f"work/{task_id}/{attempt_id}/execution-receipt.yaml"
    )
    trace = _file_ref_mapping(root, f"work/{task_id}/{attempt_id}/INDEX.yaml")
    published = [_file_ref_mapping(root, relative) for relative in publication.published_refs]
    chain_complete = _verify_closeout_chain(
        root,
        attempt_id=attempt_id,
        model=model,
        main_state_ref=publication.main_state_ref,
        require_h2_success=publication.status == "completed",
    )
    resume = _fresh_resume_check(
        root,
        main_state_ref=publication.main_state_ref,
        protocol_ref=protocol_ref,
    )
    attempt = load_document(root / "work" / task_id / attempt_id / "attempt.yaml")
    failure = attempt.get("failure") if isinstance(attempt, Mapping) else None
    stop_reason = failure.get("stop_reason") if isinstance(failure, Mapping) else None
    failure_code = failure.get("code") if isinstance(failure, Mapping) else None
    if not chain_complete:
        e2e_status, reason = "failed", "closeout-chain-failed"
    elif resume["status"] != "passed":
        e2e_status, reason = "failed", "fresh-process-resume-failed"
    elif publication.status == "completed":
        e2e_status, reason = "passed", "project-h2-completed"
    else:
        e2e_status = publication.status
        reason = (
            str(stop_reason)
            if isinstance(stop_reason, str)
            else (
                str(failure_code)
                if isinstance(failure_code, str)
                else f"closeout-{publication.status}"
            )
        )
    return {
        "status": e2e_status,
        "reason": reason,
        "closeout_status": publication.status,
        "main_state_ref": main_state,
        "receipt_ref": receipt,
        "trace_ref": trace,
        "published_refs": published,
        "fresh_process_resume_check": resume,
    }


def _verify_closeout_chain(
    root: Path,
    *,
    attempt_id: str,
    model: str,
    main_state_ref: str,
    require_h2_success: bool,
) -> bool:
    attempt_root = root / "work" / "EVID-001" / attempt_id
    required = {
        "model-assignment.yaml",
        "provider-conformance.yaml",
        "attempt.yaml",
        "INDEX.yaml",
        "handoff.yaml",
        "execution-receipt.yaml",
        "main-state.yaml",
    }
    if require_h2_success:
        required.update({"transfer-manifest.yaml", "transfer-audit.yaml"})
    if not all((attempt_root / name).is_file() for name in required):
        return False
    attempt = load_document(attempt_root / "attempt.yaml")
    receipt = load_document(attempt_root / "execution-receipt.yaml")
    trace = load_document(attempt_root / "INDEX.yaml")
    state = load_document(root / main_state_ref)
    assignment = load_document(attempt_root / "model-assignment.yaml")
    trace_ref = _file_ref_mapping(root, f"work/EVID-001/{attempt_id}/INDEX.yaml")
    assignment_ref = _file_ref_mapping(
        root, f"work/EVID-001/{attempt_id}/model-assignment.yaml"
    )
    conformance_ref = _file_ref_mapping(
        root, f"work/EVID-001/{attempt_id}/provider-conformance.yaml"
    )
    linked = bool(
        attempt.get("handoff_tier") == "H2"
        and receipt.get("handoff_tier") == "H2"
        and attempt.get("agent_trace_index_ref") == trace_ref
        and receipt.get("agent_trace_index_ref") == trace_ref
        and attempt.get("model_assignment_ref") == assignment_ref
        and receipt.get("model_assignment_ref") == assignment_ref
        and attempt.get("provider_conformance_ref") == conformance_ref
        and receipt.get("provider_conformance_ref") == conformance_ref
        and trace_ref in state.get("agent_trace_index_refs", [])
        and assignment_ref in state.get("machine_state_refs", [])
        and conformance_ref in state.get("machine_state_refs", [])
        and assignment.get("automatic_fallback") is False
        and assignment.get("provider_adapter_id") == ZHIPU_GATE_ADAPTER_ID
        and assignment.get("requested_model") == model
        and conformance_ref in trace.get("check_refs", [])
    )
    if not linked or not require_h2_success:
        return linked
    return bool(
        (attempt_root / "artifacts").is_dir()
        and tuple((attempt_root / "artifacts").glob("*.yaml"))
        and {Path(item["path"]).name for item in trace.get("handoff_refs", [])}
        == {"handoff.yaml", "transfer-manifest.yaml"}
        and {Path(item["path"]).name for item in trace.get("check_refs", [])}
        == {"transfer-audit.yaml", "provider-conformance.yaml"}
    )


def _fresh_resume_check(
    root: Path, *, main_state_ref: str, protocol_ref: str
) -> dict[str, object]:
    environment = dict(os.environ)
    environment.pop(ZHIPU_GATE_CREDENTIAL_ENV, None)
    environment.pop(ZHIPU_GATE_MODEL_ENV, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "research_workbench",
            "context",
            "resume-check",
            str(root / main_state_ref),
            "--protocol",
            str(root / protocol_ref),
            "--root",
            str(root),
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return {
        "status": "passed" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
    }


def _conformance_failure_status(document: Mapping[str, Any]) -> tuple[str, str]:
    checks = document.get("checks")
    if isinstance(checks, list):
        for check in checks:
            if not isinstance(check, Mapping) or check.get("status") != "failed":
                continue
            if check.get("error_category") in {"unsupported", "invalid_request"}:
                return ("safe-paused", "standard-api-model-or-capability-unavailable")
    return ("failed", "conformance-failed")


def _gate_next_actions() -> dict[str, str]:
    return {
        "completed": "Review the synthetic Zhipu Gate closeout; do not treat it as scientific evidence.",
        "stage-completed": "Review the stage-complete Gate closeout before promotion.",
        "safe-paused": "Resolve live cost/capability evidence before a new Gate Attempt.",
        "incomplete": "Review the incomplete Gate closeout before a new Attempt.",
        "failed": "Inspect redacted Gate failure evidence before a new Attempt.",
        "blocked": "Resolve the frozen Gate capability or policy block before a new Attempt.",
    }


def _not_run_report(
    reason: str, *, environment_checked: bool, gate_id: str = "not-run"
) -> dict[str, object]:
    return _report(
        status="not-run",
        reason=reason,
        environment_checked=environment_checked,
        gate_id=gate_id,
        conformance={"status": "not-run", "reason": reason},
        e2e={"status": "not-run", "reason": reason},
    )


def _report(
    *,
    status: str,
    reason: str,
    environment_checked: bool,
    gate_id: str,
    conformance: Mapping[str, object],
    e2e: Mapping[str, object],
    requested_model: str | None = None,
    archive: Mapping[str, object] | None = None,
) -> dict[str, object]:
    report: dict[str, object] = {
        "schema_version": "0.1.0",
        "report_kind": "zhipu_live_gate",
        "gate_id": gate_id,
        "status": status,
        "reason": reason,
        "provider": "zhipu",
        "adapter_id": ZHIPU_GATE_ADAPTER_ID,
        "environment_checked": environment_checked,
        "policy": zhipu_gate_plan(),
        "conformance": dict(conformance),
        "e2e": dict(e2e),
        "privacy": {
            "credential_values_stored": False,
            "provider_response_ids_stored": False,
            "prompt_bodies_stored": False,
            "response_bodies_stored": False,
            "tool_arguments_stored": False,
        },
        "limitations": [
            "Offline adapter tool-protocol implementation does not prove live tool compatibility.",
            "Token usage without provider-reported monetary cost and currency cannot satisfy the cost Gate.",
            "No Zhipu readiness outcome, including passed, is an ADR-0013 OpenAI Gate pass or proof of scientific correctness.",
        ],
    }
    if requested_model is not None:
        report["requested_model"] = requested_model
    if archive is not None:
        report["archive"] = dict(archive)
    return report


def _persist_gate_outcome(
    root: Path,
    report_path: Path,
    report_relative: str,
    decision_path: Path,
    report: dict[str, object],
    *,
    conformance_ref: FileReference | None,
) -> dict[str, object]:
    if SchemaCatalog().validate("zhipu_live_gate_report", report):
        raise ValueError("Zhipu Gate report is schema-invalid")
    _write_gate_document(report_path, report)
    status = str(report["status"])
    decision_name = {
        "passed": "accept",
        "safe-paused": "defer",
        "failed": "reject",
        "not-run": "not-run",
    }[status]
    decision: dict[str, object] = {
        "schema_version": "0.1.0",
        "decision_kind": "zhipu_live_gate_decision",
        "decision_id": f"{report['gate_id']}-decision",
        "gate_id": report["gate_id"],
        "gate_status": status,
        "decision": decision_name,
        "reason": report["reason"],
        "automatic_fallback": False,
        "scientific_correctness_proven": False,
        "adr_0013_passed": False,
        "gate_report_ref": _ref_mapping(
            FileReference(report_relative, hash_file(report_path))
        ),
        "limitations": [
            "No automatic provider or model fallback was allowed.",
            "Offline tool-protocol implementation is not live compatibility evidence.",
            "A Zhipu readiness result does not replace the ADR-0013 OpenAI Gate.",
        ],
    }
    if conformance_ref is not None:
        decision["conformance_check_ref"] = _ref_mapping(conformance_ref)
    e2e = report.get("e2e")
    if isinstance(e2e, Mapping):
        for key in ("main_state_ref", "receipt_ref", "trace_ref"):
            value = e2e.get(key)
            if isinstance(value, Mapping):
                decision[key] = dict(value)
    if SchemaCatalog().validate("zhipu_live_gate_decision", decision):
        raise ValueError("Zhipu Gate Decision is schema-invalid")
    _write_gate_document(decision_path, decision)
    return report


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _ref_mapping(reference: FileReference) -> dict[str, object]:
    result: dict[str, object] = {
        "path": reference.path,
        "sha256": reference.sha256,
    }
    if reference.revision is not None:
        result["revision"] = reference.revision
    return result


def _relative_to_root(root: Path, path: Path, label: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"{label} must stay within --root") from exc


def _file_ref(root: Path, path: Path) -> FileReference:
    return FileReference(_relative_to_root(root, path, "Gate archive"), hash_file(path))


def _file_ref_mapping(root: Path, relative: str) -> dict[str, object]:
    path = resolve_within_root(root, relative)
    if path is None or not path.is_file():
        raise ValueError("Gate evidence reference is unavailable")
    return _ref_mapping(FileReference(relative, hash_file(path)))


def _decision_path(report_path: Path) -> Path:
    suffix = report_path.suffix.lower()
    if suffix not in {".json", ".yaml", ".yml"}:
        raise ValueError("--report must use .json, .yaml, or .yml")
    return report_path.with_name(f"{report_path.stem}.decision{suffix}")


def _write_gate_document(path: Path, document: Mapping[str, Any]) -> None:
    if path.suffix.lower() == ".json":
        write_text_exclusive(
            path,
            json.dumps(dict(document), indent=2, ensure_ascii=False) + "\n",
        )
    else:
        write_yaml_exclusive(path, document)
