"""Per-invocation production producers with explicitly offline qualification.

Seed contracts are test fixtures; every selected Snapshot, Bundle and View below
is newly produced for the actual role Task. No live/source admission is implied.
"""
import copy
import json
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.binding import freeze_capability_selection, freeze_execution_inputs
from research_workbench.entry.executor import FrozenRoleBinding
from research_workbench.execution import CloseoutPin, PinnedExecutionInput
from research_workbench.io import load_document
from tests.execution_fixtures import ExecutionViewFixture, RuntimeBundleFixture, SequenceClock
from tests.test_entry_driver import observe

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "work/TASK-MR-ES-FROZEN-001"


def write_document(root, path, document):
    destination = root / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return PinnedExecutionInput(path, hash_file(destination))


class OfflineRoleFactory:
    def __init__(self, root, provider, *, tool=None, direct_tool=False, session_limits=None):
        self.root, self.provider = root, provider
        RuntimeBundleFixture()._build_bundle(root)
        self.seed_manifest = load_document(root / "bundle/manifest.yaml")
        self.seed_method = load_document(root / "bundle/method.yaml")
        self.task = load_document(root / "bundle/task.yaml")
        self.task["budget"] = {"max_turns": 10, "max_output_tokens": 2048, "max_seconds": 120}
        self.task["delegation"] = {"allowed": True, "max_depth": 2, "max_parallel": 3,
                                   "sub_budget": {"max_turns": 3, "max_output_tokens": 512, "max_seconds": 60}}
        text = root / "materials/approved.txt"
        text.parent.mkdir(parents=True)
        text.write_text("A bounded synthetic document. No research conclusion is requested.\n", encoding="utf-8")
        self.task["input_refs"] = [{"path": "materials/approved.txt", "sha256": hash_file(text)}]
        self.inputs = ExecutionViewFixture()._inputs(root)
        profile = load_document(root / self.inputs["agent_profile"].path)
        profile["delegation"]["allowed"] = True
        self.inputs["agent_profile"] = write_document(root, "view/profile.yaml", profile)
        self.tool, self.session_limits = tool, session_limits
        self.tool_ref = "bounded-exact-read-tool"
        if tool:
            supply = load_document(root / "bundle/supply.yaml")
            supply["supply_identity"]["components"].append({"component_kind": "tool", "component_ref": self.tool_ref,
                "version": "1.0.0", "content_hash": hash_file(Path(__file__))})
            if direct_tool:
                supply["supply_identity"]["supply_kind"] = "tool"
            write_document(root, "bundle/supply.yaml", supply)
        self.calls = []
        self.bindings = []
        self.selections = []
        self.published_controls = None

    def __call__(self, invocation):
        index = len(self.calls) + 1
        directory = f"controls/role-{index}"
        task_ref = write_document(self.root, directory + "/task.json", invocation.task)
        if self.published_controls is not None and invocation.task == self.task:
            task_ref = self.published_controls["task.json"]
        method = copy.deepcopy(self.seed_method)
        method["task_ref"].update(task_id=invocation.task["task_id"], revision=invocation.task["revision"], sha256=task_ref.sha256)
        method_ref = write_document(self.root, directory + "/method.json", method)
        if self.published_controls is not None and invocation.task == self.task:
            method_ref = self.published_controls["method.json"]
        requirement_ref = (self.published_controls["requirement-1.json"] if self.published_controls is not None
            else PinnedExecutionInput("bundle/requirement.yaml", hash_file(self.root / "bundle/requirement.yaml")))

        def verify(identity, evidence, capability):
            reference = evidence["artifact_ref"]
            if hash_file(self.root / reference["path"]) != reference["sha256"]:
                return "fail"
            observation = load_document(self.root / reference["path"])
            return "pass" if (observation["evidence_kind"] == "local-conformance"
                and observation["implementation_ref"] == identity.implementation_ref
                and observation["implementation_version"] == identity.implementation_version
                and capability in observation["capability_ids"] and observation["result"] == "pass") else "fail"

        selection = freeze_capability_selection(self.root, task=task_ref, method=method_ref,
            requirement=requirement_ref,
            supplies=[PinnedExecutionInput("bundle/supply.yaml", hash_file(self.root / "bundle/supply.yaml"))],
            supporting_documents=[{"kind": "capability_conformance_evidence", "path": "bundle/conformance.yaml",
                                   "sha256": hash_file(self.root / "bundle/conformance.yaml")}],
            evidence_check=verify, output_directory=directory + "/selection", resolution_id=f"CR-ROLE-{index}",
            snapshot_id=f"SNAPSHOT-ROLE-{index}", qualification="runtime-execution",
            evaluated_at="2026-08-26T00:00:00Z", schema_root=ROOT / "schemas")
        if selection.status != "satisfied":
            raise ValueError("offline role has no qualified test Supply")
        replacements = {"bundle/task.yaml": task_ref, "bundle/method.yaml": method_ref,
                        "bundle/requirement.yaml": requirement_ref,
                        "bundle/resolution.yaml": selection.resolution, "bundle/snapshot.yaml": selection.snapshot}
        manifest = copy.deepcopy(self.seed_manifest)
        manifest["bundle_id"] = f"RB-ROLE-{index}"
        for ref in manifest["documents"]:
            if ref["path"] in replacements:
                pin = replacements[ref["path"]]
                ref.update(path=pin.path, sha256=pin.sha256)
            else:
                ref["sha256"] = hash_file(self.root / ref["path"])
        manifest["entrypoint"].update(path=selection.snapshot.path, sha256=selection.snapshot.sha256)
        for edge in manifest["imports"]:
            for key in ("from_path", "to_path"):
                if edge[key] in replacements:
                    edge[key] = replacements[edge[key]].path
        frozen = freeze_execution_inputs(self.root, manifest=manifest, **self.inputs,
            output_directory=directory + "/execution", execution_at="2026-08-26T00:00:00Z",
            view_id=f"VIEW-ROLE-{index}", schema_root=ROOT / "schemas")
        scope = invocation.task["write_scope"][0].removesuffix("/**")
        binding = FrozenRoleBinding(CloseoutPin(frozen.bundle.path, frozen.bundle.sha256),
            CloseoutPin(frozen.view.path, frozen.view.sha256), self.provider, observe,
            scope + f"/slice-{index}/archive", scope + f"/slice-{index}/output.json",
            "deterministic-check-report", f"ROLE-{index}", schema_root=ROOT / "schemas",
            host_clock=SequenceClock("2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z", "2026-08-26T00:00:03Z"),
            session_clock=lambda: 0.0, tools=() if self.tool is None else (self.tool,),
            tool_refs={} if self.tool is None else {self.tool.definition.name: self.tool_ref},
            session_limits=self.session_limits)
        self.calls.append(invocation)
        self.bindings.append(binding)
        self.selections.append(selection)
        return binding

    def child(self, ordinal):
        child = copy.deepcopy(self.task)
        child["task_id"] = "CHILD-" + str(ordinal)
        child["goal"] = "Read the bounded synthetic input and return a limited observation."
        child["delegation"] = {"allowed": False}
        child["budget"] = {"max_turns": 3, "max_output_tokens": 512, "max_seconds": 60}
        child["write_scope"] = [PREFIX + f"/children/{ordinal}/**"]
        return child
