"""Narrow structured-output contract for the K-API-2 Task-to-API slice.

The model proposes research objects and a compact Handoff body.  It never
chooses filesystem paths or emits Attempt/Receipt/Main State documents; those
remain trusted closeout responsibilities.
"""

from __future__ import annotations

from functools import cache
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from research_workbench.adapters.models import ModelResponse
from research_workbench.adapters.models.base import decode_strict_json_value
from research_workbench.context.handoff_transfer import KIND_LOCATOR_PREFIXES, RISK_REVIEW_KINDS
from research_workbench.contracts import RiskLevel, is_path_safe_identifier
from research_workbench.protocol import ProjectProtocol
from research_workbench.tasks import TaskPacket
from research_workbench.validation import SchemaCatalog, check_claim_ceiling


_MISSING = object()


@cache
def _schema_catalog() -> SchemaCatalog:
    return SchemaCatalog()


def _string_array() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {"type": "string", "minLength": 1},
        "uniqueItems": True,
    }


API_TASK_OUTPUT_SCHEMA: Mapping[str, Any] = {
    "type": "object",
    "required": ["artifacts", "handoff", "transfer_items"],
    "properties": {
        "artifacts": {
            "type": "array",
            "maxItems": 8,
            "items": {
                "type": "object",
                "required": ["document"],
                "properties": {"document": {"type": "object"}},
                "additionalProperties": False,
            },
        },
        "handoff": {
            "type": "object",
            "required": [
                "result",
                "limitations",
                "conflicts",
                "unresolved",
                "human_decision_required",
                "recommended_next_actions",
            ],
            "properties": {
                "result": {
                    "type": "object",
                    "required": ["summary", "facts", "inferences", "recommendations"],
                    "properties": {
                        "summary": {"type": "string", "minLength": 1},
                        "facts": _string_array(),
                        "inferences": _string_array(),
                        "recommendations": _string_array(),
                    },
                    "additionalProperties": False,
                },
                "limitations": _string_array(),
                "conflicts": {
                    "type": "array",
                    "items": {"type": "object", "minProperties": 1},
                },
                "unresolved": _string_array(),
                "human_decision_required": _string_array(),
                "recommended_next_actions": _string_array(),
            },
            "additionalProperties": False,
        },
        "transfer_items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "item_id",
                    "kind",
                    "criticality",
                    "required_for_handoff",
                    "statement",
                    "source_object_id",
                    "source_locator",
                    "handoff_locator",
                ],
                "properties": {
                    "item_id": {"type": "string", "minLength": 1},
                    "kind": {
                        "enum": [
                            "fact",
                            "inference",
                            "recommendation",
                            "limitation",
                            "conflict",
                            "unresolved",
                            "human-decision",
                            "negative-result",
                            "parameter",
                            "assumption",
                            "method-boundary",
                        ]
                    },
                    "criticality": {"enum": ["critical", "material", "informational"]},
                    "required_for_handoff": {"type": "boolean"},
                    "statement": {"type": "string", "minLength": 1},
                    "source_object_id": {"type": "string", "minLength": 1},
                    "source_locator": {"type": "string", "minLength": 1},
                    "handoff_locator": {"type": "string", "minLength": 1},
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


class ApiTaskOutputError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def parse_api_task_output(
    response: ModelResponse | None,
    *,
    task: TaskPacket,
    protocol: ProjectProtocol,
) -> dict[str, Any]:
    """Parse and validate only the final model response, never a transcript."""

    if response is None:
        raise ApiTaskOutputError("API-OUTPUT-MISSING", "session has no final response")
    text = "".join(block.text or "" for block in response.output if block.kind == "text")
    if not text.strip():
        raise ApiTaskOutputError("API-OUTPUT-MISSING", "final response has no text output")
    try:
        value = decode_strict_json_value(text)
    except ValueError as exc:
        position = getattr(exc, "pos", None)
        detail = f" at offset {position}" if isinstance(position, int) else ""
        raise ApiTaskOutputError("API-OUTPUT-JSON", f"invalid JSON{detail}") from exc
    validate_api_task_output(value, task=task, protocol=protocol)
    if not isinstance(value, dict):  # validated above; keeps the return type honest
        raise ApiTaskOutputError("API-OUTPUT-CONTRACT", "top-level output must be an object")
    return value


def validate_api_task_output(
    value: Any,
    *,
    task: TaskPacket,
    protocol: ProjectProtocol,
) -> None:
    """Validate all model-controlled K-API-2 output before closeout staging."""

    errors = sorted(
        Draft202012Validator(API_TASK_OUTPUT_SCHEMA).iter_errors(value),
        key=lambda item: list(item.absolute_path),
    )
    if errors:
        first = errors[0]
        pointer = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in first.absolute_path
        )
        raise ApiTaskOutputError("API-OUTPUT-CONTRACT", f"{pointer}: {first.message}")
    if not isinstance(value, Mapping):  # guarded by the schema; keeps type checking honest
        raise ApiTaskOutputError("API-OUTPUT-CONTRACT", "top-level output must be an object")
    _validate_research_payload(value, task=task, protocol=protocol)


def _validate_research_payload(
    value: Mapping[str, Any],
    *,
    task: TaskPacket,
    protocol: ProjectProtocol,
) -> None:
    """Admit model-controlled research content before any closeout staging starts."""

    if task.handoff_policy.semantic_review == "required":
        raise ApiTaskOutputError(
            "API-OUTPUT-HUMAN-REVIEW-REQUIRED",
            "Task requires a semantic review unavailable in K-API-2",
        )
    catalog = _schema_catalog()
    frozen_inputs = {
        reference.path: reference.sha256.removeprefix("sha256:").lower()
        for reference in task.input_refs
    }
    documents: dict[str, Mapping[str, Any]] = {}
    portable_object_ids: set[str] = set()
    evidence_count = 0
    for index, wrapper in enumerate(value["artifacts"]):
        document = wrapper["document"]
        errors = catalog.validate("research_object", document)
        if errors:
            first = errors[0]
            raise ApiTaskOutputError(
                "API-OUTPUT-ARTIFACT-CONTRACT",
                f"$.artifacts[{index}].document{first.pointer[1:]}: {first.message}",
            )
        object_id = document.get("object_id")
        if not is_path_safe_identifier(object_id):
            raise ApiTaskOutputError(
                "API-OUTPUT-OBJECT-ID",
                f"$.artifacts[{index}].document.object_id is not path-safe",
            )
        portable_object_id = str(object_id).casefold()
        if portable_object_id in portable_object_ids:
            raise ApiTaskOutputError(
                "API-OUTPUT-OBJECT-DUPLICATE",
                f"object_id collides after portable path normalization: {object_id}",
            )
        portable_object_ids.add(portable_object_id)
        documents[object_id] = document
        if document.get("object_type") == "evidence":
            evidence_count += 1
            source_ref = document.get("source_ref")
            expected_hash = frozen_inputs.get(source_ref) if isinstance(source_ref, str) else None
            if expected_hash is None:
                raise ApiTaskOutputError(
                    "API-OUTPUT-EVIDENCE-SOURCE",
                    "Evidence source_ref must name one exact frozen Task input path",
                )
            content_hash = str(document.get("content_hash", "")).removeprefix("sha256:").lower()
            if content_hash != expected_hash:
                raise ApiTaskOutputError(
                    "API-OUTPUT-EVIDENCE-HASH",
                    "Evidence content_hash must equal the frozen Task input hash",
                )
        if document.get("object_type") == "claim":
            blockers = [
                risk
                for risk in check_claim_ceiling(protocol, str(document.get("strength", "")))
                if risk.level == RiskLevel.BLOCK
            ]
            if blockers:
                raise ApiTaskOutputError("API-OUTPUT-CLAIM-CEILING", blockers[0].message)

    required = {
        item if isinstance(item, str) else str(item.get("contract", ""))
        for item in task.required_outputs
    }
    if "evidence-record" in required and evidence_count == 0:
        raise ApiTaskOutputError(
            "API-OUTPUT-EVIDENCE-MISSING",
            "Task requires at least one admitted Evidence record",
        )
    if not documents:
        raise ApiTaskOutputError(
            "API-OUTPUT-ARTIFACT-MISSING",
            "a completed Attempt requires at least one research artifact",
        )

    handoff = value["handoff"]
    item_ids: set[str] = set()
    handoff_locators: set[str] = set()
    transfer_items = value["transfer_items"]
    if not transfer_items:
        raise ApiTaskOutputError(
            "API-OUTPUT-TRANSFER-EMPTY",
            "completed research artifacts require transfer items",
        )
    for index, item in enumerate(transfer_items):
        if item["required_for_handoff"] is not True:
            raise ApiTaskOutputError(
                "API-OUTPUT-TRANSFER-OPTIONAL",
                f"$.transfer_items[{index}] must be required_for_handoff in K-API-2",
            )
        if task.handoff_policy.semantic_review == "risk-triggered" and (
            item["criticality"] == "critical" or item["kind"] in RISK_REVIEW_KINDS
        ):
            raise ApiTaskOutputError(
                "API-OUTPUT-HUMAN-REVIEW-REQUIRED",
                f"$.transfer_items[{index}] requires a semantic review unavailable in K-API-2",
            )
        item_id = item["item_id"]
        if item_id in item_ids:
            raise ApiTaskOutputError(
                "API-OUTPUT-TRANSFER-DUPLICATE",
                f"duplicate transfer item_id: {item_id}",
            )
        item_ids.add(item_id)
        source = documents.get(item["source_object_id"])
        if source is None:
            raise ApiTaskOutputError(
                "API-OUTPUT-TRANSFER-SOURCE",
                f"$.transfer_items[{index}] references an unknown source_object_id",
            )
        source_value = _resolve_pointer(source, item["source_locator"])
        if source_value is _MISSING:
            raise ApiTaskOutputError(
                "API-OUTPUT-SOURCE-LOCATOR",
                f"$.transfer_items[{index}].source_locator does not resolve",
            )
        if not isinstance(source_value, str):
            raise ApiTaskOutputError(
                "API-OUTPUT-SOURCE-LOCATOR-TYPE",
                f"$.transfer_items[{index}].source_locator must resolve to a string",
            )
        handoff_locator = item["handoff_locator"]
        if handoff_locator in handoff_locators:
            raise ApiTaskOutputError(
                "API-OUTPUT-HANDOFF-LOCATOR-DUPLICATE",
                f"duplicate handoff_locator: {handoff_locator}",
            )
        handoff_locators.add(handoff_locator)
        handoff_value = _resolve_pointer(handoff, handoff_locator)
        if handoff_value is _MISSING:
            raise ApiTaskOutputError(
                "API-OUTPUT-HANDOFF-LOCATOR",
                f"$.transfer_items[{index}].handoff_locator does not resolve",
            )
        if not isinstance(handoff_value, str):
            raise ApiTaskOutputError(
                "API-OUTPUT-HANDOFF-LOCATOR-TYPE",
                f"$.transfer_items[{index}].handoff_locator must resolve to a string",
            )
        allowed = KIND_LOCATOR_PREFIXES.get(item["kind"], ())
        if not any(handoff_locator.startswith(prefix) for prefix in allowed):
            raise ApiTaskOutputError(
                "API-OUTPUT-HANDOFF-SECTION",
                f"$.transfer_items[{index}] maps to an incompatible Handoff section",
            )
        statement = item["statement"]
        if source_value != statement:
            raise ApiTaskOutputError(
                "API-OUTPUT-SOURCE-STATEMENT-DRIFT",
                f"$.transfer_items[{index}].statement differs from its source locator",
            )
        if handoff_value != statement:
            raise ApiTaskOutputError(
                "API-OUTPUT-HANDOFF-STATEMENT-DRIFT",
                f"$.transfer_items[{index}].statement differs from its Handoff locator",
            )


def _resolve_pointer(value: Any, pointer: str) -> Any:
    if pointer == "":
        return value
    if not pointer.startswith("/"):
        return _MISSING
    current = value
    for encoded in pointer[1:].split("/"):
        token = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                return _MISSING
            current = current[token]
        elif isinstance(current, list):
            if not token.isascii() or not token.isdigit() or len(token) > 20:
                return _MISSING
            index = int(token)
            if index >= len(current):
                return _MISSING
            current = current[index]
        else:
            return _MISSING
    return current
