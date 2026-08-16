"""Schema-checked document loading, staging writes, and small shared helpers."""

from __future__ import annotations

import hashlib
import json
from functools import cache
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

from research_workbench.artifacts.integrity import resolve_within_root
from research_workbench.io import load_document, write_yaml_exclusive
from research_workbench.validation import SchemaCatalog

from .errors import CloseoutContractSnapshot, CloseoutError
from .paths import _stage_path


@cache
def _schema_catalog() -> SchemaCatalog:
    """Reuse the immutable schema registry across one closeout process."""

    return SchemaCatalog()

def _snapshot_document(snapshot: CloseoutContractSnapshot) -> Mapping[str, Any]:
    if hashlib.sha256(snapshot.payload).hexdigest() != snapshot.sha256:
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-SNAPSHOT", f"snapshot digest differs for {snapshot.ref}"
        )
    try:
        text = snapshot.payload.decode("utf-8")
        suffix = PurePosixPath(snapshot.ref).suffix.lower()
        if suffix == ".json":
            value = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            value = yaml.safe_load(text)
        else:
            raise CloseoutError(
                "CLOSEOUT-CONTRACT-REF", f"unsupported contract suffix: {snapshot.ref}"
            )
    except (UnicodeDecodeError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-PARSE",
            f"contract cannot be parsed as UTF-8 structured data: {snapshot.ref}",
        ) from exc
    if not isinstance(value, Mapping):
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-PARSE", f"contract must be an object: {snapshot.ref}"
        )
    errors = _schema_catalog().validate(snapshot.kind, value)
    if errors:
        first = errors[0]
        raise CloseoutError(
            "CLOSEOUT-CONTRACT-SCHEMA",
            f"{snapshot.ref}{first.pointer}: {first.message}",
        )
    return value


def _stage_document(root: Path, relative: str, document: Mapping[str, Any], kind: str) -> None:
    _validate_schema(kind, document)
    write_yaml_exclusive(_stage_path(root, relative), document)


def _validate_schema(kind: str, document: Mapping[str, Any]) -> None:
    errors = _schema_catalog().validate(kind, document)
    if errors:
        first = errors[0]
        raise CloseoutError("CLOSEOUT-SCHEMA", f"{kind} {first.pointer}: {first.message}")


def _load_mapping(root: Path, relative: str, label: str) -> Mapping[str, Any]:
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        raise CloseoutError("REF-MISSING", f"{label} does not exist within project: {relative}")
    value = load_document(resolved)
    if not isinstance(value, Mapping):
        raise CloseoutError("DOCUMENT-INVALID", f"{label} must be an object: {relative}")
    return value


def _resolve_existing(root: Path, relative: str, label: str) -> Path:
    resolved = resolve_within_root(root, relative)
    if resolved is None or not resolved.is_file():
        raise CloseoutError("REF-MISSING", f"{label} does not exist: {relative}")
    return resolved


def _unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
