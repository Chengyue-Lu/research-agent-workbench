"""Exact UTF-8 input snapshots with scoped source-admission provenance.

Only caller-authorized Task.input_refs are read. Admission metadata never adds
refs, discovers files, grants egress, or establishes scientific source quality.
"""
from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Iterable, Mapping

from research_workbench.artifacts.admission import (
    SourceAdmission, normalized_relative, path_cites_inbox, path_cites_raw, sidecar_path_for,
)
from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.contracts.common import to_plain
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog


class MaterialInputError(ValueError):
    """A scoped input closure cannot establish the claimed material binding."""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class _CapturedInput:
    reference: FileReference
    normalized: str
    raw: bytes
    text: str

    def pin(self) -> dict[str, Any]:
        return {"path": self.reference.path, "sha256": self.reference.sha256,
                "revision": self.reference.revision}


def _zone_path(path: str) -> str:
    # Windows aliases must not disguise a source zone as an ordinary input.
    return path.casefold()


def _reference(value) -> FileReference:
    try:
        reference = FileReference.from_mapping(to_plain(value))
        if PureWindowsPath(reference.path).drive:
            raise ValueError("input path must not contain a drive")
        return reference
    except (ValueError, TypeError, KeyError) as exc:
        raise MaterialInputError("MATERIAL-INVALID-PIN", "input needs an exact relative FileReference") from exc


def _text_material(captured: _CapturedInput) -> None:
    binary_suffixes = {".pdf", ".docx", ".xlsx", ".pptx", ".zip", ".png", ".jpg", ".jpeg",
                       ".gif", ".webp", ".gz", ".parquet", ".npy", ".npz", ".h5"}
    if Path(captured.normalized).suffix.lower() in binary_suffixes or b"\0" in captured.raw:
        raise MaterialInputError("MATERIAL-UNSUPPORTED-FORMAT",
            f"source material supports UTF-8 text only: {captured.normalized}")


def read_material_inputs(
    root: str | Path, references: Iterable[FileReference | Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Read exactly the supplied pins once and validate selected material edges.

    The caller must supply its exact authorized Task.input_refs (or an already
    authorized subset). A raw source, its conventional admission sidecar, and
    any selected derivative must all be explicitly present. Unselected manifest
    derivatives are metadata only and are never opened. The legacy 1 MiB/file
    and 4 MiB/input-set text behavior is preserved for this version.
    """
    captured = []
    seen = set()
    total = 0
    for value in references:
        reference = _reference(value)
        normalized = normalized_relative(reference.path)
        if path_cites_inbox(_zone_path(normalized)):
            raise MaterialInputError("MATERIAL-INBOX-UNADMITTED", f"inbox input is not admitted: {normalized}")
        path = resolve_within_root(root, reference.path)
        if path is None or not path.is_file():
            raise MaterialInputError("MATERIAL-MISSING-INPUT", f"missing or outside-root input: {reference.path}")
        resolved_relative = path.relative_to(Path(root).resolve()).as_posix()
        if path_cites_inbox(_zone_path(resolved_relative)):
            raise MaterialInputError("MATERIAL-INBOX-UNADMITTED", f"resolved input is not admitted: {reference.path}")
        if ((path_cites_raw(_zone_path(resolved_relative)) or path_cites_raw(_zone_path(normalized)))
                and resolved_relative != normalized):
            raise MaterialInputError("MATERIAL-RAW-BINDING", "source material must use its canonical root-relative path")
        if path in seen:
            raise MaterialInputError("MATERIAL-DUPLICATE-INPUT", f"duplicate input: {reference.path}")
        seen.add(path)
        if path.stat().st_size > 1_048_576:
            raise MaterialInputError("MATERIAL-TEXT-LIMIT", f"input exceeds bounded text limit: {reference.path}")
        raw = path.read_bytes()
        total += len(raw)
        if len(raw) > 1_048_576 or total > 4_194_304:
            raise MaterialInputError("MATERIAL-TEXT-LIMIT", "input snapshot exceeds bounded text limit")
        if hashlib.sha256(raw).hexdigest() != reference.sha256:
            raise MaterialInputError("MATERIAL-HASH-DRIFT", f"input hash mismatch: {reference.path}")
        if reference.revision is not None:
            try:
                document = load_document_bytes(path, raw)
            except Exception as exc:
                raise MaterialInputError("MATERIAL-REVISION-MISMATCH", f"revision input is not a document: {reference.path}") from exc
            if not isinstance(document, Mapping) or document.get("revision") != reference.revision:
                raise MaterialInputError("MATERIAL-REVISION-MISMATCH", f"input revision mismatch: {reference.path}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MaterialInputError("MATERIAL-UNSUPPORTED-FORMAT", "entry supports explicit UTF-8 text inputs only") from exc
        captured.append(_CapturedInput(reference, normalized, raw, text))

    selected = {item.normalized: item for item in captured}
    provenance: dict[str, dict[str, Any]] = {}
    catalog = None
    for sidecar in captured:
        if not sidecar.normalized.endswith(".admission.yaml"):
            continue
        try:
            document = load_document_bytes(sidecar.normalized, sidecar.raw)
        except Exception as exc:
            raise MaterialInputError("MATERIAL-ADMISSION-INVALID", f"cannot parse selected admission: {sidecar.normalized}") from exc
        catalog = catalog or SchemaCatalog()
        if not isinstance(document, Mapping) or catalog.validate("source_admission", document):
            raise MaterialInputError("MATERIAL-ADMISSION-INVALID", f"schema-invalid selected admission: {sidecar.normalized}")
        admission = SourceAdmission.from_mapping(document)
        try:
            acquired = datetime.fromisoformat(admission.acquired_at.replace("Z", "+00:00"))
            if acquired.tzinfo is None or acquired.utcoffset() is None:
                raise ValueError("timestamp needs timezone")
        except ValueError as exc:
            raise MaterialInputError("MATERIAL-ADMISSION-INVALID", "admission acquisition timestamp needs explicit timezone") from exc
        if (sidecar.normalized != sidecar_path_for(admission.admitted_path)
                or not path_cites_raw(admission.admitted_path) or path_cites_inbox(admission.admitted_path)):
            raise MaterialInputError("MATERIAL-RAW-BINDING", f"admission sidecar does not bind its raw path: {sidecar.normalized}")
        raw_input = selected.get(admission.admitted_path)
        if raw_input is None:
            raise MaterialInputError("MATERIAL-UNAUTHORIZED-REFERENCE", f"admission raw pin was not authorized: {admission.admitted_path}")
        if raw_input.reference.sha256 != admission.sha256:
            raise MaterialInputError("MATERIAL-RAW-BINDING", f"raw pin differs from admission hash: {admission.admitted_path}")
        _text_material(raw_input)
        if raw_input.normalized in provenance or sidecar.normalized in provenance:
            raise MaterialInputError("MATERIAL-DERIVATIVE-BINDING", "raw/sidecar also has a selected derivative binding")
        base = {"schema_version": document["schema_version"], "admission_id": admission.admission_id,
                "admission_ref": sidecar.pin(), "raw_ref": raw_input.pin(),
                "acquisition": copy.deepcopy(document["acquisition"]),
                "parser": copy.deepcopy(document["parser"]), "license_or_data_use": admission.license_or_data_use,
                "sensitivity": admission.sensitivity, "egress_restriction": admission.egress_restriction,
                "verification_scope": "selected-input-bytes-and-declared-source-relation",
                "scientific_qualification": "not-established", "permission_grant": False}
        provenance[raw_input.normalized] = {"kind": "raw-source", **base}
        provenance[sidecar.normalized] = {"kind": "source-admission", **base}
        derivative_paths = set()
        for derivative in document.get("derivatives", []):
            relative = normalized_relative(derivative["path"])
            item = selected.get(relative)
            if item is None:
                continue  # Declared metadata is not permission to open a file.
            if relative in derivative_paths or relative in {admission.admitted_path, sidecar.normalized}:
                raise MaterialInputError("MATERIAL-DERIVATIVE-BINDING", "derivative identities must be unique and distinct from raw/sidecar")
            derivative_paths.add(relative)
            digest = derivative["sha256"].removeprefix("sha256:").lower()
            if path_cites_inbox(relative) or item.reference.sha256 != digest:
                raise MaterialInputError("MATERIAL-DERIVATIVE-BINDING", f"selected derivative differs from admission: {relative}")
            if relative in provenance:
                raise MaterialInputError("MATERIAL-DERIVATIVE-BINDING", f"selected derivative has ambiguous source binding: {relative}")
            _text_material(item)
            provenance[relative] = {"kind": "source-derivative", **copy.deepcopy(base),
                "derivative_ref": item.pin(), "relation": derivative["relation"]}

    results = []
    for item in captured:
        if path_cites_raw(_zone_path(item.normalized)) and item.normalized not in provenance:
            raise MaterialInputError("MATERIAL-ADMISSION-MISSING", f"raw input lacks an explicitly authorized admission closure: {item.normalized}")
        evidence = provenance.get(item.normalized, {"kind": "ordinary-input",
            "source_relation": "not-declared", "scientific_qualification": "not-established",
            "gap": "No source relation was declared by an explicitly authorized admission sidecar."})
        results.append({**item.pin(), "text": item.text, "material_provenance": copy.deepcopy(evidence)})
    return tuple(results)


__all__ = ["MaterialInputError", "read_material_inputs"]
