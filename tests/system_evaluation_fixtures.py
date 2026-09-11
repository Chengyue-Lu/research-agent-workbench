"""Synthetic M5 contracts. These objects are never production admission evidence."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from research_workbench.capability.requirements import CapabilityRequirement
from research_workbench.capability.supply import CapabilitySupplyReport, assess_supply
from research_workbench.io import load_document
from tests.execution_fixtures import ROOT, ExecutionViewFixture, RuntimeBundleFixture

BOUNDARIES = dict.fromkeys(
    (
        "runtime_input",
        "execution_authority",
        "supply_selection",
        "human_decision",
        "claim_acceptance",
        "promotion",
    ),
    False,
)
AT = "2026-09-11T00:00:00Z"


class ProtocolFixtureMixin:
    fixture_steps = ("build",)

    @classmethod
    def setUpClass(cls):
        import tempfile

        super().setUpClass()
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.template = SystemEvaluationFixture(Path(temporary.name))
        for step in cls.fixture_steps:
            getattr(cls.template, step)()

    def setUp(self):
        import shutil
        import tempfile

        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.f = copy.deepcopy(self.template)
        self.f.root = Path(temporary.name)
        shutil.copytree(self.template.root, self.f.root, dirs_exist_ok=True)


class OverlapFixtureMixin(ProtocolFixtureMixin):
    fixture_steps = ("build", "overlap_inputs")


class OverlayFixtureMixin(ProtocolFixtureMixin):
    fixture_steps = ("build", "overlap_inputs", "build_overlay", "build_pairwise")


def record(kind, key, identity, **fields):
    return {
        "schema_version": "0.1.0",
        "record_kind": kind,
        key: identity,
        "version": "1.0.0",
        **fields,
        "boundaries": dict(BOUNDARIES),
    }


class SystemEvaluationFixture:
    def __init__(self, root: Path):
        self.root = root

    def ref(self, path):
        return {
            "path": path,
            "sha256": hashlib.sha256((self.root / path).read_bytes()).hexdigest(),
        }

    def write(self, path, document):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(document, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return self.ref(path)

    def raw(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self.ref(path)

    def doc(self, path):
        return copy.deepcopy(load_document(self.root / path))

    def c_ref(self, identity, ref):
        return {
            "ref": identity,
            "document_path": ref["path"],
            "content_hash": "sha256:" + ref["sha256"],
        }

    def build(self):
        manifest = copy.deepcopy(
            load_document(
                ROOT / "examples/evals/manifests/EVAL-MANIFEST-M5-003-001.yaml"
            )
        )

        def copy_refs(value):
            if isinstance(value, dict):
                if "path" in value and "sha256" in value:
                    self.raw(value["path"], (ROOT / value["path"]).read_bytes())
                else:
                    for child in value.values():
                        copy_refs(child)
            elif isinstance(value, list):
                for child in value:
                    copy_refs(child)

        copy_refs(manifest)
        RuntimeBundleFixture()._build_bundle(self.root)
        self.task_ref = self.ref("bundle/task.yaml")
        manifest["manifest_id"] = "M5-006-SYNTHETIC-MANIFEST"
        manifest["frozen_conditions"]["budget"] = {
            "max_turns": 4,
            "max_output_tokens": 2048,
            "max_parallel": 0,
        }
        manifest["frozen_conditions"]["task_packet_refs"] = [self.task_ref]
        for treatment in manifest["arms"][2:]:
            treatment["treatment_control"]["method_resolution_refs"] = [
                self.ref("bundle/method.yaml")
            ]
        self.bindings = {}
        self.runtime_refs = {}
        for index, arm_id in ((1, "plain-agent-tool"), (2, "mode-no-skill")):
            prefix = f"arm-{index}"
            implementation = self.raw(
                f"{prefix}/implementation.py",
                b"def bounded_operation(value):\n    return value\n",
            )
            supply = self.doc("bundle/supply.yaml")
            supply["report_id"] = f"m5-synthetic-supply-{index}"
            identity = supply["supply_identity"]
            identity["supply_kind"] = "tool" if index == 1 else "procedure"
            identity["implementation_ref"] = f"m5-synthetic-implementation-{index}"
            identity["content_hash"] = "sha256:" + implementation["sha256"]
            identity["components"] = [
                {
                    "component_kind": identity["supply_kind"],
                    "component_ref": identity["implementation_ref"],
                    "version": "1.0.0",
                    "content_hash": identity["content_hash"],
                }
            ]
            conformance = self.doc("bundle/conformance.yaml")
            conformance["implementation_ref"] = identity["implementation_ref"]
            evidence_ref = self.write(f"{prefix}/conformance.json", conformance)
            supply["conformance_evidence"][0]["artifact_ref"] = evidence_ref
            structural = copy.deepcopy(conformance)
            structural["evidence_id"] += "-STRUCTURAL"
            structural["evidence_kind"] = "deterministic-fixture"
            structural["scope"] = {
                "scope_kind": "synthetic-bounded-fixture",
                "fixture_id": structural["evidence_id"],
            }
            structural_ref = self.write(
                f"{prefix}/structural-conformance.json", structural
            )
            supply_ref = self.write(f"{prefix}/supply.json", supply)
            resolution = self.doc("bundle/resolution.yaml")
            resolution["resolution_id"] = f"M5-SYNTHETIC-RESOLUTION-{index}"
            resolution["candidate_supply_report_refs"] = [
                self.c_ref(supply["report_id"] + "@1.0.0", supply_ref)
            ]
            resolution["selected_supply_report_ref"] = supply["report_id"] + "@1.0.0"
            requirement = CapabilityRequirement.from_mapping(
                self.doc("bundle/requirement.yaml")
            )

            def comparison(qualification, requirement=requirement, supply=supply):
                return assess_supply(
                    requirement,
                    CapabilitySupplyReport.from_mapping(supply),
                    qualification=qualification,
                    evidence_check=lambda *_args: "pass",
                ).to_mapping()

            resolution["comparisons"] = [comparison("runtime-execution")]
            runtime_resolution = self.write(
                f"{prefix}/runtime-resolution.json", resolution
            )
            snapshot = self.doc("bundle/snapshot.yaml")
            snapshot["snapshot_id"] = f"M5-SYNTHETIC-SNAPSHOT-{index}"
            snapshot["resolution_ref"] = self.c_ref(
                resolution["resolution_id"] + "@r1", runtime_resolution
            )
            snapshot["selected_supply_report_ref"] = self.c_ref(
                supply["report_id"] + "@1.0.0", supply_ref
            )
            snapshot["supply_identity"] = copy.deepcopy(identity)
            snapshot["conformance_evidence_refs"] = [evidence_ref]
            runtime_ref = self.write(f"{prefix}/runtime-snapshot.json", snapshot)
            self.runtime_refs[arm_id] = runtime_ref
            supply["observation_scope"] = "synthetic-bounded-fixture"
            supply["availability"]["scope"] = {
                "scope_kind": "fixture-only",
                "fixture_id": structural["evidence_id"],
            }
            supply["conformance_evidence"] = [
                {
                    "evidence_id": structural["evidence_id"],
                    "evidence_class": "deterministic",
                    "artifact_kind": "capability-conformance-evidence",
                    "artifact_ref": structural_ref,
                }
            ]
            frozen_supply_ref = self.write(f"{prefix}/frozen-supply.json", supply)
            resolution["qualification"] = "structural-replay"
            resolution["candidate_supply_report_refs"] = [
                self.c_ref(supply["report_id"] + "@1.0.0", frozen_supply_ref)
            ]
            resolution["comparisons"] = [comparison("structural-replay")]
            frozen_resolution = self.write(
                f"{prefix}/frozen-resolution.json", resolution
            )
            snapshot["qualification"] = "structural-replay"
            snapshot["boundaries"]["execution_input"] = False
            snapshot["resolution_ref"] = self.c_ref(
                resolution["resolution_id"] + "@r1", frozen_resolution
            )
            snapshot["selected_supply_report_ref"] = self.c_ref(
                supply["report_id"] + "@1.0.0", frozen_supply_ref
            )
            snapshot["conformance_evidence_refs"] = [structural_ref]
            frozen_ref = self.write(f"{prefix}/frozen-snapshot.json", snapshot)
            manifest["arms"][index]["capability_snapshot_refs"] = [frozen_ref]
            interface = record(
                "evaluation_provider_interface",
                "interface_id",
                f"M5-INTERFACE-{index}",
                supply_identity=copy.deepcopy(identity),
                supported_inputs=supply["supported_inputs"],
                supported_outputs=supply["supported_outputs"],
                provided_capabilities=supply["provided_capabilities"],
                provider_visible_interface={
                    "name": "bounded_operation",
                    "input": {"type": "string"},
                },
            )
            self.bindings[arm_id] = {
                "arm_id": arm_id,
                "snapshot_ref": frozen_ref,
                "implementation_ref": implementation,
                "component_refs": [
                    {
                        "component_ref": identity["implementation_ref"],
                        "version": "1.0.0",
                        "file_ref": implementation,
                    }
                ],
                "interface_ref": self.write(f"{prefix}/interface.json", interface),
            }
        self.manifest_ref = self.write("evaluation/manifest.json", manifest)
        schema = json.loads(
            (
                ROOT / "schemas/v0.1.0/system-evaluation-protocol.schema.json"
            ).read_bytes()
        )
        decision = schema["properties"]["decision_ref"]["const"]
        self.raw(decision["path"], (ROOT / decision["path"]).read_bytes())
        mode_refs = [
            self.raw(
                "registry/modes/evidence-synthesis.yaml",
                (ROOT / "registry/modes/evidence-synthesis.yaml").read_bytes(),
            )
        ]
        action_refs = [
            self.raw(
                f"registry/modes/actions/evidence-synthesis/{name}.yaml",
                (
                    ROOT / f"registry/modes/actions/evidence-synthesis/{name}.yaml"
                ).read_bytes(),
            )
            for name in ("ES-A3", "ES-A4")
        ]
        view_inputs = ExecutionViewFixture()._inputs(self.root)
        frozen = manifest["frozen_conditions"]
        execution_binding = self.doc(view_inputs["execution_binding"].path)
        execution_binding["model"]["ref"] = frozen["model"]["model_id"]
        execution_binding["model"]["slot"] = frozen["model"]["slot_id"]
        execution_binding["adapter"]["ref"] = frozen["model"]["provider_adapter"]
        execution_binding["host"]["ref"] = frozen["host"]["host_id"]
        execution_binding["runtime"]["ref"] = frozen["host"]["runtime"]
        self.protocol = record(
            "system_evaluation_protocol",
            "protocol_id",
            "M5-SYNTHETIC-PROTOCOL",
            decision_ref=decision,
            manifest_ref=self.manifest_ref,
            frozen_at=AT,
            purpose="synthetic-contract-proof",
            execution_time_budget_seconds=120,
            execution_binding={
                key: execution_binding[key]
                for key in ("provider", "adapter", "model", "runtime", "host")
            },
            admission_case_closure_ref=None,
            rules=schema["properties"]["rules"]["const"],
            mode_documents=mode_refs,
            action_documents=action_refs,
            execution_bindings=list(self.bindings.values()),
            design={
                "randomization": {
                    "unit": "case-replicate",
                    "method": "seeded-permutation-within-block",
                    "seed": 57,
                    "block_by": ["case_id", "replicate"],
                },
                "replicates_per_case": 3,
                "pilot_replicates_per_case": 1,
                "pilot_primary_eligible": False,
                "stopping": {
                    "rule": "fixed-complete-blocks",
                    "case_count": 2,
                    "completed_blocks": 6,
                    "early_stop": "safety-only-retain-all-attempts",
                },
                "retry": {
                    "max_retries": 0,
                    "eligible_failures": [],
                    "fresh_attempt": True,
                    "retain_failed_attempts": True,
                    "include_all_attempt_costs": True,
                },
                "drift": {
                    "pins": [
                        "model",
                        "provider",
                        "adapter",
                        "host",
                        "runtime",
                        "task",
                        "context",
                        "budget",
                        "data",
                    ],
                    "action": "block-and-new-protocol-version",
                },
                "analysis": {
                    "unit": "case-replicate-paired-difference",
                    "summary": "per-metric-paired-differences-and-intervals",
                    "interval": "case-cluster-bootstrap",
                    "confidence_level": 0.95,
                    "resamples": 1000,
                    "seed": 57,
                    "missing": "report-by-status-no-imputation",
                    "secondary": "descriptive-no-confirmatory-claim",
                    "reveal_after": "all-blind-human-reviews-frozen",
                },
            },
        )
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        return self

    def shared_view_inputs(self, view_inputs, prefix):
        from research_workbench.execution.execution_view import PinnedExecutionInput

        frozen = self.doc(self.manifest_ref["path"])["frozen_conditions"]
        profile = self.doc(view_inputs["agent_profile"].path)
        profile["model_policy"]["default_slot"] = frozen["model"]["slot_id"]
        host_policy = self.doc(view_inputs["host_policy"].path)
        binding = self.doc(view_inputs["execution_binding"].path)
        binding.update(copy.deepcopy(self.protocol["execution_binding"]))
        host_policy["subject_host"] = binding["host"]
        for key, document in (
            ("agent_profile", profile),
            ("host_policy", host_policy),
            ("execution_binding", binding),
        ):
            reference = self.write(f"{prefix}/shared-{key}.json", document)
            view_inputs[key] = PinnedExecutionInput(**reference)
        return view_inputs

    def build_pairwise(self):
        from research_workbench.evaluation.comparability import (
            comparison_surface,
            derive_comparability,
        )
        from research_workbench.evaluation.overlay import validate_overlay
        from research_workbench.evaluation.pins import EvaluationInputs
        from research_workbench.evaluation.qualification import validate_qualification
        from research_workbench.execution import (
            load_runtime_bundle,
            produce_resolved_execution_view,
        )
        from research_workbench.execution.execution_view import PinnedExecutionInput
        from tests.execution_fixtures import ExecutionViewFixture

        bundle = self.doc("bundle/manifest.yaml")
        mapping = {
            "bundle/supply.yaml": "arm-2/supply.json",
            "bundle/conformance.yaml": "arm-2/conformance.json",
            "bundle/resolution.yaml": "arm-2/runtime-resolution.json",
            "bundle/snapshot.yaml": "arm-2/runtime-snapshot.json",
        }

        def remap(value):
            if isinstance(value, dict):
                result = {k: remap(v) for k, v in value.items()}
                if "path" in result and "sha256" in result:
                    result["sha256"] = self.ref(result["path"])["sha256"]
                return result
            if isinstance(value, list):
                return [remap(v) for v in value]
            return mapping.get(value, value) if isinstance(value, str) else value

        bundle = remap(bundle)
        bundle_ref = self.write("a3/bundle.json", bundle)
        loaded = load_runtime_bundle(
            bundle_ref["path"], project_root=self.root, schema_root=ROOT / "schemas"
        )
        view_inputs = self.shared_view_inputs(
            ExecutionViewFixture()._inputs(self.root), "a3"
        )
        binding = self.doc(view_inputs["execution_binding"].path)
        binding["selected_supply_report_ref"] = "m5-synthetic-supply-2@1.0.0"
        binding_ref = self.write("a3/binding.json", binding)
        view_inputs["execution_binding"] = PinnedExecutionInput(**binding_ref)
        view = produce_resolved_execution_view(
            loaded,
            **view_inputs,
            execution_at=AT,
            view_id="M5-SYNTHETIC-A3-VIEW",
            expected_bundle_sha256=bundle_ref["sha256"],
            schema_root=ROOT / "schemas",
        )
        view_ref = self.write("a3/view.json", view)
        qualification = self.qualification("mode-no-skill")
        qualification_ref = self.write(
            "evaluation/a3-qualification.json", qualification
        )
        overlay_ref = self.write("evaluation/a4-overlay.json", self.overlay)
        inputs = EvaluationInputs(self.root, ROOT / "schemas")
        a3 = validate_qualification(
            inputs, qualification, expected_protocol_ref=self.protocol_ref
        )
        a3[0]["view"] = view
        a4 = validate_overlay(
            inputs,
            self.overlay,
            expected_protocol_ref=self.protocol_ref,
            expected_case_closure_ref=self.case_closure_ref,
            case_selection_frozen_at=AT,
            admission_verifier=lambda _evidence: True,
        )
        result = derive_comparability(
            comparison_surface(a3), comparison_surface(a4), admitted_skill_count=1
        )
        self.pairwise = record(
            "a3_a4_pairwise_comparability",
            "comparability_id",
            "M5-SYNTHETIC-PAIRWISE",
            protocol_ref=self.protocol_ref,
            manifest_ref=self.manifest_ref,
            a3_qualification_ref=qualification_ref,
            a4_overlay_ref=overlay_ref,
            a3_runtime_bindings=[
                {
                    "snapshot_ref": self.runtime_refs["mode-no-skill"],
                    "bundle_ref": bundle_ref,
                    "view_ref": view_ref,
                }
            ],
            case_closure_ref=self.case_closure_ref,
            checked_at=AT,
            stage="plan-pre-run",
            preregistered_record_ref=None,
            result=result,
        )
        return self

    def qualification(self, arm_id="plain-agent-tool"):
        binding = self.bindings[arm_id]
        return record(
            "arm_execution_qualification",
            "qualification_id",
            "M5-QUAL-" + arm_id,
            protocol_ref=self.protocol_ref,
            manifest_ref=self.manifest_ref,
            arm_id=arm_id,
            producer="m6-baseline-transport"
            if arm_id == "plain-agent-tool"
            else "evaluation-harness",
            checked_at=AT,
            qualified=True,
            bindings=[
                {
                    "frozen_snapshot_ref": binding["snapshot_ref"],
                    "runtime_snapshot_ref": self.runtime_refs[arm_id],
                    **{
                        k: binding[k]
                        for k in (
                            "implementation_ref",
                            "component_refs",
                            "interface_ref",
                        )
                    },
                }
            ],
        )

    def subject(self, identity, ref):
        return {
            "state": "resolved",
            "identity": identity,
            "ref": ref,
            "reason": "Synthetic exact commitment.",
        }

    def case(self, name, task_ref):
        task = self.doc(task_ref["path"])
        oracle = self.subject(
            name + "-ORACLE",
            self.raw(f"cases/{name}/oracle.txt", ("Synthetic oracle " + name).encode()),
        )
        case = {
            "task_kind": "formal-task",
            "task": self.subject(f"{task['task_id']}@r{task['revision']}", task_ref),
            "formal_inputs": [
                self.subject(
                    name + "-INPUT",
                    self.raw(
                        f"cases/{name}/input.txt", ("Synthetic input " + name).encode()
                    ),
                )
            ],
            "private_oracle": oracle,
        }
        for key in ("checker", "human_adjudication"):
            identity = name + "-" + key
            ref = self.write(
                f"cases/{name}/{key}.json",
                {"identity": identity, "case_id": name, "oracle_ref": oracle["ref"]},
            )
            case[key] = self.subject(identity, ref)
        case["case"] = self.subject(
            name, self.write(f"cases/{name}/case.json", {"case_id": name, **case})
        )
        return case

    def overlap_inputs(self):
        task = self.doc(self.task_ref["path"])
        task["task_id"] = "M5-SYNTHETIC-ADMISSION-TASK"
        admission_task = self.write("cases/admission-task.json", task)
        admission_case = self.case("ADMISSION-CASE", admission_task)
        self.admission_closure = record(
            "evaluation_case_closure",
            "closure_id",
            "M5-ADMISSION-CLOSURE",
            scope="admission",
            cases=[admission_case],
        )
        comparison_cases = [
            self.case(f"CONFIRMATORY-{i}", self.task_ref) for i in (1, 2)
        ]
        self.case_closure = record(
            "evaluation_case_closure",
            "closure_id",
            "M5-CONFIRMATORY-CLOSURE",
            scope="confirmatory",
            cases=comparison_cases,
        )
        self.case_closure_ref = self.write(
            "evaluation/case-closure.json", self.case_closure
        )
        manifest = self.doc(self.manifest_ref["path"])
        evaluation = self.doc(manifest["arms"][3]["skill_evaluation_ref"]["path"])
        evaluation["cases"][0]["case_id"] = "ADMISSION-CASE"
        evaluation["cases"][0]["task_contract_ref"] = admission_task
        evaluation["cases"][0]["input_ref"] = admission_case["formal_inputs"][0]["ref"]
        self.evaluation_ref = self.write("evaluation/admission.json", evaluation)
        manifest["arms"][3]["skill_evaluation_ref"] = self.evaluation_ref
        self.manifest_ref = self.write("evaluation/manifest.json", manifest)
        self.protocol["manifest_ref"] = self.manifest_ref
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        return self

    def assessment(self):
        from research_workbench.evaluation.overlap import (
            derive_overlap,
            validator_identity,
        )
        from research_workbench.evaluation.pins import EvaluationInputs, digest

        self.protocol["admission_case_closure_ref"] = self.write(
            "evaluation/admission-cases.json", self.admission_closure
        )
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        inputs = EvaluationInputs(self.root, ROOT / "schemas")
        evaluation = self.doc(self.evaluation_ref["path"])
        admission = {
            "skill_evaluation_ref": self.evaluation_ref,
            **{k: evaluation[k] for k in ("candidate_id", "skill_id", "skill_version")},
            "closure": self.admission_closure,
        }
        left, right, result = derive_overlap(
            inputs, self.admission_closure, self.case_closure
        )
        return record(
            "admission_evidence_overlap",
            "assessment_id",
            "M5-SYNTHETIC-OVERLAP",
            admission_case_closure=admission,
            comparison_input_closure={
                "protocol_ref": self.protocol_ref,
                "case_closure_ref": self.case_closure_ref,
                "admission_closure_sha256": digest(admission),
                "admission_subjects": left,
                "comparison_subjects": right,
                "input_digest": digest({"admission": left, "comparison": right}),
            },
            assessment_result={
                "checked_at": AT,
                "validator": validator_identity(inputs),
                **result,
            },
        )

    def build_overlay(self):
        import tempfile

        from research_workbench.artifacts.integrity import hash_directory
        from research_workbench.capability.lifecycle import (
            SkillLifecycleEntry,
            SkillLifecycleRecord,
        )
        from research_workbench.capability.models import SkillManifest
        from research_workbench.capability.release_projection import (
            projection_from_verified_release,
        )
        from research_workbench.execution import (
            load_runtime_bundle,
            produce_resolved_execution_view,
        )
        from research_workbench.execution.execution_view import PinnedExecutionInput
        from tests.execution_fixtures import ExecutionViewFixture
        from tests.skill_runtime_fixtures import SkillRuntimeBundleFixture

        source = self.raw(
            "accepted/synthetic-skill/SKILL.md",
            b"# Synthetic Skill\nOnly contract evidence.\n",
        )
        package_hash = hash_directory(self.root / "accepted/synthetic-skill")
        projection = SkillRuntimeBundleFixture.projection()
        contract = projection["runtime_contract"]
        release = {
            "schema_version": "0.1.0",
            "skill_id": "synthetic-runtime-skill",
            "version": "1.0.0",
            "kind": "method",
            "description": "Synthetic M5 admission mapping test.",
            "capabilities": contract["provided_capabilities"],
            "applies_to_modes": contract["compatibility"]["applies_to_modes"],
            "excludes": contract["compatibility"]["excludes"],
            "required_tools": [],
            "optional_tools": [],
            "permission_ceiling": contract["permission_ceiling"],
            "runtime_boundaries": {
                "data_egress_ceiling": contract["data_egress_ceiling"],
                "side_effect_ceiling": contract["side_effect_ceiling"],
            },
            "input_contracts": contract["supported_inputs"],
            "output_contracts": contract["supported_outputs"],
            "context_cost": {
                "metadata": "low",
                "instructions": "low",
                "references": "on-demand",
            },
            "incompatible_with": [],
            "verification": {"deterministic": ["m5-contract-proof"]},
            "source": {
                "origin": "synthetic-fixture",
                "locator": source["path"],
                "content_hash": "sha256:" + source["sha256"],
                "package_hash": "sha256:" + package_hash,
            },
        }
        release_ref = self.write("accepted/manifest.json", release)
        evaluation = self.doc(self.evaluation_ref["path"])
        evaluation.update(
            skill_id=release["skill_id"],
            skill_version=release["version"],
            skill_source_ref=source,
            skill_package_hash=package_hash,
        )
        decision = {
            "schema_version": "0.1.0",
            "object_type": "decision",
            "object_id": "D-M5-SYNTHETIC",
            "revision": 1,
            "status": "accepted",
            "decision": "Synthetic admission fixture only.",
            "scope": [evaluation["candidate_id"]],
            "reason_refs": [evaluation["evaluation_id"]],
            "actor": "Synthetic Reviewer",
            "timestamp": AT,
            "metadata": {
                "skill_evaluation_id": evaluation["evaluation_id"],
                "skill_candidate_id": evaluation["candidate_id"],
                "decision_owner": "human",
                "skill_admission_outcome": "accept",
            },
        }
        decision_ref = self.write("evaluation/decision.json", decision)
        evaluation["admission"] = {
            "status": "human-decided",
            "outcome": "accept",
            "decision_ref": decision_ref["path"],
            "rationale": "Synthetic contract fixture; no actual Human admission.",
        }
        self.evaluation_ref = self.write("evaluation/admission.json", evaluation)
        lifecycle = {
            "schema_version": "0.1.0",
            "lifecycle_id": "synthetic-runtime-skill",
            "lifecycle_version": "1.0.0",
            "record_scope": "current",
            "skill_ref": {
                "skill_id": release["skill_id"],
                "version": "1.0.0",
                "manifest_path": release_ref["path"],
                "content_hash": release["source"]["content_hash"],
                "package_hash": release["source"]["package_hash"],
            },
            "need_refs": ["NEED-SYNTHETIC-RUNTIME"],
            "intake": {
                "state": "candidate",
                "source_refs": ["synthetic:fixture"],
                "reason": "Fixture",
            },
            "evaluation": {
                "state": "evidence-ready",
                "baseline_ref": "synthetic-baseline",
                "trial_ref": "synthetic-trial",
                "evaluation_record_ref": self.evaluation_ref["path"],
                "promotion_evidence_refs": ["synthetic-evidence"],
                "reason": "Fixture",
            },
            "admission": {
                "state": "accepted",
                "decision_owner": "human",
                "decision_ref": decision_ref["path"],
                "reason": "Fixture",
            },
            "runtime_eligibility": {
                "state": "eligible",
                "eligibility_ref": "M5-SYNTHETIC-ELIGIBILITY",
                "scopes": ["new-binding"],
                "reason": "Fixture",
            },
            "lifecycle": {
                "state": "current",
                "superseded_by_refs": [],
                "reason": "Fixture",
            },
            "boundaries": dict.fromkeys(
                (
                    "stores_trial_results",
                    "stores_evaluation_results",
                    "defines_benchmark_metrics",
                    "grants_permission",
                    "promotes_claim",
                ),
                False,
            ),
        }
        lifecycle_ref = self.write("accepted/lifecycle.json", lifecycle)
        lifecycle_record = SkillLifecycleRecord.from_mapping(lifecycle)
        entry = SkillLifecycleEntry(
            lifecycle_record.reference,
            lifecycle_record.lifecycle_id,
            "1.0.0",
            lifecycle_ref["path"],
            lifecycle_ref["sha256"],
            lifecycle_record,
        )
        projection = projection_from_verified_release(
            lifecycle_entry=entry,
            manifest=SkillManifest.from_mapping(release),
            manifest_sha256=release_ref["sha256"],
            projection_version="1.0.0",
        )

        with tempfile.TemporaryDirectory() as temporary:
            scratch = Path(temporary)
            path = SkillRuntimeBundleFixture()._build_skill_bundle(scratch)
            bundle = load_document(path)
            source_documents = {
                item["path"]: copy.deepcopy(load_document(scratch / item["path"]))
                for item in bundle["documents"]
            }
        source_documents["bundle/skill-projection.yaml"] = projection
        identity = source_documents["bundle/supply.yaml"]["supply_identity"]
        identity["content_hash"] = release["source"]["content_hash"]
        identity["components"][0]["content_hash"] = identity["content_hash"]
        source_documents["bundle/snapshot.yaml"]["supply_identity"] = copy.deepcopy(
            identity
        )
        path_map = {
            old: (old if old == "bundle/task.yaml" else "a4/" + old)
            for old in source_documents
        }

        def rename(value):
            if isinstance(value, dict):
                return {k: rename(v) for k, v in value.items()}
            if isinstance(value, list):
                return [rename(v) for v in value]
            if isinstance(value, str):
                return path_map.get(value, value)
            return value

        nodes = {path_map[path]: rename(doc) for path, doc in source_documents.items()}
        nodes["bundle/task.yaml"] = self.doc("bundle/task.yaml")
        written = {"bundle/task.yaml": self.task_ref}

        def refresh(value):
            if isinstance(value, dict):
                target = value.get("document_path", value.get("path"))
                if target in nodes:
                    ref = save(target)
                    if "content_hash" in value:
                        value["content_hash"] = "sha256:" + ref["sha256"]
                    if "sha256" in value:
                        value["sha256"] = ref["sha256"]
                for child in value.values():
                    refresh(child)
            elif isinstance(value, list):
                for child in value:
                    refresh(child)

        def save(path):
            if path not in written:
                refresh(nodes[path])
                written[path] = self.write(path, nodes[path])
            return written[path]

        for path in nodes:
            save(path)
        bundle = rename(bundle)
        refresh(bundle)
        bundle_ref = self.write("a4/bundle/manifest.json", bundle)
        self.a4_bundle_ref = bundle_ref
        loaded_bundle = load_runtime_bundle(
            bundle_ref["path"], project_root=self.root, schema_root=ROOT / "schemas"
        )
        view_inputs = self.shared_view_inputs(
            ExecutionViewFixture()._inputs(self.root), "a4"
        )
        binding = self.doc(view_inputs["execution_binding"].path)
        binding["selected_supply_report_ref"] = "supply-synthetic-runtime-skill@1.0.0"
        binding_ref = self.write("a4/view/binding.json", binding)
        view_inputs["execution_binding"] = PinnedExecutionInput(**binding_ref)
        view = produce_resolved_execution_view(
            loaded_bundle,
            **view_inputs,
            execution_at=AT,
            view_id="M5-SYNTHETIC-A4-VIEW",
            expected_bundle_sha256=bundle_ref["sha256"],
            schema_root=ROOT / "schemas",
        )
        view_ref = self.write("a4/view/view.json", view)
        supply = self.doc("a4/bundle/supply.yaml")
        interface = record(
            "evaluation_provider_interface",
            "interface_id",
            "M5-A4-INTERFACE",
            supply_identity=supply["supply_identity"],
            provided_capabilities=supply["provided_capabilities"],
            supported_inputs=supply["supported_inputs"],
            supported_outputs=supply["supported_outputs"],
            provider_visible_interface={
                "name": "bounded_operation",
                "input": {"type": "string"},
            },
        )
        interface_ref = self.write("a4/view/interface.json", interface)
        manifest = self.doc(self.manifest_ref["path"])
        manifest["arms"][3]["treatment_control"]["method_resolution_refs"] = [
            self.ref("a4/bundle/method.yaml")
        ]
        manifest["arms"][3]["skill_binding"] = {
            "skill_id": release["skill_id"],
            "version": "1.0.0",
            "content_hash": package_hash,
            "source_ref": source,
        }
        manifest["arms"][3]["skill_evaluation_ref"] = self.evaluation_ref
        self.manifest_ref = self.write("evaluation/manifest.json", manifest)
        self.protocol["manifest_ref"] = self.manifest_ref
        self.protocol_ref = self.write("evaluation/protocol.json", self.protocol)
        assessment = self.assessment()
        assessment_ref = self.write("evaluation/overlap.json", assessment)
        outcome = assessment["assessment_result"]
        self.overlay = record(
            "a4_execution_qualification",
            "overlay_id",
            "M5-SYNTHETIC-OVERLAY",
            protocol_ref=self.protocol_ref,
            manifest_ref=self.manifest_ref,
            arm_id="mode-candidate-skill",
            checked_at=AT,
            task_ref=self.task_ref,
            admission_evaluation_ref=self.evaluation_ref,
            admission_decision_ref=decision_ref,
            accountable_human="Synthetic Reviewer",
            release_ref=release_ref,
            lifecycle_ref=lifecycle_ref,
            projection_ref=self.ref("a4/bundle/skill-projection.yaml"),
            promotion_provenance_ref=None,
            runtime_bindings=[
                {
                    "snapshot_ref": self.ref("a4/bundle/snapshot.yaml"),
                    "bundle_ref": bundle_ref,
                    "view_ref": view_ref,
                    "interface_ref": interface_ref,
                }
            ],
            case_closure_ref=self.case_closure_ref,
            case_selection_frozen_at=AT,
            admission_overlap_assessment_ref=assessment_ref,
            overlap_status=outcome["overlap_status"],
            overlap_refs=outcome["overlap_refs"],
            primary_confirmatory_eligible=outcome["primary_confirmatory_eligible"],
            evidence_phase="pre-run-qualification",
        )
        return self
