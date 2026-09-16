"""Real local synthetic calls; no network, model weights or efficacy evidence."""

import copy
import importlib.util
from datetime import datetime

from research_workbench.adapters.models import (
    Capability, ClientTool, ContentBlock, FinishReason, ModelResponse,
    ProviderCapabilities, ToolCall, ToolDefinition, Usage,
)
from research_workbench.evaluation.harness_execution import HarnessContext, HarnessPorts
from research_workbench.evaluation.harness_runtime import persist, plain
from research_workbench.evaluation.pins import file_ref
from research_workbench.execution import (
    ExecutionDriverResult, PinnedExecutionInput, read_skill_execution_inputs, record_skill_execution_use,
    record_skill_execution_result,
)
from research_workbench.execution.baseline import observe_baseline_binding
from tests.harness_fixtures import HarnessFixture
from tests.system_evaluation_fixtures import AT, ROOT


class LocalProvider:
    def __init__(self, error=None):
        self.requests = []
        self.error = error

    def capabilities(self):
        return ProviderCapabilities(provider="harness-local", adapter_version="1.0.0",
            supported=frozenset({Capability.TEXT, Capability.TOOLS}),
            models=("harness-local",), deployment="local")

    def generate(self, request):
        self.requests.append(request)
        if self.error:
            raise self.error
        tool = bool(request.tools) and len(self.requests) == 1
        return ModelResponse(response_id="response-" + str(len(self.requests)),
            provider="harness-local", model="harness-local",
            output=() if tool else (ContentBlock("text", text="7"),),
            finish_reason=FinishReason.TOOL_CALL if tool else FinishReason.COMPLETE,
            tool_calls=(ToolCall("call-1", "bounded_operation", {"value": "7"}),) if tool else (),
            usage=Usage(input_tokens=5, output_tokens=2))


class FixedClock:
    def __init__(self, value=AT):
        self.value = value

    def now(self):
        return datetime.fromisoformat(self.value)


class LocalDriver:
    def __init__(self, view, recorder, destination, *, skill=False, lifecycle="completed", exception=False, turns=1):
        self.view, self.recorder, self.destination = view, recorder, destination
        self.skill, self.lifecycle, self.exception = skill, lifecycle, exception
        self.calls = 0
        self.turns = turns
        self.binding = plain(view.document["binding"])
        self.observed_binding = copy.deepcopy(self.binding)
        self.selected_supply_report_ref = view.document["selected_supply_report_ref"]["ref"]
        if lifecycle == "blocked":
            self.binding["model"]["ref"] = "wrong-local-model"

    def execute(self, request):
        self.calls += 1
        if self.exception:
            raise RuntimeError("synthetic capture interruption")
        root = self.view.project_root
        view_ref = {"ref": f"{request.view['view_id']}@r{request.view['revision']}",
                    "path": self.view.view_path.relative_to(root).as_posix(), "sha256": self.view.view_sha256}
        observed = None
        if self.skill:
            snapshot = request.bundle_documents[self.view.runtime_bundle.entrypoint_path]
            observed = read_skill_execution_inputs(root, file_ref(snapshot["selected_supply_report_ref"]),
                                                    schema_root=ROOT / "schemas")
            record_skill_execution_use(self.recorder, observed, fact_id="use-1", view_ref=view_ref)
        output = {"status": "bounded", "skill": observed.projection["release"]["skill_id"] if observed else None}
        for _ in range(self.turns):
            self.recorder.record("provider-request", {"input": "synthetic bounded contract check"})
            self.recorder.record("provider-response", {"output": output, "binding": self.observed_binding})
        artifact = persist(root, self.destination / "output.json", output)
        if self.skill:
            record_skill_execution_result(self.recorder, observed, fact_id="result-1", view_ref=view_ref,
                actual_binding=self.observed_binding, actual_supply_report_ref=self.selected_supply_report_ref)
        else:
            self.recorder.record_execution_fact(fact_id="result-1", view_ref=view_ref,
                actual_binding=self.observed_binding, actual_supply_report_ref=self.selected_supply_report_ref)
        return ExecutionDriverResult(status=self.lifecycle, actual_binding=self.observed_binding,
            actual_supply_report_ref=self.selected_supply_report_ref, turns=self.turns, output_tokens=2 * self.turns,
            provider_invocations=self.turns, elapsed_seconds=0,
            artifacts=tuple({"contract": contract, **artifact} for contract in request.view["required_outputs"]),
            actual_skill_consumption=observed.consumption if observed else None)


class ExecutionFixture(HarnessFixture):
    def shared_view_inputs(self, view_inputs, prefix):
        inputs = super().shared_view_inputs(view_inputs, prefix)
        profile = self.doc(inputs["agent_profile"].path)
        profile["model_policy"]["class"] = "provider-reported"
        profile["model_policy"]["required_capabilities"] = ["text"]
        ref = self.write(inputs["agent_profile"].path, profile)
        inputs["agent_profile"] = PinnedExecutionInput(**ref)
        return inputs

    def build_execution(self):
        observed = observe_baseline_binding(LocalProvider(), model="harness-local", model_slot="primary")
        self.build_harness(execution_binding=observed, compact=True)
        self.preflight_ref = self.write("harness/preflight.json", self.preflight())
        self.context = HarnessContext(expected_plan_ref=self.plan_ref, expected_preflight_ref=self.preflight_ref,
            expected_preflight_checked_at=AT, **self.plan_context())
        return self

    def ports(self, *, provider_errors=(), lifecycle="completed", exception=False, turns=1, later_blocked=False):
        errors = list(provider_errors)
        self.providers, self.drivers = [], []

        def provider():
            item = LocalProvider(errors.pop(0) if errors else None)
            self.providers.append(item)
            return item

        def driver(view, recorder, destination, skill=False):
            state = "blocked" if later_blocked and self.drivers else lifecycle
            item = LocalDriver(view, recorder, destination, skill=skill, lifecycle=state, exception=exception, turns=turns)
            self.drivers.append(item)
            return item

        source = self.root / self.bindings["plain-agent-tool"]["implementation_ref"]["path"]
        spec = importlib.util.spec_from_file_location("harness_qualified_tool", source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tool = ClientTool(ToolDefinition(**self.tool_definition), module.bounded_operation)
        return HarnessPorts(provider, (tool,), driver,
                            lambda view, recorder, destination: driver(view, recorder, destination, True))
