"""Independent read-only Guide requests, with no research-state side effects."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping

from research_workbench.adapters.models.port import (
    ContentBlock, DataPolicy, Message, ModelRequest, ModelResponse, ProviderRegistry,
)
from research_workbench.context.models import MainStatePacket
from research_workbench.entry.roles import (
    EntryInputError, ROLE_BASELINES, _reference, document_bytes, read_pinned_inputs,
)
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog


def build_guide_request(
    root: str | Path, *, question: str,
    main_state_ref: FileReference | Mapping[str, Any],
    approved_refs: Iterable[FileReference | Mapping[str, Any]] = (),
    stage_evidence_ref: FileReference | Mapping[str, Any] | None = None,
    verification_refs: Iterable[FileReference | Mapping[str, Any]] = (),
    model: str, max_output_tokens: int = 1024, data_policy: DataPolicy | None = None,
) -> ModelRequest:
    """Read approved snapshots; separately assess explicitly granted sources.

    A stage selector grants no read: its exact pin must also be approved.
    Verification refs grant source preflight only, never model snapshots. The
    MainState's visible machine refs grant neither kind of read automatically.
    """
    if not isinstance(question, str) or not question.strip():
        raise EntryInputError("Guide question must be nonempty")
    if not isinstance(model, str) or not model.strip():
        raise EntryInputError("Guide model must be explicit")
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise EntryInputError("Guide output limit must be positive")
    approved = tuple(approved_refs)
    verification = tuple(verification_refs)
    stage_ref = _reference(stage_evidence_ref) if stage_evidence_ref is not None else None
    if stage_ref is not None and stage_ref not in tuple(_reference(value) for value in approved):
        raise EntryInputError("Guide stage evidence requires an exact approved input pin")
    if verification and stage_ref is None:
        raise EntryInputError("Guide verification refs require stage evidence")
    snapshots = read_pinned_inputs(root, (main_state_ref, *approved))
    state = load_document_bytes(Path(snapshots[0]["path"]), snapshots[0]["text"].encode("utf-8"))
    errors = SchemaCatalog().validate("main_state", state)
    if errors:
        raise EntryInputError("invalid MainState: " + "; ".join(error.message for error in errors))
    MainStatePacket.from_mapping(state)
    policy = data_policy or DataPolicy(local_only=True)
    if policy.allow_provider_server_tools:
        raise EntryInputError("Guide cannot authorize provider server tools")
    baseline = ROLE_BASELINES["guide"]
    data: dict[str, Any] = {"question": question, "approved_inputs": snapshots}
    if stage_ref is not None:
        from research_workbench.entry.stage import assess_workflow_stage_evidence

        try:
            assessment = assess_workflow_stage_evidence(
                root, main_state_ref=main_state_ref, evidence_ref=stage_ref,
                verification_refs=verification,
            )
        except ValueError as exc:
            raise EntryInputError(str(exc)) from exc
        # The approved stage snapshot already contains the source-derived facts.
        # Send only their assessment boundary, not another copy of stages or
        # observation bodies. Verification originals never become snapshots.
        data["stage_evidence_assessment"] = {
            key: assessment[key] for key in (
                "status", "qualification", "source_ref", "checked_refs",
                "missing_verification_refs", "validation_scope", "limitations",
            ) if key in assessment
        }
    payload = document_bytes(data)
    return ModelRequest(
        model=model, max_output_tokens=max_output_tokens, tools=(), data_policy=policy,
        messages=(Message("system", (ContentBlock("text", text=baseline),)),
                  Message("user", (ContentBlock("text", text=payload.decode("utf-8")),))),
        metadata={"entry_role": "guide", "qualification": "independent-read-only-guide",
                  "baseline_sha256": hashlib.sha256(baseline.encode("utf-8")).hexdigest(),
                  "input_snapshot_sha256": hashlib.sha256(payload).hexdigest()},
    )


def ask_guide(
    root: str | Path, *, providers: ProviderRegistry, provider_name: str,
    question: str, main_state_ref: FileReference | Mapping[str, Any],
    approved_refs: Iterable[FileReference | Mapping[str, Any]] = (),
    stage_evidence_ref: FileReference | Mapping[str, Any] | None = None,
    verification_refs: Iterable[FileReference | Mapping[str, Any]] = (),
    model: str, max_output_tokens: int = 1024, data_policy: DataPolicy | None = None,
) -> ModelResponse:
    """One injected Provider call; return response/usage without sinks or writers.

    No ToolCall is ever executed, including unexpected calls in a response.
    Caller authorization of a remote provider/data policy is separate.
    """
    request = build_guide_request(root, question=question, main_state_ref=main_state_ref,
                                 approved_refs=approved_refs, stage_evidence_ref=stage_evidence_ref,
                                 verification_refs=verification_refs, model=model,
                                 max_output_tokens=max_output_tokens, data_policy=data_policy)
    return providers.require(provider_name, request).generate(request)
