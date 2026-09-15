"""Exact Skill consumption observations; no Supply selection or admission."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.capability.projection_supply import (
    projection_reference, projection_supply_fact_issues,
)
from research_workbench.io import load_document_bytes
from research_workbench.validation.schemas import SchemaCatalog


SKILL_CLOSEOUT_CONTRACT = "skill-execution@1.0.0"


class SkillExecutionFactError(ValueError):
    pass


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _frozen(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _frozen(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_frozen(item) for item in value)
    return value


def _hash(value: str) -> str:
    return value.removeprefix("sha256:").lower()


@dataclass(frozen=True, slots=True)
class ObservedSkillInputs:
    """The exact parsed bytes to consume, together with their observation."""

    project_root: Path
    consumption: Mapping[str, Any]
    supply: Mapping[str, Any]
    projection: Mapping[str, Any]


def _load(root: Path, pin: Mapping[str, str], kind: str, catalog: SchemaCatalog):
    path = resolve_within_root(root, pin.get("path", ""))
    if path is None or not path.is_file():
        raise SkillExecutionFactError(f"{kind} missing or outside project root")
    content = path.read_bytes()
    if hash_bytes(content) != _hash(pin.get("sha256", "")):
        raise SkillExecutionFactError(f"{kind} hash mismatch")
    try:
        document = load_document_bytes(path, content)
    except Exception as exc:
        raise SkillExecutionFactError(f"{kind} is not parseable") from exc
    if catalog.validate(kind, document):
        raise SkillExecutionFactError(f"{kind} is schema-invalid")
    return path, document, hash_bytes(content)


def read_skill_execution_inputs(
    project_root: str | Path,
    supply_report: Mapping[str, str],
    *,
    schema_root: str | Path | None = None,
) -> ObservedSkillInputs:
    """Read the explicitly bound Supply and its Projection once, by exact pin.

    This reader does not discover candidates or choose a Supply. The producer
    consumes the returned immutable documents instead of reopening their paths.
    """
    root = Path(project_root).resolve()
    catalog = SchemaCatalog(schema_root)
    path, supply, digest = _load(root, supply_report, "capability_supply_report", catalog)
    identity = supply["supply_identity"]
    actual_ref = f"{supply['report_id']}@{supply['version']}"
    if "ref" in supply_report and supply_report["ref"] != actual_ref:
        raise SkillExecutionFactError("Supply identity differs from its external pin")
    if identity["supply_kind"] != "skill":
        raise SkillExecutionFactError("Skill consumption requires Skill Supply")
    reference = identity["skill_release_projection_ref"]
    projection_path, projection, projection_digest = _load(
        root, {"path": reference["document_path"], "sha256": reference["content_hash"]},
        "skill_release_projection", catalog,
    )
    if projection_reference(projection) != reference["ref"]:
        raise SkillExecutionFactError("Projection identity mismatch")
    issues = projection_supply_fact_issues(projection, supply)
    if issues:
        raise SkillExecutionFactError("Projection/Supply facts mismatch: " + str(issues))
    components = [item for item in identity["components"] if item["component_kind"] == "skill"]
    # projection_supply_fact_issues already requires exactly one matching Skill.
    component = _plain(components[0])
    component["content_hash"] = _hash(component["content_hash"])
    release = projection["release"]
    consumption = {
        "schema_version": "0.1.0", "contract_version": "1.0.0",
        "record_kind": "skill_execution_consumption",
        "supply_report_ref": {
            "ref": actual_ref,
            "path": path.relative_to(root).as_posix(), "sha256": digest,
        },
        "projection_ref": {
            "ref": projection_reference(projection),
            "path": projection_path.relative_to(root).as_posix(), "sha256": projection_digest,
        },
        "skill": {"skill_id": release["skill_id"], "skill_version": release["skill_version"],
                  "content_hash": _hash(release["content_hash"])},
        "component": component,
    }
    return ObservedSkillInputs(root, _frozen(consumption), _frozen(supply), _frozen(projection))


def validate_skill_consumption(project_root, consumption, *, schema_root=None) -> ObservedSkillInputs:
    catalog = SchemaCatalog(schema_root)
    if catalog.validate("skill_execution_consumption", _plain(consumption)):
        raise SkillExecutionFactError("Skill consumption is schema-invalid")
    observed = read_skill_execution_inputs(
        project_root, consumption["supply_report_ref"], schema_root=schema_root,
    )
    if _plain(observed.consumption) != _plain(consumption):
        raise SkillExecutionFactError("Skill consumption identity/component/pin drift")
    return observed


def selected_skill_consumption(view, *, schema_root=None) -> Mapping[str, Any]:
    """Recompute requested identity only; this is never an actual-use fact."""
    selected = view.document["selected_supply_report_ref"]
    observed = read_skill_execution_inputs(view.project_root, selected, schema_root=schema_root)
    return observed.consumption


def record_skill_execution_use(
    recorder, observed: ObservedSkillInputs, *, fact_id: str,
    view_ref: Mapping[str, Any],
) -> Mapping[str, str]:
    """Persist observations at the producer's consumption boundary, before use."""
    consumption = _plain(observed.consumption)
    for key in ("supply_report_ref", "projection_ref"):
        ref = consumption[key]
        recorder.record_content_read(
            ref["path"], access="content", allowlist_basis="bound Skill execution input",
            content_sha256=ref["sha256"],
        )
    reference = recorder.record_decision_snapshot(
        f"skill-execution-fact-{fact_id}",
        {
            "schema_version": "0.1.0", "contract_version": "1.0.0", "fact_id": fact_id,
            "record_kind": "skill-input-consumption", "attempt_id": recorder.attempt_id,
            "view_ref": _plain(view_ref), "execution_phase": "use-boundary",
            "actual_skill_consumption": consumption,
            "boundaries": {"actual_fact": True, "supply_selection": False, "rebinding": False,
                           "method_decision": False, "task_completion": False,
                           "claim_effect": False, "human_decision": False},
        },
    )
    _record_fact_creation(recorder, observed, reference, "Skill inputs consumed before execution")
    return reference


def _record_fact_creation(recorder, observed, reference, reason):
    fact_path = (recorder.attempt_dir / reference["path"]).relative_to(observed.project_root).as_posix()
    recorder.record_file_revision(
        fact_path, action="created", new_sha256=reference["sha256"],
        reason=reason,
    )


def record_skill_execution_result(
    recorder, observed: ObservedSkillInputs, *, fact_id: str,
    view_ref: Mapping[str, Any], actual_binding: Mapping[str, Any],
    actual_supply_report_ref: str,
) -> Mapping[str, str]:
    """Persist independently observed post-call binding using the Core fact contract."""
    reference = recorder.record_execution_fact(
        fact_id=fact_id, view_ref=_plain(view_ref), actual_binding=_plain(actual_binding),
        actual_supply_report_ref=actual_supply_report_ref,
    )
    _record_fact_creation(recorder, observed, reference, "Actual execution binding observed after execution")
    return reference
