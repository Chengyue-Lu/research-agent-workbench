"""Evaluation-owned archive bridge over the existing M11 execution ports."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path

from research_workbench.evaluation.pins import file_ref, require, timestamp
from research_workbench.execution import (
    CloseoutPin, SKILL_CLOSEOUT_CONTRACT, build_generic_execution_receipt,
    build_skill_execution_receipt, execute_frozen_view, load_resolved_execution_view,
    load_runtime_bundle, validate_generic_execution_receipt, validate_skill_execution_receipt,
)
from research_workbench.observability.trace import AgentTraceRecorder


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def reference(root, path):
    return {"path": path.relative_to(root).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def persist(root, path, document):
    """Exclusive creation: a retained Attempt is never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(plain(document), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return reference(root, path)


def load_slice(inputs, binding):
    inputs.read_bytes(binding["bundle_ref"])
    bundle = load_runtime_bundle(binding["bundle_ref"]["path"], project_root=inputs.root,
                                 schema_root=inputs.catalog.root)
    require(bundle.manifest_sha256 == binding["bundle_ref"]["sha256"], "Harness Bundle pin drift")
    require(file_ref(bundle.manifest["entrypoint"]) == file_ref(binding["snapshot_ref"]),
            "Harness Bundle Snapshot substitution")
    view = load_resolved_execution_view(binding["view_ref"]["path"],
        expected_sha256=binding["view_ref"]["sha256"], bundle=bundle, schema_root=inputs.catalog.root)
    return bundle, view


def execute_slice(inputs, binding, *, attempt_id, destination, driver_factory, clock, skill):
    """The supplied Driver owns actual operations and contemporaneous facts.

    It receives the frozen View, an Attempt recorder and a fresh output directory;
    no Evaluation closure, oracle or qualification record is passed to it.
    """
    bundle, view = load_slice(inputs, binding)
    destination.mkdir(parents=True, exist_ok=False)
    task = inputs.read(view.document["task_ref"], "task_packet")
    trace_dir = destination / "trace"
    expected = view.document["binding"]
    components = inputs.read(binding["snapshot_ref"])["supply_identity"]["components"]
    recorder = AgentTraceRecorder(
        trace_dir, task_id=task["task_id"], task_revision=task["revision"],
        attempt_id=attempt_id, task_snapshot=task, accountable_owner="evaluation-harness",
        actor_id="m11-harness-driver", runtime_identity=expected["runtime"]["ref"],
        provider=expected["provider"]["ref"], read_allowlist=[i["path"] for i in bundle.manifest["documents"]],
        write_scope=["decisions/**", destination.relative_to(inputs.root).as_posix() + "/**"],
        tool_allowlist=[c["component_ref"] for c in components if c["component_kind"] == "tool"],
        created_at=clock.now().isoformat(),
    )
    view_ref = {"ref": f"{view.document['view_id']}@r{view.document['revision']}",
                **file_ref(binding["view_ref"])}
    recorder.record_decision_snapshot("execution-scope-binding", {
        "schema_version": "0.1.0", "record_kind": "execution-scope-binding",
        "view_ref": view_ref, "execution_scope": plain(view.document["execution_scope"]),
    })
    checker = destination / "checker-source.py"
    with checker.open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    driver = driver_factory(view, recorder, destination)
    host = execute_frozen_view(view, driver, report_id="HOST-" + attempt_id,
        attempt_id=attempt_id, clock=clock, schema_root=inputs.catalog.root,
        closeout_contract=SKILL_CLOSEOUT_CONTRACT if skill else "core-execution@0.1.0")
    host_ref = persist(inputs.root, destination / "host.json", host)
    recorder.record_attempt_status(host["status"], reason="Synthetic capability-slice execution")
    recorder.seal()
    trace_ref = reference(inputs.root, trace_dir / "INDEX.yaml")
    # This check is actually performed; replay only reads its pinned source bytes.
    subjects = [host_ref, trace_ref, *[file_ref(a) for a in host["artifacts"]]]
    for subject in subjects:
        inputs.read_bytes(subject)
    validation = {
        "schema_version": "0.1.0", "report_id": "CHECK-" + attempt_id, "status": "pass",
        "checker": {"checker_id": "harness-slice-integrity", "version": "1.0.0",
                    "source_ref": reference(inputs.root, checker)},
        "subject_refs": subjects,
        "checks": [{"code": "SUBJECT-INTEGRITY", "status": "pass",
                    "detail": "Exact retained Host, Trace and artifact bytes checked."}],
        "scope": "execution-contract-only", "limitations": ["Synthetic plumbing evidence only."],
    }
    validation_ref = persist(inputs.root, destination / "validation.json", validation)
    builder = build_skill_execution_receipt if skill else build_generic_execution_receipt
    receipt = builder(view, bundle, host_report=CloseoutPin(**host_ref),
        trace_index=CloseoutPin(**trace_ref), validations=(CloseoutPin(**validation_ref),),
        receipt_id="RECEIPT-" + attempt_id, schema_root=inputs.catalog.root)
    return persist(inputs.root, destination / "receipt.json", receipt)


def replay_slice(inputs, binding, receipt_ref, *, attempt_id, destination, skill, not_before):
    bundle, view = load_slice(inputs, binding)
    inputs.read_bytes(receipt_ref)
    if skill:
        receipt = validate_skill_execution_receipt(receipt_ref["path"],
            expected_sha256=receipt_ref["sha256"], project_root=inputs.root,
            schema_root=inputs.catalog.root).document
    else:
        receipt = validate_generic_execution_receipt(receipt_ref["path"],
            expected_sha256=receipt_ref["sha256"], bundle=bundle,
            schema_root=inputs.catalog.root).document
    require(receipt["attempt_id"] == attempt_id
            and file_ref(receipt["view_ref"]) == file_ref(binding["view_ref"]),
            "Harness actual Receipt Attempt/View substitution")
    for ref in (receipt_ref, receipt["host_report_ref"], receipt["trace_ref"],
                *receipt["artifact_refs"], *receipt["validation_refs"]):
        require((inputs.root / ref["path"]).resolve().is_relative_to(destination),
                "Harness slice output escapes its fresh Attempt")
    host = inputs.read(receipt["host_report_ref"])
    require(host["execution_phase"] != "driver-exception", "incomplete Driver exception capture")
    require(timestamp(receipt["started_at"]) >= timestamp(not_before),
            "Harness actual execution precedes preflight")
    return {"completed": "completed", "failed": "post-call-failed",
            "blocked": "preflight-blocked"}[receipt["status"]]
