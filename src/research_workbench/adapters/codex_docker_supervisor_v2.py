"""Fail-closed, no-start supervisor for Docker topology v0.2.

This Huang Yi-owned adapter is deliberately additive.  It binds one inert
topology transaction to an absolute Docker binary, a stable daemon identity,
the frozen Docker API version, a canonical plan hash, bounded command output,
and monotonic command timing.  It has no default executor, never reads process
environment state or credentials, and never starts, attaches to, or executes
inside a container.

The topology contract contains a name-based cleanup plan for documentation.
This supervisor never executes it: cleanup targets only object IDs returned by
successful create commands and reconciled by both name and ID.  An ambiguous
create is neither adopted nor removed by name; final name absence evidence
then fails closed if the command did create an object.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Protocol

from research_workbench.adapters.codex_coding_plan import (
    CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS,
)
from research_workbench.adapters.codex_coding_plan_docker import (
    DockerCommandResult,
)
from research_workbench.adapters.codex_docker_topology_v2 import (
    CODEX_DOCKER_TOPOLOGY_V2_LIVE_READY,
    CODEX_DOCKER_TOPOLOGY_V2_VERSION,
    CODEX_DOCKER_V2_MAX_INSPECT_BYTES,
    CodexDockerTopologyV2Attestation,
    CodexDockerTopologyV2Plan,
    CodexDockerTopologyV2Transaction,
    attest_codex_docker_topology_v2,
    build_codex_docker_topology_v2_transaction,
)

CODEX_DOCKER_SUPERVISOR_V2_LIVE_READY = False
CODEX_DOCKER_SUPERVISOR_V2_API_VERSION = "1.53"
CODEX_DOCKER_SUPERVISOR_V2_VERSION = "0.2"
CODEX_DOCKER_SUPERVISOR_V2_MAX_CLEANUP_SECONDS = 30.0

_IDENTITY = re.compile(r"[0-9a-f]{64}\Z")
_DAEMON_IDENTITY = re.compile(r"[-A-Za-z0-9_:]{8,128}\Z")
_API_VERSION = re.compile(r"[0-9]+\.[0-9]+\Z")
_SERVER_VERSION = re.compile(r"[-+.A-Za-z0-9]{1,64}\Z")
_INSPECT_IDENTITY_FORMAT = "--format={{.Id}}|{{.Name}}"
_STATE_JSON_FORMAT = "--format={{json .State}}"
_VERSION_JSON_FORMAT = (
    '--format={"client_api_version":{{json .Client.APIVersion}},'
    '"server_api_version":{{json .Server.APIVersion}},'
    '"server_version":{{json .Server.Version}}}'
)
_INFO_JSON_FORMAT = (
    '--format={"daemon_id":{{json .ID}},"server_version":{{json .ServerVersion}}}'
)
_CONTROL_STDOUT_LIMIT = 65_536
_CONTROL_STDERR_LIMIT = 16_384
_MAX_DOCKER_BINARY_BYTES = 268_435_456
_BINARY_CHUNK_BYTES = 1_048_576
_SECRET_ASSIGNMENT = re.compile(
    r"(?:api[_-]?key|authorization|credential|password|secret|token)=",
    re.IGNORECASE,
)


class CodexDockerSupervisorV2Error(RuntimeError):
    """Stable supervisor failure with an optional bounded audit transcript."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.audit: CodexDockerSupervisorV2Audit | None = None

    def __repr__(self) -> str:
        return f"CodexDockerSupervisorV2Error({str(self)!r})"


class CodexDockerSupervisorV2CleanupError(CodexDockerSupervisorV2Error):
    """Closeout failure retaining primary and cleanup failures separately."""

    def __init__(
        self,
        *,
        primary_error: BaseException | None,
        cleanup_error: BaseException,
    ) -> None:
        super().__init__("docker-supervisor-v2-cleanup-unverified")
        self.primary_error = primary_error
        self.cleanup_error = cleanup_error


class DockerSupervisorV2Executor(Protocol):
    """Injectable bounded command boundary; no real implementation is supplied."""

    def execute(
        self,
        command: tuple[str, ...],
        *,
        stdin: bytes,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
        environment: Mapping[str, str],
    ) -> DockerCommandResult: ...


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorV2BinaryBinding:
    """Content binding for the exact absolute Docker executable token."""

    executable: str
    resolved_executable: str
    byte_count: int
    sha256: str

    def __post_init__(self) -> None:
        if (
            not Path(self.executable).is_absolute()
            or _is_remote_filesystem_path(self.executable)
            or not Path(self.resolved_executable).is_absolute()
            or _is_remote_filesystem_path(self.resolved_executable)
            or isinstance(self.byte_count, bool)
            or not 0 < self.byte_count <= _MAX_DOCKER_BINARY_BYTES
            or re.fullmatch(r"[0-9a-f]{64}", self.sha256) is None
        ):
            raise ValueError("supervisor v2 binary binding is inconsistent")


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorV2Plan:
    """Supervisor-only execution inputs that freeze Docker implicit state."""

    topology: CodexDockerTopologyV2Plan
    docker_config_directory: str
    docker_host: str

    def __post_init__(self) -> None:
        _validate_supervisor_plan(self)


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorV2DaemonBinding:
    """Daemon and negotiated API identity frozen for one transaction."""

    daemon_id_bytes: int
    daemon_id_sha256: str
    server_version: str
    client_api_version: str
    server_api_version: str

    def __post_init__(self) -> None:
        if (
            isinstance(self.daemon_id_bytes, bool)
            or not 8 <= self.daemon_id_bytes <= 128
            or re.fullmatch(r"[0-9a-f]{64}", self.daemon_id_sha256) is None
            or _SERVER_VERSION.fullmatch(self.server_version) is None
            or self.client_api_version != CODEX_DOCKER_SUPERVISOR_V2_API_VERSION
            or self.server_api_version != CODEX_DOCKER_SUPERVISOR_V2_API_VERSION
        ):
            raise ValueError("supervisor v2 daemon binding is inconsistent")


@dataclass(frozen=True, slots=True, repr=False)
class CodexDockerSupervisorV2CommandCapture:
    """Bounded observation of one submitted Docker CLI command."""

    ordinal: int
    phase: str
    command: tuple[str, ...]
    command_sha256: str
    returncode: int
    stdout: bytes
    stderr: bytes
    stdout_observed_bytes: int
    stderr_observed_bytes: int
    stdout_sha256: str
    stderr_sha256: str
    started_monotonic: float
    finished_monotonic: float
    transport_complete: bool
    timing_complete: bool
    stdout_retained: bool
    stderr_retained: bool

    def __repr__(self) -> str:
        return (
            "CodexDockerSupervisorV2CommandCapture("
            f"ordinal={self.ordinal}, phase={self.phase!r}, "
            f"returncode={self.returncode}, "
            f"stdout=<{len(self.stdout)} bounded bytes>, "
            f"stderr=<{len(self.stderr)} bounded bytes>, "
            f"transport_complete={self.transport_complete}, "
            f"timing_complete={self.timing_complete}, "
            f"stdout_retained={self.stdout_retained}, "
            f"stderr_retained={self.stderr_retained})"
        )


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorV2Audit:
    """Canonical binding over plan, binary, daemon, and every command capture."""

    plan_sha256: str
    binary: CodexDockerSupervisorV2BinaryBinding
    daemon: CodexDockerSupervisorV2DaemonBinding | None
    commands: tuple[CodexDockerSupervisorV2CommandCapture, ...]
    transcript_sha256: str
    transaction_deadline_monotonic: float
    cleanup_deadline_monotonic: float | None
    capture_complete: bool

    def __post_init__(self) -> None:
        if (
            re.fullmatch(r"[0-9a-f]{64}", self.plan_sha256) is None
            or re.fullmatch(r"[0-9a-f]{64}", self.transcript_sha256) is None
            or not math.isfinite(self.transaction_deadline_monotonic)
            or self.transaction_deadline_monotonic < 0
            or (
                self.cleanup_deadline_monotonic is not None
                and (
                    not math.isfinite(self.cleanup_deadline_monotonic)
                    or self.cleanup_deadline_monotonic < 0
                )
            )
            or tuple(item.ordinal for item in self.commands)
            != tuple(range(len(self.commands)))
        ):
            raise ValueError("supervisor v2 audit identity is inconsistent")
        prior = 0.0
        for item in self.commands:
            forbidden = _command_has_live_verb(item.command)
            if (
                item.started_monotonic < prior
                or item.finished_monotonic < item.started_monotonic
                or item.command[0] != self.binary.executable
                or forbidden
                or item.stdout_retained
                or item.stderr_retained
                or item.stdout
                or item.stderr
                or item.stdout_observed_bytes < len(item.stdout)
                or item.stderr_observed_bytes < len(item.stderr)
                or item.command_sha256
                != hashlib.sha256(_canonical_json_bytes(list(item.command))).hexdigest()
            ):
                raise ValueError("supervisor v2 audit command is inconsistent")
            prior = item.finished_monotonic
        if self.capture_complete and (
            self.daemon is None
            or self.cleanup_deadline_monotonic is None
            or not self.commands
            or any(
                not item.transport_complete or not item.timing_complete
                for item in self.commands
            )
        ):
            raise ValueError("complete supervisor v2 audit lacks complete evidence")


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorV2CleanupProof:
    """ID-only removals and independent name-plus-ID absence evidence."""

    removal_returncodes: tuple[int, ...]
    exact_name_list_proofs: int
    exact_name_inspect_proofs: int
    exact_id_inspect_proofs: int
    expected_id_inspect_proofs: int
    cleanup_authorized: bool
    daemon_rebound: bool
    binary_rebound: bool
    config_rebound: bool
    absence_verified: bool = field(default=True, init=False)
    capture_complete: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if (
            any(returncode != 0 for returncode in self.removal_returncodes)
            or not 0 <= self.expected_id_inspect_proofs <= 4
            or len(self.removal_returncodes) != self.expected_id_inspect_proofs
            or self.exact_name_list_proofs != 4
            or self.exact_name_inspect_proofs != 4
            or self.exact_id_inspect_proofs != self.expected_id_inspect_proofs
            or not self.cleanup_authorized
            or not self.daemon_rebound
            or not self.binary_rebound
            or not self.config_rebound
        ):
            raise ValueError("supervisor v2 cleanup proof is inconsistent")


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorV2Result:
    """Successful, fully cleaned, no-start-command v0.2 transaction result."""

    attestation: CodexDockerTopologyV2Attestation
    binary: CodexDockerSupervisorV2BinaryBinding
    daemon: CodexDockerSupervisorV2DaemonBinding
    plan_sha256: str
    audit: CodexDockerSupervisorV2Audit
    cleanup: CodexDockerSupervisorV2CleanupProof
    start_commands: tuple[tuple[str, ...], ...]
    attach_commands: tuple[tuple[str, ...], ...]
    exec_commands: tuple[tuple[str, ...], ...]
    start_command_issued: bool = field(default=False, init=False)
    observed_created_state: bool = field(default=True, init=False)
    assurance_scope: str = field(default="single-writer-daemon-assumption", init=False)
    transaction_capture_complete: bool = field(default=True, init=False)
    capture_complete: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if (
            self.attestation.inspect_validation_complete is not True
            or self.attestation.capture_complete is not False
            or self.audit.capture_complete is not True
            or self.cleanup.capture_complete is not True
            or self.cleanup.expected_id_inspect_proofs != 4
            or self.audit.plan_sha256 != self.plan_sha256
            or self.audit.binary != self.binary
            or self.audit.daemon != self.daemon
            or self.start_command_issued is not False
            or self.observed_created_state is not True
            or self.assurance_scope != "single-writer-daemon-assumption"
            or self.start_commands
            or self.attach_commands
            or self.exec_commands
        ):
            raise ValueError("supervisor v2 result requires complete inert evidence")


@dataclass(slots=True)
class _RunContext:
    executor: DockerSupervisorV2Executor
    clock: Callable[[], float]
    docker_executable: str
    docker_config_directory: str
    docker_host: str
    plan_sha256: str
    captures: list[CodexDockerSupervisorV2CommandCapture]
    last_finished: float | None = None
    deadline: float = 0.0
    transaction_deadline: float = 0.0
    cleanup_deadline: float | None = None
    daemon: CodexDockerSupervisorV2DaemonBinding | None = None
    ownership_ambiguous: bool = False


class CodexDockerTopologySupervisorV2:
    """Execute an inert topology v0.2 transaction and prove full closeout."""

    def __init__(
        self,
        *,
        executor: DockerSupervisorV2Executor,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if executor is None:
            raise TypeError("executor is required")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._executor = executor
        self._clock = clock

    def run_offline_transaction(
        self,
        plan: CodexDockerSupervisorV2Plan,
        *,
        timeout_seconds: float = 30.0,
    ) -> CodexDockerSupervisorV2Result:
        """Create, inspect, attest, and remove without start/attach/exec."""

        _validate_timeout(timeout_seconds)
        if CODEX_DOCKER_TOPOLOGY_V2_LIVE_READY or CODEX_DOCKER_SUPERVISOR_V2_LIVE_READY:
            raise CodexDockerSupervisorV2Error(
                "docker-topology-v2-contract-unexpected-live"
            )
        if not isinstance(plan, CodexDockerSupervisorV2Plan):
            raise TypeError("plan must be a CodexDockerSupervisorV2Plan")
        initial_tick = _read_initial_clock(self._clock)
        topology = plan.topology
        context = _RunContext(
            executor=self._executor,
            clock=self._clock,
            docker_executable=topology.docker_executable,
            docker_config_directory=plan.docker_config_directory,
            docker_host=plan.docker_host,
            plan_sha256="",
            captures=[],
            last_finished=initial_tick,
            deadline=initial_tick + float(timeout_seconds),
            transaction_deadline=initial_tick + float(timeout_seconds),
        )
        _validate_supervisor_plan(plan)
        _checkpoint_local_operation(context)
        transaction = build_codex_docker_topology_v2_transaction(topology)
        _checkpoint_local_operation(context)
        _validate_inert_transaction(plan, transaction)
        _checkpoint_local_operation(context)
        binary = _bind_docker_binary_bounded(context, topology.docker_executable)
        plan_sha256 = _hash_supervisor_plan(plan, transaction)
        _checkpoint_local_operation(context)
        context.plan_sha256 = plan_sha256
        identities: dict[str, str | None] = {
            "runtime": None,
            "proxy": None,
            "internal": None,
            "egress": None,
        }
        primary_error: BaseException | None = None
        attestation: CodexDockerTopologyV2Attestation | None = None
        transaction_started = False

        try:
            context.daemon = self._capture_daemon_binding(
                context, timeout_seconds=timeout_seconds, phase="binding-preflight"
            )
            self._assert_preflight_absent(
                context,
                topology,
                transaction,
                timeout_seconds=timeout_seconds,
            )
            transaction_started = True
            identities["internal"] = self._create_and_reconcile(
                context,
                topology,
                transaction.create[0],
                role="internal",
                kind="network",
                name=topology.internal_network,
                timeout_seconds=timeout_seconds,
            )
            identities["egress"] = self._create_and_reconcile(
                context,
                topology,
                transaction.create[1],
                role="egress",
                kind="network",
                name=topology.egress_network,
                timeout_seconds=timeout_seconds,
            )
            identities["proxy"] = self._create_and_reconcile(
                context,
                topology,
                transaction.create[2],
                role="proxy",
                kind="container",
                name=topology.proxy_container,
                timeout_seconds=timeout_seconds,
            )
            self._execute_empty_success(
                context,
                _freeze_command(plan, transaction.create[3]),
                phase="create-connect-proxy-egress",
                code="docker-supervisor-v2-network-connect-failed",
                timeout_seconds=timeout_seconds,
            )
            identities["runtime"] = self._create_and_reconcile(
                context,
                topology,
                transaction.create[4],
                role="runtime",
                kind="container",
                name=topology.runtime_container,
                timeout_seconds=timeout_seconds,
            )
            attestation = self._attest(
                context,
                plan,
                transaction,
                timeout_seconds=timeout_seconds,
            )
            _reconcile_attestation(attestation, identities, topology)
        except BaseException as exc:  # noqa: BLE001 - closeout also on cancellation
            primary_error = exc

        cleanup: CodexDockerSupervisorV2CleanupProof | None = None
        cleanup_error: BaseException | None = None
        if transaction_started:
            try:
                _begin_cleanup_deadline(context)
                cleanup = self._cleanup_verified(
                    context,
                    plan,
                    transaction,
                    identities=identities,
                    initial_binary=binary,
                    initial_daemon=context.daemon,
                    timeout_seconds=timeout_seconds,
                )
            except BaseException as exc:  # noqa: BLE001 - retain both failures
                cleanup_error = exc

        audit = _build_audit(
            context,
            binary=binary,
            capture_complete=(
                primary_error is None
                and cleanup_error is None
                and cleanup is not None
                and cleanup.capture_complete
            ),
        )
        if cleanup_error is not None:
            combined = CodexDockerSupervisorV2CleanupError(
                primary_error=primary_error,
                cleanup_error=cleanup_error,
            )
            combined.audit = audit
            _attach_audit(primary_error, audit)
            _attach_audit(cleanup_error, audit)
            raise combined from cleanup_error
        if primary_error is not None:
            _attach_audit(primary_error, audit)
            raise primary_error
        assert attestation is not None
        assert cleanup is not None
        assert context.daemon is not None
        return CodexDockerSupervisorV2Result(
            attestation=attestation,
            binary=binary,
            daemon=context.daemon,
            plan_sha256=plan_sha256,
            audit=audit,
            cleanup=cleanup,
            start_commands=(),
            attach_commands=(),
            exec_commands=(),
        )

    def run_live(self, *args: object, **kwargs: object) -> None:
        """Reject before inspecting any live input, environment, or credential."""

        del args, kwargs
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-live-disabled")

    def _capture_daemon_binding(
        self,
        context: _RunContext,
        *,
        timeout_seconds: float,
        phase: str,
    ) -> CodexDockerSupervisorV2DaemonBinding:
        version_result: DockerCommandResult | None = None
        info_result: DockerCommandResult | None = None
        failures: list[BaseException] = []
        try:
            version_result = self._execute(
                context,
                _docker_command(context, "version", _VERSION_JSON_FORMAT),
                phase=f"{phase}-version",
                timeout_seconds=min(timeout_seconds, 5.0),
                stdout_limit=_CONTROL_STDOUT_LIMIT,
                stderr_limit=_CONTROL_STDERR_LIMIT,
                retain_outputs=False,
            )
        except BaseException as exc:
            if _is_cancellation(exc):
                raise
            failures.append(exc)
        try:
            info_result = self._execute(
                context,
                _docker_command(context, "info", _INFO_JSON_FORMAT),
                phase=f"{phase}-info",
                timeout_seconds=min(timeout_seconds, 5.0),
                stdout_limit=_CONTROL_STDOUT_LIMIT,
                stderr_limit=_CONTROL_STDERR_LIMIT,
                retain_outputs=False,
            )
        except BaseException as exc:
            if _is_cancellation(exc):
                raise
            failures.append(exc)
        if failures or version_result is None or info_result is None:
            deadline_failure = next(
                (
                    failure
                    for failure in failures
                    if isinstance(failure, CodexDockerSupervisorV2Error)
                    and str(failure)
                    == "docker-supervisor-v2-absolute-deadline-exceeded"
                ),
                None,
            )
            if deadline_failure is not None:
                raise deadline_failure
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-daemon-binding-unverified"
            ) from (failures[-1] if failures else None)
        if (
            version_result.returncode != 0
            or version_result.stderr
            or info_result.returncode != 0
            or info_result.stderr
        ):
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-daemon-binding-unverified"
            )
        version = _parse_json_object(
            version_result.stdout, "docker-supervisor-v2-version-json-invalid"
        )
        info = _parse_json_object(
            info_result.stdout, "docker-supervisor-v2-info-json-invalid"
        )
        if set(version) != {
            "client_api_version",
            "server_api_version",
            "server_version",
        } or set(info) != {"daemon_id", "server_version"}:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-daemon-binding-unverified"
            )
        client_api = _require_text(
            version,
            "client_api_version",
            _API_VERSION,
            "docker-supervisor-v2-api-version-invalid",
        )
        server_api = _require_text(
            version,
            "server_api_version",
            _API_VERSION,
            "docker-supervisor-v2-api-version-invalid",
        )
        daemon_id = _require_text(
            info,
            "daemon_id",
            _DAEMON_IDENTITY,
            "docker-supervisor-v2-daemon-id-invalid",
        )
        server_version = _require_text(
            info,
            "server_version",
            _SERVER_VERSION,
            "docker-supervisor-v2-server-version-invalid",
        )
        version_server_version = _require_text(
            version,
            "server_version",
            _SERVER_VERSION,
            "docker-supervisor-v2-server-version-invalid",
        )
        if (
            client_api != CODEX_DOCKER_SUPERVISOR_V2_API_VERSION
            or server_api != CODEX_DOCKER_SUPERVISOR_V2_API_VERSION
            or version_server_version != server_version
        ):
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-api-or-server-version-mismatch"
            )
        return CodexDockerSupervisorV2DaemonBinding(
            daemon_id_bytes=len(daemon_id.encode("ascii")),
            daemon_id_sha256=hashlib.sha256(daemon_id.encode("ascii")).hexdigest(),
            server_version=server_version,
            client_api_version=client_api,
            server_api_version=server_api,
        )

    def _assert_preflight_absent(
        self,
        context: _RunContext,
        plan: CodexDockerTopologyV2Plan,
        transaction: CodexDockerTopologyV2Transaction,
        *,
        timeout_seconds: float,
    ) -> None:
        resources = _resources(plan)
        if len(transaction.preflight_absence) != len(resources):
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-preflight-plan-invalid"
            )
        for command in transaction.preflight_absence:
            result = self._execute(
                context,
                _freeze_topology_command(context, command),
                phase="preflight-name-list",
                timeout_seconds=min(timeout_seconds, 5.0),
                stdout_limit=_CONTROL_STDOUT_LIMIT,
                stderr_limit=_CONTROL_STDERR_LIMIT,
            )
            if result.returncode != 0 or result.stdout.strip() or result.stderr:
                raise CodexDockerSupervisorV2Error(
                    "docker-supervisor-v2-preflight-resource-not-absent"
                )
        for _, kind, name in resources:
            observed = self._inspect_identity(
                context,
                kind=kind,
                target=name,
                expected_name=name,
                allow_absent=True,
                phase="preflight-name-inspect",
                timeout_seconds=min(timeout_seconds, 5.0),
            )
            if observed is not None:
                raise CodexDockerSupervisorV2Error(
                    "docker-supervisor-v2-preflight-resource-not-absent"
                )

    def _create_and_reconcile(
        self,
        context: _RunContext,
        plan: CodexDockerTopologyV2Plan,
        command: tuple[str, ...],
        *,
        role: str,
        kind: str,
        name: str,
        timeout_seconds: float,
    ) -> str:
        result = self._execute(
            context,
            _freeze_topology_command(context, command),
            phase=f"create-{role}",
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
            marks_create_submission=True,
        )
        if result.returncode != 0 or result.stderr:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-create-command-failed"
            )
        identity = _decode_identity(
            result.stdout, "docker-supervisor-v2-create-identity-invalid"
        )
        for target in (name, identity):
            observed = self._inspect_identity(
                context,
                kind=kind,
                target=target,
                expected_name=name,
                allow_absent=False,
                phase=f"inspect-{role}",
                timeout_seconds=min(timeout_seconds, 5.0),
            )
            if observed != identity:
                raise CodexDockerSupervisorV2Error(
                    "docker-supervisor-v2-identity-reconcile-failed"
                )
        context.ownership_ambiguous = False
        del plan
        return identity

    def _execute_empty_success(
        self,
        context: _RunContext,
        command: tuple[str, ...],
        *,
        phase: str,
        code: str,
        timeout_seconds: float,
    ) -> None:
        result = self._execute(
            context,
            command,
            phase=phase,
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )
        if result.returncode != 0 or result.stdout.strip() or result.stderr:
            raise CodexDockerSupervisorV2Error(code)

    def _attest(
        self,
        context: _RunContext,
        plan: CodexDockerSupervisorV2Plan,
        transaction: CodexDockerTopologyV2Transaction,
        *,
        timeout_seconds: float,
    ) -> CodexDockerTopologyV2Attestation:
        if len(transaction.attest) != 3:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-attestation-plan-invalid"
            )
        observations: list[DockerCommandResult] = []
        result: DockerCommandResult | None = None
        attestation: CodexDockerTopologyV2Attestation | None = None
        topology_failed = False
        topology_cancellation: BaseException | None = None
        try:
            for index, command in enumerate(transaction.attest):
                result = self._execute(
                    context,
                    _freeze_topology_command(context, command),
                    phase=f"attest-{index}",
                    timeout_seconds=timeout_seconds,
                    stdout_limit=CODEX_DOCKER_V2_MAX_INSPECT_BYTES,
                    stderr_limit=_CONTROL_STDERR_LIMIT,
                )
                if result.returncode != 0 or result.stderr:
                    raise CodexDockerSupervisorV2Error(
                        "docker-supervisor-v2-attestation-command-failed"
                    )
                observations.append(result)
            try:
                attestation = attest_codex_docker_topology_v2(
                    plan.topology,
                    image_inspect_json=observations[0].stdout,
                    container_inspect_json=observations[1].stdout,
                    network_inspect_json=observations[2].stdout,
                )
            except BaseException as exc:  # noqa: BLE001 - sanitize parser boundary
                if _is_cancellation(exc):
                    topology_cancellation = exc.with_traceback(None)
                else:
                    topology_failed = True
        finally:
            # Raw inspect documents are parser-temporary only.  Clear every
            # local reference before a stable supervisor error is raised so a
            # traceback cannot become an alternate durable capture channel.
            observations.clear()
            result = None
        if topology_cancellation is not None:
            raise topology_cancellation.with_traceback(None)
        if topology_failed:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-topology-attestation-failed"
            )
        assert attestation is not None
        return attestation

    def _cleanup_verified(
        self,
        context: _RunContext,
        plan: CodexDockerSupervisorV2Plan,
        transaction: CodexDockerTopologyV2Transaction,
        *,
        identities: Mapping[str, str | None],
        initial_binary: CodexDockerSupervisorV2BinaryBinding,
        initial_daemon: CodexDockerSupervisorV2DaemonBinding | None,
        timeout_seconds: float,
    ) -> CodexDockerSupervisorV2CleanupProof:
        uncertainty = False
        cleanup_cancellation: BaseException | None = None
        removal_returncodes: list[int] = []
        topology = plan.topology
        expected_removals = sum(value is not None for value in identities.values())

        # No Docker mutation is authorized until the local config, executable,
        # and remote endpoint all rebind to the exact preflight observations.
        try:
            _validate_blank_config_directory_bounded(context, plan)
            precleanup_binary = _bind_docker_binary_bounded(
                context, topology.docker_executable
            )
            if precleanup_binary != initial_binary or initial_daemon is None:
                raise CodexDockerSupervisorV2Error(
                    "docker-supervisor-v2-precleanup-binding-mismatch"
                )
            precleanup_daemon = self._capture_daemon_binding(
                context,
                timeout_seconds=timeout_seconds,
                phase="binding-precleanup",
            )
            if precleanup_daemon != initial_daemon:
                raise CodexDockerSupervisorV2Error(
                    "docker-supervisor-v2-precleanup-binding-mismatch"
                )
        except BaseException as exc:
            if _is_cancellation(exc):
                raise
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-cleanup-authorization-failed"
            ) from exc

        for role in ("runtime", "proxy"):
            identity = identities[role]
            if identity is None:
                continue
            try:
                self._assert_unstarted_container_by_id(
                    context,
                    identity,
                    timeout_seconds=min(timeout_seconds, 5.0),
                )
            except BaseException as exc:  # noqa: BLE001 - continue closeout
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                removal_returncodes.append(-1)
                uncertainty = True
                continue
            command = _docker_command(context, "container", "rm", "--volumes", identity)
            try:
                result = self._execute(
                    context,
                    command,
                    phase="cleanup-id-remove",
                    timeout_seconds=min(timeout_seconds, 10.0),
                    stdout_limit=_CONTROL_STDOUT_LIMIT,
                    stderr_limit=_CONTROL_STDERR_LIMIT,
                )
            except BaseException as exc:  # noqa: BLE001 - continue closeout
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                removal_returncodes.append(-1)
                uncertainty = True
            else:
                removal_returncodes.append(result.returncode)
                if result.returncode != 0 or result.stderr:
                    uncertainty = True

        for role in ("internal", "egress"):
            identity = identities[role]
            if identity is None:
                continue
            command = _docker_command(context, "network", "rm", identity)
            try:
                result = self._execute(
                    context,
                    command,
                    phase="cleanup-id-remove",
                    timeout_seconds=min(timeout_seconds, 10.0),
                    stdout_limit=_CONTROL_STDOUT_LIMIT,
                    stderr_limit=_CONTROL_STDERR_LIMIT,
                )
            except BaseException as exc:  # noqa: BLE001 - continue closeout
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                removal_returncodes.append(-1)
                uncertainty = True
            else:
                removal_returncodes.append(result.returncode)
                if result.returncode != 0 or result.stderr:
                    uncertainty = True

        name_list_proofs = 0
        for command in transaction.final_absence:
            try:
                result = self._execute(
                    context,
                    _freeze_topology_command(context, command),
                    phase="cleanup-name-list-proof",
                    timeout_seconds=min(timeout_seconds, 5.0),
                    stdout_limit=_CONTROL_STDOUT_LIMIT,
                    stderr_limit=_CONTROL_STDERR_LIMIT,
                )
            except BaseException as exc:  # noqa: BLE001 - continue closeout
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                uncertainty = True
                continue
            if (
                result.returncode == 0
                and not result.stdout.strip()
                and not result.stderr
            ):
                name_list_proofs += 1
            else:
                uncertainty = True

        name_inspect_proofs = 0
        for _, kind, name in _resources(topology):
            try:
                observed = self._inspect_identity(
                    context,
                    kind=kind,
                    target=name,
                    expected_name=name,
                    allow_absent=True,
                    phase="cleanup-name-inspect-proof",
                    timeout_seconds=min(timeout_seconds, 5.0),
                )
            except BaseException as exc:  # noqa: BLE001 - continue closeout
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                uncertainty = True
                continue
            if observed is None:
                name_inspect_proofs += 1
            else:
                uncertainty = True

        id_inspect_proofs = 0
        expected_id_proofs = sum(value is not None for value in identities.values())
        for role, kind, name in _resources(topology):
            identity = identities[role]
            if identity is None:
                continue
            try:
                observed = self._inspect_identity(
                    context,
                    kind=kind,
                    target=identity,
                    expected_name=name,
                    allow_absent=True,
                    phase="cleanup-id-inspect-proof",
                    timeout_seconds=min(timeout_seconds, 5.0),
                )
            except BaseException as exc:  # noqa: BLE001 - continue closeout
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                uncertainty = True
                continue
            if observed is None:
                id_inspect_proofs += 1
            else:
                uncertainty = True

        config_rebound = False
        try:
            _validate_blank_config_directory_bounded(context, plan)
            config_rebound = True
        except BaseException as exc:  # noqa: BLE001 - no more Docker calls are safe
            if _is_cancellation(exc) and cleanup_cancellation is None:
                cleanup_cancellation = exc
            uncertainty = True

        binary_rebound = False
        try:
            binary_rebound = (
                _bind_docker_binary_bounded(context, topology.docker_executable)
                == initial_binary
            )
        except BaseException as exc:  # noqa: BLE001 - normalized below
            if _is_cancellation(exc) and cleanup_cancellation is None:
                cleanup_cancellation = exc
            uncertainty = True
        if not binary_rebound:
            uncertainty = True

        rebound_daemon: CodexDockerSupervisorV2DaemonBinding | None = None
        if config_rebound and binary_rebound:
            try:
                rebound_daemon = self._capture_daemon_binding(
                    context,
                    timeout_seconds=timeout_seconds,
                    phase="binding-closeout",
                )
            except BaseException as exc:  # noqa: BLE001 - normalized below
                if _is_cancellation(exc) and cleanup_cancellation is None:
                    cleanup_cancellation = exc
                uncertainty = True
        daemon_rebound = initial_daemon is not None and rebound_daemon == initial_daemon
        if not daemon_rebound:
            uncertainty = True

        if cleanup_cancellation is not None:
            raise cleanup_cancellation
        if (
            uncertainty
            or len(removal_returncodes) != expected_removals
            or name_list_proofs != 4
            or name_inspect_proofs != 4
            or id_inspect_proofs != expected_id_proofs
            or context.ownership_ambiguous
        ):
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-cleanup-unverified"
            )
        return CodexDockerSupervisorV2CleanupProof(
            removal_returncodes=tuple(removal_returncodes),
            exact_name_list_proofs=name_list_proofs,
            exact_name_inspect_proofs=name_inspect_proofs,
            exact_id_inspect_proofs=id_inspect_proofs,
            expected_id_inspect_proofs=expected_id_proofs,
            cleanup_authorized=True,
            daemon_rebound=daemon_rebound,
            binary_rebound=binary_rebound,
            config_rebound=config_rebound,
        )

    def _assert_unstarted_container_by_id(
        self,
        context: _RunContext,
        identity: str,
        *,
        timeout_seconds: float,
    ) -> None:
        result = self._execute(
            context,
            _docker_command(
                context,
                "container",
                "inspect",
                _STATE_JSON_FORMAT,
                _required_identity(identity),
            ),
            phase="cleanup-container-state-proof",
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )
        if result.returncode != 0 or result.stderr:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-cleanup-state-unverified"
            )
        state = _parse_json_object(
            result.stdout, "docker-supervisor-v2-cleanup-state-unverified"
        )
        expected = {
            "Status": "created",
            "Running": False,
            "Paused": False,
            "Restarting": False,
            "OOMKilled": False,
            "Dead": False,
            "Pid": 0,
            "ExitCode": 0,
            "Error": "",
            "StartedAt": "0001-01-01T00:00:00Z",
            "FinishedAt": "0001-01-01T00:00:00Z",
        }
        if set(state) != set(expected) or any(
            type(state[key]) is not type(value) or state[key] != value
            for key, value in expected.items()
        ):
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-cleanup-container-not-created"
            )

    def _inspect_identity(
        self,
        context: _RunContext,
        *,
        kind: str,
        target: str,
        expected_name: str,
        allow_absent: bool,
        phase: str,
        timeout_seconds: float,
    ) -> str | None:
        if kind not in {"container", "network"}:
            raise AssertionError("unsupported Docker resource kind")
        result = self._execute(
            context,
            _docker_command(context, kind, "inspect", _INSPECT_IDENTITY_FORMAT, target),
            phase=phase,
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )
        if _is_exact_not_found(result, kind=kind, target=target):
            if allow_absent:
                return None
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-resource-unexpectedly-absent"
            )
        if result.returncode != 0 or result.stderr:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-resource-inspect-unverified"
            )
        line = _decode_line(
            result.stdout, "docker-supervisor-v2-resource-inspect-unverified"
        )
        try:
            observed_id, observed_name = line.split("|", 1)
        except ValueError:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-resource-inspect-unverified"
            ) from None
        if _IDENTITY.fullmatch(observed_id) is None:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-resource-inspect-unverified"
            )
        normalized_name = f"/{expected_name}" if kind == "container" else expected_name
        if observed_name != normalized_name:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-resource-identity-mismatch"
            )
        if _IDENTITY.fullmatch(target) is not None and observed_id != target:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-resource-identity-mismatch"
            )
        return observed_id

    def _execute(
        self,
        context: _RunContext,
        command: tuple[str, ...],
        *,
        phase: str,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
        retain_outputs: bool = False,
        marks_create_submission: bool = False,
    ) -> DockerCommandResult:
        _validate_command(
            context.docker_executable,
            command,
            docker_config_directory=context.docker_config_directory,
            docker_host=context.docker_host,
        )
        started = _read_clock(context, prior=context.last_finished)
        remaining = context.deadline - started
        if remaining <= 0:
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-absolute-deadline-exceeded"
            )
        command_timeout = min(float(timeout_seconds), remaining)
        if marks_create_submission:
            context.ownership_ambiguous = True
        try:
            result = context.executor.execute(
                command,
                stdin=b"",
                timeout_seconds=command_timeout,
                stdout_limit=stdout_limit,
                stderr_limit=stderr_limit,
                environment={},
            )
        except BaseException as exc:
            finished, timing_complete = _finish_clock(context, started)
            context.captures.append(
                _capture_command(
                    context,
                    phase=phase,
                    command=command,
                    result=None,
                    started=started,
                    finished=finished,
                    stdout_limit=stdout_limit,
                    stderr_limit=stderr_limit,
                    timing_complete=timing_complete,
                    retain_outputs=retain_outputs,
                )
            )
            if _is_cancellation(exc):
                raise
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-executor-failed"
            ) from None
        finished, timing_complete = _finish_clock(context, started)
        capture = _capture_command(
            context,
            phase=phase,
            command=command,
            result=result,
            started=started,
            finished=finished,
            stdout_limit=stdout_limit,
            stderr_limit=stderr_limit,
            timing_complete=timing_complete,
            retain_outputs=retain_outputs,
        )
        context.captures.append(capture)
        if not capture.transport_complete or not capture.timing_complete:
            result = None
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-command-capture-incomplete"
            )
        if finished > context.deadline:
            result = None
            raise CodexDockerSupervisorV2Error(
                "docker-supervisor-v2-absolute-deadline-exceeded"
            )
        assert isinstance(result, DockerCommandResult)
        return result


def _capture_command(
    context: _RunContext,
    *,
    phase: str,
    command: tuple[str, ...],
    result: object,
    started: float,
    finished: float,
    stdout_limit: int,
    stderr_limit: int,
    timing_complete: bool,
    retain_outputs: bool,
) -> CodexDockerSupervisorV2CommandCapture:
    valid_result = isinstance(result, DockerCommandResult)
    returncode = result.returncode if valid_result else -1
    stdout_value = result.stdout if valid_result else b""
    stderr_value = result.stderr if valid_result else b""
    rc_valid = (
        isinstance(returncode, int)
        and not isinstance(returncode, bool)
        and -(2**31) <= returncode < 2**31
    )
    stdout_valid = isinstance(stdout_value, bytes)
    stderr_valid = isinstance(stderr_value, bytes)
    stdout = stdout_value if stdout_valid else b""
    stderr = stderr_value if stderr_valid else b""
    stdout_count = len(stdout)
    stderr_count = len(stderr)
    transport_complete = (
        valid_result
        and rc_valid
        and stdout_valid
        and stderr_valid
        and stdout_count <= stdout_limit
        and stderr_count <= stderr_limit
    )
    command_bytes = _canonical_json_bytes(list(command))
    return CodexDockerSupervisorV2CommandCapture(
        ordinal=len(context.captures),
        phase=phase,
        command=command,
        command_sha256=hashlib.sha256(command_bytes).hexdigest(),
        returncode=returncode if rc_valid else -1,
        stdout=stdout[:stdout_limit] if retain_outputs else b"",
        stderr=stderr[:stderr_limit] if retain_outputs else b"",
        stdout_observed_bytes=stdout_count,
        stderr_observed_bytes=stderr_count,
        stdout_sha256=hashlib.sha256(stdout).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr).hexdigest(),
        started_monotonic=started,
        finished_monotonic=finished,
        transport_complete=transport_complete,
        timing_complete=timing_complete,
        stdout_retained=retain_outputs,
        stderr_retained=retain_outputs,
    )


def _build_audit(
    context: _RunContext,
    *,
    binary: CodexDockerSupervisorV2BinaryBinding,
    capture_complete: bool,
) -> CodexDockerSupervisorV2Audit:
    command_documents = []
    for capture in context.captures:
        command_documents.append(
            {
                "ordinal": capture.ordinal,
                "phase": capture.phase,
                "command": list(capture.command),
                "command_sha256": capture.command_sha256,
                "returncode": capture.returncode,
                "stdout_observed_bytes": capture.stdout_observed_bytes,
                "stderr_observed_bytes": capture.stderr_observed_bytes,
                "stdout_sha256": capture.stdout_sha256,
                "stderr_sha256": capture.stderr_sha256,
                "started_monotonic": format(capture.started_monotonic, ".17g"),
                "finished_monotonic": format(capture.finished_monotonic, ".17g"),
                "transport_complete": capture.transport_complete,
                "timing_complete": capture.timing_complete,
                "stdout_retained": capture.stdout_retained,
                "stderr_retained": capture.stderr_retained,
            }
        )
    daemon_document = None
    if context.daemon is not None:
        daemon_document = {
            name: getattr(context.daemon, name)
            for name in (
                "daemon_id_bytes",
                "daemon_id_sha256",
                "server_version",
                "client_api_version",
                "server_api_version",
            )
        }
    document = {
        "contract": f"rwb-codex-docker-supervisor/{CODEX_DOCKER_SUPERVISOR_V2_VERSION}",
        "plan_sha256": context.plan_sha256,
        "transaction_deadline_monotonic": format(context.transaction_deadline, ".17g"),
        "cleanup_deadline_monotonic": (
            None
            if context.cleanup_deadline is None
            else format(context.cleanup_deadline, ".17g")
        ),
        "binary": {
            "executable": binary.executable,
            "resolved_executable": binary.resolved_executable,
            "byte_count": binary.byte_count,
            "sha256": binary.sha256,
        },
        "daemon": daemon_document,
        "commands": command_documents,
    }
    all_captures_complete = all(
        capture.transport_complete and capture.timing_complete
        for capture in context.captures
    )
    return CodexDockerSupervisorV2Audit(
        plan_sha256=context.plan_sha256,
        binary=binary,
        daemon=context.daemon,
        commands=tuple(context.captures),
        transcript_sha256=hashlib.sha256(_canonical_json_bytes(document)).hexdigest(),
        transaction_deadline_monotonic=context.transaction_deadline,
        cleanup_deadline_monotonic=context.cleanup_deadline,
        capture_complete=capture_complete and all_captures_complete,
    )


def _reconcile_attestation(
    attestation: CodexDockerTopologyV2Attestation,
    identities: Mapping[str, str | None],
    plan: CodexDockerTopologyV2Plan,
) -> None:
    if (
        attestation.inspect_validation_complete is not True
        or attestation.capture_complete is not False
        or attestation.attempt_sha256 != plan.attempt_sha256
        or attestation.proxy_url != plan.proxy_url
    ):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-inspect-validation-incomplete"
        )
    expected = {
        "runtime": attestation.runtime_container_id,
        "proxy": attestation.proxy_container_id,
        "internal": attestation.internal_network_id,
        "egress": attestation.egress_network_id,
    }
    if any(identities[role] != identity for role, identity in expected.items()):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-attested-identity-mismatch"
        )


def _resources(
    plan: CodexDockerTopologyV2Plan,
) -> tuple[tuple[str, str, str], ...]:
    return (
        ("runtime", "container", plan.runtime_container),
        ("proxy", "container", plan.proxy_container),
        ("internal", "network", plan.internal_network),
        ("egress", "network", plan.egress_network),
    )


def _hash_supervisor_plan(
    plan: CodexDockerSupervisorV2Plan,
    transaction: CodexDockerTopologyV2Transaction,
) -> str:
    topology = plan.topology
    document = {
        "contract": f"rwb-codex-docker-supervisor/{CODEX_DOCKER_SUPERVISOR_V2_VERSION}",
        "topology_version": CODEX_DOCKER_TOPOLOGY_V2_VERSION,
        "plan": {
            "topology": {
                field.name: getattr(topology, field.name) for field in fields(topology)
            },
            "docker_config_directory": plan.docker_config_directory,
            "docker_host": plan.docker_host,
        },
        "commands": {
            "preflight_absence": [
                list(_freeze_command(plan, command))
                for command in transaction.preflight_absence
            ],
            "create": [
                list(_freeze_command(plan, command)) for command in transaction.create
            ],
            "attest": [
                list(_freeze_command(plan, command)) for command in transaction.attest
            ],
            "start": [],
            "cleanup_policy": "captured-reconciled-identities-only",
            "ignored_topology_cleanup_sha256": hashlib.sha256(
                _canonical_json_bytes(
                    [list(command) for command in transaction.cleanup]
                )
            ).hexdigest(),
            "final_absence": [
                list(_freeze_command(plan, command))
                for command in transaction.final_absence
            ],
        },
    }
    return hashlib.sha256(_canonical_json_bytes(document)).hexdigest()


def _validate_inert_transaction(
    plan: CodexDockerSupervisorV2Plan,
    transaction: CodexDockerTopologyV2Transaction,
) -> None:
    if (
        len(transaction.preflight_absence) != 4
        or len(transaction.create) != 5
        or len(transaction.attest) != 3
        or transaction.start != ()
        or len(transaction.final_absence) != 4
    ):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-transaction-plan-invalid"
        )
    for phase in (
        transaction.preflight_absence,
        transaction.create,
        transaction.attest,
        transaction.start,
        transaction.final_absence,
    ):
        for command in phase:
            frozen = _freeze_command(plan, command)
            _validate_command(
                plan.topology.docker_executable,
                frozen,
                docker_config_directory=plan.docker_config_directory,
                docker_host=plan.docker_host,
            )


def _validate_command(
    docker_executable: str,
    command: tuple[str, ...],
    *,
    docker_config_directory: str,
    docker_host: str,
) -> None:
    if (
        len(command) < 6
        or command[0] != docker_executable
        or command[1:5] != ("--config", docker_config_directory, "--host", docker_host)
        or any(
            not isinstance(part, str) or not part or "\x00" in part for part in command
        )
    ):
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-command-invalid")
    if _command_has_live_verb(command):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-live-command-forbidden"
        )
    if any(part in {"--attach", "--attach=true"} for part in command):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-live-command-forbidden"
        )
    if any(_SECRET_ASSIGNMENT.search(part) is not None for part in command):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-secret-command-forbidden"
        )


def _command_has_live_verb(command: tuple[str, ...]) -> bool:
    if len(command) < 6:
        return True
    forbidden_verbs = {"start", "attach", "exec", "run", "context"}
    return command[5] in forbidden_verbs or (
        len(command) > 6 and command[5] == "container" and command[6] in forbidden_verbs
    )


def _freeze_command(
    plan: CodexDockerSupervisorV2Plan, command: tuple[str, ...]
) -> tuple[str, ...]:
    if not command or command[0] != plan.topology.docker_executable:
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-command-invalid")
    return (
        command[0],
        "--config",
        plan.docker_config_directory,
        "--host",
        plan.docker_host,
        *command[1:],
    )


def _freeze_topology_command(
    context: _RunContext, command: tuple[str, ...]
) -> tuple[str, ...]:
    if not command or command[0] != context.docker_executable:
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-command-invalid")
    return _docker_command(context, *command[1:])


def _docker_command(context: _RunContext, *arguments: str) -> tuple[str, ...]:
    return (
        context.docker_executable,
        "--config",
        context.docker_config_directory,
        "--host",
        context.docker_host,
        *arguments,
    )


def _validate_supervisor_plan(plan: CodexDockerSupervisorV2Plan) -> None:
    if not isinstance(plan, CodexDockerSupervisorV2Plan):
        raise TypeError("plan must be a CodexDockerSupervisorV2Plan")
    if not isinstance(plan.topology, CodexDockerTopologyV2Plan):
        raise TypeError("topology must be a CodexDockerTopologyV2Plan")
    if (
        _is_remote_filesystem_path(plan.topology.docker_executable)
        or not Path(plan.topology.docker_executable).is_absolute()
    ):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-docker-binary-not-absolute"
        )
    _validate_blank_config_directory(plan)
    host = plan.docker_host
    if not isinstance(host, str) or not host or "\x00" in host or len(host) > 512:
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-docker-host-invalid")
    npipe_valid = host == "npipe:////./pipe/docker_engine"
    unix_valid = host.startswith("unix:///") and _canonical_unix_socket_host(host)
    platform_local = npipe_valid if os.name == "nt" else unix_valid
    if not platform_local:
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-docker-host-must-be-local"
        )


def _validate_blank_config_directory(plan: CodexDockerSupervisorV2Plan) -> None:
    value = plan.docker_config_directory
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > 1024:
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-config-directory-invalid"
        )
    candidate = Path(value)
    if _is_remote_filesystem_path(value):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-config-directory-must-be-local"
        )
    stem = plan.topology.runtime_container.removeprefix("rwb-cp2-runtime-")
    expected_name = f"rwb-cp2-docker-config-{stem}"
    try:
        absolute = os.path.abspath(os.fspath(candidate))
        resolved = os.fspath(candidate.resolve(strict=True))
        first_entry = next(candidate.iterdir(), None)
    except OSError:
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-config-directory-invalid"
        ) from None
    if (
        not candidate.is_absolute()
        or not candidate.is_dir()
        or os.path.normcase(absolute) != os.path.normcase(resolved)
        or candidate.name != expected_name
        or first_entry is not None
    ):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-config-directory-not-private-blank"
        )


def _canonical_unix_socket_host(host: str) -> bool:
    path = host.removeprefix("unix://")
    if (
        not path.startswith("/")
        or path == "/"
        or not path.endswith(".sock")
        or "//" in path
        or "\\" in path
        or "?" in path
        or "#" in path
    ):
        return False
    parts = path.split("/")
    return all(part not in {".", ".."} for part in parts if part)


def _is_remote_filesystem_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return normalized.startswith(("//", "//?/"))


def _bind_docker_binary(executable: str) -> CodexDockerSupervisorV2BinaryBinding:
    if not isinstance(executable, str) or not executable or "\x00" in executable:
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-docker-binary-invalid")
    candidate = Path(executable)
    if _is_remote_filesystem_path(executable) or not candidate.is_absolute():
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-docker-binary-not-absolute"
        )
    try:
        absolute = os.path.abspath(os.fspath(candidate))
        resolved = os.fspath(candidate.resolve(strict=True))
        stat = candidate.stat()
    except OSError:
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-docker-binary-invalid"
        ) from None
    if (
        os.path.normcase(absolute) != os.path.normcase(resolved)
        or not candidate.is_file()
        or candidate.name.casefold() not in {"docker", "docker.exe"}
        or stat.st_size <= 0
        or stat.st_size > _MAX_DOCKER_BINARY_BYTES
    ):
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-docker-binary-invalid")
    digest = hashlib.sha256()
    observed = 0
    try:
        with candidate.open("rb") as stream:
            while True:
                chunk = stream.read(_BINARY_CHUNK_BYTES)
                if not chunk:
                    break
                observed += len(chunk)
                if observed > _MAX_DOCKER_BINARY_BYTES:
                    raise ValueError
                digest.update(chunk)
    except (OSError, ValueError):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-docker-binary-invalid"
        ) from None
    if observed != stat.st_size:
        raise CodexDockerSupervisorV2Error("docker-supervisor-v2-docker-binary-changed")
    return CodexDockerSupervisorV2BinaryBinding(
        executable=executable,
        resolved_executable=resolved,
        byte_count=observed,
        sha256=digest.hexdigest(),
    )


def _bind_docker_binary_bounded(
    context: _RunContext, executable: str
) -> CodexDockerSupervisorV2BinaryBinding:
    _checkpoint_local_operation(context)
    binding = _bind_docker_binary(executable)
    _checkpoint_local_operation(context)
    return binding


def _validate_blank_config_directory_bounded(
    context: _RunContext, plan: CodexDockerSupervisorV2Plan
) -> None:
    _checkpoint_local_operation(context)
    _validate_blank_config_directory(plan)
    _checkpoint_local_operation(context)


def _parse_json_object(payload: bytes, code: str) -> Mapping[str, object]:
    if not isinstance(payload, bytes) or len(payload) > _CONTROL_STDOUT_LIMIT:
        raise CodexDockerSupervisorV2Error(code)
    try:
        text = payload.decode("utf-8", errors="strict")
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_number,
            parse_float=_parse_finite_json_float,
        )
    except (
        UnicodeError,
        json.JSONDecodeError,
        RecursionError,
        TypeError,
        ValueError,
    ):
        raise CodexDockerSupervisorV2Error(code) from None
    if not isinstance(document, Mapping):
        raise CodexDockerSupervisorV2Error(code)
    return document


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("duplicate JSON key")
        document[key] = value
    return document


def _reject_nonfinite_json_number(value: str) -> object:
    raise ValueError(f"non-finite JSON number: {value}")


def _parse_finite_json_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON float")
    return parsed


def _require_text(
    source: Mapping[str, object], pattern_key: str, pattern: re.Pattern[str], code: str
) -> str:
    value = source.get(pattern_key)
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise CodexDockerSupervisorV2Error(code)
    return value


def _read_initial_clock(clock: Callable[[], float]) -> float:
    try:
        value = clock()
    except Exception:  # noqa: BLE001 - normalize an injected clock boundary
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-monotonic-clock-invalid"
        ) from None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-monotonic-clock-invalid"
        )
    return float(value)


def _checkpoint_local_operation(context: _RunContext) -> float:
    value = _read_clock(context, prior=context.last_finished)
    context.last_finished = value
    if value > context.deadline:
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-absolute-deadline-exceeded"
        )
    return value


def _begin_cleanup_deadline(context: _RunContext) -> None:
    started = _read_clock(context, prior=context.last_finished)
    context.last_finished = started
    context.cleanup_deadline = started + CODEX_DOCKER_SUPERVISOR_V2_MAX_CLEANUP_SECONDS
    context.deadline = context.cleanup_deadline


def _read_clock(context: _RunContext, *, prior: float | None) -> float:
    try:
        value = context.clock()
    except Exception:  # noqa: BLE001 - normalize an injected clock boundary
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-monotonic-clock-invalid"
        ) from None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (prior is not None and value < prior)
    ):
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-monotonic-clock-invalid"
        )
    return float(value)


def _finish_clock(context: _RunContext, started: float) -> tuple[float, bool]:
    try:
        finished = _read_clock(context, prior=started)
    except CodexDockerSupervisorV2Error:
        context.last_finished = started
        return started, False
    context.last_finished = finished
    return finished, True


def _decode_identity(payload: bytes, code: str) -> str:
    value = _decode_line(payload, code)
    if _IDENTITY.fullmatch(value) is None:
        raise CodexDockerSupervisorV2Error(code)
    return value


def _decode_line(payload: bytes, code: str) -> str:
    try:
        value = payload.decode("utf-8", errors="strict")
    except UnicodeError:
        raise CodexDockerSupervisorV2Error(code) from None
    normalized = value.replace("\r\n", "\n")
    if not normalized.endswith("\n") or "\n" in normalized[:-1]:
        raise CodexDockerSupervisorV2Error(code)
    line = normalized[:-1]
    if not line or line != line.strip():
        raise CodexDockerSupervisorV2Error(code)
    return line


def _required_identity(value: str) -> str:
    if not isinstance(value, str) or _IDENTITY.fullmatch(value) is None:
        raise CodexDockerSupervisorV2Error(
            "docker-supervisor-v2-resource-identity-missing"
        )
    return value


def _is_cancellation(value: BaseException) -> bool:
    return isinstance(
        value,
        (KeyboardInterrupt, SystemExit, GeneratorExit, asyncio.CancelledError),
    )


def _attach_audit(
    error: BaseException | None, audit: CodexDockerSupervisorV2Audit
) -> None:
    if error is None:
        return
    try:
        error.audit = audit  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        pass


def _is_exact_not_found(result: DockerCommandResult, *, kind: str, target: str) -> bool:
    if result.returncode != 1 or result.stdout.strip():
        return False
    expected = (
        f"Error response from daemon: No such container: {target}\n"
        if kind == "container"
        else f"Error response from daemon: network {target} not found\n"
    ).encode("ascii")
    return result.stderr.replace(b"\r\n", b"\n") == expected


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")


def _validate_timeout(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout must be within the Coding Plan ceiling")
