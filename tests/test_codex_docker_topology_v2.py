from __future__ import annotations

import copy
import ipaddress
import json
import re
import unittest
from dataclasses import replace

import research_workbench.adapters.codex_docker_topology_v2 as topology_v2
from research_workbench.adapters.codex_docker_topology_v2 import (
    CODEX_DOCKER_TOPOLOGY_V2_LIVE_READY,
    CODEX_DOCKER_V2_EGRESS_GATEWAY,
    CODEX_DOCKER_V2_EGRESS_SUBNET,
    CODEX_DOCKER_V2_INTERNAL_GATEWAY,
    CODEX_DOCKER_V2_INTERNAL_SUBNET,
    CODEX_DOCKER_V2_PROXY_COMMAND,
    CODEX_DOCKER_V2_PROXY_EGRESS_IPV4,
    CODEX_DOCKER_V2_PROXY_ENTRYPOINT,
    CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4,
    CODEX_DOCKER_V2_PROXY_URL,
    CODEX_DOCKER_V2_RUNTIME_IPV4,
    CodexDockerTopologyV2Error,
    attest_codex_docker_topology_v2,
    build_codex_docker_topology_v2_plan,
    build_codex_docker_topology_v2_transaction,
)

RUNTIME_IMAGE = "sha256:" + "1" * 64
PROXY_IMAGE = "sha256:" + "2" * 64
RUNTIME_ID = "3" * 64
PROXY_ID = "4" * 64
INTERNAL_ID = "5" * 64
EGRESS_ID = "6" * 64
ROGUE_ID = "7" * 64
ATTEMPT_SECRET = "attempt-contains-user-secret-never-copy-this"

ATTEMPT_LABEL = "org.rwb.attempt-sha256"
SCOPE_LABEL = "org.rwb.scope"
VERSION_LABEL = "org.rwb.docker-topology.version"


def _tmpfs_options() -> str:
    return "rw,noexec,nosuid,nodev,size=16777216,uid=65532,gid=65532,mode=700"


class TopologyFixture:
    def __init__(self) -> None:
        self.plan = build_codex_docker_topology_v2_plan(
            docker_executable="docker",
            attempt_id=ATTEMPT_SECRET,
            runtime_image_id=RUNTIME_IMAGE,
            proxy_image_id=PROXY_IMAGE,
            nonce="a" * 32,
        )
        self.image_documents = [
            {
                "Id": RUNTIME_IMAGE,
                "Config": {
                    "Labels": {"image.role": "runtime"},
                    "Env": ["PATH=/usr/local/bin:/usr/bin:/bin"],
                },
            },
            {
                "Id": PROXY_IMAGE,
                "Config": {
                    "Labels": {"image.role": "proxy"},
                    "Env": ["PATH=/usr/local/bin:/usr/bin:/bin"],
                },
            },
        ]
        self.container_documents = [
            self._container(role="runtime"),
            self._container(role="proxy"),
        ]
        self.network_documents = [
            self._network(internal=True),
            self._network(internal=False),
        ]

    def _labels(self, role: str) -> dict[str, str]:
        return {
            "image.role": role,
            ATTEMPT_LABEL: self.plan.attempt_sha256,
            SCOPE_LABEL: "codex-coding-plan",
            VERSION_LABEL: "0.2",
        }

    def _endpoint(
        self,
        *,
        network_id: str,
        ipv4: str,
        gateway: str,
        priority: int,
    ) -> dict[str, object]:
        return {
            "IPAMConfig": {"IPv4Address": ipv4, "IPv6Address": ""},
            "Links": None,
            "NetworkID": network_id,
            "IPAddress": ipv4,
            "Gateway": gateway,
            "GwPriority": priority,
        }

    def _container(self, *, role: str) -> dict[str, object]:
        runtime = role == "runtime"
        container_id = RUNTIME_ID if runtime else PROXY_ID
        image_id = RUNTIME_IMAGE if runtime else PROXY_IMAGE
        networks = {
            self.plan.internal_network: self._endpoint(
                network_id=INTERNAL_ID,
                ipv4=(
                    CODEX_DOCKER_V2_RUNTIME_IPV4
                    if runtime
                    else CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4
                ),
                gateway=CODEX_DOCKER_V2_INTERNAL_GATEWAY,
                priority=0,
            )
        }
        if not runtime:
            networks[self.plan.egress_network] = self._endpoint(
                network_id=EGRESS_ID,
                ipv4=CODEX_DOCKER_V2_PROXY_EGRESS_IPV4,
                gateway=CODEX_DOCKER_V2_EGRESS_GATEWAY,
                priority=1,
            )
        environment = [
            "PATH=/usr/local/bin:/usr/bin:/bin",
            "NO_COLOR=1",
            "RUST_BACKTRACE=0",
        ]
        if runtime:
            environment.extend(
                [
                    "HOME=/codex-home",
                    "CODEX_HOME=/codex-home",
                    f"HTTP_PROXY={CODEX_DOCKER_V2_PROXY_URL}",
                    f"HTTPS_PROXY={CODEX_DOCKER_V2_PROXY_URL}",
                    "NO_PROXY=",
                ]
            )
        host_access = {
            name: None
            for name in (
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
        }
        host_access.update(
            {
                "AutoRemove": False,
                "IpcMode": "none",
                "Memory": 536_870_912,
                "MemorySwap": 536_870_912,
                "NanoCpus": 1_000_000_000,
                "NetworkMode": self.plan.internal_network,
                "PidMode": "private",
                "PidsLimit": 64,
                "Privileged": False,
                "PublishAllPorts": False,
                "ReadonlyRootfs": True,
                "PortBindings": {},
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges:true"],
                "RestartPolicy": {"Name": "no", "MaximumRetryCount": 0},
                "LogConfig": {"Type": "none", "Config": {}},
                "Ulimits": [
                    {"Name": "nofile", "Hard": 64, "Soft": 64},
                    {"Name": "core", "Hard": 0, "Soft": 0},
                ],
                "Tmpfs": {"/tmp": _tmpfs_options()},
            }
        )
        if runtime:
            host_access["Tmpfs"].update(  # type: ignore[union-attr]
                {
                    "/workspace": _tmpfs_options(),
                    "/codex-home": _tmpfs_options(),
                }
            )
        return {
            "Id": container_id,
            "Name": "/"
            + (self.plan.runtime_container if runtime else self.plan.proxy_container),
            "Image": image_id,
            "State": {
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
            },
            "Config": {
                "Image": image_id,
                "Entrypoint": (
                    ["/runtime/entrypoint.mjs"]
                    if runtime
                    else list(CODEX_DOCKER_V2_PROXY_ENTRYPOINT)
                ),
                "Cmd": ["--run"] if runtime else list(CODEX_DOCKER_V2_PROXY_COMMAND),
                "OpenStdin": runtime,
                "StdinOnce": False,
                "Tty": False,
                "User": "65532:65532",
                "WorkingDir": "/workspace" if runtime else "/proxy",
                "Labels": self._labels(role),
                "ExposedPorts": None,
                "Volumes": None,
                "Env": environment,
            },
            "HostConfig": host_access,
            "Mounts": [],
            "NetworkSettings": {"Ports": {}, "Networks": networks},
        }

    def _network(self, *, internal: bool) -> dict[str, object]:
        if internal:
            network_id = INTERNAL_ID
            name = self.plan.internal_network
            subnet = CODEX_DOCKER_V2_INTERNAL_SUBNET
            gateway = CODEX_DOCKER_V2_INTERNAL_GATEWAY
            options = {"com.docker.network.bridge.enable_ip_masquerade": "false"}
            members = {
                RUNTIME_ID: {
                    "Name": self.plan.runtime_container,
                    "IPv4Address": f"{CODEX_DOCKER_V2_RUNTIME_IPV4}/29",
                    "IPv6Address": "",
                },
                PROXY_ID: {
                    "Name": self.plan.proxy_container,
                    "IPv4Address": f"{CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4}/29",
                    "IPv6Address": "",
                },
            }
        else:
            network_id = EGRESS_ID
            name = self.plan.egress_network
            subnet = CODEX_DOCKER_V2_EGRESS_SUBNET
            gateway = CODEX_DOCKER_V2_EGRESS_GATEWAY
            options = {}
            members = {
                PROXY_ID: {
                    "Name": self.plan.proxy_container,
                    "IPv4Address": f"{CODEX_DOCKER_V2_PROXY_EGRESS_IPV4}/29",
                    "IPv6Address": "",
                }
            }
        return {
            "Id": network_id,
            "Name": name,
            "Attachable": False,
            "Driver": "bridge",
            "EnableIPv6": False,
            "Ingress": False,
            "Internal": internal,
            "Scope": "local",
            "Labels": {
                ATTEMPT_LABEL: self.plan.attempt_sha256,
                SCOPE_LABEL: "codex-coding-plan",
                VERSION_LABEL: "0.2",
            },
            "Options": options,
            "IPAM": {
                "Driver": "default",
                "Options": {},
                "Config": [{"Subnet": subnet, "Gateway": gateway}],
            },
            "Containers": members,
        }

    def attest(
        self,
        *,
        images: object | None = None,
        containers: object | None = None,
        networks: object | None = None,
    ) -> object:
        return attest_codex_docker_topology_v2(
            self.plan,
            image_inspect_json=json.dumps(
                self.image_documents if images is None else images
            ),
            container_inspect_json=json.dumps(
                self.container_documents if containers is None else containers
            ),
            network_inspect_json=json.dumps(
                self.network_documents if networks is None else networks
            ),
        )


class CodexDockerTopologyV2PlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = TopologyFixture()
        self.plan = self.fixture.plan

    def test_names_are_portable_hashed_and_do_not_embed_attempt_text(self) -> None:
        names = (
            self.plan.runtime_container,
            self.plan.proxy_container,
            self.plan.internal_network,
            self.plan.egress_network,
        )
        self.assertEqual(4, len(set(names)))
        for name in names:
            self.assertLessEqual(len(name.encode("ascii")), 63)
            self.assertRegex(name, r"\Arwb-cp2-[a-z]+-[0-9a-f]{12}-[0-9a-f]{32}\Z")
            self.assertNotIn(ATTEMPT_SECRET, name)

    def test_frozen_addresses_are_distinct_in_nonoverlapping_subnets(self) -> None:
        internal = ipaddress.ip_network(CODEX_DOCKER_V2_INTERNAL_SUBNET)
        egress = ipaddress.ip_network(CODEX_DOCKER_V2_EGRESS_SUBNET)
        self.assertFalse(internal.overlaps(egress))
        self.assertIn(ipaddress.ip_address(CODEX_DOCKER_V2_RUNTIME_IPV4), internal)
        self.assertIn(
            ipaddress.ip_address(CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4), internal
        )
        self.assertIn(ipaddress.ip_address(CODEX_DOCKER_V2_PROXY_EGRESS_IPV4), egress)
        self.assertEqual(
            f"http://{CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4}:3128",
            self.plan.proxy_url,
        )
        self.assertIsNotNone(re.fullmatch(r"http://[0-9.]+:3128", self.plan.proxy_url))

    def test_frozen_fields_cannot_be_rebound(self) -> None:
        mutations = {
            "internal_subnet": "172.29.0.0/29",
            "internal_gateway": "172.28.53.4",
            "runtime_ipv4": "172.28.53.4",
            "proxy_internal_ipv4": "172.28.53.4",
            "egress_subnet": "172.29.0.8/29",
            "egress_gateway": "172.28.53.11",
            "proxy_egress_ipv4": "172.28.53.11",
            "proxy_url": "http://rwb-egress-proxy:3128",
        }
        for field, value in mutations.items():
            with self.subTest(field=field), self.assertRaises(ValueError):
                replace(self.plan, **{field: value})

    def test_invalid_names_images_and_executable_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.plan, runtime_container="../runtime")
        with self.assertRaises(ValueError):
            replace(self.plan, proxy_image_id="latest")
        with self.assertRaises(ValueError):
            replace(self.plan, proxy_image_id=RUNTIME_IMAGE)
        with self.assertRaises(ValueError):
            build_codex_docker_topology_v2_plan(
                docker_executable="powershell",
                attempt_id="attempt",
                runtime_image_id=RUNTIME_IMAGE,
                proxy_image_id=PROXY_IMAGE,
                nonce="b" * 32,
            )


class CodexDockerTopologyV2TransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = TopologyFixture()
        self.plan = self.fixture.plan
        self.transaction = build_codex_docker_topology_v2_transaction(self.plan)

    def test_transaction_is_ordered_inert_and_has_no_executor(self) -> None:
        self.assertEqual(4, len(self.transaction.preflight_absence))
        self.assertEqual(5, len(self.transaction.create))
        self.assertEqual(3, len(self.transaction.attest))
        self.assertEqual((), self.transaction.start)
        self.assertEqual(4, len(self.transaction.cleanup))
        self.assertEqual(4, len(self.transaction.final_absence))
        self.assertFalse(CODEX_DOCKER_TOPOLOGY_V2_LIVE_READY)
        self.assertFalse(hasattr(topology_v2, "DockerExecutor"))
        words = {
            word
            for phase in (
                self.transaction.preflight_absence,
                self.transaction.create,
                self.transaction.attest,
                self.transaction.cleanup,
                self.transaction.final_absence,
            )
            for command in phase
            for word in command
        }
        self.assertNotIn("start", words)
        self.assertNotIn("exec", words)

    def test_create_commands_freeze_python_proxy_and_static_routes(self) -> None:
        internal, egress, proxy, connect, runtime = self.transaction.create
        self.assertIn(f"--subnet={CODEX_DOCKER_V2_INTERNAL_SUBNET}", internal)
        self.assertIn(f"--gateway={CODEX_DOCKER_V2_INTERNAL_GATEWAY}", internal)
        self.assertIn(f"--subnet={CODEX_DOCKER_V2_EGRESS_SUBNET}", egress)
        self.assertIn(f"--gateway={CODEX_DOCKER_V2_EGRESS_GATEWAY}", egress)
        self.assertEqual(
            (*CODEX_DOCKER_V2_PROXY_COMMAND,),
            proxy[-len(CODEX_DOCKER_V2_PROXY_COMMAND) :],
        )
        self.assertIn(f"--ip={CODEX_DOCKER_V2_PROXY_INTERNAL_IPV4}", proxy)
        self.assertNotIn("--gw-priority=0", proxy)
        self.assertIn(f"--ip={CODEX_DOCKER_V2_PROXY_EGRESS_IPV4}", connect)
        self.assertIn("--gw-priority=1", connect)
        self.assertIn(f"--ip={CODEX_DOCKER_V2_RUNTIME_IPV4}", runtime)
        self.assertIn(f"--env=HTTP_PROXY={CODEX_DOCKER_V2_PROXY_URL}", runtime)

    def test_every_command_is_secret_free_without_host_mount_or_publish(self) -> None:
        commands = (
            *self.transaction.preflight_absence,
            *self.transaction.create,
            *self.transaction.attest,
            *self.transaction.cleanup,
            *self.transaction.final_absence,
        )
        serialized = "\n".join(" ".join(command) for command in commands)
        self.assertNotIn(ATTEMPT_SECRET, serialized)
        self.assertNotRegex(
            serialized,
            r"(?i)(?:api[_-]?key|authorization|credential|password|secret|token)=",
        )
        create_serialized = "\n".join(
            " ".join(command) for command in self.transaction.create
        )
        self.assertNotIn("--mount", create_serialized)
        self.assertNotIn("--volume", create_serialized)
        self.assertNotRegex(create_serialized, r"(?:^|\s)(?:-p|--publish)(?:=|\s)")
        self.assertNotIn("--dns", create_serialized)
        self.assertNotIn("--add-host", create_serialized)


class CodexDockerTopologyV2AttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = TopologyFixture()

    def test_complete_strict_inspection_is_attested(self) -> None:
        result = self.fixture.attest()
        self.assertEqual(RUNTIME_ID, result.runtime_container_id)
        self.assertEqual(PROXY_ID, result.proxy_container_id)
        self.assertEqual(INTERNAL_ID, result.internal_network_id)
        self.assertEqual(EGRESS_ID, result.egress_network_id)
        self.assertEqual(CODEX_DOCKER_V2_PROXY_URL, result.proxy_url)
        self.assertTrue(result.inspect_validation_complete)
        self.assertFalse(result.capture_complete)
        self.assertEqual("caller-supplied-inspect-documents", result.evidence_assurance)

    def test_process_or_started_state_drift_fails_closed(self) -> None:
        cases: list[tuple[str, list[dict[str, object]]]] = []
        process = copy.deepcopy(self.fixture.container_documents)
        process[1]["Config"]["Entrypoint"] = ["/bin/sh"]  # type: ignore[index]
        cases.append(("process", process))
        for field, value in (
            ("Status", "running"),
            ("Running", True),
            ("Pid", 31337),
            ("Pid", False),
            ("Running", 0),
            ("Restarting", True),
            ("Dead", True),
            ("Error", "started-before-attestation"),
        ):
            state = copy.deepcopy(self.fixture.container_documents)
            state[0]["State"][field] = value  # type: ignore[index]
            cases.append((f"state-{field}", state))
        for name, containers in cases:
            with self.subTest(name=name), self.assertRaises(CodexDockerTopologyV2Error):
                self.fixture.attest(containers=containers)

    def test_duplicate_nonfinite_and_oversized_inspect_json_fail_closed(self) -> None:
        first = json.dumps(self.fixture.container_documents[0])
        duplicate_state = (
            first[:-1]
            + ',"State":'
            + json.dumps(self.fixture.container_documents[0]["State"])
            + "}"
        )
        duplicate_payload = (
            "["
            + duplicate_state
            + ","
            + json.dumps(self.fixture.container_documents[1])
            + "]"
        )
        positive_overflow = (
            "["
            + first[:-1]
            + ',"Overflow":1e999},'
            + json.dumps(self.fixture.container_documents[1])
            + "]"
        )
        negative_overflow = positive_overflow.replace("1e999", "-1e999")
        invalid_payloads = (
            duplicate_payload,
            '[{"State":NaN}]',
            positive_overflow,
            negative_overflow,
            "[" * 10_000 + "0" + "]" * 10_000,
            "[" + " " * topology_v2.CODEX_DOCKER_V2_MAX_INSPECT_BYTES + "]",
        )
        for payload in invalid_payloads:
            with (
                self.subTest(payload_prefix=payload[:32]),
                self.assertRaisesRegex(
                    CodexDockerTopologyV2Error,
                    "v2-container-inspect-invalid",
                ),
            ):
                attest_codex_docker_topology_v2(
                    self.fixture.plan,
                    image_inspect_json=json.dumps(self.fixture.image_documents),
                    container_inspect_json=payload,
                    network_inspect_json=json.dumps(self.fixture.network_documents),
                )

    def test_host_mount_port_and_dns_drift_fail_closed(self) -> None:
        mutations = (
            ("Binds", ["C:/host:/workspace"]),
            ("PortBindings", {"3128/tcp": [{"HostPort": "3128"}]}),
            ("Dns", ["8.8.8.8"]),
            ("ExtraHosts", ["metadata:169.254.169.254"]),
        )
        for field, value in mutations:
            containers = copy.deepcopy(self.fixture.container_documents)
            containers[1]["HostConfig"][field] = value  # type: ignore[index]
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(
                    CodexDockerTopologyV2Error,
                    "host-access-or-dns-drift|port-binding-drift",
                ),
            ):
                self.fixture.attest(containers=containers)

    def test_static_ip_route_and_network_id_drift_fail_closed(self) -> None:
        mutations = (
            ("IPAMConfig", {"IPv4Address": "172.28.53.4"}),
            ("Gateway", CODEX_DOCKER_V2_INTERNAL_GATEWAY),
            ("GwPriority", 0),
            ("NetworkID", "9" * 64),
        )
        for field, value in mutations:
            containers = copy.deepcopy(self.fixture.container_documents)
            endpoint = containers[1]["NetworkSettings"]["Networks"][  # type: ignore[index]
                self.fixture.plan.egress_network
            ]
            endpoint[field] = value
            if field == "Gateway":
                self.assertNotEqual(value, CODEX_DOCKER_V2_EGRESS_GATEWAY)
            with (
                self.subTest(field=field),
                self.assertRaises(CodexDockerTopologyV2Error),
            ):
                self.fixture.attest(containers=containers)

    def test_rogue_member_or_member_address_drift_fails_closed(self) -> None:
        rogue = copy.deepcopy(self.fixture.network_documents)
        rogue[0]["Containers"][ROGUE_ID] = {  # type: ignore[index]
            "Name": "rogue",
            "IPv4Address": "172.28.53.4/29",
            "IPv6Address": "",
        }
        with self.assertRaisesRegex(
            CodexDockerTopologyV2Error, "network-members-mismatch"
        ):
            self.fixture.attest(networks=rogue)

        address = copy.deepcopy(self.fixture.network_documents)
        address[0]["Containers"][RUNTIME_ID][  # type: ignore[index]
            "IPv4Address"
        ] = "172.28.53.4/29"
        with self.assertRaisesRegex(
            CodexDockerTopologyV2Error, "network-member-address-drift"
        ):
            self.fixture.attest(networks=address)

    def test_subnet_gateway_options_and_dns_environment_drift_fail_closed(self) -> None:
        networks = copy.deepcopy(self.fixture.network_documents)
        networks[0]["IPAM"]["Config"] = [  # type: ignore[index]
            {"Subnet": "172.28.54.0/29", "Gateway": "172.28.54.1"}
        ]
        with self.assertRaisesRegex(CodexDockerTopologyV2Error, "network-ipam-drift"):
            self.fixture.attest(networks=networks)

        environment = copy.deepcopy(self.fixture.container_documents)
        environment[1]["Config"]["Env"].append("API_TOKEN=not-a-real-key")  # type: ignore[index,union-attr]
        with self.assertRaisesRegex(
            CodexDockerTopologyV2Error, "container-environment-invalid"
        ):
            self.fixture.attest(containers=environment)

        unexpected = copy.deepcopy(self.fixture.container_documents)
        unexpected[1]["Config"]["Env"].append("UNDECLARED=value")  # type: ignore[index,union-attr]
        with self.assertRaisesRegex(
            CodexDockerTopologyV2Error, "container-environment-drift"
        ):
            self.fixture.attest(containers=unexpected)

    def test_incomplete_or_extra_inspect_documents_never_attest(self) -> None:
        cases = (
            {"images": self.fixture.image_documents[:1]},
            {"containers": self.fixture.container_documents[:1]},
            {"networks": self.fixture.network_documents[:1]},
            {"networks": [*self.fixture.network_documents, {"Name": "rogue"}]},
        )
        for mutation in cases:
            with (
                self.subTest(mutation=tuple(mutation)),
                self.assertRaises(CodexDockerTopologyV2Error),
            ):
                self.fixture.attest(**mutation)


if __name__ == "__main__":
    unittest.main()
