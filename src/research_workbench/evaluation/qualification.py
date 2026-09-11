"""Frozen-to-runtime exact binding comparison; never selects a Supply."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from research_workbench.evaluation.pins import (
    EvaluationInputs,
    arm,
    digest,
    file_ref,
    require,
    sha,
    timestamp,
)
from research_workbench.evaluation.system_protocol import validate_protocol
from research_workbench.validation.capability_supply_registry import (
    validate_capability_supply_chain,
)
from research_workbench.validation.document_core import LoadedDocuments


def snapshot_chain(
    inputs: EvaluationInputs, reference: Mapping[str, Any]
) -> dict[str, Any]:
    """Load only the declared Snapshot closure, including unselected candidates."""
    before = set(inputs.documents)
    snapshot = inputs.read(reference, "resolved_capability_snapshot")
    chain = {"snapshot": snapshot}
    for key, kind in (
        ("task", "task_packet"),
        ("method_resolution", "method_resolution"),
        ("requirement", "capability_requirement"),
        ("resolution", "capability_resolution"),
        ("selected_supply_report", "capability_supply_report"),
    ):
        chain[key] = inputs.read(snapshot[key + "_ref"], kind)
    resolution = chain["resolution"]
    for ref in resolution["candidate_supply_report_refs"]:
        supply = inputs.read(ref, "capability_supply_report")
        for evidence in supply["conformance_evidence"]:
            inputs.read(evidence["artifact_ref"], "capability_conformance_evidence")
        projection = supply["supply_identity"].get("skill_release_projection_ref")
        if projection:
            inputs.read(projection, "skill_release_projection")
    # Explicitly validate the complete selected subgraph. The existing resolver
    # checker redoes candidate comparison; this function never produces selection.
    paths = set(inputs.documents) - before
    paths.update(
        (inputs.root / file_ref(snapshot[key])["path"]).resolve()
        for key in (
            "task_ref",
            "method_resolution_ref",
            "requirement_ref",
            "resolution_ref",
            "selected_supply_report_ref",
        )
    )
    paths.add((inputs.root / file_ref(reference)["path"]).resolve())
    # Include already-read candidates/evidence too, without merging other arms'
    # same-identity historical revisions into this validation invocation.
    for ref in resolution["candidate_supply_report_refs"]:
        path = (inputs.root / file_ref(ref)["path"]).resolve()
        paths.add(path)
        supply = inputs.documents[path]
        for ev in supply["conformance_evidence"]:
            paths.add((inputs.root / ev["artifact_ref"]["path"]).resolve())
        projection = supply["supply_identity"].get("skill_release_projection_ref")
        if projection:
            paths.add((inputs.root / file_ref(projection)["path"]).resolve())
    selected = LoadedDocuments()
    for path in paths:
        selected.add(
            path, inputs.documents[path], sha256=inputs.documents.sha256_for(path)
        )
    issues = validate_capability_supply_chain(selected)
    require(
        not issues,
        "Snapshot closure: " + "; ".join(f"{i.code}: {i.message}" for i in issues[:5]),
    )
    require(
        snapshot["task_ref"]["ref"]
        == f"{chain['task']['task_id']}@r{chain['task']['revision']}",
        "Snapshot Task identity mismatch",
    )
    require(
        chain["method_resolution"]["task_ref"]["sha256"].removeprefix("sha256:")
        == file_ref(snapshot["task_ref"])["sha256"],
        "Method Task binding mismatch",
    )
    return chain


def validate_requirement_closure(
    inputs: EvaluationInputs,
    chains: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    selected_arm: Mapping[str, Any],
    *,
    task_ref: Mapping[str, Any] | None = None,
) -> None:
    """Require one qualified binding per frozen Task/Method/Requirement identity.

    Method declares Requirement IDs, not Requirement document hashes. Each
    qualified Snapshot independently pins and validates those document bytes;
    the demand set comes from frozen Methods, never from submitted bindings.
    A4 records cover one frozen case Task; A3 covers the frozen arm.
    """
    tasks = {}
    for reference in manifest["frozen_conditions"]["task_packet_refs"]:
        task = inputs.read(reference, "task_packet")
        tasks[(task["task_id"], task["revision"], file_ref(reference)["sha256"])] = (
            digest(file_ref(reference)),
            task,
        )
    expected = Counter()
    covered_tasks = set()
    for reference in selected_arm["treatment_control"]["method_resolution_refs"]:
        method = inputs.read(reference, "method_resolution")
        bound = method["task_ref"]
        key = (bound["task_id"], bound["revision"], sha(bound["sha256"]))
        require(key in tasks, "frozen Method Task is outside frozen Task closure")
        task_identity, task = tasks[key]
        if task_ref is not None and task_identity != digest(file_ref(task_ref)):
            continue
        covered_tasks.add(task_identity)
        requirements = {
            identity
            for decision in method["action_decisions"]
            for identity in decision["capability_requirements"]
        }
        require(
            requirements == set(task["required_capabilities"]),
            "frozen Method Requirement set differs from Task capability closure",
        )
        for identity in requirements:
            expected[(task_identity, digest(file_ref(reference)), identity)] = 1
    required_tasks = (
        {digest(file_ref(task_ref))}
        if task_ref is not None
        else {identity for identity, _task in tasks.values()}
    )
    require(
        covered_tasks == required_tasks,
        "frozen Method closure must cover every qualified Task",
    )
    observed = Counter(
        (
            digest(file_ref(chain["snapshot"]["task_ref"])),
            digest(file_ref(chain["snapshot"]["method_resolution_ref"])),
            chain["snapshot"]["requirement_ref"]["requirement_id"],
        )
        for chain in chains
    )
    require(
        observed == expected,
        "qualified Requirement set must equal frozen Task/Method closure exactly once",
    )


def ceilings_narrow(frozen: Mapping[str, Any], runtime: Mapping[str, Any]) -> bool:
    """Compare authority ceilings, including roots and forbidden payload growth."""
    for name, ranks in (
        ("filesystem", ["forbidden", "read-only", "worktree-write", "workspace-write"]),
        ("network", ["forbidden", "search-and-fetch", "allowed"]),
    ):
        a, b = (
            frozen["supply_required_permissions"],
            runtime["supply_required_permissions"],
        )
        if (
            a[name] not in ranks
            or b[name] not in ranks
            or ranks.index(b[name]) > ranks.index(a[name])
        ):
            return False
    a, b = frozen["supply_required_permissions"], runtime["supply_required_permissions"]
    for permissions in (a, b):
        if any(
            not isinstance(root, str)
            or not root
            or "\\" in root
            or ":" in root
            or any(part in {"", ".", ".."} for part in root.split("/"))
            for root in permissions.get("allowed_roots", [])
        ):
            return False
    if b["external_write"] and not a["external_write"]:
        return False
    if "allowed_roots" in a and (
        "allowed_roots" not in b
        or not all(
            any(
                root == prior or root.startswith(prior.rstrip("/") + "/")
                for prior in a["allowed_roots"]
            )
            for root in b["allowed_roots"]
        )
    ):
        return False
    for key, allow, ranks in (
        ("supply_data_egress", "allowed_payloads", ["forbidden", "allowlisted-only"]),
        ("supply_side_effects", "allowed_effects", ["none", "allowlisted-only"]),
    ):
        a, b = frozen[key], runtime[key]
        if (
            a["policy"] not in ranks
            or b["policy"] not in ranks
            or ranks.index(b["policy"]) > ranks.index(a["policy"])
        ):
            return False
        if not set(b[allow]).issubset(a[allow]):
            return False
        if key == "supply_data_egress" and not set(a["forbidden_payloads"]).issubset(
            b["forbidden_payloads"]
        ):
            return False
    return True


def validate_implementation(
    inputs: EvaluationInputs, binding: Mapping[str, Any], chain: Mapping[str, Any]
) -> Mapping[str, Any]:
    identity = chain["snapshot"]["supply_identity"]
    inputs.read_bytes(binding["implementation_ref"])
    require(
        file_ref(binding["implementation_ref"])["sha256"]
        == sha(identity["content_hash"]),
        "implementation bytes do not match frozen Supply",
    )
    components = Counter(
        (c["component_ref"], c["version"], sha(c["content_hash"]))
        for c in identity["components"]
    )
    observed = Counter(
        (c["component_ref"], c["version"], file_ref(c["file_ref"])["sha256"])
        for c in binding["component_refs"]
    )
    require(components == observed, "component implementation closure mismatch")
    for component in binding["component_refs"]:
        inputs.read_bytes(component["file_ref"])
    interface = inputs.read(binding["interface_ref"], "evaluation_provider_interface")
    require(
        interface["supply_identity"] == identity, "provider interface Supply mismatch"
    )
    supply = chain["selected_supply_report"]
    for key in ("supported_inputs", "supported_outputs", "provided_capabilities"):
        require(interface[key] == supply[key], f"provider interface {key} mismatch")
    return interface


def validate_qualification(
    inputs: EvaluationInputs,
    document: Mapping[str, Any],
    *,
    expected_protocol_ref: Mapping[str, Any],
) -> list[dict[str, Any]]:
    inputs.validate("arm_execution_qualification", document)
    require(
        file_ref(document["protocol_ref"]) == file_ref(expected_protocol_ref),
        "qualification protocol substitution",
    )
    protocol = validate_protocol(inputs, expected_protocol_ref)
    require(
        file_ref(document["manifest_ref"]) == file_ref(protocol["manifest_ref"]),
        "qualification Manifest substitution",
    )
    manifest = inputs.manifest(document["manifest_ref"])
    selected_arm = arm(manifest, document["arm_id"])
    require(
        document["producer"]
        == (
            "m6-baseline-transport"
            if document["arm_id"] == "plain-agent-tool"
            else "evaluation-harness"
        ),
        "qualification producer ownership mismatch",
    )
    require(
        timestamp(document["checked_at"]) >= timestamp(protocol["frozen_at"]),
        "qualification precedes Protocol freeze",
    )
    expected = Counter(
        digest(file_ref(r)) for r in selected_arm["capability_snapshot_refs"]
    )
    actual = Counter(
        digest(file_ref(b["frozen_snapshot_ref"])) for b in document["bindings"]
    )
    require(
        expected == actual,
        "qualification must cover every frozen Snapshot exactly once",
    )
    qualified = []
    for binding in document["bindings"]:
        declarations = [
            b
            for b in protocol["execution_bindings"]
            if b["arm_id"] == document["arm_id"]
            and file_ref(b["snapshot_ref"]) == file_ref(binding["frozen_snapshot_ref"])
        ]
        require(
            len(declarations) == 1,
            "missing frozen implementation/interface declaration",
        )
        for key in ("implementation_ref", "component_refs", "interface_ref"):
            require(binding[key] == declarations[0][key], f"frozen {key} substitution")
        frozen = snapshot_chain(inputs, binding["frozen_snapshot_ref"])
        runtime = snapshot_chain(inputs, binding["runtime_snapshot_ref"])
        a, b = frozen["snapshot"], runtime["snapshot"]
        require(
            b["qualification"] == "runtime-execution"
            and b["boundaries"]["execution_input"],
            "runtime-execution Snapshot required",
        )
        for key in ("task_ref", "requirement_ref", "supply_identity"):
            require(a[key] == b[key], f"frozen {key} substitution")
        require(
            a["selected_supply_report_ref"]["ref"]
            == b["selected_supply_report_ref"]["ref"],
            "selected Supply identity substitution",
        )
        require(ceilings_narrow(a, b), "runtime ceiling expansion")
        require(
            not any(
                c["component_kind"] == "skill"
                for c in b["supply_identity"]["components"]
            ),
            "Skill component in A2/A3",
        )
        require(
            b["supply_identity"]["supply_kind"]
            in (
                {"tool"}
                if document["arm_id"] == "plain-agent-tool"
                else {"tool", "procedure"}
            ),
            "invalid arm Supply kind",
        )
        if document["arm_id"] == "mode-no-skill":
            require(
                runtime["method_resolution"]["skill_disposition"]["status"]
                == "no-skill",
                "A3 Core requires no-skill Method disposition",
            )
            require(
                a["method_resolution_ref"] == b["method_resolution_ref"],
                "A3 Method/Action substitution",
            )
            require(
                file_ref(b["method_resolution_ref"])
                in selected_arm["treatment_control"]["method_resolution_refs"],
                "A3 Method is outside frozen arm",
            )
        availability = runtime["selected_supply_report"]["availability"]
        require(
            timestamp(availability["observed_at"])
            <= timestamp(document["checked_at"])
            <= timestamp(availability["valid_until"]),
            "runtime availability is stale or future",
        )
        runtime["interface"] = validate_implementation(inputs, binding, runtime)
        validate_implementation(inputs, binding, frozen)
        qualified.append(runtime)
    if document["arm_id"] == "mode-no-skill":
        validate_requirement_closure(inputs, qualified, manifest, selected_arm)
    inputs.recheck()
    return qualified
