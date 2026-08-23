"""Enforce repository PR topology, metadata, and TASKS authority boundaries."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
OWNER_HANDLES = ("Chengyue-Lu", "let778750-cpu")
WORKSTREAM_OWNER_HANDLES = {
    "chengyue-lu": "Chengyue-Lu",
    "huangyi": "let778750-cpu",
}
ALLOWED_BASES = {"develop", "main"}
VALID_STATUSES = {"DONE", "IN_PROGRESS", "READY", "BLOCKED", "PARKED"}
PR_CLASSES = {"feature", "task-definition", "task-closeout", "release"}
TASK_ID_RE = re.compile(r"^M\d+-\d+$")
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

REQUIRED_FIELDS = (
    "PR class",
    "Task ID(s)",
    "Workstream",
    "Accountable owner",
    "Cross-owner reviewer",
    "Base SHA",
)
REQUIRED_SECTIONS = (
    "Scope and non-goals",
    "Contract and authority impact",
    "TASKS transition",
    "Risk ledger",
    "Verification evidence",
    "Closeout and history",
)
FIELD_ALIASES = {
    "PR 类型": "PR class",
    "任务 ID": "Task ID(s)",
    "工作流目录": "Workstream",
    "责任人": "Accountable owner",
    "跨负责人审查人": "Cross-owner reviewer",
    "基线 SHA": "Base SHA",
}
SECTION_ALIASES = {
    "范围与非目标": "Scope and non-goals",
    "契约与权限影响": "Contract and authority impact",
    "契约与权威影响": "Contract and authority impact",
    "TASKS 状态变更": "TASKS transition",
    "风险台账": "Risk ledger",
    "验证证据": "Verification evidence",
    "收尾与历史记录": "Closeout and history",
}
CLOSEOUT_ALLOWED_EXACT = {
    "CHANGELOG.md",
    "DEVELOPMENT_HISTORY.md",
    "docs/STATUS.md",
    "docs/TASKS.md",
}


class GovernanceError(RuntimeError):
    """A deterministic PR governance violation."""


@dataclass(frozen=True)
class TaskRow:
    task_id: str
    status: str
    remainder: tuple[str, ...]
    line_number: int


def _clean_value(value: str) -> str:
    return HTML_COMMENT_RE.sub("", value).strip().strip("`")


def parse_metadata(body: str) -> dict[str, str]:
    """Parse bold list fields and normalize Chinese labels to stable keys."""
    result: dict[str, str] = {}
    for line in body.splitlines():
        match = re.match(r"^\s*-\s+\*\*(.+?)\*\*:\s*(.*)$", line)
        if match:
            label = match.group(1).strip()
            result[FIELD_ALIASES.get(label, label)] = _clean_value(match.group(2))
    return result


def parse_sections(body: str) -> dict[str, str]:
    """Return normalized level-two section bodies with guidance removed."""
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


def validate_body(body: str, expected_base_sha: str) -> dict[str, str]:
    metadata = parse_metadata(body)
    missing = [field for field in REQUIRED_FIELDS if not metadata.get(field)]
    if missing:
        raise GovernanceError("missing PR metadata: " + ", ".join(missing))

    sections = parse_sections(body)
    empty_sections = [name for name in REQUIRED_SECTIONS if not sections.get(name)]
    if empty_sections:
        raise GovernanceError("missing or empty PR sections: " + ", ".join(empty_sections))

    pr_class = metadata["PR class"]
    if pr_class not in PR_CLASSES:
        raise GovernanceError(f"invalid PR class: {pr_class!r}")

    base_sha = metadata["Base SHA"].lower()
    if not re.fullmatch(r"[0-9a-f]{40}", base_sha):
        raise GovernanceError("Base SHA must be an exact 40-character commit SHA")
    if base_sha != expected_base_sha.lower():
        raise GovernanceError(
            f"Base SHA {base_sha} does not match current PR base {expected_base_sha.lower()}"
        )

    owner = normalize_handle(metadata["Accountable owner"])
    reviewer = normalize_handle(metadata["Cross-owner reviewer"])
    if owner not in OWNER_HANDLES:
        raise GovernanceError(f"unknown accountable owner: {owner!r}")
    expected_reviewer = next(handle for handle in OWNER_HANDLES if handle != owner)
    if reviewer != expected_reviewer:
        raise GovernanceError(
            f"cross-owner reviewer must be @{expected_reviewer} for owner @{owner}"
        )

    raw_workstream = metadata["Workstream"].replace("\\", "/").rstrip("/")
    workstream = PurePosixPath(raw_workstream)
    if (
        workstream.is_absolute()
        or ".." in workstream.parts
        or workstream.parts[:2] != ("docs", "workstreams")
        or len(workstream.parts) < 4
    ):
        raise GovernanceError(
            "Workstream must be docs/workstreams/<owner>/<task-id-or-slug>/"
        )
    owner_slug = workstream.parts[2]
    expected_owner = WORKSTREAM_OWNER_HANDLES.get(owner_slug)
    if expected_owner is None:
        raise GovernanceError(f"unknown workstream owner path: {owner_slug!r}")
    if owner != expected_owner:
        raise GovernanceError(
            f"Workstream owner path {owner_slug!r} requires accountable owner "
            f"@{expected_owner}, not @{owner}"
        )
    metadata["Workstream"] = workstream.as_posix()
    metadata["Accountable owner"] = owner
    metadata["Cross-owner reviewer"] = reviewer
    metadata["Base SHA"] = base_sha
    return metadata


def validate_topology(
    *,
    base_ref: str,
    head_ref: str,
    base_repository: str,
    head_repository: str,
    pr_class: str,
) -> None:
    if base_ref not in ALLOWED_BASES:
        raise GovernanceError(f"PR base must be develop or main, not {base_ref!r}")
    if base_ref == "main":
        if head_ref != "develop" or head_repository != base_repository:
            raise GovernanceError("main accepts only an exact same-repository develop branch")
        if pr_class != "release":
            raise GovernanceError("develop -> main PR must use PR class release")
    elif pr_class == "release":
        raise GovernanceError("release PRs must target main from develop")


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
        rows[task_id] = TaskRow(task_id, status, cells[2:], line_number)
    return rows


def normalize_task_statuses(text: str) -> str:
    normalized: list[str] = []
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and len(cells) >= 3 and TASK_ID_RE.fullmatch(cells[0]):
            cells[1] = "<STATUS>"
            normalized.append("| " + " | ".join(cells) + " |")
        else:
            normalized.append(line.rstrip())
    return "\n".join(normalized).strip()


def _assert_done_rows_immutable(
    base_rows: Mapping[str, TaskRow], head_rows: Mapping[str, TaskRow]
) -> None:
    for task_id, before in base_rows.items():
        if task_id not in head_rows:
            raise GovernanceError(f"TASKS row removed: {task_id}")
        after = head_rows[task_id]
        if before.status == "DONE" and (
            after.status != before.status or after.remainder != before.remainder
        ):
            raise GovernanceError(f"completed TASKS row is immutable: {task_id}")


def _docs_only(paths: Iterable[str]) -> bool:
    root_docs = {"CHANGELOG.md", "DEVELOPMENT_HISTORY.md", "README.md"}
    return all(path.startswith("docs/") or path in root_docs for path in paths)


def _closeout_path_allowed(path: str) -> bool:
    return (
        path in CLOSEOUT_ALLOWED_EXACT
        or path.startswith("docs/workstreams/")
        or path.startswith("docs/history/")
    )


def task_ids_from_metadata(value: str) -> set[str]:
    return set(re.findall(r"\bM\d+-\d+\b", value))


def validate_task_changes(
    *,
    base_text: str,
    head_text: str,
    pr_class: str,
    labels: set[str],
    changed_paths: Sequence[str],
    declared_task_ids: set[str],
    base_ref: str,
) -> None:
    base_rows = parse_task_rows(base_text)
    head_rows = parse_task_rows(head_text)
    _assert_done_rows_immutable(base_rows, head_rows)

    definition_label = "governance/task-definition" in labels
    closeout_label = "governance/task-closeout" in labels
    if definition_label and closeout_label:
        raise GovernanceError("task-definition and task-closeout labels are mutually exclusive")

    expected_class = (
        "task-definition" if definition_label else "task-closeout" if closeout_label else None
    )
    if expected_class and pr_class != expected_class:
        raise GovernanceError(f"label requires PR class {expected_class}")
    if pr_class == "task-definition" and not definition_label:
        raise GovernanceError("task-definition PR requires governance/task-definition label")
    if pr_class == "task-closeout" and not closeout_label:
        raise GovernanceError("task-closeout PR requires governance/task-closeout label")

    if pr_class == "release":
        return

    if pr_class == "task-definition":
        if not _docs_only(changed_paths):
            raise GovernanceError("task-definition PR must be documentation-only")
        removed = set(base_rows) - set(head_rows)
        if removed:
            raise GovernanceError(
                "task-definition PR cannot remove existing Task IDs: " + ", ".join(sorted(removed))
            )
        for task_id, after in head_rows.items():
            before = base_rows.get(task_id)
            if after.status == "DONE" and (before is None or before.status != "DONE"):
                raise GovernanceError(f"task-definition PR cannot set DONE: {task_id}")
        changed_definitions = {
            task_id
            for task_id, after in head_rows.items()
            if (before := base_rows.get(task_id)) is None
            or before.status != after.status
            or before.remainder != after.remainder
        }
        if not changed_definitions:
            raise GovernanceError("task-definition PR must define or revise at least one Task ID")
        if changed_definitions != declared_task_ids:
            raise GovernanceError(
                "declared Task ID(s) must equal task-definition changes: "
                f"declared={sorted(declared_task_ids)}, "
                f"changed={sorted(changed_definitions)}"
            )
        return

    missing = set(base_rows) - set(head_rows)
    added = set(head_rows) - set(base_rows)
    if missing or added:
        raise GovernanceError(
            "only task-definition PRs may add/remove TASKS rows: "
            f"added={sorted(added)}, removed={sorted(missing)}"
        )

    if pr_class == "task-closeout":
        if base_ref != "develop":
            raise GovernanceError("task-closeout PR must target develop")
        disallowed = [path for path in changed_paths if not _closeout_path_allowed(path)]
        if disallowed:
            raise GovernanceError("task-closeout PR contains non-closeout paths: " + ", ".join(disallowed))
        completed: set[str] = set()
        for task_id, before in base_rows.items():
            after = head_rows[task_id]
            if before.remainder != after.remainder:
                raise GovernanceError(f"task-closeout cannot rewrite task/acceptance: {task_id}")
            if before.status != after.status:
                if before.status == "DONE" or after.status != "DONE":
                    raise GovernanceError(
                        f"task-closeout only permits non-DONE -> DONE: {task_id}"
                    )
                completed.add(task_id)
        if not completed:
            raise GovernanceError("task-closeout PR must complete at least one task")
        if completed != declared_task_ids:
            raise GovernanceError(
                "declared Task ID(s) must equal closeout transitions: "
                f"declared={sorted(declared_task_ids)}, completed={sorted(completed)}"
            )
        return

    # Ordinary feature/documentation PRs may update only non-DONE status cells.
    if normalize_task_statuses(base_text) != normalize_task_statuses(head_text):
        raise GovernanceError(
            "feature PR cannot redefine TASKS text; use an approved task-definition PR"
        )
    for task_id, before in base_rows.items():
        after = head_rows[task_id]
        if before.status != "DONE" and after.status == "DONE":
            raise GovernanceError(
                f"feature PR cannot set DONE: {task_id}; use a separate task-closeout PR"
            )
    changed_statuses = {
        task_id
        for task_id, before in base_rows.items()
        if before.status != head_rows[task_id].status
    }
    undeclared = changed_statuses - declared_task_ids
    if undeclared:
        raise GovernanceError(
            "TASKS status changes must be declared in Task ID(s): " + ", ".join(sorted(undeclared))
        )


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


def _changed_paths(base_sha: str, head_sha: str) -> list[str]:
    return [line for line in _git("diff", "--name-only", base_sha, head_sha).splitlines() if line]


def _assert_up_to_date(base_sha: str, head_sha: str) -> None:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, head_sha],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise GovernanceError(
            "PR head is not based on the current target SHA; rebase onto the latest target branch"
        )


def check_pull_request(event: Mapping[str, object]) -> None:
    pull_request = event.get("pull_request")
    if not isinstance(pull_request, Mapping):
        raise GovernanceError("pull_request event payload is missing")
    base = pull_request.get("base")
    head = pull_request.get("head")
    if not isinstance(base, Mapping) or not isinstance(head, Mapping):
        raise GovernanceError("pull_request base/head payload is missing")

    base_sha = str(base["sha"]).lower()
    head_sha = str(head["sha"]).lower()
    body = str(pull_request.get("body") or "")
    metadata = validate_body(body, base_sha)

    base_repo = base.get("repo")
    head_repo = head.get("repo")
    if not isinstance(base_repo, Mapping) or not isinstance(head_repo, Mapping):
        raise GovernanceError("pull_request repository identity is missing")
    validate_topology(
        base_ref=str(base["ref"]),
        head_ref=str(head["ref"]),
        base_repository=str(base_repo["full_name"]),
        head_repository=str(head_repo["full_name"]),
        pr_class=metadata["PR class"],
    )

    _assert_up_to_date(base_sha, head_sha)
    workstream_readme = f"{metadata['Workstream']}/README.md"
    _read_blob(head_sha, workstream_readme)

    labels_payload = pull_request.get("labels") or []
    labels = {
        str(item.get("name"))
        for item in labels_payload
        if isinstance(item, Mapping) and item.get("name")
    }
    changed_paths = _changed_paths(base_sha, head_sha)
    validate_task_changes(
        base_text=_read_blob(base_sha, "docs/TASKS.md"),
        head_text=_read_blob(head_sha, "docs/TASKS.md"),
        pr_class=metadata["PR class"],
        labels=labels,
        changed_paths=changed_paths,
        declared_task_ids=task_ids_from_metadata(metadata["Task ID(s)"]),
        base_ref=str(base["ref"]),
    )


def main() -> int:
    if os.environ.get("GITHUB_EVENT_NAME") != "pull_request":
        print("governance: push/non-PR event; PR-only checks skipped")
        return 0
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("governance: GITHUB_EVENT_PATH is required", file=sys.stderr)
        return 2
    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        check_pull_request(event)
    except (GovernanceError, KeyError, json.JSONDecodeError) as exc:
        print(f"governance: FAIL: {exc}", file=sys.stderr)
        return 1
    print("governance: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
