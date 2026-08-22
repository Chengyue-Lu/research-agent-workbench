"""Export the trace JSON Schemas as a baseline-bound consumer bundle.

``trace.py`` defines the physical trace format; this module publishes that
format so an external consumer can machine-validate an attempt directory
without reading workbench source. The exported manifest pins every schema
file by sha256 and binds the set to the trace baseline identifier: a
schema change must ship together with a baseline bump in the same change.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from research_workbench.artifacts.integrity import hash_file
from research_workbench.observability.trace import TRACE_BASELINE
from research_workbench.validation.schemas import SchemaCatalog

BUNDLE_KIND = "rwb-trace-schema-bundle"
MANIFEST_FILENAME = "trace-schema-bundle.json"

# Trace schema documents and the physical artifacts they govern. The
# envelope schema additionally references the actors schema, and every
# document references shared definitions in common.schema.json; both are
# carried by the bundle so cross-file $refs resolve stand-alone.
TRACE_SCHEMA_DOCUMENTS: tuple[tuple[str, str], ...] = (
    ("agent-trace-index", "INDEX.yaml"),
    ("agent-trace-actors", "ACTORS.yaml"),
    ("agent-trace-event", "events.jsonl (one JSON object per line)"),
    ("agent-trace-envelope", "messages/*.trace (YAML envelope header)"),
)
TRACE_SCHEMA_REFERENCES: tuple[str, ...] = ("common",)


@dataclass(frozen=True, slots=True)
class TraceSchemaBundle:
    """A hash-verified, stand-alone view of one exported schema bundle."""

    manifest_path: Path
    baseline: str
    schema_version: str
    documents: tuple[Mapping[str, Any], ...]
    _schemas: Mapping[str, Mapping[str, Any]]
    _registry: Registry

    def validator(self, document: str) -> Draft202012Validator:
        try:
            schema = self._schemas[document]
        except KeyError as exc:
            raise KeyError(f"document not in bundle: {document!r}") from exc
        return Draft202012Validator(
            schema,
            registry=self._registry,
            format_checker=FormatChecker(),
        )

    def validate(self, document: str, instance: Any) -> list[str]:
        """Validate one trace artifact against the exported schema set."""

        return [
            f"{error.message} at {list(error.absolute_path)}"
            for error in sorted(self.validator(document).iter_errors(instance), key=lambda item: list(item.absolute_path))
        ]


def _create_exclusive(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def export_trace_schema_bundle(
    target_dir: str | Path,
    *,
    schema_version: str = "0.1.0",
) -> Path:
    """Write the schema bundle and its pinned manifest into ``target_dir``.

    Every file is created exclusively: exporting into a directory that
    already holds (part of) a bundle fails loudly instead of merging, so a
    published bundle is never silently rewritten.
    """

    target = Path(target_dir)
    catalog = SchemaCatalog(version=schema_version)
    documents: list[dict[str, str]] = []
    references: list[dict[str, str]] = []
    payloads: list[tuple[Path, bytes]] = []

    for document, governs in TRACE_SCHEMA_DOCUMENTS:
        source = catalog.directory / f"{document}.schema.json"
        if not source.is_file():
            raise FileNotFoundError(f"trace schema not found: {source}")
        documents.append(
            {
                "document": document,
                "governs": governs,
                "file": source.name,
                "sha256": hash_file(source),
            }
        )
        payloads.append((target / source.name, source.read_bytes()))
    for document in TRACE_SCHEMA_REFERENCES:
        source = catalog.directory / f"{document}.schema.json"
        if not source.is_file():
            raise FileNotFoundError(f"referenced schema not found: {source}")
        references.append(
            {
                "document": document,
                "file": source.name,
                "sha256": hash_file(source),
            }
        )
        payloads.append((target / source.name, source.read_bytes()))

    manifest = {
        "bundle_kind": BUNDLE_KIND,
        "baseline": TRACE_BASELINE,
        "schema_version": schema_version,
        "generator": "research-agent-workbench",
        "documents": documents,
        "references": references,
    }
    manifest_path = target / MANIFEST_FILENAME
    payloads.append(
        (manifest_path, (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))
    )

    target.mkdir(parents=True, exist_ok=True)
    for path, payload in payloads:
        _create_exclusive(path, payload)
    return manifest_path


def load_trace_schema_bundle(manifest_path: str | Path) -> TraceSchemaBundle:
    """Load an exported bundle, re-hashing every listed schema file."""

    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping) or manifest.get("bundle_kind") != BUNDLE_KIND:
        raise ValueError(f"not a trace schema bundle manifest: {path}")

    schemas: dict[str, Mapping[str, Any]] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    entries = [
        *(
            {"document": entry["document"], "file": entry["file"], "sha256": entry["sha256"]}
            for entry in manifest.get("documents", [])
        ),
        *(
            {"document": entry["document"], "file": entry["file"], "sha256": entry["sha256"]}
            for entry in manifest.get("references", [])
        ),
    ]
    expected_documents = {document for document, _ in TRACE_SCHEMA_DOCUMENTS}
    listed_documents = {entry["document"] for entry in entries}
    if expected_documents - listed_documents:
        raise ValueError(
            f"bundle is missing trace schema documents: {sorted(expected_documents - listed_documents)}"
        )
    for entry in entries:
        schema_path = path.parent / str(entry["file"])
        if not schema_path.is_file():
            raise FileNotFoundError(f"bundle file is missing: {schema_path}")
        if hash_file(schema_path) != str(entry["sha256"]).lower().removeprefix("sha256:"):
            raise ValueError(f"bundle file drifted from its pinned hash: {schema_path}")
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if not isinstance(schema, Mapping):
            raise ValueError(f"bundle schema is not an object: {schema_path}")
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            resources.append((schema_id, Resource.from_contents(schema)))
        schemas[str(entry["document"])] = schema
    registry: Registry = Registry()
    registry = registry.with_resources(resources)
    return TraceSchemaBundle(
        manifest_path=path,
        baseline=str(manifest.get("baseline", "")),
        schema_version=str(manifest.get("schema_version", "")),
        documents=tuple(manifest.get("documents", [])),
        _schemas=schemas,
        _registry=registry,
    )
