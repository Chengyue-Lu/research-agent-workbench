"""Cold, explicit Conformance-to-Pilot applicability evidence.

Distinct manifests remain distinct. The comparison is structural evidence for a
separately verified named Human Decision, never a live qualification or permit.
Archived Python is read and checked by existing cold readers, never imported.
"""

from research_workbench.adapters.models.profile_conformance_report import verify_profile_conformance_report
from research_workbench.adapters.models.provider_binding import GRAPH_POLICY, read_provider_binding_manifest
from research_workbench.evaluation.pins import digest, file_ref, require


KIND = "evaluation_provider_applicability_relation"
QUALIFIED_TRANSPORT = "research_workbench.adapters.models.conformance_transport.GuardedConformanceTransport"
PILOT_TRANSPORT = "research_workbench.evaluation.live_transport.GuardedPilotTransport"
LIMITATIONS = (
    "structural-comparison-is-not-joint-live-conformance",
    "original-report-warnings-and-source-compiler-trust-remain",
    "human-must-evaluate-every-source-and-facade-difference",
    "runtime-instance-callback-and-delegate-authority-remains-with-trusted-driver",
    "input-bound-account-window-skill-and-pilot-grants-are-independent",
)
_FIELDS = {"schema_version", "record_kind", "version", "purpose", "qualified_report_ref",
           "qualified_binding_ref", "pilot_binding_ref", "comparison", "limitations"}
_EQUAL_FIELDS = ("adapter_class", "adapter_version", "provider_identity", "credential_reference",
                 "credential_class", "code_runtime", "model_policy", "generation_policy")


def _comparison(inputs, qualified_ref, pilot_ref):
    qualified = read_provider_binding_manifest(inputs, qualified_ref).to_mapping()
    pilot = read_provider_binding_manifest(inputs, pilot_ref).to_mapping()
    require(all(m["version"] == "1.1.0" and m["binding_policy_version"] == GRAPH_POLICY
                for m in (qualified, pilot)), "applicability needs two cold source-graph bindings")
    require(qualified["transport_identity"]["class"] == QUALIFIED_TRANSPORT
            and pilot["transport_identity"]["class"] == PILOT_TRANSPORT,
            "applicability requires explicit Conformance and Pilot facades")
    require(all(qualified[k] == pilot[k] for k in _EQUAL_FIELDS)
            and qualified["transport_identity"]["options"] == pilot["transport_identity"]["options"],
            "applicability cannot substitute model/profile/credential/runtime/transport limits")
    profiles = [inputs.read(m["profile_ref"], "provider_api_profile") for m in (qualified, pilot)]
    configs = [inputs.read(m["resolved_config_ref"]) for m in (qualified, pilot)]
    require(profiles[0] == profiles[1] and configs[0] == configs[1],
            "applicability requires identical profile and resolved configuration content")
    # Both manifests have just validated their exact cold source closures. Read
    # those same pinned documents for comparison instead of compiling them a
    # second time. inputs.recheck() detects changes during this operation.
    graphs = [inputs.read(m["implementation_closure_ref"]) for m in (qualified, pilot)]
    require(graphs[0]["compiler"] == graphs[1]["compiler"]
            and graphs[0]["trusted_boundaries"] == graphs[1]["trusted_boundaries"],
            "applicability source compiler/trust substitution")
    modules = []
    for name in sorted(set(graphs[0]["modules"]) | set(graphs[1]["modules"])):
        refs = [file_ref(g["modules"][name]["source_ref"]) if name in g["modules"] else None for g in graphs]
        modules.append({"module": name, "qualified_source_ref": refs[0], "pilot_source_ref": refs[1],
                        "same_bytes": refs[0] is not None and refs[1] is not None
                                      and refs[0]["sha256"] == refs[1]["sha256"]})
    result = {"equal_identity": {k: qualified[k] for k in _EQUAL_FIELDS},
              "profile_content_sha256": digest(profiles[0]), "config_content_sha256": digest(configs[0]),
              "qualified_transport": qualified["transport_identity"], "pilot_transport": pilot["transport_identity"],
              "qualified_source_roots": qualified["source_roots"], "pilot_source_roots": pilot["source_roots"],
              "qualified_closure_ref": file_ref(qualified["implementation_closure_ref"]),
              "pilot_closure_ref": file_ref(pilot["implementation_closure_ref"]),
              "trusted_boundaries": graphs[0]["trusted_boundaries"], "modules": modules}
    inputs.recheck()
    return result, qualified, pilot


def _derive(inputs, qualified_report_ref, pilot_binding_ref):
    report = verify_profile_conformance_report(inputs.read(qualified_report_ref), root=inputs.root,
                                              schema_root=inputs.catalog.directory.parent)
    qualified_ref = file_ref(report["binding"]["manifest_ref"])
    pilot_ref = file_ref(pilot_binding_ref)
    require(qualified_ref != pilot_ref, "different-facade applicability needs distinct manifests")
    comparison, _, pilot = _comparison(inputs, qualified_ref, pilot_ref)
    inputs.recheck()
    return {"schema_version": "0.1.0", "record_kind": KIND, "version": "1.0.0",
            "purpose": "m5-conformance-to-pilot-applicability",
            "qualified_report_ref": file_ref(qualified_report_ref), "qualified_binding_ref": qualified_ref,
            "pilot_binding_ref": pilot_ref, "comparison": comparison, "limitations": list(LIMITATIONS)}, report, pilot


def provider_applicability_candidate(inputs, *, qualified_report_ref, pilot_binding_ref):
    """Build reviewable evidence; no acceptance, grant or implicit file write."""
    return _derive(inputs, qualified_report_ref, pilot_binding_ref)[0]


def read_provider_applicability_relation(inputs, reference, *, expected_pilot_binding_ref):
    """Recompute the full candidate. This returns evidence, never permission."""
    relation = inputs.read(reference)
    require(type(relation) is dict and set(relation) == _FIELDS,
            "applicability relation has unsupported fields")
    expected, report, pilot = _derive(inputs, relation["qualified_report_ref"], expected_pilot_binding_ref)
    require(relation == expected, "applicability relation differs from independently selected cold evidence")
    # _derive used the unchanged report verifier and original exact Conformance
    # class, accounting, warnings and cold source-closure validation once.
    inputs.recheck()
    return relation, report, pilot
