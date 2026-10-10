"""Application lifecycle checks; ScriptedExecutor is explicitly offline evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.entry.workflow import RoleObservation, WorkflowBudget, run_research_workflow


def task(identifier="MAIN"):
    source = Path(__file__).parents[1]/"examples/quickstart/task-no-skill.yaml"
    value = yaml.safe_load(source.read_bytes())
    value.update(task_id=identifier, write_scope=["work/**"])
    value["permissions"]["allowed_roots"] = ["work"]
    value["budget"] = {"max_turns": 4, "max_output_tokens": 600, "max_seconds": 60}
    value["delegation"] = {"allowed": True, "max_depth": 2, "max_parallel": 1}
    return value


def child(identifier):
    value = task(identifier)
    value["write_scope"] = [f"work/{identifier}/**"]
    value["permissions"]["allowed_roots"] = [f"work/{identifier}"]
    value["delegation"] = {"allowed": False, "max_depth": 0, "max_parallel": 0}
    return value


def output(decision="complete", children=(), summary="bounded output", next_actions=None):
    return json.dumps({"decision": decision, "delegations": [{"task": item} for item in children],
                       "summary": summary, "limitations": [], "next_actions": next_actions or ["Human review."]})


class ScriptedExecutor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.invocations = []

    def __call__(self, invocation):
        self.invocations.append(invocation)
        item = next(self.responses)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, RoleObservation):
            return item
        return RoleObservation("completed", item, 1, 20, 15)


class EntryWorkflowTests(unittest.TestCase):
    def budget(self, **changes):
        data = dict(max_model_calls=12, max_total_tokens=10000, input_reservation_per_call=100,
                    max_output_tokens_per_call=100, max_seconds=60, max_children_per_task=4, max_depth=2)
        return WorkflowBudget(**dict(data, **changes))

    def run_case(self, executor, *, main=None, budget=None, **kwargs):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_research_workflow(root, directory="work/workflow", task=main or task(),
                executor=executor, budget=budget or self.budget(), **kwargs)
            records = [json.loads(i) for i in (root/"work/workflow/events.jsonl").read_text().splitlines()]
            report = (root/"work/workflow/REPORT.md").read_text()
            return result, records, report

    def test_main_decides_zero_or_variable_children_and_consumes_real_results(self):
        for count in (0, 1, 3):
            with self.subTest(count=count):
                scripts = [output()] if not count else [output("delegate", [child(f"C{i}") for i in range(count)])]
                if count:
                    scripts += [output(summary=f"result {i}") for i in range(count)]+[output(summary="main consumed children")]
                executor = ScriptedExecutor(scripts)
                result, records, readable = self.run_case(executor)
                self.assertEqual("stage-completed", result.status)
                self.assertEqual(1 if not count else count+2, result.model_calls)
                self.assertFalse(result.task_completion)
                self.assertFalse(result.human_acceptance)
                self.assertIn("Actual model calls", readable)
                if count:
                    consumed = executor.invocations[-1].context["child_results"]
                    self.assertEqual([f"result {i}" for i in range(count)], [i["summary"] for i in consumed])
                    self.assertEqual("consume-child-results", executor.invocations[-1].context["phase"])
                    self.assertIn("child-results-consumed", [i["kind"] for i in records])
                    self.assertIn("handoff-produced-and-validated", [i["kind"] for i in records])
                    for actual in consumed:
                        self.assertEqual(actual["task_id"], actual["handoff"]["task_id"])
                        self.assertEqual(actual["summary"], actual["handoff"]["result"]["summary"])
                        self.assertEqual([], actual["handoff"]["skill_lock"])
                        self.assertIn("producer_ref", actual["handoff"])

    def test_overwide_child_and_write_collision_block_whole_wave_before_child_calls(self):
        cases = []
        too_wide = child("wide")
        too_wide["write_scope"] = ["other/**"]
        cases.append([too_wide])
        duplicate_scope = child("B")
        duplicate_scope["write_scope"] = ["work/A/**"]
        cases.append([child("A"), duplicate_scope])
        for children in cases:
            executor = ScriptedExecutor([output("delegate", children)])
            result, _, _ = self.run_case(executor)
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(1, len(executor.invocations))

    def test_canonical_network_permissions_allow_narrowing_and_block_expansion(self):
        for network, expected in (("none", "stage-completed"),
                                  ("search-and-fetch", "stage-completed"),
                                  ("allowed", "safe-paused")):
            with self.subTest(network=network):
                parent = task()
                parent["permissions"]["network"] = "search-and-fetch"
                proposed = child("CANONICAL-NETWORK")
                proposed["permissions"]["network"] = network
                executor = ScriptedExecutor([output("delegate", [proposed]), output(), output()])
                result, _, _ = self.run_case(executor, main=parent)
                self.assertEqual(expected, result.status, result.summary)
                self.assertEqual(3 if expected == "stage-completed" else 1, len(executor.invocations))

    def test_child_input_permission_and_depth_expansion_are_rejected(self):
        for field in ("input", "permission", "depth", "mode", "budget"):
            item = child("C")
            if field == "input":
                item["input_refs"] = [{"path": "private.txt", "sha256": "a"*64}]
            elif field == "permission":
                item["permissions"]["network"] = "allowed"
            elif field == "depth":
                item["delegation"] = {"allowed": True, "max_depth": 2, "max_parallel": 1}
            elif field == "mode":
                item["active_modes"] = ["invented-mode@0.1.0"]
            else:
                item["budget"]["max_seconds"] = 90
            result, _, _ = self.run_case(ScriptedExecutor([output("delegate", [item])]))
            self.assertEqual("safe-paused", result.status, field)
            self.assertEqual(1, result.model_calls)

    def test_unknown_usage_and_executor_exception_preserve_hold_and_stop(self):
        for observed in (RoleObservation("completed", output(), 1, None, 10), RuntimeError("secret excluded")):
            executor = ScriptedExecutor([observed])
            result, records, _ = self.run_case(executor)
            self.assertEqual("safe-paused", result.status)
            self.assertEqual(200, result.held_tokens)
            self.assertEqual(1, len(executor.invocations))
            self.assertNotIn("secret excluded", json.dumps(records))

    def test_prior_intake_usage_consumes_same_budget(self):
        executor = ScriptedExecutor([output()])
        prior = RoleObservation("completed", "intake", 2, 50, 40)
        result, _, _ = self.run_case(executor, budget=self.budget(max_model_calls=2), prior_usage=(prior,))
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(90, result.known_tokens)
        self.assertEqual([], executor.invocations)

    def test_task_budget_does_not_reset_for_main_result_consumption(self):
        parent = task()
        parent["budget"]["max_turns"] = 1
        only_child = child("C")
        only_child["budget"]["max_turns"] = 1
        executor = ScriptedExecutor([output("delegate", [only_child]), output()])
        result, _, _ = self.run_case(executor, main=parent)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(2, result.model_calls)
        self.assertIn("turn budget exhausted", result.summary)

    def test_failed_child_keeps_unstarted_siblings_and_no_retry(self):
        executor = ScriptedExecutor([output("delegate", [child("C1"), child("C2")]),
                                    RoleObservation("failed", "failed actual call", 1, 9, 1)])
        result, _, _ = self.run_case(executor)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("C2",), result.unstarted_tasks)
        self.assertEqual(2, result.model_calls)

    def test_cancel_before_dispatch_and_deadline_after_call(self):
        executor = ScriptedExecutor([])
        result, _, _ = self.run_case(executor, cancel_requested=lambda: True)
        self.assertEqual(0, result.model_calls)
        self.assertEqual("safe-paused", result.status)
        ticks = iter([0, 0, 0, 0, 70])
        result, _, _ = self.run_case(ScriptedExecutor([output()]), clock=lambda: next(ticks))
        self.assertEqual("safe-paused", result.status)

    def test_plain_directory_scope_anchor_is_compatible_without_similar_prefix_expansion(self):
        from research_workbench.entry.workflow import _scope_within
        parent = task()
        parent["write_scope"] = ["work"]
        result, _, _ = self.run_case(ScriptedExecutor([output()]), main=parent)
        self.assertEqual("stage-completed", result.status)
        self.assertTrue(_scope_within("work/task/run/**", "work/task"))
        self.assertFalse(_scope_within("work/task-other/run/**", "work/task"))
        parent["write_scope"] = ["work/flow"]
        with self.assertRaisesRegex(ValueError, "write scope"):
            self.run_case(ScriptedExecutor([]), main=parent)

    def test_actual_output_over_dispatch_and_node_budget_stops_before_control_parse(self):
        parent = task()
        parent["budget"]["max_output_tokens"] = 10
        observed = RoleObservation("completed", output(), 1, 20, 15)
        executor = ScriptedExecutor([observed])
        result, records, _ = self.run_case(executor, main=parent)
        self.assertEqual(10, executor.invocations[0].max_output_tokens)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(35, result.known_tokens)
        self.assertEqual(15, result.observations[0]["output_tokens"])
        self.assertIn("output token cap", result.summary)
        self.assertEqual(1, len(executor.invocations))
        self.assertIn("role-finished", [record["kind"] for record in records])

    def test_node_actual_elapsed_exceeds_task_but_not_workflow_deadline(self):
        parent = task()
        parent["budget"]["max_seconds"] = 10
        ticks = [0]
        def execute(invocation):
            ticks[0] = 20
            return RoleObservation("completed", output(), 1, 20, 15)
        result, _, _ = self.run_case(execute, main=parent, clock=lambda: ticks[0])
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(35, result.known_tokens)
        self.assertEqual(1, result.model_calls)
        self.assertIn("role Task deadline", result.summary)

    def test_final_node_turn_overrun_retains_usage_and_stops(self):
        parent = task()
        parent["budget"]["max_turns"] = 1
        result, _, _ = self.run_case(ScriptedExecutor([
            RoleObservation("completed", output(), 2, 20, 15)]), main=parent)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(35, result.known_tokens)
        self.assertIn("Task turn budget", result.summary)

    def test_recursive_dynamic_delegation_uses_configured_depth(self):
        level1 = child("C1")
        level1["delegation"] = {"allowed": True, "max_depth": 1, "max_parallel": 1}
        level2 = child("C2")
        level2["write_scope"] = ["work/C1/C2/**"]
        level2["permissions"]["allowed_roots"] = ["work/C1/C2"]
        executor = ScriptedExecutor([output("delegate", [level1]), output("delegate", [level2]),
                                    output(), output(), output()])
        result, _, _ = self.run_case(executor)
        self.assertEqual("stage-completed", result.status)
        self.assertEqual([0, 1, 2, 1, 0], [i.depth for i in executor.invocations])


if __name__ == "__main__":
    unittest.main()
