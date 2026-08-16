"""Fail-closed Docker host for the Codex GLM-5.3 Coding Plan runtime.

This module is deliberately separate from the native process contract.  It
provides a bounded, no-key isolation probe and freezes a future credential
transport without enabling provider egress.  Every container created here has
``network=none`` and no host bind mount, so this is not yet a live provider
adapter and cannot close K-API-2.

The only supported live entry point fails before consulting an environment
mapping.  Enabling egress requires a separately reviewed destination-restricted
transport; changing ``network=none`` in this module is not an acceptable
shortcut.
"""

from __future__ import annotations

import os
import re
import subprocess
import threading
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from research_workbench.adapters.codex_coding_plan import (
    CODEX_CODING_PLAN_ALLOWED_SOURCE_CREDENTIAL_ENVS,
    CODEX_CODING_PLAN_MAX_JSONL_BYTES,
    CODEX_CODING_PLAN_MAX_PROMPT_BYTES,
    CODEX_CODING_PLAN_MAX_STDERR_BYTES,
    CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS,
    CodexCodingPlanRunResult,
    CodexCodingPlanRuntimeError,
    parse_codex_coding_plan_jsonl,
)

CODEX_CODING_PLAN_DOCKER_BASE_IMAGE = (
    "node@sha256:968df39aedcea65eeb078fb336ed7191baf48f972b4479711397108be0966920"
)
CODEX_CODING_PLAN_DOCKER_CLI_VERSION = "0.124.0"
CODEX_CODING_PLAN_DOCKER_NPM_INTEGRITY = (
    "sha512-1EVAuPyAQZ8zIVMw3bPJ6a4R8ifLAZ7LGsOyknj5c2he9AFXVRCmWx12WrdZJ25"
    "wcBvOEKt1n1Zx+QAj0EVGbQ=="
)
CODEX_CODING_PLAN_DOCKER_LIVE_READY = False

_CONTAINER_UID = 65_532
_CONTAINER_GID = 65_532
_CONTAINER_MEMORY_BYTES = 536_870_912
_CONTAINER_PIDS = 64
_CONTAINER_CPUS = "1"
_CONTAINER_NOFILE = "64:64"
_PROBE_STDOUT_LIMIT = 32_768
_CONTROL_STDOUT_LIMIT = 8_192
_CONTROL_STDERR_LIMIT = 16_384
_MAX_CREDENTIAL_BYTES = 16_384
_FRAME_MAGIC = b"RWBCP001"
_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
_CONTAINER_NAME = re.compile(r"rwb-cp-[0-9a-f]{32}\Z")
_ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


@dataclass(frozen=True, slots=True, repr=False)
class DockerCommandResult:
    """Bounded observation of one Docker CLI command."""

    returncode: int
    stdout: bytes
    stderr: bytes

    def __repr__(self) -> str:
        """Never copy captured provider output into incidental diagnostics."""

        return (
            "DockerCommandResult("
            f"returncode={self.returncode}, "
            f"stdout=<{len(self.stdout)} bytes>, "
            f"stderr=<{len(self.stderr)} bytes>)"
        )


class DockerCleanupUnverifiedError(CodexCodingPlanRuntimeError):
    """Stable closeout failure retaining both primary and cleanup evidence."""

    def __init__(
        self,
        *,
        primary_error: BaseException | None,
        cleanup_error: BaseException,
    ) -> None:
        super().__init__("docker-cleanup-unverified")
        self.primary_error = primary_error
        self.cleanup_error = cleanup_error

    def __repr__(self) -> str:
        return "DockerCleanupUnverifiedError('docker-cleanup-unverified')"


class DockerCommandExecutor(Protocol):
    """Small injectable boundary used by deterministic no-network tests."""

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
class CodexCodingPlanDockerProbeResult:
    """Attested shape returned by the image's zero-credential probe."""

    image_id: str
    container_id: str
    raw_json: str


class _SecretStdinPayload:
    """One-shot mutable secret transport with a deliberately redacted repr."""

    __slots__ = ("_consumed", "_payload")

    def __init__(self, payload: bytearray) -> None:
        self._payload = payload
        self._consumed = False

    def __repr__(self) -> str:
        return "_SecretStdinPayload(<redacted>)"

    def _consume(self) -> bytearray:
        if self._consumed:
            raise CodexCodingPlanRuntimeError("credential-frame-already-consumed")
        self._consumed = True
        payload = self._payload
        self._payload = bytearray()
        return payload


def _build_credential_frame(credential: str, prompt: str) -> _SecretStdinPayload:
    """Build a private, redacted, one-shot stdin frame for a future live host."""

    if not isinstance(credential, str) or not credential or "\x00" in credential:
        raise CodexCodingPlanRuntimeError("credential-invalid")
    if not isinstance(prompt, str) or not prompt.strip() or "\x00" in prompt:
        raise ValueError("prompt must be non-empty text without NUL")
    try:
        credential_bytes = credential.encode("utf-8", errors="strict")
        prompt_bytes = prompt.encode("utf-8", errors="strict")
    except UnicodeError:
        raise CodexCodingPlanRuntimeError("docker-frame-invalid-encoding") from None
    if len(credential_bytes) > _MAX_CREDENTIAL_BYTES:
        raise CodexCodingPlanRuntimeError("credential-byte-limit-exceeded")
    if len(prompt_bytes) > CODEX_CODING_PLAN_MAX_PROMPT_BYTES:
        raise CodexCodingPlanRuntimeError("prompt-byte-limit-exceeded")
    if credential in prompt:
        raise CodexCodingPlanRuntimeError("credential-present-in-prompt")
    return _SecretStdinPayload(
        bytearray(
            b"".join(
                (
                    _FRAME_MAGIC,
                    len(credential_bytes).to_bytes(4, "big"),
                    credential_bytes,
                    len(prompt_bytes).to_bytes(4, "big"),
                    prompt_bytes,
                )
            )
        )
    )


def assert_no_exact_credential_disclosure(
    credential: str,
    *,
    stdout: bytes | bytearray | memoryview | str = b"",
    stderr: bytes | bytearray | memoryview | str = b"",
    error: BaseException | None = None,
) -> None:
    """Fail closed if the exact credential occurs in captured output/errors.

    This intentionally performs exact matching, not heuristic secret detection.
    The raised error never contains the credential or the offending observation.
    """

    if not isinstance(credential, str) or not credential or "\x00" in credential:
        raise CodexCodingPlanRuntimeError("credential-invalid")
    try:
        encoded = bytearray(credential.encode("utf-8", errors="strict"))
    except UnicodeError:
        raise CodexCodingPlanRuntimeError("credential-invalid") from None

    def contains(value: bytes | bytearray | memoryview | str) -> bool:
        if isinstance(value, str):
            return credential in value
        return bytes(encoded) in bytes(value)

    disclosed = contains(stdout) or contains(stderr)
    seen: set[int] = set()
    current = error
    while not disclosed and current is not None and id(current) not in seen:
        seen.add(id(current))
        disclosed = credential in str(current)
        current = current.__cause__ or current.__context__
    encoded[:] = b"\x00" * len(encoded)
    if disclosed:
        raise CodexCodingPlanRuntimeError("credential-disclosure-detected")


def build_docker_create_command(
    *,
    docker_executable: str | Path,
    image_id: str,
    container_name: str,
    mode: str = "probe",
) -> tuple[str, ...]:
    """Build the immutable, mount-free, network-none container command."""

    executable = _resolve_docker_executable(docker_executable)
    _validate_image_id(image_id)
    _validate_container_name(container_name)
    if mode not in {"probe", "run"}:
        raise ValueError("mode must be probe or run")

    return (
        executable,
        "create",
        "--pull=never",
        f"--name={container_name}",
        "--network=none",
        "--read-only",
        f"--user={_CONTAINER_UID}:{_CONTAINER_GID}",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--ipc=none",
        f"--pids-limit={_CONTAINER_PIDS}",
        f"--memory={_CONTAINER_MEMORY_BYTES}",
        f"--memory-swap={_CONTAINER_MEMORY_BYTES}",
        f"--cpus={_CONTAINER_CPUS}",
        f"--ulimit=nofile={_CONTAINER_NOFILE}",
        "--ulimit=core=0:0",
        "--stop-timeout=1",
        "--log-driver=none",
        "--workdir=/workspace",
        "--env=HOME=/codex-home",
        "--env=CODEX_HOME=/codex-home",
        "--env=NO_COLOR=1",
        "--env=RUST_BACKTRACE=0",
        "--tmpfs=/workspace:rw,noexec,nosuid,nodev,size=16777216,uid=65532,gid=65532,mode=700",
        "--tmpfs=/codex-home:rw,noexec,nosuid,nodev,size=16777216,uid=65532,gid=65532,mode=700",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16777216,uid=65532,gid=65532,mode=700",
        "--entrypoint=/runtime/entrypoint.mjs",
        image_id,
        f"--{mode}",
    )


class BoundedDockerCommandExecutor:
    """Run Docker CLI commands with incremental output and wall-clock ceilings."""

    def __init__(self, *, environment: Mapping[str, str] | None = None) -> None:
        source = os.environ if environment is None else environment
        self._environment = {
            key: source[key]
            for key in ("SYSTEMROOT", "WINDIR")
            if isinstance(source.get(key), str) and source[key]
        }

    def execute(
        self,
        command: tuple[str, ...],
        *,
        stdin: bytes,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
    ) -> DockerCommandResult:
        _validate_process_request(
            command,
            stdin=stdin,
            timeout_seconds=timeout_seconds,
            stdout_limit=stdout_limit,
            stderr_limit=stderr_limit,
        )
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self._environment,
                shell=False,
                creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
            )
        except (OSError, ValueError):
            raise CodexCodingPlanRuntimeError("docker-process-start-failed") from None

        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None
        stdout = bytearray()
        stderr = bytearray()
        violation: list[str] = []
        violation_event = threading.Event()

        def read_stream(
            stream: object, target: bytearray, limit: int, code: str
        ) -> None:
            try:
                while True:
                    chunk = stream.read(4096)  # type: ignore[attr-defined]
                    if not chunk:
                        return
                    if len(target) + len(chunk) > limit:
                        remaining = max(0, limit - len(target))
                        target.extend(chunk[:remaining])
                        violation.append(code)
                        violation_event.set()
                        return
                    target.extend(chunk)
            except OSError:
                violation.append("docker-output-read-failed")
                violation_event.set()

        def write_stdin() -> None:
            try:
                if stdin:
                    process.stdin.write(stdin)
                    process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            finally:
                try:
                    process.stdin.close()
                except OSError:
                    pass

        readers = (
            threading.Thread(
                target=read_stream,
                args=(
                    process.stdout,
                    stdout,
                    stdout_limit,
                    "docker-stdout-limit-exceeded",
                ),
                daemon=True,
            ),
            threading.Thread(
                target=read_stream,
                args=(
                    process.stderr,
                    stderr,
                    stderr_limit,
                    "docker-stderr-limit-exceeded",
                ),
                daemon=True,
            ),
        )
        writer = threading.Thread(target=write_stdin, daemon=True)
        for thread in readers:
            thread.start()
        writer.start()

        deadline = time.monotonic() + timeout_seconds
        failure_code: str | None = None
        while process.poll() is None:
            if violation_event.wait(0.02):
                failure_code = violation[0]
                break
            if time.monotonic() >= deadline:
                failure_code = "docker-process-timeout"
                break
        if failure_code is not None:
            process.kill()
        try:
            returncode = process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2.0)
            failure_code = failure_code or "docker-process-termination-failed"
            returncode = process.returncode
        for thread in readers:
            thread.join(timeout=2.0)
        writer.join(timeout=2.0)
        if writer.is_alive():
            try:
                process.stdin.close()
            except (OSError, ValueError):
                pass
            writer.join(timeout=2.0)
        if violation and failure_code is None:
            failure_code = violation[0]
        if any(thread.is_alive() for thread in readers):
            failure_code = failure_code or "docker-output-drain-failed"
        if writer.is_alive():
            failure_code = failure_code or "docker-stdin-writer-not-terminated"
        try:
            process.stdout.close()
            process.stderr.close()
        except OSError:
            failure_code = failure_code or "docker-output-close-failed"
        if failure_code is not None:
            raise CodexCodingPlanRuntimeError(failure_code)
        return DockerCommandResult(
            returncode=int(returncode),
            stdout=bytes(stdout),
            stderr=bytes(stderr),
        )


class CodexCodingPlanDockerHost:
    """No-key Docker isolation host; provider networking remains disabled."""

    def __init__(
        self,
        *,
        docker_executable: str | Path,
        image_id: str,
        executor: DockerCommandExecutor | None = None,
    ) -> None:
        self._docker_executable = _resolve_docker_executable(docker_executable)
        self._image_id = _validate_image_id(image_id)
        self._executor = executor or BoundedDockerCommandExecutor()

    def probe(
        self, *, timeout_seconds: float = 30.0
    ) -> CodexCodingPlanDockerProbeResult:
        """Run the baked zero-key probe with no network and no host mount."""

        _validate_timeout(timeout_seconds)
        inspected = self._execute_control(
            (
                self._docker_executable,
                "image",
                "inspect",
                "--format={{.Id}}",
                self._image_id,
            ),
            timeout_seconds=timeout_seconds,
        )
        observed_image = _decode_single_line(
            inspected.stdout, "docker-image-id-invalid"
        )
        if (
            inspected.returncode != 0
            or inspected.stderr
            or observed_image != self._image_id
        ):
            raise CodexCodingPlanRuntimeError("docker-image-identity-mismatch")

        container_name = f"rwb-cp-{uuid.uuid4().hex}"
        create_command = build_docker_create_command(
            docker_executable=self._docker_executable,
            image_id=self._image_id,
            container_name=container_name,
            mode="probe",
        )
        create_submitted = False
        container_id = ""
        primary_error: BaseException | None = None
        probe_result: CodexCodingPlanDockerProbeResult | None = None
        try:
            # Once create is submitted, cleanup by the collision-resistant name
            # even if Docker's response is truncated or the client times out.
            create_submitted = True
            create = self._execute_control(
                create_command, timeout_seconds=timeout_seconds
            )
            if create.returncode != 0 or create.stderr:
                raise CodexCodingPlanRuntimeError("docker-create-failed")
            candidate_id = _decode_single_line(
                create.stdout, "docker-container-id-invalid"
            )
            if not _CONTAINER_ID.fullmatch(candidate_id):
                raise CodexCodingPlanRuntimeError("docker-create-failed")
            container_id = candidate_id
            observed = self._inspect_container(container_name)
            if observed is None or observed != candidate_id:
                raise CodexCodingPlanRuntimeError("docker-container-reconcile-failed")
            started = self._executor.execute(
                (
                    self._docker_executable,
                    "start",
                    "--attach",
                    "--interactive",
                    container_id,
                ),
                stdin=b"",
                timeout_seconds=timeout_seconds,
                stdout_limit=_PROBE_STDOUT_LIMIT,
                stderr_limit=_CONTROL_STDERR_LIMIT,
            )
            if started.returncode != 0 or started.stderr:
                raise CodexCodingPlanRuntimeError("docker-probe-failed")
            raw_json = _decode_single_line(
                started.stdout, "docker-probe-output-invalid"
            )
            _validate_probe_json(raw_json)
            probe_result = CodexCodingPlanDockerProbeResult(
                image_id=self._image_id,
                container_id=container_id,
                raw_json=raw_json,
            )
        except BaseException as exc:  # noqa: BLE001 - cleanup also on cancellation
            primary_error = exc
        cleanup_error: BaseException | None = None
        if create_submitted:
            try:
                self._cleanup_verified(
                    container_name,
                    expected_id=container_id or None,
                    timeout_seconds=timeout_seconds,
                )
            except BaseException as exc:  # noqa: BLE001 - retain cleanup evidence
                cleanup_error = exc
        if cleanup_error is not None:
            combined = DockerCleanupUnverifiedError(
                primary_error=primary_error,
                cleanup_error=cleanup_error,
            )
            raise combined from cleanup_error
        if primary_error is not None:
            raise primary_error
        assert probe_result is not None
        return probe_result

    def run_live_from_environment(
        self,
        prompt: str,
        *,
        credential_env: str,
        environment: Mapping[str, str] | None = None,
    ) -> CodexCodingPlanRunResult:
        """Fail before credential lookup until restricted egress is reviewed."""

        del prompt, credential_env, environment
        raise CodexCodingPlanRuntimeError("docker-live-network-not-ready")

    @staticmethod
    def parse_runtime_jsonl(payload: str) -> CodexCodingPlanRunResult:
        """Delegate protocol validation to the existing immutable parser."""

        return parse_codex_coding_plan_jsonl(payload)

    def _execute_control(
        self, command: tuple[str, ...], *, timeout_seconds: float
    ) -> DockerCommandResult:
        return self._executor.execute(
            command,
            stdin=b"",
            timeout_seconds=timeout_seconds,
            stdout_limit=_CONTROL_STDOUT_LIMIT,
            stderr_limit=_CONTROL_STDERR_LIMIT,
        )

    def _inspect_container(self, target: str) -> str | None:
        inspected = self._execute_control(
            (
                self._docker_executable,
                "container",
                "inspect",
                "--format={{.Id}}|{{.Name}}",
                target,
            ),
            timeout_seconds=5.0,
        )
        if inspected.returncode == 1 and not inspected.stdout.strip():
            expected = (
                f"Error response from daemon: No such container: {target}\n".encode(
                    "ascii"
                )
            )
            if inspected.stderr.replace(b"\r\n", b"\n") == expected:
                return None
        if inspected.returncode != 0 or inspected.stderr:
            raise CodexCodingPlanRuntimeError("docker-container-inspect-unverified")
        observation = _decode_single_line(
            inspected.stdout, "docker-container-inspect-unverified"
        )
        try:
            observed_id, observed_name = observation.split("|", 1)
        except ValueError:
            raise CodexCodingPlanRuntimeError(
                "docker-container-inspect-unverified"
            ) from None
        if not _CONTAINER_ID.fullmatch(observed_id):
            raise CodexCodingPlanRuntimeError("docker-container-inspect-unverified")
        if not observed_name.startswith("/"):
            raise CodexCodingPlanRuntimeError("docker-container-inspect-unverified")
        if _CONTAINER_NAME.fullmatch(target) and observed_name != f"/{target}":
            raise CodexCodingPlanRuntimeError("docker-container-identity-mismatch")
        return observed_id

    def _cleanup_verified(
        self,
        container_name: str,
        *,
        expected_id: str | None,
        timeout_seconds: float,
    ) -> None:
        """Remove only the reconciled container and prove both handles vanished."""

        try:
            observed_id = self._inspect_container(container_name)
        except BaseException as exc:
            raise CodexCodingPlanRuntimeError("docker-cleanup-unverified") from exc
        if observed_id is None:
            if (
                expected_id is not None
                and self._inspect_container(expected_id) is not None
            ):
                raise CodexCodingPlanRuntimeError("docker-cleanup-unverified")
            return
        if expected_id is not None and observed_id != expected_id:
            raise CodexCodingPlanRuntimeError("docker-cleanup-unverified")
        target_id = observed_id
        try:
            self._execute_control(
                (self._docker_executable, "kill", target_id),
                timeout_seconds=min(timeout_seconds, 5.0),
            )
        except CodexCodingPlanRuntimeError:
            pass
        try:
            self._execute_control(
                (self._docker_executable, "rm", "--force", target_id),
                timeout_seconds=min(timeout_seconds, 10.0),
            )
        except CodexCodingPlanRuntimeError:
            pass
        try:
            name_observation = self._inspect_container(container_name)
            id_observation = self._inspect_container(target_id)
        except BaseException as exc:
            raise CodexCodingPlanRuntimeError("docker-cleanup-unverified") from exc
        if name_observation is not None or id_observation is not None:
            raise CodexCodingPlanRuntimeError("docker-cleanup-unverified")


def _resolve_docker_executable(path: str | Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError("docker_executable must be an absolute docker.exe path")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError:
        raise ValueError("docker_executable must exist") from None
    if not resolved.is_file() or resolved.name.casefold() != "docker.exe":
        raise ValueError("docker_executable must be an absolute docker.exe path")
    return os.fspath(resolved)


def _validate_image_id(image_id: str) -> str:
    if not isinstance(image_id, str) or not _IMAGE_ID.fullmatch(image_id):
        raise ValueError("image_id must be an immutable sha256 image ID")
    return image_id


def _validate_container_name(name: str) -> str:
    if not isinstance(name, str) or not _CONTAINER_NAME.fullmatch(name):
        raise ValueError("container_name must be generated by this Docker host")
    return name


def _validate_timeout(value: float) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or value <= 0
        or value > CODEX_CODING_PLAN_MAX_TIMEOUT_SECONDS
    ):
        raise ValueError("timeout must be within the Coding Plan ceiling")


def _validate_process_request(
    command: Sequence[str],
    *,
    stdin: bytes,
    timeout_seconds: float,
    stdout_limit: int,
    stderr_limit: int,
) -> None:
    if not command or not all(isinstance(item, str) and item for item in command):
        raise ValueError("command must contain non-empty text arguments")
    _resolve_docker_executable(command[0])
    if not isinstance(stdin, bytes):
        raise TypeError("stdin must be bytes")
    _validate_timeout(timeout_seconds)
    for value in (stdout_limit, stderr_limit):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError("output limits must be positive integers")
    if stdout_limit > CODEX_CODING_PLAN_MAX_JSONL_BYTES:
        raise ValueError("stdout limit exceeds the Coding Plan capture ceiling")
    if stderr_limit > CODEX_CODING_PLAN_MAX_STDERR_BYTES:
        raise ValueError("stderr limit exceeds the Coding Plan capture ceiling")


def _decode_single_line(payload: bytes, code: str) -> str:
    try:
        value = payload.decode("utf-8", errors="strict").strip()
    except UnicodeError:
        raise CodexCodingPlanRuntimeError(code) from None
    if not value or "\n" in value or "\r" in value:
        raise CodexCodingPlanRuntimeError(code)
    return value


def _validate_probe_json(payload: str) -> None:
    import json

    try:
        document = json.loads(payload)
    except json.JSONDecodeError:
        raise CodexCodingPlanRuntimeError("docker-probe-output-invalid") from None
    expected = {
        "schema": "rwb-codex-coding-plan-docker-probe/0.1",
        "uid": _CONTAINER_UID,
        "gid": _CONTAINER_GID,
        "network_interfaces": ["lo"],
        "rootfs_read_only": True,
        "workspace_tmpfs_writable": True,
        "host_paths_absent": True,
        "docker_socket_absent": True,
        "credential_observed": False,
        "core_dump_limit_zero": True,
    }
    if not isinstance(document, dict) or any(
        document.get(key) != value for key, value in expected.items()
    ):
        raise CodexCodingPlanRuntimeError("docker-probe-attestation-failed")
    cap_eff = document.get("cap_eff")
    no_new_privs = document.get("no_new_privs")
    seccomp = document.get("seccomp")
    if cap_eff != "0000000000000000" or no_new_privs != 1 or seccomp != 2:
        raise CodexCodingPlanRuntimeError("docker-probe-attestation-failed")


def validate_credential_environment_name(name: str) -> str:
    """Public validation helper for a future reviewed live host."""

    if not isinstance(name, str) or not _ENVIRONMENT_NAME.fullmatch(name):
        raise ValueError("credential_env must be a portable environment variable name")
    if name not in CODEX_CODING_PLAN_ALLOWED_SOURCE_CREDENTIAL_ENVS:
        raise ValueError("credential_env must be an approved Coding Plan key source")
    return name
