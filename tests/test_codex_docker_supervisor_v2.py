from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import unittest
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import research_workbench.adapters.codex_docker_supervisor_v2 as supervisor_module
from research_workbench.adapters.codex_coding_plan_docker import (
    DockerCommandResult,
)
from research_workbench.adapters.codex_docker_supervisor_v2 import (
    CODEX_DOCKER_SUPERVISOR_V2_API_VERSION,
    CODEX_DOCKER_SUPERVISOR_V2_LIVE_READY,
    CodexDockerSupervisorV2CleanupError,
    CodexDockerSupervisorV2Error,
    CodexDockerSupervisorV2Plan,
    CodexDockerTopologySupervisorV2,
)
from research_workbench.adapters.codex_docker_topology_v2 import (
    CodexDockerTopologyV2Attestation,
    CodexDockerTopologyV2Error,
    build_codex_docker_topology_v2_plan,
)

RUNTIME_IMAGE = "sha256:" + "e" * 64
PROXY_IMAGE = "sha256:" + "f" * 64
RUNTIME_ID = "a" * 64
PROXY_ID = "b" * 64
INTERNAL_ID = "c" * 64
EGRESS_ID = "d" * 64
DAEMON_ID = "RWB:LOCAL:DAEMON:0001"
DOCKER_HOST = (
    "npipe:////./pipe/docker_engine"
    if os.name == "nt"
    else "unix:///var/run/docker.sock"
)
SENSITIVE_CANARY = "sensitive-canary-must-never-be-read-or-forwarded"

CREATED_STATE = {
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


class StepClock:
    def __init__(self, *, step: float = 0.01) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        current = self.value
        self.value += self.step
        return current


class ManualClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class PoisonValue:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"live value was inspected: {name}")


class PoisonClock:
    def __call__(self) -> float:
        raise AssertionError("live clock was called")


class FakeSupervisorV2Executor:
    def __init__(
        self,
        plan: CodexDockerSupervisorV2Plan,
        *,
        fail_at: str | None = None,
        fail_after_effect: bool = False,
        retain: frozenset[str] = frozenset(),
        mismatch_identity_once: str | None = None,
        duplicate_version: bool = False,
        duplicate_state: str | None = None,
        running_state: str | None = None,
        daemon_drift: bool = False,
        oversize_at: str | None = None,
        write_config_at: str | None = None,
        attest_canary: str | None = None,
        cancel_at: str | None = None,
        cancel_after_effect: bool = False,
        clock_to_advance: ManualClock | None = None,
        advance_clock_at: str | None = None,
        advance_clock_to: float = 0.0,
    ) -> None:
        self.plan = plan
        self.fail_at = fail_at
        self.fail_after_effect = fail_after_effect
        self.retain = retain
        self.mismatch_identity_once = mismatch_identity_once
        self.duplicate_version = duplicate_version
        self.duplicate_state = duplicate_state
        self.running_state = running_state
        self.daemon_drift = daemon_drift
        self.oversize_at = oversize_at
        self.write_config_at = write_config_at
        self.attest_canary = attest_canary
        self.cancel_at = cancel_at
        self.cancel_after_effect = cancel_after_effect
        self.clock_to_advance = clock_to_advance
        self.advance_clock_at = advance_clock_at
        self.advance_clock_to = advance_clock_to
        self.failure_consumed = False
        self.cancellation_consumed = False
        self.version_calls = 0
        self.info_calls = 0
        self.present = {
            "runtime": False,
            "proxy": False,
            "internal": False,
            "egress": False,
        }
        self.calls: list[
            tuple[
                tuple[str, ...],
                bytes,
                float,
                int,
                int,
                Mapping[str, str],
                str,
            ]
        ] = []

    def execute(
        self,
        command: tuple[str, ...],
        *,
        stdin: bytes,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
        environment: Mapping[str, str],
    ) -> DockerCommandResult:
        self._assert_frozen_prefix(command)
        marker = self._marker(command)
        self.calls.append(
            (
                command,
                stdin,
                timeout_seconds,
                stdout_limit,
                stderr_limit,
                dict(environment),
                marker,
            )
        )
        if self.write_config_at == marker:
            Path(self.plan.docker_config_directory, "unexpected.json").write_text(
                "{}", encoding="utf-8"
            )
        if self.oversize_at == marker:
            return DockerCommandResult(0, b"x" * (stdout_limit + 1), b"")
        should_fail = self.fail_at == marker and not self.failure_consumed
        should_cancel = self.cancel_at == marker and not self.cancellation_consumed
        if should_cancel and not self.cancel_after_effect:
            self.cancellation_consumed = True
            raise KeyboardInterrupt
        if should_fail and not self.fail_after_effect:
            self.failure_consumed = True
            raise RuntimeError("untrusted executor detail")
        result = self._execute_command(command, marker)
        if self.clock_to_advance is not None and self.advance_clock_at == marker:
            self.clock_to_advance.value = self.advance_clock_to
        if should_cancel:
            self.cancellation_consumed = True
            raise KeyboardInterrupt
        if should_fail:
            self.failure_consumed = True
            raise RuntimeError("ambiguous command completion")
        return result

    def _execute_command(
        self, command: tuple[str, ...], marker: str
    ) -> DockerCommandResult:
        if marker == "binding_version":
            self.version_calls += 1
            if self.duplicate_version and self.version_calls == 1:
                return DockerCommandResult(
                    0,
                    (
                        b'{"client_api_version":"1.53",'
                        b'"client_api_version":"1.53",'
                        b'"server_api_version":"1.53",'
                        b'"server_version":"29.2.0"}\n'
                    ),
                    b"",
                )
            return DockerCommandResult(
                0,
                json.dumps(
                    {
                        "client_api_version": CODEX_DOCKER_SUPERVISOR_V2_API_VERSION,
                        "server_api_version": CODEX_DOCKER_SUPERVISOR_V2_API_VERSION,
                        "server_version": "29.2.0",
                    },
                    separators=(",", ":"),
                ).encode()
                + b"\n",
                b"",
            )
        if marker == "binding_info":
            self.info_calls += 1
            daemon_id = DAEMON_ID
            if self.daemon_drift and self.info_calls > 1:
                daemon_id = "RWB:LOCAL:DAEMON:9999"
            return DockerCommandResult(
                0,
                json.dumps(
                    {"daemon_id": daemon_id, "server_version": "29.2.0"},
                    separators=(",", ":"),
                ).encode()
                + b"\n",
                b"",
            )
        if marker.startswith("create_"):
            role = marker.removeprefix("create_")
            self.present[role] = True
            return DockerCommandResult(0, f"{self._identity(role)}\n".encode(), b"")
        if marker == "connect_proxy_egress":
            return DockerCommandResult(0, b"", b"")
        if marker.startswith("inspect_identity_"):
            role = marker.removeprefix("inspect_identity_")
            return self._identity_observation(command, role)
        if marker.startswith("state_"):
            role = marker.removeprefix("state_")
            if self.duplicate_state == role:
                return DockerCommandResult(
                    0, b'{"Status":"created","Status":"created"}\n', b""
                )
            state = dict(CREATED_STATE)
            if self.running_state == role:
                state.update({"Status": "running", "Running": True, "Pid": 44})
            return DockerCommandResult(
                0, json.dumps(state, separators=(",", ":")).encode() + b"\n", b""
            )
        if marker.startswith("attest_"):
            document = {"capture_kind": marker}
            if self.attest_canary is not None:
                document["canary"] = self.attest_canary
            return DockerCommandResult(
                0,
                json.dumps([document], separators=(",", ":")).encode() + b"\n",
                b"",
            )
        if marker.startswith("remove_"):
            role = marker.removeprefix("remove_")
            if role not in self.retain:
                self.present[role] = False
            return DockerCommandResult(0, f"{self._identity(role)}\n".encode(), b"")
        if marker.startswith("list_"):
            role = marker.removeprefix("list_")
            stdout = f"{self._identity(role)}\n".encode() if self.present[role] else b""
            return DockerCommandResult(0, stdout, b"")
        raise AssertionError(command)

    def _identity_observation(
        self, command: tuple[str, ...], role: str
    ) -> DockerCommandResult:
        args = command[5:]
        kind = args[0]
        target = args[-1]
        if not self.present[role]:
            error = (
                f"Error response from daemon: No such container: {target}\n"
                if kind == "container"
                else f"Error response from daemon: network {target} not found\n"
            )
            return DockerCommandResult(1, b"", error.encode())
        identity = self._identity(role)
        if self.mismatch_identity_once == role:
            self.mismatch_identity_once = None
            identity = "9" * 64
        name = self._name(role)
        if kind == "container":
            name = f"/{name}"
        return DockerCommandResult(0, f"{identity}|{name}\n".encode(), b"")

    def _marker(self, command: tuple[str, ...]) -> str:
        args = command[5:]
        if args[0] == "version":
            return "binding_version"
        if args[0] == "info":
            return "binding_info"
        if args[:2] == ("network", "create"):
            return f"create_{self._role_from_target(args[-1])}"
        if args[:2] == ("container", "create"):
            name = next(
                part.removeprefix("--name=")
                for part in args
                if part.startswith("--name=")
            )
            return f"create_{self._role_from_target(name)}"
        if args[:2] == ("network", "connect"):
            return "connect_proxy_egress"
        if (
            len(args) > 3
            and args[1] == "inspect"
            and args[2] == "--format={{.Id}}|{{.Name}}"
        ):
            return f"inspect_identity_{self._role_from_target(args[-1])}"
        if (
            len(args) > 3
            and args[:2] == ("container", "inspect")
            and args[2] == "--format={{json .State}}"
        ):
            return f"state_{self._role_from_target(args[-1])}"
        if args[:2] == ("image", "inspect"):
            return "attest_images"
        if args[:2] == ("container", "inspect"):
            return "attest_containers"
        if args[:2] == ("network", "inspect"):
            return "attest_networks"
        if len(args) > 2 and args[1] == "rm":
            return f"remove_{self._role_from_target(args[-1])}"
        if len(args) > 2 and args[1] == "ls":
            return f"list_{self._role_from_filter(args[-1])}"
        raise AssertionError(command)

    def _assert_frozen_prefix(self, command: tuple[str, ...]) -> None:
        self.assertion(
            command[:5]
            == (
                self.plan.topology.docker_executable,
                "--config",
                self.plan.docker_config_directory,
                "--host",
                self.plan.docker_host,
            ),
            command,
        )

    @staticmethod
    def assertion(condition: bool, detail: object) -> None:
        if not condition:
            raise AssertionError(detail)

    def _role_from_target(self, target: str) -> str:
        mapping = {
            self.plan.topology.runtime_container: "runtime",
            self.plan.topology.proxy_container: "proxy",
            self.plan.topology.internal_network: "internal",
            self.plan.topology.egress_network: "egress",
            RUNTIME_ID: "runtime",
            PROXY_ID: "proxy",
            INTERNAL_ID: "internal",
            EGRESS_ID: "egress",
        }
        try:
            return mapping[target]
        except KeyError:
            raise AssertionError(f"unexpected fake target: {target!r}") from None

    def _role_from_filter(self, value: str) -> str:
        for role in ("runtime", "proxy", "internal", "egress"):
            if self._name(role) in value:
                return role
        raise AssertionError(value)

    def _name(self, role: str) -> str:
        return {
            "runtime": self.plan.topology.runtime_container,
            "proxy": self.plan.topology.proxy_container,
            "internal": self.plan.topology.internal_network,
            "egress": self.plan.topology.egress_network,
        }[role]

    @staticmethod
    def _identity(role: str) -> str:
        return {
            "runtime": RUNTIME_ID,
            "proxy": PROXY_ID,
            "internal": INTERNAL_ID,
            "egress": EGRESS_ID,
        }[role]


class SupervisorV2TestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        docker = root / "docker.exe"
        docker.write_bytes(b"bounded fake docker binary")
        topology = build_codex_docker_topology_v2_plan(
            docker_executable=str(docker.resolve()),
            attempt_id="A-GLM53-SUPERVISOR-V2-001",
            runtime_image_id=RUNTIME_IMAGE,
            proxy_image_id=PROXY_IMAGE,
            nonce="1" * 32,
        )
        stem = topology.runtime_container.removeprefix("rwb-cp2-runtime-")
        config = root / f"rwb-cp2-docker-config-{stem}"
        config.mkdir()
        self.plan = CodexDockerSupervisorV2Plan(
            topology=topology,
            docker_config_directory=str(config.resolve()),
            docker_host=DOCKER_HOST,
        )
        self.attestation = CodexDockerTopologyV2Attestation(
            attempt_sha256=topology.attempt_sha256,
            runtime_container_id=RUNTIME_ID,
            proxy_container_id=PROXY_ID,
            internal_network_id=INTERNAL_ID,
            egress_network_id=EGRESS_ID,
            proxy_url=topology.proxy_url,
        )

    def run_transaction(
        self, executor: FakeSupervisorV2Executor, *, timeout_seconds: float = 10.0
    ) -> object:
        with patch.object(
            supervisor_module,
            "attest_codex_docker_topology_v2",
            return_value=self.attestation,
        ) as validator:
            result = CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=timeout_seconds)
        self.assertEqual(1, validator.call_count)
        return result


class SupervisorV2SuccessTests(SupervisorV2TestCase):
    def test_attestation_binds_three_distinct_parser_temporary_payloads(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        with patch.object(
            supervisor_module,
            "attest_codex_docker_topology_v2",
            return_value=self.attestation,
        ) as validator:
            result = CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        kwargs = validator.call_args.kwargs
        payloads = (
            kwargs["image_inspect_json"],
            kwargs["container_inspect_json"],
            kwargs["network_inspect_json"],
        )
        self.assertEqual(3, len(set(payloads)))
        captures = [
            item for item in result.audit.commands if item.phase.startswith("attest-")
        ]
        self.assertEqual(3, len(captures))
        self.assertEqual(
            [hashlib.sha256(payload).hexdigest() for payload in payloads],
            [item.stdout_sha256 for item in captures],
        )
        self.assertTrue(all(item.stdout == b"" for item in captures))

    def test_result_audit_and_cleanup_objects_reject_inconsistent_overclaims(
        self,
    ) -> None:
        result = self.run_transaction(FakeSupervisorV2Executor(self.plan))
        with self.assertRaises(ValueError):
            replace(result.audit, commands=(), capture_complete=True)
        with self.assertRaises(ValueError):
            replace(result.cleanup, daemon_rebound=False)
        with self.assertRaises(ValueError):
            replace(result, plan_sha256="9" * 64)
        with self.assertRaises(ValueError):
            replace(result, start_commands=(("forbidden",),))

    def test_success_is_no_start_and_has_complete_transaction_capture(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        result = self.run_transaction(executor)

        self.assertFalse(CODEX_DOCKER_SUPERVISOR_V2_LIVE_READY)
        self.assertFalse(result.attestation.capture_complete)
        self.assertTrue(result.attestation.inspect_validation_complete)
        self.assertTrue(result.transaction_capture_complete)
        self.assertTrue(result.capture_complete)
        self.assertEqual((), result.start_commands)
        self.assertEqual((), result.attach_commands)
        self.assertEqual((), result.exec_commands)
        self.assertFalse(result.start_command_issued)
        self.assertTrue(result.observed_created_state)
        self.assertEqual("single-writer-daemon-assumption", result.assurance_scope)
        self.assertTrue(result.cleanup.absence_verified)
        self.assertTrue(result.cleanup.config_rebound)
        self.assertEqual(4, result.cleanup.exact_name_list_proofs)
        self.assertEqual(4, result.cleanup.exact_name_inspect_proofs)
        self.assertEqual(4, result.cleanup.exact_id_inspect_proofs)
        self.assertFalse(any(executor.present.values()))

    def test_all_commands_freeze_binary_config_host_empty_env_and_deadline(
        self,
    ) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        result = self.run_transaction(executor)

        self.assertRegex(result.plan_sha256, r"[0-9a-f]{64}\Z")
        self.assertRegex(result.audit.transcript_sha256, r"[0-9a-f]{64}\Z")
        self.assertEqual(
            hashlib.sha256(DAEMON_ID.encode()).hexdigest(),
            result.daemon.daemon_id_sha256,
        )
        self.assertEqual(len(DAEMON_ID), result.daemon.daemon_id_bytes)
        for call, capture in zip(executor.calls, result.audit.commands, strict=True):
            command, stdin, timeout, stdout_limit, stderr_limit, environment, _ = call
            self.assertEqual(b"", stdin)
            self.assertEqual({}, environment)
            self.assertEqual(self.plan.topology.docker_executable, command[0])
            self.assertEqual(
                (
                    "--config",
                    self.plan.docker_config_directory,
                    "--host",
                    DOCKER_HOST,
                ),
                command[1:5],
            )
            self.assertGreater(timeout, 0)
            cleanup_phase = capture.phase.startswith(
                "cleanup-"
            ) or capture.phase.startswith(("binding-precleanup", "binding-closeout"))
            active_deadline = (
                result.audit.cleanup_deadline_monotonic
                if cleanup_phase
                else result.audit.transaction_deadline_monotonic
            )
            assert active_deadline is not None
            self.assertLessEqual(timeout, active_deadline - capture.started_monotonic)
            self.assertLessEqual(len(capture.stdout), stdout_limit)
            self.assertLessEqual(len(capture.stderr), stderr_limit)
        binding_captures = [
            item for item in result.audit.commands if item.phase.startswith("binding-")
        ]
        self.assertEqual(6, len(binding_captures))
        self.assertTrue(all(item.stdout == b"" for item in binding_captures))
        self.assertTrue(
            all(item.stdout_observed_bytes > 0 for item in binding_captures)
        )
        self.assertTrue(all(not item.stdout_retained for item in binding_captures))
        self.assertTrue(all(item.stdout == b"" for item in result.audit.commands))
        self.assertTrue(all(item.stderr == b"" for item in result.audit.commands))
        self.assertTrue(all(not item.stdout_retained for item in result.audit.commands))
        self.assertTrue(all(not item.stderr_retained for item in result.audit.commands))

    def test_cleanup_is_state_attested_id_only_without_force(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        self.run_transaction(executor)
        calls = [(call[0][5:], call[-1]) for call in executor.calls]
        removals = [
            (args, marker) for args, marker in calls if marker.startswith("remove_")
        ]

        self.assertEqual(4, len(removals))
        for args, marker in removals:
            self.assertNotIn("--force", args)
            self.assertRegex(args[-1], r"[0-9a-f]{64}\Z")
            self.assertNotIn(self.plan.topology.runtime_container, args)
            self.assertNotIn(self.plan.topology.proxy_container, args)
            if marker in {"remove_runtime", "remove_proxy"}:
                state_marker = marker.replace("remove_", "state_")
                state_index = next(
                    i
                    for i, call in enumerate(executor.calls)
                    if call[-1] == state_marker
                )
                removal_index = next(
                    i for i, call in enumerate(executor.calls) if call[-1] == marker
                )
                self.assertLess(state_index, removal_index)

        forbidden = {"start", "attach", "exec", "run", "context"}
        for command, *_ in executor.calls:
            args = command[5:]
            self.assertNotIn(args[0], forbidden)
            if args[0] == "container" and len(args) > 1:
                self.assertNotIn(args[1], forbidden)
        removal_targets = {args[-1] for args, _ in removals}
        self.assertTrue(
            removal_targets.isdisjoint(
                {
                    self.plan.topology.runtime_container,
                    self.plan.topology.proxy_container,
                    self.plan.topology.internal_network,
                    self.plan.topology.egress_network,
                }
            )
        )

    def test_both_networks_are_reconciled_by_name_and_id_immediately(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        self.run_transaction(executor)
        markers = [call[-1] for call in executor.calls]
        for role in ("internal", "egress"):
            create_index = markers.index(f"create_{role}")
            inspect_indices = [
                index
                for index, marker in enumerate(markers)
                if marker == f"inspect_identity_{role}" and index > create_index
            ]
            self.assertGreaterEqual(len(inspect_indices), 4)
            self.assertEqual([create_index + 1, create_index + 2], inspect_indices[:2])

    def test_live_entry_rejects_before_inspecting_any_input(self) -> None:
        supervisor = CodexDockerTopologySupervisorV2(
            executor=FakeSupervisorV2Executor(self.plan), clock=PoisonClock()
        )
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "supervisor-v2-live-disabled"
        ):
            supervisor.run_live(PoisonValue(), environment=PoisonValue())

    def test_offline_entry_self_locks_if_supervisor_flag_is_ever_enabled(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        with (
            patch.object(
                supervisor_module,
                "CODEX_DOCKER_SUPERVISOR_V2_LIVE_READY",
                True,
            ),
            self.assertRaisesRegex(
                CodexDockerSupervisorV2Error, "contract-unexpected-live"
            ),
        ):
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=PoisonClock()
            ).run_offline_transaction(self.plan)
        self.assertEqual([], executor.calls)


class SupervisorV2FailureTests(SupervisorV2TestCase):
    def test_cancellation_before_create_is_not_normalized(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan, cancel_at="binding_version")
        with self.assertRaises(KeyboardInterrupt) as caught:
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        self.assertFalse(any(call[-1].startswith("create_") for call in executor.calls))
        self.assertIsNotNone(caught.exception.audit)
        self.assertFalse(caught.exception.audit.capture_complete)

    def test_cancellation_after_known_effect_closes_out_then_rethrows(self) -> None:
        executor = FakeSupervisorV2Executor(
            self.plan,
            cancel_at="connect_proxy_egress",
            cancel_after_effect=True,
        )
        with self.assertRaises(KeyboardInterrupt) as caught:
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        self.assertFalse(any(executor.present.values()))
        self.assertTrue(any(call[-1] == "remove_proxy" for call in executor.calls))
        self.assertIsNotNone(caught.exception.audit)
        self.assertFalse(caught.exception.audit.capture_complete)

    def test_cancellation_during_ambiguous_create_is_retained_in_composite(
        self,
    ) -> None:
        for after_effect in (False, True):
            with self.subTest(after_effect=after_effect):
                executor = FakeSupervisorV2Executor(
                    self.plan,
                    cancel_at="create_runtime",
                    cancel_after_effect=after_effect,
                )
                with self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught:
                    CodexDockerTopologySupervisorV2(
                        executor=executor, clock=StepClock()
                    ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                self.assertIsInstance(caught.exception.primary_error, KeyboardInterrupt)
                self.assertFalse(caught.exception.audit.capture_complete)
                self.assertFalse(
                    any(call[-1] == "remove_runtime" for call in executor.calls)
                )

    def test_inspect_canary_never_enters_success_or_failure_evidence(self) -> None:
        canary = SENSITIVE_CANARY
        success_executor = FakeSupervisorV2Executor(self.plan, attest_canary=canary)
        success = self.run_transaction(success_executor)
        self.assertNotIn(canary, repr(success.audit))
        self.assertTrue(all(item.stdout == b"" for item in success.audit.commands))
        self.assertTrue(all(item.stderr == b"" for item in success.audit.commands))

        def reject_inspect_documents(
            *_args: object, **_kwargs: object
        ) -> CodexDockerTopologyV2Attestation:
            raise RuntimeError(canary)

        failure_executor = FakeSupervisorV2Executor(self.plan, attest_canary=canary)
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_topology_v2",
                new=reject_inspect_documents,
            ),
            self.assertRaises(CodexDockerSupervisorV2Error) as caught,
        ):
            CodexDockerTopologySupervisorV2(
                executor=failure_executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        failure = caught.exception
        self.assertIsNotNone(failure.audit)
        self.assertNotIn(canary, str(failure))
        self.assertNotIn(canary, repr(failure))
        self.assertNotIn(canary, repr(vars(failure)))
        self.assertNotIn(canary, repr(failure.audit))
        self.assertIsNone(failure.__context__)
        self.assertTrue(all(item.stdout == b"" for item in failure.audit.commands))
        self.assertTrue(all(item.stderr == b"" for item in failure.audit.commands))

    def test_primary_stage_fault_matrix_runs_required_cleanup(self) -> None:
        stages = (
            ("binding_version", False),
            ("list_runtime", False),
            ("connect_proxy_egress", True),
            ("attest_images", True),
            ("attest_containers", True),
            ("attest_networks", True),
        )
        for stage, cleanup_expected in stages:
            with self.subTest(stage=stage):
                executor = FakeSupervisorV2Executor(self.plan, fail_at=stage)
                with (
                    patch.object(
                        supervisor_module,
                        "attest_codex_docker_topology_v2",
                        return_value=self.attestation,
                    ),
                    self.assertRaises(CodexDockerSupervisorV2Error),
                ):
                    CodexDockerTopologySupervisorV2(
                        executor=executor, clock=StepClock()
                    ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                removals = [
                    call for call in executor.calls if call[-1].startswith("remove_")
                ]
                self.assertEqual(cleanup_expected, bool(removals))
                self.assertFalse(any(executor.present.values()))

    def test_removal_transport_fault_is_cleanup_failure_even_after_effect(self) -> None:
        for after_effect in (False, True):
            with self.subTest(after_effect=after_effect):
                executor = FakeSupervisorV2Executor(
                    self.plan,
                    fail_at="remove_proxy",
                    fail_after_effect=after_effect,
                )
                with (
                    patch.object(
                        supervisor_module,
                        "attest_codex_docker_topology_v2",
                        return_value=self.attestation,
                    ),
                    self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught,
                ):
                    CodexDockerTopologySupervisorV2(
                        executor=executor, clock=StepClock()
                    ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                self.assertIsNone(caught.exception.primary_error)
                self.assertFalse(caught.exception.audit.capture_complete)
                markers = [call[-1] for call in executor.calls]
                self.assertIn("remove_internal", markers)
                self.assertIn("remove_egress", markers)
                self.assertEqual(
                    4,
                    sum(
                        marker.startswith("list_")
                        for marker in markers[markers.index("remove_proxy") + 1 :]
                    ),
                )

    def test_every_ambiguous_create_is_never_adopted_and_never_complete(self) -> None:
        for stage in (
            "create_internal",
            "create_egress",
            "create_proxy",
            "create_runtime",
        ):
            for after_effect in (False, True):
                with self.subTest(stage=stage, after_effect=after_effect):
                    executor = FakeSupervisorV2Executor(
                        self.plan,
                        fail_at=stage,
                        fail_after_effect=after_effect,
                    )
                    with (
                        patch.object(
                            supervisor_module,
                            "attest_codex_docker_topology_v2",
                            return_value=self.attestation,
                        ),
                        self.assertRaises(
                            CodexDockerSupervisorV2CleanupError
                        ) as caught,
                    ):
                        CodexDockerTopologySupervisorV2(
                            executor=executor, clock=StepClock()
                        ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                    self.assertIsInstance(
                        caught.exception.primary_error, CodexDockerSupervisorV2Error
                    )
                    self.assertIsInstance(
                        caught.exception.cleanup_error, CodexDockerSupervisorV2Error
                    )
                    self.assertIsNotNone(caught.exception.audit)
                    self.assertFalse(caught.exception.audit.capture_complete)
                    failed_role = stage.removeprefix("create_")
                    self.assertFalse(
                        any(
                            call[-1] == f"remove_{failed_role}"
                            for call in executor.calls
                        )
                    )

    def test_network_identity_mismatch_is_ownership_ambiguous(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan, mismatch_identity_once="egress")
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_topology_v2",
                return_value=self.attestation,
            ),
            self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught,
        ):
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        self.assertFalse(caught.exception.audit.capture_complete)
        self.assertTrue(executor.present["egress"])
        self.assertFalse(any(call[-1] == "remove_egress" for call in executor.calls))

    def test_attestation_attempt_and_proxy_metadata_are_reconciled(self) -> None:
        drifts = (
            replace(self.attestation, attempt_sha256="9" * 64),
            replace(self.attestation, proxy_url="http://172.28.53.3:9999"),
        )
        for drift in drifts:
            with self.subTest(drift=drift):
                executor = FakeSupervisorV2Executor(self.plan)
                with (
                    patch.object(
                        supervisor_module,
                        "attest_codex_docker_topology_v2",
                        return_value=drift,
                    ),
                    self.assertRaisesRegex(
                        CodexDockerSupervisorV2Error,
                        "inspect-validation-incomplete",
                    ),
                ):
                    CodexDockerTopologySupervisorV2(
                        executor=executor, clock=StepClock()
                    ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                self.assertFalse(any(executor.present.values()))

    def test_duplicate_daemon_json_is_rejected_before_any_create(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan, duplicate_version=True)
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "version-json-invalid"
        ) as caught:
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan)
        self.assertFalse(any(call[-1].startswith("create_") for call in executor.calls))
        self.assertIsNotNone(caught.exception.audit)
        self.assertFalse(caught.exception.audit.capture_complete)

    def test_duplicate_or_running_state_prevents_container_deletion(self) -> None:
        for option in ("duplicate", "running"):
            with self.subTest(option=option):
                executor = FakeSupervisorV2Executor(
                    self.plan,
                    duplicate_state="runtime" if option == "duplicate" else None,
                    running_state="runtime" if option == "running" else None,
                )
                with (
                    patch.object(
                        supervisor_module,
                        "attest_codex_docker_topology_v2",
                        return_value=self.attestation,
                    ),
                    self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught,
                ):
                    CodexDockerTopologySupervisorV2(
                        executor=executor, clock=StepClock()
                    ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                self.assertIsNone(caught.exception.primary_error)
                self.assertTrue(executor.present["runtime"])
                self.assertFalse(
                    any(call[-1] == "remove_runtime" for call in executor.calls)
                )

    def test_primary_attestation_and_cleanup_failure_are_both_retained(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan, retain=frozenset({"proxy"}))
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_topology_v2",
                side_effect=CodexDockerTopologyV2Error("invalid"),
            ),
            self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught,
        ):
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        self.assertRegex(str(caught.exception.primary_error), "attestation-failed")
        self.assertRegex(str(caught.exception.cleanup_error), "cleanup-unverified")
        self.assertIs(caught.exception.__cause__, caught.exception.cleanup_error)

    def test_preexisting_exact_name_is_not_adopted_or_removed(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        executor.present["internal"] = True
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "preflight-resource-not-absent"
        ):
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan)
        self.assertTrue(executor.present["internal"])
        self.assertFalse(any(call[-1].startswith("remove_") for call in executor.calls))

    def test_oversized_create_output_is_bounded_and_ownership_ambiguous(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan, oversize_at="create_internal")
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_topology_v2",
                return_value=self.attestation,
            ),
            self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught,
        ):
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=StepClock()
            ).run_offline_transaction(self.plan, timeout_seconds=10.0)
        capture = next(
            item
            for item in caught.exception.audit.commands
            if item.phase == "create-internal"
        )
        self.assertFalse(capture.transport_complete)
        self.assertEqual(65_537, capture.stdout_observed_bytes)
        self.assertEqual(0, len(capture.stdout))
        self.assertFalse(capture.stdout_retained)
        self.assertFalse(caught.exception.audit.capture_complete)

    def test_daemon_or_config_drift_invalidates_cleanup_capture(self) -> None:
        for mode in ("daemon", "config"):
            with self.subTest(mode=mode):
                executor = FakeSupervisorV2Executor(
                    self.plan,
                    daemon_drift=mode == "daemon",
                    write_config_at="attest_networks" if mode == "config" else None,
                )
                with (
                    patch.object(
                        supervisor_module,
                        "attest_codex_docker_topology_v2",
                        return_value=self.attestation,
                    ),
                    self.assertRaises(CodexDockerSupervisorV2CleanupError) as caught,
                ):
                    CodexDockerTopologySupervisorV2(
                        executor=executor, clock=StepClock()
                    ).run_offline_transaction(self.plan, timeout_seconds=10.0)
                self.assertIsNone(caught.exception.primary_error)
                self.assertFalse(caught.exception.audit.capture_complete)
                self.assertFalse(
                    any(call[-1].startswith("remove_") for call in executor.calls)
                )
                unexpected = Path(self.plan.docker_config_directory, "unexpected.json")
                if unexpected.exists():
                    unexpected.unlink()

    def test_single_absolute_deadline_is_not_reset_per_command(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        clock = StepClock(step=0.6)
        with self.assertRaises(CodexDockerSupervisorV2Error) as caught:
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=clock
            ).run_offline_transaction(self.plan, timeout_seconds=1.0)
        self.assertIn(
            "deadline",
            str(caught.exception)
            + str(getattr(caught.exception, "primary_error", ""))
            + str(getattr(caught.exception, "cleanup_error", "")),
        )
        self.assertTrue(all(call[2] <= 1.0 for call in executor.calls))

    def test_primary_deadline_exhaustion_gets_one_independent_cleanup_deadline(
        self,
    ) -> None:
        clock = ManualClock()
        executor = FakeSupervisorV2Executor(
            self.plan,
            clock_to_advance=clock,
            advance_clock_at="attest_images",
            advance_clock_to=2.0,
        )
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "absolute-deadline-exceeded"
        ) as caught:
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=clock
            ).run_offline_transaction(self.plan, timeout_seconds=1.0)
        self.assertFalse(any(executor.present.values()))
        self.assertIsNotNone(caught.exception.audit)
        self.assertEqual(1.0, caught.exception.audit.transaction_deadline_monotonic)
        self.assertEqual(32.0, caught.exception.audit.cleanup_deadline_monotonic)
        self.assertFalse(caught.exception.audit.capture_complete)
        self.assertTrue(any(call[-1] == "remove_runtime" for call in executor.calls))

    def test_slow_local_binary_binding_cannot_escape_transaction_deadline(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        clock = ManualClock()
        real_binder = supervisor_module._bind_docker_binary

        def slow_binder(executable: str) -> object:
            clock.value = 2.0
            return real_binder(executable)

        with (
            patch.object(supervisor_module, "_bind_docker_binary", new=slow_binder),
            self.assertRaisesRegex(
                CodexDockerSupervisorV2Error, "absolute-deadline-exceeded"
            ),
        ):
            CodexDockerTopologySupervisorV2(
                executor=executor, clock=clock
            ).run_offline_transaction(self.plan, timeout_seconds=1.0)
        self.assertEqual([], executor.calls)

    def test_plan_rejects_implicit_remote_or_nonblank_docker_state(self) -> None:
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "docker-host-must-be-local"
        ):
            CodexDockerSupervisorV2Plan(
                topology=self.plan.topology,
                docker_config_directory=self.plan.docker_config_directory,
                docker_host="tcp://127.0.0.1:2375",
            )
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "docker-binary-not-absolute"
        ):
            CodexDockerSupervisorV2Plan(
                topology=replace(
                    self.plan.topology,
                    docker_executable=r"\\server\share\docker.exe",
                ),
                docker_config_directory=self.plan.docker_config_directory,
                docker_host=DOCKER_HOST,
            )
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "config-directory-must-be-local"
        ):
            CodexDockerSupervisorV2Plan(
                topology=self.plan.topology,
                docker_config_directory=r"\\server\share\rwb-cp2-docker-config-x",
                docker_host=DOCKER_HOST,
            )
        Path(self.plan.docker_config_directory, "config.json").write_text(
            "{}", encoding="utf-8"
        )
        with self.assertRaisesRegex(
            CodexDockerSupervisorV2Error, "config-directory-not-private-blank"
        ):
            CodexDockerSupervisorV2Plan(
                topology=self.plan.topology,
                docker_config_directory=self.plan.docker_config_directory,
                docker_host=DOCKER_HOST,
            )

    def test_invalid_timeout_and_missing_executor_fail_before_commands(self) -> None:
        with self.assertRaisesRegex(TypeError, "executor is required"):
            CodexDockerTopologySupervisorV2(executor=None)  # type: ignore[arg-type]
        executor = FakeSupervisorV2Executor(self.plan)
        for timeout in (0, float("nan"), math.inf):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                CodexDockerTopologySupervisorV2(
                    executor=executor, clock=StepClock()
                ).run_offline_transaction(self.plan, timeout_seconds=timeout)
        self.assertEqual([], executor.calls)

    def test_no_command_or_environment_contains_a_credential(self) -> None:
        executor = FakeSupervisorV2Executor(self.plan)
        self.run_transaction(executor)
        serialized = "\n".join(" ".join(call[0]) for call in executor.calls)
        self.assertNotIn(SENSITIVE_CANARY, serialized)
        self.assertNotRegex(
            serialized,
            r"(?:API[_-]?KEY|AUTHORIZATION|TOKEN|SECRET|PASSWORD|CREDENTIAL)=",
        )
        self.assertTrue(all(call[5] == {} for call in executor.calls))


if __name__ == "__main__":
    unittest.main()
