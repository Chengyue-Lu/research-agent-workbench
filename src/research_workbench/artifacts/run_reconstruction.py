"""Bounded, file-pinned Python Run reconstruction without an Agent session."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench.artifacts.admission import check_raw_reference_admission, path_cites_inbox
from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.contracts.common import ContractError
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog


AUTHORITY_BOUNDARIES = {
    "claim_acceptance": False,
    "human_decision": False,
    "scientific_correctness": False,
    "promotion": False,
}


class ReconstructionError(ValueError):
    def __init__(self, status: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status


def _schema(kind: str, document: Any, catalog: SchemaCatalog) -> None:
    errors = catalog.validate(kind, document)
    if errors:
        raise ReconstructionError("manifest-invalid", "; ".join(
            f"{error.pointer}: {error.message}" for error in errors[:4]
        ))


def _read_pin(root: Path, raw: Mapping[str, Any]) -> bytes:
    reference = FileReference.from_mapping(raw)
    path = resolve_within_root(root, reference.path)
    if path is None or path_cites_inbox(reference.path):
        raise ReconstructionError("manifest-invalid", f"reference outside admitted/root boundary: {reference.path}")
    if not path.is_file():
        raise ReconstructionError("prerequisite-missing", f"missing reference: {reference.path}")
    content = path.read_bytes()
    if hash_bytes(content) != reference.sha256.removeprefix("sha256:").lower():
        raise ReconstructionError("pin-drift", f"changed reference: {reference.path}")
    admission = check_raw_reference_admission(root, reference.path, reference_sha256=reference.sha256)
    if admission:
        raise ReconstructionError("manifest-invalid", "; ".join(item.message for item in admission))
    return content


def _document(raw_ref: Mapping[str, Any], content: bytes) -> Mapping[str, Any]:
    try:
        document = load_document_bytes(str(raw_ref["path"]), content)
    except (ValueError, yaml.YAMLError) as exc:
        raise ReconstructionError("manifest-invalid", f"invalid pinned document: {exc}") from exc
    if not isinstance(document, Mapping):
        raise ReconstructionError("manifest-invalid", "referenced document must be an object")
    return document


def _key(raw_ref: Mapping[str, Any]) -> tuple[str, str]:
    reference = FileReference.from_mapping(raw_ref)
    return reference.path.replace("\\", "/"), reference.sha256.removeprefix("sha256:").lower()


def _object_key(raw: Any) -> tuple[str, int, str | None]:
    if isinstance(raw, str):
        identifier, separator, revision_text = raw.partition("@")
        if not separator or not identifier or not revision_text.isdecimal() or int(revision_text) < 1:
            raise ReconstructionError("manifest-invalid", "Run object references must include an explicit positive revision")
        return identifier, int(revision_text), None
    digest = raw.get("sha256")
    return raw["object_id"], raw["revision"], digest.removeprefix("sha256:").lower() if digest else None


def _object_set(references: list[Any]) -> set[tuple[str, int, str | None]]:
    keys = [_object_key(reference) for reference in references]
    if len({key[:2] for key in keys}) != len(keys):
        raise ReconstructionError("manifest-invalid", "duplicate Run object identity/revision binding")
    return set(keys)


def _check_run_bindings(run: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    if run["revision"] != manifest["run_ref"]["revision"]:
        raise ReconstructionError("manifest-invalid", "run_ref revision differs from the declared Run revision")
    inputs = manifest["input_bindings"]
    if _object_set(run["input_refs"]) != _object_set([item["object_ref"] for item in inputs]):
        raise ReconstructionError("manifest-invalid", "Run input_refs differ from exact input bindings")
    # ObjectRef hashes retain their declared logical meaning; FileRefs alone pin bytes.
    def file_key(reference: Mapping[str, Any]) -> tuple[str, str, int | None]:
        return (*_key(reference), reference.get("revision"))

    if {item["role"] for item in inputs} != {"input", "parameters"}:
        raise ReconstructionError("manifest-invalid", "input bindings need exactly one input and one parameters role")
    for item in inputs:
        if file_key(item["file_ref"]) != file_key(manifest[f"{item['role']}_ref"]):
            raise ReconstructionError("manifest-invalid", "input binding file differs from its executed role")
    environment = manifest["environment_binding"]
    if (_object_key(run["environment_ref"]) != _object_key(environment["object_ref"])
            or file_key(environment["file_ref"]) != file_key(manifest["environment_ref"])):
        raise ReconstructionError("manifest-invalid", "Run environment_ref differs from the executed environment binding")
    if _object_set(run["output_refs"]) != _object_set([
        output["object_ref"] for output in manifest["expected_outputs"]
    ]):
        raise ReconstructionError("manifest-invalid", "Run output_refs differ from expected artifact bindings")


def _capture(root: Path, manifest: Mapping[str, Any]) -> tuple[dict[str, bytes], dict[str, bytes]]:
    catalog = SchemaCatalog()
    _schema("run_reconstruction_manifest", manifest, catalog)
    roles = ("run_ref", "code_ref", "input_ref", "parameters_ref", "environment_ref")
    captured = {role: _read_pin(root, manifest[role]) for role in roles}
    if len({_key(manifest[role])[0].casefold() for role in roles}) != len(roles):
        raise ReconstructionError("manifest-invalid", "Run, code, input, parameters and environment must be distinct files")
    run = _document(manifest["run_ref"], captured["run_ref"])
    _schema("research_object", run, catalog)
    if run.get("object_type") != "run" or run.get("object_id") != manifest["run_id"]:
        raise ReconstructionError("manifest-invalid", "run_ref must identify the declared Run")
    _check_run_bindings(run, manifest)
    environment = _document(manifest["environment_ref"], captured["environment_ref"])
    _schema("run_reconstruction_environment", environment, catalog)
    expected: dict[str, bytes] = {}
    casefolded: set[str] = set()
    artifact_paths: set[str] = set()
    for output in manifest["expected_outputs"]:
        name = output["output_path"]
        if name.casefold() in casefolded:
            raise ReconstructionError("manifest-invalid", "expected output paths must be unique")
        casefolded.add(name.casefold())
        artifact_path = _key(output["artifact_ref"])[0].casefold()
        if artifact_path in artifact_paths or artifact_path in {_key(manifest[role])[0].casefold() for role in roles}:
            raise ReconstructionError("manifest-invalid", "expected output artifacts must be distinct from each other and input files")
        artifact_paths.add(artifact_path)
        expected[name] = _read_pin(root, output["artifact_ref"])
    receipt_ref = manifest.get("promotion_receipt_ref")
    if receipt_ref is not None:
        captured["promotion_receipt_ref"] = _read_pin(root, receipt_ref)
        receipt = _document(receipt_ref, captured["promotion_receipt_ref"])
        _schema("promotion_execution_receipt", receipt, catalog)
        canonical_path = f"runs/promotions/{receipt['promotion_id']}/receipt.json"
        if (receipt_ref["path"] != canonical_path
                or resolve_within_root(root, canonical_path) != root / canonical_path):
            raise ReconstructionError("manifest-invalid", "Promotion Receipt must use its canonical, unaliased promotion path")
        published = {_key(item["target_ref"]) for item in receipt["target_artifact_refs"]}
        for output in manifest["expected_outputs"]:
            if _key(output["artifact_ref"]) not in published:
                raise ReconstructionError("manifest-invalid", "expected artifact is not a target in the pinned Promotion Receipt")
    return captured, expected


def check_run_manifest(root: str | Path, manifest: Mapping[str, Any]) -> list[dict[str, str]]:
    """Check declared exact closure without running code or promotion validators."""
    try:
        _capture(Path(root).resolve(), manifest)
    except (ReconstructionError, ContractError, ValueError, OSError) as exc:
        return [{"status": getattr(exc, "status", "manifest-invalid"), "detail": str(exc)}]
    return []


def _environment_matches(document: Mapping[str, Any]) -> bool:
    return (
        document["python_implementation"] == platform.python_implementation()
        and document["python_version"] == platform.python_version()
        and document["platform"] == sys.platform
    )


def _child_environment() -> dict[str, str]:
    keep = {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR"}
    result = {key: value for key, value in os.environ.items() if key.upper() in keep}
    result.update(PYTHONHASHSEED="0", PYTHONDONTWRITEBYTECODE="1", TZ="UTC")
    return result


def _attempt_directory(root: Path, attempt_dir: str | Path) -> Path:
    raw = Path(attempt_dir)
    path = (raw if raw.is_absolute() else root / raw).resolve()
    if not path.is_relative_to(root / "work") or path == root / "work":
        raise ContractError("attempt_dir", "must be a new directory inside root/work")
    path.mkdir(parents=True, exist_ok=False)
    return path


def reproduce_run(
    root: str | Path,
    manifest_path: str | Path,
    *,
    attempt_dir: str | Path,
) -> dict[str, Any]:
    """Run one explicitly pinned, trusted standard-library program in a fresh cwd.

    Isolation removes Agent/session imports; it is not an OS sandbox. Callers
    must trust the pinned code. Every ordinary failure is retained in work.
    """
    root = Path(root).resolve()
    raw_path = Path(manifest_path)
    path = (raw_path if raw_path.is_absolute() else root / raw_path).resolve()
    if not path.is_relative_to(root):
        raise ContractError("manifest", "must be a file inside root")
    content = path.read_bytes()
    try:
        manifest = load_document_bytes(path, content)
    except (ValueError, yaml.YAMLError) as exc:
        raise ContractError("manifest", f"cannot parse reconstruction manifest: {exc}") from exc
    destination = _attempt_directory(root, attempt_dir)
    report: dict[str, Any] = {
        "schema_version": "0.1.0", "reconstruction_id": destination.name,
        "report_kind": "run-reconstruction",
        "manifest_ref": {"path": path.relative_to(root).as_posix(), "sha256": hash_bytes(content)},
        "status": "manifest-invalid", "detail": "", "executed": False,
        "returncode": None, "duration_seconds": 0.0, "comparisons": [],
        "staged_refs": [], "output_refs": [],
        "authority_boundaries": dict(AUTHORITY_BOUNDARIES),
        "limitations": ["Current reconstruction only; no historical or scientific authority.",
                        "Pinned program bytes are not bound to the Run's declared Method implementation.",
                        "Trusted code; fresh cwd and isolated Python are not an OS sandbox."],
    }
    stdout = b""
    stderr = b""
    outputs: Path | None = None
    try:
        captured, expected = _capture(root, manifest)
        report["run_id"] = manifest["run_id"]
        report["negative_result"] = manifest["negative_result"]
        if "promotion_receipt_ref" in manifest:
            report["promotion_receipt_ref"] = manifest["promotion_receipt_ref"]
        environment = _document(manifest["environment_ref"], captured["environment_ref"])
        if not _environment_matches(environment):
            raise ReconstructionError("prerequisite-missing", "current Python implementation/version/platform differs from pinned environment")
        stage = destination / "staged"
        stage.mkdir()
        outputs = stage / "outputs"
        outputs.mkdir()
        for role, name in (("code_ref", "program.py"), ("input_ref", "inputs.json"),
                           ("parameters_ref", "parameters.json"), ("environment_ref", "environment.json")):
            (stage / name).write_bytes(captured[role])
            report["staged_refs"].append({"path": (stage / name).relative_to(root).as_posix(),
                                          "sha256": hash_bytes(captured[role])})
        command = [sys.executable, "-I", "-S", "program.py", "inputs.json", "parameters.json", "outputs"]
        report["command"] = ["<pinned-python>", *command[1:]]
        report["cwd"] = stage.relative_to(root).as_posix()
        report["python"] = {"implementation": platform.python_implementation(),
                            "version": platform.python_version(), "platform": sys.platform}
        started = time.monotonic()
        process = subprocess.Popen(command, cwd=stage, env=_child_environment(),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        report["executed"] = True
        report["child_pid"] = process.pid
        try:
            stdout, stderr = process.communicate(timeout=manifest["timeout_seconds"])
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise ReconstructionError("run-failed", "simulation exceeded timeout")
        finally:
            report["duration_seconds"] = round(time.monotonic() - started, 6)
            report["returncode"] = process.returncode
        if process.returncode != 0:
            raise ReconstructionError("run-failed", "simulation returned a nonzero exit code")
        actual: dict[str, bytes] = {}
        for output in outputs.rglob("*"):
            if output.is_symlink() or not output.resolve().is_relative_to(outputs.resolve()):
                raise ReconstructionError("run-failed", "simulation output escapes its output directory")
            if output.is_file():
                actual[output.relative_to(outputs).as_posix()] = output.read_bytes()
        for name in sorted(set(expected) | set(actual)):
            expected_hash = hash_bytes(expected[name]) if name in expected else None
            actual_hash = hash_bytes(actual[name]) if name in actual else None
            report["comparisons"].append({"output_path": name, "expected_sha256": expected_hash,
                                           "actual_sha256": actual_hash,
                                           "matched": expected_hash == actual_hash})
        report["status"] = "matched" if all(item["matched"] for item in report["comparisons"]) else "output-different"
        report["detail"] = "Exact output set and bytes match." if report["status"] == "matched" else "Output set or bytes differ; both versions are preserved."
    except (ReconstructionError, ContractError, ValueError, OSError) as exc:
        report["status"] = getattr(exc, "status", "run-failed")
        report["detail"] = str(exc)
    if outputs is not None:
        for output in sorted(outputs.rglob("*")):
            if output.is_file() and not output.is_symlink() and output.resolve().is_relative_to(outputs.resolve()):
                report["output_refs"].append({"path": output.relative_to(root).as_posix(),
                                              "sha256": hash_bytes(output.read_bytes())})
    (destination / "stdout.txt").write_bytes(stdout)
    (destination / "stderr.txt").write_bytes(stderr)
    report["stdout_ref"] = {"path": (destination / "stdout.txt").relative_to(root).as_posix(), "sha256": hash_bytes(stdout)}
    report["stderr_ref"] = {"path": (destination / "stderr.txt").relative_to(root).as_posix(), "sha256": hash_bytes(stderr)}
    report_path = destination / "reconstruction-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
