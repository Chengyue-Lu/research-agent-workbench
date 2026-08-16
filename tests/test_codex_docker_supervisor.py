from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import research_workbench.adapters.codex_docker_supervisor as supervisor_module
from research_workbench.adapters.codex_coding_plan_docker import (
    DockerCommandResult,
)
from research_workbench.adapters.codex_docker_network import (
    CODEX_DOCKER_RUNTIME_PROXY_URL,
    CodexDockerNetworkAttestation,
    build_codex_docker_network_plan,
)
from research_workbench.adapters.codex_docker_supervisor import (
    CODEX_DOCKER_SUPERVISOR_LIVE_READY,
    CodexDockerSupervisorCleanupError,
    CodexDockerSupervisorError,
    CodexDockerTopologySupervisor,
)

RUNTIME_IMAGE = "sha256:" + "e" * 64
PROXY_IMAGE = "sha256:" + "f" * 64
RUNTIME_ID = "a" * 64
PROXY_ID = "b" * 64
INTERNAL_ID = "c" * 64
EGRESS_ID = "d" * 64
SECRET = "must-not-appear-in-supervisor-commands"

IDENTITY_FORMAT = "--format={{.Id}}|{{.Name}}"


class FakeSupervisorExecutor:
    def __init__(
        self,
        plan: object,
        *,
        fail_at: str | None = None,
        fail_after_effect: bool = False,
        retain: frozenset[str] = frozenset(),
        mismatch_identity_once: str | None = None,
    ) -> None:
        self.plan = plan
        self.fail_at = fail_at
        self.fail_after_effect = fail_after_effect
        self.retain = retain
        self.mismatch_identity_once = mismatch_identity_once
        self.failure_consumed = False
        self.calls: list[tuple[tuple[str, ...], bytes, float, int, int, str]] = []
        self.present = {
            "runtime": False,
            "proxy": False,
            "internal": False,
            "egress": False,
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
        marker = self._marker(command)
        self.calls.append(
            (
                command,
                stdin,
                timeout_seconds,
                stdout_limit,
                stderr_limit,
                marker,
            )
        )
        should_fail = self.fail_at == marker and not self.failure_consumed
        if should_fail and not self.fail_after_effect:
            self.failure_consumed = True
            raise RuntimeError("untrusted executor detail")

        result = self._execute_command(command, marker)
        if should_fail:
            self.failure_consumed = True
            raise RuntimeError("ambiguous command completion")
        return result

    def _execute_command(
        self, command: tuple[str, ...], marker: str
    ) -> DockerCommandResult:
        if marker.startswith("create_"):
            role = marker.removeprefix("create_")
            self.present[role] = True
            return DockerCommandResult(0, f"{self._identity(role)}\n".encode(), b"")
        if marker == "connect_proxy_egress":
            return DockerCommandResult(0, b"", b"")
        if marker.startswith("inspect_identity_"):
            role = marker.removeprefix("inspect_identity_")
            return self._identity_observation(command, role)
        if marker.startswith("attest_"):
            return DockerCommandResult(0, b'[{"bounded":true}]\n', b"")
        if marker.startswith("remove_"):
            role = marker.removeprefix("remove_")
            if role not in self.retain:
                self.present[role] = False
            return DockerCommandResult(0, b"removed\n", b"")
        if marker.startswith("list_"):
            role = marker.removeprefix("list_")
            stdout = f"{self._identity(role)}\n".encode() if self.present[role] else b""
            return DockerCommandResult(0, stdout, b"")
        raise AssertionError(command)

    def _identity_observation(
        self, command: tuple[str, ...], role: str
    ) -> DockerCommandResult:
        kind = command[1]
        target = command[-1]
        if not self.present[role]:
            if kind == "container":
                error = f"Error response from daemon: No such container: {target}\n"
            else:
                error = f"Error response from daemon: network {target} not found\n"
            return DockerCommandResult(1, b"", error.encode())
        identity = self._identity(role)
        if self.mismatch_identity_once == role:
            self.mismatch_identity_once = None
            identity = "9" * 64
        observed_name = self._name(role)
        if kind == "container":
            observed_name = f"/{observed_name}"
        return DockerCommandResult(0, f"{identity}|{observed_name}\n".encode(), b"")

    def _marker(self, command: tuple[str, ...]) -> str:
        if command[1:3] == ("network", "create"):
            return f"create_{self._role_from_target(command[-1])}"
        if command[1:3] == ("container", "create"):
            name = next(
                part.removeprefix("--name=")
                for part in command
                if part.startswith("--name=")
            )
            return f"create_{self._role_from_target(name)}"
        if command[1:3] == ("network", "connect"):
            return "connect_proxy_egress"
        if (
            len(command) > 3
            and command[2] == "inspect"
            and command[3] == IDENTITY_FORMAT
        ):
            return f"inspect_identity_{self._role_from_target(command[-1])}"
        if command[1:3] == ("image", "inspect"):
            return "attest_images"
        if command[1:3] == ("container", "inspect") and IDENTITY_FORMAT not in command:
            return "attest_containers"
        if command[1:3] == ("network", "inspect") and IDENTITY_FORMAT not in command:
            return "attest_networks"
        if command[2] == "rm":
            return f"remove_{self._role_from_target(command[-1])}"
        if command[2] == "ls":
            return f"list_{self._role_from_filter(command[-1])}"
        return "unknown"

    def _role_from_target(self, target: str) -> str:
        mapping = {
            self.plan.runtime_container: "runtime",
            self.plan.proxy_container: "proxy",
            self.plan.internal_network: "internal",
            self.plan.egress_network: "egress",
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
            "runtime": self.plan.runtime_container,
            "proxy": self.plan.proxy_container,
            "internal": self.plan.internal_network,
            "egress": self.plan.egress_network,
        }[role]

    @staticmethod
    def _identity(role: str) -> str:
        return {
            "runtime": RUNTIME_ID,
            "proxy": PROXY_ID,
            "internal": INTERNAL_ID,
            "egress": EGRESS_ID,
        }[role]


class PoisonValue:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"live input was inspected: {name}")


class CodexDockerSupervisorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        docker = Path(self.directory.name) / "docker.exe"
        docker.write_bytes(b"fake bounded docker boundary")
        self.plan = build_codex_docker_network_plan(
            docker_executable=docker,
            attempt_id="A-GLM53-SUPERVISOR-001",
            runtime_image_id=RUNTIME_IMAGE,
            proxy_image_id=PROXY_IMAGE,
            nonce="1" * 32,
        )
        self.attestation = CodexDockerNetworkAttestation(
            attempt_sha256=self.plan.attempt_sha256,
            runtime_container_id=RUNTIME_ID,
            proxy_container_id=PROXY_ID,
            internal_network_id=INTERNAL_ID,
            egress_network_id=EGRESS_ID,
            proxy_url=CODEX_DOCKER_RUNTIME_PROXY_URL,
        )

    def run_transaction(self, executor: FakeSupervisorExecutor) -> object:
        with patch.object(
            supervisor_module,
            "attest_codex_docker_network",
            return_value=self.attestation,
        ) as validator:
            result = CodexDockerTopologySupervisor(
                executor=executor
            ).run_offline_transaction(self.plan, timeout_seconds=17.0)
        self.assertEqual(1, validator.call_count)
        return result


class CodexDockerSupervisorSuccessTests(CodexDockerSupervisorTestCase):
    def test_transaction_attests_without_start_and_proves_dual_absence(self) -> None:
        executor = FakeSupervisorExecutor(self.plan)
        result = self.run_transaction(executor)

        self.assertEqual(self.attestation, result.attestation)
        self.assertFalse(result.proxy_started)
        self.assertFalse(result.runtime_started)
        self.assertEqual(
            "docker-proxy-ip-interface-not-frozen", result.start_blocked_reason
        )
        self.assertTrue(result.capture_complete)
        self.assertEqual((0, 0, 0, 0), result.cleanup.removal_returncodes)
        self.assertEqual(4, result.cleanup.exact_name_list_proofs)
        self.assertEqual(4, result.cleanup.exact_name_inspect_proofs)
        self.assertEqual(4, result.cleanup.exact_id_inspect_proofs)
        self.assertTrue(result.cleanup.absence_verified)
        self.assertFalse(any(executor.present.values()))

        markers = [call[-1] for call in executor.calls]
        ordered = (
            "create_internal",
            "create_egress",
            "create_proxy",
            "connect_proxy_egress",
            "create_runtime",
            "attest_images",
            "attest_containers",
            "attest_networks",
        )
        positions = [markers.index(marker) for marker in ordered]
        self.assertEqual(sorted(positions), positions)
        self.assertEqual(4, sum(marker.startswith("remove_") for marker in markers))
        self.assertEqual(8, sum(marker.startswith("list_") for marker in markers))
        verbs = {part for call in executor.calls for part in call[0][1:3]}
        self.assertNotIn("start", verbs)
        self.assertNotIn("exec", verbs)

    def test_all_commands_are_bounded_empty_stdin_and_secret_free(self) -> None:
        executor = FakeSupervisorExecutor(self.plan)
        self.run_transaction(executor)
        serialized = "\n".join(" ".join(call[0]) for call in executor.calls)
        self.assertNotIn(SECRET, serialized)
        self.assertNotRegex(
            serialized,
            r"(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)=",
        )
        self.assertNotIn(
            "--env",
            " ".join(
                command_part
                for command, *_ in executor.calls
                for command_part in command
                if "KEY" in command_part or "CREDENTIAL" in command_part
            ),
        )
        for _, stdin, timeout, stdout_limit, stderr_limit, _ in executor.calls:
            self.assertEqual(b"", stdin)
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 17.0)
            self.assertGreater(stdout_limit, 0)
            self.assertGreater(stderr_limit, 0)
        self.assertFalse(CODEX_DOCKER_SUPERVISOR_LIVE_READY)

    def test_container_create_output_is_reconciled_by_both_name_and_id(self) -> None:
        executor = FakeSupervisorExecutor(self.plan)
        self.run_transaction(executor)
        first_removal = next(
            index
            for index, call in enumerate(executor.calls)
            if call[-1].startswith("remove_")
        )
        identity_targets = [
            call[0][-1]
            for call in executor.calls[:first_removal]
            if call[-1].startswith("inspect_identity_")
        ]
        self.assertIn(self.plan.proxy_container, identity_targets)
        self.assertIn(PROXY_ID, identity_targets)
        self.assertIn(self.plan.runtime_container, identity_targets)
        self.assertIn(RUNTIME_ID, identity_targets)

    def test_live_entry_is_disabled_before_touching_inputs(self) -> None:
        supervisor = CodexDockerTopologySupervisor(
            executor=FakeSupervisorExecutor(self.plan)
        )
        with self.assertRaisesRegex(
            CodexDockerSupervisorError, "supervisor-live-disabled"
        ):
            supervisor.run_live(PoisonValue(), environment=PoisonValue())


class CodexDockerSupervisorFailureTests(CodexDockerSupervisorTestCase):
    def test_faults_at_every_stage_still_attempt_all_removals_and_proofs(self) -> None:
        stages = (
            ("create_internal", 0),
            ("create_egress", 1),
            ("create_proxy", 2),
            ("connect_proxy_egress", 3),
            ("create_runtime", 3),
            ("attest_images", 4),
            ("attest_containers", 4),
            ("attest_networks", 4),
        )
        for stage, known_resources in stages:
            with self.subTest(stage=stage):
                executor = FakeSupervisorExecutor(self.plan, fail_at=stage)
                with (
                    patch.object(
                        supervisor_module,
                        "attest_codex_docker_network",
                        return_value=self.attestation,
                    ),
                    self.assertRaises(CodexDockerSupervisorError),
                ):
                    CodexDockerTopologySupervisor(
                        executor=executor
                    ).run_offline_transaction(self.plan)
                markers = [call[-1] for call in executor.calls]
                self.assertEqual(
                    known_resources,
                    sum(marker.startswith("remove_") for marker in markers),
                )
                self.assertEqual(
                    8, sum(marker.startswith("list_") for marker in markers)
                )
                self.assertFalse(any(executor.present.values()))

    def test_ambiguous_create_never_acquires_or_deletes_unknown_identity(self) -> None:
        executor = FakeSupervisorExecutor(
            self.plan,
            fail_at="create_proxy",
            fail_after_effect=True,
        )
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_network",
                return_value=self.attestation,
            ),
            self.assertRaisesRegex(
                CodexDockerSupervisorCleanupError,
                "supervisor-cleanup-unverified",
            ) as captured,
        ):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan
            )
        self.assertIsInstance(
            captured.exception.primary_error, CodexDockerSupervisorError
        )
        self.assertTrue(executor.present["proxy"])
        proxy_removals = [call for call in executor.calls if call[-1] == "remove_proxy"]
        self.assertEqual([], proxy_removals)

    def test_identity_mismatch_fails_before_attestation_and_cleanup_succeeds(
        self,
    ) -> None:
        executor = FakeSupervisorExecutor(self.plan, mismatch_identity_once="proxy")
        with self.assertRaisesRegex(
            CodexDockerSupervisorError, "identity-reconcile-failed"
        ):
            self.run_transaction(executor)
        markers = [call[-1] for call in executor.calls]
        self.assertNotIn("attest_images", markers)
        self.assertEqual(3, sum(marker.startswith("remove_") for marker in markers))
        self.assertFalse(any(executor.present.values()))

    def test_cleanup_failure_retains_primary_and_attempts_every_proof(self) -> None:
        executor = FakeSupervisorExecutor(
            self.plan,
            fail_at="attest_networks",
            retain=frozenset({"proxy"}),
        )
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_network",
                return_value=self.attestation,
            ),
            self.assertRaisesRegex(
                CodexDockerSupervisorCleanupError,
                "supervisor-cleanup-unverified",
            ) as captured,
        ):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan
            )
        self.assertIsInstance(
            captured.exception.primary_error, CodexDockerSupervisorError
        )
        self.assertIsInstance(
            captured.exception.cleanup_error, CodexDockerSupervisorError
        )
        self.assertIs(captured.exception.cleanup_error, captured.exception.__cause__)
        markers = [call[-1] for call in executor.calls]
        self.assertEqual(4, sum(marker.startswith("remove_") for marker in markers))
        self.assertEqual(8, sum(marker.startswith("list_") for marker in markers))
        self.assertGreaterEqual(
            sum(marker.startswith("inspect_identity_") for marker in markers), 8
        )

    def test_attested_identity_mismatch_fails_closed_and_never_starts(self) -> None:
        executor = FakeSupervisorExecutor(self.plan)
        drift = CodexDockerNetworkAttestation(
            attempt_sha256=self.plan.attempt_sha256,
            runtime_container_id="9" * 64,
            proxy_container_id=PROXY_ID,
            internal_network_id=INTERNAL_ID,
            egress_network_id=EGRESS_ID,
            proxy_url=CODEX_DOCKER_RUNTIME_PROXY_URL,
        )
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_network",
                return_value=drift,
            ),
            self.assertRaisesRegex(
                CodexDockerSupervisorError, "attested-identity-mismatch"
            ),
        ):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan
            )
        command_words = {word for call in executor.calls for word in call[0][1:3]}
        self.assertNotIn("start", command_words)
        self.assertNotIn("exec", command_words)
        self.assertFalse(any(executor.present.values()))

    def test_incomplete_attestation_cannot_be_reported_as_complete(self) -> None:
        executor = FakeSupervisorExecutor(self.plan)
        incomplete = CodexDockerNetworkAttestation(
            attempt_sha256=self.plan.attempt_sha256,
            runtime_container_id=RUNTIME_ID,
            proxy_container_id=PROXY_ID,
            internal_network_id=INTERNAL_ID,
            egress_network_id=EGRESS_ID,
            proxy_url=CODEX_DOCKER_RUNTIME_PROXY_URL,
            capture_complete=False,
        )
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_network",
                return_value=incomplete,
            ),
            self.assertRaisesRegex(
                CodexDockerSupervisorError, "attestation-capture-incomplete"
            ),
        ):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan
            )
        self.assertFalse(any(executor.present.values()))

    def test_preexisting_exact_name_is_never_removed_or_adopted(self) -> None:
        executor = FakeSupervisorExecutor(self.plan)
        executor.present["internal"] = True
        with self.assertRaisesRegex(
            CodexDockerSupervisorError, "preflight-resource-not-absent"
        ):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan
            )
        self.assertTrue(executor.present["internal"])
        self.assertFalse(any(call[-1].startswith("remove_") for call in executor.calls))

    def test_removal_capture_gap_is_cleanup_failure_even_when_absence_passes(
        self,
    ) -> None:
        executor = FakeSupervisorExecutor(
            self.plan,
            fail_at="remove_proxy",
            fail_after_effect=True,
        )
        with (
            patch.object(
                supervisor_module,
                "attest_codex_docker_network",
                return_value=self.attestation,
            ),
            self.assertRaisesRegex(
                CodexDockerSupervisorCleanupError,
                "supervisor-cleanup-unverified",
            ) as captured,
        ):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan
            )
        self.assertIsNone(captured.exception.primary_error)
        self.assertFalse(any(executor.present.values()))

    def test_invalid_timeout_and_missing_executor_fail_before_docker(self) -> None:
        with self.assertRaisesRegex(TypeError, "executor is required"):
            CodexDockerTopologySupervisor(executor=None)  # type: ignore[arg-type]
        executor = FakeSupervisorExecutor(self.plan)
        with self.assertRaises(ValueError):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan, timeout_seconds=0
            )
        with self.assertRaises(ValueError):
            CodexDockerTopologySupervisor(executor=executor).run_offline_transaction(
                self.plan, timeout_seconds=float("nan")
            )
        self.assertEqual([], executor.calls)


if __name__ == "__main__":
    unittest.main()
