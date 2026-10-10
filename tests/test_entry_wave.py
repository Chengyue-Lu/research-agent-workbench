"""Offline workflow boundary regressions; these callbacks are not live evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.entry.workflow import RoleObservation, WorkflowBudget, run_research_workflow


def main_task():
    path = Path(__file__).parents[1] / "examples/quickstart/task-no-skill.yaml"
    value = yaml.safe_load(path.read_bytes())
    value.update(task_id="MAIN", write_scope=["work/**"])
    value["permissions"]["allowed_roots"] = ["work"]
    value["budget"] = {"max_turns": 8, "max_output_tokens": 800, "max_seconds": 60}
    value["delegation"] = {"allowed": True, "max_depth": 2, "max_parallel": 3}
    return value


def child_task(identifier, *, parent=None, delegating=False):
    value = copy.deepcopy(main_task() if parent is None else parent)
    parent_scope = "work" if parent is None else parent["write_scope"][0].removesuffix("/**")
    scope = parent_scope + "/" + identifier
    value.update(task_id=identifier, write_scope=[scope + "/**"])
    value["permissions"]["allowed_roots"] = [scope]
    value["delegation"] = {"allowed": delegating, "max_depth": 1 if delegating else 0,
                           "max_parallel": 3 if delegating else 0}
    return value


def control(children=(), *, summary="bounded offline observation"):
    return json.dumps({"decision": "delegate" if children else "complete",
        "delegations": [{"task": item} for item in children], "summary": summary,
        "limitations": [], "next_actions": ["Human review."]})


class OfflineExecutor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.invocations = []

    def __call__(self, invocation):
        self.invocations.append(invocation)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(invocation)
        if isinstance(response, RoleObservation):
            return response
        return RoleObservation("completed", response, 1, 20, 15)


class EntryWaveTests(unittest.TestCase):
    def budget(self, **changes):
        values = dict(max_model_calls=16, max_total_tokens=10000, input_reservation_per_call=100,
                      max_output_tokens_per_call=100, max_seconds=60,
                      max_children_per_task=8, max_depth=2)
        return WorkflowBudget(**dict(values, **changes))

    def run_case(self, executor, *, task=None, budget=None, **options):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = run_research_workflow(root, directory="work/workflow", task=task or main_task(),
                executor=executor, budget=budget or self.budget(), **options)
            journal = [json.loads(line) for line in (root / "work/workflow/events.jsonl").read_text().splitlines()]
            report = json.loads((root / result.report_ref["path"]).read_text())
            return result, journal, report

    def assert_refusal(self, result, executor, children, *, calls=1, known=35):
        self.assertEqual("safe-paused", result.status, result.summary)
        self.assertEqual(calls, result.model_calls)
        self.assertEqual(known, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertEqual(tuple(item["task_id"] for item in children), result.unstarted_tasks)
        self.assertEqual(["MAIN"], [item.task["task_id"] for item in executor.invocations])

    def nested_tasks(self):
        first = child_task("A", delegating=True)
        sibling = child_task("B")
        grandchild = child_task("G", parent=first)
        return first, sibling, grandchild

    def test_zero_and_variable_children_keep_normal_formal_handoff_consumption(self):
        for count in (0, 1, 3):
            with self.subTest(count=count):
                children = [child_task("C" + str(index)) for index in range(count)]
                responses = [control(children)]
                if children:
                    responses += [control(summary=item["task_id"]) for item in children] + [control()]
                executor = OfflineExecutor(responses)
                result, journal, report = self.run_case(executor)
                self.assertEqual("stage-completed", result.status, result.summary)
                self.assertEqual(1 if count == 0 else count + 2, result.model_calls)
                self.assertEqual(0, result.held_tokens)
                self.assertEqual((), result.unstarted_tasks)
                self.assertFalse(result.task_completion)
                self.assertFalse(result.human_acceptance)
                self.assertEqual(count, len(report["handoff_consumptions"]))
                if count:
                    consumed = executor.invocations[-1].context["child_results"]
                    self.assertEqual("consume-child-results", executor.invocations[-1].context["phase"])
                    self.assertEqual([item["task_id"] for item in children], [item["task_id"] for item in consumed])
                    self.assertTrue(all(item["handoff"]["task_id"] == item["task_id"] for item in consumed))
                    proposed = next(item for item in journal if item["kind"] == "delegation-proposed")
                    self.assertTrue(proposed["admitted"])
                    self.assertEqual(count + 1, proposed["reserved_model_calls"])

    def test_exhausted_parent_turns_refuse_every_child_and_keep_prior_actual_usage(self):
        parent = main_task()
        parent["budget"]["max_turns"] = 1
        children = [child_task(identifier, parent=parent) for identifier in ("A", "B")]
        executor = OfflineExecutor([control(children)])
        prior = RoleObservation("completed", "prior intake", 2, 30, 10)
        result, journal, _ = self.run_case(executor, task=parent, prior_usage=(prior,))
        self.assert_refusal(result, executor, children, calls=3, known=75)
        self.assertIn("turn budget exhausted", result.summary)
        self.assertFalse(next(item for item in journal if item["kind"] == "delegation-proposed")["admitted"])

    def test_exhausted_parent_output_refuses_children_before_any_child_session(self):
        parent = main_task()
        parent["budget"]["max_output_tokens"] = 15
        children = [child_task(identifier, parent=parent) for identifier in ("A", "B")]
        executor = OfflineExecutor([control(children)])
        result, _, _ = self.run_case(executor, task=parent)
        self.assert_refusal(result, executor, children)
        self.assertIn("output budget exhausted", result.summary)

    def test_global_call_shortage_accounts_intake_and_refuses_whole_wave(self):
        children = [child_task("A"), child_task("B")]
        executor = OfflineExecutor([control(children)])
        prior = RoleObservation("completed", "prior intake", 2, 30, 10)
        result, _, _ = self.run_case(executor, budget=self.budget(max_model_calls=4), prior_usage=(prior,))
        self.assert_refusal(result, executor, children, calls=3, known=75)
        self.assertIn("wave call reservation", result.summary)

    def test_global_token_shortage_cannot_start_the_individually_affordable_first_child(self):
        children = [child_task("A"), child_task("B")]
        executor = OfflineExecutor([control(children)])
        result, _, _ = self.run_case(executor, budget=self.budget(max_total_tokens=500))
        self.assert_refusal(result, executor, children)
        self.assertIn("wave token reservation", result.summary)

    def test_admission_reserves_first_sessions_rather_than_entire_task_maxima(self):
        parent = main_task()
        parent["budget"].update(max_turns=50, max_output_tokens=20000)
        children = [child_task(identifier, parent=parent) for identifier in ("A", "B")]
        executor = OfflineExecutor([control(children), control(), control(), control()])
        result, _, _ = self.run_case(executor, task=parent,
            budget=self.budget(max_model_calls=4, max_total_tokens=1000))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual(4, result.model_calls)
        self.assertEqual([1] * 4, [item.max_model_calls for item in executor.invocations])
        self.assertEqual([200] * 4, [item.max_total_tokens for item in executor.invocations])

    def test_invalid_later_child_refuses_all_proposed_children_before_first_dispatch(self):
        first, invalid = child_task("A"), child_task("B")
        invalid["write_scope"] = ["other/**"]
        children = [first, invalid]
        executor = OfflineExecutor([control(children)])
        result, journal, _ = self.run_case(executor)
        self.assert_refusal(result, executor, children)
        self.assertIn("child write scope", result.summary)
        self.assertFalse(next(item for item in journal if item["kind"] == "delegation-proposed")["admitted"])

    def test_completed_wave_releases_reservations_before_a_new_main_proposal(self):
        first, second = child_task("A"), child_task("B")
        executor = OfflineExecutor([control([first]), control(), control([second]), control(), control()])
        result, journal, _ = self.run_case(executor,
            budget=self.budget(max_model_calls=5, max_total_tokens=505))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual(5, result.model_calls)
        self.assertEqual(175, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertEqual(["A", "B"], [item["task_id"] for item in executor.invocations[-1].context["child_results"]])
        self.assertEqual([0, 0], [item["ancestor_and_sibling_model_calls"] for item in journal
            if item["kind"] == "delegation-proposed"])

    def test_nested_wave_preserves_outer_sibling_and_both_parent_consumers(self):
        first, sibling, grandchild = self.nested_tasks()
        executor = OfflineExecutor([control([first, sibling]), control([grandchild]),
                                    control(), control(), control(), control()])
        result, journal, report = self.run_case(executor,
            budget=self.budget(max_model_calls=6, max_total_tokens=900))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual(["MAIN", "A", "G", "A", "B", "MAIN"],
                         [item.task["task_id"] for item in executor.invocations])
        self.assertEqual(6, result.model_calls)
        self.assertEqual(210, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        inner = next(item for item in journal if item["kind"] == "delegation-proposed" and item["parent"] == "A")
        self.assertEqual(2, inner["ancestor_and_sibling_model_calls"])
        self.assertEqual(400, inner["ancestor_and_sibling_tokens"])
        self.assertEqual("G", executor.invocations[3].context["child_results"][0]["handoff"]["task_id"])
        self.assertEqual(["A", "B"], [item["handoff"]["task_id"] for item in executor.invocations[-1].context["child_results"]])
        self.assertEqual(3, len(report["handoff_consumptions"]))

    def test_nested_call_shortage_keeps_ancestor_and_pending_sibling_reservations(self):
        first, sibling, grandchild = self.nested_tasks()
        executor = OfflineExecutor([control([first, sibling]), control([grandchild])])
        result, journal, _ = self.run_case(executor, budget=self.budget(max_model_calls=5))
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(["MAIN", "A"], [item.task["task_id"] for item in executor.invocations])
        self.assertEqual(("G", "B"), result.unstarted_tasks)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(70, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertIn("wave call reservation", result.summary)
        self.assertNotIn("handoff-produced-and-validated", [item["kind"] for item in journal])

    def test_nested_token_shortage_cannot_spend_outer_sibling_or_consumer_capacity(self):
        first, sibling, grandchild = self.nested_tasks()
        executor = OfflineExecutor([control([first, sibling]), control([grandchild])])
        result, _, _ = self.run_case(executor, budget=self.budget(max_total_tokens=800))
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("G", "B"), result.unstarted_tasks)
        self.assertEqual(2, len(executor.invocations))
        self.assertEqual(70, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertIn("wave token reservation", result.summary)

    def test_multiturn_session_upper_limits_preserve_every_child_and_parent_slice(self):
        children = [child_task("A"), child_task("B")]
        texts = [control(children), control(), control(), control()]
        executor = OfflineExecutor([RoleObservation("completed", text, 2, 40, 30) for text in texts])
        result, journal, _ = self.run_case(executor,
            budget=self.budget(max_model_calls=8, max_session_model_turns=2))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual(8, result.model_calls)
        self.assertEqual(280, result.known_tokens)
        self.assertEqual([2] * 4, [item.max_model_calls for item in executor.invocations])
        self.assertEqual([400] * 4, [item.max_total_tokens for item in executor.invocations])
        proposed = next(item for item in journal if item["kind"] == "delegation-proposed")
        self.assertEqual(6, proposed["reserved_model_calls"])

    def test_multiturn_wave_requires_all_bounded_session_turns_before_first_child(self):
        children = [child_task("A"), child_task("B")]
        executor = OfflineExecutor([RoleObservation("completed", control(children), 2, 40, 30)])
        result, _, _ = self.run_case(executor,
            budget=self.budget(max_model_calls=7, max_session_model_turns=2))
        self.assert_refusal(result, executor, children, calls=2, known=70)
        self.assertIn("wave call reservation", result.summary)

    def test_unused_multiturn_capacity_becomes_available_to_a_later_proposed_inner_wave(self):
        first, sibling, grandchild = self.nested_tasks()
        executor = OfflineExecutor([control([first, sibling]), control([grandchild]),
                                    control(), control(), control(), control()])
        result, _, _ = self.run_case(executor,
            budget=self.budget(max_model_calls=10, max_total_tokens=1800, max_session_model_turns=2))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual(6, result.model_calls)
        self.assertEqual([2] * 6, [item.max_model_calls for item in executor.invocations])
        self.assertEqual(210, result.known_tokens)
        self.assertEqual(0, result.held_tokens)

    def test_actual_failed_child_keeps_known_usage_without_holding_unstarted_slices(self):
        children = [child_task("A"), child_task("B")]
        executor = OfflineExecutor([control(children), RoleObservation("failed", "", 1, 9, 1)])
        result, _, _ = self.run_case(executor)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(45, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertEqual(("B",), result.unstarted_tasks)
        self.assertEqual(2, len(executor.invocations))

    def test_child_handoff_failure_keeps_actual_response_and_unstarted_siblings(self):
        children = [child_task("A"), child_task("B")]
        missing = {"path": "work/A/missing-output.json", "sha256": "a" * 64}
        executor = OfflineExecutor([control(children),
            RoleObservation("completed", control(), 1, 20, 15, artifact_refs=(missing,))])
        result, _, _ = self.run_case(executor)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("B",), result.unstarted_tasks)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(70, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertEqual(missing, result.observations[-1]["artifact_refs"][0])
        self.assertEqual(2, len(executor.invocations))

    def test_unknown_current_slice_holds_only_that_slice_and_does_not_retry(self):
        children = [child_task("A"), child_task("B")]
        for turns in (1, 2):
            for response, actual_calls in ((RoleObservation("failed", "", 1, None, None), 2),
                                           (RuntimeError("private exception detail"), 1)):
                with self.subTest(turns=turns, response=type(response).__name__):
                    executor = OfflineExecutor([control(children), response])
                    result, journal, _ = self.run_case(executor, budget=self.budget(max_session_model_turns=turns))
                    self.assertEqual("safe-paused", result.status)
                    self.assertEqual(actual_calls, result.model_calls)
                    self.assertEqual(35, result.known_tokens)
                    self.assertEqual(200 * turns, result.held_tokens)
                    self.assertEqual(("B",), result.unstarted_tasks)
                    self.assertEqual(2, len(executor.invocations))
                    self.assertNotIn("private exception detail", json.dumps(journal))

    def test_proven_zero_dispatch_failure_marks_current_and_later_children_unstarted(self):
        children = [child_task("A"), child_task("B")]
        executor = OfflineExecutor([control(children), RoleObservation("safe-paused", "", 0, 0, 0)])
        result, _, _ = self.run_case(executor)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("A", "B"), result.unstarted_tasks)
        self.assertEqual(1, result.model_calls)
        self.assertEqual(35, result.known_tokens)
        self.assertEqual(0, result.held_tokens)

    def test_cancel_or_deadline_before_wave_refuses_all_children_and_keeps_initial_response(self):
        children = [child_task("A"), child_task("B")]
        for kind in ("cancel", "deadline"):
            with self.subTest(kind=kind):
                canceled, ticks = [False], [0.0]
                def finish_main(invocation):
                    if kind == "cancel":
                        canceled[0] = True
                    else:
                        ticks[0] = 60.0
                    return RoleObservation("completed", control(children), 1, 20, 15)
                executor = OfflineExecutor([finish_main])
                result, _, _ = self.run_case(executor, clock=lambda: ticks[0], cancel_requested=lambda: canceled[0])
                self.assert_refusal(result, executor, children)
                self.assertEqual(control(children), result.observations[0]["text"])

    def test_cancel_between_siblings_keeps_the_completed_child_and_unstarted_sibling(self):
        children = [child_task("A"), child_task("B")]
        canceled = [False]
        def finish_first_child(invocation):
            canceled[0] = True
            return RoleObservation("completed", control(), 1, 20, 15)
        executor = OfflineExecutor([control(children), finish_first_child])
        result, journal, _ = self.run_case(executor, cancel_requested=lambda: canceled[0])
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("B",), result.unstarted_tasks)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(70, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertEqual(1, sum(item["kind"] == "handoff-produced-and-validated" for item in journal))

    def test_expired_ancestor_consumer_blocks_inner_wave_even_while_child_time_remains(self):
        parent = main_task()
        parent["budget"]["max_seconds"] = 10
        first = child_task("A", parent=parent, delegating=True)
        sibling = child_task("B", parent=parent)
        grandchild = child_task("G", parent=first)
        ticks, advance_after_finish = [0.0], [False]
        def clock():
            value = ticks[0]
            if advance_after_finish[0]:
                # The child finishes within its admitted slice; subsequent
                # routing/admission preparation consumes the remaining time.
                ticks[0] = 11.0
                advance_after_finish[0] = False
            return value
        def first_result(invocation):
            ticks[0] = 8.0
            return RoleObservation("completed", control([first, sibling]), 1, 20, 15)
        def nested_proposal(invocation):
            self.assertEqual(10.0, invocation.deadline_monotonic)
            self.assertEqual(2.0, invocation.max_seconds)
            ticks[0] = 9.0
            advance_after_finish[0] = True
            return RoleObservation("completed", control([grandchild]), 1, 20, 15)
        executor = OfflineExecutor([first_result, nested_proposal])
        result, _, _ = self.run_case(executor, task=parent, clock=clock)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("G", "B"), result.unstarted_tasks)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(70, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertIn("pending parent consumption deadline", result.summary)

    def test_actual_usage_cannot_exceed_its_slice_and_consume_protected_sibling_capacity(self):
        children = [child_task("A"), child_task("B")]
        executor = OfflineExecutor([control(children), RoleObservation("completed", control(), 1, 190, 15)])
        result, _, _ = self.run_case(executor)
        self.assertEqual("safe-paused", result.status)
        self.assertEqual(("B",), result.unstarted_tasks)
        self.assertEqual(2, result.model_calls)
        self.assertEqual(240, result.known_tokens)
        self.assertEqual(0, result.held_tokens)
        self.assertIn("dispatched model/token budget", result.summary)

    def test_parent_output_remaining_narrows_the_reserved_consuming_session(self):
        parent = main_task()
        parent["budget"]["max_output_tokens"] = 200
        children = [child_task(identifier, parent=parent) for identifier in ("A", "B")]
        executor = OfflineExecutor([
            RoleObservation("completed", control(children), 2, 40, 150),
            RoleObservation("completed", control(), 2, 40, 30),
            RoleObservation("completed", control(), 2, 40, 30),
            RoleObservation("completed", control(), 2, 40, 20)])
        result, _, _ = self.run_case(executor, task=parent,
            budget=self.budget(max_model_calls=8, max_total_tokens=1500, max_session_model_turns=2))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual(2, executor.invocations[-1].max_model_calls)
        self.assertEqual(25, executor.invocations[-1].max_output_tokens)
        self.assertEqual(250, executor.invocations[-1].max_total_tokens)
        self.assertEqual(390, result.known_tokens)

    def test_parent_remaining_single_turn_is_preserved_alongside_multiturn_children(self):
        parent = main_task()
        parent["budget"]["max_turns"] = 3
        children = [child_task(identifier, parent=parent) for identifier in ("A", "B")]
        executor = OfflineExecutor([
            RoleObservation("completed", control(children), 2, 40, 30),
            RoleObservation("completed", control(), 2, 40, 30),
            RoleObservation("completed", control(), 2, 40, 30),
            RoleObservation("completed", control(), 1, 20, 15)])
        result, _, _ = self.run_case(executor, task=parent,
            budget=self.budget(max_model_calls=7, max_session_model_turns=2))
        self.assertEqual("stage-completed", result.status, result.summary)
        self.assertEqual([2, 2, 2, 1], [item.max_model_calls for item in executor.invocations])
        self.assertEqual(7, result.model_calls)
        self.assertEqual(245, result.known_tokens)


if __name__ == "__main__":
    unittest.main()
