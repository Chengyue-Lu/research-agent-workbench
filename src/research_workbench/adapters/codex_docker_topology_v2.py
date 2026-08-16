"""Offline Docker topology v0.2 contract for the Coding Plan lane.

This Huang Yi-owned adapter contract is additive.  It does not supersede or
modify :mod:`codex_docker_network` (the committed v0.1 contract), and it does
not change shared CLI, schema, Trace, Handoff, Mode, Skill, or selection
semantics.

The module freezes a static dual-network layout for the Python egress proxy,
builds a secret-free transaction command plan, and strictly validates supplied
Docker inspect documents.  It deliberately has no executor, does not start a
container, does not open a socket, and does not read credentials or process
environment state.  A future live supervisor must be reviewed separately.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

CODEX_DOCKER_TOPOLOGY_V2_LIVE_READY = False
CODEX_DOCKER_TOPOLOGY_V2_VERSION = "0.2"
CODEX_DOCKER_V2_MAX_INSPECT_BYTES = 2_097_152

CODEX_DOCKER_V2_INTERNAL_SUBNET = "172.28.53.0/29"
CODEX_DOCKER_V2_INTERNAL_GATEWAY = "172.28.53.1"
CODEX_DOCKER_V2_RUNTIME_IPV4 = "172.28.53.2"
CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4 = "172.28.53.3"
CODEX_DOCKER_V2_EGRESS_SUBNET = "172.28.53.8/29"
CODEX_DOCKER_V2_EGRESS_GATEWAY = "172.28.53.9"
CODEX_DOCKER_V2_PROXY_EGRESS_IPV4 = "172.28.53.10"
CODEX_DOCKER_V2_PROXY_PORT = 3128
CODEX_DOCKER_V2_PROXY_URL = (
    f"http://{CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4}:{CODEX_DOCKER_V2_PROXY_PORT}"
)

CODEX_DOCKER_V2_PROXY_ENTRYPOINT = (
    "/usr/local/bin/python",
    "-I",
    "-S",
    "/runtime/entrypoint.py",
)
CODEX_DOCKER_V2_PROXY_COMMAND = (
    "--serve",
    "--listen-ip",
    CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4,
    "--runtime-peer-ip",
    CODEX_DOCKER_V2_RUNTIME_IPV4,
)

_IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}\Z")
_OBJECT_ID = re.compile(r"[0-9a-f]{64}\Z")
_NONCE = re.compile(r"[0-9a-f]{32}\Z")
_SAFE_NAME = re.compile(
    r"rwb-cp2-(?:runtime|proxy|internal|egress)-[0-9a-f]{12}-[0-9a-f]{32}\Z"
)
_SECRET_ENV_NAME = re.compile(
    r"(?:api[_-]?key|authorization|credential|password|secret|token)",
    re.IGNORECASE,
)

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
_VERSION_LABEL = "org.rwb.docker-topology.version"
_SCOPE_VALUE = "codex-coding-plan"

_EMPTY_HOST_ACCESS_FIELDS = (
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


class CodexDockerTopologyV2Error(RuntimeError):
    """Stable fail-closed error for a v0.2 plan or inspect drift."""


@dataclass(frozen=True, slots=True)
class CodexDockerTopologyV2Plan:
    """Immutable names, images, networks, and addresses for one Attempt."""

    docker_executable: str
    attempt_sha256: str
    runtime_image_id: str
    proxy_image_id: str
    runtime_container: str
    proxy_container: str
    internal_network: str
    egress_network: str
    internal_subnet: str = CODEX_DOCKER_V2_INTERNAL_SUBNET
    internal_gateway: str = CODEX_DOCKER_V2_INTERNAL_GATEWAY
    runtime_ipv4: str = CODEX_DOCKER_V2_RUNTIME_IPV4
    proxy_internal_ipv4: str = CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4
    egress_subnet: str = CODEX_DOCKER_V2_EGRESS_SUBNET
    egress_gateway: str = CODEX_DOCKER_V2_EGRESS_GATEWAY
    proxy_egress_ipv4: str = CODEX_DOCKER_V2_PROXY_EGRESS_IPV4
    proxy_url: str = CODEX_DOCKER_V2_PROXY_URL

    def __post_init__(self) -> None:
        _validate_plan(self)


@dataclass(frozen=True, slots=True)
class CodexDockerTopologyV2Transaction:
    """Ordered, inert Docker CLI plan; all start/exec phases stay empty."""

    preflight_absence: tuple[tuple[str, ...], ...]
    create: tuple[tuple[str, ...], ...]
    attest: tuple[tuple[str, ...], ...]
    start: tuple[tuple[str, ...], ...]
    cleanup: tuple[tuple[str, ...], ...]
    final_absence: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class CodexDockerTopologyV2Attestation:
    """Result of strict validation of caller-supplied inspect documents.

    This inert contract has no executor and therefore cannot attest that the
    supplied documents are a complete capture of a Docker transaction.  A
    future supervisor must bind command results, daemon identity, timing, and
    process lifecycle before it may claim capture completeness.
    """

    attempt_sha256: str
    runtime_container_id: str
    proxy_container_id: str
    internal_network_id: str
    egress_network_id: str
    proxy_url: str
    inspect_validation_complete: bool = field(default=True, init=False)
    capture_complete: bool = field(default=False, init=False)
    evidence_assurance: str = field(
        default="caller-supplied-inspect-documents", init=False
    )


def build_codex_docker_topology_v2_plan(
    *,
    docker_executable: str,
    attempt_id: str,
    runtime_image_id: str,
    proxy_image_id: str,
    nonce: str | None = None,
) -> CodexDockerTopologyV2Plan:
    """Build portable ASCII Docker names without embedding Attempt text."""

    executable = _validate_docker_executable(docker_executable)
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
    return CodexDockerTopologyV2Plan(
        docker_executable=executable,
        attempt_sha256=attempt_sha256,
        runtime_image_id=_validate_image_id(runtime_image_id),
        proxy_image_id=_validate_image_id(proxy_image_id),
        runtime_container=f"rwb-cp2-runtime-{stem}",
        proxy_container=f"rwb-cp2-proxy-{stem}",
        internal_network=f"rwb-cp2-internal-{stem}",
        egress_network=f"rwb-cp2-egress-{stem}",
    )


def build_codex_docker_topology_v2_transaction(
    plan: CodexDockerTopologyV2Plan,
) -> CodexDockerTopologyV2Transaction:
    """Build the full offline transaction without executing any command."""

    _validate_plan(plan)
    absence = _build_absence_commands(plan)
    return CodexDockerTopologyV2Transaction(
        preflight_absence=absence,
        create=_build_create_commands(plan),
        attest=_build_attestation_commands(plan),
        start=(),
        cleanup=_build_cleanup_commands(plan),
        final_absence=absence,
    )


def attest_codex_docker_topology_v2(
    plan: CodexDockerTopologyV2Plan,
    *,
    image_inspect_json: bytes | str,
    container_inspect_json: bytes | str,
    network_inspect_json: bytes | str,
) -> CodexDockerTopologyV2Attestation:
    """Validate complete image, container, route, DNS, and membership evidence."""

    _validate_plan(plan)
    images = _parse_json_array(image_inspect_json, "v2-image-inspect-invalid")
    containers = _parse_json_array(
        container_inspect_json, "v2-container-inspect-invalid"
    )
    networks = _parse_json_array(network_inspect_json, "v2-network-inspect-invalid")

    expected_image_ids = {plan.runtime_image_id, plan.proxy_image_id}
    images_by_id = _index_exact(
        images,
        key="Id",
        expected=expected_image_ids,
        error_code="v2-image-identity-mismatch",
    )
    image_labels = {
        image_id: _attested_image_labels(item)
        for image_id, item in images_by_id.items()
    }
    image_environments = {
        image_id: _attested_image_environment(item)
        for image_id, item in images_by_id.items()
    }

    normalized_containers: list[Mapping[str, object]] = []
    for item in containers:
        normalized = dict(item)
        name = _require_string(item, "Name", "v2-container-name-invalid")
        normalized["Name"] = name.removeprefix("/")
        normalized_containers.append(normalized)
    containers_by_name = _index_exact(
        normalized_containers,
        key="Name",
        expected={plan.runtime_container, plan.proxy_container},
        error_code="v2-container-set-mismatch",
    )

    runtime_id = _attest_container(
        plan,
        containers_by_name[plan.runtime_container],
        role="runtime",
        expected_image_labels=image_labels[plan.runtime_image_id],
        expected_image_environment=image_environments[plan.runtime_image_id],
    )
    proxy_id = _attest_container(
        plan,
        containers_by_name[plan.proxy_container],
        role="proxy",
        expected_image_labels=image_labels[plan.proxy_image_id],
        expected_image_environment=image_environments[plan.proxy_image_id],
    )

    networks_by_name = _index_exact(
        networks,
        key="Name",
        expected={plan.internal_network, plan.egress_network},
        error_code="v2-network-set-mismatch",
    )
    internal_id = _attest_network(
        plan,
        networks_by_name[plan.internal_network],
        internal=True,
    )
    egress_id = _attest_network(
        plan,
        networks_by_name[plan.egress_network],
        internal=False,
    )
    return CodexDockerTopologyV2Attestation(
        attempt_sha256=plan.attempt_sha256,
        runtime_container_id=runtime_id,
        proxy_container_id=proxy_id,
        internal_network_id=internal_id,
        egress_network_id=egress_id,
        proxy_url=plan.proxy_url,
    )


def _build_create_commands(
    plan: CodexDockerTopologyV2Plan,
) -> tuple[tuple[str, ...], ...]:
    docker = plan.docker_executable
    labels = (
        f"--label={_SCOPE_LABEL}={_SCOPE_VALUE}",
        f"--label={_VERSION_LABEL}={CODEX_DOCKER_TOPOLOGY_V2_VERSION}",
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
        f"--subnet={plan.internal_subnet}",
        f"--gateway={plan.internal_gateway}",
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
        f"--subnet={plan.egress_subnet}",
        f"--gateway={plan.egress_gateway}",
        *labels,
        plan.egress_network,
    )
    proxy = _build_container_create_command(plan, role="proxy")
    connect_proxy_egress = (
        docker,
        "network",
        "connect",
        "--gw-priority=1",
        f"--ip={plan.proxy_egress_ipv4}",
        plan.egress_network,
        plan.proxy_container,
    )
    runtime = _build_container_create_command(plan, role="runtime")
    return internal, egress, proxy, connect_proxy_egress, runtime


def _build_container_create_command(
    plan: CodexDockerTopologyV2Plan, *, role: str
) -> tuple[str, ...]:
    if role == "runtime":
        name = plan.runtime_container
        image = plan.runtime_image_id
        ipv4 = plan.runtime_ipv4
        interactive = ("--interactive",)
        working_dir = "/workspace"
        environments = (
            "--env=HOME=/codex-home",
            "--env=CODEX_HOME=/codex-home",
            f"--env=HTTP_PROXY={plan.proxy_url}",
            f"--env=HTTPS_PROXY={plan.proxy_url}",
            "--env=NO_PROXY=",
        )
        tmpfs = (
            f"--tmpfs=/workspace:{_tmpfs_options()}",
            f"--tmpfs=/codex-home:{_tmpfs_options()}",
        )
        entrypoint = ("--entrypoint=/runtime/entrypoint.mjs",)
        tail = (image, "--run")
    elif role == "proxy":
        name = plan.proxy_container
        image = plan.proxy_image_id
        ipv4 = plan.proxy_internal_ipv4
        interactive = ()
        working_dir = "/proxy"
        environments = ()
        tmpfs = ()
        entrypoint = ()
        tail = (image, *CODEX_DOCKER_V2_PROXY_COMMAND)
    else:
        raise ValueError("role must be runtime or proxy")
    return (
        plan.docker_executable,
        "container",
        "create",
        "--pull=never",
        f"--name={name}",
        f"--network={plan.internal_network}",
        f"--ip={ipv4}",
        "--read-only",
        f"--user={_CONTAINER_UID}:{_CONTAINER_GID}",
        "--cap-drop=ALL",
        f"--security-opt={_SECURITY_OPT}",
        "--ipc=none",
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
        f"--label={_VERSION_LABEL}={CODEX_DOCKER_TOPOLOGY_V2_VERSION}",
        f"--label={_ATTEMPT_LABEL}={plan.attempt_sha256}",
        *interactive,
        f"--workdir={working_dir}",
        *environments,
        *tmpfs,
        *entrypoint,
        *tail,
    )


def _build_attestation_commands(
    plan: CodexDockerTopologyV2Plan,
) -> tuple[tuple[str, ...], ...]:
    images = tuple(dict.fromkeys((plan.runtime_image_id, plan.proxy_image_id)))
    return (
        (plan.docker_executable, "image", "inspect", *images),
        (
            plan.docker_executable,
            "container",
            "inspect",
            plan.runtime_container,
            plan.proxy_container,
        ),
        (
            plan.docker_executable,
            "network",
            "inspect",
            plan.internal_network,
            plan.egress_network,
        ),
    )


def _build_cleanup_commands(
    plan: CodexDockerTopologyV2Plan,
) -> tuple[tuple[str, ...], ...]:
    docker = plan.docker_executable
    return (
        (docker, "container", "rm", "--force", "--volumes", plan.runtime_container),
        (docker, "container", "rm", "--force", "--volumes", plan.proxy_container),
        (docker, "network", "rm", plan.internal_network),
        (docker, "network", "rm", plan.egress_network),
    )


def _build_absence_commands(
    plan: CodexDockerTopologyV2Plan,
) -> tuple[tuple[str, ...], ...]:
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


def _attest_container(
    plan: CodexDockerTopologyV2Plan,
    item: Mapping[str, object],
    *,
    role: str,
    expected_image_labels: Mapping[str, str],
    expected_image_environment: Mapping[str, str],
) -> str:
    container_id = _require_object_id(item, "Id", "v2-container-id-invalid")
    expected_image = plan.runtime_image_id if role == "runtime" else plan.proxy_image_id
    if item.get("Image") != expected_image:
        raise CodexDockerTopologyV2Error("v2-container-image-mismatch")
    state = _require_mapping(item, "State", "v2-container-state-invalid")
    expected_state = {
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
    if set(state) != set(expected_state) or any(
        type(state[key]) is not type(expected) or state[key] != expected
        for key, expected in expected_state.items()
    ):
        raise CodexDockerTopologyV2Error("v2-container-unexpectedly-started")

    config = _require_mapping(item, "Config", "v2-container-config-invalid")
    if config.get("Image") != expected_image:
        raise CodexDockerTopologyV2Error("v2-container-image-mismatch")
    expected_entrypoint: list[str]
    expected_command: list[str]
    expected_workdir: str
    if role == "runtime":
        expected_entrypoint = ["/runtime/entrypoint.mjs"]
        expected_command = ["--run"]
        expected_workdir = "/workspace"
    else:
        expected_entrypoint = list(CODEX_DOCKER_V2_PROXY_ENTRYPOINT)
        expected_command = list(CODEX_DOCKER_V2_PROXY_COMMAND)
        expected_workdir = "/proxy"
    if (
        config.get("Entrypoint") != expected_entrypoint
        or config.get("Cmd") != expected_command
        or config.get("OpenStdin") is not (role == "runtime")
        # Docker records `--interactive` as both OpenStdin and StdinOnce for
        # a created container. The proxy has neither flag.
        or config.get("StdinOnce") is not (role == "runtime")
        or config.get("Tty") is not False
        or config.get("User") != f"{_CONTAINER_UID}:{_CONTAINER_GID}"
        or config.get("WorkingDir") != expected_workdir
    ):
        raise CodexDockerTopologyV2Error("v2-container-process-config-drift")
    labels = _require_mapping(config, "Labels", "v2-container-labels-invalid")
    expected_labels = {
        **expected_image_labels,
        _ATTEMPT_LABEL: plan.attempt_sha256,
        _SCOPE_LABEL: _SCOPE_VALUE,
        _VERSION_LABEL: CODEX_DOCKER_TOPOLOGY_V2_VERSION,
    }
    if labels != expected_labels:
        raise CodexDockerTopologyV2Error("v2-container-labels-mismatch")
    if not _empty(config.get("ExposedPorts")) or not _empty(config.get("Volumes")):
        raise CodexDockerTopologyV2Error("v2-container-publish-or-volume-drift")
    _attest_environment(
        plan,
        config.get("Env"),
        role=role,
        expected_image_environment=expected_image_environment,
    )

    host = _require_mapping(item, "HostConfig", "v2-container-host-config-invalid")
    if any(not _empty(host.get(field)) for field in _EMPTY_HOST_ACCESS_FIELDS):
        raise CodexDockerTopologyV2Error("v2-container-host-access-or-dns-drift")
    if not _empty(host.get("PortBindings")):
        raise CodexDockerTopologyV2Error("v2-container-port-binding-drift")
    expected_fixed = {
        "AutoRemove": False,
        "IpcMode": "none",
        "Memory": _MEMORY_BYTES,
        "MemorySwap": _MEMORY_BYTES,
        "NanoCpus": _NANO_CPUS,
        "NetworkMode": plan.internal_network,
        # Docker's private PID namespace is represented by the empty default
        # PidMode. The CLI rejects the tempting but invalid `--pid=private`.
        "PidMode": "",
        "PidsLimit": _PIDS_LIMIT,
        "Privileged": False,
        "PublishAllPorts": False,
        "ReadonlyRootfs": True,
    }
    if any(host.get(name) != value for name, value in expected_fixed.items()):
        raise CodexDockerTopologyV2Error("v2-container-security-resource-drift")
    if host.get("CapDrop") != ["ALL"] or host.get("SecurityOpt") != [_SECURITY_OPT]:
        raise CodexDockerTopologyV2Error("v2-container-security-resource-drift")
    if host.get("RestartPolicy") != {"Name": "no", "MaximumRetryCount": 0}:
        raise CodexDockerTopologyV2Error("v2-container-security-resource-drift")
    log_config = host.get("LogConfig")
    if not isinstance(log_config, Mapping) or log_config.get("Type") != "none":
        raise CodexDockerTopologyV2Error("v2-container-security-resource-drift")
    if not _empty(log_config.get("Config")):
        raise CodexDockerTopologyV2Error("v2-container-security-resource-drift")
    if _normalized_ulimits(host.get("Ulimits")) != {
        ("core", 0, 0),
        ("nofile", _NOFILE, _NOFILE),
    }:
        raise CodexDockerTopologyV2Error("v2-container-security-resource-drift")
    expected_tmpfs = {"/tmp": _tmpfs_options()}
    if role == "runtime":
        expected_tmpfs.update(
            {
                "/workspace": _tmpfs_options(),
                "/codex-home": _tmpfs_options(),
            }
        )
    if host.get("Tmpfs") != expected_tmpfs:
        raise CodexDockerTopologyV2Error("v2-container-tmpfs-drift")
    if item.get("Mounts") not in (None, []):
        raise CodexDockerTopologyV2Error("v2-container-mount-drift")

    network_settings = _require_mapping(
        item, "NetworkSettings", "v2-container-networks-invalid"
    )
    if not _empty(network_settings.get("Ports")):
        raise CodexDockerTopologyV2Error("v2-container-port-binding-drift")
    networks = _require_mapping(
        network_settings, "Networks", "v2-container-networks-invalid"
    )
    expected_networks = (
        {plan.internal_network: (plan.runtime_ipv4, plan.internal_gateway, 0)}
        if role == "runtime"
        else {
            plan.internal_network: (plan.proxy_internal_ipv4, plan.internal_gateway, 0),
            plan.egress_network: (plan.proxy_egress_ipv4, plan.egress_gateway, 1),
        }
    )
    if set(networks) != set(expected_networks):
        raise CodexDockerTopologyV2Error("v2-container-network-set-mismatch")
    for name, (ipv4, gateway, priority) in expected_networks.items():
        endpoint = networks.get(name)
        if not isinstance(endpoint, Mapping):
            raise CodexDockerTopologyV2Error("v2-container-endpoint-invalid")
        ipam = _require_mapping(endpoint, "IPAMConfig", "v2-static-ip-drift")
        if ipam != {"IPv4Address": ipv4}:
            raise CodexDockerTopologyV2Error("v2-static-ip-drift")
        if (
            # Before first start Docker keeps the assigned address only in
            # IPAMConfig. Runtime endpoint fields and NetworkID remain empty;
            # network inspect below independently validates network policy and
            # IPAM, but no-start Docker does not expose member IDs here.
            endpoint.get("IPAddress") != ""
            or endpoint.get("Gateway") != ""
            or endpoint.get("NetworkID") != ""
            or endpoint.get("GwPriority") != priority
        ):
            raise CodexDockerTopologyV2Error("v2-route-or-ip-drift")
        if not _empty(endpoint.get("Links")):
            raise CodexDockerTopologyV2Error("v2-container-host-access-or-dns-drift")
    return container_id


def _attest_environment(
    plan: CodexDockerTopologyV2Plan,
    raw: object,
    *,
    role: str,
    expected_image_environment: Mapping[str, str],
) -> None:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise CodexDockerTopologyV2Error("v2-container-environment-invalid")
    parsed: dict[str, str] = {}
    for value in raw:
        if not isinstance(value, str) or "=" not in value:
            raise CodexDockerTopologyV2Error("v2-container-environment-invalid")
        name, content = value.split("=", 1)
        if not name or name in parsed or _SECRET_ENV_NAME.search(name):
            raise CodexDockerTopologyV2Error("v2-container-environment-invalid")
        parsed[name] = content
    expected = dict(expected_image_environment)
    expected.update({"NO_COLOR": "1", "RUST_BACKTRACE": "0"})
    if role == "runtime":
        expected.update(
            {
                "HOME": "/codex-home",
                "CODEX_HOME": "/codex-home",
                "HTTP_PROXY": plan.proxy_url,
                "HTTPS_PROXY": plan.proxy_url,
                "NO_PROXY": "",
            }
        )
    elif {"HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"} & set(parsed):
        raise CodexDockerTopologyV2Error("v2-proxy-recursive-proxy-drift")
    if parsed != expected:
        raise CodexDockerTopologyV2Error("v2-container-environment-drift")


def _attest_network(
    plan: CodexDockerTopologyV2Plan,
    item: Mapping[str, object],
    *,
    internal: bool,
) -> str:
    network_id = _require_object_id(item, "Id", "v2-network-id-invalid")
    expected_policy = {
        "Attachable": False,
        "ConfigOnly": False,
        "Driver": "bridge",
        "EnableIPv4": True,
        "EnableIPv6": False,
        "Ingress": False,
        "Internal": internal,
        "Scope": "local",
    }
    if any(item.get(name) != value for name, value in expected_policy.items()):
        raise CodexDockerTopologyV2Error("v2-network-policy-drift")
    labels = _require_mapping(item, "Labels", "v2-network-labels-invalid")
    if labels != {
        _ATTEMPT_LABEL: plan.attempt_sha256,
        _SCOPE_LABEL: _SCOPE_VALUE,
        _VERSION_LABEL: CODEX_DOCKER_TOPOLOGY_V2_VERSION,
    }:
        raise CodexDockerTopologyV2Error("v2-network-labels-mismatch")
    expected_options = {"com.docker.network.enable_ipv4": "true"}
    if internal:
        expected_options["com.docker.network.bridge.enable_ip_masquerade"] = "false"
    if (item.get("Options") or {}) != expected_options:
        raise CodexDockerTopologyV2Error("v2-network-options-drift")
    ipam = _require_mapping(item, "IPAM", "v2-network-ipam-invalid")
    expected_subnet = plan.internal_subnet if internal else plan.egress_subnet
    expected_gateway = plan.internal_gateway if internal else plan.egress_gateway
    if (
        ipam.get("Driver") != "default"
        or not _empty(ipam.get("Options"))
        or ipam.get("Config")
        != [{"Subnet": expected_subnet, "Gateway": expected_gateway}]
    ):
        raise CodexDockerTopologyV2Error("v2-network-ipam-drift")
    members = _require_mapping(item, "Containers", "v2-network-members-invalid")
    # Docker does not populate the network member table until a container is
    # started. A no-start topology therefore requires the table to stay empty;
    # each container's IPAMConfig above carries the frozen static assignment.
    if members:
        raise CodexDockerTopologyV2Error("v2-network-members-mismatch")
    return network_id


def _attested_image_labels(item: Mapping[str, object]) -> dict[str, str]:
    config = _require_mapping(item, "Config", "v2-image-config-invalid")
    raw_labels = config.get("Labels")
    if raw_labels is None:
        return {}
    if not isinstance(raw_labels, Mapping):
        raise CodexDockerTopologyV2Error("v2-image-labels-invalid")
    labels: dict[str, str] = {}
    for name, value in raw_labels.items():
        if not isinstance(name, str) or not isinstance(value, str):
            raise CodexDockerTopologyV2Error("v2-image-labels-invalid")
        if name in {_ATTEMPT_LABEL, _SCOPE_LABEL, _VERSION_LABEL}:
            raise CodexDockerTopologyV2Error("v2-image-label-reserved")
        labels[name] = value
    return labels


def _attested_image_environment(item: Mapping[str, object]) -> dict[str, str]:
    config = _require_mapping(item, "Config", "v2-image-config-invalid")
    raw_environment = config.get("Env")
    if raw_environment is None:
        return {}
    if not isinstance(raw_environment, Sequence) or isinstance(
        raw_environment, (str, bytes)
    ):
        raise CodexDockerTopologyV2Error("v2-image-environment-invalid")
    environment: dict[str, str] = {}
    for value in raw_environment:
        if not isinstance(value, str) or "=" not in value:
            raise CodexDockerTopologyV2Error("v2-image-environment-invalid")
        name, content = value.split("=", 1)
        if not name or name in environment or _SECRET_ENV_NAME.search(name):
            raise CodexDockerTopologyV2Error("v2-image-environment-invalid")
        environment[name] = content
    if {"HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"} & set(environment):
        raise CodexDockerTopologyV2Error("v2-image-proxy-environment-forbidden")
    return environment


def _index_exact(
    items: Sequence[Mapping[str, object]],
    *,
    key: str,
    expected: set[str],
    error_code: str,
) -> dict[str, Mapping[str, object]]:
    indexed: dict[str, Mapping[str, object]] = {}
    for item in items:
        value = _require_string(item, key, error_code)
        if value in indexed:
            raise CodexDockerTopologyV2Error(error_code)
        indexed[value] = item
    if set(indexed) != expected or len(items) != len(expected):
        raise CodexDockerTopologyV2Error(error_code)
    return indexed


def _parse_json_array(
    payload: bytes | str, error_code: str
) -> list[Mapping[str, object]]:
    if not isinstance(payload, (bytes, str)):
        raise CodexDockerTopologyV2Error(error_code)
    try:
        if isinstance(payload, bytes):
            if len(payload) > CODEX_DOCKER_V2_MAX_INSPECT_BYTES:
                raise ValueError
            text = payload.decode("utf-8", errors="strict")
        else:
            encoded = payload.encode("utf-8", errors="strict")
            if len(encoded) > CODEX_DOCKER_V2_MAX_INSPECT_BYTES:
                raise ValueError
            text = payload
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
        raise CodexDockerTopologyV2Error(error_code) from None
    if (
        not isinstance(document, list)
        or not document
        or any(not isinstance(item, Mapping) for item in document)
    ):
        raise CodexDockerTopologyV2Error(error_code)
    return list(document)


def _reject_duplicate_json_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
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


def _require_mapping(
    source: Mapping[str, object], key: str, error_code: str
) -> Mapping[str, object]:
    value = source.get(key)
    if not isinstance(value, Mapping):
        raise CodexDockerTopologyV2Error(error_code)
    return value


def _require_string(source: Mapping[str, object], key: str, error_code: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value:
        raise CodexDockerTopologyV2Error(error_code)
    return value


def _require_object_id(source: Mapping[str, object], key: str, error_code: str) -> str:
    value = _require_string(source, key, error_code)
    if _OBJECT_ID.fullmatch(value) is None:
        raise CodexDockerTopologyV2Error(error_code)
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


def _validate_plan(plan: CodexDockerTopologyV2Plan) -> None:
    _validate_docker_executable(plan.docker_executable)
    if re.fullmatch(r"[0-9a-f]{64}", plan.attempt_sha256) is None:
        raise ValueError("attempt_sha256 must be a lowercase SHA-256")
    _validate_image_id(plan.runtime_image_id)
    _validate_image_id(plan.proxy_image_id)
    if plan.runtime_image_id == plan.proxy_image_id:
        raise ValueError("v0.2 runtime and proxy images must be distinct")
    names = (
        plan.runtime_container,
        plan.proxy_container,
        plan.internal_network,
        plan.egress_network,
    )
    if len(set(names)) != 4 or any(
        len(name.encode("ascii", errors="strict")) > 63
        or _SAFE_NAME.fullmatch(name) is None
        for name in names
    ):
        raise ValueError("v0.2 Docker names must be distinct portable ASCII names")
    stems = {tuple(name.rsplit("-", 2)[-2:]) for name in names}
    if len(stems) != 1:
        raise ValueError("v0.2 Docker names must share one Attempt stem")
    fixed = {
        "internal_subnet": CODEX_DOCKER_V2_INTERNAL_SUBNET,
        "internal_gateway": CODEX_DOCKER_V2_INTERNAL_GATEWAY,
        "runtime_ipv4": CODEX_DOCKER_V2_RUNTIME_IPV4,
        "proxy_internal_ipv4": CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4,
        "egress_subnet": CODEX_DOCKER_V2_EGRESS_SUBNET,
        "egress_gateway": CODEX_DOCKER_V2_EGRESS_GATEWAY,
        "proxy_egress_ipv4": CODEX_DOCKER_V2_PROXY_EGRESS_IPV4,
        "proxy_url": CODEX_DOCKER_V2_PROXY_URL,
    }
    if any(getattr(plan, name) != value for name, value in fixed.items()):
        raise ValueError("v0.2 topology constants are immutable")
    internal = ipaddress.ip_network(plan.internal_subnet, strict=True)
    egress = ipaddress.ip_network(plan.egress_subnet, strict=True)
    if internal.overlaps(egress):
        raise ValueError("v0.2 network subnets must not overlap")
    internal_addresses = (
        plan.internal_gateway,
        plan.runtime_ipv4,
        plan.proxy_internal_ipv4,
    )
    egress_addresses = (plan.egress_gateway, plan.proxy_egress_ipv4)
    if any(ipaddress.ip_address(value) not in internal for value in internal_addresses):
        raise ValueError("v0.2 internal address is outside the internal subnet")
    if any(ipaddress.ip_address(value) not in egress for value in egress_addresses):
        raise ValueError("v0.2 egress address is outside the egress subnet")
    if len({*internal_addresses, *egress_addresses}) != 5:
        raise ValueError("v0.2 topology addresses must be distinct")
    if (
        plan.proxy_url
        != f"http://{ipaddress.ip_address(plan.proxy_internal_ipv4)}:3128"
    ):
        raise ValueError("v0.2 proxy URL must use the fixed numeric internal IPv4")


def _validate_image_id(image_id: str) -> str:
    if not isinstance(image_id, str) or _IMAGE_ID.fullmatch(image_id) is None:
        raise ValueError("image must be an immutable lowercase sha256 ID")
    return image_id


def _validate_docker_executable(value: str) -> str:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > 512:
        raise ValueError(
            "docker executable must be the docker token or an absolute path"
        )
    normalized = value.replace("\\", "/")
    is_absolute = (
        normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized) is not None
    )
    basename = normalized.rsplit("/", 1)[-1].lower()
    if value != "docker" and (
        not is_absolute or basename not in {"docker", "docker.exe"}
    ):
        raise ValueError(
            "docker executable must be the docker token or an absolute path"
        )
    return value
