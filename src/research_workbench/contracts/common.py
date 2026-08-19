from __future__ import annotations

import re
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping, TypeVar


class ContractError(ValueError):
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"{field}: {message}")


SKILL_REFERENCE_RE = re.compile(
    r"^(?P<skill_id>[0-9A-Za-z][0-9A-Za-z._-]*)(?:@(?P<version>[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?))?$"
)


@dataclass(frozen=True, slots=True)
class SkillReference:
    skill_id: str
    version: str | None = None

    @property
    def identifier(self) -> str:
        return f"{self.skill_id}@{self.version}" if self.version else self.skill_id


def parse_skill_reference(value: str, field: str = "skill") -> SkillReference:
    match = SKILL_REFERENCE_RE.fullmatch(value)
    if match is None:
        raise ContractError(field, "must be a Skill ID or exact skill_id@semver selector")
    return SkillReference(match.group("skill_id"), match.group("version"))


def require_string(data: Mapping[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(field, "must be a non-empty string")
    return value


def optional_string(data: Mapping[str, Any], field: str) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ContractError(field, "must be null or a non-empty string")
    return value


def string_tuple(data: Mapping[str, Any], field: str, *, required: bool = False) -> tuple[str, ...]:
    value = data.get(field)
    if value is None and not required:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ContractError(field, "must be an array of non-empty strings")
    return tuple(value)


def mapping_value(data: Mapping[str, Any], field: str, *, required: bool = False) -> Mapping[str, Any]:
    value = data.get(field)
    if value is None and not required:
        return {}
    if not isinstance(value, Mapping):
        raise ContractError(field, "must be an object")
    return value


def mapping_tuple(data: Mapping[str, Any], field: str) -> tuple[Mapping[str, Any], ...]:
    value = data.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, Mapping) for item in value):
        raise ContractError(field, "must be an array of objects")
    return tuple(value)


def require_relative_path(value: str, field: str) -> str:
    if PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute():
        raise ContractError(field, "must be repository-relative")
    if ".." in PurePosixPath(value.replace("\\", "/")).parts:
        raise ContractError(field, "must not escape the project root")
    return value


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    filesystem: str = "unspecified"
    network: str = "unspecified"
    external_write: bool = False
    allowed_roots: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "PermissionPolicy":
        external = data.get("external_write", False)
        if isinstance(external, str):
            if external not in {"allowed", "forbidden"}:
                raise ContractError("external_write", "must be allowed, forbidden, or boolean")
            external = external == "allowed"
        if not isinstance(external, bool):
            raise ContractError("external_write", "must be allowed, forbidden, or boolean")
        roots = string_tuple(data, "allowed_roots")
        for index, root in enumerate(roots):
            require_relative_path(root, f"allowed_roots[{index}]")
        filesystem = data.get("filesystem", "unspecified")
        network = data.get("network", "unspecified")
        if not isinstance(filesystem, str) or not isinstance(network, str):
            raise ContractError("permissions", "filesystem and network must be strings")
        return cls(filesystem, network, external, roots)


def ensure_unique(values: Iterable[str], field: str) -> tuple[str, ...]:
    result = tuple(values)
    if len(result) != len(set(result)):
        raise ContractError(field, "must not contain duplicates")
    return result


T = TypeVar("T")


def to_plain(value: T) -> Any:
    """Convert nested contract dataclasses to JSON/YAML-safe primitives."""

    if is_dataclass(value):
        value = asdict(value)  # type: ignore[assignment]
    if isinstance(value, Mapping):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [to_plain(item) for item in value]
    if isinstance(value, list):
        return [to_plain(item) for item in value]
    return value
