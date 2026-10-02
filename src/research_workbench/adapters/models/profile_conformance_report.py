"""Validate and publish a new, redacted profile conformance report file."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from research_workbench.adapters.models.provider_binding import CONFORMANCE_ROOTS, GRAPH_POLICY, read_provider_binding_manifest
from research_workbench.adapters.models.provider_source_closure import read_source_closure
from research_workbench.evaluation.pins import EvaluationInputs
from research_workbench.validation.schemas import SchemaCatalog


def _verify_binding(report, *, root, schema_root):
    """Derive archived pins without loading archived code or resolving a Key."""
    inputs = EvaluationInputs(root, schema_root)
    binding = report["binding"]
    manifest = read_provider_binding_manifest(inputs, binding["manifest_ref"]).to_mapping()
    if (manifest["version"] != "1.1.0" or manifest["binding_policy_version"] != GRAPH_POLICY
            or not set(CONFORMANCE_ROOTS) <= set(manifest["source_roots"])
            or manifest["implementation_closure_ref"] != binding["implementation_closure_ref"]
            or manifest["resolved_config_ref"] != report["config_ref"]
            or manifest["transport_identity"]["class"] !=
            "research_workbench.adapters.models.conformance_transport.GuardedConformanceTransport"):
        return False
    config = inputs.read(manifest["resolved_config_ref"])
    profile = inputs.read(manifest["profile_ref"], "provider_api_profile")
    if (config["profile_ref"] != report["profile_ref"]
            or profile["identity"]["provider"] != report["provider"]
            or profile["profile_id"] != report["profile_id"]
            or profile["profile_id"] != "deepseek-responses-nonthinking-v1"
            or config["model"] != report["requested_model"]
            or profile["identity"]["provider"] != "deepseek"
            or profile["protocol"]["family"] != "responses"
            or profile["model"]["requested_id"] != "deepseek-flash"
            or profile["generation"]["mode"] != "nonthinking"
            or any(model not in profile["model"]["allowed_observed_ids"] for model in report["observed_models"])
            or binding["body_policy"]["max_output_tokens"] != report["limits"]["max_output_tokens"]):
        return False
    attempt_ordinal = binding["attempt_ordinal"]
    if attempt_ordinal is None:
        if report["calls"]:
            return False
    elif report["accounting"] is not None:
        accounting = report["accounting"]
        if len([attempt for attempt in accounting["attempts"] if attempt["ordinal"] == attempt_ordinal]) != 1:
            return False
        reservations = [call for call in accounting["calls"] if call["attempt_ordinal"] == attempt_ordinal]
        if len(reservations) != len(report["calls"]):
            return False
        for ordinal, (reservation, call) in enumerate(zip(reservations, report["calls"]), 1):
            if (call["ordinal"] != ordinal
                    or reservation["input_upper_tokens"] != binding["input_upper_tokens"][ordinal - 1]
                    or reservation["output_upper_tokens"] != report["limits"]["max_output_tokens"]):
                return False
    graph = read_source_closure(inputs, binding["implementation_closure_ref"])
    for reference in report["source_refs"]:
        module = graph["modules"].get(reference["module"])
        if module is None or module["source_ref"]["sha256"] != reference["source_sha256"]:
            return False
    # The surrounding report cannot acquire human/Windows/API authority from a
    # source graph. Preserve these qualifications on every bound receipt.
    if not {"caller-attested-gates", "input-bound-proof-unverified", "windows-run-unaccepted",
            "remote-strict-unclaimed"} <= set(report["warnings"]):
        return False
    inputs.recheck()
    return True


def verify_profile_conformance_report(
    report: Mapping[str, object], *, schema_root: str | Path | None = None,
    root: str | Path | None = None,
) -> dict:
    """Cold-check a closed report; the result grants no execution acceptance."""
    serialized = None
    try:
        serialized = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    except (TypeError, ValueError, OverflowError, RecursionError):
        pass
    if serialized is None:
        raise ValueError("profile conformance report requires finite JSON primitives")
    detached = json.loads(serialized)
    if SchemaCatalog(schema_root).validate("profile_conformance_report", detached):
        raise ValueError("profile conformance report violates its closed contract")
    if detached["report_version"] == "1.1.0":
        if root is None:
            raise ValueError("bound profile conformance report requires its archive root")
        valid = False
        try:
            valid = _verify_binding(detached, root=root, schema_root=schema_root)
        except Exception:
            pass
        if not valid:
            raise ValueError("profile conformance report binding validation failed")
    return detached


def write_profile_conformance_report(
    report: Mapping[str, object], destination: str | Path, *, schema_root: str | Path | None = None,
    root: str | Path | None = None,
) -> None:
    """No overwrite or credential access; structural validity is not acceptance."""
    detached = verify_profile_conformance_report(report, schema_root=schema_root, root=root)
    serialized = json.dumps(detached, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    # 'x' refuses every existing target, including symlinks and directories.
    # An interrupted first write remains visible; retry must choose a fresh path.
    with Path(destination).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(serialized)
