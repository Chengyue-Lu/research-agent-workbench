"""One synthetic M5/M6 baseline fixture; no TestCase or private oracle imports."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Mapping

from research_workbench.evaluation.pins import EvaluationInputs
from research_workbench.execution.baseline_envelope import (
    compile_baseline_envelope,
    produce_a2_qualification,
)
from tests.system_evaluation_fixtures import AT, ROOT, SystemEvaluationFixture


A1 = "plain-agent"
A2 = "plain-agent-tool"


class BaselineFixture(SystemEvaluationFixture):
    """Reuse the Protocol/A2 chain, without constructing A4 or overlap cases."""

    def inputs(self) -> EvaluationInputs:
        return EvaluationInputs(self.root, ROOT / "schemas")

    def build_baseline(
        self,
        arm_id: str = A1,
        execution_binding: Mapping[str, Any] | None = None,
    ) -> "BaselineFixture":
        if not hasattr(self, "protocol"):
            self.build()
        self.arm_id = arm_id
        self.accountable_owner = "Huang Yi (synthetic baseline fixture)"
        self.task = self.doc(self.task_ref["path"])
        self.public_input_ref = self.raw("baseline/public-input.txt", "数值输入：7\n".encode("utf-8"))
        self.public_projection = {
            "task_ref": self.task_ref,
            "instruction": "Report the supplied integer value.",
            "input_refs": [self.public_input_ref],
            "required_outputs": ["plain-text-answer"],
        }
        self.public_payload_ref = self.write("baseline/public-projection.json", self.public_projection)
        self.tool_definition = {
            "name": "bounded_operation",
            "description": "Return the explicitly supplied value.",
            "input_schema": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
        }
        interface = self.doc(self.bindings[A2]["interface_ref"]["path"])
        interface["provider_visible_interface"] = copy.deepcopy(self.tool_definition)
        self.bindings[A2]["interface_ref"] = self.write("arm-1/interface.json", interface)
        for binding in self.protocol["execution_bindings"]:
            if binding["arm_id"] == A2:
                binding["interface_ref"] = copy.deepcopy(self.bindings[A2]["interface_ref"])
        manifest = self.doc(self.manifest_ref["path"])
        frozen = manifest["frozen_conditions"]
        frozen["budget"]["max_parallel"] = 1
        context_policy = self.doc(frozen["context"]["policy_ref"]["path"])
        # A fixture-chosen character limit for the existing ClientTool loop;
        # this is distinct from the Manifest's provider input-token budget.
        context_policy["context_policy"]["baseline_transport"] = {
            "max_tool_result_chars": 16000,
        }
        frozen["context"]["policy_ref"] = self.write(
            "baseline/context-policy.json", context_policy
        )
        refs = frozen["context"]["initial_context_refs"]
        for ref in (self.public_input_ref, self.public_payload_ref):
            if ref not in refs:
                refs.append(ref)
        if execution_binding is not None:
            self.protocol["execution_binding"] = copy.deepcopy(dict(execution_binding))
            frozen["model"].update(
                slot_id=execution_binding["model"]["slot"],
                model_id=execution_binding["model"]["ref"],
                provider_adapter=execution_binding["adapter"]["ref"],
            )
            frozen["host"].update(
                host_id=execution_binding["host"]["ref"],
                runtime=execution_binding["runtime"]["ref"],
            )
            pool = self.doc(frozen["model"]["pool_ref"]["path"])
            slot = pool["slots"][0]
            slot["slot_id"] = execution_binding["model"]["slot"]
            slot["provider_adapter"] = execution_binding["adapter"]["ref"]
            pool["slots"] = [slot]
            frozen["model"]["pool_ref"] = self.write("baseline/model-pool.json", pool)
        self.manifest_ref = self.write("evaluation/manifest.json", manifest)
        self.protocol["manifest_ref"] = self.manifest_ref
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        self.execution_binding = copy.deepcopy(self.protocol["execution_binding"])
        self.provider_binding = self.execution_binding["provider"]
        self.qualification_ref = None
        if arm_id == A2:
            qualification = produce_a2_qualification(
                self.inputs(),
                protocol_ref=self.protocol_ref,
                qualification_id="BASELINE-A2-QUALIFICATION",
                checked_at=AT,
                bindings=self.qualification(A2)["bindings"],
            )
            self.qualification_ref = self.write("baseline/a2-qualification.json", qualification)
        self.envelope = self.compile()
        self.envelope_ref = self.write(f"baseline/{arm_id}-envelope.json", self.envelope)
        self.tools = self.envelope["provider_visible_payload"]["tools"]
        self.tool_bindings = self.doc(self.qualification_ref["path"])["bindings"] if self.qualification_ref else []
        return self

    def compile(self, **overrides: Any) -> dict[str, Any]:
        arguments = {
            "protocol_ref": self.protocol_ref,
            "task_ref": self.task_ref,
            "public_payload_ref": self.public_payload_ref,
            "arm_id": self.arm_id,
            "envelope_id": "BASELINE-" + self.arm_id,
            "accountable_owner": self.accountable_owner,
            "qualification_ref": self.qualification_ref,
        }
        arguments.update(overrides)
        return compile_baseline_envelope(self.inputs(), **arguments)

    def freeze_public_projection(self, projection: Mapping[str, Any]) -> None:
        """Freeze a changed public declaration without replacing Task controls."""
        old_ref = self.public_payload_ref
        self.public_projection = copy.deepcopy(dict(projection))
        self.public_payload_ref = self.write("baseline/public-projection.json", projection)
        manifest = self.doc(self.manifest_ref["path"])
        refs = manifest["frozen_conditions"]["context"]["initial_context_refs"]
        refs[refs.index(old_ref)] = self.public_payload_ref
        self.manifest_ref = self.write("evaluation/manifest.json", manifest)
        self.protocol["manifest_ref"] = self.manifest_ref
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        if self.qualification_ref is not None:
            qualification = self.doc(self.qualification_ref["path"])
            qualification["protocol_ref"] = self.protocol_ref
            qualification["manifest_ref"] = self.manifest_ref
            self.qualification_ref = self.write("baseline/a2-qualification.json", qualification)


def build_baseline(
    root: Path,
    arm_id: str = A1,
    execution_binding: Mapping[str, Any] | None = None,
) -> BaselineFixture:
    return BaselineFixture(root).build_baseline(arm_id, execution_binding)
