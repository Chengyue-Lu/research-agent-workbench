"""Human obligations survive actual intake and package caller consumption.

All Providers and qualification inputs are explicitly offline test ports. These
checks establish engineering boundaries, not live/Skill/Human acceptance.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from research_workbench.adapters.models import ContentBlock, FinishReason, ModelResponse
from research_workbench.entry.caller import run_frozen_intake_workflow
from research_workbench.entry.handoff import consume_compact_handoff, workflow_handoff_observation
from research_workbench.entry.intake import compile_control_draft
from research_workbench.entry.intake_call import IntakeCallBudget, call_intake
from research_workbench.entry.roles import EntryInputError
from research_workbench.entry.workflow import WorkflowBudget
from research_workbench.execution import PinnedExecutionInput, load_runtime_bundle, validate_generic_execution_receipt
from research_workbench.io import load_document
from research_workbench.scaffold import _protocol
from tests.entry_chain_support import PREFIX
from tests.entry_factory_support import FactoryTestInputs
from tests.test_entry_caller import CallerRoleProvider
from tests.test_entry_driver import ScriptedRoleProvider
from tests.test_entry_intake import control_documents


class ConstraintProposalProvider(ScriptedRoleProvider):
    def __init__(self, edit):
        super().__init__()
        self.edit = edit

    def generate(self, request):
        base = super().generate(request)
        payload = json.loads(request.messages[1].content[0].text)["caller_context"]
        proposal = copy.deepcopy(payload["control_ceilings"])
        proposal.update(method=payload["context"]["approved_method"],
                        requirements=payload["context"]["requirements"],
                        unknowns=["Offline structural test; human acceptance remains separate."])
        self.edit(proposal["task"])
        return ModelResponse(base.response_id, base.provider, base.model,
            (ContentBlock("text", text=json.dumps(proposal)),), FinishReason.COMPLETE, usage=base.usage)


class EntryIntakeConstraintTests(unittest.TestCase):
    def test_handoff_defaults_cannot_be_weakened_by_explicit_sampling(self):
        with tempfile.TemporaryDirectory() as temporary:
            protocol, task = control_documents()
            proposal = {"protocol": copy.deepcopy(protocol), "task": copy.deepcopy(task), "unknowns": []}
            proposal["task"]["handoff_policy"] = {
                "require_transfer_manifest": False, "semantic_review": "risk-triggered",
                "minimum_semantic_samples": 0}
            with self.assertRaisesRegex(EntryInputError, "weakens human handoff_policy"):
                compile_control_draft(Path(temporary), response=proposal,
                                      protocol_ceiling=protocol, task_ceiling=task)
            proposal["task"]["handoff_policy"]["minimum_semantic_samples"] = 1
            draft = compile_control_draft(Path(temporary), response=proposal,
                                          protocol_ceiling=protocol, task_ceiling=task)
            self.assertEqual(1, draft.task["handoff_policy"]["minimum_semantic_samples"])

    def prepare(self, root, *, edit=lambda task: None, human_edit=lambda task: None):
        provider = CallerRoleProvider()
        inputs = FactoryTestInputs(root, provider)
        human_task = copy.deepcopy(inputs.task)
        human_task["budget"] = {"max_turns": 2, "max_output_tokens": 128, "max_seconds": 60}
        human_task["delegation"]["sub_budget"] = {
            "max_turns": 1, "max_output_tokens": 64, "max_seconds": 30}
        human_edit(human_task)
        protocol = _protocol("OFFLINE-INTAKE-CONSTRAINTS")
        protocol["active_modes"] = human_task["active_modes"]
        protocol["question_refs"] = human_task["question_refs"]
        protocol["budgets"].update(max_parallel_subagents=3, max_delegation_depth=2)
        # The compiler's future execution Task is distinct from the authorized
        # intake-role Task. An unsupported future Skill/H2 obligation never
        # becomes an obligation for the parser's own model request.
        intake_provider = ConstraintProposalProvider(edit)
        intake = call_intake(root, intake_task=inputs.task,
            intake_profile=load_document(root / inputs.options["profile_pin"].path),
            protocol_ceiling=protocol, task_ceiling=human_task, provider=intake_provider,
            model="bounded-local-model", directory=PREFIX + "/intake",
            budget=IntakeCallBudget(100, 128, 10000, 60),
            context={"approved_method": inputs.method, "requirements": [inputs.requirement]},
            clock=lambda: 0.0)
        refs = {Path(ref.path).name: ref for ref in intake.draft_refs}
        options = {}
        for name, keyword in (("task.json", "task_pin"), ("method.json", "method_pin"),
                              ("requirement-1.json", "requirement_pin")):
            if name in refs:
                options[keyword] = PinnedExecutionInput(refs[name].path, refs[name].sha256)
        factory = inputs.build_factory(**options)
        provider.task = copy.deepcopy(factory.root_task)
        return human_task, intake, factory, provider, intake_provider

    def run_caller(self, root, intake, factory):
        return run_frozen_intake_workflow(root, intake_result=intake, binding_factory=factory,
            directory=PREFIX + "/workflow", budget=WorkflowBudget(8, 10000, 100, 512, 120, 3, 2),
            accountable_owner="offline intake constraint test", deadline_monotonic=120,
            clock=lambda: 0.0)

    def assert_rejected_before_roles(self, root, intake, factory, provider, detail):
        self.assertEqual("rejected", intake.status, intake.details)
        self.assertEqual("INTAKE-COMPILER-REJECTED", intake.reason)
        self.assertIn(detail, intake.details["detail"])
        self.assertEqual(1, intake.model_calls)
        self.assertEqual((30, 8, 0), (intake.input_tokens, intake.output_tokens, intake.held_tokens))
        self.assertEqual((), intake.draft_refs)
        self.assertTrue((root / (PREFIX + "/intake/response.json")).is_file())
        self.assertFalse((root / (PREFIX + "/intake/draft")).exists())
        result = self.run_caller(root, intake, factory)
        self.assertIsNone(result.workflow, result.reason)
        self.assertEqual([], provider.requests)
        self.assertEqual((), factory.record_refs)
        self.assertTrue(result.intake_report_verified)
        self.assertIsNone(result.handoff_ref)
        self.assertFalse((root / (PREFIX + "/workflow")).exists())

    def test_each_human_budget_omission_rejects_actual_intake_and_dispatch(self):
        for field in ("max_turns", "max_output_tokens", "max_seconds"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, intake, factory, provider, _ = self.prepare(root,
                    edit=lambda task, field=field: task["budget"].pop(field))
                self.assert_rejected_before_roles(root, intake, factory, provider,
                                                  "draft removes budget " + field)

    def test_each_child_budget_and_whole_sub_budget_omission_reject_before_roles(self):
        for field in ("max_turns", "max_output_tokens", "max_seconds", "whole"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                def edit(task):
                    if field == "whole":
                        task["delegation"].pop("sub_budget")
                    else:
                        task["delegation"]["sub_budget"].pop(field)
                _, intake, factory, provider, _ = self.prepare(root, edit=edit)
                self.assert_rejected_before_roles(root, intake, factory, provider,
                                                  "draft removes child sub-budget")

    def test_disabled_delegation_cannot_erase_supplied_child_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def edit(task):
                task["delegation"] = {"allowed": False, "max_depth": 0, "max_parallel": 0}
            _, intake, factory, provider, _ = self.prepare(root, edit=edit)
            self.assert_rejected_before_roles(root, intake, factory, provider,
                                              "draft removes child sub-budget")

    def test_equal_or_narrower_limits_reach_host_receipt_and_formal_handoff(self):
        for narrowed in (False, True):
            with self.subTest(narrowed=narrowed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                def edit(task):
                    if narrowed:
                        task["budget"] = {"max_turns": 1, "max_output_tokens": 64, "max_seconds": 30}
                        task["delegation"]["sub_budget"] = {
                            "max_turns": 1, "max_output_tokens": 32, "max_seconds": 15}
                human_task, intake, factory, provider, _ = self.prepare(root, edit=edit)
                self.assertEqual("success", intake.status, intake.details)
                expected = copy.deepcopy(human_task)
                edit(expected)
                self.assertEqual(expected, factory.root_task)
                result = self.run_caller(root, intake, factory)
                self.assertIsNotNone(result.workflow, result.reason)
                self.assertEqual("stage-completed", result.workflow.status, result.workflow.summary)
                self.assertEqual(1, len(provider.requests))
                self.assertEqual(expected["budget"]["max_output_tokens"], provider.requests[0].max_output_tokens)
                self.assertEqual(2, result.workflow.model_calls)
                self.assertEqual(76, result.workflow.known_tokens)
                self.assertEqual(0, result.workflow.held_tokens)
                self.assertIsNotNone(result.handoff_ref, result.reason)
                report = load_document(root / result.workflow.report_ref["path"])
                self.assertEqual(expected, report["task"])
                for record in factory.records:
                    receipt = next(item for item in result.workflow.observations
                        if item["ordinal"] == record["ordinal"])["receipt_refs"][0]
                    bundle = load_runtime_bundle(record["bundle"]["path"], project_root=root)
                    checked = validate_generic_execution_receipt(receipt["path"],
                        expected_sha256=receipt["sha256"], bundle=bundle)
                    self.assertFalse(checked.document["boundaries"]["task_completion"])
                observation = workflow_handoff_observation(report, root)
                observation["artifact_refs"].append(dict(result.workflow.report_ref))
                consumed = consume_compact_handoff(root, result.handoff_ref,
                    expected_task=expected, expected_attempt_id=report["attempt_id"],
                    expected_observation=observation)
                self.assertFalse(consumed["human_acceptance"])

    def test_removing_mandatory_skill_never_publishes_weakened_task(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, provider, _ = self.prepare(root,
                human_edit=lambda task: task.update(required_skills=["required-method@1.0.0"]),
                edit=lambda task: task.update(required_skills=[]))
            self.assert_rejected_before_roles(root, intake, factory, provider,
                                              "draft removes required human Skills")

    def test_preserved_mandatory_skill_stops_unsupported_caller_before_roles(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, intake, factory, provider, _ = self.prepare(root,
                human_edit=lambda task: task.update(required_skills=["required-method@1.0.0"]))
            self.assertEqual("success", intake.status, intake.details)
            self.assertEqual(["required-method@1.0.0"], factory.root_task["required_skills"])
            with self.assertRaisesRegex(ValueError, "Skill"):
                self.run_caller(root, intake, factory)
            self.assertEqual([], provider.requests)
            self.assertEqual((), factory.record_refs)
            self.assertFalse((root / (PREFIX + "/workflow")).exists())

    def test_handoff_policy_omission_or_weakening_never_dispatches_roles(self):
        policy = {"require_transfer_manifest": True, "semantic_review": "required",
                  "minimum_semantic_samples": 3}
        for field in ("whole", "require_transfer_manifest", "semantic_review", "minimum_semantic_samples",
                      "missing-semantic-field"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                def edit(task):
                    if field == "whole":
                        task.pop("handoff_policy")
                    elif field == "missing-semantic-field":
                        task["handoff_policy"].pop("semantic_review")
                    else:
                        task["handoff_policy"][field] = {
                            "require_transfer_manifest": False, "semantic_review": "risk-triggered",
                            "minimum_semantic_samples": 2}[field]
                _, intake, factory, provider, _ = self.prepare(root, edit=edit,
                    human_edit=lambda task: task.update(handoff_policy=copy.deepcopy(policy)))
                self.assert_rejected_before_roles(root, intake, factory, provider,
                    "invalid task_packet" if field == "missing-semantic-field" else "handoff_policy")

    def test_preserved_h2_task_blocks_before_actual_role_execution(self):
        for policy in (
            {"require_transfer_manifest": True, "semantic_review": "risk-triggered", "minimum_semantic_samples": 1},
            {"require_transfer_manifest": False, "semantic_review": "required", "minimum_semantic_samples": 1},
        ):
            with self.subTest(policy=policy), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                _, intake, factory, provider, _ = self.prepare(root,
                    human_edit=lambda task: task.update(handoff_policy=copy.deepcopy(policy)))
                self.assertEqual("success", intake.status, intake.details)
                self.assertEqual(policy, factory.root_task["handoff_policy"])
                with self.assertRaisesRegex(ValueError, "HANDOFF-TRANSFER-AUDIT-REQUIRED"):
                    self.run_caller(root, intake, factory)
                self.assertEqual([], provider.requests)
                self.assertEqual((), factory.record_refs)
                self.assertFalse((root / (PREFIX + "/workflow")).exists())

    def test_compact_policy_can_strengthen_sampling_without_erasing_obligations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = {"require_transfer_manifest": False, "semantic_review": "risk-triggered",
                      "minimum_semantic_samples": 2}
            _, intake, factory, provider, _ = self.prepare(root,
                human_edit=lambda task: task.update(handoff_policy=copy.deepcopy(policy)),
                edit=lambda task: task["handoff_policy"].update(minimum_semantic_samples=3))
            self.assertEqual("success", intake.status, intake.details)
            self.assertEqual(3, factory.root_task["handoff_policy"]["minimum_semantic_samples"])
            result = self.run_caller(root, intake, factory)
            self.assertEqual("stage-completed", result.workflow.status, result.reason)
            self.assertEqual(1, len(provider.requests))
            self.assertIsNotNone(result.handoff_ref)


if __name__ == "__main__":
    unittest.main()
