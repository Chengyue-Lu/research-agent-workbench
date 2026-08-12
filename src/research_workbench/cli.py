from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from research_workbench.artifacts.integrity import hash_file, resolve_within_root
from research_workbench.capability import (
    AgentProfile,
    ResolutionError,
    SkillManifest,
    filter_candidates,
    load_candidates,
    resolve_task,
)
from research_workbench.capability.catalog import DEFAULT_CANDIDATES
from research_workbench.context import MainStatePacket
from research_workbench.contracts import ContractError, ContractRisk, RiskLevel, to_plain
from research_workbench.io import iter_documents, load_document
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
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        yaml.safe_dump(dict(document), stream, sort_keys=False, allow_unicode=True)


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
    if kind == "task_packet":
        references = TaskPacket.from_mapping(document).input_refs
    elif kind == "handoff_packet":
        handoff = HandoffPacket.from_mapping(document)
        references = handoff.input_lock
        path_only.extend(handoff.artifact_refs)
        path_only.extend(handoff.validation_refs)
    elif kind == "skill_manifest":
        skill = SkillManifest.from_mapping(document)
        if skill.source_locator and not skill.source_locator.startswith(("http://", "https://")):
            references = (
                FileReference(skill.source_locator, skill.source_content_hash.removeprefix("sha256:")),
            )
    elif kind == "attempt":
        attempt = AttemptRecord.from_mapping(document)
        references = attempt.input_lock
        path_only.extend(attempt.artifact_refs)
        if attempt.handoff_ref:
            path_only.append(attempt.handoff_ref)
    elif kind == "main_state":
        state = MainStatePacket.from_mapping(document)
        path_only.extend(item.ref for item in state.recent_handoffs)
        path_only.extend(state.artifact_index_refs)
    risks = check_references(root, references)
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
    skills = [SkillManifest.from_mapping(_load_valid(path, "skill_manifest")) for path in args.skill]
    try:
        resolved = resolve_task(task, profile, skills)
    except ResolutionError as exc:
        return _print_risks(exc.risks)
    print(json.dumps(to_plain(resolved), ensure_ascii=False, indent=2))
    return 0


def _handoff_validate(args: argparse.Namespace) -> int:
    handoff_document = _load_valid(args.handoff, "handoff_packet")
    handoff = HandoffPacket.from_mapping(handoff_document)
    if not args.task:
        return _print_risks(_document_reference_risks(handoff_document, Path(args.root).resolve()))
    task = TaskPacket.from_mapping(_load_valid(args.task, "task_packet"))
    return _print_risks(check_handoff_against_task(task, handoff, project_root=args.root))


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


def _context_checkpoint(args: argparse.Namespace) -> int:
    protocol_path = Path(args.protocol)
    protocol = ProjectProtocol.from_mapping(_load_valid(protocol_path, "project_protocol"))
    root = Path(args.root).resolve()
    try:
        relative_protocol = protocol_path.resolve().relative_to(root).as_posix()
    except ValueError as exc:
        raise ValueError("protocol must be within --root") from exc
    constraints = list(args.constraint)
    if protocol.data_boundary.get("local_only"):
        constraints.append("local data must not be uploaded")
    constraints.append("claim ceiling: " + ", ".join(protocol.claim_ceiling))
    document = {
        "schema_version": "0.1.0",
        "checkpoint_id": args.id,
        "project_protocol_ref": f"{relative_protocol}@{protocol.revision}",
        "current_questions": list(protocol.question_refs),
        "pinned_constraints": constraints,
        "accepted_decisions": [],
        "active_tasks": [],
        "recent_handoffs": [],
        "open_conflicts": [],
        "open_risks": list(args.risk),
        "next_actions": list(args.next_action),
        "artifact_index_refs": [],
        "rollover_reason": args.rollover_reason,
    }
    errors = SchemaCatalog().validate("main_state", document)
    if errors:
        raise ValueError("generated checkpoint failed schema validation")
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

    providers = subparsers.add_parser("providers", help="inspect model provider baselines")
    provider_subparsers = providers.add_subparsers(dest="providers_command", required=True)
    provider_list = provider_subparsers.add_parser("list")
    provider_list.add_argument("--registry", default="registry/providers/capabilities.json")
    provider_list.add_argument("--json", action="store_true")
    provider_list.set_defaults(handler=_provider_list)

    task = subparsers.add_parser("task", help="resolve Task/Profile/Skill bindings")
    task_subparsers = task.add_subparsers(dest="task_command", required=True)
    task_resolve = task_subparsers.add_parser("resolve")
    task_resolve.add_argument("task")
    task_resolve.add_argument("--profile", required=True)
    task_resolve.add_argument("--skill", action="append", required=True)
    task_resolve.set_defaults(handler=_task_resolve)

    handoff = subparsers.add_parser("handoff", help="validate Handoff structure and locks")
    handoff_subparsers = handoff.add_subparsers(dest="handoff_command", required=True)
    handoff_validate = handoff_subparsers.add_parser("validate")
    handoff_validate.add_argument("handoff")
    handoff_validate.add_argument("--task")
    handoff_validate.add_argument("--root", default=".")
    handoff_validate.set_defaults(handler=_handoff_validate)

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

    context = subparsers.add_parser("context", help="create and validate recoverable Main State")
    context_subparsers = context.add_subparsers(dest="context_command", required=True)
    checkpoint = context_subparsers.add_parser("checkpoint")
    checkpoint.add_argument("--id", required=True)
    checkpoint.add_argument("--protocol", required=True)
    checkpoint.add_argument("--output", required=True)
    checkpoint.add_argument("--root", default=".")
    checkpoint.add_argument("--next-action", action="append", default=[])
    checkpoint.add_argument("--risk", action="append", default=[])
    checkpoint.add_argument("--constraint", action="append", default=[])
    checkpoint.add_argument("--rollover-reason", default="manual checkpoint")
    checkpoint.set_defaults(handler=_context_checkpoint)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except (ContractError, FileExistsError, FileNotFoundError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2
