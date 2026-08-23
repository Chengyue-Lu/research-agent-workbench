from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from research_workbench.contracts.common import (
    ContractError,
    ensure_unique,
    mapping_tuple,
    mapping_value,
    optional_string,
    require_string,
    string_tuple,
)


DECISION_AUTHORITY_MATRIX_ID = "rwb-decision-authority"
DECISION_AUTHORITY_MATRIX_VERSION = "1.0.0"
DECISION_AUTHORITY_MATRIX_REF = (
    f"{DECISION_AUTHORITY_MATRIX_ID}@{DECISION_AUTHORITY_MATRIX_VERSION}"
)
DECISION_AUTHORITY_MATRIX_PATH = (
    "registry/authority/decision-authority-matrix.yaml"
)

DECISION_KINDS_V1 = frozenset(
    {
        "mode-selection",
        "action-selection",
        "mechanism-selection",
        "skill-tool-binding",
        "permission-relaxation",
        "data-boundary-relaxation",
        "claim-promotion",
    }
)
DETERMINISTIC_COMMIT_KINDS = frozenset(
    {
        "mode-selection",
        "action-selection",
        "mechanism-selection",
        "skill-tool-binding",
    }
)
REQUIRED_COMMIT_FACTS_V1 = {
    ("mode-selection", "deterministic-resolver"): frozenset(
        {"mode-candidates-registered", "selection-unambiguous"}
    ),
    ("mode-selection", "human-gate"): frozenset(
        {"mode-candidates-registered", "ambiguity-disclosed"}
    ),
    ("action-selection", "deterministic-resolver"): frozenset(
        {"action-registry-closed", "trigger-match-unambiguous"}
    ),
    ("action-selection", "human-gate"): frozenset(
        {"action-registry-closed", "ambiguity-disclosed"}
    ),
    ("mechanism-selection", "deterministic-resolver"): frozenset(
        {"method-obligations-closed", "minimal-mechanism-unambiguous"}
    ),
    ("mechanism-selection", "human-gate"): frozenset(
        {"method-obligations-closed", "ambiguity-disclosed"}
    ),
    ("skill-tool-binding", "deterministic-resolver"): frozenset(
        {
            "capability-snapshot-frozen",
            "permission-intersection-satisfied",
            "binding-unambiguous",
        }
    ),
    ("skill-tool-binding", "human-gate"): frozenset(
        {
            "capability-snapshot-frozen",
            "permission-intersection-satisfied",
            "ambiguity-disclosed",
        }
    ),
    ("permission-relaxation", "human-gate"): frozenset(
        {"requested-scope-explicit", "revised-task-or-protocol", "risk-review-complete"}
    ),
    ("data-boundary-relaxation", "human-gate"): frozenset(
        {
            "requested-scope-explicit",
            "data-destination-explicit",
            "revised-task-or-protocol",
            "risk-review-complete",
        }
    ),
    ("claim-promotion", "human-gate"): frozenset(
        {
            "evidence-chain-structurally-valid",
            "claim-ceiling-allows",
            "limitations-reviewed",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class DecisionAuthorityRule:
    operation: str
    actor_class: str
    required_facts: tuple[str, ...]
    human_gate_required: bool
    effect: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DecisionAuthorityRule":
        gate_required = data.get("human_gate_required")
        if not isinstance(gate_required, bool):
            raise ContractError("human_gate_required", "must be a boolean")
        return cls(
            operation=require_string(data, "operation"),
            actor_class=require_string(data, "actor_class"),
            required_facts=ensure_unique(
                string_tuple(data, "required_facts", required=True),
                "required_facts",
            ),
            human_gate_required=gate_required,
            effect=require_string(data, "effect"),
        )


@dataclass(frozen=True, slots=True)
class DecisionAuthorityEntry:
    decision_kind: str
    description: str
    rules: tuple[DecisionAuthorityRule, ...]
    denied_disposition: str

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DecisionAuthorityEntry":
        rules = tuple(
            DecisionAuthorityRule.from_mapping(item)
            for item in mapping_tuple(data, "rules")
        )
        if not rules:
            raise ContractError("rules", "must contain at least one authority rule")
        pairs = [(rule.operation, rule.actor_class) for rule in rules]
        if len(pairs) != len(set(pairs)):
            raise ContractError("rules", "operation and actor_class pairs must be unique")
        return cls(
            decision_kind=require_string(data, "decision_kind"),
            description=require_string(data, "description"),
            rules=rules,
            denied_disposition=require_string(data, "denied_disposition"),
        )

    def rule_for(
        self, operation: str, actor_class: str
    ) -> DecisionAuthorityRule | None:
        return next(
            (
                rule
                for rule in self.rules
                if rule.operation == operation and rule.actor_class == actor_class
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class DecisionAuthorityMatrix:
    schema_version: str
    matrix_id: str
    version: str
    authority_classes: tuple[str, ...]
    entries: tuple[DecisionAuthorityEntry, ...]
    limitations: tuple[str, ...]

    @property
    def reference(self) -> str:
        return f"{self.matrix_id}@{self.version}"

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "DecisionAuthorityMatrix":
        matrix = cls(
            schema_version=require_string(data, "schema_version"),
            matrix_id=require_string(data, "matrix_id"),
            version=require_string(data, "version"),
            authority_classes=ensure_unique(
                string_tuple(data, "authority_classes", required=True),
                "authority_classes",
            ),
            entries=tuple(
                DecisionAuthorityEntry.from_mapping(item)
                for item in mapping_tuple(data, "entries")
            ),
            limitations=ensure_unique(
                string_tuple(data, "limitations", required=True),
                "limitations",
            ),
        )
        matrix._validate_invariants()
        return matrix

    def _validate_invariants(self) -> None:
        if self.schema_version != "0.1.0":
            raise ContractError("schema_version", "must be 0.1.0")
        if self.reference != DECISION_AUTHORITY_MATRIX_REF:
            raise ContractError(
                "matrix_id",
                f"supported Matrix identity is {DECISION_AUTHORITY_MATRIX_REF}",
            )
        if set(self.authority_classes) != {
            "agent",
            "deterministic-resolver",
            "human-gate",
        }:
            raise ContractError("authority_classes", "must contain the three v1 authority classes")
        kinds = [entry.decision_kind for entry in self.entries]
        if len(kinds) != len(set(kinds)):
            raise ContractError("entries", "decision_kind values must be unique")
        if set(kinds) != DECISION_KINDS_V1:
            raise ContractError("entries", "must contain the exact v1 decision kind closed set")

        for entry in self.entries:
            pairs = {(rule.operation, rule.actor_class) for rule in entry.rules}
            if ("propose", "agent") not in pairs or (
                "validate",
                "deterministic-resolver",
            ) not in pairs:
                raise ContractError(
                    f"entries.{entry.decision_kind}",
                    "must allow agent proposal and deterministic structural validation",
                )
            expected_commit_actors = (
                {"deterministic-resolver", "human-gate"}
                if entry.decision_kind in DETERMINISTIC_COMMIT_KINDS
                else {"human-gate"}
            )
            actual_commit_actors = {
                rule.actor_class
                for rule in entry.rules
                if rule.operation == "commit"
            }
            if actual_commit_actors != expected_commit_actors:
                raise ContractError(
                    f"entries.{entry.decision_kind}.rules",
                    "commit authority does not match the frozen v1 boundary",
                )
            for rule in entry.rules:
                expected_effect = {
                    "propose": "non-binding-proposal",
                    "validate": "structural-validation",
                    "commit": "binding-decision",
                }.get(rule.operation)
                if expected_effect is None or rule.effect != expected_effect:
                    raise ContractError(
                        f"entries.{entry.decision_kind}.rules",
                        "operation and effect must remain aligned",
                    )
                allowed_operation = {
                    "agent": "propose",
                    "human-gate": "commit",
                }.get(rule.actor_class)
                if allowed_operation is not None and rule.operation != allowed_operation:
                    raise ContractError(
                        f"entries.{entry.decision_kind}.rules",
                        f"{rule.actor_class} cannot perform {rule.operation}",
                    )
                if rule.actor_class == "deterministic-resolver" and rule.operation not in {
                    "validate",
                    "commit",
                }:
                    raise ContractError(
                        f"entries.{entry.decision_kind}.rules",
                        "deterministic resolver may only validate or commit",
                    )
                must_require_gate = (
                    rule.actor_class == "human-gate" and rule.operation == "commit"
                )
                if rule.human_gate_required != must_require_gate:
                    raise ContractError(
                        f"entries.{entry.decision_kind}.rules",
                        "only Human Gate commits require a human_gate_ref",
                    )
                if rule.operation == "commit" and set(rule.required_facts) != set(
                    REQUIRED_COMMIT_FACTS_V1[(entry.decision_kind, rule.actor_class)]
                ):
                    raise ContractError(
                        f"entries.{entry.decision_kind}.rules",
                        "commit required_facts do not match the frozen v1 boundary",
                    )

    def entry_for(self, decision_kind: str) -> DecisionAuthorityEntry | None:
        return next(
            (entry for entry in self.entries if entry.decision_kind == decision_kind),
            None,
        )


def evaluate_authority_rule_eligibility(
    eligibility: Mapping[str, Any],
    matrix_document: Mapping[str, Any],
    *,
    matrix_content_hash: str,
) -> dict[str, str]:
    matrix = DecisionAuthorityMatrix.from_mapping(matrix_document)
    matrix_ref = mapping_value(eligibility, "matrix_ref", required=True)
    if matrix_ref.get("ref") != matrix.reference:
        return _blocked(
            "AUTHORITY-MATRIX-REF-MISMATCH",
            "blocked",
            "The eligibility record does not reference the loaded Matrix identity.",
        )
    if matrix_ref.get("document_path") != DECISION_AUTHORITY_MATRIX_PATH:
        return _blocked(
            "AUTHORITY-MATRIX-PATH-MISMATCH",
            "blocked",
            "The eligibility record does not reference the canonical Matrix path.",
        )
    normalized_hash = matrix_content_hash.removeprefix("sha256:").lower()
    recorded_hash = str(matrix_ref.get("content_hash", "")).removeprefix("sha256:").lower()
    if recorded_hash != normalized_hash:
        return _blocked(
            "AUTHORITY-MATRIX-HASH-MISMATCH",
            "blocked",
            "The eligibility Matrix hash does not match the loaded raw document bytes.",
        )

    decision_kind = require_string(eligibility, "decision_kind")
    operation = require_string(eligibility, "operation")
    actor_class = require_string(eligibility, "actor_class")
    facts = set(string_tuple(eligibility, "asserted_facts", required=True))
    human_gate_ref = optional_string(eligibility, "human_gate_ref")
    entry = matrix.entry_for(decision_kind)
    if entry is None:
        return _blocked(
            "AUTHORITY-DECISION-KIND-UNKNOWN",
            "blocked",
            "The requested decision kind is not governed by this Matrix version.",
        )
    rule = entry.rule_for(operation, actor_class)
    if rule is None:
        return _blocked(
            "AUTHORITY-RULE-DENIED",
            entry.denied_disposition,
            f"{actor_class} is not eligible for the {operation} rule for {decision_kind}.",
        )
    if rule.human_gate_required and human_gate_ref is None:
        return _blocked(
            "AUTHORITY-HUMAN-GATE-REQUIRED",
            "human-gate",
            "Eligibility for this commit rule requires an explicit Human Gate reference; the reference does not prove approval.",
        )
    if not rule.human_gate_required and human_gate_ref is not None:
        return _blocked(
            "AUTHORITY-HUMAN-GATE-NOT-CONSUMED",
            "blocked",
            "This eligibility path cannot consume a Human Gate as cosmetic approval.",
        )
    missing = sorted(set(rule.required_facts) - facts)
    if missing:
        return _blocked(
            "AUTHORITY-ASSERTED-FACTS-MISSING",
            "blocked",
            f"Required asserted facts are missing: {', '.join(missing)}.",
        )
    return {
        "status": "eligible",
        "code": "AUTHORITY-RULE-ELIGIBLE",
        "disposition": "eligible-for-decision",
        "reason": (
            f"Assuming the asserted facts are true, {actor_class} is eligible for the "
            f"{operation} rule for {decision_kind}; no decision or authority effect is executed."
        ),
    }


def _blocked(code: str, disposition: str, reason: str) -> dict[str, str]:
    return {
        "status": "blocked",
        "code": code,
        "disposition": disposition,
        "reason": reason,
    }
