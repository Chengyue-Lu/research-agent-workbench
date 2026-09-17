"""Synthetic evaluation-side inputs. M6 produces A2 before Harness invocation."""

import copy
import shutil
import tempfile
from pathlib import Path

from research_workbench.evaluation.harness_plan import compile_harness_plan
from research_workbench.evaluation.harness_preflight import (
    produce_a3_qualification,
    compile_harness_preflight,
)
from research_workbench.execution.baseline_envelope import produce_a2_qualification
from tests.baseline_fixtures import BaselineFixture
from tests.system_evaluation_fixtures import AT


class HarnessFixture(BaselineFixture):
    def build_harness(self):
        self.build_baseline("plain-agent-tool")
        self.overlap_inputs()
        manifest = self.doc(self.manifest_ref["path"])
        context = manifest["frozen_conditions"]["context"]["initial_context_refs"]
        self.public_cases = []
        for case in self.case_closure["cases"]:
            name = case["case"]["identity"]
            refs = [i["ref"] for i in case["formal_inputs"]]
            projection = {
                "task_ref": case["task"]["ref"],
                "instruction": "Use the supplied public case inputs.",
                "input_refs": refs,
                "required_outputs": ["plain-text-answer"],
            }
            projection_ref = self.write(f"public/{name}.json", projection)
            context.extend([*refs, projection_ref])
            self.public_cases.append(
                {"case_id": name, "public_payload_ref": projection_ref}
            )
        self.manifest_ref = self.write("evaluation/manifest.json", manifest)
        self.protocol["manifest_ref"] = self.manifest_ref
        self.protocol["design"]["retry"].update(
            max_retries=1, eligible_failures=["provider-transient"]
        )
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        self.build_overlay()
        self.build_pairwise()
        self.a2 = produce_a2_qualification(
            self.inputs(),
            protocol_ref=self.protocol_ref,
            qualification_id="HARNESS-A2",
            checked_at=AT,
            bindings=self.qualification()["bindings"],
        )
        self.a2_ref = self.write("harness/a2.json", self.a2)
        self.a3 = produce_a3_qualification(
            self.inputs(),
            protocol_ref=self.protocol_ref,
            qualification_id="HARNESS-A3",
            preflight_checked_at=AT,
            bindings=self.qualification("mode-no-skill")["bindings"],
        )
        self.a3_ref = self.write("harness/a3.json", self.a3)
        self.pairwise["a3_qualification_ref"] = self.a3_ref
        self.pairwise_ref = self.write("harness/pairwise.json", self.pairwise)
        self.overlay_ref = self.pairwise["a4_overlay_ref"]
        self.overlap_ref = self.overlay["admission_overlap_assessment_ref"]
        self.case_bindings = [
            {
                "case_id": c["case_id"],
                "a4_overlay_ref": self.overlay_ref,
                "pairwise_ref": self.pairwise_ref,
            }
            for c in self.public_cases
        ]
        self.plan = self.compile_plan()
        self.plan_ref = self.write("harness/plan.json", self.plan)
        return self

    def plan_context(self):
        return {
            "expected_protocol_ref": self.protocol_ref,
            "expected_case_closure_ref": self.case_closure_ref,
            "case_selection_frozen_at": AT,
            "expected_run_id": "SYNTHETIC-RUN-1",
        }

    def compile_plan(self, **overrides):
        args = {
            "protocol_ref": self.protocol_ref,
            "case_closure_ref": self.case_closure_ref,
            "case_selection_frozen_at": AT,
            "public_cases": self.public_cases,
            "plan_id": "HARNESS-PLAN-1",
            "run_id": "SYNTHETIC-RUN-1",
        }
        return compile_harness_plan(self.inputs(), **(args | overrides))

    def preflight_args(self):
        return {
            **self.plan_context(),
            "plan_ref": self.plan_ref,
            "preflight_id": "HARNESS-PREFLIGHT-1",
            "preflight_checked_at": AT,
            "a2_qualification_ref": self.a2_ref,
            "a3_qualification_ref": self.a3_ref,
            "overlap_ref": self.overlap_ref,
            "case_bindings": self.case_bindings,
            "admission_verifier": lambda _: True,
        }

    def preflight(self, **overrides):
        return compile_harness_preflight(
            self.inputs(), **(self.preflight_args() | overrides)
        )

    def freeze_protocol(self):
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)

    def freeze_case(self, index=0):
        case = self.case_closure["cases"][index]
        document = {
            "case_id": case["case"]["identity"],
            **{k: v for k, v in case.items() if k != "case"},
        }
        case["case"]["ref"] = self.write(case["case"]["ref"]["path"], document)
        self.case_closure_ref = self.write(
            "evaluation/case-closure.json", self.case_closure
        )

    def refreeze_overlap(self, state):
        case = self.case_closure["cases"][0]
        if state == "admission-overlap":
            case["private_oracle"] = copy.deepcopy(
                self.admission_closure["cases"][0]["private_oracle"]
            )
        else:
            case["private_oracle"] = {
                "state": "unknown",
                "identity": None,
                "ref": None,
                "reason": "Synthetic missing oracle",
            }
        for key in ("checker", "human_adjudication"):
            document = self.doc(case[key]["ref"]["path"])
            document["oracle_ref"] = case["private_oracle"]["ref"]
            case[key]["ref"] = self.write(case[key]["ref"]["path"], document)
        self.freeze_case()
        assessment = self.assessment()
        self.overlap_ref = self.write("harness/new-overlap.json", assessment)
        self.overlay.update(
            case_closure_ref=self.case_closure_ref,
            admission_overlap_assessment_ref=self.overlap_ref,
        )
        for key in ("overlap_status", "overlap_refs", "primary_confirmatory_eligible"):
            self.overlay[key] = assessment["assessment_result"][key]
        self.overlay_ref = self.write("harness/new-overlay.json", self.overlay)
        self.pairwise.update(
            case_closure_ref=self.case_closure_ref, a4_overlay_ref=self.overlay_ref
        )
        self.pairwise_ref = self.write("harness/new-pairwise.json", self.pairwise)
        self.case_bindings = [
            {
                "case_id": c["case_id"],
                "a4_overlay_ref": self.overlay_ref,
                "pairwise_ref": self.pairwise_ref,
            }
            for c in self.public_cases
        ]
        self.plan = self.compile_plan()
        self.plan_ref = self.write("harness/plan.json", self.plan)


class HarnessFixtureMixin:
    @classmethod
    def setUpClass(cls):
        cls.source = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.source.cleanup)
        cls.prototype = HarnessFixture(Path(cls.source.name)).build_harness()

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.f = copy.deepcopy(self.prototype)
        self.f.root = Path(directory.name)
        shutil.copytree(self.prototype.root, self.f.root, dirs_exist_ok=True)
