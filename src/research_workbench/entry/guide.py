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
    EntryInputError, ROLE_BASELINES, document_bytes, read_pinned_inputs,
)
from research_workbench.io import load_document_bytes
from research_workbench.tasks.models import FileReference
from research_workbench.validation.schemas import SchemaCatalog


def build_guide_request(
    root: str | Path, *, question: str,
    main_state_ref: FileReference | Mapping[str, Any],
    approved_refs: Iterable[FileReference | Mapping[str, Any]] = (),
    model: str, max_output_tokens: int = 1024, data_policy: DataPolicy | None = None,
) -> ModelRequest:
    """Only MainState and explicitly granted necessary refs; never follow links."""
    if not isinstance(question, str) or not question.strip():
        raise EntryInputError("Guide question must be nonempty")
    if not isinstance(model, str) or not model.strip():
        raise EntryInputError("Guide model must be explicit")
    if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise EntryInputError("Guide output limit must be positive")
    snapshots = read_pinned_inputs(root, (main_state_ref, *tuple(approved_refs)))
    state = load_document_bytes(Path(snapshots[0]["path"]), snapshots[0]["text"].encode("utf-8"))
    errors = SchemaCatalog().validate("main_state", state)
    if errors:
        raise EntryInputError("invalid MainState: " + "; ".join(error.message for error in errors))
    MainStatePacket.from_mapping(state)
    policy = data_policy or DataPolicy(local_only=True)
    if policy.allow_provider_server_tools:
        raise EntryInputError("Guide cannot authorize provider server tools")
    baseline = ROLE_BASELINES["guide"]
    payload = document_bytes({"question": question, "approved_inputs": snapshots})
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
    model: str, max_output_tokens: int = 1024, data_policy: DataPolicy | None = None,
) -> ModelResponse:
    """One injected Provider call; return response/usage without sinks or writers.

    No ToolCall is ever executed, including unexpected calls in a response.
    Caller authorization of a remote provider/data policy is separate.
    """
    request = build_guide_request(root, question=question, main_state_ref=main_state_ref,
                                 approved_refs=approved_refs, model=model,
                                 max_output_tokens=max_output_tokens, data_policy=data_policy)
    return providers.require(provider_name, request).generate(request)
