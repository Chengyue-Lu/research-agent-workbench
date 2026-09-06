"""Read-only localization of declared Claim evidence and file provenance."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench.artifacts.admission import (
    SourceAdmission,
    path_cites_inbox,
    path_cites_raw,
    sidecar_path_for,
)
from research_workbench.artifacts.integrity import hash_bytes, resolve_within_root
from research_workbench.io import load_document_bytes
from research_workbench.research_state.closure import ClosureIndex
from research_workbench.validation.document_core import LoadedDocuments
from research_workbench.validation.schemas import SchemaCatalog


def _digest(value: str) -> str:
    return value.lower().removeprefix("sha256:")


def _identity(reference: str | Mapping[str, Any]) -> tuple[str, int]:
    if isinstance(reference, str):
        identifier, separator, revision = reference.rpartition("@")
        if not separator or not identifier or not revision.isdigit() or int(revision) < 1:
            raise ValueError(f"reference must have an exact revision: {reference}")
        return identifier, int(revision)
    return reference["object_id"], reference["revision"]


class _ReadSet:
    def __init__(self, root: Path, catalog: SchemaCatalog) -> None:
        self.root = root
        self.catalog = catalog
        self.contents: dict[Path, tuple[bytes, str]] = {}
        self.documents: dict[tuple[Path, str], Mapping[str, Any]] = {}

    def read(self, reference: Mapping[str, Any]) -> tuple[Path, bytes]:
        relative = reference["path"]
        path = resolve_within_root(self.root, relative)
        if path is None:
            raise ValueError(f"REF-OUTSIDE-ROOT: {relative}")
        if path_cites_inbox(relative) or path_cites_inbox(path.relative_to(self.root).as_posix()):
            raise ValueError(f"ARTIFACT-INBOX-CITATION: {relative}")
        if path not in self.contents:
            try:
                content = path.read_bytes()
                self.contents[path] = (content, hash_bytes(content))
            except OSError as exc:
                raise ValueError(f"REF-MISSING: {relative}: {exc.strerror}") from exc
        content, digest = self.contents[path]
        if digest != _digest(reference["sha256"]):
            raise ValueError(f"REF-HASH-MISMATCH: {relative}")
        return path, content

    def document(self, reference: Mapping[str, Any], kind: str) -> Mapping[str, Any]:
        path, content = self.read(reference)
        key = (path, kind)
        if key in self.documents:
            return self.documents[key]
        try:
            document = load_document_bytes(path, content)
        except (ValueError, yaml.YAMLError) as exc:
            raise ValueError(f"DOCUMENT-INVALID: {reference['path']}: {exc}") from exc
        errors = self.catalog.validate(kind, document)
        if errors:
            first = errors[0]
            raise ValueError(f"SCHEMA-INVALID: {reference['path']}{first.pointer}: {first.message}")
        self.documents[key] = document
        return document


def _source_provenance(
    reads: _ReadSet, binding: Mapping[str, Any]
) -> dict[str, Any]:
    artifact = binding["artifact_ref"]
    reads.read(artifact)
    provenance = binding["provenance_ref"]
    if path_cites_raw(artifact["path"]):
        if provenance["path"] != sidecar_path_for(artifact["path"]):
            raise ValueError("ARTIFACT-MISSING-PROVENANCE: raw source needs its exact admission sidecar")
        admission = reads.document(provenance, "source_admission")
        admitted = SourceAdmission.from_mapping(admission)
        if (admitted.admitted_path != artifact["path"]
                or admitted.sha256 != _digest(artifact["sha256"])):
            raise ValueError("ARTIFACT-MISSING-PROVENANCE: admission does not bind this source")
        return {"kind": "source_admission", "receipt_ref": dict(provenance)}

    receipt = reads.document(provenance, "promotion_execution_receipt")
    record = reads.document(receipt["promotion_record_ref"], "promotion_record")
    if record["promotion_id"] != receipt["promotion_id"]:
        raise ValueError("ARTIFACT-MISSING-PROVENANCE: receipt and record identities differ")
    matches = [
        item for item in receipt["target_artifact_refs"]
        if item["target_ref"]["path"] == artifact["path"]
        and _digest(item["target_ref"]["sha256"]) == _digest(artifact["sha256"])
    ]
    retained = [
        entry for entry in record["entries"]
        if entry["disposition"] == "retain-in-work"
        and entry["artifact"]["path"] == artifact["path"]
        and _digest(entry["artifact"]["sha256"]) == _digest(artifact["sha256"])
        and entry["artifact"] in receipt["source_artifact_refs"]
    ]
    if not matches and len(retained) == 1:
        return {
            "kind": "promotion_execution_receipt", "disposition": "retain-in-work",
            "receipt_ref": dict(provenance),
            "promotion_record_ref": dict(receipt["promotion_record_ref"]),
            "negative_result": retained[0]["negative_result"], "reason": retained[0]["reason"],
        }
    if len(matches) != 1 or retained:
        raise ValueError("ARTIFACT-MISSING-PROVENANCE: receipt must map this exact target once")
    source = matches[0]["source_ref"]
    if source not in receipt["source_artifact_refs"] or _digest(source["sha256"]) != _digest(artifact["sha256"]):
        raise ValueError("ARTIFACT-MISSING-PROVENANCE: promotion source/target mapping differs")
    reads.read(source)
    entries = [
        entry for entry in record["entries"]
        if entry["disposition"] == "promote"
        and entry["artifact"] == source
        and entry["target"] == artifact["path"]
    ]
    if len(entries) != 1:
        raise ValueError("ARTIFACT-MISSING-PROVENANCE: record does not select this promotion")
    return {
        "kind": "promotion_execution_receipt",
        "disposition": "promote", "negative_result": entries[0]["negative_result"],
        "receipt_ref": dict(provenance),
        "promotion_record_ref": dict(receipt["promotion_record_ref"]),
        "work_source_ref": dict(source),
    }


def localize_claim(
    root: str | Path,
    evidence_map: Mapping[str, Any],
    *,
    claim_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve one explicit evidence map; never execute, promote or accept a Claim.

    Byte checks use a per-invocation captured read set. ObjectRef hashes retain
    their existing content_hash semantics; they are not substituted for FileRefs.
    """
    catalog = SchemaCatalog()
    errors = catalog.validate("claim_evidence_map", evidence_map)
    if errors:
        first = errors[0]
        raise ValueError(f"SCHEMA-INVALID: {first.pointer}: {first.message}")
    reads = _ReadSet(Path(root).resolve(), catalog)
    claim_ref = evidence_map["claim_ref"]
    if claim_path is not None and Path(claim_path).resolve() != resolve_within_root(reads.root, claim_ref["path"]):
        raise ValueError("claim argument does not match evidence map claim_ref")
    claim = reads.document(claim_ref, "research_object")
    if claim["object_type"] != "claim":
        raise ValueError("OBJECT-NOT-CLAIM: evidence map must reference a Claim")
    problems: list[str] = []
    documents = LoadedDocuments()
    evidence_files: dict[tuple[str, int], Mapping[str, Any]] = {}
    for reference in evidence_map["evidence_refs"]:
        document = reads.document(reference, "research_object")
        if document["object_type"] != "evidence":
            raise ValueError(f"OBJECT-NOT-EVIDENCE: {reference['path']}")
        key = (document["object_id"], document["revision"])
        if key in evidence_files:
            raise ValueError(f"ambiguous Evidence identity: {key[0]}@{key[1]}")
        evidence_files[key] = reference
        documents.add(Path(reference["path"]), document, sha256=_digest(reference["sha256"]))
    index = ClosureIndex.from_documents(documents)
    bindings: dict[tuple[str, int], Mapping[str, Any]] = {}
    for binding in evidence_map["source_bindings"]:
        key = _identity(binding["source_ref"])
        if key in bindings:
            raise ValueError(f"ambiguous source binding: {key[0]}@{key[1]}")
        bindings[key] = binding

    provenance_cache: dict[tuple[str, int], dict[str, Any]] = {}
    located: dict[str, list[dict[str, Any]]] = {"support": [], "counterevidence": []}
    for relation, field in (("support", "support_refs"), ("counterevidence", "counterevidence_refs")):
        for position, reference in enumerate(claim[field]):
            item: dict[str, Any] = {"reference": reference, "claim_pointer": f"/{field}/{position}"}
            located[relation].append(item)
            try:
                key = _identity(reference)
                resolved = index.resolve(reference)
                if resolved["status"] != "ok":
                    raise ValueError(f"Evidence {key[0]}@{key[1]}: {resolved['status']}")
                evidence_ref = evidence_files[key]
                evidence = documents[Path(evidence_ref["path"])]
                source_key = _identity(evidence["source_ref"])
                binding = bindings.get(source_key)
                if binding is None:
                    raise ValueError(f"missing source binding: {source_key[0]}@{source_key[1]}")
                if isinstance(evidence["source_ref"], Mapping) and evidence["source_ref"].get("sha256"):
                    source_hash = binding["source_ref"].get("sha256")
                    if source_hash is None or _digest(source_hash) != _digest(evidence["source_ref"]["sha256"]):
                        raise ValueError("source ObjectRef hash does not match its explicit binding")
                if source_key not in provenance_cache:
                    provenance_cache[source_key] = _source_provenance(reads, binding)
                item.update(
                    status="located", evidence_ref=dict(evidence_ref),
                    statement=evidence["statement"], locator=evidence["locator"],
                    quality_flags=evidence["quality_flags"],
                    source_ref=evidence["source_ref"], artifact_ref=dict(binding["artifact_ref"]),
                    provenance=provenance_cache[source_key],
                )
            except ValueError as exc:
                item.update(status="unresolved", problem=str(exc))
                problems.append(f"{item['claim_pointer']}: {exc}")
    return {
        "claim_id": claim["object_id"], "revision": claim["revision"],
        "strength": claim["strength"], "claim_ref": dict(claim_ref),
        "support_refs": claim["support_refs"], "counterevidence_refs": claim["counterevidence_refs"],
        "limitations": claim["limitations"],
        "localization": {
            **located,
            "limitations": [
                {"text": text, "file_ref": dict(claim_ref), "pointer": f"/limitations/{position}"}
                for position, text in enumerate(claim["limitations"])
            ],
        },
        "complete": not problems, "problems": problems,
        "captured_file_count": len(reads.contents),
        "claim_acceptance": False, "scientific_correctness": False,
    }
