"""Explicit v2 live-pilot inputs for nonexecuting evaluation preparation.

This reader grants nothing and has no Provider, Tool, Driver or credential port.
The generic H1 plan is reusable; v1 execution/review records remain synthetic.
"""
from __future__ import annotations

import hashlib
import json
from datetime import timedelta, timezone

from research_workbench.evaluation.bounded_evidence import EvidenceOutputSpec, FORMAT
from research_workbench.evaluation.pins import (
    EvaluationInputs, EvaluationValidationError, digest, file_ref, require, timestamp,
)
from research_workbench.validation.schemas import SchemaCatalog


class LiveEvaluationInputs(EvaluationInputs):
    """Opt-in version routing, with an external Task token ceiling.

    Hash-consistent references are not qualified conformance, source admission,
    actual ledger totals or named authorization. Later execution must verify
    those facts independently. A scope never points back to its own Protocol or
    authorization; the external grant can bind the completed immutable inputs.
    """

    def __init__(self, root, schema_root=None, *, cumulative_token_ceiling: int):
        require(type(cumulative_token_ceiling) is int and cumulative_token_ceiling > 0,
                "live input policy requires an external positive token ceiling")
        super().__init__(root, schema_root)
        self.cumulative_token_ceiling = cumulative_token_ceiling
        # Self-contained schemas reuse frozen v1 fragments. Default loading uses
        # pinned package resources independently, without changing Core routing.
        self.live_catalog = SchemaCatalog(schema_root, version="0.2.0")
        self.live_schema_hashes = {}
        for name in self.live_catalog.names:
            path = self.live_catalog.directory / (name + ".schema.json")
            raw = path.read_bytes()
            require(json.loads(raw) == self.live_catalog.schema(name),
                    "live Schema changed while loading")
            self.live_schema_hashes[path.name] = hashlib.sha256(raw).hexdigest()

    def validate(self, kind, document):
        if kind in {"system_evaluation_protocol", "evaluation_live_scope"}:
            # Keep the accepted reader's finite-JSON invariant in the new route.
            try:
                digest(document)
            except (TypeError, ValueError) as exc:
                raise EvaluationValidationError("live document is not finite JSON data") from exc
            errors = self.live_catalog.validate(kind, document)
            require(not errors, "live schema: " + "; ".join(
                f"{error.pointer}: {error.validator}" for error in errors[:5]))
            return document
        require(not (kind.startswith("evaluation_harness_")
                     and kind != "evaluation_harness_plan")
                and kind != "evaluation_measurement",
                "live input reader supports nonexecuting H1 only; v1 downstream records are synthetic")
        result = super().validate(kind, document)
        if kind == "evaluation_harness_plan":
            request = document["request"]
            protocol = self.read(request["protocol_ref"], "system_evaluation_protocol")
            scope = self.read(protocol["live_scope_ref"], "evaluation_live_scope")
            require(file_ref(request["case_closure_ref"]) == file_ref(scope["input_closure_ref"]),
                    "live plan must use the exact scope input closure")
        return result

    def read(self, reference, kind=None):
        document = super().read(reference, kind)
        if kind == "system_evaluation_protocol":
            scope = self.read(document["live_scope_ref"], "evaluation_live_scope")
            self._check_scope(scope, document)
        return document

    def _check_scope(self, scope, protocol):
        require(timestamp(scope["frozen_at"]) <= timestamp(protocol["frozen_at"]),
                "live scope freeze follows Protocol freeze")
        require(protocol["admission_case_closure_ref"] is not None,
                "live Protocol needs a pinned admission case closure")
        require(protocol["design"]["retry"]["max_retries"] == 0,
                "this live candidate has no automatic retry/fallback")
        budget = scope["budget"]
        require(budget["cumulative_token_limit"] <= self.cumulative_token_ceiling,
                "live cumulative limit exceeds external Task policy")
        reserve = budget["max_provider_calls"] * (
            budget["max_request_input_tokens"] + budget["max_request_output_tokens"])
        require(budget["prior_tokens"] + reserve <= budget["cumulative_token_limit"],
                "live proposed reserve exceeds remaining cumulative tokens")
        require(budget["max_provider_calls"] >= budget["max_attempts"]
                and budget["max_provider_calls"] <= budget["max_attempts"] * budget["max_calls_per_attempt"],
                "live attempt/call bounds disagree")
        require(budget["max_attempt_seconds"] <= budget["max_run_seconds"],
                "live attempt time exceeds whole run time")
        require(budget["max_attempt_seconds"] == protocol["execution_time_budget_seconds"],
                "live per-attempt time differs from frozen shared conditions")
        window = scope["window"]
        start, end = timestamp(window["not_before"]), timestamp(window["not_after"])
        local = timezone(timedelta(hours=8))
        require(end > start and start.astimezone(local).date() == end.astimezone(local).date()
                and start.astimezone(local).hour >= 18,
                "this Task window must be within one Beijing evening after18:00")
        require(timestamp(protocol["frozen_at"]) <= start
                and (end - start).total_seconds() >= budget["max_run_seconds"],
                "live frozen/run time does not fit the proposed execution window")
        # Every declared reference is read/hash checked. This is deliberately
        # separate from the later qualified applicability/ledger/grant verifier.
        refs = [scope[key] for key in (
            "provider_config_ref", "provider_applicability_ref", "windows_context_ref",
            "budget_checkpoint_ref", "input_closure_ref")]
        refs += scope["source_artifact_refs"] + scope["tool_configuration_refs"]
        refs += [window["official_window_ref"]]
        for ref in refs:
            self.read_bytes(ref)
        source_refs = [file_ref(ref) for ref in scope["source_artifact_refs"]]
        require(len({ref["path"] for ref in source_refs}) == len(source_refs),
                "live source aliases duplicate a path")
        closure = self.read(scope["input_closure_ref"], "evaluation_case_closure")
        require(closure["scope"] == "confirmatory",
                "live input closure uses the existing evaluation-case scope")
        # 'confirmatory' is the existing case-closure type, never the use of a
        # live-pilot run. New downstream execution/analysis stays pilot-only.
        expected = {case["case"]["identity"] for case in closure["cases"]}
        require(len(expected) == len(closure["cases"]) == protocol["design"]["stopping"]["case_count"],
                "live input cases differ from the frozen Protocol count")
        pilot_replicates = protocol["design"]["pilot_replicates_per_case"]
        require(pilot_replicates > 0
                and budget["max_attempts"] >= len(expected) * pilot_replicates * 4,
                "live budget does not cover the full planned pilot blocks")
        rows = scope["output_contract"]["cases"]
        require(len({row["case_id"] for row in rows}) == len(rows)
                and {row["case_id"] for row in rows} == expected,
                "live output contract must cover each frozen input case once")
        require(scope["output_contract"]["format"] == FORMAT, "unsupported live output format")
        for row in rows:
            EvidenceOutputSpec(tuple(row["claim_ids"]), tuple(row["source_ids"]))
        self.recheck()

    def schema_identity(self):
        """Namespaced fingerprints for a future v2 parent record, never old H2."""
        return {**{"v0.1.0/" + name: value for name, value in self.schema_hashes.items()},
                **{"v0.2.0/" + name: value for name, value in self.live_schema_hashes.items()}}

    def recheck(self):
        super().recheck()
        for name, expected in self.live_schema_hashes.items():
            require(hashlib.sha256((self.live_catalog.directory / name).read_bytes()).hexdigest() == expected,
                    "live Schema bytes changed during validation")
