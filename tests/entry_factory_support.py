"""Explicitly offline inputs for package factory/caller tests.

These temporary contracts and injected checks prove bounded consumer behavior.
They are not provider live evidence, Skill/Source admission or a paid grant.
Only tests import this module; product code never imports test fixture builders.
"""
from __future__ import annotations

import copy
from pathlib import Path

from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.factory import ApiRoleBindingFactory
from research_workbench.entry.workflow import RoleInvocation
from research_workbench.execution import PinnedExecutionInput
from research_workbench.io import load_document
from tests.entry_chain_support import OfflineRoleFactory, PREFIX, write_document
from tests.test_entry_driver import ScriptedRoleProvider, observe


class FactoryTestInputs:
    """A test-only explicit input provider, separate from the package factory."""

    def __init__(self, root: Path, provider=None):
        self.root = Path(root)
        self.provider = provider if provider is not None else ScriptedRoleProvider()
        seed = OfflineRoleFactory(self.root, self.provider)
        self.task = copy.deepcopy(seed.task)
        self.method = copy.deepcopy(seed.seed_method)
        self.requirement = load_document(self.root / "bundle/requirement.yaml")
        self.task_pin = write_document(self.root, "controls/root-task.json", self.task)
        self.method["task_ref"].update(task_id=self.task["task_id"], revision=self.task["revision"],
                                       sha256=self.task_pin.sha256)
        self.method_pin = write_document(self.root, "controls/root-method.json", self.method)
        self.requirement_pin = PinnedExecutionInput("bundle/requirement.yaml",
            hash_file(self.root / "bundle/requirement.yaml"))
        self.pins = dict(seed.inputs)
        self.options = dict(provider=self.provider, observed_binding=observe,
            task_pin=self.task_pin, profile_pin=self.pins["agent_profile"],
            method_pin=self.method_pin, requirement_pin=self.requirement_pin,
            supplies=(PinnedExecutionInput("bundle/supply.yaml", hash_file(self.root / "bundle/supply.yaml")),),
            conformance_refs=(PinnedExecutionInput("bundle/conformance.yaml",
                hash_file(self.root / "bundle/conformance.yaml")),),
            evidence_check=self.verify_test_evidence, data_policy_pin=self.pins["data_policy"],
            host_policy_pin=self.pins["host_policy"], timestamp=lambda: "2026-08-26T00:00:00Z",
            output_directory=PREFIX, output_contract="deterministic-check-report",
            action_ref="ES-A4@1.0.0", session_clock=lambda: 0.0)

    def verify_test_evidence(self, identity, evidence, capability):
        """Check the explicit test bytes/identity; never assert live admission."""
        pin = evidence["artifact_ref"]
        if hash_file(self.root / pin["path"]) != pin["sha256"]:
            return "fail"
        document = load_document(self.root / pin["path"])
        return "pass" if (
            document["evidence_kind"] == "local-conformance"
            and document["scope"]["scope_ref"] == "test-runtime-host"
            and document["implementation_ref"] == identity.implementation_ref
            and document["implementation_version"] == identity.implementation_version
            and capability in document["capability_ids"]
            and document["result"] == "pass"
        ) else "fail"

    def build_factory(self, **overrides):
        options = dict(self.options)
        options.update(overrides)
        return ApiRoleBindingFactory(self.root, **options)

    def invocation(self, role="main", task=None, ordinal=1, depth=0):
        return RoleInvocation(role, copy.deepcopy(self.task if task is None else task), ordinal,
            depth, {}, max_model_calls=1, max_output_tokens=128, max_seconds=60,
            max_total_tokens=1000)

    def child(self, ordinal):
        task = copy.deepcopy(self.task)
        task["task_id"] = f"FACTORY-CHILD-{ordinal}"
        task["write_scope"] = [f"{PREFIX}/child-{ordinal}/**"]
        return task


def make_factory(root, provider=None, **overrides):
    inputs = FactoryTestInputs(root, provider)
    return inputs, inputs.build_factory(**overrides)
