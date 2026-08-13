"""Small, explicit model pool configuration.

The pool intentionally does not score, rank, or automatically route models.
Callers select one named slot and receive one pinned provider/model binding.
Model identifiers may be supplied by an injected environment mapping so tests
and dry-run paths never need to read the host process environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.adapters.models.port import Capability
from research_workbench.io import load_document


MODEL_ROLES = frozenset({"primary", "worker", "specialist"})
SELECTION_POLICY = "explicit-slot-only"


@dataclass(frozen=True, slots=True)
class ModelBinding:
    slot_id: str
    role: str
    provider_adapter: str
    model: str
    capabilities: frozenset[Capability]
    reasoning_effort: str | None
    specialties: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelSlotConfig:
    slot_id: str
    role: str
    provider_adapter: str
    model_env: str
    enabled: bool
    capabilities: frozenset[Capability]
    reasoning_effort: str | None = None
    specialties: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ModelSlotConfig":
        required = {
            "slot_id",
            "role",
            "provider_adapter",
            "model_env",
            "enabled",
            "capabilities",
        }
        optional = {"reasoning_effort", "specialties"}
        missing = sorted(required - set(value))
        unknown = sorted(set(value) - required - optional)
        if missing:
            raise ValueError("model slot lacks fields: " + ", ".join(missing))
        if unknown:
            raise ValueError("model slot has unknown fields: " + ", ".join(unknown))

        slot_id = _nonempty_string(value["slot_id"], "slot_id")
        role = _nonempty_string(value["role"], "role")
        if role not in MODEL_ROLES:
            raise ValueError(f"model slot {slot_id!r} has unsupported role: {role}")
        provider_adapter = _nonempty_string(value["provider_adapter"], "provider_adapter")
        model_env = _environment_name(value["model_env"], "model_env")
        if not isinstance(value["enabled"], bool):
            raise ValueError(f"model slot {slot_id!r} enabled must be boolean")

        raw_capabilities = value["capabilities"]
        if not isinstance(raw_capabilities, list) or not raw_capabilities:
            raise ValueError(f"model slot {slot_id!r} capabilities must be a non-empty array")
        try:
            capabilities = frozenset(Capability(item) for item in raw_capabilities)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"model slot {slot_id!r} has an unknown capability") from exc
        if Capability.TEXT not in capabilities:
            raise ValueError(f"model slot {slot_id!r} must include text capability")

        reasoning_effort = value.get("reasoning_effort")
        if reasoning_effort is not None:
            reasoning_effort = _nonempty_string(reasoning_effort, "reasoning_effort")
            if Capability.REASONING not in capabilities:
                raise ValueError(
                    f"model slot {slot_id!r} sets reasoning_effort without reasoning capability"
                )

        raw_specialties = value.get("specialties", [])
        if not isinstance(raw_specialties, list) or any(
            not isinstance(item, str) or not item.strip() for item in raw_specialties
        ):
            raise ValueError(f"model slot {slot_id!r} specialties must be an array of strings")
        specialties = tuple(item.strip() for item in raw_specialties)
        if len(specialties) != len(set(specialties)):
            raise ValueError(f"model slot {slot_id!r} specialties must be unique")
        if role == "specialist" and not specialties:
            raise ValueError(f"specialist model slot {slot_id!r} requires at least one specialty")
        if role != "specialist" and specialties:
            raise ValueError(f"non-specialist model slot {slot_id!r} cannot declare specialties")

        return cls(
            slot_id=slot_id,
            role=role,
            provider_adapter=provider_adapter,
            model_env=model_env,
            enabled=value["enabled"],
            capabilities=capabilities,
            reasoning_effort=reasoning_effort,
            specialties=specialties,
        )

    def bind(self, environment: Mapping[str, str]) -> ModelBinding:
        if not self.enabled:
            raise ValueError(f"model slot is disabled: {self.slot_id}")
        model = environment.get(self.model_env, "").strip()
        if not model:
            raise ValueError(
                f"model slot {self.slot_id!r} requires a non-empty {self.model_env} value"
            )
        return ModelBinding(
            slot_id=self.slot_id,
            role=self.role,
            provider_adapter=self.provider_adapter,
            model=model,
            capabilities=self.capabilities,
            reasoning_effort=self.reasoning_effort,
            specialties=self.specialties,
        )

    def probe(self, *, environment: Mapping[str, str] | None = None) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "role": self.role,
            "provider_adapter": self.provider_adapter,
            "enabled": self.enabled,
            "model_source": f"env:{self.model_env}",
            "model_status": (
                "unchecked"
                if environment is None
                else ("present" if environment.get(self.model_env, "").strip() else "missing")
            ),
            "capabilities": sorted(str(item) for item in self.capabilities),
            "reasoning_effort": self.reasoning_effort,
            "specialties": list(self.specialties),
        }


@dataclass(frozen=True, slots=True)
class ModelPool:
    pool_id: str
    slots: tuple[ModelSlotConfig, ...]
    selection_policy: str = SELECTION_POLICY

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ModelPool":
        if value.get("registry_kind") != "model_pool":
            raise ValueError("model pool config must have registry_kind: model_pool")
        if value.get("schema_version") != "0.1.0":
            raise ValueError("model pool config must use schema_version: 0.1.0")
        pool_id = _nonempty_string(value.get("pool_id"), "pool_id")
        policy = _nonempty_string(value.get("selection_policy"), "selection_policy")
        if policy != SELECTION_POLICY:
            raise ValueError(f"unsupported model selection policy: {policy}")
        raw_slots = value.get("slots")
        if not isinstance(raw_slots, list) or not raw_slots:
            raise ValueError("model pool config must contain a non-empty slots array")
        slots: list[ModelSlotConfig] = []
        seen: set[str] = set()
        for index, raw_slot in enumerate(raw_slots):
            if not isinstance(raw_slot, Mapping):
                raise ValueError(f"model slot at index {index} must be an object")
            slot = ModelSlotConfig.from_mapping(raw_slot)
            if slot.slot_id in seen:
                raise ValueError(f"duplicate model slot id: {slot.slot_id}")
            seen.add(slot.slot_id)
            slots.append(slot)
        return cls(pool_id=pool_id, slots=tuple(slots), selection_policy=policy)

    def get(self, slot_id: str) -> ModelSlotConfig:
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(f"unknown model slot: {slot_id}")

    def bind(self, slot_id: str, *, environment: Mapping[str, str]) -> ModelBinding:
        """Resolve exactly one caller-selected slot; never rank or fall back."""

        return self.get(slot_id).bind(environment)

    def probe(self, *, environment: Mapping[str, str] | None = None) -> dict[str, object]:
        return {
            "pool_id": self.pool_id,
            "selection_policy": self.selection_policy,
            "environment_checked": environment is not None,
            "slots": [slot.probe(environment=environment) for slot in self.slots],
        }


def load_model_pool(path: str | Path) -> ModelPool:
    document = load_document(path)
    if not isinstance(document, Mapping):
        raise ValueError("model pool config must be an object")
    allowed = {"schema_version", "registry_kind", "pool_id", "selection_policy", "warning", "slots"}
    unknown = sorted(set(document) - allowed)
    if unknown:
        raise ValueError("model pool config has unknown fields: " + ", ".join(unknown))
    return ModelPool.from_mapping(document)


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _environment_name(value: object, field: str) -> str:
    name = _nonempty_string(value, field)
    if not name.replace("_", "").isalnum():
        raise ValueError(f"{field} must contain only letters, digits, and underscores")
    return name
