"""Synthetic Skill consumption through the real Host and closeout pipeline."""

from __future__ import annotations

import runpy
from dataclasses import replace
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.execution import (
    CloseoutPin, SKILL_CLOSEOUT_CONTRACT, build_skill_execution_receipt,
    execute_frozen_view, load_resolved_execution_view, load_runtime_bundle,
    read_skill_execution_inputs, record_skill_execution_use, record_skill_execution_result,
)
from research_workbench.io import load_document
from research_workbench.observability.trace import AgentTraceRecorder
from tests.execution_fixtures import ExecutionViewFixture, RecordingDriver, SequenceClock, plain
from tests.skill_runtime_fixtures import SkillRuntimeBundleFixture


ROOT = Path(__file__).resolve().parents[1]


def write(root: Path, relative: str, document) -> CloseoutPin:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(plain(document), sort_keys=False), encoding="utf-8", newline="\n")
    return CloseoutPin(relative, hash_file(path))


class SkillCloseoutFixture:
    def __init__(self, root: Path, *, lifecycle="completed", drift="model", capture=True, exception=False,
                 with_tool=False):
        self.root = root
        helper_bundle = SkillRuntimeBundleFixture()
        manifest = helper_bundle._build_skill_bundle(root)
        if with_tool:
            def add_tool(projection, supply, method, manifest):
                projection["runtime_contract"]["dependencies"]["required_tools"] = ["synthetic-skill-tool"]
                supply["supply_identity"]["components"].append({
                    "component_kind": "tool", "component_ref": "synthetic-skill-tool",
                    "version": "1.0.0", "content_hash": "2" * 64,
                })
            manifest = helper_bundle._rewrite_skill_bundle(root, add_tool)
        self.bundle = load_runtime_bundle(manifest, project_root=root, schema_root=ROOT / "schemas")
        helper = ExecutionViewFixture()
        inputs = helper._inputs(root)
        binding_document = load_document(root / "view/binding.yaml")
        binding_document["selected_supply_report_ref"] = "supply-synthetic-runtime-skill@1.0.0"
        binding_pin = write(root, "view/binding.yaml", binding_document)
        from research_workbench.execution import PinnedExecutionInput
        inputs["execution_binding"] = PinnedExecutionInput(binding_pin.path, binding_pin.sha256)
        view_doc = helper._produce(root, self.bundle, inputs)
        view_pin = write(root, "view/skill.yaml", view_doc)
        self.view = load_resolved_execution_view(view_pin.path, expected_sha256=view_pin.sha256,
                                                bundle=self.bundle, schema_root=ROOT / "schemas")
        self.actual_binding = None
        actor_binding = plain(self.view.document["binding"])
        if lifecycle == "failed" and drift in {"provider", "runtime"}:
            actor_binding[drift]["ref"] = "observed-drift-" + drift
        self.supply_pin = {"path": "bundle/supply.yaml", "sha256": hash_file(root / "bundle/supply.yaml")}
        if lifecycle == "failed" and drift in {"supply", "projection", "projection-identity"}:
            supply = load_document(root / "bundle/supply.yaml")
            if drift != "projection-identity":
                supply["report_id"] = "observed-drift-supply"
            if drift in {"projection", "projection-identity"}:
                projection = load_document(root / "bundle/skill-projection.yaml")
                projection["projection_id"] = "observed-drift-projection"
                pin = write(root, "bundle/observed-projection.yaml", projection)
                supply["supply_identity"]["skill_release_projection_ref"] = {
                    "ref": "observed-drift-projection@1.0.0", "document_path": pin.path,
                    "content_hash": "sha256:" + pin.sha256,
                }
            pin = write(root, "bundle/observed-supply.yaml", supply)
            self.supply_pin = {"path": pin.path, "sha256": pin.sha256}
        task = load_document(root / "bundle/task.yaml")
        self.trace_dir = root / "closeout/trace"
        self.recorder = AgentTraceRecorder(
            self.trace_dir, task_id=task["task_id"], task_revision=task.get("revision", 1),
            attempt_id="ATTEMPT-SKILL-CLOSEOUT", task_snapshot=task,
            accountable_owner="M11 synthetic execution owner", actor_id="runtime-host",
            runtime_identity=actor_binding["runtime"]["ref"],
            provider=actor_binding["provider"]["ref"],
            read_allowlist=["bundle/**"], write_scope=["work/**", "closeout/**"],
            tool_allowlist=["synthetic-skill-tool"] if with_tool else [],
            created_at="2026-08-26T00:00:00Z",
        )
        self.view_ref = {"ref": f"{view_doc['view_id']}@r{view_doc['revision']}",
                         "path": view_pin.path, "sha256": view_pin.sha256}
        self.recorder.record_decision_snapshot("execution-scope-binding", {
            "schema_version": "0.1.0", "record_kind": "execution-scope-binding",
            "view_ref": self.view_ref, "execution_scope": plain(view_doc["execution_scope"]),
        })
        fixture = self

        class Driver(RecordingDriver):
            def execute(self, request):
                if exception:
                    raise RuntimeError("synthetic incomplete capture")
                observed = read_skill_execution_inputs(root, fixture.supply_pin, schema_root=ROOT / "schemas")
                if capture:
                    record_skill_execution_use(fixture.recorder, observed, fact_id="SKILL-USE-1",
                                               view_ref=fixture.view_ref)
                # The synthetic operation consumes the returned immutable Projection,
                # never a second path read or a planned View claim.
                self.consumed_skill = observed.projection["release"]["skill_id"]
                fixture.recorder.record("provider-request", {"input": {"skill_id": self.consumed_skill}})
                # The synthetic backend's response is the first observation of
                # binding drift; input consumption cannot predict this response.
                response_binding = plain(self.binding)
                if lifecycle == "failed" and drift in response_binding:
                    response_binding[drift]["ref"] = "observed-drift-" + drift
                fixture.recorder.record("provider-response", {
                    "status": "synthetic-completed", "observed_binding": response_binding,
                })
                fixture.actual_binding = response_binding
                if with_tool:
                    fixture.recorder.record_tool_call(operation_id="skill-tool-1", tool_name="synthetic-skill-tool",
                                                       status="completed", arguments={}, result={"synthetic": True})
                result = super().execute(request)
                record_skill_execution_result(fixture.recorder, observed, fact_id="SKILL-RESULT-1",
                    view_ref=fixture.view_ref, actual_binding=response_binding,
                    actual_supply_report_ref=observed.consumption["supply_report_ref"]["ref"])
                return replace(result, actual_binding=fixture.actual_binding,
                               provider_invocations=1,
                               actual_supply_report_ref=observed.consumption["supply_report_ref"]["ref"],
                               actual_skill_consumption=observed.consumption if capture else None)

        binding = plain(self.view.document["binding"])
        if lifecycle == "blocked":
            binding["model"]["ref"] = "preflight-mismatched-model"
        self.driver = Driver(root, binding, supply_ref=self.view.document["selected_supply_report_ref"]["ref"],
                             tool_refs=("synthetic-skill-tool",) if with_tool else ())
        self.host = execute_frozen_view(
            self.view, self.driver, report_id="HOST-SKILL-CLOSEOUT", attempt_id="ATTEMPT-SKILL-CLOSEOUT",
            clock=SequenceClock("2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z"),
            schema_root=ROOT / "schemas", closeout_contract=SKILL_CLOSEOUT_CONTRACT,
        )
        self.recorder.record_attempt_status(self.host["status"], reason="bounded synthetic execution")
        self.recorder.seal()
        self.refresh_validation()

    def refresh_validation(self):
        self.host_pin = write(self.root, "closeout/host.yaml", self.host)
        self.trace_pin = CloseoutPin("closeout/trace/INDEX.yaml", hash_file(self.trace_dir / "INDEX.yaml"))
        checker = self.root / "closeout/checker.py"
        checker.write_text(
            "import hashlib\n"
            "def check(root, subjects):\n"
            "    for subject in subjects:\n"
            "        path = (root / subject['path']).resolve()\n"
            "        if not path.is_relative_to(root) or not path.is_file():\n"
            "            return False\n"
            "        if hashlib.sha256(path.read_bytes()).hexdigest() != subject['sha256']:\n"
            "            return False\n"
            "    return True\n", encoding="utf-8", newline="\n",
        )
        subjects = [{"path": self.host_pin.path, "sha256": self.host_pin.sha256},
                    {"path": self.trace_pin.path, "sha256": self.trace_pin.sha256},
                    *[{"path": a["path"], "sha256": a["sha256"]} for a in self.host["artifacts"]]]
        checked = runpy.run_path(str(checker))["check"](self.root.resolve(), subjects)
        assert checked, "synthetic deterministic validation must actually check its subjects"
        self.validation = {
            "schema_version": "0.1.0", "report_id": "CHECK-SKILL-CLOSEOUT", "status": "pass" if checked else "fail",
            "checker": {"checker_id": "synthetic-skill-check", "version": "1.0.0",
                        "source_ref": {"path": "closeout/checker.py", "sha256": hash_file(checker)}},
            "subject_refs": subjects,
            "checks": [{"code": "execution-contract-closed", "status": "pass",
                        "detail": "Bounded synthetic Host/Trace/output subjects."}],
            "scope": "execution-contract-only", "limitations": ["Synthetic evidence only."],
        }
        self.validation_pin = write(self.root, "closeout/validation.yaml", self.validation)

    def build(self):
        return build_skill_execution_receipt(
            self.view, self.bundle, host_report=self.host_pin, trace_index=self.trace_pin,
            validations=(self.validation_pin,), receipt_id="RECEIPT-SKILL-CLOSEOUT", schema_root=ROOT / "schemas",
        )

    def receipt(self):
        return write(self.root, "closeout/receipt.yaml", self.build())
