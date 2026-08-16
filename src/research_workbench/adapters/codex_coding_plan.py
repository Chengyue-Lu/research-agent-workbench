"""Offline contract for a future Codex Coding Plan Runtime using GLM-5.3.

This module freezes the command, environment, JSONL, and attestation boundaries
for an optional native-agent runtime.  It deliberately ships without a live
process host: the default runner fails closed before reading a credential.  A
live host still needs incremental output limits, Windows process-tree
containment, binary identity verification, and a reviewed egress policy.

It is not a ``ModelProvider`` implementation and does not close the
project-level K-API-2 Gate.  It does not create or mutate Assignment, Trace,
Receipt, Handoff, or Main State objects.  A caller may consume a result from a
trusted injected test boundary only after applying those shared contracts
outside this adapter.

The Codex JSONL surface reports the requested run and token usage, but does not
positively attest the serving provider or actual model.  The result therefore
keeps those identities unknown even though the request is fixed to GLM-5.3.
"""

from __future__ import annotations

import json
import math
import os
import re
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

CODEX_CODING_PLAN_RUNTIME_ID = "codex-coding-plan"
CODEX_CODING_PLAN_PROVIDER_ID = "zhipu_coding_plan"
CODEX_CODING_PLAN_MODEL = "glm-5.3"
CODEX_CODING_PLAN_BASE_URL = "https://open.bigmodel.cn/api/v1"
CODEX_CODING_PLAN_WIRE_API = "responses"
CODEX_CODING_PLAN_REASONING_EFFORT = "low"
CODEX_CODING_PLAN_CLI_VERSION = "0.124.0"
CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV = "RWB_CODEX_CODING_PLAN_CREDENTIAL"
CODEX_CODING_PLAN_LIVE_READY = False
CODEX_CODING_PLAN_ALLOWED_SOURCE_CREDENTIAL_ENVS = frozenset(
    {
        "ZHIPU_API_KEY",
        "RWB_ZHIPU_API_KEY",
        "RWB_CODEX_CODING_PLAN_KEY",
    }
)

CODEX_CODING_PLAN_DISABLED_FEATURES = (
    "shell_tool",
    "multi_agent",
    "browser_use",
    "computer_use",
    "apps",
    "plugins",
    "image_generation",
    "in_app_browser",
    "codex_hooks",
    "skill_mcp_dependency_install",
    "workspace_dependencies",
)

CODEX_CODING_PLAN_MAX_TOTAL_TOKENS = 5_000
CODEX_CODING_PLAN_MAX_OUTPUT_TOKENS = 1_024
CODEX_CODING_PLAN_MAX_PROMPT_BYTES = 65_536
CODEX_CODING_PLAN_MAX_JSONL_EVENTS = 64
CODEX_CODING_PLAN_MAX_JSONL_BYTES = 1_048_576
CODEX_CODING_PLAN_MAX_JSONL_LINE_BYTES = 262_144
CODEX_CODING_PLAN_MAX_STDERR_BYTES = 65_536
CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS = 120.0
CODEX_CODING_PLAN_STREAM_IDLE_TIMEOUT_MS = 30_000

# Single-model compatibility projection of the metadata published in the
# Zhipu GLM Coding Plan Codex guide.  Codex 0.124 cannot parse the newer
# ``max`` reasoning enum, so this fixed-low runtime advertises only the
# published levels that 0.124 can represent.  The Runtime also understates
# parallel/apply-patch capability because neither is authorized by this
# no-write transport contract.  The catalog contains no credential or
# machine-specific value.
CODEX_CODING_PLAN_MODEL_CATALOG = {
    "models": [
        {
            "slug": "glm-5.3",
            "display_name": "glm-5.3",
            "description": "Z.ai's latest flagship model",
            "default_reasoning_level": "low",
            "supported_reasoning_levels": [
                {"effort": "low", "description": "Light reasoning"},
                {"effort": "high", "description": "Enhanced reasoning"},
            ],
            "shell_type": "shell_command",
            "visibility": "list",
            "supported_in_api": True,
            "priority": 0,
            "base_instructions": "",
            "supports_reasoning_summaries": True,
            "default_reasoning_summary": "none",
            "support_verbosity": False,
            "truncation_policy": {"mode": "bytes", "limit": 10_000},
            "context_window": 1_048_576,
            "max_context_window": 1_048_576,
            "effective_context_window_percent": 95,
            "supports_parallel_tool_calls": False,
            "experimental_supported_tools": [],
            "input_modalities": ["text"],
        }
    ]
}
_CODEX_CODING_PLAN_MODEL_CATALOG_JSON = (
    json.dumps(
        CODEX_CODING_PLAN_MODEL_CATALOG,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    + "\n"
)
_CODEX_CODING_PLAN_MODEL_CATALOG_MAX_BYTES = 65_536

CODEX_CODING_PLAN_ATTESTATION_LIMITATIONS = (
    "Codex exec JSONL does not positively attest the serving provider or actual model.",
    "The requested glm-5.3 slot is configuration evidence only; actual model identity is unknown.",
    "This Coding Plan Runtime result is not a ModelProvider result or a project-level K-API-2 Gate.",
    "Token ceilings are validated after Codex reports usage; they are not provider-side spend caps.",
    "Codex JSONL does not report provider currency cost or Coding Plan billed points.",
    "Codex 0.124 still advertises local tools; the current contract does not authorize live dispatch.",
    "The repository process host is intentionally disabled until live isolation checks are implemented.",
)

_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_WINDOWS_SYSTEM_ENVIRONMENT = ("SYSTEMROOT", "WINDIR")


class CodexCodingPlanRuntimeError(RuntimeError):
    """A safe, stable runtime failure that never contains provider output."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class CodexCodingPlanLimits:
    """Parser/capture ceilings plus post-observation token ceilings."""

    max_total_tokens: int = CODEX_CODING_PLAN_MAX_TOTAL_TOKENS
    max_output_tokens: int = CODEX_CODING_PLAN_MAX_OUTPUT_TOKENS
    max_prompt_bytes: int = CODEX_CODING_PLAN_MAX_PROMPT_BYTES
    max_jsonl_events: int = CODEX_CODING_PLAN_MAX_JSONL_EVENTS
    max_jsonl_bytes: int = CODEX_CODING_PLAN_MAX_JSONL_BYTES
    max_jsonl_line_bytes: int = CODEX_CODING_PLAN_MAX_JSONL_LINE_BYTES
    max_stderr_bytes: int = CODEX_CODING_PLAN_MAX_STDERR_BYTES
    timeout_seconds: float = CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS

    def __post_init__(self) -> None:
        _bounded_positive_int(
            "max_total_tokens",
            self.max_total_tokens,
            CODEX_CODING_PLAN_MAX_TOTAL_TOKENS,
        )
        _bounded_positive_int(
            "max_output_tokens",
            self.max_output_tokens,
            CODEX_CODING_PLAN_MAX_OUTPUT_TOKENS,
        )
        _bounded_positive_int(
            "max_prompt_bytes",
            self.max_prompt_bytes,
            CODEX_CODING_PLAN_MAX_PROMPT_BYTES,
        )
        _bounded_positive_int(
            "max_jsonl_events",
            self.max_jsonl_events,
            CODEX_CODING_PLAN_MAX_JSONL_EVENTS,
        )
        _bounded_positive_int(
            "max_jsonl_bytes",
            self.max_jsonl_bytes,
            CODEX_CODING_PLAN_MAX_JSONL_BYTES,
        )
        _bounded_positive_int(
            "max_jsonl_line_bytes",
            self.max_jsonl_line_bytes,
            CODEX_CODING_PLAN_MAX_JSONL_LINE_BYTES,
        )
        _bounded_positive_int(
            "max_stderr_bytes",
            self.max_stderr_bytes,
            CODEX_CODING_PLAN_MAX_STDERR_BYTES,
        )
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
            or self.timeout_seconds > CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS
        ):
            raise ValueError("timeout_seconds must be within the fixed runtime ceiling")


@dataclass(frozen=True, slots=True)
class CodexCodingPlanUsage:
    """Token counters reported by the terminal Codex JSONL event."""

    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int

    @property
    def total_tokens(self) -> int:
        """Return billable-shape total without double-counting cached/reasoning subsets."""

        return self.input_tokens + self.output_tokens


@dataclass(frozen=True, slots=True)
class CodexCodingPlanRunResult:
    """Validated observation from a trusted injected process boundary."""

    status: Literal["transport-completed", "runtime-failed"]
    terminal_event: str
    failure_code: str | None
    thread_id: str | None
    final_message: str | None
    usage: CodexCodingPlanUsage | None
    event_count: int
    capture_complete: bool = True
    live_ready: bool = CODEX_CODING_PLAN_LIVE_READY
    requested_model: str = CODEX_CODING_PLAN_MODEL
    actual_model: None = None
    actual_provider: None = None
    model_identity_verified: bool = False
    limitations: tuple[str, ...] = CODEX_CODING_PLAN_ATTESTATION_LIMITATIONS


@dataclass(frozen=True, slots=True)
class CodexCodingPlanProcessResult:
    """Minimal process boundary used by the injectable runner."""

    returncode: int
    stdout: str
    stderr: str


class CodexCodingPlanProcessRunner(Protocol):
    """Injectable process boundary; tests can implement it without networking."""

    def __call__(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: Mapping[str, str],
        stdin: str,
        timeout_seconds: float,
    ) -> CodexCodingPlanProcessResult: ...


def build_codex_coding_plan_command(
    *,
    isolated_workspace: str | Path,
    model_catalog_json: str | Path,
    codex_executable: str | Path,
) -> tuple[str, ...]:
    """Build the immutable, no-secret ``codex exec`` command for GLM-5.3."""

    workspace = _resolve_isolated_workspace(isolated_workspace)
    model_catalog = _resolve_official_model_catalog(model_catalog_json)
    executable = _resolve_native_codex_executable(codex_executable)

    provider_prefix = f"model_providers.{CODEX_CODING_PLAN_PROVIDER_ID}"
    config_overrides = (
        f'model_provider="{CODEX_CODING_PLAN_PROVIDER_ID}"',
        f'model_reasoning_effort="{CODEX_CODING_PLAN_REASONING_EFFORT}"',
        f"model_catalog_json={_toml_string(model_catalog.as_posix())}",
        'approval_policy="never"',
        'history.persistence="none"',
        "analytics.enabled=false",
        "feedback.enabled=false",
        'otel.exporter="none"',
        'otel.metrics_exporter="none"',
        'otel.trace_exporter="none"',
        "otel.log_user_prompt=false",
        "allow_login_shell=false",
        "hide_agent_reasoning=true",
        "show_raw_agent_reasoning=false",
        'shell_environment_policy.inherit="none"',
        'web_search="disabled"',
        "tools.web_search=false",
        "tools.view_image=false",
        f'{provider_prefix}.name="Zhipu GLM Coding Plan"',
        f'{provider_prefix}.base_url="{CODEX_CODING_PLAN_BASE_URL}"',
        f'{provider_prefix}.env_key="{CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV}"',
        f'{provider_prefix}.wire_api="{CODEX_CODING_PLAN_WIRE_API}"',
        f"{provider_prefix}.request_max_retries=0",
        f"{provider_prefix}.stream_max_retries=0",
        f"{provider_prefix}.stream_idle_timeout_ms={CODEX_CODING_PLAN_STREAM_IDLE_TIMEOUT_MS}",
        f"{provider_prefix}.requires_openai_auth=false",
        f"{provider_prefix}.supports_standalone_web_search=false",
        f"{provider_prefix}.supports_websockets=false",
    )

    command = [
        executable,
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--cd",
        os.fspath(workspace),
        "--model",
        CODEX_CODING_PLAN_MODEL,
    ]
    for override in config_overrides:
        command.extend(("--config", override))
    for feature in CODEX_CODING_PLAN_DISABLED_FEATURES:
        command.extend(("--disable", feature))
    command.append("-")
    return tuple(command)


def parse_codex_coding_plan_jsonl(
    payload: str,
    *,
    limits: CodexCodingPlanLimits | None = None,
) -> CodexCodingPlanRunResult:
    """Parse the narrow no-tool Codex JSONL protocol with one terminal outcome."""

    active_limits = limits or CodexCodingPlanLimits()
    if not isinstance(payload, str):
        raise CodexCodingPlanRuntimeError("jsonl-not-text")
    if _utf8_size(payload, "jsonl-invalid-encoding") > active_limits.max_jsonl_bytes:
        raise CodexCodingPlanRuntimeError("jsonl-byte-limit-exceeded")

    lines = payload.splitlines()
    if not lines:
        raise CodexCodingPlanRuntimeError("jsonl-empty")
    if len(lines) > active_limits.max_jsonl_events:
        raise CodexCodingPlanRuntimeError("jsonl-event-limit-exceeded")

    thread_id: str | None = None
    thread_started = False
    turn_started = False
    final_message: str | None = None
    usage: CodexCodingPlanUsage | None = None
    terminal_event: str | None = None
    item_error_seen = False
    error_seen = False

    for line in lines:
        if not line.strip():
            raise CodexCodingPlanRuntimeError("jsonl-blank-record")
        if (
            _utf8_size(line, "jsonl-invalid-encoding")
            > active_limits.max_jsonl_line_bytes
        ):
            raise CodexCodingPlanRuntimeError("jsonl-line-limit-exceeded")
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, UnicodeError):
            raise CodexCodingPlanRuntimeError("jsonl-invalid-record") from None
        if not isinstance(event, dict):
            raise CodexCodingPlanRuntimeError("jsonl-record-not-object")
        event_type = event.get("type")
        if not isinstance(event_type, str) or not event_type:
            raise CodexCodingPlanRuntimeError("jsonl-event-type-invalid")
        if terminal_event is not None:
            raise CodexCodingPlanRuntimeError("jsonl-multiple-terminal-events")
        if error_seen and event_type != "turn.failed":
            raise CodexCodingPlanRuntimeError("jsonl-event-after-error")

        if event_type == "thread.started":
            if thread_started or turn_started:
                raise CodexCodingPlanRuntimeError("jsonl-thread-order-invalid")
            candidate = event.get("thread_id")
            if not isinstance(candidate, str) or not candidate.strip():
                raise CodexCodingPlanRuntimeError("jsonl-thread-id-invalid")
            thread_id = candidate
            thread_started = True
        elif event_type == "turn.started":
            if not thread_started or turn_started:
                raise CodexCodingPlanRuntimeError("jsonl-turn-order-invalid")
            turn_started = True
        elif event_type == "item.completed":
            item = event.get("item")
            if not isinstance(item, dict):
                raise CodexCodingPlanRuntimeError("jsonl-item-type-unsupported")
            if item.get("type") == "agent_message":
                if not turn_started or final_message is not None or item_error_seen:
                    raise CodexCodingPlanRuntimeError("jsonl-item-order-invalid")
                text = item.get("text")
                if not isinstance(text, str) or not text.strip():
                    raise CodexCodingPlanRuntimeError("jsonl-agent-message-invalid")
                final_message = text
            elif item.get("type") == "error":
                if not thread_started or item_error_seen or final_message is not None:
                    raise CodexCodingPlanRuntimeError("jsonl-item-error-order-invalid")
                item_error_seen = True
            else:
                raise CodexCodingPlanRuntimeError("jsonl-item-type-unsupported")
        elif event_type == "turn.completed":
            if not turn_started or final_message is None or item_error_seen:
                raise CodexCodingPlanRuntimeError("jsonl-completion-order-invalid")
            usage = _parse_usage(event.get("usage"), active_limits)
            terminal_event = event_type
        elif event_type == "turn.failed":
            if not turn_started:
                raise CodexCodingPlanRuntimeError("jsonl-failure-order-invalid")
            if "usage" in event:
                usage = _parse_usage(event.get("usage"), active_limits)
            terminal_event = event_type
        elif event_type == "error":
            if error_seen:
                raise CodexCodingPlanRuntimeError("jsonl-duplicate-error")
            error_seen = True
        else:
            raise CodexCodingPlanRuntimeError("jsonl-event-type-unsupported")

    if terminal_event == "turn.completed":
        return CodexCodingPlanRunResult(
            status="transport-completed",
            terminal_event=terminal_event,
            failure_code=None,
            thread_id=thread_id,
            final_message=final_message,
            usage=usage,
            event_count=len(lines),
        )
    if terminal_event == "turn.failed":
        return CodexCodingPlanRunResult(
            status="runtime-failed",
            terminal_event=terminal_event,
            failure_code=(
                "codex-error" if error_seen or item_error_seen else "turn-failed"
            ),
            thread_id=thread_id,
            final_message=final_message,
            usage=usage,
            event_count=len(lines),
        )
    if error_seen or item_error_seen:
        raise CodexCodingPlanRuntimeError("jsonl-capture-incomplete")
    raise CodexCodingPlanRuntimeError("jsonl-terminal-event-missing")


class CodexCodingPlanRuntimeRunner:
    """Validate one run from a trusted injected, bounded process host.

    The repository intentionally provides no default live host.  A production
    host must satisfy the limitations named at module level before it may pass
    a real credential to this contract.
    """

    def __init__(
        self,
        *,
        codex_executable: str | Path,
        process_runner: CodexCodingPlanProcessRunner | None = None,
        limits: CodexCodingPlanLimits | None = None,
    ) -> None:
        self._codex_executable = os.fspath(codex_executable)
        self._process_runner = process_runner
        self._limits = limits or CodexCodingPlanLimits()

    def run(
        self,
        prompt: str,
        *,
        isolated_workspace: str | Path,
        credential_env: str,
        environment: Mapping[str, str] | None = None,
    ) -> CodexCodingPlanRunResult:
        """Validate one trusted-host run without returning or logging the key."""

        if self._process_runner is None:
            raise CodexCodingPlanRuntimeError("live-runtime-not-ready")

        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be non-empty text")
        if (
            _utf8_size(prompt, "prompt-invalid-encoding")
            > self._limits.max_prompt_bytes
        ):
            raise CodexCodingPlanRuntimeError("prompt-byte-limit-exceeded")
        workspace = _resolve_isolated_workspace(isolated_workspace)
        executable = _resolve_native_codex_executable(self._codex_executable)
        environment_name = _validate_source_credential_environment_name(credential_env)
        source_environment = os.environ if environment is None else environment
        _reject_casefold_environment_collisions(source_environment)
        credential = source_environment.get(environment_name)
        if not isinstance(credential, str) or not credential or "\x00" in credential:
            raise CodexCodingPlanRuntimeError("credential-environment-missing")
        if credential in prompt:
            raise CodexCodingPlanRuntimeError("credential-present-in-prompt")

        try:
            with tempfile.TemporaryDirectory(
                prefix="rwb-codex-coding-plan-"
            ) as directory:
                codex_home = Path(directory).resolve(strict=True)
                model_catalog = _write_official_model_catalog(codex_home)
                command = build_codex_coding_plan_command(
                    isolated_workspace=workspace,
                    model_catalog_json=model_catalog,
                    codex_executable=executable,
                )
                child_environment = _build_child_environment(
                    source_environment,
                    credential=credential,
                    codex_home=codex_home,
                )
                try:
                    process = self._process_runner(
                        command,
                        cwd=workspace,
                        env=child_environment,
                        stdin=prompt,
                        timeout_seconds=float(self._limits.timeout_seconds),
                    )
                # Collapse every ordinary host exception so its text (which may
                # contain a command or secret) cannot escape into a caller log.
                except Exception:  # noqa: BLE001
                    raise CodexCodingPlanRuntimeError("codex-process-failed") from None
        except OSError:
            raise CodexCodingPlanRuntimeError("codex-home-isolation-failed") from None

        if not _workspace_remains_empty(workspace):
            raise CodexCodingPlanRuntimeError("isolated-workspace-mutated")

        if (
            isinstance(process.returncode, bool)
            or not isinstance(process.returncode, int)
            or not isinstance(process.stdout, str)
            or not isinstance(process.stderr, str)
        ):
            raise CodexCodingPlanRuntimeError("codex-process-result-invalid")
        if credential in process.stdout or credential in process.stderr:
            raise CodexCodingPlanRuntimeError("credential-exposure-detected")
        if (
            _utf8_size(process.stderr, "stderr-invalid-encoding")
            > self._limits.max_stderr_bytes
        ):
            raise CodexCodingPlanRuntimeError("stderr-byte-limit-exceeded")
        if process.stderr:
            raise CodexCodingPlanRuntimeError("stderr-not-empty")

        result = parse_codex_coding_plan_jsonl(process.stdout, limits=self._limits)
        if result.status == "transport-completed" and process.returncode != 0:
            raise CodexCodingPlanRuntimeError("process-exit-status-mismatch")
        if result.status == "runtime-failed" and process.returncode == 0:
            raise CodexCodingPlanRuntimeError("process-exit-status-mismatch")
        return result


def _resolve_isolated_workspace(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("isolated_workspace must be an absolute path")
    if candidate.is_symlink() or _is_reparse_point(candidate):
        raise ValueError("isolated_workspace must not be a link or reparse point")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise ValueError("isolated_workspace must be an existing directory") from None
    if not resolved.is_dir() or resolved.parent == resolved:
        raise ValueError("isolated_workspace must be an existing non-root directory")
    try:
        if next(resolved.iterdir(), None) is not None:
            raise ValueError("isolated_workspace must be empty")
    except OSError:
        raise ValueError("isolated_workspace must be readable") from None
    return resolved


def _resolve_native_codex_executable(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("codex_executable must be an absolute native path")
    if candidate.is_symlink() or _is_reparse_point(candidate):
        raise ValueError("codex_executable must not be a link or reparse point")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise ValueError("codex_executable must be an existing native file") from None
    if not resolved.is_file():
        raise ValueError("codex_executable must be an existing native file")
    if os.name == "nt" and resolved.suffix.casefold() != ".exe":
        raise ValueError("codex_executable must be an absolute native .exe")
    return os.fspath(resolved)


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _workspace_remains_empty(workspace: Path) -> bool:
    try:
        return next(workspace.iterdir(), None) is None
    except OSError:
        return False


def _write_official_model_catalog(codex_home: Path) -> Path:
    path = codex_home / "models.json"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(_CODEX_CODING_PLAN_MODEL_CATALOG_JSON)
    return path.resolve(strict=True)


def _resolve_official_model_catalog(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("model_catalog_json must be an absolute path")
    if candidate.is_symlink():
        raise ValueError("model_catalog_json must not be a symlink")
    try:
        resolved = candidate.resolve(strict=True)
        if (
            not resolved.is_file()
            or resolved.stat().st_size > _CODEX_CODING_PLAN_MODEL_CATALOG_MAX_BYTES
        ):
            raise ValueError(
                "model_catalog_json must contain the fixed GLM-5.3 catalog"
            )
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError(
            "model_catalog_json must contain the fixed GLM-5.3 catalog"
        ) from None
    expected = json.loads(_CODEX_CODING_PLAN_MODEL_CATALOG_JSON)
    if document != expected:
        raise ValueError("model_catalog_json must contain the fixed GLM-5.3 catalog")
    return resolved


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _validate_source_credential_environment_name(name: str) -> str:
    if not isinstance(name, str) or _ENVIRONMENT_NAME.fullmatch(name) is None:
        raise ValueError("credential_env must be a portable environment variable name")
    if name not in CODEX_CODING_PLAN_ALLOWED_SOURCE_CREDENTIAL_ENVS:
        raise ValueError("credential_env must be an approved Coding Plan key source")
    return name


def _reject_casefold_environment_collisions(source: Mapping[str, str]) -> None:
    seen: set[str] = set()
    for name in source:
        if not isinstance(name, str):
            raise CodexCodingPlanRuntimeError("environment-name-invalid")
        normalized = name.casefold()
        if normalized in seen:
            raise CodexCodingPlanRuntimeError("environment-name-collision")
        seen.add(normalized)


def _build_child_environment(
    source: Mapping[str, str],
    *,
    credential: str,
    codex_home: Path,
) -> dict[str, str]:
    child: dict[str, str] = {}
    for name in _WINDOWS_SYSTEM_ENVIRONMENT:
        value = source.get(name)
        if isinstance(value, str) and "\x00" not in value:
            child[name] = value
    user_home = codex_home / "home"
    app_data = codex_home / "appdata"
    local_app_data = codex_home / "localappdata"
    temp_dir = codex_home / "temp"
    for directory in (user_home, app_data, local_app_data, temp_dir):
        directory.mkdir(mode=0o700)
    child.update(
        {
            "APPDATA": os.fspath(app_data),
            "CODEX_HOME": os.fspath(codex_home),
            "HOME": os.fspath(user_home),
            "LOCALAPPDATA": os.fspath(local_app_data),
            "NO_COLOR": "1",
            "RUST_BACKTRACE": "0",
            "TEMP": os.fspath(temp_dir),
            "TMP": os.fspath(temp_dir),
            "USERPROFILE": os.fspath(user_home),
            CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV: credential,
        }
    )
    return child


def _parse_usage(
    document: object,
    limits: CodexCodingPlanLimits,
) -> CodexCodingPlanUsage:
    if not isinstance(document, dict):
        raise CodexCodingPlanRuntimeError("jsonl-usage-missing")
    input_tokens = _usage_integer(document, "input_tokens", required=True)
    cached_input_tokens = _usage_integer(
        document, "cached_input_tokens", required=False
    )
    output_tokens = _usage_integer(document, "output_tokens", required=True)
    reasoning_output_tokens = _usage_integer(
        document,
        "reasoning_output_tokens",
        required=False,
    )
    usage = CodexCodingPlanUsage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
        reasoning_output_tokens=reasoning_output_tokens,
    )
    if cached_input_tokens > input_tokens:
        raise CodexCodingPlanRuntimeError("jsonl-cached-usage-invalid")
    if reasoning_output_tokens > output_tokens:
        raise CodexCodingPlanRuntimeError("jsonl-reasoning-usage-invalid")
    if output_tokens > limits.max_output_tokens:
        raise CodexCodingPlanRuntimeError("output-token-limit-exceeded")
    if usage.total_tokens > limits.max_total_tokens:
        raise CodexCodingPlanRuntimeError("total-token-limit-exceeded")
    return usage


def _usage_integer(
    document: Mapping[str, object], field: str, *, required: bool
) -> int:
    if field not in document and not required:
        return 0
    value = document.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CodexCodingPlanRuntimeError("jsonl-usage-invalid")
    return value


def _utf8_size(value: str, error_code: str) -> int:
    try:
        return len(value.encode("utf-8"))
    except UnicodeError:
        raise CodexCodingPlanRuntimeError(error_code) from None


def _bounded_positive_int(name: str, value: int, ceiling: int) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value <= 0
        or value > ceiling
    ):
        raise ValueError(f"{name} must be within the fixed runtime ceiling")
