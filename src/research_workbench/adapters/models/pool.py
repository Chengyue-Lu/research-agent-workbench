"""Small, explicit model pool configuration.

The pool intentionally does not score, rank, or automatically route models.
Callers select one named slot and receive one pinned provider/model binding.
Model identifiers may be supplied by an injected environment mapping so tests
and dry-run paths never need to read the host process environment.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from research_workbench.adapters.models.port import Capability, DataPolicy
from research_workbench.adapters.models.session import ApiSessionLimits
from research_workbench.contracts.common import is_path_safe_identifier
from research_workbench.io import load_document
from research_workbench.tasks import FileReference


MODEL_ROLES = frozenset({"primary", "worker", "specialist"})
MODEL_POOL_SCHEMA_VERSION = "0.1.0"
MODEL_POOL_REGISTRY_KIND = "model_pool"
SELECTION_POLICY = "explicit-slot-only"
MODEL_ASSIGNMENT_SOURCES = frozenset(
    {"profile-default", "task-override", "human-override"}
)


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
class ModelAssignment:
    """Canonical, immutable explicit model selection for one Task revision."""

    schema_version: str
    model_assignment_id: str
    attempt_id: str
    task_id: str
    task_revision: int
    agent_profile_ref: FileReference
    pool_id: str
    pool_config_hash: str
    slot_id: str
    role: str
    selection_source: str
    selection_reason: str
    selection_ref: FileReference | None
    provider_adapter_id: str
    requested_model: str
    capabilities: frozenset[Capability]
    reasoning_effort: str | None
    specialties: tuple[str, ...]
    effective_data_policy: DataPolicy
    execution_limits: ApiSessionLimits
    automatic_fallback: bool

    @classmethod
    def create(
        cls,
        *,
        attempt_id: str,
        task_id: str,
        task_revision: int,
        agent_profile_ref: FileReference,
        pool_id: str,
        pool_config_hash: str,
        binding: ModelBinding,
        selection_source: str,
        selection_reason: str,
        effective_data_policy: DataPolicy,
        execution_limits: ApiSessionLimits,
        selection_ref: FileReference | None = None,
    ) -> "ModelAssignment":
        fields = _validated_assignment_fields(
            attempt_id=attempt_id,
            task_id=task_id,
            task_revision=task_revision,
            agent_profile_ref=agent_profile_ref,
            pool_id=pool_id,
            pool_config_hash=pool_config_hash,
            slot_id=binding.slot_id,
            role=binding.role,
            selection_source=selection_source,
            selection_reason=selection_reason,
            selection_ref=selection_ref,
            provider_adapter_id=binding.provider_adapter,
            requested_model=binding.model,
            capabilities=binding.capabilities,
            reasoning_effort=binding.reasoning_effort,
            specialties=binding.specialties,
            effective_data_policy=effective_data_policy,
            execution_limits=execution_limits,
            automatic_fallback=False,
        )
        identifier = _model_assignment_identifier(**fields)
        return cls("0.1.0", identifier, **fields)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ModelAssignment":
        required = {
            "schema_version",
            "model_assignment_id",
            "attempt_id",
            "task_id",
            "task_revision",
            "agent_profile_ref",
            "pool_id",
            "pool_config_hash",
            "slot_id",
            "role",
            "selection_source",
            "selection_reason",
            "provider_adapter_id",
            "requested_model",
            "capabilities",
            "reasoning_effort",
            "specialties",
            "effective_data_policy",
            "execution_limits",
            "automatic_fallback",
        }
        optional = {"selection_ref"}
        missing = sorted(required - set(value))
        unknown = sorted(set(value) - required - optional)
        if missing:
            raise ValueError("model assignment lacks fields: " + ", ".join(missing))
        if unknown:
            raise ValueError("model assignment has unknown fields: " + ", ".join(unknown))
        if value.get("schema_version") != "0.1.0":
            raise ValueError("model assignment must use schema_version: 0.1.0")
        raw_capabilities = value.get("capabilities")
        if not isinstance(raw_capabilities, list):
            raise ValueError("model assignment capabilities must be an array")
        try:
            capabilities = frozenset(Capability(item) for item in raw_capabilities)
        except (TypeError, ValueError) as exc:
            raise ValueError("model assignment has an unknown capability") from exc
        raw_specialties = value.get("specialties")
        if not isinstance(raw_specialties, list):
            raise ValueError("model assignment specialties must be an array")
        raw_profile_ref = value.get("agent_profile_ref")
        if not isinstance(raw_profile_ref, Mapping):
            raise ValueError("model assignment agent_profile_ref must be a file reference")
        raw_policy = value.get("effective_data_policy")
        if not isinstance(raw_policy, Mapping):
            raise ValueError("effective_data_policy must be an object")
        raw_limits = value.get("execution_limits")
        if not isinstance(raw_limits, Mapping):
            raise ValueError("execution_limits must be an object")
        raw_selection_ref = value.get("selection_ref")
        if raw_selection_ref is not None and not isinstance(raw_selection_ref, Mapping):
            raise ValueError("selection_ref must be a hash-bound file reference")
        fields = _validated_assignment_fields(
            attempt_id=value.get("attempt_id"),
            task_id=value.get("task_id"),
            task_revision=value.get("task_revision"),
            agent_profile_ref=FileReference.from_mapping(raw_profile_ref),
            pool_id=value.get("pool_id"),
            pool_config_hash=value.get("pool_config_hash"),
            slot_id=value.get("slot_id"),
            role=value.get("role"),
            selection_source=value.get("selection_source"),
            selection_reason=value.get("selection_reason"),
            selection_ref=(
                FileReference.from_mapping(raw_selection_ref)
                if isinstance(raw_selection_ref, Mapping)
                else None
            ),
            provider_adapter_id=value.get("provider_adapter_id"),
            requested_model=value.get("requested_model"),
            capabilities=capabilities,
            reasoning_effort=value.get("reasoning_effort"),
            specialties=tuple(raw_specialties),
            effective_data_policy=_data_policy_from_mapping(raw_policy),
            execution_limits=_limits_from_mapping(raw_limits),
            automatic_fallback=value.get("automatic_fallback"),
        )
        expected = _model_assignment_identifier(**fields)
        identifier = _nonempty_string(value.get("model_assignment_id"), "model_assignment_id")
        if identifier != expected:
            raise ValueError(
                f"model_assignment_id does not match canonical content; expected {expected}"
            )
        return cls("0.1.0", identifier, **fields)

    def to_binding(self) -> ModelBinding:
        return ModelBinding(
            slot_id=self.slot_id,
            role=self.role,
            provider_adapter=self.provider_adapter_id,
            model=self.requested_model,
            capabilities=self.capabilities,
            reasoning_effort=self.reasoning_effort,
            specialties=self.specialties,
        )

    def to_mapping(self) -> dict[str, object]:
        document: dict[str, object] = {
            "schema_version": self.schema_version,
            "model_assignment_id": self.model_assignment_id,
            "attempt_id": self.attempt_id,
            "task_id": self.task_id,
            "task_revision": self.task_revision,
            "agent_profile_ref": {
                "path": self.agent_profile_ref.path,
                "sha256": self.agent_profile_ref.sha256,
                **(
                    {"revision": self.agent_profile_ref.revision}
                    if self.agent_profile_ref.revision is not None
                    else {}
                ),
            },
            "pool_id": self.pool_id,
            "pool_config_hash": self.pool_config_hash,
            "slot_id": self.slot_id,
            "role": self.role,
            "selection_source": self.selection_source,
            "selection_reason": self.selection_reason,
            "provider_adapter_id": self.provider_adapter_id,
            "requested_model": self.requested_model,
            "capabilities": sorted(str(item) for item in self.capabilities),
            "reasoning_effort": self.reasoning_effort,
            "specialties": list(self.specialties),
            "effective_data_policy": _data_policy_mapping(self.effective_data_policy),
            "execution_limits": _limits_mapping(self.execution_limits),
            "automatic_fallback": self.automatic_fallback,
        }
        if self.selection_ref is not None:
            document["selection_ref"] = _file_reference_mapping(self.selection_ref)
        return document


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

    def _canonical_mapping(self) -> dict[str, object]:
        return {
            "slot_id": self.slot_id,
            "role": self.role,
            "provider_adapter": self.provider_adapter,
            "model_env": self.model_env,
            "enabled": self.enabled,
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
        allowed = {
            "schema_version",
            "registry_kind",
            "pool_id",
            "selection_policy",
            "warning",
            "slots",
        }
        unknown = sorted(set(value) - allowed)
        if unknown:
            raise ValueError("model pool config has unknown fields: " + ", ".join(unknown))
        if value.get("registry_kind") != MODEL_POOL_REGISTRY_KIND:
            raise ValueError("model pool config must have registry_kind: model_pool")
        if value.get("schema_version") != MODEL_POOL_SCHEMA_VERSION:
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

    @property
    def config_hash(self) -> str:
        """Hash the complete normalized execution-affecting pool configuration."""

        payload = {
            "schema_version": MODEL_POOL_SCHEMA_VERSION,
            "registry_kind": MODEL_POOL_REGISTRY_KIND,
            "pool_id": self.pool_id,
            "selection_policy": self.selection_policy,
            "automatic_fallback": False,
            "slots": [
                slot._canonical_mapping()
                for slot in sorted(self.slots, key=lambda item: item.slot_id)
            ],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get(self, slot_id: str) -> ModelSlotConfig:
        for slot in self.slots:
            if slot.slot_id == slot_id:
                return slot
        raise KeyError(f"unknown model slot: {slot_id}")

    def bind(self, slot_id: str, *, environment: Mapping[str, str]) -> ModelBinding:
        """Resolve exactly one caller-selected slot; never rank or fall back."""

        return self.get(slot_id).bind(environment)

    def assign(
        self,
        slot_id: str,
        *,
        environment: Mapping[str, str],
        attempt_id: str,
        task_id: str,
        task_revision: int,
        agent_profile_ref: FileReference,
        pool_config_hash: str | None = None,
        selection_reason: str,
        effective_data_policy: DataPolicy,
        execution_limits: ApiSessionLimits,
        selection_source: str = "profile-default",
        selection_ref: FileReference | None = None,
    ) -> ModelAssignment:
        """Create one canonical assignment from exactly one caller-selected slot."""

        canonical_hash = self.config_hash
        if pool_config_hash is not None:
            supplied_hash = _nonempty_string(pool_config_hash, "pool_config_hash")
            if not _is_sha256(supplied_hash):
                raise ValueError("pool_config_hash must be a SHA-256 digest")
            supplied_hash = supplied_hash.removeprefix("sha256:").lower()
            if supplied_hash != canonical_hash:
                raise ValueError(
                    "pool_config_hash does not match the canonical ModelPool configuration"
                )
        binding = self.bind(slot_id, environment=environment)
        return ModelAssignment.create(
            attempt_id=attempt_id,
            task_id=task_id,
            task_revision=task_revision,
            agent_profile_ref=agent_profile_ref,
            pool_id=self.pool_id,
            pool_config_hash=canonical_hash,
            binding=binding,
            selection_source=selection_source,
            selection_reason=selection_reason,
            selection_ref=selection_ref,
            effective_data_policy=effective_data_policy,
            execution_limits=execution_limits,
        )

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


def _validated_assignment_fields(
    *,
    attempt_id: object,
    task_id: object,
    task_revision: object,
    agent_profile_ref: object,
    pool_id: object,
    pool_config_hash: object,
    slot_id: object,
    role: object,
    selection_source: object,
    selection_reason: object,
    selection_ref: object,
    provider_adapter_id: object,
    requested_model: object,
    capabilities: object,
    reasoning_effort: object,
    specialties: object,
    effective_data_policy: object,
    execution_limits: object,
    automatic_fallback: object,
) -> dict[str, Any]:
    normalized_attempt_id = _nonempty_string(attempt_id, "attempt_id")
    if not is_path_safe_identifier(normalized_attempt_id):
        raise ValueError("attempt_id must be a portable path-safe identifier")
    if isinstance(task_revision, bool) or not isinstance(task_revision, int) or task_revision < 1:
        raise ValueError("task_revision must be a positive integer")
    if not isinstance(agent_profile_ref, FileReference):
        raise ValueError("agent_profile_ref must be a FileReference")
    profile_ref = FileReference.from_mapping(_file_reference_mapping(agent_profile_ref))
    normalized_pool_hash = _nonempty_string(pool_config_hash, "pool_config_hash")
    if not _is_sha256(normalized_pool_hash):
        raise ValueError("pool_config_hash must be a SHA-256 digest")
    normalized_pool_hash = normalized_pool_hash.removeprefix("sha256:").lower()
    normalized_role = _nonempty_string(role, "role")
    if normalized_role not in MODEL_ROLES:
        raise ValueError(f"unsupported model assignment role: {normalized_role}")
    normalized_source = _nonempty_string(selection_source, "selection_source")
    if normalized_source not in MODEL_ASSIGNMENT_SOURCES:
        raise ValueError(f"unsupported model assignment selection source: {normalized_source}")
    normalized_reason = _nonempty_string(selection_reason, "selection_reason")
    normalized_selection_ref: FileReference | None
    if selection_ref is None:
        normalized_selection_ref = None
    else:
        if not isinstance(selection_ref, FileReference):
            raise ValueError("selection_ref must be a hash-bound FileReference")
        normalized_selection_ref = FileReference.from_mapping(
            _file_reference_mapping(selection_ref)
        )
    if normalized_source == "profile-default" and normalized_selection_ref is not None:
        raise ValueError("profile-default selection must not carry selection_ref")
    if normalized_source != "profile-default" and normalized_selection_ref is None:
        raise ValueError(f"{normalized_source} selection requires an explicit selection_ref")
    if not isinstance(capabilities, frozenset) or not capabilities:
        raise ValueError("model assignment capabilities must be a non-empty frozenset")
    if any(not isinstance(item, Capability) for item in capabilities):
        raise ValueError("model assignment capabilities contain an invalid value")
    if Capability.TEXT not in capabilities:
        raise ValueError("model assignment must include text capability")
    normalized_reasoning = reasoning_effort
    if normalized_reasoning is not None:
        normalized_reasoning = _nonempty_string(reasoning_effort, "reasoning_effort")
        if Capability.REASONING not in capabilities:
            raise ValueError("reasoning_effort requires reasoning capability")
    if not isinstance(specialties, tuple) or any(
        not isinstance(item, str) or not item.strip() for item in specialties
    ):
        raise ValueError("model assignment specialties must be a tuple of strings")
    normalized_specialties = tuple(item.strip() for item in specialties)
    if len(normalized_specialties) != len(set(normalized_specialties)):
        raise ValueError("model assignment specialties must be unique")
    if normalized_role == "specialist" and not normalized_specialties:
        raise ValueError("specialist model assignment requires specialties")
    if normalized_role != "specialist" and normalized_specialties:
        raise ValueError("non-specialist model assignment cannot declare specialties")
    if not isinstance(effective_data_policy, DataPolicy):
        raise ValueError("effective_data_policy must be a DataPolicy")
    normalized_policy = _data_policy_from_mapping(
        _data_policy_mapping(effective_data_policy)
    )
    if not isinstance(execution_limits, ApiSessionLimits):
        raise ValueError("execution_limits must be ApiSessionLimits")
    normalized_limits = _limits_from_mapping(_limits_mapping(execution_limits))
    if automatic_fallback is not False:
        raise ValueError("automatic_fallback must be false")
    return {
        "attempt_id": normalized_attempt_id,
        "task_id": _nonempty_string(task_id, "task_id"),
        "task_revision": task_revision,
        "agent_profile_ref": profile_ref,
        "pool_id": _nonempty_string(pool_id, "pool_id"),
        "pool_config_hash": normalized_pool_hash,
        "slot_id": _nonempty_string(slot_id, "slot_id"),
        "role": normalized_role,
        "selection_source": normalized_source,
        "selection_reason": normalized_reason,
        "selection_ref": normalized_selection_ref,
        "provider_adapter_id": _nonempty_string(
            provider_adapter_id, "provider_adapter_id"
        ),
        "requested_model": _nonempty_string(requested_model, "requested_model"),
        "capabilities": capabilities,
        "reasoning_effort": normalized_reasoning,
        "specialties": normalized_specialties,
        "effective_data_policy": normalized_policy,
        "execution_limits": normalized_limits,
        "automatic_fallback": False,
    }


def _model_assignment_identifier(**fields: Any) -> str:
    payload = {
        **fields,
        "agent_profile_ref": _file_reference_mapping(fields["agent_profile_ref"]),
        "selection_ref": (
            _file_reference_mapping(fields["selection_ref"])
            if fields["selection_ref"] is not None
            else None
        ),
        "capabilities": sorted(str(item) for item in fields["capabilities"]),
        "specialties": list(fields["specialties"]),
        "effective_data_policy": _data_policy_mapping(fields["effective_data_policy"]),
        "execution_limits": _limits_mapping(fields["execution_limits"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "MA-" + hashlib.sha256(encoded).hexdigest()[:16].upper()


def _file_reference_mapping(reference: FileReference) -> dict[str, object]:
    mapping: dict[str, object] = {
        "path": reference.path,
        "sha256": reference.sha256,
    }
    if reference.revision is not None:
        mapping["revision"] = reference.revision
    return mapping


def _is_sha256(value: str) -> bool:
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(character in "0123456789abcdefABCDEF" for character in digest)


def _data_policy_mapping(policy: DataPolicy) -> dict[str, object]:
    return {
        "local_only": policy.local_only,
        "zero_data_retention_required": policy.zero_data_retention_required,
        "training_opt_out_required": policy.training_opt_out_required,
        "allowed_regions": list(policy.allowed_regions),
        "allow_provider_server_tools": policy.allow_provider_server_tools,
    }


def _data_policy_from_mapping(value: Mapping[str, Any]) -> DataPolicy:
    expected = {
        "local_only",
        "zero_data_retention_required",
        "training_opt_out_required",
        "allowed_regions",
        "allow_provider_server_tools",
    }
    if set(value) != expected:
        raise ValueError("effective_data_policy must contain exactly its canonical fields")
    boolean_fields = expected - {"allowed_regions"}
    if any(not isinstance(value[field], bool) for field in boolean_fields):
        raise ValueError("effective_data_policy control fields must be boolean")
    raw_regions = value["allowed_regions"]
    if not isinstance(raw_regions, list) or any(
        not isinstance(region, str) or not region.strip() for region in raw_regions
    ):
        raise ValueError("effective_data_policy.allowed_regions must be an array of strings")
    regions = tuple(region.strip() for region in raw_regions)
    if len(regions) != len(set(regions)):
        raise ValueError("effective_data_policy.allowed_regions must be unique")
    return DataPolicy(
        local_only=value["local_only"],
        zero_data_retention_required=value["zero_data_retention_required"],
        training_opt_out_required=value["training_opt_out_required"],
        allowed_regions=regions,
        allow_provider_server_tools=value["allow_provider_server_tools"],
    )


def _limits_mapping(limits: ApiSessionLimits) -> dict[str, object]:
    return {
        "max_model_turns": limits.max_model_turns,
        "max_tool_calls": limits.max_tool_calls,
        "max_parallel_tool_calls": limits.max_parallel_tool_calls,
        "max_tool_result_chars": limits.max_tool_result_chars,
        "max_output_tokens_per_turn": limits.max_output_tokens_per_turn,
        "max_seconds": float(limits.max_seconds),
        "max_total_tokens": limits.max_total_tokens,
        "max_provider_reported_cost": (
            None
            if limits.max_provider_reported_cost is None
            else float(limits.max_provider_reported_cost)
        ),
        "allowed_tool_side_effects": sorted(limits.allowed_tool_side_effects),
        "max_compute_values_per_call": limits.max_compute_values_per_call,
    }


def _limits_from_mapping(value: Mapping[str, Any]) -> ApiSessionLimits:
    expected = {
        "max_model_turns",
        "max_tool_calls",
        "max_parallel_tool_calls",
        "max_tool_result_chars",
        "max_output_tokens_per_turn",
        "max_seconds",
        "max_total_tokens",
        "max_provider_reported_cost",
        "allowed_tool_side_effects",
        "max_compute_values_per_call",
    }
    if set(value) != expected:
        raise ValueError("execution_limits must contain exactly its canonical fields")
    raw_side_effects = value["allowed_tool_side_effects"]
    if not isinstance(raw_side_effects, list) or any(
        not isinstance(item, str) or not item for item in raw_side_effects
    ):
        raise ValueError("execution_limits.allowed_tool_side_effects must be an array of strings")
    if len(raw_side_effects) != len(set(raw_side_effects)):
        raise ValueError("execution_limits.allowed_tool_side_effects must be unique")
    return ApiSessionLimits(
        max_model_turns=value["max_model_turns"],
        max_tool_calls=value["max_tool_calls"],
        max_parallel_tool_calls=value["max_parallel_tool_calls"],
        max_tool_result_chars=value["max_tool_result_chars"],
        max_output_tokens_per_turn=value["max_output_tokens_per_turn"],
        max_seconds=value["max_seconds"],
        max_total_tokens=value["max_total_tokens"],
        max_provider_reported_cost=value["max_provider_reported_cost"],
        allowed_tool_side_effects=frozenset(raw_side_effects),
        max_compute_values_per_call=value["max_compute_values_per_call"],
    )
