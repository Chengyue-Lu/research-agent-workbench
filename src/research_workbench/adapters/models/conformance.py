"""Bounded, content-redacted live conformance checks for model adapters.

The runner uses only fixed synthetic prompts. Reports retain control-plane
evidence, never prompt/response text, function arguments, credentials, or
provider response identifiers.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Sequence

from research_workbench.adapters.models.anthropic import AnthropicMessagesProvider
from research_workbench.adapters.models.configuration import ProviderAdapterConfig
from research_workbench.adapters.models.gemini import GeminiGenerateContentProvider
from research_workbench.adapters.models.http import EnvironmentCredential, HttpTransport
from research_workbench.adapters.models.openai import OpenAIResponsesProvider
from research_workbench.adapters.models.port import (
    Capability,
    ContentBlock,
    FinishReason,
    Message,
    ModelProvider,
    ModelRequest,
    ModelResponse,
    ProviderError,
    ResponseFormat,
    ToolChoice,
    ToolDefinition,
    Usage,
)
from research_workbench.adapters.models.zhipu_chat import ZhipuChatCompletionsProvider

CHECK_ORDER = ("text", "structured", "tools")
CHECK_CAPABILITIES = {
    "text": Capability.TEXT,
    "structured": Capability.STRUCTURED_OUTPUT,
    "tools": Capability.TOOLS,
}
MIN_OUTPUT_TOKENS = 16
MAX_OUTPUT_TOKENS = 256
MAX_CHECKS = len(CHECK_ORDER)


@dataclass(frozen=True, slots=True)
class ConformanceCheckResult:
    check: str
    status: str
    finish_reason: str | None = None
    output_kinds: tuple[str, ...] = ()
    tool_call_count: int = 0
    warnings_count: int = 0
    usage: Usage = Usage()
    error_category: str | None = None
    error_status_code: int | None = None
    error_retryable: bool | None = None
    failure_code: str | None = None

    def to_mapping(self) -> dict[str, object]:
        result: dict[str, object] = {
            "check": self.check,
            "status": self.status,
            "output_kinds": list(self.output_kinds),
            "tool_call_count": self.tool_call_count,
            "warnings_count": self.warnings_count,
        }
        optional: dict[str, object | None] = {
            "finish_reason": self.finish_reason,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cached_input_tokens": self.usage.cached_input_tokens,
            "reasoning_tokens": self.usage.reasoning_tokens,
            "error_category": self.error_category,
            "error_status_code": self.error_status_code,
            "error_retryable": self.error_retryable,
            "failure_code": self.failure_code,
        }
        result.update({key: value for key, value in optional.items() if value is not None})
        return result


@dataclass(frozen=True, slots=True)
class ConformanceBudgetRecord:
    max_provider_invocations: int
    max_output_tokens_per_invocation: int
    provider_invocations: int
    successful_responses: int
    elapsed_seconds: float


@dataclass(frozen=True, slots=True)
class ProviderConformanceReport:
    report_id: str
    adapter_id: str
    provider: str
    adapter_version: str
    execution_context: str
    requested_model: str
    observed_models: tuple[str, ...]
    started_at: str
    finished_at: str
    status: str
    checks: tuple[ConformanceCheckResult, ...]
    budget: ConformanceBudgetRecord
    limitations: tuple[str, ...]
    schema_version: str = "0.1.0"

    def to_mapping(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "report_id": self.report_id,
            "adapter_id": self.adapter_id,
            "provider": self.provider,
            "adapter_version": self.adapter_version,
            "execution_context": self.execution_context,
            "requested_model": self.requested_model,
            "observed_models": list(self.observed_models),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "checks": [check.to_mapping() for check in self.checks],
            "budget": {
                "max_provider_invocations": self.budget.max_provider_invocations,
                "max_output_tokens_per_invocation": self.budget.max_output_tokens_per_invocation,
                "provider_invocations": self.budget.provider_invocations,
                "successful_responses": self.budget.successful_responses,
                "elapsed_seconds": self.budget.elapsed_seconds,
            },
            "privacy": {
                "fixed_synthetic_prompts_only": True,
                "credential_values_stored": False,
                "request_content_stored": False,
                "response_content_stored": False,
                "provider_response_ids_stored": False,
                "tool_arguments_stored": False,
            },
            "limitations": list(self.limitations),
        }


def conformance_plan(
    config: ProviderAdapterConfig,
    *,
    checks: Sequence[str] | None = None,
    max_provider_invocations: int = MAX_CHECKS,
    max_output_tokens: int = 64,
) -> dict[str, object]:
    selected = normalize_checks(config, checks, max_provider_invocations, max_output_tokens)
    return {
        "mode": "dry-run",
        "adapter_id": config.adapter_id,
        "provider": config.provider,
        "adapter_enabled": config.enabled,
        "credential_source": f"env:{config.credential_env}",
        "model_source": f"env:{config.model_env}",
        "checks": list(selected),
        "budget": {
            "max_provider_invocations": max_provider_invocations,
            "max_output_tokens_per_invocation": max_output_tokens,
        },
        "environment_read": False,
        "network_requests": 0,
        "prompt_or_response_content_retained": False,
        "execute_requirements": [
            "use a local config with enabled: true",
            "pass --execute, --execution-context, and --output",
            "run in the intended real-user authorization context",
        ],
    }


def normalize_checks(
    config: ProviderAdapterConfig,
    checks: Sequence[str] | None,
    max_provider_invocations: int,
    max_output_tokens: int,
) -> tuple[str, ...]:
    selected = tuple(checks) if checks else tuple(
        check for check in CHECK_ORDER if CHECK_CAPABILITIES[check] in config.capabilities
    )
    if not selected:
        raise ValueError("at least one conformance check is required")
    if len(selected) != len(set(selected)):
        raise ValueError("conformance checks must not contain duplicates")
    unknown = sorted(set(selected) - set(CHECK_ORDER))
    if unknown:
        raise ValueError("unknown conformance checks: " + ", ".join(unknown))
    missing = [
        check for check in selected if CHECK_CAPABILITIES[check] not in config.capabilities
    ]
    if missing:
        raise ValueError(
            f"adapter {config.adapter_id!r} does not claim capabilities for checks: "
            + ", ".join(missing)
        )
    if not 1 <= max_provider_invocations <= MAX_CHECKS:
        raise ValueError(f"max_provider_invocations must be between 1 and {MAX_CHECKS}")
    if len(selected) > max_provider_invocations:
        raise ValueError("selected checks exceed max_provider_invocations")
    if not MIN_OUTPUT_TOKENS <= max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise ValueError(
            f"max_output_tokens must be between {MIN_OUTPUT_TOKENS} and {MAX_OUTPUT_TOKENS}"
        )
    return selected


def build_live_provider(
    config: ProviderAdapterConfig,
    *,
    transport: HttpTransport | None = None,
) -> ModelProvider:
    """Resolve only the non-secret model selector; API key stays deferred."""

    if not config.enabled:
        raise ValueError(
            f"adapter {config.adapter_id!r} is disabled; use a local config and set enabled: true"
        )
    model = os.environ.get(config.model_env)
    if not model:
        raise ValueError(f"model selector is unavailable from env:{config.model_env}")
    common: dict[str, Any] = {
        "model": model,
        "credential": EnvironmentCredential(config.credential_env),
        "supported": config.capabilities,
        "base_url": config.base_url,
    }
    if transport is not None:
        common["transport"] = transport
    if config.provider == "openai":
        return OpenAIResponsesProvider(**common)
    if config.provider == "anthropic":
        return AnthropicMessagesProvider(**common)
    if config.provider == "google":
        return GeminiGenerateContentProvider(**common)
    if config.provider == "zhipu":
        return ZhipuChatCompletionsProvider(**common)
    raise ValueError(f"unsupported provider adapter: {config.provider}")


def run_provider_conformance(
    provider: ModelProvider,
    *,
    adapter_id: str,
    execution_context: str,
    checks: Sequence[str],
    max_provider_invocations: int,
    max_output_tokens: int,
    tool_choice_override: ToolChoice | None = None,
    now: Callable[[], datetime] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> ProviderConformanceReport:
    if not execution_context.strip():
        raise ValueError("execution_context must be a non-empty human assertion")
    snapshot = provider.capabilities()
    if len(snapshot.models) != 1:
        raise ValueError("conformance provider must be bound to exactly one model")
    synthetic_config = ProviderAdapterConfig(
        adapter_id=adapter_id,
        provider=snapshot.provider,
        enabled=True,
        base_url="https://conformance.invalid",
        credential_env="CONFORMANCE_CREDENTIAL",
        model_env="CONFORMANCE_MODEL",
        capabilities=snapshot.supported,
        live_conformance="pending",
    )
    selected = normalize_checks(
        synthetic_config,
        checks,
        max_provider_invocations,
        max_output_tokens,
    )
    current_time = now or (lambda: datetime.now(timezone.utc))
    started = current_time()
    start_tick = monotonic()
    results: list[ConformanceCheckResult] = []
    observed_models: list[str] = []
    invocations = 0
    successful = 0
    stopped = False

    for check in selected:
        if stopped:
            results.append(ConformanceCheckResult(check=check, status="not-run", failure_code="prior_failure"))
            continue
        request = _request_for(
            check,
            snapshot.models[0],
            max_output_tokens,
            tool_choice_override=tool_choice_override,
        )
        invocations += 1
        try:
            response = provider.generate(request)
        except ProviderError as exc:
            results.append(
                ConformanceCheckResult(
                    check=check,
                    status="failed",
                    error_category=str(exc.category),
                    error_status_code=exc.status_code,
                    error_retryable=exc.retryable,
                    failure_code="provider_error",
                )
            )
            stopped = True
            continue
        successful += 1
        if response.model not in observed_models:
            observed_models.append(response.model)
        result = _evaluate(check, response, expected_provider=snapshot.provider)
        results.append(result)
        if result.status != "passed":
            stopped = True

    finished = current_time()
    elapsed = max(0.0, monotonic() - start_tick)
    status = "passed" if all(item.status == "passed" for item in results) else "failed"
    limitations = [
        "Fixed synthetic prompts only; this report does not measure research quality.",
        "No prompt, response content, tool arguments, credential, or provider response ID is retained.",
        "Provider token fields are recorded when reported, but monetary cost is not inferred.",
    ]
    if stopped:
        limitations.append("Execution stopped after the first failed check to preserve the request budget.")
    if any(
        item.status == "passed"
        and (item.usage.input_tokens is None or item.usage.output_tokens is None)
        for item in results
    ):
        limitations.append("At least one successful response did not report complete input/output usage.")
    return ProviderConformanceReport(
        report_id=f"PCR-{uuid.uuid4().hex}",
        adapter_id=adapter_id,
        provider=snapshot.provider,
        adapter_version=snapshot.adapter_version,
        execution_context=execution_context.strip(),
        requested_model=snapshot.models[0],
        observed_models=tuple(observed_models),
        started_at=_timestamp(started),
        finished_at=_timestamp(finished),
        status=status,
        checks=tuple(results),
        budget=ConformanceBudgetRecord(
            max_provider_invocations=max_provider_invocations,
            max_output_tokens_per_invocation=max_output_tokens,
            provider_invocations=invocations,
            successful_responses=successful,
            elapsed_seconds=round(elapsed, 6),
        ),
        limitations=tuple(limitations),
    )


def _request_for(
    check: str,
    model: str,
    max_output_tokens: int,
    *,
    tool_choice_override: ToolChoice | None = None,
) -> ModelRequest:
    system = Message(
        "system",
        (
            ContentBlock(
                kind="text",
                text=(
                    "This is a fixed synthetic API conformance probe. Do not use external knowledge, "
                    "tools other than those supplied, or sensitive data."
                ),
            ),
        ),
    )
    if check == "text":
        return ModelRequest(
            model=model,
            messages=(system, Message("user", (ContentBlock(kind="text", text="Reply with OK."),))),
            max_output_tokens=max_output_tokens,
        )
    if check == "structured":
        schema = {
            "type": "object",
            "properties": {"ok": {"const": True}},
            "required": ["ok"],
            "additionalProperties": False,
        }
        return ModelRequest(
            model=model,
            messages=(
                system,
                Message("user", (ContentBlock(kind="text", text="Return the requested conformance object."),)),
            ),
            response_format=ResponseFormat(kind="json_schema", name="rwb_conformance", schema=schema),
            max_output_tokens=max_output_tokens,
        )
    if check == "tools":
        tool = ToolDefinition(
            name="rwb_conformance_echo",
            description="Return a fixed synthetic probe value; used only to verify client tool-call shape.",
            input_schema={
                "type": "object",
                "properties": {"value": {"const": "probe"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            strict=True,
        )
        return ModelRequest(
            model=model,
            messages=(
                system,
                Message(
                    "user",
                    (ContentBlock(kind="text", text="Call the supplied conformance tool with its probe value."),),
                ),
            ),
            tools=(tool,),
            tool_choice=(
                tool_choice_override
                if tool_choice_override is not None
                else ToolChoice(kind="specific", name=tool.name)
            ),
            max_output_tokens=max_output_tokens,
        )
    raise ValueError(f"unknown conformance check: {check}")


def _evaluate(check: str, response: ModelResponse, *, expected_provider: str) -> ConformanceCheckResult:
    common = {
        "check": check,
        "finish_reason": str(response.finish_reason),
        "output_kinds": tuple(block.kind for block in response.output),
        "tool_call_count": len(response.tool_calls),
        "warnings_count": len(response.warnings),
        "usage": response.usage,
    }
    if response.provider != expected_provider:
        return ConformanceCheckResult(status="failed", failure_code="provider_mismatch", **common)
    if check in {"text", "structured"}:
        acceptable = response.finish_reason in {FinishReason.COMPLETE, FinishReason.STOP}
        has_text = any(block.kind == "text" and bool(block.text) for block in response.output)
        if not acceptable:
            return ConformanceCheckResult(status="failed", failure_code="unexpected_finish", **common)
        if not has_text:
            return ConformanceCheckResult(status="failed", failure_code="missing_text", **common)
        if check == "structured":
            text = "".join(block.text or "" for block in response.output if block.kind == "text")
            try:
                value = json.loads(text)
            except json.JSONDecodeError:
                return ConformanceCheckResult(status="failed", failure_code="invalid_json", **common)
            if value != {"ok": True}:
                return ConformanceCheckResult(status="failed", failure_code="wrong_structured_value", **common)
        return ConformanceCheckResult(status="passed", **common)
    if check == "tools":
        if response.finish_reason != FinishReason.TOOL_CALL:
            return ConformanceCheckResult(status="failed", failure_code="missing_tool_finish", **common)
        if not response.tool_calls:
            return ConformanceCheckResult(status="failed", failure_code="missing_tool_call", **common)
        if any(call.name != "rwb_conformance_echo" for call in response.tool_calls):
            return ConformanceCheckResult(status="failed", failure_code="wrong_tool", **common)
        if any(dict(call.arguments) != {"value": "probe"} for call in response.tool_calls):
            return ConformanceCheckResult(status="failed", failure_code="wrong_tool_arguments", **common)
        return ConformanceCheckResult(status="passed", **common)
    raise ValueError(f"unknown conformance check: {check}")


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
