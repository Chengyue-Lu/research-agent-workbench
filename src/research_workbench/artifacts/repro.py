"""Run manifest reproduction checks (M4-004).

A run must remain understandable and rebuildable without the original agent
session: declared inputs, parameters, environment lock, and outputs are
hash-checked, and an optional rerun directory can be compared byte-for-byte.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.artifacts.integrity import (
    ReferenceStatus,
    check_file_reference,
    resolve_within_root,
)
from research_workbench.contracts.common import ContractError, require_relative_path, require_string
from research_workbench.contracts.risks import ContractRisk, RiskLevel
from research_workbench.tasks.models import FileReference

RUN_STATUSES = {"planned", "running", "completed", "incomplete", "failed"}


@dataclass(frozen=True, slots=True)
class RunManifest:
    run_id: str
    status: str
    input_refs: tuple[FileReference, ...]
    parameters_ref: FileReference
    lock_ref: FileReference
    task_ref: str
    outputs: tuple[FileReference, ...]
    skill_assignment_ref: str | None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "RunManifest":
        try:
            environment = data["environment"]
            agent_execution = data["agent_execution"]
            return cls(
                run_id=require_string(data, "run_id"),
                status=require_string(data, "status"),
                input_refs=tuple(FileReference.from_mapping(item) for item in data["input_refs"]),
                parameters_ref=FileReference.from_mapping(data["parameters_ref"]),
                lock_ref=FileReference.from_mapping(environment["lock_ref"]),
                task_ref=require_relative_path(
                    require_string(agent_execution, "task_ref"), "task_ref"
                ).replace("\\", "/"),
                outputs=tuple(FileReference.from_mapping(item) for item in data["outputs"]),
                skill_assignment_ref=(
                    require_relative_path(
                        require_string(agent_execution, "skill_assignment_ref"),
                        "skill_assignment_ref",
                    ).replace("\\", "/")
                    if "skill_assignment_ref" in agent_execution
                    else None
                ),
            )
        except KeyError as exc:
            raise ContractError(str(exc.args[0]), "is required") from exc

    @property
    def has_no_skill_path(self) -> bool:
        return self.skill_assignment_ref is None


def check_run_manifest(
    root: str | Path,
    data: Mapping[str, Any],
    rerun_dir: str | Path | None = None,
) -> list[ContractRisk]:
    """Verify declared reproduction facts and optionally compare a rerun."""

    risks: list[ContractRisk] = []
    manifest = RunManifest.from_mapping(data)
    if manifest.status not in RUN_STATUSES:
        risks.append(
            ContractRisk(
                "REPRO-GAP", RiskLevel.BLOCK, f"unknown run status: {manifest.status!r}"
            )
        )
    elif manifest.status != "completed":
        risks.append(
            ContractRisk(
                "REPRO-GAP",
                RiskLevel.WARNING,
                f"{manifest.run_id}: status is {manifest.status!r}; outputs describe a partial run",
            )
        )

    for input_ref in manifest.input_refs:
        risks.extend(_file_risks(root, input_ref, "input"))
    risks.extend(_file_risks(root, manifest.parameters_ref, "parameters_ref"))
    risks.extend(_file_risks(root, manifest.lock_ref, "environment.lock_ref"))

    task_path = resolve_within_root(root, manifest.task_ref)
    if task_path is None:
        risks.append(
            ContractRisk(
                "REF-OUTSIDE-ROOT",
                RiskLevel.BLOCK,
                f"task_ref escapes root: {manifest.task_ref}",
            )
        )
    elif not task_path.is_file():
        risks.append(
            ContractRisk(
                "REF-MISSING", RiskLevel.BLOCK, f"task file is missing: {manifest.task_ref}"
            )
        )
    if manifest.skill_assignment_ref is not None:
        assignment = resolve_within_root(root, manifest.skill_assignment_ref)
        if assignment is None or not assignment.is_file():
            risks.append(
                ContractRisk(
                    "REF-MISSING",
                    RiskLevel.BLOCK,
                    f"skill assignment is missing: {manifest.skill_assignment_ref}",
                )
            )

    for output in manifest.outputs:
        risks.extend(_file_risks(root, output, "output"))

    if rerun_dir is not None:
        from research_workbench.artifacts.integrity import hash_file

        rerun_root = Path(rerun_dir)
        for output in manifest.outputs:
            rerun_path = rerun_root / Path(output.path).name
            if not rerun_path.is_file():
                risks.append(
                    ContractRisk(
                        "REPRO-GAP",
                        RiskLevel.BLOCK,
                        f"rerun did not reproduce output: {output.path}",
                    )
                )
                continue
            if hash_file(rerun_path) != output.sha256.removeprefix("sha256:").lower():
                risks.append(
                    ContractRisk(
                        "ARTIFACT-HASH-MISMATCH",
                        RiskLevel.BLOCK,
                        f"rerun output differs from recorded output: {output.path}",
                    )
                )
    return risks


def _file_risks(root: str | Path, reference: FileReference, label: str) -> list[ContractRisk]:
    check = check_file_reference(root, reference)
    if check.status == ReferenceStatus.OK:
        return []
    if check.status == ReferenceStatus.MISSING:
        return [
            ContractRisk(
                "REPRO-GAP", RiskLevel.BLOCK, f"{label} is missing: {reference.path}"
            )
        ]
    if check.status == ReferenceStatus.OUTSIDE_ROOT:
        return [
            ContractRisk(
                "REF-OUTSIDE-ROOT", RiskLevel.BLOCK, f"{label} escapes root: {reference.path}"
            )
        ]
    return [
        ContractRisk(
            "ARTIFACT-HASH-MISMATCH",
            RiskLevel.BLOCK,
            f"{label} bytes differ from declared sha256: {reference.path}",
        )
    ]
