"""Fail-closed Docker topology contract for the Codex Coding Plan lane.

This module only freezes names, Docker CLI commands, daemon observations, and
cleanup evidence.  It deliberately provides no subprocess executor, proxy
socket, credential transport, or live-ready switch.  A caller may inject an
executor for deterministic tests or for a separately reviewed supervisor.

The runtime has one endpoint on an ``--internal`` bridge.  A separately named
proxy has endpoints on that bridge and on a dedicated egress bridge.  This is
topology isolation, not destination authorization: a later proxy
implementation must independently enforce the provider allowlist.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

CODEX_DOCKER_NETWORK_LIVE_READY = False
CODEX_DOCKER_PROXY_ALIAS = "rwb-egress-proxy"
CODEX_DOCKER_PROXY_PORT = 3128
CODEX_DOCKER_RUNTIME_PROXY_URL = (
    f"http://{CODEX_DOCKER_PROXY_ALIAS}:{CODEX_DOCKER_PROXY_PORT}"
)

_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTAINER_ID = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_NAME = re.compile(r"rwb-cp-(?:rt|px|in|eg)-[0-9a-f]{12}-[0-9a-f]{32}\Z")
_NONCE = re.compile(r"[0-9a-f]{32}\Z")

_CONTAINER_UID = 65_532
_CONTAINER_GID = 65_532
_MEMORY_BYTES = 536_870_912
_NANO_CPUS = 1_000_000_000
_PIDS_LIMIT = 64
_NOFILE = 64
_TMPFS_SIZE = 16_777_216
_SECURITY_OPT = "no-new-privileges:true"
_ATTEMPT_LABEL = "org.rwb.attempt-sha256"
_SCOPE_LABEL = "org.rwb.scope"
_SCOPE_VALUE = "codex-coding-plan"

_EMPTY_HOST_CONFIG_FIELDS = (
    "Binds",
    "CapAdd",
    "DeviceCgroupRules",
    "DeviceRequests",
    "Devices",
    "Dns",
    "DnsOptions",
    "DnsSearch",
    "ExtraHosts",
    "GroupAdd",
    "Links",
    "VolumesFrom",
)
_SECRET_ENV_NAME = re.compile(
    r"(?:api[_-]?key|credential|password|secret|token|authorization)",
    re.IGNORECASE,
)


class CodexDockerNetworkError(RuntimeError):
    """Stable fail-closed error for topology or cleanup drift."""


@dataclass(frozen=True, slots=True, repr=False)
class DockerControlResult:
    """One bounded Docker control-plane observation."""

    returncode: int
    stdout: bytes
    stderr: bytes

    def __repr__(self) -> str:
        return (
            "DockerControlResult("
            f"returncode={self.returncode}, "
            f"stdout=<{len(self.stdout)} bytes>, "
            f"stderr=<{len(self.stderr)} bytes>)"
        )


class DockerControlExecutor(Protocol):
    """Injectable boundary; this module intentionally supplies no real runner."""

    def execute(self, command: tuple[str, ...]) -> DockerControlResult: ...


@dataclass(frozen=True, slots=True)
class CodexDockerNetworkPlan:
    """Immutable names and identities for one Attempt topology."""

    docker_executable: str
    attempt_sha256: str
    runtime_image_id: str
    proxy_image_id: str
    runtime_container: str
    proxy_container: str
    internal_network: str
    egress_network: str
    proxy_url: str = CODEX_DOCKER_RUNTIME_PROXY_URL

    def __post_init__(self) -> None:
        _validate_plan(self)


@dataclass(frozen=True, slots=True)
class CodexDockerNetworkAttestation:
    """Identity-only result of a complete daemon topology observation."""

    attempt_sha256: str
    runtime_container_id: str
    proxy_container_id: str
    internal_network_id: str
    egress_network_id: str
    proxy_url: str
    capture_complete: bool = True


@dataclass(frozen=True, slots=True)
class CodexDockerCleanupProof:
    """Final exact-name absence proof after idempotent cleanup commands."""

    attempted_commands: int
    removal_returncodes: tuple[int, ...]
    absence_verified: bool
    capture_complete: bool


def build_codex_docker_network_plan(
    *,
    docker_executable: str | Path,
    attempt_id: str,
    runtime_image_id: str,
    proxy_image_id: str,
    nonce: str | None = None,
) -> CodexDockerNetworkPlan:
    """Create collision-resistant, path-safe names without exposing Attempt text."""

    executable = _resolve_docker_executable(docker_executable)
    if (
        not isinstance(attempt_id, str)
        or not attempt_id.strip()
        or "\x00" in attempt_id
    ):
        raise ValueError("attempt_id must be non-empty text without NUL")
    try:
        encoded_attempt = attempt_id.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValueError("attempt_id must be valid UTF-8 text") from None
    if len(encoded_attempt) > 512:
        raise ValueError("attempt_id exceeds the fixed byte ceiling")
    attempt_sha256 = hashlib.sha256(encoded_attempt).hexdigest()
    entropy = uuid.uuid4().hex if nonce is None else nonce
    if not isinstance(entropy, str) or _NONCE.fullmatch(entropy) is None:
        raise ValueError("nonce must be 32 lowercase hexadecimal characters")
    stem = f"{attempt_sha256[:12]}-{entropy}"
    return CodexDockerNetworkPlan(
        docker_executable=executable,
        attempt_sha256=attempt_sha256,
        runtime_image_id=_validate_image_id(runtime_image_id),
        proxy_image_id=_validate_image_id(proxy_image_id),
        runtime_container=f"rwb-cp-rt-{stem}",
        proxy_container=f"rwb-cp-px-{stem}",
        internal_network=f"rwb-cp-in-{stem}",
        egress_network=f"rwb-cp-eg-{stem}",
    )


def build_topology_create_commands(
    plan: CodexDockerNetworkPlan,
) -> tuple[tuple[str, ...], ...]:
    """Build, but do not run, the complete immutable topology setup."""

    _validate_plan(plan)
    docker = plan.docker_executable
    labels = (
        f"--label={_SCOPE_LABEL}={_SCOPE_VALUE}",
        f"--label={_ATTEMPT_LABEL}={plan.attempt_sha256}",
    )
    internal = (
        docker,
        "network",
        "create",
        "--driver=bridge",
        "--internal",
        "--attachable=false",
        "--ipv6=false",
        "--opt=com.docker.network.bridge.enable_ip_masquerade=false",
        *labels,
        plan.internal_network,
    )
    egress = (
        docker,
        "network",
        "create",
        "--driver=bridge",
        "--attachable=false",
        "--ipv6=false",
        *labels,
        plan.egress_network,
    )
    proxy = _build_container_create_command(plan, role="proxy")
    connect_proxy_egress = (
        docker,
        "network",
        "connect",
        "--gw-priority=1",
        plan.egress_network,
        plan.proxy_container,
    )
    runtime = _build_container_create_command(plan, role="runtime")
    return internal, egress, proxy, connect_proxy_egress, runtime


def build_topology_attestation_commands(
    plan: CodexDockerNetworkPlan,
) -> tuple[tuple[str, ...], ...]:
    """Build exact image/container/network inspect commands."""

    _validate_plan(plan)
    images = tuple(dict.fromkeys((plan.runtime_image_id, plan.proxy_image_id)))
    docker = plan.docker_executable
    return (
        (docker, "image", "inspect", *images),
        (
            docker,
            "container",
            "inspect",
            plan.runtime_container,
            plan.proxy_container,
        ),
        (
            docker,
            "network",
            "inspect",
            plan.internal_network,
            plan.egress_network,
        ),
    )


def attest_codex_docker_network(
    plan: CodexDockerNetworkPlan,
    *,
    image_inspect_json: bytes | str,
    container_inspect_json: bytes | str,
    network_inspect_json: bytes | str,
) -> CodexDockerNetworkAttestation:
    """Validate a complete Docker daemon observation with no inferred fields."""

    _validate_plan(plan)
    images = _parse_json_array(image_inspect_json, "docker-image-inspect-invalid")
    containers = _parse_json_array(
        container_inspect_json, "docker-container-inspect-invalid"
    )
    networks = _parse_json_array(network_inspect_json, "docker-network-inspect-invalid")

    expected_images = {plan.runtime_image_id, plan.proxy_image_id}
    images_by_id: dict[str, Mapping[str, object]] = {}
    for item in images:
        image_id = _require_string(item, "Id", "docker-image-identity-invalid")
        if image_id in images_by_id:
            raise CodexDockerNetworkError("docker-image-identity-mismatch")
        images_by_id[image_id] = item
    observed_images = set(images_by_id)
    if observed_images != expected_images or len(images) != len(expected_images):
        raise CodexDockerNetworkError("docker-image-identity-mismatch")

    by_name: dict[str, Mapping[str, object]] = {}
    for item in containers:
        raw_name = _require_string(item, "Name", "docker-container-name-invalid")
        name = raw_name.removeprefix("/")
        if name in by_name:
            raise CodexDockerNetworkError("docker-container-name-duplicate")
        by_name[name] = item
    if set(by_name) != {plan.runtime_container, plan.proxy_container}:
        raise CodexDockerNetworkError("docker-container-set-mismatch")

    runtime_id = _attest_container(
        plan,
        by_name[plan.runtime_container],
        role="runtime",
        expected_networks=(plan.internal_network,),
        expected_image=plan.runtime_image_id,
        expected_image_labels=_attested_image_labels(
            images_by_id[plan.runtime_image_id]
        ),
    )
    proxy_id = _attest_container(
        plan,
        by_name[plan.proxy_container],
        role="proxy",
        expected_networks=(plan.internal_network, plan.egress_network),
        expected_image=plan.proxy_image_id,
        expected_image_labels=_attested_image_labels(images_by_id[plan.proxy_image_id]),
    )

    by_network_name: dict[str, Mapping[str, object]] = {}
    for item in networks:
        name = _require_string(item, "Name", "docker-network-name-invalid")
        if name in by_network_name:
            raise CodexDockerNetworkError("docker-network-name-duplicate")
        by_network_name[name] = item
    if set(by_network_name) != {plan.internal_network, plan.egress_network}:
        raise CodexDockerNetworkError("docker-network-set-mismatch")

    internal_id = _attest_network(
        plan,
        by_network_name[plan.internal_network],
        internal=True,
        expected_members={
            runtime_id: plan.runtime_container,
            proxy_id: plan.proxy_container,
        },
    )
    egress_id = _attest_network(
        plan,
        by_network_name[plan.egress_network],
        internal=False,
        expected_members={proxy_id: plan.proxy_container},
    )
    _attest_endpoint_network_ids(
        by_name[plan.runtime_container],
        {plan.internal_network: internal_id},
    )
    _attest_endpoint_network_ids(
        by_name[plan.proxy_container],
        {plan.internal_network: internal_id, plan.egress_network: egress_id},
    )
    return CodexDockerNetworkAttestation(
        attempt_sha256=plan.attempt_sha256,
        runtime_container_id=runtime_id,
        proxy_container_id=proxy_id,
        internal_network_id=internal_id,
        egress_network_id=egress_id,
        proxy_url=plan.proxy_url,
    )


def attest_codex_docker_network_with_executor(
    plan: CodexDockerNetworkPlan,
    executor: DockerControlExecutor,
) -> CodexDockerNetworkAttestation:
    """Collect the three exact observations through an injected executor."""

    results = tuple(
        executor.execute(command)
        for command in build_topology_attestation_commands(plan)
    )
    for result in results:
        if result.returncode != 0 or result.stderr:
            raise CodexDockerNetworkError("docker-attestation-command-failed")
    return attest_codex_docker_network(
        plan,
        image_inspect_json=results[0].stdout,
        container_inspect_json=results[1].stdout,
        network_inspect_json=results[2].stdout,
    )


def build_topology_cleanup_commands(
    plan: CodexDockerNetworkPlan,
) -> tuple[tuple[str, ...], ...]:
    """Build exact-name, idempotence-tolerant removal commands."""

    _validate_plan(plan)
    docker = plan.docker_executable
    return (
        (
            docker,
            "container",
            "rm",
            "--force",
            "--volumes",
            plan.runtime_container,
        ),
        (
            docker,
            "container",
            "rm",
            "--force",
            "--volumes",
            plan.proxy_container,
        ),
        (docker, "network", "rm", plan.internal_network),
        (docker, "network", "rm", plan.egress_network),
    )


def build_topology_absence_commands(
    plan: CodexDockerNetworkPlan,
) -> tuple[tuple[str, ...], ...]:
    """Build list queries whose successful empty output proves exact-name absence."""

    _validate_plan(plan)
    docker = plan.docker_executable
    return (
        (
            docker,
            "container",
            "ls",
            "--all",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"name=^/{plan.runtime_container}$",
        ),
        (
            docker,
            "container",
            "ls",
            "--all",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"name=^/{plan.proxy_container}$",
        ),
        (
            docker,
            "network",
            "ls",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"name=^{plan.internal_network}$",
        ),
        (
            docker,
            "network",
            "ls",
            "--quiet",
            "--no-trunc",
            "--filter",
            f"name=^{plan.egress_network}$",
        ),
    )


def cleanup_codex_docker_network_with_executor(
    plan: CodexDockerNetworkPlan,
    executor: DockerControlExecutor,
) -> CodexDockerCleanupProof:
    """Attempt all removals, then require four successful empty list queries."""

    removal_returncodes: list[int] = []
    for command in build_topology_cleanup_commands(plan):
        try:
            result = executor.execute(command)
        except Exception:  # noqa: BLE001 - every remaining cleanup must still run
            removal_returncodes.append(-1)
        else:
            removal_returncodes.append(result.returncode)
    absence_verified = True
    for command in build_topology_absence_commands(plan):
        try:
            result = executor.execute(command)
        except Exception:  # noqa: BLE001 - still run every remaining proof query
            absence_verified = False
            continue
        if result.returncode != 0 or result.stderr or result.stdout.strip():
            absence_verified = False
    if not absence_verified:
        raise CodexDockerNetworkError("docker-cleanup-absence-unverified")
    return CodexDockerCleanupProof(
        attempted_commands=len(removal_returncodes),
        removal_returncodes=tuple(removal_returncodes),
        absence_verified=True,
        capture_complete=True,
    )


def _build_container_create_command(
    plan: CodexDockerNetworkPlan, *, role: str
) -> tuple[str, ...]:
    if role == "runtime":
        name = plan.runtime_container
        image = plan.runtime_image_id
        network_args = (f"--network={plan.internal_network}",)
        role_args = (
            "--interactive",
            "--workdir=/workspace",
            "--env=HOME=/codex-home",
            "--env=CODEX_HOME=/codex-home",
            f"--env=HTTP_PROXY={plan.proxy_url}",
            f"--env=HTTPS_PROXY={plan.proxy_url}",
            "--env=NO_PROXY=",
            f"--tmpfs=/workspace:{_tmpfs_options()}",
            f"--tmpfs=/codex-home:{_tmpfs_options()}",
            "--entrypoint=/runtime/entrypoint.mjs",
        )
        tail = (image, "--run")
    elif role == "proxy":
        name = plan.proxy_container
        image = plan.proxy_image_id
        network_args = (
            f"--network={plan.internal_network}",
            f"--network-alias={CODEX_DOCKER_PROXY_ALIAS}",
        )
        role_args = (
            "--workdir=/proxy",
            "--entrypoint=/runtime/egress-proxy.mjs",
        )
        tail = (image, "--serve")
    else:
        raise ValueError("role must be runtime or proxy")
    return (
        plan.docker_executable,
        "container",
        "create",
        "--pull=never",
        f"--name={name}",
        *network_args,
        "--read-only",
        f"--user={_CONTAINER_UID}:{_CONTAINER_GID}",
        "--cap-drop=ALL",
        f"--security-opt={_SECURITY_OPT}",
        "--ipc=none",
        "--pid=private",
        f"--pids-limit={_PIDS_LIMIT}",
        f"--memory={_MEMORY_BYTES}",
        f"--memory-swap={_MEMORY_BYTES}",
        "--cpus=1",
        f"--ulimit=nofile={_NOFILE}:{_NOFILE}",
        "--ulimit=core=0:0",
        "--restart=no",
        "--log-driver=none",
        "--env=NO_COLOR=1",
        "--env=RUST_BACKTRACE=0",
        f"--tmpfs=/tmp:{_tmpfs_options()}",
        f"--label={_SCOPE_LABEL}={_SCOPE_VALUE}",
        f"--label={_ATTEMPT_LABEL}={plan.attempt_sha256}",
        *role_args,
        *tail,
    )


def _attest_container(
    plan: CodexDockerNetworkPlan,
    item: Mapping[str, object],
    *,
    role: str,
    expected_networks: tuple[str, ...],
    expected_image: str,
    expected_image_labels: Mapping[str, str],
) -> str:
    container_id = _require_string(item, "Id", "docker-container-id-invalid")
    if _CONTAINER_ID.fullmatch(container_id) is None:
        raise CodexDockerNetworkError("docker-container-id-invalid")
    if item.get("Image") != expected_image:
        raise CodexDockerNetworkError("docker-container-image-mismatch")
    config = _require_mapping(item, "Config", "docker-container-config-invalid")
    if config.get("Image") != expected_image:
        raise CodexDockerNetworkError("docker-container-image-mismatch")
    expected_name = (
        plan.runtime_container if role == "runtime" else plan.proxy_container
    )
    expected_entrypoint = (
        ["/runtime/entrypoint.mjs"]
        if role == "runtime"
        else ["/runtime/egress-proxy.mjs"]
    )
    expected_command = ["--run"] if role == "runtime" else ["--serve"]
    expected_workdir = "/workspace" if role == "runtime" else "/proxy"
    if (
        config.get("Entrypoint") != expected_entrypoint
        or config.get("Cmd") != expected_command
        or config.get("OpenStdin") is not (role == "runtime")
        or config.get("StdinOnce") is not False
        or config.get("Tty") is not False
        or config.get("User") != f"{_CONTAINER_UID}:{_CONTAINER_GID}"
        or config.get("WorkingDir") != expected_workdir
    ):
        raise CodexDockerNetworkError("docker-container-process-config-drift")
    labels = _require_mapping(config, "Labels", "docker-container-labels-invalid")
    expected_labels = {
        **expected_image_labels,
        _ATTEMPT_LABEL: plan.attempt_sha256,
        _SCOPE_LABEL: _SCOPE_VALUE,
    }
    if labels != expected_labels:
        raise CodexDockerNetworkError("docker-container-labels-mismatch")
    if not _empty(config.get("ExposedPorts")) or not _empty(config.get("Volumes")):
        raise CodexDockerNetworkError("docker-container-publish-or-volume-drift")
    _attest_environment(plan, config.get("Env"), role=role)

    host = _require_mapping(item, "HostConfig", "docker-container-host-config-invalid")
    for field in _EMPTY_HOST_CONFIG_FIELDS:
        if not _empty(host.get(field)):
            raise CodexDockerNetworkError("docker-container-host-access-drift")
    if not _empty(host.get("PortBindings")):
        raise CodexDockerNetworkError("docker-container-port-binding-drift")
    fixed_values = {
        "AutoRemove": False,
        "IpcMode": "none",
        "Memory": _MEMORY_BYTES,
        "MemorySwap": _MEMORY_BYTES,
        "NanoCpus": _NANO_CPUS,
        "NetworkMode": plan.internal_network,
        "PidMode": "private",
        "PidsLimit": _PIDS_LIMIT,
        "Privileged": False,
        "PublishAllPorts": False,
        "ReadonlyRootfs": True,
    }
    for field, expected in fixed_values.items():
        if host.get(field) != expected:
            raise CodexDockerNetworkError("docker-container-security-resource-drift")
    if host.get("CapDrop") != ["ALL"] or host.get("SecurityOpt") != [_SECURITY_OPT]:
        raise CodexDockerNetworkError("docker-container-security-resource-drift")
    if host.get("RestartPolicy") != {"Name": "no", "MaximumRetryCount": 0}:
        raise CodexDockerNetworkError("docker-container-security-resource-drift")
    log_config = host.get("LogConfig")
    if not isinstance(log_config, Mapping) or log_config.get("Type") != "none":
        raise CodexDockerNetworkError("docker-container-security-resource-drift")
    if not _empty(log_config.get("Config")):
        raise CodexDockerNetworkError("docker-container-security-resource-drift")
    if _normalized_ulimits(host.get("Ulimits")) != {
        ("core", 0, 0),
        ("nofile", _NOFILE, _NOFILE),
    }:
        raise CodexDockerNetworkError("docker-container-security-resource-drift")
    expected_tmpfs = {"/tmp": _tmpfs_options()}
    if role == "runtime":
        expected_tmpfs |= {
            "/workspace": _tmpfs_options(),
            "/codex-home": _tmpfs_options(),
        }
    if host.get("Tmpfs") != expected_tmpfs:
        raise CodexDockerNetworkError("docker-container-tmpfs-drift")
    if item.get("Mounts") not in (None, []):
        raise CodexDockerNetworkError("docker-container-mount-drift")

    network_settings = _require_mapping(
        item, "NetworkSettings", "docker-container-networks-invalid"
    )
    if not _empty(network_settings.get("Ports")):
        raise CodexDockerNetworkError("docker-container-port-binding-drift")
    observed_networks = _require_mapping(
        network_settings, "Networks", "docker-container-networks-invalid"
    )
    if set(observed_networks) != set(expected_networks):
        raise CodexDockerNetworkError("docker-container-network-set-mismatch")
    for network_name, endpoint in observed_networks.items():
        if not isinstance(endpoint, Mapping):
            raise CodexDockerNetworkError("docker-container-endpoint-invalid")
        if not _empty(endpoint.get("Links")):
            raise CodexDockerNetworkError("docker-container-host-access-drift")
        ipam = endpoint.get("IPAMConfig")
        if not _empty(ipam):
            raise CodexDockerNetworkError("docker-container-static-ip-drift")
        expected_gateway_priority = (
            1 if role == "proxy" and network_name == plan.egress_network else 0
        )
        if endpoint.get("GwPriority") != expected_gateway_priority:
            raise CodexDockerNetworkError("docker-container-gateway-priority-drift")
        aliases = endpoint.get("Aliases")
        if role == "proxy" and network_name == plan.internal_network:
            if not isinstance(aliases, Sequence) or isinstance(aliases, (str, bytes)):
                raise CodexDockerNetworkError("docker-proxy-alias-missing")
            if CODEX_DOCKER_PROXY_ALIAS not in aliases:
                raise CodexDockerNetworkError("docker-proxy-alias-missing")
    if expected_name not in {plan.runtime_container, plan.proxy_container}:
        raise AssertionError("unreachable container role")
    return container_id


def _attested_image_labels(item: Mapping[str, object]) -> dict[str, str]:
    config = _require_mapping(item, "Config", "docker-image-config-invalid")
    raw_labels = config.get("Labels")
    if raw_labels is None:
        return {}
    if not isinstance(raw_labels, Mapping):
        raise CodexDockerNetworkError("docker-image-labels-invalid")
    labels: dict[str, str] = {}
    for name, value in raw_labels.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise CodexDockerNetworkError("docker-image-labels-invalid")
        if name in {_ATTEMPT_LABEL, _SCOPE_LABEL}:
            raise CodexDockerNetworkError("docker-image-label-reserved")
        labels[name] = value
    return labels


def _attest_environment(
    plan: CodexDockerNetworkPlan, raw_environment: object, *, role: str
) -> None:
    if not isinstance(raw_environment, Sequence) or isinstance(
        raw_environment, (str, bytes)
    ):
        raise CodexDockerNetworkError("docker-container-environment-invalid")
    parsed: dict[str, str] = {}
    for raw in raw_environment:
        if not isinstance(raw, str) or "=" not in raw:
            raise CodexDockerNetworkError("docker-container-environment-invalid")
        name, value = raw.split("=", 1)
        if not name or name in parsed or _SECRET_ENV_NAME.search(name):
            raise CodexDockerNetworkError("docker-container-environment-invalid")
        parsed[name] = value
    for name, expected in {"NO_COLOR": "1", "RUST_BACKTRACE": "0"}.items():
        if parsed.get(name) != expected:
            raise CodexDockerNetworkError("docker-container-environment-drift")
    proxy_names = {"HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"}
    if role == "runtime":
        if parsed.get("HTTP_PROXY") != plan.proxy_url:
            raise CodexDockerNetworkError("docker-runtime-proxy-url-drift")
        if parsed.get("HTTPS_PROXY") != plan.proxy_url:
            raise CodexDockerNetworkError("docker-runtime-proxy-url-drift")
        if parsed.get("NO_PROXY") != "":
            raise CodexDockerNetworkError("docker-runtime-proxy-url-drift")
        if parsed.get("HOME") != "/codex-home" or parsed.get("CODEX_HOME") != (
            "/codex-home"
        ):
            raise CodexDockerNetworkError("docker-container-environment-drift")
    elif proxy_names & set(parsed):
        raise CodexDockerNetworkError("docker-proxy-recursive-proxy-drift")


def _attest_network(
    plan: CodexDockerNetworkPlan,
    item: Mapping[str, object],
    *,
    internal: bool,
    expected_members: Mapping[str, str],
) -> str:
    network_id = _require_string(item, "Id", "docker-network-id-invalid")
    if _CONTAINER_ID.fullmatch(network_id) is None:
        raise CodexDockerNetworkError("docker-network-id-invalid")
    fixed = {
        "Attachable": False,
        "Driver": "bridge",
        "EnableIPv6": False,
        "Ingress": False,
        "Internal": internal,
        "Scope": "local",
    }
    for field, expected in fixed.items():
        if item.get(field) != expected:
            raise CodexDockerNetworkError("docker-network-policy-drift")
    labels = _require_mapping(item, "Labels", "docker-network-labels-invalid")
    if labels != {
        _ATTEMPT_LABEL: plan.attempt_sha256,
        _SCOPE_LABEL: _SCOPE_VALUE,
    }:
        raise CodexDockerNetworkError("docker-network-labels-mismatch")
    expected_options = (
        {"com.docker.network.bridge.enable_ip_masquerade": "false"} if internal else {}
    )
    options = item.get("Options")
    if options is None:
        options = {}
    if options != expected_options:
        raise CodexDockerNetworkError("docker-network-options-drift")
    members = _require_mapping(item, "Containers", "docker-network-members-invalid")
    if set(members) != set(expected_members):
        raise CodexDockerNetworkError("docker-network-members-mismatch")
    for member_id, expected_name in expected_members.items():
        member = members.get(member_id)
        if not isinstance(member, Mapping) or member.get("Name") != expected_name:
            raise CodexDockerNetworkError("docker-network-members-mismatch")
    return network_id


def _attest_endpoint_network_ids(
    container: Mapping[str, object], expected: Mapping[str, str]
) -> None:
    network_settings = _require_mapping(
        container, "NetworkSettings", "docker-container-networks-invalid"
    )
    networks = _require_mapping(
        network_settings, "Networks", "docker-container-networks-invalid"
    )
    for name, expected_id in expected.items():
        endpoint = networks.get(name)
        if (
            not isinstance(endpoint, Mapping)
            or endpoint.get("NetworkID") != expected_id
        ):
            raise CodexDockerNetworkError("docker-container-network-id-mismatch")


def _parse_json_array(
    payload: bytes | str, error_code: str
) -> list[Mapping[str, object]]:
    try:
        text = (
            payload.decode("utf-8", errors="strict")
            if isinstance(payload, bytes)
            else payload
        )
        document = json.loads(text)
    except (UnicodeError, json.JSONDecodeError, TypeError):
        raise CodexDockerNetworkError(error_code) from None
    if not isinstance(document, list) or not document:
        raise CodexDockerNetworkError(error_code)
    if any(not isinstance(item, Mapping) for item in document):
        raise CodexDockerNetworkError(error_code)
    return list(document)


def _require_mapping(
    source: Mapping[str, object], key: str, error_code: str
) -> Mapping[str, object]:
    value = source.get(key)
    if not isinstance(value, Mapping):
        raise CodexDockerNetworkError(error_code)
    return value


def _require_string(source: Mapping[str, object], key: str, error_code: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise CodexDockerNetworkError(error_code)
    return value


def _normalized_ulimits(value: object) -> set[tuple[str, int, int]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return set()
    normalized: set[tuple[str, int, int]] = set()
    for item in value:
        if not isinstance(item, Mapping):
            return set()
        name, hard, soft = item.get("Name"), item.get("Hard"), item.get("Soft")
        if (
            not isinstance(name, str)
            or isinstance(hard, bool)
            or not isinstance(hard, int)
            or isinstance(soft, bool)
            or not isinstance(soft, int)
        ):
            return set()
        normalized.add((name, hard, soft))
    return normalized


def _empty(value: object) -> bool:
    return value is None or value == [] or value == {} or value == ""


def _tmpfs_options() -> str:
    return (
        "rw,noexec,nosuid,nodev,"
        f"size={_TMPFS_SIZE},uid={_CONTAINER_UID},gid={_CONTAINER_GID},mode=700"
    )


def _validate_plan(plan: CodexDockerNetworkPlan) -> None:
    executable = _resolve_docker_executable(plan.docker_executable)
    if executable != plan.docker_executable:
        raise ValueError("docker executable identity is not canonical")
    if re.fullmatch(r"[0-9a-f]{64}", plan.attempt_sha256) is None:
        raise ValueError("attempt_sha256 must be a lowercase SHA-256")
    _validate_image_id(plan.runtime_image_id)
    _validate_image_id(plan.proxy_image_id)
    names = (
        plan.runtime_container,
        plan.proxy_container,
        plan.internal_network,
        plan.egress_network,
    )
    if len(set(names)) != 4 or any(
        _SAFE_NAME.fullmatch(name) is None for name in names
    ):
        raise ValueError("Docker topology names must be distinct and path-safe")
    stems = {name.split("-", 3)[-1] for name in names}
    if len(stems) != 1:
        raise ValueError("Docker topology names do not share one Attempt stem")
    if plan.proxy_url != CODEX_DOCKER_RUNTIME_PROXY_URL:
        raise ValueError("runtime proxy URL is not the fixed internal alias")


def _validate_image_id(image_id: str) -> str:
    if not isinstance(image_id, str) or _IMAGE_ID.fullmatch(image_id) is None:
        raise ValueError("image must be an immutable lowercase sha256 ID")
    return image_id


def _resolve_docker_executable(value: str | Path) -> str:
    path = Path(value)
    if not path.is_absolute() or path.suffix.lower() != ".exe":
        raise ValueError("docker executable must be an absolute docker.exe path")
    try:
        resolved = path.resolve(strict=True)
    except OSError:
        raise ValueError("docker executable must exist") from None
    if not resolved.is_file() or resolved.name.lower() != "docker.exe":
        raise ValueError("docker executable must be an absolute docker.exe path")
    return str(resolved)
