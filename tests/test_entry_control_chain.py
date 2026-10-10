"""Full producer-to-checkpoint integration using explicit offline port facts.

The existing fixture supplies typed local evidence and an observed local port;
this test does not establish live source/provider qualification or Human approval.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.adapters.models import ContentBlock, FinishReason, ModelResponse
from research_workbench.artifacts.integrity import hash_file
from research_workbench.entry.binding import freeze_capability_selection, freeze_execution_inputs
from research_workbench.entry.executor import FrozenRoleBinding, FrozenRoleExecutor
from research_workbench.entry.guide import build_guide_request
from research_workbench.entry.intake import compile_control_draft, persist_control_draft
from research_workbench.entry.state import publish_workflow_checkpoint
from research_workbench.entry.workflow import WorkflowBudget, run_research_workflow
from research_workbench.execution import CloseoutPin, PinnedExecutionInput, load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from research_workbench.validation.schemas import SchemaCatalog
from tests.execution_fixtures import ExecutionViewFixture, RuntimeBundleFixture, SequenceClock
from tests.test_entry_driver import ScriptedRoleProvider, observe


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "work/TASK-MR-ES-FROZEN-001"


class ControlChainProvider(ScriptedRoleProvider):
    """An actual injected offline Provider port, with observable request/usage."""
    def generate(self, request):
        response = super().generate(request)
        output = {"decision": "complete", "delegations": [],
            "summary": "The bounded contract-check execution slice produced retained Host and Trace facts.",
            "limitations": ["Offline scripted Provider; no live source qualification or whole Task completion."],
            "next_actions": ["Human review of the retained contract-check slice."]}
        return ModelResponse(response.response_id, response.provider, response.model,
            (ContentBlock("text", text=json.dumps(output)),), FinishReason.COMPLETE, usage=response.usage)


class EntryControlChainTests(unittest.TestCase):
    def test_actual_control_producers_feed_session_host_receipt_workflow_state_and_guide(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            RuntimeBundleFixture()._build_bundle(root)
            fixture_manifest = load_document(root / "bundle/manifest.yaml")
            human_task = load_document(root / "bundle/task.yaml")
            human_protocol = _protocol("JOINT-CONTROL-OFFLINE")
            human_protocol["active_modes"] = list(human_task["active_modes"])
            human_protocol["question_refs"] = list(human_task["question_refs"])
            model_proposal = {"protocol": copy.deepcopy(human_protocol), "task": copy.deepcopy(human_task),
                "method": load_document(root / "bundle/method.yaml"),
                "requirements": [load_document(root / "bundle/requirement.yaml")],
                "unknowns": ["Real source and provider admission are untested in this offline integration."]}

            draft = compile_control_draft(root, response=model_proposal,
                protocol_ceiling=human_protocol, task_ceiling=human_task,
                schema_catalog=SchemaCatalog(ROOT / "schemas"))
            published = persist_control_draft(root, directory="control/intake", draft=draft)
            refs = {Path(ref.path).name: ref for ref in published}
            self.assertEqual("draft", load_document(root / "control/intake/draft.json")["status"])
            actual_task = load_document(root / refs["task.json"].path)
            actual_method = load_document(root / refs["method.json"].path)
            self.assertEqual(refs["task.json"].sha256, actual_method["task_ref"]["sha256"])

            def pin(reference):
                return PinnedExecutionInput(reference.path, reference.sha256)

            verifier_calls = []
            def verify(identity, evidence, capability):
                reference = evidence["artifact_ref"]
                self.assertEqual(reference["sha256"], hash_file(root / reference["path"]))
                artifact = load_document(root / reference["path"])
                self.assertEqual(evidence["evidence_id"], artifact["evidence_id"])
                self.assertEqual(identity.implementation_ref, artifact["implementation_ref"])
                self.assertEqual(identity.implementation_version, artifact["implementation_version"])
                self.assertIn(capability, artifact["capability_ids"])
                self.assertEqual("local-conformance", artifact["evidence_kind"])
                self.assertEqual("live", evidence["evidence_class"])
                verifier_calls.append(reference["path"])
                return artifact["result"]

            selection = freeze_capability_selection(root, task=pin(refs["task.json"]),
                method=pin(refs["method.json"]), requirement=pin(refs["requirement-1.json"]),
                supplies=[PinnedExecutionInput("bundle/supply.yaml", hash_file(root / "bundle/supply.yaml"))],
                supporting_documents=[{"kind": "capability_conformance_evidence", "path": "bundle/conformance.yaml",
                    "sha256": hash_file(root / "bundle/conformance.yaml")}],
                evidence_check=verify, output_directory="control/selection", resolution_id="CR-CONTROL-JOINT",
                snapshot_id="RCS-CONTROL-JOINT", qualification="runtime-execution",
                evaluated_at="2026-08-26T00:00:00Z", schema_root=ROOT / "schemas")
            self.assertEqual("satisfied", selection.status)
            self.assertEqual(["bundle/conformance.yaml"], verifier_calls)

            # Closure refs come from real producer returns, not copied fixture resolution/snapshot.
            replacements = {"bundle/task.yaml": pin(refs["task.json"]),
                "bundle/method.yaml": pin(refs["method.json"]),
                "bundle/requirement.yaml": pin(refs["requirement-1.json"]),
                "bundle/resolution.yaml": selection.resolution, "bundle/snapshot.yaml": selection.snapshot}
            manifest = copy.deepcopy(fixture_manifest)
            manifest["bundle_id"] = "RB-CONTROL-JOINT"
            for reference in manifest["documents"]:
                if reference["path"] in replacements:
                    replacement = replacements[reference["path"]]
                    reference.update(path=replacement.path, sha256=replacement.sha256)
            manifest["entrypoint"].update(path=selection.snapshot.path, sha256=selection.snapshot.sha256)
            for edge in manifest["imports"]:
                for key in ("from_path", "to_path"):
                    if edge[key] in replacements:
                        edge[key] = replacements[edge[key]].path
            execution = freeze_execution_inputs(root, manifest=manifest,
                **ExecutionViewFixture()._inputs(root), output_directory="control/execution",
                execution_at="2026-08-26T00:00:00Z", view_id="VIEW-CONTROL-JOINT",
                schema_root=ROOT / "schemas")
            view = load_document(root / execution.view.path)
            self.assertEqual(refs["task.json"].path, view["task_ref"]["path"])
            self.assertEqual(selection.snapshot.path, manifest["entrypoint"]["path"])
            self.assertFalse(manifest["execution_scope"]["task_capability_closure"]["task_completion"])

            provider = ControlChainProvider()
            binding = FrozenRoleBinding(CloseoutPin(execution.bundle.path, execution.bundle.sha256),
                CloseoutPin(execution.view.path, execution.view.sha256), provider, observe,
                PREFIX + "/archive", PREFIX + "/role.json", "deterministic-check-report", "CONTROL-JOINT-001",
                schema_root=ROOT / "schemas",
                host_clock=SequenceClock("2026-08-26T00:00:01Z", "2026-08-26T00:00:02Z", "2026-08-26T00:00:03Z"),
                session_clock=lambda: 0.0)
            bound_invocations = []
            def binding_factory(invocation):
                self.assertEqual(actual_task, invocation.task)
                bound_invocations.append(invocation.role)
                return binding
            executor = FrozenRoleExecutor(root, binding_factory=binding_factory,
                accountable_owner="offline control chain test owner")
            result = run_research_workflow(root, directory=PREFIX + "/workflow", task=actual_task,
                executor=executor, budget=WorkflowBudget(3, 10000, 100, 128, 60, 3, 2))
            self.assertEqual("stage-completed", result.status, result.summary)
            self.assertEqual(["main"], bound_invocations)
            self.assertEqual(1, result.model_calls)
            self.assertEqual(38, result.known_tokens)
            self.assertEqual(0, result.held_tokens)
            self.assertEqual(1, len(provider.requests))
            self.assertEqual((), provider.requests[0].tools)
            self.assertEqual("main", provider.requests[0].metadata["entry_role"])
            executed = executor.results[0]
            self.assertIsNotNone(executed.session)
            self.assertEqual(1, executed.session.model_turns)
            self.assertEqual("completed", executed.host_report["status"])
            self.assertIsNone(executed.closeout_error)
            self.assertIsNotNone(executed.receipt_ref)
            bundle = load_runtime_bundle(execution.bundle.path, project_root=root, schema_root=ROOT / "schemas")
            validate_generic_execution_receipt(executed.receipt_ref.path, expected_sha256=executed.receipt_ref.sha256,
                bundle=bundle, schema_root=ROOT / "schemas")
            self.assertFalse(result.task_completion)
            self.assertFalse(result.human_acceptance)
            self.assertIn("stage-completed", (root / (PREFIX + "/workflow/REPORT.md")).read_text())

            state_ref = publish_workflow_checkpoint(root, result=result, protocol_ref=refs["project-protocol.json"],
                checkpoint_id="CONTROL-JOINT-STATE", output=PREFIX + "/state.json",
                write_scope=[PREFIX + "/**"], created_at="2026-10-07T00:00:00Z")
            state = load_document(root / state_ref.path)
            self.assertEqual([], state["accepted_decisions"])
            self.assertIn(refs["project-protocol.json"].path, state["project_protocol_ref"])
            self.assertIn(executed.receipt_ref.path, [ref["path"] for ref in state["machine_state_refs"]])
            before = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
            guide = build_guide_request(root, question="Explain the completed slice and pending human review.",
                main_state_ref=state_ref, model="offline-guide-model")
            self.assertEqual((), guide.tools)
            guide_inputs = json.loads(guide.messages[1].content[0].text)["approved_inputs"]
            self.assertEqual([state_ref.path], [ref["path"] for ref in guide_inputs])
            self.assertIn("Human review of the retained contract-check slice", guide_inputs[0]["text"])
            self.assertEqual(before, {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})
            self.assertEqual(1, len(provider.requests))  # Guide request construction sends nothing.


if __name__ == "__main__":
    unittest.main()
