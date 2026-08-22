from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from research_workbench.adapters import CodexRuntimeAdapter
from research_workbench.adapters.models import (
    build_live_provider,
    conformance_plan,
    get_provider_adapter_config,
    load_model_pool,
    probe_provider_adapters,
    run_provider_conformance,
)
from research_workbench.artifacts.integrity import hash_directory, hash_file, resolve_within_root
from research_workbench.capability import (
    AcceptedSkillRegistry,
    AgentProfile,
    ResolvedTask,
    ResolutionError,
    SkillManifest,
    audit_skill_archive,
    filter_candidates,
    load_candidates,
    resolve_task,
    resolve_task_from_registry,
)
from research_workbench.capability.catalog import DEFAULT_ACCEPTED, DEFAULT_CANDIDATES
from research_workbench.context import (
    CONTEXT_METRIC_NAMES,
    ContextBudgetEstimate,
    ContextPolicySnapshot,
    ContextSnapshot,
    assess_handoff_transfer,
    MainStatePacket,
    checkpoint_digest,
)
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel, to_plain
from research_workbench.evaluation import assess_skill_evaluation
from research_workbench.io import iter_documents, load_document
from research_workbench.observability import ExecutionReceipt, check_execution_receipt
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import AttemptRecord, FileReference, HandoffPacket, TaskPacket
from research_workbench.validation import (
    SchemaCatalog,
    check_claim_ceiling,
    check_handoff_against_task,
    check_references,
)
from research_workbench.validation.documents import (
    Severity,
    infer_document_kind,
    load_and_validate,
)


def _write_yaml(path: Path, document: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            yaml.safe_dump(dict(document), stream, sort_keys=False, allow_unicode=True)
            stream.flush()
            os.fsync(stream.fileno())

        # Linking publishes a fully flushed inode only when the destination is
        # still absent. It preserves the previous exclusive-create behaviour
        # without exposing a partially written checkpoint as the final path.
        os.link(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def _print_risks(risks) -> int:
    if not risks:
        print("ok: no blocking deterministic risks")
        return 0
    for risk in risks:
        print(f"{risk.level.upper():7} {risk.code:28} {risk.message}")
    blockers = sum(risk.level == RiskLevel.BLOCK for risk in risks)
    return 1 if blockers else 0


def _document_reference_risks(document: Mapping[str, Any], root: Path):
    kind = infer_document_kind(document)
    references: tuple[FileReference, ...] = ()
    path_only: list[str] = []
    extra_risks: list[ContractRisk] = []
    if kind == "task_packet":
        references = TaskPacket.from_mapping(document).input_refs
    elif kind == "handoff_packet":
        handoff = HandoffPacket.from_mapping(document)
        references = handoff.input_lock
        if handoff.skill_assignment_ref:
            path_only.append(handoff.skill_assignment_ref)
        path_only.extend(handoff.artifact_refs)
        path_only.extend(handoff.validation_refs)
        if handoff.execution_receipt_ref:
            path_only.append(handoff.execution_receipt_ref)
        if handoff.transfer_manifest_ref:
            path_only.append(handoff.transfer_manifest_ref)
    elif kind == "skill_manifest":
        skill = SkillManifest.from_mapping(document)
        if skill.source_locator and not skill.source_locator.startswith(("http://", "https://")):
            references = (
                FileReference(skill.source_locator, skill.source_content_hash.removeprefix("sha256:")),
            )
    elif kind == "skill_assignment":
        assignment = ResolvedTask.from_mapping(document)
        references = tuple(
            FileReference(lock.source_locator, lock.content_hash.removeprefix("sha256:"))
            for lock in assignment.skill_lock
            if lock.source_locator
        )
        for lock in assignment.skill_lock:
            if lock.source_locator and lock.package_hash:
                resolved = resolve_within_root(root, lock.source_locator)
                if resolved is not None and resolved.is_file():
                    actual = hash_directory(resolved.parent)
                    expected = lock.package_hash.removeprefix("sha256:").lower()
                    if actual != expected:
                        extra_risks.append(
                            ContractRisk(
                                "SKILL-PACKAGE-DRIFT",
                                RiskLevel.BLOCK,
                                f"Skill package drift: {lock.identifier} expected={expected} actual={actual}",
                            )
                        )
    elif kind == "attempt":
        attempt = AttemptRecord.from_mapping(document)
        references = attempt.input_lock
        path_only.extend(attempt.artifact_refs)
        if attempt.handoff_ref:
            path_only.append(attempt.handoff_ref)
        if attempt.execution_receipt_ref:
            path_only.append(attempt.execution_receipt_ref)
    elif kind == "main_state":
        state = MainStatePacket.from_mapping(document)
        references = state.machine_state_refs
        path_only.extend(item.ref for item in state.recent_handoffs)
        path_only.extend(state.artifact_index_refs)
        if state.previous_checkpoint_ref:
            path_only.append(state.previous_checkpoint_ref)
        if state.context_snapshot_ref:
            path_only.append(state.context_snapshot_ref)
    elif kind == "context_snapshot":
        snapshot = ContextSnapshot.from_mapping(document)
        if snapshot.handoff_audit_ref:
            path_only.append(snapshot.handoff_audit_ref)
    elif kind == "execution_receipt":
        receipt = ExecutionReceipt.from_mapping(document)
        path_only.extend(
            (
                receipt.attempt_ref,
                receipt.agent_profile_ref,
                receipt.skill_assignment_ref,
                *receipt.output_refs,
                *receipt.validation_refs,
            )
        )
        if receipt.context_snapshot_ref:
            path_only.append(receipt.context_snapshot_ref)
        if receipt.runtime.capability_snapshot_ref:
            path_only.append(receipt.runtime.capability_snapshot_ref)
    elif kind == "deterministic_check_report":
        checker = document.get("checker")
        if isinstance(checker, Mapping) and isinstance(checker.get("source_ref"), Mapping):
            references = (FileReference.from_mapping(checker["source_ref"]),)
        for subject_ref in document.get("subject_refs", []):
            if isinstance(subject_ref, Mapping):
                references += (FileReference.from_mapping(subject_ref),)
    elif kind == "handoff_transfer_manifest":
        for source_ref in document.get("source_artifact_refs", []):
            if isinstance(source_ref, Mapping):
                references += (FileReference.from_mapping(source_ref),)
    elif kind == "handoff_transfer_audit":
        for key in ("task_ref", "handoff_ref", "manifest_ref"):
            reference = document.get(key)
            if isinstance(reference, Mapping):
                references += (FileReference.from_mapping(reference),)
    elif kind == "skill_evaluation":
        source_ref = document.get("skill_source_ref")
        if isinstance(source_ref, Mapping):
            references = (FileReference.from_mapping(source_ref),)
        project_protocol_ref = document.get("project_protocol_ref")
        if isinstance(project_protocol_ref, Mapping):
            references += (FileReference.from_mapping(project_protocol_ref),)
        model_config_ref = document.get("model_config_ref")
        if isinstance(model_config_ref, Mapping):
            references += (FileReference.from_mapping(model_config_ref),)
        for case in document.get("cases", []):
            if not isinstance(case, Mapping):
                continue
            for key in ("task_contract_ref", "input_ref"):
                case_ref = case.get(key)
                if isinstance(case_ref, Mapping):
                    references += (FileReference.from_mapping(case_ref),)
            arms = case.get("arms")
            if not isinstance(arms, Mapping):
                continue
            for arm in arms.values():
                if not isinstance(arm, Mapping):
                    continue
                for key in ("output_ref", "validation_ref"):
                    reference = arm.get(key)
                    if isinstance(reference, Mapping):
                        references += (FileReference.from_mapping(reference),)
                receipt_ref = arm.get("execution_receipt_ref")
                if isinstance(receipt_ref, str):
                    path_only.append(receipt_ref)
        admission = document.get("admission")
        if isinstance(admission, Mapping) and isinstance(admission.get("decision_ref"), str):
            path_only.append(str(admission["decision_ref"]))
    risks = check_references(root, references)
    risks.extend(extra_risks)
    for relative in path_only:
        resolved = resolve_within_root(root, relative)
        if resolved is None:
            risks.append(ContractRisk("REF-OUTSIDE-ROOT", RiskLevel.BLOCK, f"reference escapes root: {relative}"))
        elif not resolved.is_file():
            risks.append(ContractRisk("REF-MISSING", RiskLevel.BLOCK, f"missing file: {relative}"))
    return risks


def _load_valid(path: str | Path, kind: str) -> Mapping[str, Any]:
    document = load_document(path)
    if not isinstance(document, Mapping):
        raise ValueError(f"{path}: document must be an object")
    errors = SchemaCatalog().validate(kind, document)
    if errors:
        rendered = "; ".join(f"{error.pointer}: {error.message}" for error in errors[:5])
        raise ValueError(f"{path}: schema validation failed: {rendered}")
    return document


def _validate(args: argparse.Namespace) -> int:
    paths = iter_documents(args.paths)
    documents, issues = load_and_validate(paths)
    for issue in issues:
        print(f"{issue.severity.upper():7} {issue.code:20} {issue.path}: {issue.message}")
    errors = sum(issue.severity == Severity.ERROR for issue in issues)
    warnings = sum(issue.severity == Severity.WARNING for issue in issues)
    reference_risks = []
    if not args.structure_only:
        error_paths = {issue.path for issue in issues if issue.severity == Severity.ERROR}
        for path, document in documents.items():
            if path in error_paths or not isinstance(document, Mapping):
                continue
            try:
                reference_risks.extend(_document_reference_risks(document, Path(args.root).resolve()))
            except ContractError as exc:
                print(f"ERROR   CONTRACT-INVALID     {path}: {exc}")
                errors += 1
        errors += sum(risk.level == RiskLevel.BLOCK for risk in reference_risks)
        warnings += sum(risk.level == RiskLevel.WARNING for risk in reference_risks)
        for risk in reference_risks:
            print(f"{risk.level.upper():7} {risk.code:20} {risk.message}")
    print(f"validated={len(paths)} errors={errors} warnings={warnings}")
    return 1 if errors else 0


def _hash(args: argparse.Namespace) -> int:
    path = Path(args.path)
    print(f"sha256:{hash_file(path)}  {path}")
    return 0


def _init_project(args: argparse.Namespace) -> int:
    root = Path(args.path)
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"refusing to initialize a non-empty directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    project_id = args.project_id or root.name
    protocol = {
        "schema_version": "0.1.0",
        "project_id": project_id,
        "revision": 1,
        "question_refs": [],
        "active_modes": [],
        "claim_ceiling": ["unresolved"],
        "required_human_gates": ["approve_main_claim", "approve_external_release"],
        "budgets": {
            "max_parallel_subagents": 1,
            "max_delegation_depth": 1,
            "coordination_cost_ratio_warn": 0.33,
        },
        "context_policy": {"proactive_checkpoint": True, "main_raw_material": "on-demand"},
        "data_boundary": {"local_only": True, "external_upload_requires_approval": True},
    }
    errors = SchemaCatalog().validate("project_protocol", protocol)
    if errors:
        raise ValueError("internal protocol template failed schema validation")
    _write_yaml(root / "project-protocol.yaml", protocol)
    for directory in ("objects", "tasks", "handoffs", "checkpoints", "work"):
        (root / directory).mkdir()
    print(f"initialized {project_id!r} at {root}")
    return 0


def _skill_candidates(args: argparse.Namespace) -> int:
    candidates = filter_candidates(
        load_candidates(args.registry),
        status=args.status,
        mode=args.mode,
        capability=args.capability,
    )
    if args.json:
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
        return 0
    print("candidate_id\tstatus\tkind\tcontext\tdecision")
    for candidate in candidates:
        print(
            f"{candidate['candidate_id']}\t{candidate['status']}\t{candidate['kind']}\t"
            f"{candidate['context_cost']}\t{candidate['decision']['action']}"
        )
    return 0


def _skill_accepted(args: argparse.Namespace) -> int:
    registry = AcceptedSkillRegistry.load(args.registry, project_root=args.root)
    if args.json:
        print(
            json.dumps(
                {
                    "registry_digest": registry.digest,
                    "entries": [
                        {
                            "skill_id": entry.skill_id,
                            "version": entry.version,
                            "source_path": entry.source_path,
                            "content_hash": entry.content_hash,
                            "package_hash": entry.package_hash,
                            "license_status": entry.license_status,
                            "lifecycle": entry.lifecycle,
                        }
                        for entry in registry.entries
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    print("skill\tversion\tlifecycle\tlicense\tcontent_hash")
    for entry in registry.entries:
        print(
            f"{entry.skill_id}\t{entry.version}\t{entry.lifecycle}\t"
            f"{entry.license_status}\t{entry.content_hash}"
        )
    print(f"registry_digest\t{registry.digest}")
    return 0


def _skill_audit_archive(args: argparse.Namespace) -> int:
    report = audit_skill_archive(
        args.archive,
        source_id=args.source_id,
        expected_sha256=args.expected_sha256,
        candidate_registry=args.registry,
        generated_at=args.generated_at,
    )
    schema_errors = SchemaCatalog().validate("skill_archive_audit", report)
    if schema_errors:
        first = schema_errors[0]
        raise ValueError(f"generated archive audit is invalid at {first.pointer}: {first.message}")
    if args.output:
        output = Path(args.output)
        if output.suffix.lower() == ".json":
            _write_text(output, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        elif output.suffix.lower() in {".yaml", ".yml"}:
            _write_yaml(output, report)
        else:
            raise ValueError("archive audit output must use .json, .yaml, or .yml")
        summary = report["summary"]
        print(
            f"skill archive audit written: skills={summary['skill_count']} "
            f"registered={summary['registered_skill_count']} "
            f"unregistered={summary['unregistered_skill_count']} output={output}"
        )
        return 0
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _skill_eval_assess(args: argparse.Namespace) -> int:
    document = _load_valid(args.evaluation, "skill_evaluation")
    assessment = assess_skill_evaluation(
        document,
        root=args.root,
        candidate_registry=args.registry,
    )
    print(f"skill evaluation verdict: {assessment.verdict}")
    return _print_risks(assessment.risks)


def _provider_list(args: argparse.Namespace) -> int:
    document = load_document(args.registry)
    providers = document.get("providers", [])
    if args.json:
        print(json.dumps(providers, ensure_ascii=False, indent=2))
        return 0
    print("provider\tapi_surface\tadapter_status")
    for provider in providers:
        print(f"{provider['provider']}\t{provider['api_surface']}\t{provider['adapter_status']}")
    return 0


def _provider_probe(args: argparse.Namespace) -> int:
    result = probe_provider_adapters(
        args.config,
        check_environment=args.check_environment,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    print(f"environment_checked\t{str(result['environment_checked']).lower()}")
    print("adapter\tprovider\tenabled\tcredential\tmodel\tlive_conformance")
    for adapter in result["adapters"]:
        print(
            f"{adapter['adapter_id']}\t{adapter['provider']}\t"
            f"{str(adapter['enabled']).lower()}\t{adapter['credential_status']}\t"
            f"{adapter['model_status']}\t{adapter['live_conformance']}"
        )
    print(result["note"])
    return 0


def _provider_conformance(args: argparse.Namespace) -> int:
    config = get_provider_adapter_config(args.config, args.adapter)
    checks = tuple(args.check) if args.check else None
    plan = conformance_plan(
        config,
        checks=checks,
        max_provider_invocations=args.max_provider_invocations,
        max_output_tokens=args.max_output_tokens,
    )
    if not args.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    if not args.execution_context:
        raise ValueError("--execute requires --execution-context")
    if not args.output:
        raise ValueError("--execute requires --output")
    provider = build_live_provider(config)
    report = run_provider_conformance(
        provider,
        adapter_id=config.adapter_id,
        execution_context=args.execution_context,
        checks=tuple(plan["checks"]),
        max_provider_invocations=args.max_provider_invocations,
        max_output_tokens=args.max_output_tokens,
    )
    document = report.to_mapping()
    schema_errors = SchemaCatalog().validate("provider_conformance_report", document)
    if schema_errors:
        first = schema_errors[0]
        raise ValueError(f"generated provider conformance report is invalid at {first.pointer}: {first.message}")
    _write_yaml(Path(args.output), document)
    print(
        f"provider conformance {report.status}: adapter={report.adapter_id} "
        f"invocations={report.budget.provider_invocations} output={args.output}"
    )
    return 0 if report.status == "passed" else 1


def _model_pool_probe(args: argparse.Namespace) -> int:
    pool = load_model_pool(args.config)
    environment = os.environ if args.check_environment else None
    report = pool.probe(environment=environment)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"pool\t{report['pool_id']}")
    print(f"selection_policy\t{report['selection_policy']}")
    print(f"environment_checked\t{str(report['environment_checked']).lower()}")
    print("slot\trole\tprovider_adapter\tenabled\tmodel")
    for slot in report["slots"]:
        print(
            f"{slot['slot_id']}\t{slot['role']}\t{slot['provider_adapter']}\t"
            f"{str(slot['enabled']).lower()}\t{slot['model_status']}"
        )
    return 0


def _schema_list(args: argparse.Namespace) -> int:
    catalog = SchemaCatalog(args.root, args.version)
    for name in catalog.names:
        marker = "document" if catalog.schema(name).get("x-rwb-document-kind") else "shared"
        print(f"{name}\t{marker}")
    return 0


def _schema_show(args: argparse.Namespace) -> int:
    catalog = SchemaCatalog(args.root, args.version)
    print(json.dumps(catalog.schema(args.name), ensure_ascii=False, indent=2))
    return 0


def _task_resolve(args: argparse.Namespace) -> int:
    task = TaskPacket.from_mapping(_load_valid(args.task, "task_packet"))
    profile = AgentProfile.from_mapping(_load_valid(args.profile, "agent_profile"))
    try:
        if args.registry:
            if args.skill:
                raise ValueError("use either --registry or --skill, not both")
            registry = AcceptedSkillRegistry.load(args.registry, project_root=args.root)
            resolved = resolve_task_from_registry(
                task,
                profile,
                registry,
                allow_auto_select=args.auto_select,
                resolution_purpose=(
                    "historical-replay" if args.historical_replay else "new-assignment"
                ),
            )
        else:
            if not args.skill:
                raise ValueError("task resolution requires --registry or at least one --skill")
            skills = [SkillManifest.from_mapping(_load_valid(path, "skill_manifest")) for path in args.skill]
            resolved = resolve_task(task, profile, skills)
    except (KeyError, ResolutionError) as exc:
        if isinstance(exc, KeyError):
            print(f"BLOCK   SKILL-MISSING                {exc}")
            return 1
        return _print_risks(exc.risks)
    document = to_plain(resolved)
    if args.output:
        _write_yaml(Path(args.output), document)
        print(f"assignment {resolved.assignment_id} written to {args.output}")
    else:
        print(json.dumps(document, ensure_ascii=False, indent=2))
    return 0


def _runtime_codex_validate(args: argparse.Namespace) -> int:
    adapter = CodexRuntimeAdapter(args.root, platform_version=args.platform_version)
    issues = adapter.validate_project_layout()
    for issue in issues:
        print(f"ERROR   CODEX-LAYOUT                 {issue}")
    if issues:
        return 1
    print(json.dumps(to_plain(adapter.capabilities()), ensure_ascii=False, indent=2))
    return 0


def _runtime_codex_render(args: argparse.Namespace) -> int:
    task = TaskPacket.from_mapping(_load_valid(args.task, "task_packet"))
    profile = AgentProfile.from_mapping(_load_valid(args.profile, "agent_profile"))
    registry = AcceptedSkillRegistry.load(args.registry, project_root=args.root)
    try:
        assignment = resolve_task_from_registry(
            task,
            profile,
            registry,
            resolution_purpose=(
                "historical-replay" if args.historical_replay else "new-assignment"
            ),
        )
    except ResolutionError as exc:
        return _print_risks(exc.risks)
    adapter = CodexRuntimeAdapter(args.root, platform_version=args.platform_version)
    prompt = adapter.render_task_prompt(task, profile, assignment)
    if args.output:
        _write_text(Path(args.output), prompt)
        print(f"Codex dispatch prompt written to {args.output}")
    else:
        print(prompt, end="")
    return 0


def _handoff_validate(args: argparse.Namespace) -> int:
    handoff_document = _load_valid(args.handoff, "handoff_packet")
    handoff = HandoffPacket.from_mapping(handoff_document)
    root = Path(args.root).resolve()
    if not args.task:
        return _print_risks(_document_reference_risks(handoff_document, root))
    task = TaskPacket.from_mapping(_load_valid(args.task, "task_packet"))
    assignment_path = args.assignment or handoff.skill_assignment_ref
    assignment = None
    risks = []
    if args.assignment and handoff.skill_assignment_ref:
        supplied = (Path(args.root) / args.assignment).resolve()
        recorded = (Path(args.root) / handoff.skill_assignment_ref).resolve()
        if supplied != recorded:
            risks.append(
                ContractRisk(
                    "HANDOFF-ASSIGNMENT-REF-DRIFT",
                    RiskLevel.BLOCK,
                    "supplied Assignment differs from the Handoff Assignment reference",
                )
            )
    if assignment_path:
        assignment_document = _load_valid(root / assignment_path, "skill_assignment")
        assignment = ResolvedTask.from_mapping(assignment_document)
        risks.extend(_document_reference_risks(assignment_document, root))
    if handoff.execution_receipt_ref:
        receipt_path = resolve_within_root(root, handoff.execution_receipt_ref)
        if receipt_path is None or not receipt_path.is_file():
            risks.append(
                ContractRisk(
                    "HANDOFF-RECEIPT-MISSING",
                    RiskLevel.BLOCK,
                    f"Execution Receipt does not exist: {handoff.execution_receipt_ref}",
                )
            )
        else:
            receipt = ExecutionReceipt.from_mapping(_load_valid(receipt_path, "execution_receipt"))
            handoff_ref = _project_relative(args.handoff, root, "handoff")
            if receipt.task_id != handoff.task_id or receipt.status != handoff.status:
                risks.append(
                    ContractRisk(
                        "HANDOFF-RECEIPT-DRIFT",
                        RiskLevel.BLOCK,
                        "Execution Receipt task or status differs from Handoff",
                    )
                )
            if handoff_ref not in receipt.output_refs:
                risks.append(
                    ContractRisk(
                        "HANDOFF-RECEIPT-BACKREF",
                        RiskLevel.BLOCK,
                        "Execution Receipt does not list this Handoff as an output",
                    )
                )
    risks.extend(
        check_handoff_against_task(
            task,
            handoff,
            project_root=args.root,
            assignment=assignment,
        )
    )
    return _print_risks(risks)


def _handoff_audit_transfer(args: argparse.Namespace) -> int:
    audit = _load_valid(args.audit, "handoff_transfer_audit")
    assessment = assess_handoff_transfer(audit, root=args.root)
    print(
        f"handoff transfer verdict: {assessment.verdict} "
        f"review_required={str(assessment.review_required).lower()}"
    )
    return _print_risks(assessment.risks)


def _reference_check(args: argparse.Namespace) -> int:
    document = load_document(args.document)
    return _print_risks(_document_reference_risks(document, Path(args.root).resolve()))


def _claim_trace(args: argparse.Namespace) -> int:
    document = load_document(args.claim)
    if not isinstance(document, Mapping):
        print("ERROR   DOCUMENT-INVALID              claim document must be an object")
        return 1
    errors = SchemaCatalog().validate("research_object", document)
    if errors or document.get("object_type") != "claim":
        for error in errors:
            print(f"ERROR   SCHEMA-INVALID               {error.pointer}: {error.message}")
        if document.get("object_type") != "claim":
            print("ERROR   OBJECT-NOT-CLAIM             document object_type is not claim")
        return 1
    trace = {
        "claim_id": document["object_id"],
        "revision": document["revision"],
        "strength": document["strength"],
        "support_refs": document["support_refs"],
        "counterevidence_refs": document["counterevidence_refs"],
        "limitations": document["limitations"],
    }
    print(json.dumps(trace, ensure_ascii=False, indent=2))
    if args.protocol:
        protocol = ProjectProtocol.from_mapping(_load_valid(args.protocol, "project_protocol"))
        return _print_risks(check_claim_ceiling(protocol, str(document["strength"])))
    return 0


def _project_relative(path: str | Path, root: Path, field: str) -> str:
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError(f"{field} must be within --root") from exc


def _parse_context_metrics(values: Sequence[str]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for raw in values:
        name, separator, raw_value = raw.partition("=")
        if not separator or name not in CONTEXT_METRIC_NAMES:
            known = ", ".join(CONTEXT_METRIC_NAMES)
            raise ValueError(f"--metric must be NAME=VALUE using one of: {known}")
        if name in metrics:
            raise ValueError(f"duplicate context metric: {name}")
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"context metric {name!r} must be an integer") from exc
        if value < 0:
            raise ValueError(f"context metric {name!r} must be non-negative")
        metrics[name] = value
    return metrics


def _context_assess(args: argparse.Namespace) -> int:
    protocol = ProjectProtocol.from_mapping(_load_valid(args.protocol, "project_protocol"))
    metrics = _parse_context_metrics(args.metric)
    explicit_unknown = tuple(args.unknown)
    invalid_unknown = sorted(set(explicit_unknown) - set(CONTEXT_METRIC_NAMES))
    if invalid_unknown:
        raise ValueError(f"unknown context metrics: {', '.join(invalid_unknown)}")
    overlap = sorted(set(metrics) & set(explicit_unknown))
    if overlap:
        raise ValueError(f"metrics cannot be both measured and unknown: {', '.join(overlap)}")
    unknown = tuple(
        name for name in CONTEXT_METRIC_NAMES if name not in metrics
    )
    if args.context_budget_status == "unavailable":
        budget = ContextBudgetEstimate("unavailable")
    else:
        budget = ContextBudgetEstimate.from_mapping(
            {
                "status": args.context_budget_status,
                "unit": args.context_budget_unit,
                "remaining": args.remaining_context,
                "next_atomic_cost": args.next_atomic_cost,
                "closeout_cost": args.closeout_cost,
                "safety_margin": args.safety_margin,
            }
        )
    handoff_ready = {"yes": True, "no": False, "unknown": None}[args.handoff_ready]
    snapshot = ContextSnapshot.create(
        snapshot_id=args.id,
        captured_at=args.captured_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        scope=args.scope,
        owner_ref=args.owner_ref,
        measurement_source=args.measurement_source,
        metrics=metrics,
        unknown_metrics=unknown,
        handoff_ready=handoff_ready,
        context_budget=budget,
        handoff_audit_ref=args.handoff_audit_ref,
        policy=ContextPolicySnapshot.from_project_policy(protocol.context_policy),
    )
    document = snapshot.to_mapping()
    errors = SchemaCatalog().validate("context_snapshot", document)
    if errors:
        rendered = "; ".join(f"{error.pointer}: {error.message}" for error in errors[:5])
        raise ValueError(f"generated Context Snapshot failed schema validation: {rendered}")
    if args.output:
        _write_yaml(Path(args.output), document)
        print(f"context snapshot {args.id!r} written to {args.output}")
    else:
        print(json.dumps(document, ensure_ascii=False, indent=2))
    return 1 if snapshot.assessment.level == "block" else 0


def _context_resume_check(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    state_document = _load_valid(args.state, "main_state")
    state = MainStatePacket.from_mapping(state_document)
    protocol_path = Path(args.protocol)
    protocol = ProjectProtocol.from_mapping(_load_valid(protocol_path, "project_protocol"))
    expected_protocol = f"{_project_relative(protocol_path, root, 'protocol')}@{protocol.revision}"
    risks = list(_document_reference_risks(state_document, root))
    if state.checkpoint_digest is None:
        risks.append(
            ContractRisk(
                "STATE-DIGEST-MISSING",
                RiskLevel.BLOCK,
                "Main State must carry a canonical checkpoint_digest before resume",
            )
        )
    if state.project_protocol_ref != expected_protocol:
        risks.append(
            ContractRisk(
                "STATE-PROTOCOL-DRIFT",
                RiskLevel.BLOCK,
                f"Main State pins {state.project_protocol_ref!r}, current protocol is {expected_protocol!r}",
            )
        )
    if state.current_questions != protocol.question_refs:
        risks.append(
            ContractRisk(
                "STATE-QUESTION-DRIFT",
                RiskLevel.BLOCK,
                "Main State questions differ from the pinned Project Protocol",
            )
        )
    if not state.next_actions:
        risks.append(
            ContractRisk(
                "STATE-NEXT-ACTION-MISSING",
                RiskLevel.BLOCK,
                "resume requires at least one bounded next action",
            )
        )
    if state.continuity_status == "safe-paused" and not state.rollover_reason:
        risks.append(
            ContractRisk(
                "STATE-SAFE-PAUSE-REASON-MISSING",
                RiskLevel.BLOCK,
                "safe-paused state must explain why work stopped",
            )
        )
    if state.git_head:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        actual_head = completed.stdout.strip().lower() if completed.returncode == 0 else None
        if actual_head is None:
            risks.append(
                ContractRisk(
                    "RESUME-GIT-UNAVAILABLE",
                    RiskLevel.BLOCK,
                    "Main State pins a Git HEAD but the current project cannot resolve HEAD",
                )
            )
        elif actual_head != state.git_head:
            risks.append(
                ContractRisk(
                    "RESUME-CONFLICT-GIT",
                    RiskLevel.BLOCK,
                    f"Main State pins Git HEAD {state.git_head}, current HEAD is {actual_head}",
                )
            )
    for active in state.active_tasks:
        if active.status in {"ready", "running"} and active.expected_handoff is None:
            risks.append(
                ContractRisk(
                    "STATE-HANDOFF-EXPECTED",
                    RiskLevel.BLOCK,
                    f"active Task {active.task_id!r} has no expected_handoff",
                )
            )
    if state.context_snapshot_ref is None:
        risks.append(
            ContractRisk(
                "STATE-CONTEXT-SNAPSHOT-MISSING",
                RiskLevel.BLOCK,
                "resume requires the pre-rollover Context Snapshot",
            )
        )
    else:
        snapshot_path = resolve_within_root(root, state.context_snapshot_ref)
        if snapshot_path is not None and snapshot_path.is_file():
            snapshot = ContextSnapshot.from_mapping(_load_valid(snapshot_path, "context_snapshot"))
            if snapshot.scope != "main":
                risks.append(
                    ContractRisk(
                        "STATE-CONTEXT-SCOPE",
                        RiskLevel.BLOCK,
                        "Main State must reference a main-scope Context Snapshot",
                    )
                )
            if snapshot.assessment.level == "block":
                risks.append(
                    ContractRisk(
                        "STATE-CONTEXT-BLOCKED",
                        RiskLevel.BLOCK,
                        "blocking context condition was not repaired before resume",
                    )
                )
            if snapshot.assessment.level in {"warn", "rollover"} and not state.rollover_reason:
                risks.append(
                    ContractRisk(
                        "STATE-ROLLOVER-REASON-MISSING",
                        RiskLevel.BLOCK,
                        "pressure-triggered checkpoint must explain its rollover reason",
                    )
                )
    if state.previous_checkpoint_ref:
        previous_path = resolve_within_root(root, state.previous_checkpoint_ref)
        if previous_path is not None and previous_path.is_file():
            previous = MainStatePacket.from_mapping(_load_valid(previous_path, "main_state"))
            lost_constraints = sorted(set(previous.pinned_constraints) - set(state.pinned_constraints))
            lost_decisions = sorted(set(previous.accepted_decisions) - set(state.accepted_decisions))
            if lost_constraints:
                risks.append(
                    ContractRisk(
                        "STATE-CONSTRAINT-LOSS",
                        RiskLevel.BLOCK,
                        "checkpoint dropped pinned constraints: " + "; ".join(lost_constraints),
                    )
                )
            if lost_decisions:
                risks.append(
                    ContractRisk(
                        "STATE-DECISION-LOSS",
                        RiskLevel.BLOCK,
                        "checkpoint dropped accepted decisions: " + "; ".join(lost_decisions),
                    )
                )
    return _print_risks(risks)


def _execution_assess(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    receipt_path = Path(args.receipt)
    receipt = ExecutionReceipt.from_mapping(_load_valid(receipt_path, "execution_receipt"))
    protocol = ProjectProtocol.from_mapping(_load_valid(args.protocol, "project_protocol"))
    receipt_ref = _project_relative(receipt_path, root, "receipt")
    return _print_risks(
        check_execution_receipt(receipt, protocol, root=root, receipt_ref=receipt_ref)
    )


def _trace_validate(args: argparse.Namespace) -> int:
    from research_workbench.observability.trace import validate_attempt_trace

    return _print_risks(validate_attempt_trace(args.root, args.attempt).risks)


def _trace_export_schema(args: argparse.Namespace) -> int:
    from research_workbench.observability.trace import TRACE_BASELINE
    from research_workbench.observability.trace_schema import export_trace_schema_bundle

    manifest_path = export_trace_schema_bundle(args.out, schema_version=args.schema_version)
    print(f"baseline\t{TRACE_BASELINE}")
    print(f"manifest\t{manifest_path}")
    return 0


def _execute_verify(args: argparse.Namespace) -> int:
    from research_workbench.execution import verify_execution_archive

    return _print_risks(
        verify_execution_archive(
            args.attempt,
            root=args.root,
            protocol=args.protocol,
        )
    )


def _execute_recovery_check(args: argparse.Namespace) -> int:
    from research_workbench.execution import prepare_recovery_attempt

    result = prepare_recovery_attempt(
        root=args.root,
        previous_attempt_dir=args.previous_attempt,
        main_state=args.main_state,
        protocol=args.protocol,
        new_attempt_id=args.new_attempt_id,
        new_attempt_dir=args.new_attempt_dir,
    )
    return _print_risks(result.risks)


def _context_checkpoint(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol = ProjectProtocol.from_mapping(_load_valid(protocol_path, "project_protocol"))
    root = Path(args.root).resolve()
    relative_protocol = _project_relative(protocol_path, root, "protocol")
    base: Mapping[str, Any] = {}
    if args.from_state:
        base = _load_valid(args.from_state, "main_state")
        MainStatePacket.from_mapping(base)
    constraints = list(base.get("pinned_constraints", [])) + list(args.constraint)
    if protocol.data_boundary.get("local_only"):
        if "local data must not be uploaded" not in constraints:
            constraints.append("local data must not be uploaded")
    claim_constraint = "claim ceiling: " + ", ".join(protocol.claim_ceiling)
    if claim_constraint not in constraints:
        constraints.append(claim_constraint)
    risks = list(base.get("open_risks", [])) + list(args.risk)
    snapshot_ref = None
    if args.snapshot:
        snapshot_ref = _project_relative(args.snapshot, root, "snapshot")
        snapshot = ContextSnapshot.from_mapping(_load_valid(args.snapshot, "context_snapshot"))
        if snapshot.scope != "main":
            raise ValueError("checkpoint snapshot must have scope=main")
        for rule in snapshot.assessment.triggered_rules:
            if rule not in risks:
                risks.append(rule)
    previous_ref = None
    if args.previous_checkpoint:
        previous_ref = _project_relative(args.previous_checkpoint, root, "previous checkpoint")
    elif args.from_state:
        previous_ref = _project_relative(args.from_state, root, "from-state")
    next_actions = list(base.get("next_actions", [])) + list(args.next_action)
    if not next_actions:
        raise ValueError("checkpoint requires at least one --next-action or a prior next action")
    machine_refs_by_path: dict[str, Mapping[str, Any]] = {
        str(item.get("path")): item
        for item in base.get("machine_state_refs", [])
        if isinstance(item, Mapping) and isinstance(item.get("path"), str)
    }

    def freeze_machine_state(raw_path: str | Path) -> None:
        path = Path(raw_path)
        relative = _project_relative(path, root, "machine state")
        resolved = resolve_within_root(root, relative)
        if resolved is None or not resolved.is_file():
            raise ValueError(f"machine state reference does not exist: {relative}")
        machine_refs_by_path[relative] = {"path": relative, "sha256": hash_file(resolved)}

    freeze_machine_state(protocol_path)
    if args.snapshot:
        freeze_machine_state(args.snapshot)
    for raw_ref in args.machine_state_ref:
        freeze_machine_state(raw_ref)

    document = {
        "schema_version": "0.1.0",
        "checkpoint_id": args.id,
        "continuity_status": args.continuity_status,
        "project_protocol_ref": f"{relative_protocol}@{protocol.revision}",
        "current_questions": list(protocol.question_refs),
        "pinned_constraints": constraints,
        "accepted_decisions": list(base.get("accepted_decisions", [])) + list(args.decision),
        "active_tasks": list(base.get("active_tasks", [])),
        "recent_handoffs": list(base.get("recent_handoffs", [])),
        "open_conflicts": list(base.get("open_conflicts", [])),
        "open_risks": risks,
        "next_actions": next_actions,
        "artifact_index_refs": list(base.get("artifact_index_refs", [])),
        "machine_state_refs": [machine_refs_by_path[path] for path in sorted(machine_refs_by_path)],
        "rollover_reason": args.rollover_reason,
        "created_at": args.created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if previous_ref:
        document["previous_checkpoint_ref"] = previous_ref
    if snapshot_ref:
        document["context_snapshot_ref"] = snapshot_ref
    if args.capture_git_head:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ValueError("cannot capture Git HEAD from the checkpoint root")
        document["git_head"] = completed.stdout.strip().lower()
    document["checkpoint_digest"] = checkpoint_digest(document)
    errors = SchemaCatalog().validate("main_state", document)
    if errors:
        raise ValueError("generated checkpoint failed schema validation")
    MainStatePacket.from_mapping(document)
    _write_yaml(Path(args.output), document)
    print(f"checkpoint {args.id!r} written to {args.output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rwb", description="Research Agent Workbench utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="initialize a minimal file-first project")
    init_parser.add_argument("path")
    init_parser.add_argument("--project-id")
    init_parser.set_defaults(handler=_init_project)

    validate = subparsers.add_parser("validate", help="run schema, deterministic, and reference checks")
    validate.add_argument("paths", nargs="+", help="document files or directories")
    validate.add_argument("--root", default=".", help="project root for repository-relative references")
    validate.add_argument("--structure-only", action="store_true", help="skip live file/hash checks")
    validate.set_defaults(handler=_validate)

    hash_parser = subparsers.add_parser("hash", help="calculate a SHA-256 content identifier")
    hash_parser.add_argument("path")
    hash_parser.set_defaults(handler=_hash)

    schema_parser = subparsers.add_parser("schema", help="inspect versioned JSON Schemas")
    schema_subparsers = schema_parser.add_subparsers(dest="schema_command", required=True)
    schema_list = schema_subparsers.add_parser("list")
    schema_list.add_argument("--root")
    schema_list.add_argument("--version", default="0.1.0")
    schema_list.set_defaults(handler=_schema_list)
    schema_show = schema_subparsers.add_parser("show")
    schema_show.add_argument("name")
    schema_show.add_argument("--root")
    schema_show.add_argument("--version", default="0.1.0")
    schema_show.set_defaults(handler=_schema_show)

    skills = subparsers.add_parser("skills", help="inspect the skill candidate registry")
    skill_subparsers = skills.add_subparsers(dest="skills_command", required=True)
    candidates = skill_subparsers.add_parser("candidates", help="list or filter candidates")
    candidates.add_argument("--registry", default=str(DEFAULT_CANDIDATES))
    candidates.add_argument("--status")
    candidates.add_argument("--mode")
    candidates.add_argument("--capability")
    candidates.add_argument("--json", action="store_true")
    candidates.set_defaults(handler=_skill_candidates)
    accepted = skill_subparsers.add_parser("accepted", help="validate and list accepted repository Skills")
    accepted.add_argument("--registry", default=str(DEFAULT_ACCEPTED))
    accepted.add_argument("--root", default=".")
    accepted.add_argument("--json", action="store_true")
    accepted.set_defaults(handler=_skill_accepted)
    archive_audit = skill_subparsers.add_parser(
        "audit-archive",
        help="statically audit Skill packages in a ZIP without extracting or executing them",
    )
    archive_audit.add_argument("archive")
    archive_audit.add_argument("--source-id", required=True)
    archive_audit.add_argument("--expected-sha256", required=True)
    archive_audit.add_argument("--registry", default=str(DEFAULT_CANDIDATES))
    archive_audit.add_argument("--generated-at")
    archive_audit.add_argument("--output")
    archive_audit.set_defaults(handler=_skill_audit_archive)
    skill_eval = skill_subparsers.add_parser(
        "eval",
        help="assess whether paired Skill evidence is ready for a human admission decision",
    )
    skill_eval_subparsers = skill_eval.add_subparsers(dest="skill_eval_command", required=True)
    skill_eval_assess = skill_eval_subparsers.add_parser(
        "assess",
        help="check paired outputs, receipts, context, blind review, and case coverage",
    )
    skill_eval_assess.add_argument("evaluation")
    skill_eval_assess.add_argument("--root", default=".")
    skill_eval_assess.add_argument("--registry", default=str(DEFAULT_CANDIDATES))
    skill_eval_assess.set_defaults(handler=_skill_eval_assess)

    providers = subparsers.add_parser("providers", help="inspect model provider baselines")
    provider_subparsers = providers.add_subparsers(dest="providers_command", required=True)
    provider_list = provider_subparsers.add_parser("list")
    provider_list.add_argument("--registry", default="registry/providers/capabilities.json")
    provider_list.add_argument("--json", action="store_true")
    provider_list.set_defaults(handler=_provider_list)
    provider_probe = provider_subparsers.add_parser(
        "probe",
        help="validate non-secret adapter config and optionally check environment presence",
    )
    provider_probe.add_argument("--config", default="registry/providers/adapters.yaml")
    provider_probe.add_argument(
        "--check-environment",
        action="store_true",
        help="explicitly check named variables in the current process without printing values",
    )
    provider_probe.add_argument("--json", action="store_true")
    provider_probe.set_defaults(handler=_provider_probe)
    provider_conformance = provider_subparsers.add_parser(
        "conformance",
        help="plan or explicitly execute bounded synthetic provider checks",
    )
    provider_conformance.add_argument("--config", default="registry/providers/adapters.yaml")
    provider_conformance.add_argument("--adapter", required=True)
    provider_conformance.add_argument(
        "--check",
        action="append",
        choices=("text", "structured", "tools"),
        help="check to run; repeat to select multiple (default: all claimed checks)",
    )
    provider_conformance.add_argument("--max-provider-invocations", type=int, default=3)
    provider_conformance.add_argument("--max-output-tokens", type=int, default=64)
    provider_conformance.add_argument(
        "--execute",
        action="store_true",
        help="perform live network requests; without this flag the command is a zero-environment dry run",
    )
    provider_conformance.add_argument(
        "--execution-context",
        help="human assertion describing the real authorization context; required with --execute",
    )
    provider_conformance.add_argument("--output", help="new YAML report path; required with --execute")
    provider_conformance.set_defaults(handler=_provider_conformance)

    models = subparsers.add_parser("models", help="inspect the explicit local model pool")
    model_subparsers = models.add_subparsers(dest="models_command", required=True)
    model_probe = model_subparsers.add_parser(
        "probe",
        help="validate model slots without choosing, ranking, or calling a model",
    )
    model_probe.add_argument("--config", default="registry/models/pool.example.yaml")
    model_probe.add_argument(
        "--check-environment",
        action="store_true",
        help="explicitly check named model variables without printing their values",
    )
    model_probe.add_argument("--json", action="store_true")
    model_probe.set_defaults(handler=_model_pool_probe)

    task = subparsers.add_parser("task", help="resolve Task/Profile/Skill bindings")
    task_subparsers = task.add_subparsers(dest="task_command", required=True)
    task_resolve = task_subparsers.add_parser("resolve")
    task_resolve.add_argument("task")
    task_resolve.add_argument("--profile", required=True)
    task_resolve.add_argument("--skill", action="append", default=[])
    task_resolve.add_argument("--registry")
    task_resolve.add_argument("--root", default=".")
    task_resolve.add_argument("--auto-select", action="store_true")
    task_resolve.add_argument(
        "--historical-replay",
        action="store_true",
        help="resolve exact legacy/deprecated Skill versions for an intentional historical replay",
    )
    task_resolve.add_argument("--output")
    task_resolve.set_defaults(handler=_task_resolve)

    runtime = subparsers.add_parser("runtime", help="inspect native runtime mappings")
    runtime_subparsers = runtime.add_subparsers(dest="runtime_command", required=True)
    codex = runtime_subparsers.add_parser("codex", help="inspect the Codex native adapter")
    codex_subparsers = codex.add_subparsers(dest="codex_command", required=True)
    codex_validate = codex_subparsers.add_parser("validate")
    codex_validate.add_argument("--root", default=".")
    codex_validate.add_argument("--platform-version", default="unprobed")
    codex_validate.set_defaults(handler=_runtime_codex_validate)
    codex_render = codex_subparsers.add_parser("render")
    codex_render.add_argument("task")
    codex_render.add_argument("--profile", required=True)
    codex_render.add_argument("--registry", default=str(DEFAULT_ACCEPTED))
    codex_render.add_argument("--root", default=".")
    codex_render.add_argument("--platform-version", default="unprobed")
    codex_render.add_argument(
        "--historical-replay",
        action="store_true",
        help="render an intentional replay using exact legacy/deprecated Skill versions",
    )
    codex_render.add_argument("--output")
    codex_render.set_defaults(handler=_runtime_codex_render)

    handoff = subparsers.add_parser("handoff", help="validate Handoff structure and locks")
    handoff_subparsers = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_validate = handoff_subparsers.add_parser("validate")
    handoff_validate.add_argument("handoff")
    handoff_validate.add_argument("--task")
    handoff_validate.add_argument("--assignment")
    handoff_validate.add_argument("--root", default=".")
    handoff_validate.set_defaults(handler=_handoff_validate)
    handoff_audit = handoff_subparsers.add_parser(
        "audit-transfer",
        help="check manifest coverage and bounded semantic review for a compressed Handoff",
    )
    handoff_audit.add_argument("audit")
    handoff_audit.add_argument("--root", default=".")
    handoff_audit.set_defaults(handler=_handoff_audit_transfer)

    reference = subparsers.add_parser("reference", help="check live file and hash references")
    reference_subparsers = reference.add_subparsers(dest="reference_command", required=True)
    reference_check = reference_subparsers.add_parser("check")
    reference_check.add_argument("document")
    reference_check.add_argument("--root", default=".")
    reference_check.set_defaults(handler=_reference_check)

    claim = subparsers.add_parser("claim", help="inspect Claim support and counterevidence")
    claim_subparsers = claim.add_subparsers(dest="claim_command", required=True)
    claim_trace = claim_subparsers.add_parser("trace")
    claim_trace.add_argument("claim")
    claim_trace.add_argument("--protocol")
    claim_trace.set_defaults(handler=_claim_trace)

    trace = subparsers.add_parser("trace", help="validate a file-authoritative Attempt trace")
    trace_subparsers = trace.add_subparsers(dest="trace_command", required=True)
    trace_validate = trace_subparsers.add_parser("validate")
    trace_validate.add_argument("--attempt", required=True, help="Attempt directory or INDEX.yaml")
    trace_validate.add_argument("--root", default=".")
    trace_validate.set_defaults(handler=_trace_validate)
    trace_export = trace_subparsers.add_parser(
        "export-schema",
        help="export the trace JSON Schemas as a baseline-bound bundle for external consumers",
    )
    trace_export.add_argument("--out", required=True, help="fresh target directory for the bundle")
    trace_export.add_argument("--schema-version", default="0.1.0")
    trace_export.set_defaults(handler=_trace_export_schema)

    execute = subparsers.add_parser("execute", help="verify a committed execution archive")
    execute_subparsers = execute.add_subparsers(dest="execute_command", required=True)
    execute_verify = execute_subparsers.add_parser("verify")
    execute_verify.add_argument("--attempt", required=True)
    execute_verify.add_argument("--protocol", required=True)
    execute_verify.add_argument("--root", default=".")
    execute_verify.set_defaults(handler=_execute_verify)
    execute_recovery = execute_subparsers.add_parser("recovery-check")
    execute_recovery.add_argument("--previous-attempt", required=True)
    execute_recovery.add_argument("--main-state", required=True)
    execute_recovery.add_argument("--new-attempt-id", required=True)
    execute_recovery.add_argument("--new-attempt-dir", required=True)
    execute_recovery.add_argument("--protocol", required=True)
    execute_recovery.add_argument("--root", default=".")
    execute_recovery.set_defaults(handler=_execute_recovery_check)

    context = subparsers.add_parser("context", help="create and validate recoverable Main State")
    context_subparsers = context.add_subparsers(dest="context_command", required=True)
    assess = context_subparsers.add_parser("assess", help="record deterministic context-pressure proxies")
    assess.add_argument("--id", required=True)
    assess.add_argument("--protocol", required=True)
    assess.add_argument("--scope", choices=("main", "task"), required=True)
    assess.add_argument("--owner-ref")
    assess.add_argument(
        "--measurement-source",
        choices=("runtime", "manual", "file-estimate", "mixed"),
        default="manual",
    )
    assess.add_argument("--metric", action="append", default=[], metavar="NAME=VALUE")
    assess.add_argument("--unknown", action="append", default=[], metavar="NAME")
    assess.add_argument(
        "--context-budget-status",
        choices=("measured", "estimated", "unavailable"),
        default="unavailable",
    )
    assess.add_argument("--context-budget-unit", choices=("tokens", "characters"))
    assess.add_argument("--remaining-context", type=int)
    assess.add_argument("--next-atomic-cost", type=int)
    assess.add_argument("--closeout-cost", type=int)
    assess.add_argument("--safety-margin", type=int)
    assess.add_argument("--handoff-ready", choices=("yes", "no", "unknown"), default="unknown")
    assess.add_argument(
        "--handoff-audit-ref",
        help="project-relative Handoff Transfer Audit required for a compacted handoff-ready task",
    )
    assess.add_argument(
        "--captured-at",
    )
    assess.add_argument("--output")
    assess.set_defaults(handler=_context_assess)
    checkpoint = context_subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--id", required=True)
    checkpoint.add_argument("--protocol", required=True)
    checkpoint.add_argument("--output", required=True)
    checkpoint.add_argument("--root", default=".")
    checkpoint.add_argument("--next-action", action="append", default=[])
    checkpoint.add_argument("--risk", action="append", default=[])
    checkpoint.add_argument("--constraint", action="append", default=[])
    checkpoint.add_argument("--decision", action="append", default=[])
    checkpoint.add_argument("--from-state")
    checkpoint.add_argument("--previous-checkpoint")
    checkpoint.add_argument("--snapshot")
    checkpoint.add_argument(
        "--continuity-status",
        choices=("active", "stage-completed", "safe-paused", "waiting", "blocked"),
        default="active",
    )
    checkpoint.add_argument("--machine-state-ref", action="append", default=[])
    checkpoint.add_argument("--capture-git-head", action="store_true")
    checkpoint.add_argument("--rollover-reason", default="manual checkpoint")
    checkpoint.add_argument(
        "--created-at",
    )
    checkpoint.set_defaults(handler=_context_checkpoint)
    resume = context_subparsers.add_parser("resume-check", help="verify a checkpoint can safely seed a new main session")
    resume.add_argument("state")
    resume.add_argument("--protocol", required=True)
    resume.add_argument("--root", default=".")
    resume.set_defaults(handler=_context_resume_check)

    execution = subparsers.add_parser("execution", help="validate cost, context, trace, and delegation receipts")
    execution_subparsers = execution.add_subparsers(dest="execution_command", required=True)
    execution_assess = execution_subparsers.add_parser("assess")
    execution_assess.add_argument("receipt")
    execution_assess.add_argument("--protocol", required=True)
    execution_assess.add_argument("--root", default=".")
    execution_assess.set_defaults(handler=_execution_assess)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (ContractError, OSError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
