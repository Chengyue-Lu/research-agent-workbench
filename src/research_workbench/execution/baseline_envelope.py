"""Compile the frozen A1/A2 public surface without selecting a Supply."""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource

from research_workbench.evaluation.pins import (
    EvaluationInputs,
    EvaluationValidationError,
    digest,
    file_ref,
    require,
)
from research_workbench.evaluation.qualification import validate_qualification
from research_workbench.evaluation.system_protocol import validate_protocol


KIND = "baseline_execution_envelope"
COMPILER_PATH = "src/research_workbench/execution/baseline_envelope.py"
BOUNDARIES = dict.fromkeys(
    (
        "execution_authority",
        "supply_selection",
        "permission_grant",
        "method_decision",
        "task_completion",
        "claim_acceptance",
        "human_decision",
        "promotion",
        "topic5_recovery",
    ),
    False,
)


def compiler_reference() -> dict[str, str]:
    """Identify the running compiler; this path is not a project input path."""
    return {
        "path": COMPILER_PATH,
        "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def _validate_definition(
    inputs: EvaluationInputs, name: str, document: Mapping[str, Any]
) -> None:
    schema = inputs.catalog.schema_for_kind(KIND)
    resources = (
        (item["$id"], Resource.from_contents(item))
        for item in (inputs.catalog.schema(name) for name in inputs.catalog.names)
    )
    validator = Draft202012Validator(
        {"$ref": f"{schema['$id']}#/$defs/{name}"},
        registry=Registry().with_resources(resources),
        format_checker=FormatChecker(),
    )
    errors = list(validator.iter_errors(document))
    require(
        not errors,
        f"baseline {name} schema: " + "; ".join(error.message for error in errors[:3]),
    )


def produce_a2_qualification(
    inputs: EvaluationInputs,
    *,
    protocol_ref: Mapping[str, Any],
    qualification_id: str,
    checked_at: str,
    bindings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Produce only the M5-owned A2 record and run its existing validator."""
    protocol = validate_protocol(inputs, protocol_ref)
    document = {
        "schema_version": "0.1.0",
        "record_kind": "arm_execution_qualification",
        "qualification_id": qualification_id,
        "version": "1.0.0",
        "protocol_ref": file_ref(protocol_ref),
        "manifest_ref": file_ref(protocol["manifest_ref"]),
        "arm_id": "plain-agent-tool",
        "producer": "m6-baseline-transport",
        "checked_at": checked_at,
        "bindings": copy.deepcopy(list(bindings)),
        "qualified": True,
        "boundaries": copy.deepcopy(
            inputs.catalog.schema_for_kind("arm_execution_qualification")["properties"][
                "boundaries"
            ]["const"]
        ),
    }
    validate_qualification(inputs, document, expected_protocol_ref=protocol_ref)
    return document


def _public_payload(
    inputs: EvaluationInputs,
    projection: Mapping[str, Any],
    task_ref: Mapping[str, Any],
    task: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_definition(inputs, "publicProjection", projection)
    require(
        file_ref(projection["task_ref"]) == file_ref(task_ref),
        "public projection Task substitution",
    )
    allowed = {
        digest(file_ref(ref))
        for ref in [
            *task["input_refs"],
            *manifest["frozen_conditions"]["context"]["initial_context_refs"],
        ]
    }
    public_inputs = []
    for reference in projection["input_refs"]:
        require(
            digest(file_ref(reference)) in allowed,
            "public input is outside frozen Task/context input references",
        )
        raw = inputs.read_bytes(reference)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvaluationValidationError("baseline public inputs must be UTF-8 text") from exc
        public_inputs.append({"ref": file_ref(reference), "text": text})
    return {
        "instruction": projection["instruction"],
        "inputs": public_inputs,
        "required_outputs": copy.deepcopy(projection["required_outputs"]),
        "tools": [],
    }


def _a2_tools(
    inputs: EvaluationInputs,
    qualification_ref: Mapping[str, Any],
    protocol_ref: Mapping[str, Any],
    task_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    qualification = inputs.read(qualification_ref, "arm_execution_qualification")
    require(qualification["arm_id"] == "plain-agent-tool", "baseline A2 qualification required")
    chains = validate_qualification(inputs, qualification, expected_protocol_ref=protocol_ref)
    selected = [
        (chain, binding)
        for chain, binding in zip(chains, qualification["bindings"])
        if file_ref(chain["snapshot"]["task_ref"]) == file_ref(task_ref)
    ]
    require(bool(selected), "A2 qualification has no binding for the selected Task")
    tools: dict[str, tuple[str, dict[str, Any]]] = {}
    for chain, binding in selected:
        visible = chain["interface"]["provider_visible_interface"]
        _validate_definition(inputs, "toolDefinition", visible)
        try:
            Draft202012Validator.check_schema(visible["input_schema"])
        except SchemaError as exc:
            raise EvaluationValidationError("A2 Tool input_schema is invalid JSON Schema") from exc
        # A function name is one callable. Multiple Requirement uses may share
        # it only when the exact implementation and visible interface agree.
        identity = digest(
            {
                "visible": visible,
                "supply": chain["snapshot"]["supply_identity"],
                "implementation_ref": file_ref(binding["implementation_ref"]),
                "component_refs": binding["component_refs"],
            }
        )
        prior = tools.get(visible["name"])
        require(prior is None or prior[0] == identity, "A2 Tool name binds different implementations/interfaces")
        tools[visible["name"]] = (identity, copy.deepcopy(dict(visible)))
    return [tools[name][1] for name in sorted(tools)]


def compile_baseline_envelope(
    inputs: EvaluationInputs,
    *,
    protocol_ref: Mapping[str, Any],
    task_ref: Mapping[str, Any],
    public_payload_ref: Mapping[str, Any],
    arm_id: str,
    envelope_id: str,
    accountable_owner: str,
    qualification_ref: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Use explicit public projection; all treatment controls remain metadata."""
    require(arm_id in {"plain-agent", "plain-agent-tool"}, "baseline supports only A1/A2")
    require(
        isinstance(accountable_owner, str) and bool(accountable_owner.strip()),
        "baseline accountable owner is required",
    )
    protocol = validate_protocol(inputs, protocol_ref)
    manifest_ref = file_ref(protocol["manifest_ref"])
    manifest = inputs.manifest(manifest_ref)
    frozen = manifest["frozen_conditions"]
    require(
        file_ref(task_ref) in [file_ref(ref) for ref in frozen["task_packet_refs"]],
        "baseline Task is outside frozen Manifest",
    )
    task = inputs.read(task_ref, "task_packet")
    require(
        file_ref(public_payload_ref)
        in [file_ref(ref) for ref in frozen["context"]["initial_context_refs"]],
        "public projection is not frozen in Manifest context",
    )
    projection = inputs.read(public_payload_ref)
    payload = _public_payload(inputs, projection, task_ref, task, manifest)
    if arm_id == "plain-agent":
        require(qualification_ref is None, "A1 must not carry A2 qualification")
    else:
        require(qualification_ref is not None, "A2 qualification is required")
        payload["tools"] = _a2_tools(inputs, qualification_ref, protocol_ref, task_ref)
    budget = copy.deepcopy(frozen["budget"])
    budget["max_seconds"] = protocol["execution_time_budget_seconds"]
    document = {
        "schema_version": "0.1.0",
        "record_kind": KIND,
        "version": "1.0.0",
        "envelope_id": envelope_id,
        "provider_visible_payload": payload,
        "transport_enforcement_metadata": {
            "protocol_ref": file_ref(protocol_ref),
            "manifest_ref": manifest_ref,
            "task_ref": file_ref(task_ref),
            "public_payload_ref": file_ref(public_payload_ref),
            "qualification_ref": file_ref(qualification_ref) if qualification_ref is not None else None,
            "arm_id": arm_id,
            "accountable_owner": accountable_owner,
            "execution_binding": copy.deepcopy(protocol["execution_binding"]),
            "budget": budget,
            "context": copy.deepcopy(frozen["context"]),
            "permissions": copy.deepcopy(task["permissions"]),
            "write_scope": copy.deepcopy(task["write_scope"]),
            "compiler_ref": compiler_reference(),
        },
        "boundaries": dict(BOUNDARIES),
    }
    inputs.validate(KIND, document)
    inputs.recheck()
    return document


def validate_baseline_envelope(
    inputs: EvaluationInputs,
    envelope: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
) -> dict[str, Any]:
    """Reload original inputs and require an exact deterministic projection."""
    inputs.validate(KIND, envelope)
    metadata = envelope["transport_enforcement_metadata"]
    require(
        file_ref(metadata["protocol_ref"]) == file_ref(expected_protocol_ref),
        "baseline Protocol substitution",
    )
    expected = compile_baseline_envelope(
        inputs,
        protocol_ref=expected_protocol_ref,
        task_ref=metadata["task_ref"],
        public_payload_ref=metadata["public_payload_ref"],
        arm_id=metadata["arm_id"],
        envelope_id=envelope["envelope_id"],
        accountable_owner=metadata["accountable_owner"],
        qualification_ref=metadata["qualification_ref"],
    )
    require(envelope == expected, "baseline envelope differs from frozen input compilation")
    return expected
