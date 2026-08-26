"""Enforce risk-proportional PR governance at the shared-truth boundary."""

from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / ".github" / "governance-policy.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

RISK_ORDER = tuple(POLICY["risk_order"])
RISK_RANK = {name: index for index, name in enumerate(RISK_ORDER)}
SEVERITIES = tuple(POLICY["finding_severities"])
PR_CLASSES = set(POLICY["pr_classes"])
VALID_STATUSES = set(POLICY["task_statuses"])
TASK_TRANSITIONS = {
    before: set(after) for before, after in POLICY["task_transitions"].items()
}
OWNER_SLUGS = dict(POLICY["owners"])
WORKSTREAM_OWNERS = {slug: owner for owner, slug in OWNER_SLUGS.items()}
MINIMUM_RISK_PATHS = {
    risk: tuple(patterns) for risk, patterns in POLICY["minimum_risk_paths"].items()
}
PUBLISHED_IDENTITIES = tuple(POLICY["published_identities"])

ALLOWED_BASES = {"develop", "main"}
TASK_ID_RE = re.compile(r"^M\d+-\d+$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
YES_VALUES = {"yes", "true", "是"}
NO_VALUES = {"no", "false", "否"}
NONE_VALUES = {"", "none", "n/a", "not applicable", "无"}

REQUIRED_FIELDS = ("PR class", "Risk tier", "Accountable owner")
REQUIRED_SECTIONS = (
    "Scope and non-goals",
    "Contract and authority impact",
    "TASKS transition",
    "Verification evidence",
    "Residual risk and follow-up",
)
FIELD_ALIASES = {
    "PR 类型": "PR class",
    "任务 ID": "Task ID(s)",
    "风险等级": "Risk tier",
    "责任人": "Accountable owner",
    "工作流目录": "Workstream",
    "共享契约": "Shared contract",
    "权威、权限或数据边界": "Authority impact",
    "权威/权限/数据边界": "Authority impact",
}
SECTION_ALIASES = {
    "范围与非目标": "Scope and non-goals",
    "契约与权限影响": "Contract and authority impact",
    "契约与权威影响": "Contract and authority impact",
    "TASKS 状态变更": "TASKS transition",
    "验证证据": "Verification evidence",
    "剩余风险与后续": "Residual risk and follow-up",
    "权威依据": "Authority basis",
    "对抗性证据": "Adversarial evidence",
}


class GovernanceError(RuntimeError):
    """A repository or event fact could not be read deterministically."""


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str


@dataclass
class GovernanceReport:
    findings: list[Finding] = field(default_factory=list)
    declared_risk: str = "unknown"
    inferred_risk: str = "R0"
    effective_risk: str = "unknown"
    risk_reasons: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)

    def add(self, severity: str, code: str, message: str) -> None:
        if severity not in SEVERITIES:
            raise GovernanceError(f"unknown finding severity: {severity}")
        self.findings.append(Finding(severity, code, message))

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "ERROR" for item in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(item.severity == "WARNING" for item in self.findings)

    def emit(self) -> None:
        print(f"Declared risk: {self.declared_risk}")
        print(f"Inferred minimum: {self.inferred_risk}")
        print(f"Effective risk: {self.effective_risk}")
        print("Reason:")
        for reason in self.risk_reasons or ["no changed surface requires more than R0"]:
            print(f"- {reason}")
        print("Requirements:")
        for requirement in self.requirements:
            print(f"- {requirement}")
        if self.findings:
            print("Findings:")
            for item in self.findings:
                print(f"- {item.severity} {item.code}: {item.message}")
        if self.has_errors:
            print("governance: FAIL", file=sys.stderr)
        elif self.warning_count:
            print(f"governance: PASS WITH {self.warning_count} WARNING(S)")
        else:
            print("governance: PASS")


@dataclass(frozen=True)
class TaskRow:
    task_id: str
    status: str
    remainder: tuple[str, ...]
    dependencies: str
    line_number: int


@dataclass(frozen=True)
class PublishedDocument:
    kind: str
    identity: tuple[str, ...]
    path: str
    content: str


def _clean_value(value: str) -> str:
    return HTML_COMMENT_RE.sub("", value).strip().strip("`")


def parse_metadata(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in body.splitlines():
        match = re.match(r"^\s*-\s+\*\*(.+?)\*\*:\s*(.*)$", line)
        if match:
            label = match.group(1).strip()
            result[FIELD_ALIASES.get(label, label)] = _clean_value(match.group(2))
    return result


def parse_sections(body: str) -> dict[str, str]:
    headings = list(re.finditer(r"(?m)^##\s+(.+?)\s*$", body))
    sections: dict[str, str] = {}
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(body)
        heading = match.group(1).strip()
        sections[SECTION_ALIASES.get(heading, heading)] = _clean_value(
            body[match.end() : end]
        )
    return sections


def normalize_handle(value: str) -> str:
    return value.strip().lstrip("@").strip("`")


def _parse_yes_no(
    metadata: Mapping[str, str], key: str, report: GovernanceReport
) -> bool:
    value = metadata.get(key, "").strip().lower()
    if value in YES_VALUES:
        return True
    if value in NO_VALUES:
        return False
    report.add("ERROR", "META-BOOLEAN", f"{key} must be an explicit yes/no value")
    return False


def validate_body(
    body: str, report: GovernanceReport
) -> tuple[dict[str, str], dict[str, str], bool, bool]:
    metadata = parse_metadata(body)
    sections = parse_sections(body)
    for field_name in REQUIRED_FIELDS:
        if not metadata.get(field_name):
            report.add("ERROR", "META-MISSING", f"missing PR metadata: {field_name}")
    for section_name in REQUIRED_SECTIONS:
        if not sections.get(section_name):
            report.add("ERROR", "SECTION-MISSING", f"missing or empty PR section: {section_name}")

    metadata.setdefault("Task ID(s)", "none")
    metadata.setdefault("Workstream", "none")
    pr_class = metadata.get("PR class", "")
    if pr_class and pr_class not in PR_CLASSES:
        report.add("ERROR", "PR-CLASS", f"invalid PR class: {pr_class!r}")

    declared_risk = metadata.get("Risk tier", "")
    report.declared_risk = declared_risk or "unknown"
    if declared_risk and declared_risk not in RISK_RANK:
        report.add("ERROR", "RISK-DECLARATION", f"invalid Risk tier: {declared_risk!r}")

    owner = normalize_handle(metadata.get("Accountable owner", ""))
    if owner and owner not in OWNER_SLUGS:
        report.add("ERROR", "OWNER-UNKNOWN", f"unknown accountable owner: {owner!r}")
    metadata["Accountable owner"] = owner
    shared_contract = _parse_yes_no(metadata, "Shared contract", report)
    authority_impact = _parse_yes_no(metadata, "Authority impact", report)
    return metadata, sections, shared_contract, authority_impact


def _max_risk(left: str, right: str) -> str:
    return left if RISK_RANK[left] >= RISK_RANK[right] else right


def infer_minimum_risk(
    changed_paths: Sequence[str], *, shared_contract: bool, authority_impact: bool
) -> tuple[str, list[str]]:
    risk = "R0"
    reasons: list[str] = []
    for path in changed_paths:
        normalized = path.replace("\\", "/")
        for candidate, patterns in MINIMUM_RISK_PATHS.items():
            if any(fnmatch.fnmatchcase(normalized, pattern) for pattern in patterns):
                risk = _max_risk(risk, candidate)
                reasons.append(f"{normalized} matches the {candidate} policy surface")
    if shared_contract:
        risk = _max_risk(risk, "R1")
        reasons.append("PR declares a shared-contract impact")
    if authority_impact:
        risk = "R2"
        reasons.append("PR declares an authority, permission, or data-boundary impact")
    return risk, list(dict.fromkeys(reasons))


def resolve_effective_risk(
    declared: str, inferred: str, report: GovernanceReport
) -> str:
    if declared not in RISK_RANK:
        effective = inferred
    else:
        effective = _max_risk(declared, inferred)
        if RISK_RANK[declared] < RISK_RANK[inferred]:
            report.add(
                "WARNING",
                "RISK-AUTO-UPGRADE",
                f"declared {declared} was automatically upgraded to {inferred}",
            )
    report.inferred_risk = inferred
    report.effective_risk = effective
    report.requirements = {
        "R0": ["pull request and required CI"],
        "R1": ["pull request and required CI", "cross-owner review before merge"],
        "R2": [
            "pull request and required CI",
            "cross-owner review before merge",
            "explicit authority basis",
            "adversarial or negative evidence",
            "owner-matched workstream and Risk Ledger",
        ],
    }[effective]
    return effective


def validate_topology(
    *,
    base_ref: str,
    head_ref: str,
    base_repository: str,
    head_repository: str,
    pr_class: str,
    report: GovernanceReport,
) -> None:
    if base_ref not in ALLOWED_BASES:
        report.add("ERROR", "TOPOLOGY-BASE", f"PR base must be develop or main, not {base_ref!r}")
        return
    if base_ref == "main":
        if head_ref != "develop" or head_repository != base_repository:
            report.add(
                "ERROR",
                "TOPOLOGY-MAIN-SOURCE",
                "main accepts only an exact same-repository develop branch",
            )
        if pr_class != "release":
            report.add("ERROR", "TOPOLOGY-RELEASE-CLASS", "develop -> main must use release")
    elif pr_class == "release":
        report.add("ERROR", "TOPOLOGY-RELEASE-BASE", "release PRs must target main from develop")


def parse_task_rows(text: str) -> dict[str, TaskRow]:
    rows: dict[str, TaskRow] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.lstrip().startswith("|"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        if len(cells) < 3 or not TASK_ID_RE.fullmatch(cells[0]):
            continue
        task_id, status = cells[0], cells[1]
        if status not in VALID_STATUSES:
            raise GovernanceError(
                f"{task_id} has invalid status {status!r} at TASKS line {line_number}"
            )
        if task_id in rows:
            raise GovernanceError(f"duplicate TASKS row: {task_id}")
        dependencies = cells[-2] if len(cells) >= 5 else ""
        rows[task_id] = TaskRow(task_id, status, cells[2:], dependencies, line_number)
    return rows


def _docs_only(paths: Iterable[str]) -> bool:
    root_docs = {"CHANGELOG.md", "DEVELOPMENT_HISTORY.md", "README.md", "AGENTS.md"}
    return all(path.startswith("docs/") or path in root_docs for path in paths)


def task_ids_from_metadata(value: str) -> set[str]:
    return set(re.findall(r"\bM\d+-\d+\b", value))


def _dependency_ids(value: str) -> set[str]:
    result = set(re.findall(r"\bM\d+-\d+\b", value))
    for prefix, start, end in re.findall(r"\b(M\d+)-(\d+)\.\.(\d+)\b", value):
        width = len(start)
        result.update(f"{prefix}-{number:0{width}d}" for number in range(int(start), int(end) + 1))
    return result


def _validate_dependencies(
    task_ids: Iterable[str], head_rows: Mapping[str, TaskRow], report: GovernanceReport
) -> None:
    for task_id in sorted(set(task_ids)):
        row = head_rows.get(task_id)
        if row is None or row.status not in {"READY", "IN_PROGRESS"}:
            continue
        for dependency in sorted(_dependency_ids(row.dependencies)):
            dependency_row = head_rows.get(dependency)
            if dependency_row is None:
                report.add(
                    "ERROR", "TASK-DEPENDENCY-UNKNOWN", f"{task_id} references unknown dependency {dependency}"
                )
            elif dependency_row.status != "DONE":
                report.add(
                    "ERROR",
                    "TASK-DEPENDENCY-NOT-DONE",
                    f"{task_id} cannot enter {row.status} while {dependency} is {dependency_row.status}",
                )


def _validate_atomic_completion_dag(
    completed_ids: set[str],
    parked_completed_ids: set[str],
    base_rows: Mapping[str, TaskRow],
    head_rows: Mapping[str, TaskRow],
    effective_risk: str,
    verification_evidence: str,
    report: GovernanceReport,
) -> None:
    if not completed_ids:
        return
    completion_valid = True
    for task_id in sorted(completed_ids):
        if re.search(rf"\b{re.escape(task_id)}\b", verification_evidence) is None:
            completion_valid = False
            report.add(
                "ERROR",
                "TASK-DONE-EVIDENCE-MISSING",
                f"{task_id} enters DONE without task-specific verification evidence",
            )

    dependencies_within_chain: dict[str, set[str]] = {
        task_id: set() for task_id in completed_ids
    }
    dependents: dict[str, set[str]] = {task_id: set() for task_id in completed_ids}
    for task_id in sorted(completed_ids):
        row = head_rows[task_id]
        for dependency in sorted(_dependency_ids(row.dependencies)):
            dependency_row = head_rows.get(dependency)
            if dependency_row is None:
                completion_valid = False
                report.add(
                    "ERROR",
                    "TASK-DEPENDENCY-UNKNOWN",
                    f"{task_id} references unknown dependency {dependency}",
                )
                continue
            if dependency_row.status != "DONE":
                completion_valid = False
                report.add(
                    "ERROR",
                    "TASK-DEPENDENCY-NOT-DONE",
                    f"{task_id} cannot enter DONE while {dependency} is {dependency_row.status}",
                )
                continue
            if dependency in completed_ids:
                dependencies_within_chain[task_id].add(dependency)
                dependents[dependency].add(task_id)
            elif base_rows.get(dependency) is None or base_rows[dependency].status != "DONE":
                completion_valid = False
                report.add(
                    "ERROR",
                    "TASK-DEPENDENCY-NOT-ATOMIC",
                    f"{task_id} depends on {dependency}, which was not DONE in base or completed in this Stage",
                )

    entry_anchor_ids = {
        task_id for task_id in completed_ids if base_rows[task_id].status == "READY"
    }
    if parked_completed_ids and effective_risk != "R2":
        completion_valid = False
        report.add(
            "ERROR",
            "TASK-ATOMIC-RISK",
            "PARKED -> DONE is allowed only for an R2 Stage atomic completion",
        )
    if parked_completed_ids and not entry_anchor_ids:
        completion_valid = False
        report.add(
            "ERROR",
            "TASK-ATOMIC-ANCHOR-MISSING",
            "PARKED -> DONE requires a READY entry Task completing as the module anchor",
        )

    reachable = set(entry_anchor_ids)
    frontier = sorted(entry_anchor_ids)
    while frontier:
        task_id = frontier.pop(0)
        for dependent in sorted(dependents[task_id]):
            if dependent not in reachable:
                reachable.add(dependent)
                frontier.append(dependent)
    connectivity_required = len(completed_ids) > 1
    disconnected = sorted(
        (completed_ids if connectivity_required else parked_completed_ids) - reachable
    )
    if disconnected:
        completion_valid = False
        report.add(
            "ERROR",
            "TASK-MODULE-DAG-DISCONNECTED",
            "completed Tasks are not dependency-reachable from a READY module entry: "
            + ", ".join(disconnected),
        )

    ready = sorted(
        task_id
        for task_id, dependencies in dependencies_within_chain.items()
        if not dependencies
    )
    order: list[str] = []
    while ready:
        task_id = ready.pop(0)
        order.append(task_id)
        for dependent in sorted(dependents[task_id]):
            dependencies_within_chain[dependent].discard(task_id)
            if not dependencies_within_chain[dependent] and dependent not in order and dependent not in ready:
                ready.append(dependent)
        ready.sort()
    if len(order) != len(completed_ids):
        completion_valid = False
        unresolved = sorted(completed_ids - set(order))
        report.add(
            "ERROR",
            "TASK-DEPENDENCY-CYCLE",
            f"atomic completion dependency graph is cyclic or unresolved: {unresolved}",
        )
    elif connectivity_required and completion_valid:
        report.add(
            "INFO",
            "TASK-MODULE-COMPLETION",
            "validated module completion order: " + " -> ".join(order),
        )


def validate_mode_action_registry_history(
    base_registry: Mapping[str, object],
    head_registry: Mapping[str, object],
    report: GovernanceReport,
) -> None:
    """Reject deletion or mutation of a published action_id@version entry."""

    def index(registry: Mapping[str, object]) -> dict[tuple[str, str], Mapping[str, object]]:
        result: dict[tuple[str, str], Mapping[str, object]] = {}
        entries = registry.get("entries", [])
        if not isinstance(entries, list):
            report.add("ERROR", "ACTION-REGISTRY-SHAPE", "Mode Action Registry entries must be a list")
            return result
        for entry in entries:
            if not isinstance(entry, Mapping):
                report.add("ERROR", "ACTION-REGISTRY-SHAPE", "Mode Action Registry entry must be an object")
                continue
            key = (str(entry.get("action_id", "")), str(entry.get("version", "")))
            if key in result:
                report.add("ERROR", "ACTION-REGISTRY-DUPLICATE", f"duplicate published identity: {key}")
            result[key] = entry
        return result

    before = index(base_registry)
    after = index(head_registry)
    for key, old_entry in before.items():
        new_entry = after.get(key)
        reference = f"{key[0]}@{key[1]}"
        if new_entry is None:
            report.add("ERROR", "ACTION-IDENTITY-REMOVED", f"published Action removed: {reference}")
        elif dict(old_entry) != dict(new_entry):
            report.add(
                "ERROR",
                "ACTION-IDENTITY-MUTATED",
                f"published Action entry changed in place: {reference}; publish a new version",
            )


def _published_identity_spec(path: str) -> tuple[str, tuple[str, ...]] | None:
    normalized = path.replace("\\", "/")
    candidate = PurePosixPath(normalized)
    for declaration in PUBLISHED_IDENTITIES:
        patterns = tuple(str(pattern) for pattern in declaration.get("patterns", ()))
        if any(candidate.match(pattern) for pattern in patterns):
            return (
                str(declaration["kind"]),
                tuple(str(field) for field in declaration["identity_fields"]),
            )
    return None


def _top_level_scalar(document: str, field_name: str) -> str | None:
    stripped = document.lstrip()
    if stripped.startswith("{"):
        try:
            value = json.loads(document).get(field_name)
        except (json.JSONDecodeError, AttributeError):
            return None
        return value if isinstance(value, str) and value else None
    match = re.search(
        rf"(?m)^{re.escape(field_name)}:\s*([^#\r\n]+?)\s*$",
        document,
    )
    if match is None:
        return None
    value = match.group(1).strip().strip("'\"")
    return value or None


def _index_published_documents(
    documents: Mapping[str, str], report: GovernanceReport
) -> dict[tuple[str, tuple[str, ...]], PublishedDocument]:
    indexed: dict[tuple[str, tuple[str, ...]], PublishedDocument] = {}
    for path, content in sorted(documents.items()):
        spec = _published_identity_spec(path)
        if spec is None:
            continue
        kind, fields = spec
        identity_values = tuple(_top_level_scalar(content, field) or "" for field in fields)
        if any(not value for value in identity_values):
            report.add(
                "ERROR",
                "PUBLISHED-IDENTITY-SHAPE",
                f"{path} lacks published identity fields {fields}",
            )
            continue
        key = (kind, identity_values)
        if key in indexed:
            report.add(
                "ERROR",
                "PUBLISHED-IDENTITY-DUPLICATE",
                f"duplicate {kind} identity: {'@'.join(identity_values)}",
            )
            continue
        indexed[key] = PublishedDocument(kind, identity_values, path, content)
    return indexed


def validate_published_identity_history(
    base_documents: Mapping[str, str],
    head_documents: Mapping[str, str],
    report: GovernanceReport,
) -> None:
    """Reject removal, relocation, or content mutation of any published identity."""

    before = _index_published_documents(base_documents, report)
    after = _index_published_documents(head_documents, report)
    for key, old_document in before.items():
        new_document = after.get(key)
        reference = "@".join(old_document.identity)
        if new_document is None:
            report.add(
                "ERROR",
                "PUBLISHED-IDENTITY-REMOVED",
                f"published {old_document.kind} removed: {reference}",
            )
        elif (
            new_document.path != old_document.path
            or new_document.content != old_document.content
        ):
            report.add(
                "ERROR",
                "PUBLISHED-IDENTITY-MUTATED",
                f"published {old_document.kind} changed in place: {reference}; publish a new version",
            )


def validate_task_changes(
    *,
    base_text: str,
    head_text: str,
    pr_class: str,
    changed_paths: Sequence[str],
    declared_task_ids: set[str],
    effective_risk: str,
    verification_evidence: str,
    report: GovernanceReport,
) -> None:
    try:
        base_rows = parse_task_rows(base_text)
        head_rows = parse_task_rows(head_text)
    except GovernanceError as exc:
        report.add("ERROR", "TASK-PARSE", str(exc))
        return

    for task_id, before in base_rows.items():
        after = head_rows.get(task_id)
        if after is None:
            report.add("ERROR", "TASK-REMOVED", f"TASKS row removed: {task_id}")
        elif before.status == "DONE" and (
            after.status != before.status or after.remainder != before.remainder
        ):
            report.add("ERROR", "TASK-DONE-IMMUTABLE", f"completed TASKS row is immutable: {task_id}")

    if pr_class == "release":
        return

    added = set(head_rows) - set(base_rows)
    removed = set(base_rows) - set(head_rows)
    definition_changes = {
        task_id
        for task_id in set(base_rows) & set(head_rows)
        if base_rows[task_id].remainder != head_rows[task_id].remainder
    } | added
    status_changes = {
        task_id
        for task_id in set(base_rows) & set(head_rows)
        if base_rows[task_id].status != head_rows[task_id].status
    }
    changed_task_ids = definition_changes | status_changes | removed

    if pr_class == "task-definition":
        if not _docs_only(changed_paths):
            report.add("ERROR", "TASK-DEFINITION-DOCS", "task-definition PR must be documentation-only")
        if removed:
            report.add("ERROR", "TASK-DEFINITION-REMOVE", "task-definition cannot remove Task IDs")
        if not definition_changes:
            report.add("ERROR", "TASK-DEFINITION-EMPTY", "task-definition must define or revise a Task")
        if changed_task_ids != declared_task_ids:
            report.add(
                "ERROR",
                "TASK-DECLARATION-CLOSURE",
                f"declared={sorted(declared_task_ids)} changed={sorted(changed_task_ids)}",
            )
        for task_id in changed_task_ids:
            before = base_rows.get(task_id)
            after = head_rows.get(task_id)
            if after and after.status == "DONE" and (before is None or before.status != "DONE"):
                report.add("ERROR", "TASK-DEFINITION-DONE", f"task-definition cannot set DONE: {task_id}")
        _validate_dependencies(changed_task_ids, head_rows, report)
        return

    if added or removed:
        report.add(
            "ERROR",
            "TASK-DEFINITION-CLASS",
            f"only task-definition may add/remove rows: added={sorted(added)}, removed={sorted(removed)}",
        )
    for task_id in sorted(definition_changes):
        report.add("ERROR", "TASK-DEFINITION-REWRITE", f"feature cannot rewrite Task definition: {task_id}")

    undeclared = status_changes - declared_task_ids
    if undeclared:
        report.add(
            "ERROR", "TASK-STATUS-UNDECLARED", "status changes must be declared: " + ", ".join(sorted(undeclared))
        )
    for task_id in sorted(status_changes):
        before = base_rows[task_id].status
        after = head_rows[task_id].status
        parked_completion = before == "PARKED" and after == "DONE"
        atomic_completion = parked_completion and effective_risk == "R2"
        if after not in TASK_TRANSITIONS.get(before, set()) and not atomic_completion:
            report.add("ERROR", "TASK-TRANSITION", f"illegal transition {task_id}: {before} -> {after}")
        else:
            transition_kind = "atomic completion" if atomic_completion else "valid transition"
            report.add("INFO", "TASK-TRANSITION", f"{transition_kind} {task_id}: {before} -> {after}")
    completed_ids = {
        task_id
        for task_id in status_changes
        if head_rows[task_id].status == "DONE" and base_rows[task_id].status != "DONE"
    }
    parked_completed_ids = {
        task_id
        for task_id in completed_ids
        if base_rows[task_id].status == "PARKED"
    }
    _validate_atomic_completion_dag(
        completed_ids,
        parked_completed_ids,
        base_rows,
        head_rows,
        effective_risk,
        verification_evidence,
        report,
    )
    _validate_dependencies(status_changes, head_rows, report)


def validate_workstream(
    *,
    raw_workstream: str,
    owner: str,
    effective_risk: str,
    head_sha: str,
    report: GovernanceReport,
) -> None:
    normalized = raw_workstream.replace("\\", "/").rstrip("/").strip()
    if normalized.lower() in NONE_VALUES:
        if effective_risk == "R2":
            report.add("ERROR", "WORKSTREAM-R2", "R2 changes require a workstream")
        elif effective_risk == "R1":
            report.add("WARNING", "WORKSTREAM-R1", "R1 workstream omitted; PR body is the evidence surface")
        return

    workstream = PurePosixPath(normalized)
    if (
        workstream.is_absolute()
        or ".." in workstream.parts
        or workstream.parts[:2] != ("docs", "workstreams")
        or len(workstream.parts) < 4
    ):
        report.add(
            "ERROR", "WORKSTREAM-PATH", "Workstream must be docs/workstreams/<owner>/<task-id-or-slug>/ or none"
        )
        return
    expected_owner = WORKSTREAM_OWNERS.get(workstream.parts[2])
    if expected_owner is None:
        report.add("ERROR", "WORKSTREAM-OWNER-PATH", f"unknown owner path: {workstream.parts[2]}")
    elif owner != expected_owner:
        report.add(
            "ERROR", "WORKSTREAM-OWNER-MISMATCH", f"{workstream.parts[2]} requires @{expected_owner}, not @{owner}"
        )
    try:
        _read_blob(head_sha, f"{workstream.as_posix()}/README.md")
        if effective_risk == "R2":
            _read_blob(head_sha, f"{workstream.as_posix()}/RISK_LEDGER.md")
    except GovernanceError as exc:
        report.add("ERROR", "WORKSTREAM-EVIDENCE", str(exc))


def validate_risk_requirements(
    *, effective_risk: str, sections: Mapping[str, str], raw_task_ids: str, report: GovernanceReport
) -> None:
    if effective_risk in {"R1", "R2"} and raw_task_ids.strip().lower() in NONE_VALUES:
        report.add("ERROR", "TASK-ID-RISK", f"{effective_risk} changes require a Task or Audit ID")
    if effective_risk != "R2":
        return
    for section_name, code in (
        ("Authority basis", "R2-AUTHORITY-BASIS"),
        ("Adversarial evidence", "R2-ADVERSARIAL-EVIDENCE"),
    ):
        value = sections.get(section_name, "").strip().lower()
        if value in NONE_VALUES:
            report.add("ERROR", code, f"R2 requires a substantive {section_name} section")


def _git(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if process.returncode != 0:
        raise GovernanceError(
            f"git {' '.join(args)} failed: {process.stderr.strip() or process.stdout.strip()}"
        )
    return process.stdout


def _read_blob(commit: str, path: str) -> str:
    return _git("show", f"{commit}:{path}")


def _blob_exists(commit: str, path: str) -> bool:
    process = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return process.returncode == 0


def _merge_base(base_sha: str, head_sha: str) -> str:
    return _git("merge-base", base_sha, head_sha).strip()


def _changed_paths(base_sha: str, head_sha: str) -> list[str]:
    return [line for line in _git("diff", "--name-only", f"{base_sha}...{head_sha}").splitlines() if line]


def _published_documents_at(commit: str) -> dict[str, str]:
    paths = [
        line
        for line in _git(
            "ls-tree",
            "-r",
            "--name-only",
            commit,
        ).splitlines()
        if _published_identity_spec(line) is not None
    ]
    return {path: _read_blob(commit, path) for path in paths}


def check_pull_request(event: Mapping[str, object]) -> GovernanceReport:
    report = GovernanceReport()
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, Mapping):
        report.add("ERROR", "EVENT-PR", "pull_request event payload is missing")
        return report
    base = pull_request.get("base")
    head = pull_request.get("head")
    if not isinstance(base, Mapping) or not isinstance(head, Mapping):
        report.add("ERROR", "EVENT-REFS", "pull_request base/head payload is missing")
        return report

    base_sha = str(base.get("sha", "")).lower()
    head_sha = str(head.get("sha", "")).lower()
    metadata, sections, shared_contract, authority_impact = validate_body(
        str(pull_request.get("body") or ""), report
    )
    base_repo = base.get("repo")
    head_repo = head.get("repo")
    if isinstance(base_repo, Mapping) and isinstance(head_repo, Mapping):
        validate_topology(
            base_ref=str(base.get("ref", "")),
            head_ref=str(head.get("ref", "")),
            base_repository=str(base_repo.get("full_name", "")),
            head_repository=str(head_repo.get("full_name", "")),
            pr_class=metadata.get("PR class", ""),
            report=report,
        )
    else:
        report.add("ERROR", "EVENT-REPOSITORY", "repository identity is missing")

    try:
        changed_paths = _changed_paths(base_sha, head_sha)
        merge_base = _merge_base(base_sha, head_sha)
        if merge_base != base_sha:
            report.add(
                "WARNING",
                "BASE-STALE",
                "branch does not contain the latest target commit; validate the GitHub merge ref before merge",
            )
    except GovernanceError as exc:
        report.add("ERROR", "GIT-DIFF", str(exc))
        changed_paths = []
        merge_base = base_sha

    inferred, reasons = infer_minimum_risk(
        changed_paths, shared_contract=shared_contract, authority_impact=authority_impact
    )
    report.risk_reasons = reasons
    effective = resolve_effective_risk(metadata.get("Risk tier", ""), inferred, report)
    validate_risk_requirements(
        effective_risk=effective,
        sections=sections,
        raw_task_ids=metadata.get("Task ID(s)", "none"),
        report=report,
    )
    validate_workstream(
        raw_workstream=metadata.get("Workstream", "none"),
        owner=metadata.get("Accountable owner", ""),
        effective_risk=effective,
        head_sha=head_sha,
        report=report,
    )

    try:
        validate_task_changes(
            base_text=_read_blob(merge_base, "docs/TASKS.md"),
            head_text=_read_blob(head_sha, "docs/TASKS.md"),
            pr_class=metadata.get("PR class", ""),
            changed_paths=changed_paths,
            declared_task_ids=task_ids_from_metadata(metadata.get("Task ID(s)", "none")),
            effective_risk=effective,
            verification_evidence=sections.get("Verification evidence", ""),
            report=report,
        )
    except GovernanceError as exc:
        report.add("ERROR", "TASK-READ", str(exc))

    action_registry_path = "registry/modes/actions.json"
    if action_registry_path in changed_paths and _blob_exists(merge_base, action_registry_path):
        if not _blob_exists(head_sha, action_registry_path):
            report.add("ERROR", "ACTION-REGISTRY-REMOVED", "published Mode Action Registry was removed")
        else:
            try:
                validate_mode_action_registry_history(
                    json.loads(_read_blob(merge_base, action_registry_path)),
                    json.loads(_read_blob(head_sha, action_registry_path)),
                    report,
                )
            except (GovernanceError, json.JSONDecodeError) as exc:
                report.add("ERROR", "ACTION-REGISTRY-READ", str(exc))

    try:
        validate_published_identity_history(
            _published_documents_at(merge_base),
            _published_documents_at(head_sha),
            report,
        )
    except GovernanceError as exc:
        report.add("ERROR", "PUBLISHED-IDENTITY-READ", str(exc))

    if pull_request.get("mergeable") is False:
        report.add("ERROR", "MERGE-CONFLICT", "GitHub reports that the PR is not mergeable")
    return report


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        print("governance: push/non-PR event; PR-only checks skipped")
        return 0
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("governance: FAIL: GITHUB_EVENT_PATH is required", file=sys.stderr)
        return 2
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        report = check_pull_request(event)
    except (GovernanceError, KeyError, json.JSONDecodeError) as exc:
        print(f"governance: FAIL: {exc}", file=sys.stderr)
        return 2
    report.emit()
    return 1 if report.has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
