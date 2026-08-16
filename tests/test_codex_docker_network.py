from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from research_workbench.adapters.codex_docker_network import (
    CODEX_DOCKER_NETWORK_LIVE_READY,
    CODEX_DOCKER_PROXY_ALIAS,
    CODEX_DOCKER_RUNTIME_PROXY_URL,
    CodexDockerNetworkError,
    DockerControlResult,
    attest_codex_docker_network_with_executor,
    build_codex_docker_network_plan,
    build_topology_absence_commands,
    build_topology_attestation_commands,
    build_topology_cleanup_commands,
    build_topology_create_commands,
    cleanup_codex_docker_network_with_executor,
)

RUNTIME_IMAGE = "sha256:" + ("a" * 64)
PROXY_IMAGE = "sha256:" + ("b" * 64)
RUNTIME_ID = "c" * 64
PROXY_ID = "d" * 64
INTERNAL_ID = "e" * 64
EGRESS_ID = "f" * 64
SECRET = "glm-secret-must-stay-out-of-docker-commands"
TMPFS = "rw,noexec,nosuid,nodev,size=16777216,uid=65532,gid=65532,mode=700"
IMAGE_LABELS = {
    "org.opencontainers.image.title": "RWB test runtime",
    "io.research-workbench.asset-manifest.sha256": "1" * 64,
}


def _host_config(plan: object, *, runtime: bool) -> dict[str, object]:
    empty_fields = {
        "Binds": None,
        "CapAdd": None,
        "DeviceCgroupRules": None,
        "DeviceRequests": None,
        "Devices": None,
        "Dns": None,
        "DnsOptions": None,
        "DnsSearch": None,
        "ExtraHosts": None,
        "GroupAdd": None,
        "Links": None,
        "VolumesFrom": None,
    }
    tmpfs = {"/tmp": TMPFS}
    if runtime:
        tmpfs |= {"/workspace": TMPFS, "/codex-home": TMPFS}
    return {
        **empty_fields,
        "AutoRemove": False,
        "CapDrop": ["ALL"],
        "IpcMode": "none",
        "LogConfig": {"Type": "none", "Config": {}},
        "Memory": 536_870_912,
        "MemorySwap": 536_870_912,
        "NanoCpus": 1_000_000_000,
        "NetworkMode": plan.internal_network,
        "PidMode": "private",
        "PidsLimit": 64,
        "PortBindings": {},
        "Privileged": False,
        "PublishAllPorts": False,
        "ReadonlyRootfs": True,
        "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
        "SecurityOpt": ["no-new-privileges:true"],
        "Tmpfs": tmpfs,
        "Ulimits": [
            {"Name": "nofile", "Hard": 64, "Soft": 64},
            {"Name": "core", "Hard": 0, "Soft": 0},
        ],
    }


def _container_documents(plan: object) -> list[dict[str, object]]:
    labels = {
        **IMAGE_LABELS,
        "org.rwb.attempt-sha256": plan.attempt_sha256,
        "org.rwb.scope": "codex-coding-plan",
    }
    runtime = {
        "Id": RUNTIME_ID,
        "Name": f"/{plan.runtime_container}",
        "Image": RUNTIME_IMAGE,
        "Config": {
            "Image": RUNTIME_IMAGE,
            "Labels": labels,
            "Entrypoint": ["/runtime/entrypoint.mjs"],
            "Cmd": ["--run"],
            "OpenStdin": True,
            "StdinOnce": False,
            "Tty": False,
            "User": "65532:65532",
            "WorkingDir": "/workspace",
            "Env": [
                "NO_COLOR=1",
                "RUST_BACKTRACE=0",
                "HOME=/codex-home",
                "CODEX_HOME=/codex-home",
                f"HTTP_PROXY={CODEX_DOCKER_RUNTIME_PROXY_URL}",
                f"HTTPS_PROXY={CODEX_DOCKER_RUNTIME_PROXY_URL}",
                "NO_PROXY=",
                "PATH=/usr/local/bin:/usr/bin:/bin",
            ],
            "ExposedPorts": None,
            "Volumes": None,
        },
        "HostConfig": _host_config(plan, runtime=True),
        "Mounts": [],
        "NetworkSettings": {
            "Ports": {},
            "Networks": {
                plan.internal_network: {
                    "Aliases": [plan.runtime_container],
                    "Links": None,
                    "IPAMConfig": None,
                    "GwPriority": 0,
                    "NetworkID": INTERNAL_ID,
                    "Gateway": "172.28.0.1",
                }
            },
        },
    }
    proxy = {
        "Id": PROXY_ID,
        "Name": f"/{plan.proxy_container}",
        "Image": PROXY_IMAGE,
        "Config": {
            "Image": PROXY_IMAGE,
            "Labels": labels,
            "Entrypoint": ["/runtime/egress-proxy.mjs"],
            "Cmd": ["--serve"],
            "OpenStdin": False,
            "StdinOnce": False,
            "Tty": False,
            "User": "65532:65532",
            "WorkingDir": "/proxy",
            "Env": [
                "NO_COLOR=1",
                "RUST_BACKTRACE=0",
                "PATH=/usr/local/bin:/usr/bin:/bin",
            ],
            "ExposedPorts": None,
            "Volumes": None,
        },
        "HostConfig": _host_config(plan, runtime=False),
        "Mounts": [],
        "NetworkSettings": {
            "Ports": {},
            "Networks": {
                plan.internal_network: {
                    "Aliases": [plan.proxy_container, CODEX_DOCKER_PROXY_ALIAS],
                    "Links": None,
                    "IPAMConfig": None,
                    "GwPriority": 0,
                    "NetworkID": INTERNAL_ID,
                    "Gateway": "172.28.0.1",
                },
                plan.egress_network: {
                    "Aliases": [plan.proxy_container],
                    "Links": None,
                    "IPAMConfig": None,
                    "GwPriority": 1,
                    "NetworkID": EGRESS_ID,
                    "Gateway": "172.29.0.1",
                },
            },
        },
    }
    return [runtime, proxy]


def _network_documents(plan: object) -> list[dict[str, object]]:
    labels = {
        "org.rwb.attempt-sha256": plan.attempt_sha256,
        "org.rwb.scope": "codex-coding-plan",
    }
    common = {
        "Driver": "bridge",
        "Scope": "local",
        "Attachable": False,
        "Ingress": False,
        "EnableIPv6": False,
        "Labels": labels,
    }
    return [
        {
            **common,
            "Name": plan.internal_network,
            "Id": INTERNAL_ID,
            "Internal": True,
            "Options": {"com.docker.network.bridge.enable_ip_masquerade": "false"},
            "Containers": {
                RUNTIME_ID: {"Name": plan.runtime_container},
                PROXY_ID: {"Name": plan.proxy_container},
            },
        },
        {
            **common,
            "Name": plan.egress_network,
            "Id": EGRESS_ID,
            "Internal": False,
            "Options": {},
            "Containers": {PROXY_ID: {"Name": plan.proxy_container}},
        },
    ]


class FakeExecutor:
    def __init__(
        self,
        plan: object,
        *,
        containers: list[dict[str, object]] | None = None,
        networks: list[dict[str, object]] | None = None,
        cleanup_drift: str | None = None,
        raise_on_calls: frozenset[int] = frozenset(),
    ) -> None:
        self.plan = plan
        self.containers = containers or _container_documents(plan)
        self.networks = networks or _network_documents(plan)
        self.cleanup_drift = cleanup_drift
        self.raise_on_calls = raise_on_calls
        self.calls: list[tuple[str, ...]] = []

    def execute(self, command: tuple[str, ...]) -> DockerControlResult:
        self.calls.append(command)
        if len(self.calls) in self.raise_on_calls:
            raise RuntimeError("raw executor failure")
        if command[1:3] == ("image", "inspect"):
            images = [
                {"Id": RUNTIME_IMAGE, "Config": {"Labels": IMAGE_LABELS}},
                {"Id": PROXY_IMAGE, "Config": {"Labels": IMAGE_LABELS}},
            ]
            return DockerControlResult(0, json.dumps(images).encode(), b"")
        if command[1:3] == ("container", "inspect"):
            return DockerControlResult(0, json.dumps(self.containers).encode(), b"")
        if command[1:3] == ("network", "inspect"):
            return DockerControlResult(0, json.dumps(self.networks).encode(), b"")
        if command[2] == "rm":
            return DockerControlResult(0, b"removed\n", b"")
        if command[2] == "ls":
            target = command[-1]
            if self.cleanup_drift is not None and self.cleanup_drift in target:
                return DockerControlResult(0, b"9" * 64 + b"\n", b"")
            return DockerControlResult(0, b"", b"")
        raise AssertionError(command)


class CodexDockerNetworkTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.docker = Path(self.directory.name) / "docker.exe"
        self.docker.write_bytes(b"fake docker boundary")
        self.plan = build_codex_docker_network_plan(
            docker_executable=self.docker,
            attempt_id="A-GLM53-001",
            runtime_image_id=RUNTIME_IMAGE,
            proxy_image_id=PROXY_IMAGE,
            nonce="1" * 32,
        )


class CodexDockerNetworkCommandTests(CodexDockerNetworkTestCase):
    def test_names_are_attempt_scoped_path_safe_and_nonce_distinct(self) -> None:
        names = {
            self.plan.runtime_container,
            self.plan.proxy_container,
            self.plan.internal_network,
            self.plan.egress_network,
        }
        self.assertEqual(4, len(names))
        for name in names:
            self.assertRegex(
                name,
                r"\Arwb-cp-(?:rt|px|in|eg)-[0-9a-f]{12}-[0-9a-f]{32}\Z",
            )
            self.assertNotIn("A-GLM53-001", name)
        second = build_codex_docker_network_plan(
            docker_executable=self.docker,
            attempt_id="A-GLM53-001",
            runtime_image_id=RUNTIME_IMAGE,
            proxy_image_id=PROXY_IMAGE,
            nonce="2" * 32,
        )
        self.assertNotEqual(self.plan.internal_network, second.internal_network)
        self.assertNotEqual(self.plan.egress_network, second.egress_network)

    def test_create_connect_and_inspect_commands_freeze_isolation(self) -> None:
        commands = (
            *build_topology_create_commands(self.plan),
            *build_topology_attestation_commands(self.plan),
        )
        resolved_docker = str(self.docker.resolve())
        self.assertTrue(all(command[0] == resolved_docker for command in commands))
        internal, egress, proxy, connect, runtime = commands[:5]
        self.assertIn("--internal", internal)
        self.assertNotIn("--internal", egress)
        self.assertEqual(
            (
                "network",
                "connect",
                "--gw-priority=1",
                self.plan.egress_network,
                self.plan.proxy_container,
            ),
            connect[1:],
        )
        self.assertIn(f"--network={self.plan.internal_network}", runtime)
        self.assertNotIn(self.plan.egress_network, runtime)
        self.assertIn(f"--network={self.plan.internal_network}", proxy)
        self.assertIn(f"--network-alias={CODEX_DOCKER_PROXY_ALIAS}", proxy)
        self.assertEqual("--serve", proxy[-1])
        self.assertIn(RUNTIME_IMAGE, runtime)
        self.assertIn(PROXY_IMAGE, proxy)
        for command in (runtime, proxy):
            self.assertIn("--pull=never", command)
            self.assertIn("--read-only", command)
            self.assertIn("--cap-drop=ALL", command)
            self.assertIn("--security-opt=no-new-privileges:true", command)
            self.assertIn("--pids-limit=64", command)
            self.assertIn("--memory=536870912", command)
            self.assertIn("--cpus=1", command)
            joined = " ".join(command)
            for forbidden in ("--publish", "--mount", "--volume", "host-gateway"):
                self.assertNotIn(forbidden, joined)
        self.assertIn(f"--env=HTTPS_PROXY={CODEX_DOCKER_RUNTIME_PROXY_URL}", runtime)
        self.assertIn("--interactive", runtime)
        self.assertNotIn("--interactive", proxy)
        self.assertNotIn("HTTPS_PROXY", " ".join(proxy))
        image_inspect, container_inspect, _ = commands[5:]
        self.assertNotIn("--type=image", image_inspect)
        self.assertNotIn("--type=container", container_inspect)
        self.assertFalse(CODEX_DOCKER_NETWORK_LIVE_READY)

    def test_no_command_contains_secret_or_mutable_image_reference(self) -> None:
        commands = (
            *build_topology_create_commands(self.plan),
            *build_topology_attestation_commands(self.plan),
            *build_topology_cleanup_commands(self.plan),
            *build_topology_absence_commands(self.plan),
        )
        joined = "\n".join(" ".join(command) for command in commands)
        self.assertNotIn(SECRET, joined)
        self.assertNotRegex(joined, re.compile(r"(?:API_KEY|TOKEN|SECRET|PASSWORD)="))
        self.assertNotIn(":latest", joined)

    def test_mutable_image_and_nonabsolute_docker_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "immutable"):
            build_codex_docker_network_plan(
                docker_executable=self.docker,
                attempt_id="A-1",
                runtime_image_id="rwb/codex:latest",
                proxy_image_id=PROXY_IMAGE,
            )
        with self.assertRaisesRegex(ValueError, "absolute docker.exe"):
            build_codex_docker_network_plan(
                docker_executable="docker",
                attempt_id="A-1",
                runtime_image_id=RUNTIME_IMAGE,
                proxy_image_id=PROXY_IMAGE,
            )


class CodexDockerNetworkAttestationTests(CodexDockerNetworkTestCase):
    def test_exact_topology_attests_from_fake_executor(self) -> None:
        executor = FakeExecutor(self.plan)
        attestation = attest_codex_docker_network_with_executor(self.plan, executor)
        self.assertEqual(RUNTIME_ID, attestation.runtime_container_id)
        self.assertEqual(PROXY_ID, attestation.proxy_container_id)
        self.assertEqual(INTERNAL_ID, attestation.internal_network_id)
        self.assertEqual(EGRESS_ID, attestation.egress_network_id)
        self.assertEqual(CODEX_DOCKER_RUNTIME_PROXY_URL, attestation.proxy_url)
        self.assertTrue(attestation.capture_complete)
        self.assertEqual(3, len(executor.calls))

    def test_rogue_container_on_internal_network_is_rejected(self) -> None:
        networks = copy.deepcopy(_network_documents(self.plan))
        networks[0]["Containers"]["9" * 64] = {"Name": "rogue"}
        with self.assertRaisesRegex(
            CodexDockerNetworkError, "network-members-mismatch"
        ):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, networks=networks)
            )

    def test_runtime_extra_egress_or_default_network_is_rejected(self) -> None:
        for network_name in (self.plan.egress_network, "bridge"):
            containers = copy.deepcopy(_container_documents(self.plan))
            containers[0]["NetworkSettings"]["Networks"][network_name] = {
                "Aliases": [],
                "Links": None,
                "IPAMConfig": None,
                "NetworkID": EGRESS_ID,
            }
            with (
                self.subTest(network=network_name),
                self.assertRaisesRegex(
                    CodexDockerNetworkError, "container-network-set-mismatch"
                ),
            ):
                attest_codex_docker_network_with_executor(
                    self.plan, FakeExecutor(self.plan, containers=containers)
                )
        containers = copy.deepcopy(_container_documents(self.plan))
        containers[0]["HostConfig"]["NetworkMode"] = "default"
        with self.assertRaisesRegex(CodexDockerNetworkError, "security-resource-drift"):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, containers=containers)
            )

    def test_host_gateway_and_host_access_fields_are_rejected(self) -> None:
        containers = copy.deepcopy(_container_documents(self.plan))
        containers[0]["HostConfig"]["ExtraHosts"] = [
            "host.docker.internal:host-gateway"
        ]
        with self.assertRaisesRegex(CodexDockerNetworkError, "host-access-drift"):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, containers=containers)
            )

    def test_inherited_image_label_drift_is_rejected(self) -> None:
        containers = copy.deepcopy(_container_documents(self.plan))
        containers[0]["Config"]["Labels"]["unexpected"] = "drift"
        with self.assertRaisesRegex(
            CodexDockerNetworkError, "container-labels-mismatch"
        ):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, containers=containers)
            )
        containers = copy.deepcopy(_container_documents(self.plan))
        containers[0]["Mounts"] = [
            {"Type": "bind", "Source": "C:\\", "Destination": "/host"}
        ]
        with self.assertRaisesRegex(CodexDockerNetworkError, "mount-drift"):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, containers=containers)
            )

    def test_proxy_third_network_and_runtime_secret_env_are_rejected(self) -> None:
        containers = copy.deepcopy(_container_documents(self.plan))
        containers[1]["NetworkSettings"]["Networks"]["bridge"] = {
            "Aliases": [],
            "Links": None,
            "IPAMConfig": None,
            "NetworkID": "8" * 64,
        }
        with self.assertRaisesRegex(
            CodexDockerNetworkError, "container-network-set-mismatch"
        ):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, containers=containers)
            )
        containers = copy.deepcopy(_container_documents(self.plan))
        containers[0]["Config"]["Env"].append(f"ZHIPU_API_KEY={SECRET}")
        with self.assertRaisesRegex(
            CodexDockerNetworkError, "container-environment-invalid"
        ):
            attest_codex_docker_network_with_executor(
                self.plan, FakeExecutor(self.plan, containers=containers)
            )

    def test_internal_network_must_be_internal_without_masquerade(self) -> None:
        for mutation in ("internal", "masquerade"):
            networks = copy.deepcopy(_network_documents(self.plan))
            if mutation == "internal":
                networks[0]["Internal"] = False
            else:
                networks[0]["Options"][
                    "com.docker.network.bridge.enable_ip_masquerade"
                ] = "true"
            with (
                self.subTest(mutation=mutation),
                self.assertRaises(CodexDockerNetworkError),
            ):
                attest_codex_docker_network_with_executor(
                    self.plan, FakeExecutor(self.plan, networks=networks)
                )


class CodexDockerNetworkCleanupTests(CodexDockerNetworkTestCase):
    def test_cleanup_uses_exact_names_and_proves_absence(self) -> None:
        executor = FakeExecutor(self.plan)
        proof = cleanup_codex_docker_network_with_executor(self.plan, executor)
        self.assertTrue(proof.absence_verified)
        self.assertTrue(proof.capture_complete)
        self.assertEqual(4, proof.attempted_commands)
        self.assertEqual((0, 0, 0, 0), proof.removal_returncodes)
        self.assertEqual(8, len(executor.calls))
        flattened = "\n".join(" ".join(command) for command in executor.calls)
        for name in (
            self.plan.runtime_container,
            self.plan.proxy_container,
            self.plan.internal_network,
            self.plan.egress_network,
        ):
            self.assertIn(name, flattened)

    def test_cleanup_drift_fails_closed(self) -> None:
        executor = FakeExecutor(self.plan, cleanup_drift=self.plan.internal_network)
        with self.assertRaisesRegex(
            CodexDockerNetworkError, "cleanup-absence-unverified"
        ):
            cleanup_codex_docker_network_with_executor(self.plan, executor)

    def test_cleanup_continues_after_removal_executor_exception(self) -> None:
        executor = FakeExecutor(self.plan, raise_on_calls=frozenset({1}))
        proof = cleanup_codex_docker_network_with_executor(self.plan, executor)
        self.assertEqual(8, len(executor.calls))
        self.assertEqual((-1, 0, 0, 0), proof.removal_returncodes)
        self.assertTrue(proof.absence_verified)

    def test_cleanup_runs_all_absence_queries_after_executor_exception(self) -> None:
        executor = FakeExecutor(self.plan, raise_on_calls=frozenset({5}))
        with self.assertRaisesRegex(
            CodexDockerNetworkError, "cleanup-absence-unverified"
        ):
            cleanup_codex_docker_network_with_executor(self.plan, executor)
        self.assertEqual(8, len(executor.calls))


if __name__ == "__main__":
    unittest.main()
