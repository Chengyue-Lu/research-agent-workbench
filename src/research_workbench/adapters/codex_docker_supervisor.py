"""Transactional, no-start supervisor for the Coding Plan Docker topology.

This module composes the already frozen image and network contracts.  It does
not enable a live provider lane: there is no credential input, no default
executor, and neither container is started.  In particular, this module does
not assume the legacy JavaScript proxy readiness interface.  The reviewed
proxy requires frozen internal and peer IP arguments that the current shared
topology contract cannot yet express.  A future live supervisor needs a
separate interface review and must not turn the switch here into a bypass.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from research_workbench.adapters.codex_coding_plan import (
    CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS,
)
from research_workbench.adapters.codex_coding_plan_docker import (
    DockerCommandResult,
)
from research_workbench.adapters.codex_docker_network import (
    CODEX_DOCKER_NETWORK_LIVE_READY,
    CodexDockerNetworkAttestation,
    CodexDockerNetworkError,
    CodexDockerNetworkPlan,
    attest_codex_docker_network,
    build_topology_absence_commands,
    build_topology_attestation_commands,
    build_topology_create_commands,
)

CODEX_DOCKER_SUPERVISOR_LIVE_READY = False

_IDENTITY = re.compile(r"[0-9a-f]{64}\Z")
_CONTROL_STDOUT_LIMIT = 8_192
_CONTROL_STDERR_LIMIT = 16_384
_ATTESTATION_STDOUT_LIMIT = 262_144
_INSPECT_IDENTITY_FORMAT = "--format={{.Id}}|{{.Name}}"


class CodexDockerSupervisorError(RuntimeError):
    """Stable fail-closed orchestration error without captured daemon output."""


class CodexDockerSupervisorCleanupError(CodexDockerSupervisorError):
    """Closeout error that retains primary and cleanup failures separately."""

    def __init__(
        self,
        *,
        primary_error: BaseException | None,
        cleanup_error: BaseException,
    ) -> None:
        super().__init__("docker-supervisor-cleanup-unverified")
        self.primary_error = primary_error
        self.cleanup_error = cleanup_error

    def __repr__(self) -> str:
        return (
            "CodexDockerSupervisorCleanupError('docker-supervisor-cleanup-unverified')"
        )


class DockerSupervisorExecutor(Protocol):
    """Bounded injectable command boundary; no real runner is supplied here."""

    def execute(
        self,
        command: tuple[str, ...],
        *,
        stdin: bytes,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
    ) -> DockerCommandResult: ...


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorCleanupProof:
    """Evidence that every removal and every independent proof was attempted."""

    removal_returncodes: tuple[int, ...]
    exact_name_list_proofs: int
    exact_name_inspect_proofs: int
    exact_id_inspect_proofs: int
    absence_verified: bool
    capture_complete: bool


@dataclass(frozen=True, slots=True)
class CodexDockerSupervisorResult:
    """Identity-only result of one cleaned-up, no-start transaction."""

    attestation: CodexDockerNetworkAttestation
    proxy_started: bool
    runtime_started: bool
    start_blocked_reason: str
    cleanup: CodexDockerSupervisorCleanupProof
    capture_complete: bool = True


class CodexDockerTopologySupervisor:
    """Create, attest, and unconditionally remove one unstarted topology."""

    def __init__(self, *, executor: DockerSupervisorExecutor) -> None:
        if executor is None:
            raise TypeError("executor is required")
        self._executor = executor

    def run_offline_transaction(
        self,
        plan: CodexDockerNetworkPlan,
        *,
        timeout_seconds: float = 30.0,
    ) -> CodexDockerSupervisorResult:
        """Create and attest topology, then stop before either container starts."""

        _validate_timeout(timeout_seconds)
        if CODEX_DOCKER_NETWORK_LIVE_READY:
            raise CodexDockerSupervisorError("docker-network-contract-unexpected-live")

        create_commands = build_topology_create_commands(plan)
        if len(create_commands) != 5:
            raise CodexDockerSupervisorError("docker-create-plan-invalid")

        identities: dict[str, str | None] = {
            "runtime": None,
            "proxy": None,
            "internal": None,
            "egress": None,
        }
        primary_error: BaseException | None = None
        outcome: CodexDockerNetworkAttestation | None = None
        transaction_started = False
        try:
            self._assert_preflight_absent(plan, timeout_seconds=timeout_seconds)
            transaction_started = True
            identities["internal"] = self._create_identity(
                create_commands[0], timeout_seconds=timeout_seconds
            )
            identities["egress"] = self._create_identity(
                create_commands[1], timeout_seconds=timeout_seconds
            )
            identities["proxy"] = self._create_identity(
                create_commands[2], timeout_seconds=timeout_seconds
            )
            self._reconcile_container(
                plan,
                name=plan.proxy_container,
                expected_id=_required_identity(identities["proxy"]),
            )
            self._execute_empty_success(
                create_commands[3], timeout_seconds=timeout_seconds
            )
            identities["runtime"] = self._create_identity(
                create_commands[4], timeout_seconds=timeout_seconds
            )
            self._reconcile_container(
                plan,
                name=plan.runtime_container,
                expected_id=_required_identity(identities["runtime"]),
            )

            attestation = self._attest(plan, timeout_seconds=timeout_seconds)
            _reconcile_attestation(attestation, identities)
            outcome = attestation
        except BaseException as exc:  # noqa: BLE001 - closeout also on cancellation
            primary_error = exc

        cleanup: CodexDockerSupervisorCleanupProof | None = None
        cleanup_error: BaseException | None = None
        if transaction_started:
            try:
                cleanup = self._cleanup_verified(
                    plan,
                    identities=identities,
                    timeout_seconds=timeout_seconds,
                )
            except BaseException as exc:  # noqa: BLE001 - retain both failures
                cleanup_error = exc
        if cleanup_error is not None:
            combined = CodexDockerSupervisorCleanupError(
                primary_error=primary_error,
                cleanup_error=cleanup_error,
            )
            raise combined from cleanup_error
        if primary_error is not None:
            raise primary_error
        assert outcome is not None
        assert cleanup is not None
        return CodexDockerSupervisorResult(
            attestation=outcome,
            proxy_started=False,
            runtime_started=False,
            start_blocked_reason="docker-proxy-ip-interface-not-frozen",
            cleanup=cleanup,
            capture_complete=outcome.capture_complete and cleanup.capture_complete,
        )

    def run_live(self, *args: object, **kwargs: object) -> None:
        """Reject all live inputs before inspecting them."""

        del args, kwargs
        raise CodexDockerSupervisorError("docker-supervisor-live-disabled")

    def _create_identity(
        self, command: tuple[str, ...], *, timeout_seconds: float
    ) -> str:
        result = self._execute(
            command,
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )
        if result.returncode != 0 or result.stderr:
            raise CodexDockerSupervisorError("docker-create-command-failed")
        return _decode_identity(result.stdout, "docker-create-identity-invalid")

    def _execute_empty_success(
        self, command: tuple[str, ...], *, timeout_seconds: float
    ) -> None:
        result = self._execute(
            command,
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )
        if result.returncode != 0 or result.stdout.strip() or result.stderr:
            raise CodexDockerSupervisorError("docker-network-connect-failed")

    def _reconcile_container(
        self,
        plan: CodexDockerNetworkPlan,
        *,
        name: str,
        expected_id: str,
    ) -> None:
        for target in (name, expected_id):
            observed = self._inspect_identity(
                plan,
                kind="container",
                target=target,
                expected_name=name,
                allow_absent=False,
                timeout_seconds=5.0,
            )
            if observed != expected_id:
                raise CodexDockerSupervisorError(
                    "docker-container-identity-reconcile-failed"
                )

    def _attest(
        self, plan: CodexDockerNetworkPlan, *, timeout_seconds: float
    ) -> CodexDockerNetworkAttestation:
        commands = build_topology_attestation_commands(plan)
        if len(commands) != 3:
            raise CodexDockerSupervisorError("docker-attestation-plan-invalid")
        observations: list[DockerCommandResult] = []
        for command in commands:
            result = self._execute(
                command,
                timeout_seconds=timeout_seconds,
                stdout_limit=_ATTESTATION_STDOUT_LIMIT,
                stderr_limit=_CONTROL_STDERR_LIMIT,
            )
            if result.returncode != 0 or result.stderr:
                raise CodexDockerSupervisorError("docker-attestation-command-failed")
            observations.append(result)
        try:
            return attest_codex_docker_network(
                plan,
                image_inspect_json=observations[0].stdout,
                container_inspect_json=observations[1].stdout,
                network_inspect_json=observations[2].stdout,
            )
        except CodexDockerNetworkError:
            raise CodexDockerSupervisorError(
                "docker-topology-attestation-failed"
            ) from None

    def _assert_preflight_absent(
        self, plan: CodexDockerNetworkPlan, *, timeout_seconds: float
    ) -> None:
        """Refuse to create or clean up when any exact transaction name exists."""

        resources = (
            ("container", plan.runtime_container),
            ("container", plan.proxy_container),
            ("network", plan.internal_network),
            ("network", plan.egress_network),
        )
        absence_commands = build_topology_absence_commands(plan)
        if len(absence_commands) != len(resources):
            raise CodexDockerSupervisorError("docker-preflight-plan-invalid")
        for command in absence_commands:
            result = self._execute(
                command,
                timeout_seconds=min(timeout_seconds, 5.0),
                stdout_limit=_CONTROL_STDOUT_LIMIT,
                stderr_limit=_CONTROL_STDERR_LIMIT,
            )
            if result.returncode != 0 or result.stdout.strip() or result.stderr:
                raise CodexDockerSupervisorError("docker-preflight-resource-not-absent")
        for kind, name in resources:
            observed = self._inspect_identity(
                plan,
                kind=kind,
                target=name,
                expected_name=name,
                allow_absent=True,
                timeout_seconds=min(timeout_seconds, 5.0),
            )
            if observed is not None:
                raise CodexDockerSupervisorError("docker-preflight-resource-not-absent")

    def _cleanup_verified(
        self,
        plan: CodexDockerNetworkPlan,
        *,
        identities: Mapping[str, str | None],
        timeout_seconds: float,
    ) -> CodexDockerSupervisorCleanupProof:
        discovered = dict(identities)
        uncertainty = False
        resources = (
            ("runtime", "container", plan.runtime_container),
            ("proxy", "container", plan.proxy_container),
            ("internal", "network", plan.internal_network),
            ("egress", "network", plan.egress_network),
        )

        # Never acquire an identity by name after an ambiguous create.  A
        # same-name resource could have won a race after the absence preflight.
        # Unknown identities are left untouched and make the final absence
        # proof fail closed instead of risking deletion of another owner.
        removal_returncodes: list[int] = []
        cleanup_commands = _build_identity_cleanup_commands(plan, discovered)
        for command in cleanup_commands:
            try:
                result = self._execute(
                    command,
                    timeout_seconds=min(timeout_seconds, 10.0),
                    stdout_limit=_CONTROL_STDOUT_LIMIT,
                    stderr_limit=_CONTROL_STDERR_LIMIT,
                )
            except BaseException:  # noqa: BLE001 - attempt every removal
                removal_returncodes.append(-1)
                uncertainty = True
            else:
                removal_returncodes.append(result.returncode)
                if result.returncode != 0 or result.stderr:
                    uncertainty = True

        name_list_proofs = 0
        for command in build_topology_absence_commands(plan):
            try:
                result = self._execute(
                    command,
                    timeout_seconds=5.0,
                    stdout_limit=_CONTROL_STDOUT_LIMIT,
                    stderr_limit=_CONTROL_STDERR_LIMIT,
                )
            except BaseException:  # noqa: BLE001 - run every remaining proof
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
        for _, kind, name in resources:
            try:
                observed = self._inspect_identity(
                    plan,
                    kind=kind,
                    target=name,
                    expected_name=name,
                    allow_absent=True,
                    timeout_seconds=min(timeout_seconds, 5.0),
                )
            except BaseException:  # noqa: BLE001 - run every remaining proof
                uncertainty = True
                continue
            if observed is None:
                name_inspect_proofs += 1
            else:
                uncertainty = True

        id_inspect_proofs = 0
        for role, kind, name in resources:
            identity = discovered[role]
            if identity is None:
                continue
            try:
                observed = self._inspect_identity(
                    plan,
                    kind=kind,
                    target=identity,
                    expected_name=name,
                    allow_absent=True,
                    timeout_seconds=min(timeout_seconds, 5.0),
                )
            except BaseException:  # noqa: BLE001 - run every remaining proof
                uncertainty = True
                continue
            if observed is None:
                id_inspect_proofs += 1
            else:
                uncertainty = True

        if (
            uncertainty
            or len(removal_returncodes) != len(cleanup_commands)
            or name_list_proofs != 4
            or name_inspect_proofs != 4
            or id_inspect_proofs
            != sum(identity is not None for identity in discovered.values())
        ):
            raise CodexDockerSupervisorError("docker-supervisor-cleanup-unverified")
        return CodexDockerSupervisorCleanupProof(
            removal_returncodes=tuple(removal_returncodes),
            exact_name_list_proofs=name_list_proofs,
            exact_name_inspect_proofs=name_inspect_proofs,
            exact_id_inspect_proofs=id_inspect_proofs,
            absence_verified=True,
            capture_complete=True,
        )

    def _inspect_identity(
        self,
        plan: CodexDockerNetworkPlan,
        *,
        kind: str,
        target: str,
        expected_name: str,
        allow_absent: bool,
        timeout_seconds: float,
    ) -> str | None:
        if kind not in {"container", "network"}:
            raise AssertionError("unsupported Docker resource kind")
        result = self._execute(
            (
                plan.docker_executable,
                kind,
                "inspect",
                _INSPECT_IDENTITY_FORMAT,
                target,
            ),
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )
        if _is_exact_not_found(result, kind=kind, target=target):
            if allow_absent:
                return None
            raise CodexDockerSupervisorError("docker-resource-unexpectedly-absent")
        if result.returncode != 0 or result.stderr:
            raise CodexDockerSupervisorError("docker-resource-inspect-unverified")
        line = _decode_line(result.stdout, "docker-resource-inspect-unverified")
        try:
            observed_id, observed_name = line.split("|", 1)
        except ValueError:
            raise CodexDockerSupervisorError(
                "docker-resource-inspect-unverified"
            ) from None
        if _IDENTITY.fullmatch(observed_id) is None:
            raise CodexDockerSupervisorError("docker-resource-inspect-unverified")
        expected_observed_name = (
            f"/{expected_name}" if kind == "container" else expected_name
        )
        if observed_name != expected_observed_name:
            raise CodexDockerSupervisorError("docker-resource-identity-mismatch")
        if _IDENTITY.fullmatch(target) is not None and observed_id != target:
            raise CodexDockerSupervisorError("docker-resource-identity-mismatch")
        return observed_id

    def _execute(
        self,
        command: tuple[str, ...],
        *,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
    ) -> DockerCommandResult:
        if not command or any(
            not isinstance(part, str) or not part for part in command
        ):
            raise CodexDockerSupervisorError("docker-supervisor-command-invalid")
        try:
            result = self._executor.execute(
                command,
                stdin=b"",
                timeout_seconds=timeout_seconds,
                stdout_limit=stdout_limit,
                stderr_limit=stderr_limit,
            )
        except Exception:  # noqa: BLE001 - normalize the injected trust boundary
            raise CodexDockerSupervisorError(
                "docker-supervisor-executor-failed"
            ) from None
        if not isinstance(result, DockerCommandResult):
            raise CodexDockerSupervisorError("docker-supervisor-result-invalid")
        if (
            isinstance(result.returncode, bool)
            or not isinstance(result.returncode, int)
            or not isinstance(result.stdout, bytes)
            or not isinstance(result.stderr, bytes)
            or len(result.stdout) > stdout_limit
            or len(result.stderr) > stderr_limit
        ):
            raise CodexDockerSupervisorError("docker-supervisor-result-invalid")
        return result


def _reconcile_attestation(
    attestation: CodexDockerNetworkAttestation,
    identities: Mapping[str, str | None],
) -> None:
    if attestation.capture_complete is not True:
        raise CodexDockerSupervisorError("docker-attestation-capture-incomplete")
    expected = {
        "runtime": attestation.runtime_container_id,
        "proxy": attestation.proxy_container_id,
        "internal": attestation.internal_network_id,
        "egress": attestation.egress_network_id,
    }
    if any(identities[role] != observed for role, observed in expected.items()):
        raise CodexDockerSupervisorError("docker-attested-identity-mismatch")


def _required_identity(value: str | None) -> str:
    if value is None or _IDENTITY.fullmatch(value) is None:
        raise CodexDockerSupervisorError("docker-resource-identity-missing")
    return value


def _decode_identity(payload: bytes, code: str) -> str:
    value = _decode_line(payload, code)
    if _IDENTITY.fullmatch(value) is None:
        raise CodexDockerSupervisorError(code)
    return value


def _decode_line(payload: bytes, code: str) -> str:
    try:
        value = payload.decode("utf-8", errors="strict")
    except UnicodeError:
        raise CodexDockerSupervisorError(code) from None
    normalized = value.replace("\r\n", "\n")
    if not normalized.endswith("\n") or "\n" in normalized[:-1]:
        raise CodexDockerSupervisorError(code)
    line = normalized[:-1]
    if not line or line != line.strip():
        raise CodexDockerSupervisorError(code)
    return line


def _is_exact_not_found(result: DockerCommandResult, *, kind: str, target: str) -> bool:
    if result.returncode != 1 or result.stdout.strip():
        return False
    expected = (
        f"Error response from daemon: No such container: {target}\n"
        if kind == "container"
        else f"Error response from daemon: network {target} not found\n"
    ).encode("ascii")
    return _normalize_newlines(result.stderr) == expected


def _normalize_newlines(value: bytes) -> bytes:
    return value.replace(b"\r\n", b"\n")


def _validate_timeout(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
        or value > CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout must be within the Coding Plan ceiling")


def _build_identity_cleanup_commands(
    plan: CodexDockerNetworkPlan,
    identities: Mapping[str, str | None],
) -> tuple[tuple[str, ...], ...]:
    """Remove only identities explicitly returned by this transaction."""

    commands: list[tuple[str, ...]] = []
    for role in ("runtime", "proxy"):
        identity = identities[role]
        if identity is not None:
            commands.append(
                (
                    plan.docker_executable,
                    "container",
                    "rm",
                    "--force",
                    "--volumes",
                    _required_identity(identity),
                )
            )
    for role in ("internal", "egress"):
        identity = identities[role]
        if identity is not None:
            commands.append(
                (
                    plan.docker_executable,
                    "network",
                    "rm",
                    _required_identity(identity),
                )
            )
    return tuple(commands)
