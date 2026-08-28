"""Runner-owned bounded Phase C continuity and verification Gate."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from research_workbench.artifacts.integrity import hash_bytes
from research_workbench.io import load_document_bytes
from research_workbench.research_state.boundaries import AUTHORITY_LIMITS
from research_workbench.validation.documents import (
    LoadedDocuments,
    infer_document_kind,
    validate_documents,
)
from research_workbench.validation.schemas import SchemaCatalog


REQUIRED_PROFILES = {"evidence-synthesis", "simulation-negative"}
REQUIRED_ORACLE_FIELDS = {
    "status",
    "case_id",
    "profile",
    "active_state",
    "method_trace",
    "applied_modes",
    "applied_actions",
    "current_evidence_refs",
    "human_decision_refs",
    "open_items",
    "invalidated_items",
    "candidate_paths",
    "recommended_path",
    "known_failures",
    "actual_binding_status",
    "actual_binding_coverage",
    "authority_limits",
}
ALLOWED_PREDICATES = {
    "known-failed-paths-are-avoided",
    "recommendation-does-not-repeat-known-failure",
    "topic-5-remains-unauthorized",
}


@dataclass(frozen=True, slots=True)
class GateCase:
    manifest: Path
    oracle: Path


def _load_json_object(path: Path) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def _safe_source_path(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    if not normalized or normalized.startswith("/"):
        raise ValueError(f"source path must be repository-relative: {relative!r}")
    parts = normalized.split("/")
    if ".." in parts or ":" in parts[0]:
        raise ValueError(f"source path escapes the project root: {relative!r}")
    candidate = (root / Path(*parts)).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError(f"source path escapes the project root: {relative!r}")
    return candidate


def _manifest_errors(manifest: Mapping[str, Any]) -> list[str]:
    return [
        f"{error.pointer}: {error.message}"
        for error in SchemaCatalog().validate("phase_c_gate_manifest", manifest)
    ]


def _identity(kind: str, document: Mapping[str, Any]) -> tuple[str, int]:
    fields = {
        "research_state": "state_id",
        "research_object": "object_id",
        "research_attempt_lineage": "lineage_id",
        "attempt": "attempt_id",
        "research_failure": "failure_id",
        "task_packet": "task_id",
        "method_resolution": "resolution_id",
        "method_trace": "trace_id",
    }
    identifier = document.get(fields[kind])
    revision = document.get("revision", 1)
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"{kind} lacks its durable identity")
    if not isinstance(revision, int) or revision < 1:
        raise ValueError(f"{kind} has an invalid revision")
    return identifier, revision


def _stage_case(
    manifest: Mapping[str, Any], *, project_root: Path, actor_root: Path, oracle: Path
) -> tuple[Path, Path, list[str]]:
    entries = manifest.get("documents", [])
    aliases: set[str] = set()
    identities: set[tuple[str, int]] = set()
    source_paths: set[Path] = set()
    staged_documents = LoadedDocuments()
    actor_entries: list[dict[str, Any]] = []

    for position, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, Mapping):
            raise ValueError(f"documents[{position}] must be an object")
        alias = str(raw_entry.get("alias", ""))
        if not alias or alias in aliases:
            raise ValueError(f"documents[{position}] has an empty or duplicate alias")
        aliases.add(alias)

        expected_kind = str(raw_entry.get("kind", ""))
        expected_identity = raw_entry.get("identity")
        if not isinstance(expected_identity, Mapping):
            raise ValueError(f"documents[{position}] lacks identity")
        identity = (
            str(expected_identity.get("object_id", "")),
            expected_identity.get("revision"),
        )
        if not identity[0] or not isinstance(identity[1], int):
            raise ValueError(f"documents[{position}] has an invalid identity")
        if identity in identities:
            raise ValueError(f"source manifest repeats identity {identity[0]}@{identity[1]}")
        identities.add(identity)

        source_ref = raw_entry.get("source_ref")
        if not isinstance(source_ref, Mapping):
            raise ValueError(f"documents[{position}] lacks source_ref")
        relative = str(source_ref.get("path", ""))
        source_path = _safe_source_path(project_root, relative)
        if source_path == oracle.resolve():
            raise ValueError("private oracle cannot be part of the actor closure")
        if source_path in source_paths:
            raise ValueError(f"source manifest repeats file path: {relative}")
        source_paths.add(source_path)

        content = source_path.read_bytes()
        actual_hash = hash_bytes(content)
        expected_hash = str(source_ref.get("sha256", "")).removeprefix("sha256:").lower()
        if actual_hash != expected_hash:
            raise ValueError(f"source byte pin drifts for alias {alias}")
        document = load_document_bytes(source_path, content)
        if not isinstance(document, Mapping):
            raise ValueError(f"source document is not an object: {alias}")
        actual_kind = infer_document_kind(document)
        if actual_kind != expected_kind:
            raise ValueError(
                f"source kind mismatch for {alias}: expected {expected_kind}, got {actual_kind}"
            )
        if _identity(expected_kind, document) != identity:
            raise ValueError(f"source identity mismatch for alias {alias}")

        staged_relative = Path("inputs") / Path(*relative.replace("\\", "/").split("/"))
        staged_path = actor_root / staged_relative
        staged_path.parent.mkdir(parents=True, exist_ok=True)
        staged_path.write_bytes(content)
        staged_documents.add(staged_path, document, sha256=actual_hash)
        actor_entries.append(
            {
                "alias": alias,
                "path": staged_relative.as_posix(),
                "sha256": actual_hash,
                "kind": expected_kind,
                "identity": {
                    "object_id": identity[0],
                    "revision": identity[1],
                },
            }
        )

    issues = validate_documents(staged_documents)
    if issues:
        rendered = "; ".join(f"{issue.code}: {issue.message}" for issue in issues[:12])
        raise ValueError(f"runner-owned source closure validation failed: {rendered}")

    actor_manifest = {
        "case_id": manifest["case_id"],
        "profile": manifest["profile"],
        "state_alias": manifest["state_alias"],
        "method_trace_alias": manifest["method_trace_alias"],
        "documents": actor_entries,
        "candidate_paths": manifest["candidate_paths"],
    }
    actor_manifest_path = actor_root / "actor-manifest.json"
    actor_manifest_path.write_text(
        json.dumps(actor_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    answer_path = actor_root / "answer.json"
    expected_surface = [
        "actor-manifest.json",
        *sorted(entry["path"] for entry in actor_entries),
    ]
    return actor_manifest_path, answer_path, expected_surface


def _load_oracle(oracle_path: Path) -> Mapping[str, Any]:
    oracle = _load_json_object(oracle_path)
    required = {"case_id", "exact_output", "exact_read_surface", "predicates"}
    if set(oracle) != required:
        raise ValueError("private oracle must contain exactly case_id/exact_output/exact_read_surface/predicates")
    exact_output = oracle.get("exact_output")
    if not isinstance(exact_output, Mapping) or set(exact_output) != REQUIRED_ORACLE_FIELDS:
        raise ValueError("private oracle exact_output does not satisfy the runner-owned minimum")
    surface = oracle.get("exact_read_surface")
    if not isinstance(surface, list) or not surface or not all(isinstance(item, str) for item in surface):
        raise ValueError("private oracle exact_read_surface must be a non-empty string list")
    predicates = oracle.get("predicates")
    if (
        not isinstance(predicates, list)
        or not predicates
        or not all(isinstance(item, str) and item in ALLOWED_PREDICATES for item in predicates)
        or len(predicates) != len(set(predicates))
    ):
        raise ValueError("private oracle predicates are empty, duplicated, or outside the fixed vocabulary")
    if "topic-5-remains-unauthorized" not in predicates:
        raise ValueError("private oracle must retain the Topic 5 authority ceiling")
    return oracle


def _check_predicate(name: str, answer: Mapping[str, Any]) -> bool:
    candidates = answer.get("candidate_paths", [])
    if not isinstance(candidates, list):
        return False
    by_id = {
        str(item.get("path_id")): str(item.get("classification"))
        for item in candidates
        if isinstance(item, Mapping)
    }
    recommended = answer.get("recommended_path")
    if name == "known-failed-paths-are-avoided":
        return any(value == "known-failed-avoid" for value in by_id.values())
    if name == "recommendation-does-not-repeat-known-failure":
        return isinstance(recommended, str) and by_id.get(recommended) == "recommendable"
    if name == "topic-5-remains-unauthorized":
        return "machine-gate-does-not-authorize-topic-5" in answer.get("authority_limits", [])
    return False


def _evaluate_oracle(
    oracle: Mapping[str, Any],
    answer: Mapping[str, Any],
    *,
    expected_surface: list[str],
) -> list[str]:
    if oracle.get("case_id") != answer.get("case_id"):
        raise ValueError("private oracle case_id does not match actor output")
    declared_surface = list(oracle.get("exact_read_surface", []))
    if declared_surface != expected_surface:
        raise ValueError("private oracle read surface does not match the runner-owned staged closure")
    if answer.get("read_surface") != expected_surface:
        raise ValueError("fresh actor read surface differs from the exact allowlist")
    if answer.get("input_write_surface") != []:
        raise ValueError("fresh actor attempted to write an input or unlisted path")

    exact_output = oracle.get("exact_output", {})
    for field, expected in exact_output.items():
        if answer.get(field) != expected:
            raise ValueError(f"private oracle exact output mismatch: {field}")
    checks = [f"exact:{field}" for field in sorted(exact_output)]
    checks.append("exact:read-surface")
    checks.append("exact:no-input-writes")
    for predicate in oracle.get("predicates", []):
        if not _check_predicate(str(predicate), answer):
            raise ValueError(f"private oracle predicate failed: {predicate}")
        checks.append(f"predicate:{predicate}")
    return checks


def _failure_result(case_id: str, profile: str, problem: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "profile": profile,
        "status": "fail",
        "actor_pid": None,
        "answer_sha256": None,
        "read_surface": [],
        "oracle_checks": [f"blocked:{problem}"],
    }


def run_gate_case(case: GateCase, *, project_root: Path) -> dict[str, Any]:
    """Run one manifest in a fresh actor, then and only then read its private oracle."""

    manifest = _load_json_object(case.manifest.resolve())
    case_id = str(manifest.get("case_id", ""))
    profile = str(manifest.get("profile", ""))
    errors = _manifest_errors(manifest)
    if errors:
        return _failure_result(case_id, profile, "manifest schema: " + "; ".join(errors[:4]))

    try:
        with tempfile.TemporaryDirectory(prefix="rwb-phase-c-") as temporary:
            actor_root = Path(temporary).resolve()
            actor_manifest, answer_path, expected_surface = _stage_case(
                manifest,
                project_root=project_root.resolve(),
                actor_root=actor_root,
                oracle=case.oracle.resolve(),
            )
            environment = dict(os.environ)
            environment.pop("RWB_PHASE_C_ORACLE", None)
            environment["PYTHONHASHSEED"] = "0"
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_workbench.research_state.fresh_actor",
                    str(actor_manifest),
                    str(answer_path),
                ],
                cwd=actor_root,
                env=environment,
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            if completed.returncode != 0 or not answer_path.is_file():
                detail = completed.stderr.strip() or "fresh actor produced no successful output"
                raise ValueError(detail)
            answer_bytes = answer_path.read_bytes()
            answer = json.loads(answer_bytes.decode("utf-8"))
            if not isinstance(answer, Mapping) or answer.get("status") != "ok":
                raise ValueError("fresh actor output is not a successful object")
            actor_pid = answer.get("actor_pid")
            if not isinstance(actor_pid, int) or actor_pid < 1 or actor_pid == os.getpid():
                raise ValueError("fresh actor PID does not prove a distinct process")
            if answer.get("authority_limits") != AUTHORITY_LIMITS:
                raise ValueError("fresh actor authority limits drifted")

            # This is intentionally the first private-oracle read in the case path.
            oracle = _load_oracle(case.oracle.resolve())
            checks = _evaluate_oracle(oracle, answer, expected_surface=expected_surface)
            return {
                "case_id": case_id,
                "profile": profile,
                "status": "pass",
                "actor_pid": actor_pid,
                "answer_sha256": hash_bytes(answer_bytes),
                "read_surface": answer["read_surface"],
                "oracle_checks": checks,
            }
    except Exception as exc:
        return _failure_result(case_id, profile, str(exc))


def run_phase_c_gate(cases: Sequence[GateCase], *, project_root: Path) -> dict[str, Any]:
    """Run exactly the two canonical bounded profiles and return a runner-owned report."""

    if len(cases) != 2:
        raise ValueError("Phase C Gate requires exactly two bounded cases")
    headers: list[tuple[str, str]] = []
    for case in cases:
        manifest = _load_json_object(case.manifest.resolve())
        headers.append((str(manifest.get("case_id", "")), str(manifest.get("profile", ""))))
    if len({case_id for case_id, _ in headers}) != 2:
        raise ValueError("Phase C Gate case_id values must be unique")
    if {profile for _, profile in headers} != REQUIRED_PROFILES:
        raise ValueError("Phase C Gate requires one evidence-synthesis and one simulation-negative case")

    results = [run_gate_case(case, project_root=project_root) for case in cases]
    report = {
        "schema_version": "0.1.0",
        "gate_id": "PHASE-C-M10-003-BOUNDED-GATE",
        "machine_gate": {
            "status": "pass" if all(item["status"] == "pass" for item in results) else "fail",
            "cases": results,
        },
        "human_semantic_review": {
            "status": "pending",
            "actor": None,
            "evidence_ref": None,
        },
        "r2_closeout": {
            "status": "pending",
            "actor": None,
            "evidence_ref": None,
        },
        "phase_c_closeout": "pending",
        "boundaries": {
            "reviewer_reconstruction_proven": False,
            "scientific_correctness_proven": False,
            "topic_5_authorized": False,
        },
    }
    errors = SchemaCatalog().validate("phase_c_gate_report", report)
    if errors:
        rendered = "; ".join(f"{error.pointer}: {error.message}" for error in errors)
        raise ValueError(f"runner produced an invalid Phase C Gate report: {rendered}")
    return report
