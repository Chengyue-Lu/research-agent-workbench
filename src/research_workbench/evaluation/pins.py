"""Exact, bounded input reads for the M5 evaluation-only contracts."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from research_workbench.io import load_document_bytes
from research_workbench.validation.document_core import LoadedDocuments
from research_workbench.validation.schemas import SchemaCatalog


class EvaluationValidationError(ValueError):
    """A declared evaluation record cannot be independently reproduced."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvaluationValidationError(message)


def digest(value: Any) -> str:
    def plain(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {k: plain(v) for k, v in item.items()}
        if isinstance(item, (tuple, list)):
            return [plain(v) for v in item]
        return item

    return hashlib.sha256(
        json.dumps(
            plain(value),
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def sha(value: str) -> str:
    require(isinstance(value, str), "hash must be a string")
    result = value.removeprefix("sha256:")
    require(re.fullmatch(r"[0-9a-f]{64}", result) is not None, "invalid SHA-256")
    return result


def file_ref(reference: Mapping[str, Any]) -> dict[str, str]:
    """Normalize existing FileReference and Capability reference encodings."""
    if "document_path" in reference:
        return {
            "path": reference["document_path"],
            "sha256": sha(reference["content_hash"]),
        }
    return {"path": reference["path"], "sha256": sha(reference["sha256"])}


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except (TypeError, ValueError, AttributeError) as exc:
        raise EvaluationValidationError("invalid timestamp") from exc
    require(result.tzinfo is not None, "timestamp requires a timezone")
    return result


class EvaluationInputs:
    """Read each referenced artifact once; hashes cover exactly the parsed bytes.

    A caller supplies the root and authoritative outer reference. Nothing is
    selected from a registry, fetched, executed, or granted by this reader.
    """

    def __init__(self, root: str | Path, schema_root: str | Path | None = None):
        self.root = Path(root).resolve()
        self.catalog = SchemaCatalog(schema_root)
        self.schema_hashes: dict[str, str] = {}
        for name in self.catalog.names:
            path = self.catalog.directory / f"{name}.schema.json"
            content = path.read_bytes()
            require(
                json.loads(content) == self.catalog.schema(name),
                "Schema changed while loading the validator",
            )
            self.schema_hashes[path.name] = hashlib.sha256(content).hexdigest()
        self.documents = LoadedDocuments()
        self.hashes: dict[str, str] = {}
        self.schema_checks: set[tuple[str, str]] = set()
        self.manifest_cache: dict[str, Mapping[str, Any]] = {}
        self.protocol_cache: dict[str, Mapping[str, Any]] = {}

    def validate(self, kind: str, document: Any) -> Mapping[str, Any]:
        try:
            key = (kind, digest(document))
        except (TypeError, ValueError) as exc:
            raise EvaluationValidationError("document is not finite JSON data") from exc
        if key in self.schema_checks:
            return document
        errors = self.catalog.validate(kind, document)
        require(
            not errors,
            f"{kind} schema: "
            + "; ".join(f"{e.pointer}: {e.message}" for e in errors[:5]),
        )
        self.schema_checks.add(key)
        return document

    def read_bytes(self, reference: Mapping[str, Any]) -> bytes:
        ref = file_ref(reference)
        name = ref["path"]
        require(
            isinstance(name, str)
            and bool(name)
            and "\\" not in name
            and ":" not in name
            and not name.startswith("/")
            and all(part not in {"", ".", ".."} for part in name.split("/")),
            "reference must be a portable path within the evaluation root",
        )
        path = (self.root / name).resolve()
        require(path.is_relative_to(self.root), "reference escapes evaluation root")
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise EvaluationValidationError(f"reference unavailable: {name}") from exc
        actual = hashlib.sha256(content).hexdigest()
        require(actual == ref["sha256"], f"reference hash mismatch: {name}")
        require(
            self.hashes.get(name, actual) == actual,
            f"reference changed during validation: {name}",
        )
        self.hashes[name] = actual
        return content

    def read(
        self, reference: Mapping[str, Any], kind: str | None = None
    ) -> Mapping[str, Any]:
        ref = file_ref(reference)
        content = self.read_bytes(ref)
        try:
            document = load_document_bytes(Path(ref["path"]), content)
        except Exception as exc:
            raise EvaluationValidationError(
                f"unparseable document: {ref['path']}"
            ) from exc
        require(
            isinstance(document, Mapping), f"document must be an object: {ref['path']}"
        )
        if kind:
            self.validate(kind, document)
        self.documents.add(
            (self.root / ref["path"]).resolve(), document, sha256=ref["sha256"]
        )
        return document

    def manifest(self, reference: Mapping[str, Any]) -> Mapping[str, Any]:
        from research_workbench.evaluation.manifest import (
            check_evaluation_manifest,
            check_reference_closure,
        )

        key = digest(file_ref(reference))
        if key in self.manifest_cache:
            self.recheck()
            return copy.deepcopy(self.manifest_cache[key])
        doc = self.read(reference, "evaluation_manifest")
        problems = check_evaluation_manifest(doc)
        require(not problems, "manifest semantics: " + "; ".join(problems))

        # Verify every explicit file reference, including references which the
        # legacy semantic checker intentionally skips when files are missing.
        def visit(value: Any) -> None:
            if isinstance(value, Mapping):
                if "path" in value and "sha256" in value:
                    self.read_bytes(value)
                else:
                    for child in value.values():
                        visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(doc)
        problems = check_reference_closure(self.root, doc)
        require(not problems, "manifest closure: " + "; ".join(problems))
        self.manifest_cache[key] = copy.deepcopy(doc)
        return doc

    def recheck(self) -> None:
        for name, expected in self.schema_hashes.items():
            require(
                hashlib.sha256((self.catalog.directory / name).read_bytes()).hexdigest()
                == expected,
                "Schema bytes changed during validation",
            )
        for path, expected in list(self.hashes.items()):
            self.read_bytes({"path": path, "sha256": expected})


def arm(manifest: Mapping[str, Any], arm_id: str) -> Mapping[str, Any]:
    return next(item for item in manifest["arms"] if item["arm_id"] == arm_id)
