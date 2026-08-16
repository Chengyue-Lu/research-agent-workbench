"""Conservative Zhipu standard Chat Completions API adapter.

GLM-5.3 requires enabled thinking for client-tool turns and requires the
provider-returned ``reasoning_content`` to be handed back unchanged.  The
provider-neutral port intentionally does not expose hidden reasoning, so this
adapter keeps the minimum continuation envelope in private, bounded memory.
One adapter instance is therefore single-Attempt state: callers must construct
a fresh instance per Attempt and discard it in ``finally``.
"""

from __future__ import annotations

import hashlib
import json
import math
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from research_workbench.adapters.models.base import (
    decode_strict_json_value,
    perform_json_request,
    preflight,
    provider_extension,
    raise_provider_http_error,
    reject_unknown_extension_keys,
    require_list,
    require_object,
    text_from_output,
    validate_adapter_capabilities,
    validate_response_contract,
)
from research_workbench.adapters.models.http import (
    CredentialProvider,
    HttpTransport,
    UrllibTransport,
)
from research_workbench.adapters.models.port import (
    Capability,
    ContentBlock,
    FinishReason,
    Message,
    ModelRequest,
    ModelResponse,
    ProviderCapabilities,
    ProviderError,
    ProviderErrorCategory,
    ToolCall,
    Usage,
)

ZHIPU_STANDARD_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
ZHIPU_MAX_OUTPUT_TOKENS = 131_072
ZHIPU_MAX_SCHEMA_INSTRUCTION_BYTES = 16_384
ZHIPU_REASONING_EFFORTS = frozenset({"low", "high", "max"})
ZHIPU_DEFAULT_CONTINUATION_TURNS = 3
ZHIPU_DEFAULT_CONTINUATION_BYTES = 262_144


@dataclass(slots=True, repr=False)
class _ContinuationTurn:
    assistant_sha256: str
    call_id: str
    name: str
    arguments_sha256: str
    native_assistant_json: bytes


@dataclass(slots=True, repr=False)
class _ContinuationState:
    control_sha256: str
    expected_prefix_count: int
    expected_prefix_sha256: str
    turns: tuple[_ContinuationTurn, ...]
    stored_bytes: int


@dataclass(slots=True, repr=False)
class _PendingContinuation:
    call_id: str
    name: str
    arguments_sha256: str
    native_assistant_json: bytes


class ZhipuChatCompletionsProvider:
    """One model-bound, single-active-Attempt Zhipu standard API adapter."""

    provider_name = "zhipu"
    adapter_version = "0.1.0"
    implemented_capabilities = frozenset(
        {
            Capability.TEXT,
            Capability.TOOLS,
            Capability.STRUCTURED_OUTPUT,
            Capability.REASONING,
        }
    )

    def __init__(
        self,
        *,
        model: str,
        credential: CredentialProvider,
        transport: HttpTransport | None = None,
        supported: frozenset[Capability] = frozenset({Capability.TEXT}),
        base_url: str = ZHIPU_STANDARD_BASE_URL,
        timeout_seconds: float = 60.0,
        max_retries: int = 0,
        default_reasoning_effort: str = "low",
        max_continuation_turns: int = ZHIPU_DEFAULT_CONTINUATION_TURNS,
        max_continuation_bytes: int = ZHIPU_DEFAULT_CONTINUATION_BYTES,
        regions: frozenset[str] = frozenset(),
        data_controls: frozenset[str] = frozenset(),
    ) -> None:
        if not model.strip():
            raise ValueError("Zhipu model must not be empty")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if isinstance(max_retries, bool) or max_retries != 0:
            raise ValueError("Zhipu adapter requires max_retries=0")
        if default_reasoning_effort not in ZHIPU_REASONING_EFFORTS:
            raise ValueError("Zhipu default_reasoning_effort must be low, high, or max")
        if (
            isinstance(max_continuation_turns, bool)
            or not isinstance(max_continuation_turns, int)
            or max_continuation_turns <= 0
        ):
            raise ValueError("max_continuation_turns must be a positive integer")
        if (
            isinstance(max_continuation_bytes, bool)
            or not isinstance(max_continuation_bytes, int)
            or max_continuation_bytes <= 0
        ):
            raise ValueError("max_continuation_bytes must be a positive integer")
        normalized_base_url = base_url.rstrip("/")
        if normalized_base_url != ZHIPU_STANDARD_BASE_URL:
            raise ValueError(
                "Zhipu adapter accepts only the standard API base URL; "
                "Coding Plan and compatible third-party endpoints are not interchangeable"
            )
        validate_adapter_capabilities(
            supported,
            self.implemented_capabilities,
            self.provider_name,
        )
        self.model = model
        self.credential = credential
        self.transport = transport or UrllibTransport()
        self.supported = supported
        self.base_url = normalized_base_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.default_reasoning_effort = default_reasoning_effort
        self.max_continuation_turns = max_continuation_turns
        self.max_continuation_bytes = max_continuation_bytes
        self.regions = regions
        self.data_controls = data_controls
        self._state_lock = threading.Lock()
        self._continuation: _ContinuationState | None = None

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} provider='zhipu' model={self.model!r} "
            f"continuation_active={self._continuation is not None}>"
        )

    def discard_ephemeral_continuation(self) -> None:
        """Drop the private reasoning handback chain without serializing it."""

        with self._state_lock:
            self._continuation = None

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider=self.provider_name,
            adapter_version=self.adapter_version,
            supported=self.supported,
            models=(self.model,),
            deployment="remote",
            regions=self.regions,
            limits={
                "max_retries": self.max_retries,
                "max_tool_calls_per_turn": 1,
                "max_continuation_turns": self.max_continuation_turns,
                "max_continuation_bytes": self.max_continuation_bytes,
                "default_reasoning_effort": self.default_reasoning_effort,
                "tool_choice": "auto-only",
                "session_scope": "single-active-attempt",
            },
            data_controls=self.data_controls,
            known_gaps=(
                "only one client function call per turn and tool_choice=auto are supported",
                "parallel tools, streaming, images, files, and server tools are not implemented",
                "json_schema requests use provider json_object mode and local JSON Schema validation",
                "tool-turn reasoning is retained only in bounded adapter-private memory and is never normalized",
                "one fresh adapter instance and explicit final discard are required per Attempt",
                "provider-reported currency cost is unavailable",
                "capability availability remains model/account specific and requires live conformance",
            ),
        )

    def generate(self, request: ModelRequest) -> ModelResponse:
        with self._state_lock:
            try:
                return self._generate_locked(request)
            except Exception:
                self._continuation = None
                raise

    def _generate_locked(self, request: ModelRequest) -> ModelResponse:
        preflight(request, self.capabilities())
        self._validate_sampling_controls(request)
        self._validate_tool_controls(request)
        extension = provider_extension(request, self.provider_name)
        reject_unknown_extension_keys(
            extension,
            provider=self.provider_name,
            allowed=frozenset(),
        )
        continuation_turns = self._prepare_continuation(request)
        payload = self._payload(request, continuation_turns)
        http_response, document = perform_json_request(
            provider=self.provider_name,
            transport=self.transport,
            credential=self.credential,
            url=f"{self.base_url}/chat/completions",
            headers={
                "Authorization": "Bearer {API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "research-agent-workbench/0.1",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )
        if http_response.status_code >= 400:
            self._raise_api_error(http_response.status_code, document)
        response, pending = self._parse_response(request, document)
        response = validate_response_contract(request, response)
        if pending is None:
            self._continuation = None
        else:
            self._install_continuation(request, response, pending)
        return response

    def _payload(
        self,
        request: ModelRequest,
        continuation_turns: tuple[_ContinuationTurn, ...],
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": request.model,
            "messages": self._messages(request, continuation_turns),
            "stream": False,
            "thinking": {"type": "enabled", "clear_thinking": False},
            "reasoning_effort": request.reasoning_effort or self.default_reasoning_effort,
        }
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": dict(tool.input_schema),
                    },
                }
                for tool in request.tools
            ]
            payload["tool_choice"] = "auto"
        if request.response_format.kind == "json_schema":
            # The standard Chat API exposes json_object, not strict
            # provider-side JSON Schema.  The shared response validator checks
            # the requested schema locally before the result can be consumed.
            payload["response_format"] = {"type": "json_object"}
        if request.max_output_tokens is not None:
            payload["max_tokens"] = request.max_output_tokens
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        return payload

    def _messages(
        self,
        request: ModelRequest,
        continuation_turns: tuple[_ContinuationTurn, ...],
    ) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = []
        if request.response_format.kind == "json_schema":
            assert isinstance(request.response_format.schema, Mapping)
            schema = json.dumps(
                request.response_format.schema,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            instruction = (
                "Return exactly one JSON object and no surrounding prose. "
                "The object must validate against this JSON Schema: "
                f"{schema}"
            )
            if len(instruction.encode("utf-8")) > ZHIPU_MAX_SCHEMA_INSTRUCTION_BYTES:
                raise ProviderError(
                    ProviderErrorCategory.INVALID_REQUEST,
                    "Zhipu structured-output schema instruction exceeds the bounded size",
                )
            messages.append({"role": "system", "content": instruction})
        continuation_index = 0
        for message in request.messages:
            if message.name is not None:
                raise ProviderError(
                    ProviderErrorCategory.UNSUPPORTED,
                    "Zhipu message names are not implemented by this adapter",
                )
            call_blocks = tuple(block for block in message.content if block.kind == "tool_call")
            if call_blocks:
                if message.role != "assistant" or len(call_blocks) != 1:
                    raise ProviderError(
                        ProviderErrorCategory.CONTRACT_VIOLATION,
                        "Zhipu continuation requires one assistant function call per turn",
                    )
                if continuation_index >= len(continuation_turns):
                    raise ProviderError(
                        ProviderErrorCategory.CONTRACT_VIOLATION,
                        "Zhipu continuation reasoning is unavailable for an assistant tool turn",
                    )
                turn = continuation_turns[continuation_index]
                if _message_sha256(message) != turn.assistant_sha256:
                    raise ProviderError(
                        ProviderErrorCategory.CONTRACT_VIOLATION,
                        "Zhipu assistant tool history differs from the private continuation chain",
                    )
                data = call_blocks[0].data or {}
                if (
                    data.get("call_id") != turn.call_id
                    or data.get("name") != turn.name
                    or _value_sha256(data.get("arguments")) != turn.arguments_sha256
                ):
                    raise ProviderError(
                        ProviderErrorCategory.CONTRACT_VIOLATION,
                        "Zhipu assistant tool identity differs from the private continuation chain",
                    )
                native = json.loads(turn.native_assistant_json)
                if not isinstance(native, dict):
                    raise ProviderError(
                        ProviderErrorCategory.CONTRACT_VIOLATION,
                        "Zhipu private continuation envelope is invalid",
                    )
                messages.append(native)
                continuation_index += 1
                continue

            if message.role == "tool":
                if len(message.content) != 1 or message.content[0].kind != "tool_result":
                    raise ProviderError(
                        ProviderErrorCategory.CONTRACT_VIOLATION,
                        "Zhipu tool messages require exactly one complete tool result",
                    )
                data = message.content[0].data or {}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": data["call_id"],
                        "content": text_from_output(data["output"]),
                    }
                )
                continue

            if message.role not in {"system", "user", "assistant"}:
                raise ProviderError(
                    ProviderErrorCategory.UNSUPPORTED,
                    f"Zhipu adapter cannot serialize message role: {message.role}",
                )
            parts: list[str] = []
            for block in message.content:
                if block.kind != "text":
                    raise ProviderError(
                        ProviderErrorCategory.UNSUPPORTED,
                        f"Zhipu adapter cannot serialize content block: {block.kind}",
                    )
                parts.append(block.text or "")
            messages.append({"role": message.role, "content": "\n".join(parts)})
        if continuation_index != len(continuation_turns):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu request omitted a turn from the private continuation chain",
            )
        return messages

    def _parse_response(
        self,
        request: ModelRequest,
        document: Mapping[str, object],
    ) -> tuple[ModelResponse, _PendingContinuation | None]:
        response_id = document.get("id")
        if not isinstance(response_id, str) or not response_id:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response lacks a non-empty id",
            )
        model = document.get("model")
        if not isinstance(model, str) or not model:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response lacks a non-empty model",
            )
        if model != request.model:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"Zhipu returned model {model!r} for exact request {request.model!r}",
            )

        choices = require_list(
            document.get("choices"),
            provider=self.provider_name,
            field="choices",
        )
        if len(choices) != 1:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response must contain exactly one choice",
            )
        choice = require_object(
            choices[0],
            provider=self.provider_name,
            field="choices[0]",
        )
        message = require_object(
            choice.get("message"),
            provider=self.provider_name,
            field="choices[0].message",
        )
        raw_calls = message.get("tool_calls")
        calls: tuple[ToolCall, ...] = ()
        pending: _PendingContinuation | None = None
        native_calls: list[dict[str, object]] = []
        if raw_calls is not None:
            call_values = require_list(
                raw_calls,
                provider=self.provider_name,
                field="choices[0].message.tool_calls",
            )
            if len(call_values) > 1:
                raise ProviderError(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    "Zhipu returned more than one function call in one turn",
                )
            if call_values:
                call, native_call = self._parse_tool_call(call_values[0])
                calls = (call,)
                native_calls.append(native_call)

        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu response message content must be text or null",
            )
        if not calls and not isinstance(content, str):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu terminal response message content must be text",
            )

        raw_finish = choice.get("finish_reason")
        if raw_finish == "tool_calls" and not calls:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu reported a tool-call finish without one function call",
            )
        if calls and raw_finish != "tool_calls":
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu returned a function call without the tool_calls finish reason",
            )
        finish_reason = (
            FinishReason.TOOL_CALL
            if calls
            else _FINISH_REASONS.get(raw_finish, FinishReason.UNKNOWN)
        )

        reasoning = message.get("reasoning_content")
        if calls:
            if not isinstance(reasoning, str):
                raise ProviderError(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    "Zhipu tool response lacks reasoning_content required for exact handback",
                )
            native_assistant = {
                "role": "assistant",
                "content": content,
                "reasoning_content": reasoning,
                "tool_calls": native_calls,
            }
            native_json = _canonical_json(native_assistant)
            call = calls[0]
            pending = _PendingContinuation(
                call_id=call.call_id,
                name=call.name,
                arguments_sha256=_value_sha256(call.arguments),
                native_assistant_json=native_json,
            )

        warnings: list[str] = []
        if request.metadata:
            warnings.append(
                "Canonical request metadata remained local and was not transmitted to Zhipu"
            )
        if request.response_format.kind == "json_schema":
            warnings.append(
                "Zhipu enforced json_object only; requested JSON Schema was validated locally"
            )
        usage, reported_total = self._usage(document.get("usage"))
        metadata: dict[str, Any] = {"finish_reason": raw_finish}
        if isinstance(document.get("created"), int) and not isinstance(
            document.get("created"), bool
        ):
            metadata["created"] = document["created"]
        if reported_total is not None:
            metadata["reported_total_tokens"] = reported_total
        output = (
            ()
            if finish_reason == FinishReason.REFUSAL
            else (
                (ContentBlock(kind="text", text=content),)
                if isinstance(content, str) and content
                else ()
            )
        )
        return (
            ModelResponse(
                response_id=response_id,
                provider=self.provider_name,
                model=model,
                output=output,
                finish_reason=finish_reason,
                tool_calls=calls,
                usage=usage,
                warnings=tuple(warnings),
                provider_metadata=metadata,
            ),
            pending,
        )

    def _parse_tool_call(
        self,
        value: object,
    ) -> tuple[ToolCall, dict[str, object]]:
        call = require_object(
            value,
            provider=self.provider_name,
            field="choices[0].message.tool_calls[0]",
        )
        if call.get("type") != "function" or "mcp" in call:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu returned a non-function or provider-hosted tool call",
            )
        call_id = call.get("id")
        function = require_object(
            call.get("function"),
            provider=self.provider_name,
            field="choices[0].message.tool_calls[0].function",
        )
        name = function.get("name")
        raw_arguments = function.get("arguments")
        if (
            not isinstance(call_id, str)
            or not call_id
            or not isinstance(name, str)
            or not name
            or not isinstance(raw_arguments, str)
        ):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu function call lacks id, name, or JSON arguments",
            )
        try:
            arguments = decode_strict_json_value(raw_arguments)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu function call arguments are not strict JSON",
            ) from exc
        if not isinstance(arguments, Mapping):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu function call arguments are not an object",
            )
        native = {
            "id": call_id,
            "type": "function",
            "function": {"name": name, "arguments": raw_arguments},
        }
        return ToolCall(call_id=call_id, name=name, arguments=dict(arguments)), native

    def _prepare_continuation(
        self,
        request: ModelRequest,
    ) -> tuple[_ContinuationTurn, ...]:
        state = self._continuation
        has_tool_history = any(
            block.kind in {"tool_call", "tool_result"}
            for message in request.messages
            for block in message.content
        )
        if state is None:
            if has_tool_history:
                raise ProviderError(
                    ProviderErrorCategory.CONTRACT_VIOLATION,
                    "Zhipu tool history has no private reasoning continuation",
                )
            return ()
        if _request_control_sha256(request) != state.control_sha256:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu continuation request controls differ from the active Attempt",
            )
        if len(request.messages) != state.expected_prefix_count + 1:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu continuation does not append exactly one complete tool-result message",
            )
        if _messages_sha256(request.messages[:-1]) != state.expected_prefix_sha256:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu continuation transcript differs from the active Attempt",
            )
        result_message = request.messages[-1]
        if (
            result_message.role != "tool"
            or result_message.name is not None
            or len(result_message.content) != 1
            or result_message.content[0].kind != "tool_result"
        ):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu continuation requires one complete tool-result message",
            )
        data = result_message.content[0].data
        last = state.turns[-1]
        if (
            not isinstance(data, Mapping)
            or set(data) != {"call_id", "name", "output", "is_error"}
            or data.get("call_id") != last.call_id
            or data.get("name") != last.name
            or not isinstance(data.get("is_error"), bool)
        ):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu tool result does not exactly match the pending function call",
            )
        return state.turns

    def _install_continuation(
        self,
        request: ModelRequest,
        response: ModelResponse,
        pending: _PendingContinuation,
    ) -> None:
        previous = self._continuation
        turns = previous.turns if previous is not None else ()
        if len(turns) + 1 > self.max_continuation_turns:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu continuation exceeds the bounded tool-turn count",
            )
        stored_bytes = (
            (previous.stored_bytes if previous is not None else 0)
            + len(pending.native_assistant_json)
        )
        if stored_bytes > self.max_continuation_bytes:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu continuation exceeds the bounded private-memory size",
            )
        assistant = Message(
            "assistant",
            (
                *response.output,
                ContentBlock(
                    kind="tool_call",
                    data={
                        "call_id": pending.call_id,
                        "name": pending.name,
                        "arguments": dict(response.tool_calls[0].arguments),
                    },
                ),
            ),
        )
        turn = _ContinuationTurn(
            assistant_sha256=_message_sha256(assistant),
            call_id=pending.call_id,
            name=pending.name,
            arguments_sha256=pending.arguments_sha256,
            native_assistant_json=pending.native_assistant_json,
        )
        expected_prefix = (*request.messages, assistant)
        self._continuation = _ContinuationState(
            control_sha256=(
                previous.control_sha256
                if previous is not None
                else _request_control_sha256(request)
            ),
            expected_prefix_count=len(expected_prefix),
            expected_prefix_sha256=_messages_sha256(expected_prefix),
            turns=(*turns, turn),
            stored_bytes=stored_bytes,
        )

    def _validate_tool_controls(self, request: ModelRequest) -> None:
        if request.tools and request.tool_choice.kind != "auto":
            raise ProviderError(
                ProviderErrorCategory.UNSUPPORTED,
                "Zhipu standard API supports only tool_choice=auto",
            )

    def _usage(self, value: object) -> tuple[Usage, int | None]:
        if value is None:
            return Usage(provider_reported_cost=None), None
        usage = require_object(value, provider=self.provider_name, field="usage")
        input_tokens = self._usage_integer(usage, "prompt_tokens")
        output_tokens = self._usage_integer(usage, "completion_tokens")
        total_tokens = self._usage_integer(usage, "total_tokens")
        details_value = usage.get("prompt_tokens_details")
        cached_tokens = None
        if details_value is not None:
            details = require_object(
                details_value,
                provider=self.provider_name,
                field="usage.prompt_tokens_details",
            )
            cached_tokens = self._usage_integer(
                details,
                "cached_tokens",
                path="usage.prompt_tokens_details.cached_tokens",
            )
        if (
            total_tokens is not None
            and input_tokens is not None
            and output_tokens is not None
            and total_tokens != input_tokens + output_tokens
        ):
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                "Zhipu usage.total_tokens does not equal prompt_tokens plus completion_tokens",
            )
        return (
            Usage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cached_input_tokens=cached_tokens,
                provider_reported_cost=None,
                currency=None,
            ),
            total_tokens,
        )

    def _usage_integer(
        self,
        value: Mapping[str, Any],
        field: str,
        *,
        path: str | None = None,
    ) -> int | None:
        raw = value.get(field)
        if raw is None:
            return None
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ProviderError(
                ProviderErrorCategory.CONTRACT_VIOLATION,
                f"Zhipu response field {path or f'usage.{field}'} must be a non-negative integer",
            )
        return raw

    def _validate_sampling_controls(self, request: ModelRequest) -> None:
        output_tokens = request.max_output_tokens
        if output_tokens is not None and (
            isinstance(output_tokens, bool)
            or not isinstance(output_tokens, int)
            or not 1 <= output_tokens <= ZHIPU_MAX_OUTPUT_TOKENS
        ):
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                f"Zhipu max_output_tokens must be an integer between 1 and {ZHIPU_MAX_OUTPUT_TOKENS}",
            )
        temperature = request.temperature
        if temperature is not None and (
            isinstance(temperature, bool)
            or not isinstance(temperature, (int, float))
            or not math.isfinite(float(temperature))
            or not 0 <= temperature <= 1
            or round(float(temperature), 2) != float(temperature)
        ):
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "Zhipu temperature must be between 0 and 1 with at most two decimal places",
            )
        if (
            request.reasoning_effort is not None
            and request.reasoning_effort not in ZHIPU_REASONING_EFFORTS
        ):
            raise ProviderError(
                ProviderErrorCategory.INVALID_REQUEST,
                "Zhipu reasoning_effort must be low, high, or max",
            )

    def _raise_api_error(
        self,
        status_code: int,
        document: Mapping[str, object],
    ) -> None:
        raw_error = document.get("error")
        error = raw_error if isinstance(raw_error, Mapping) else document
        raw_message = error.get("message") or error.get("msg")
        message = raw_message if isinstance(raw_message, str) else f"HTTP {status_code}"
        raw_code = error.get("code")
        provider_code = str(raw_code) if raw_code is not None else None
        override = None
        if provider_code in {"1000", "1001", "1002", "1003", "1004"}:
            override = ProviderErrorCategory.AUTHENTICATION
        elif provider_code in {
            "1110",
            "1111",
            "1112",
            "1113",
            "1121",
            "1220",
            "1309",
            "1311",
        }:
            override = ProviderErrorCategory.PERMISSION
        elif provider_code in {"1211", "1212", "1221", "1222"}:
            override = ProviderErrorCategory.UNSUPPORTED
        elif provider_code in {"1261", "context_length_exceeded", "max_tokens"}:
            override = ProviderErrorCategory.CONTEXT_LIMIT
        elif provider_code in {"1300", "1301", "content_filter", "safety"}:
            override = ProviderErrorCategory.SAFETY_REFUSAL
        elif provider_code == "1302":
            override = ProviderErrorCategory.RATE_LIMIT
        elif provider_code in {"1120", "1234", "500", "1305"}:
            override = ProviderErrorCategory.TRANSIENT
        elif provider_code in {"1304", "1308", "1310"}:
            raise ProviderError(
                ProviderErrorCategory.RATE_LIMIT,
                f"{self.provider_name} API request failed: {message}",
                retryable=False,
                status_code=status_code,
                provider_code=provider_code,
            )
        raise_provider_http_error(
            provider=self.provider_name,
            status_code=status_code,
            message=message,
            provider_code=provider_code,
            category_override=override,
        )


_FINISH_REASONS: dict[object, FinishReason] = {
    "stop": FinishReason.COMPLETE,
    "length": FinishReason.LENGTH,
    "content_filter": FinishReason.REFUSAL,
    "sensitive": FinishReason.REFUSAL,
    "network_error": FinishReason.ERROR,
    "model_context_window_exceeded": FinishReason.CONTEXT_LIMIT,
}


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProviderError(
            ProviderErrorCategory.INVALID_REQUEST,
            "Zhipu continuation controls must be canonical JSON values",
        ) from exc


def _value_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _block_mapping(block: ContentBlock) -> dict[str, object]:
    return {
        "kind": block.kind,
        "text": block.text,
        "data": dict(block.data) if isinstance(block.data, Mapping) else block.data,
        "mime_type": block.mime_type,
        "reference": block.reference,
    }


def _message_mapping(message: Message) -> dict[str, object]:
    return {
        "role": message.role,
        "name": message.name,
        "content": [_block_mapping(block) for block in message.content],
    }


def _message_sha256(message: Message) -> str:
    return _value_sha256(_message_mapping(message))


def _messages_sha256(messages: tuple[Message, ...]) -> str:
    return _value_sha256([_message_mapping(message) for message in messages])


def _request_control_sha256(request: ModelRequest) -> str:
    return _value_sha256(
        {
            "model": request.model,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": dict(tool.input_schema),
                    "strict": tool.strict,
                }
                for tool in request.tools
            ],
            "response_format": {
                "kind": request.response_format.kind,
                "name": request.response_format.name,
                "schema": (
                    dict(request.response_format.schema)
                    if isinstance(request.response_format.schema, Mapping)
                    else request.response_format.schema
                ),
            },
            "max_output_tokens": request.max_output_tokens,
            "temperature": request.temperature,
            "reasoning_effort": request.reasoning_effort,
            "capability_requirements": sorted(
                str(item) for item in request.capability_requirements
            ),
            "data_policy": {
                "local_only": request.data_policy.local_only,
                "zero_data_retention_required": request.data_policy.zero_data_retention_required,
                "training_opt_out_required": request.data_policy.training_opt_out_required,
                "allowed_regions": list(request.data_policy.allowed_regions),
                "allow_provider_server_tools": request.data_policy.allow_provider_server_tools,
            },
            "metadata": dict(request.metadata),
            "extensions": dict(request.extensions),
            "tool_choice": {
                "kind": request.tool_choice.kind,
                "name": request.tool_choice.name,
            },
        }
    )
