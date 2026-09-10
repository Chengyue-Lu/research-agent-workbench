from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


@dataclass(frozen=True, slots=True)
class SchemaValidationError:
    pointer: str
    message: str
    validator: str


class SchemaCatalog:
    def __init__(self, root: str | Path | None = None, version: str = "0.1.0", *, resource_reader=None) -> None:
        if root is None:
            from research_workbench.resources import RuntimeResources
            resource_reader = RuntimeResources()
            root = resource_reader.schema_root
        self._resource_reader = resource_reader
        self.root = Path(root)
        if resource_reader is not None and self.root != resource_reader.schema_root:
            raise ValueError("Schema root differs from pinned Runtime resources")
        self.version = version
        self.directory = self.root / f"v{version}"
        self._schemas: dict[str, Mapping[str, Any]] = {}
        self._kind_to_name: dict[str, str] = {}
        self._registry: Registry = Registry()
        self._load()

    def _load(self) -> None:
        if not self.directory.is_dir():
            raise FileNotFoundError(f"schema version not found: {self.directory}")
        resources: list[tuple[str, Resource[Any]]] = []
        for path in sorted(self.directory.glob("*.schema.json")):
            if self._resource_reader is None:
                schema = json.loads(path.read_bytes())
            else:
                logical = path.relative_to(self._resource_reader.catalog_root).as_posix()
                schema = json.loads(self._resource_reader.read(logical))
            if not isinstance(schema, Mapping):
                raise SchemaError(f"schema must be an object: {path}")
            Draft202012Validator.check_schema(schema)
            schema_id = schema.get("$id")
            if not isinstance(schema_id, str):
                raise SchemaError(f"schema lacks $id: {path}")
            name = path.name.removesuffix(".schema.json")
            self._schemas[name] = schema
            kind = schema.get("x-rwb-document-kind")
            if isinstance(kind, str):
                self._kind_to_name[kind] = name
            resources.append((schema_id, Resource.from_contents(schema)))
        self._registry = self._registry.with_resources(resources)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._schemas))

    @property
    def document_kinds(self) -> tuple[str, ...]:
        return tuple(sorted(self._kind_to_name))

    def schema(self, name: str) -> Mapping[str, Any]:
        try:
            return self._schemas[name]
        except KeyError as exc:
            raise KeyError(f"unknown schema {name!r} for version {self.version}") from exc

    def schema_for_kind(self, kind: str) -> Mapping[str, Any]:
        try:
            return self.schema(self._kind_to_name[kind])
        except KeyError as exc:
            raise KeyError(f"no schema for document kind: {kind}") from exc

    def validate(self, kind: str, instance: Any) -> list[SchemaValidationError]:
        schema = self.schema_for_kind(kind)
        validation_schema: Mapping[str, Any] = schema
        if kind == "research_object" and isinstance(instance, Mapping):
            object_type = instance.get("object_type")
            definition = "proposition" if object_type == "hypothesis" else object_type
            if isinstance(definition, str) and definition in schema.get("$defs", {}):
                validation_schema = {"$ref": f"{schema['$id']}#/$defs/{definition}"}
        validator = Draft202012Validator(
            validation_schema,
            registry=self._registry,
            format_checker=FormatChecker(),
        )
        result: list[SchemaValidationError] = []
        for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
            pointer = "$"
            for part in error.absolute_path:
                pointer += f"[{part}]" if isinstance(part, int) else f".{part}"
            result.append(SchemaValidationError(pointer, error.message, str(error.validator)))
        return result
