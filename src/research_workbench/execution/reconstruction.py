"""Rebuild the last persisted provider request from an Attempt trace.

The trace validator already proves structural integrity; this module makes the
``model-visible ⟺ recorded`` invariant executable by reconstructing the exact
:class:`ModelRequest` from the persisted message and binding it to the hashes
recorded at write time.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from research_workbench.adapters.models.port import (
    Capability,
    ContentBlock,
    DataPolicy,
    Message,
    ModelRequest,
    ResponseFormat,
    ToolChoice,
    ToolDefinition,
)
from research_workbench.artifacts.integrity import hash_file
from research_workbench.observability.trace import TRACE_INDEX_FILENAME


class TraceReconstructionError(ValueError):
    """The persisted trace cannot yield a hash-verified provider request."""


@dataclass(frozen=True, slots=True)
class ReconstructedRequest:
    request: ModelRequest
    message_id: str
    message_path: str
    content_sha256: str
    file_sha256: str


def reconstruct_last_provider_request(
    attempt_dir: str | Path,
    *,
    root: str | Path | None = None,
) -> ReconstructedRequest:
    """Return the last ``provider-request`` in the trace, verified against its hashes.

    Every failure mode (missing message, whole-file hash mismatch, envelope
    separator damage, content hash mismatch, malformed payload) raises
    :class:`TraceReconstructionError`; reconstruction never silently degrades.
    """

    raw = Path(attempt_dir)
    directory = raw if raw.is_absolute() else Path(root or ".") / raw
    directory = directory.resolve()

    try:
        index_document = yaml.safe_load((directory / TRACE_INDEX_FILENAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise TraceReconstructionError(f"trace index is unreadable: {exc}") from exc
    if not isinstance(index_document, Mapping):
        raise TraceReconstructionError("trace index is not an object")

    entries = index_document.get("messages", [])
    provider_requests = [
        entry
        for entry in entries
        if isinstance(entry, Mapping) and entry.get("kind") == "provider-request"
    ]
    if not provider_requests:
        raise TraceReconstructionError("trace contains no provider-request message")
    entry = provider_requests[-1]

    relative = str(entry.get("path", ""))
    message_path = directory / relative
    try:
        content = message_path.read_bytes()
    except OSError as exc:
        raise TraceReconstructionError(f"provider-request message is unreadable: {exc}") from exc

    file_sha256 = hash_file(message_path)
    recorded_file_sha = str(entry.get("sha256", ""))
    if file_sha256 != recorded_file_sha:
        raise TraceReconstructionError(
            f"provider-request message file hash mismatch: index {recorded_file_sha} != file {file_sha256}"
        )

    if not content.startswith(b"---\n"):
        raise TraceReconstructionError("provider-request message lacks an envelope header")
    header_bytes, separator, body_with_newline = content[4:].partition(b"---\n")
    if not separator:
        raise TraceReconstructionError("provider-request message lacks the envelope separator")
    body_bytes = body_with_newline[:-1] if body_with_newline.endswith(b"\n") else body_with_newline

    try:
        envelope = yaml.safe_load(header_bytes)
    except yaml.YAMLError as exc:
        raise TraceReconstructionError(f"provider-request envelope is invalid YAML: {exc}") from exc
    if not isinstance(envelope, Mapping):
        raise TraceReconstructionError("provider-request envelope is not an object")

    content_sha256 = str(envelope.get("content_sha256", ""))
    recomputed = hashlib.sha256(body_bytes).hexdigest()
    if content_sha256 != recomputed:
        raise TraceReconstructionError(
            f"provider-request content hash mismatch: envelope {content_sha256} != body {recomputed}"
        )

    try:
        document = json.loads(body_bytes)
    except json.JSONDecodeError as exc:
        raise TraceReconstructionError(f"provider-request body is not valid JSON: {exc}") from exc
    if not isinstance(document, Mapping) or not isinstance(document.get("request"), Mapping):
        raise TraceReconstructionError("provider-request body lacks a request object")

    request = _model_request_from_mapping(document["request"])
    return ReconstructedRequest(
        request=request,
        message_id=str(envelope.get("message_id", "")),
        message_path=relative,
        content_sha256=content_sha256,
        file_sha256=file_sha256,
    )


def _model_request_from_mapping(payload: Mapping[str, Any]) -> ModelRequest:
    try:
        return ModelRequest(
            model=str(payload["model"]),
            messages=tuple(
                Message(
                    role=str(message["role"]),
                    content=tuple(
                        ContentBlock(
                            kind=str(block["kind"]),
                            text=block.get("text"),
                            data=block.get("data"),
                            mime_type=block.get("mime_type"),
                            reference=block.get("reference"),
                        )
                        for block in message.get("content", ())
                    ),
                    name=message.get("name"),
                )
                for message in payload.get("messages", ())
            ),
            tools=tuple(
                ToolDefinition(
                    name=str(tool["name"]),
                    description=str(tool["description"]),
                    input_schema=dict(tool["input_schema"]),
                    strict=bool(tool.get("strict", True)),
                )
                for tool in payload.get("tools", ())
            ),
            response_format=_response_format(payload.get("response_format")),
            max_output_tokens=payload.get("max_output_tokens"),
            temperature=payload.get("temperature"),
            reasoning_effort=payload.get("reasoning_effort"),
            capability_requirements=frozenset(
                Capability(str(value)) for value in payload.get("capability_requirements", ())
            ),
            data_policy=_data_policy(payload.get("data_policy")),
            metadata=dict(payload.get("metadata", {})),
            extensions=dict(payload.get("extensions", {})),
            tool_choice=_tool_choice(payload.get("tool_choice")),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise TraceReconstructionError(f"provider-request payload does not match ModelRequest: {exc}") from exc


def _response_format(value: Any) -> ResponseFormat:
    if not isinstance(value, Mapping):
        return ResponseFormat()
    return ResponseFormat(
        kind=str(value.get("kind", "text")),
        name=value.get("name"),
        schema=value.get("schema"),
    )


def _data_policy(value: Any) -> DataPolicy:
    if not isinstance(value, Mapping):
        return DataPolicy()
    return DataPolicy(
        local_only=bool(value.get("local_only", False)),
        zero_data_retention_required=bool(value.get("zero_data_retention_required", False)),
        training_opt_out_required=bool(value.get("training_opt_out_required", False)),
        allowed_regions=tuple(value.get("allowed_regions", ())),
        allow_provider_server_tools=bool(value.get("allow_provider_server_tools", False)),
    )


def _tool_choice(value: Any) -> ToolChoice:
    if not isinstance(value, Mapping):
        return ToolChoice()
    return ToolChoice(kind=str(value.get("kind", "auto")), name=value.get("name"))
