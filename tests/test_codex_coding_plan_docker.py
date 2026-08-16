from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path

from research_workbench.adapters import codex_coding_plan_docker as docker_runtime
from research_workbench.adapters.codex_coding_plan import (
    CodexCodingPlanRuntimeError,
)
from research_workbench.adapters.codex_coding_plan_docker import (
    CODEX_CODING_PLAN_DOCKER_BASE_IMAGE,
    CODEX_CODING_PLAN_DOCKER_CLI_VERSION,
    CODEX_CODING_PLAN_DOCKER_LIVE_READY,
    CODEX_CODING_PLAN_DOCKER_NPM_INTEGRITY,
    BoundedDockerCommandExecutor,
    CodexCodingPlanDockerHost,
    DockerCleanupUnverifiedError,
    DockerCommandResult,
    assert_no_exact_credential_disclosure,
    build_docker_create_command,
)

IMAGE_ID = "sha256:" + ("a" * 64)
CONTAINER_ID = "b" * 64
SECRET = "zhipu-secret-must-never-enter-docker-config"


def successful_probe() -> str:
    return json.dumps(
        {
            "schema": "rwb-codex-coding-plan-docker-probe/0.1",
            "uid": 65532,
            "gid": 65532,
            "network_interfaces": ["lo"],
            "rootfs_read_only": True,
            "workspace_tmpfs_writable": True,
            "host_paths_absent": True,
            "docker_socket_absent": True,
            "credential_observed": False,
            "cap_eff": "0000000000000000",
            "no_new_privs": 1,
            "seccomp": 2,
            "core_dump_limit_zero": True,
        },
        separators=(",", ":"),
    )


class RecordingExecutor:
    def __init__(
        self,
        *,
        start_failure: BaseException | None = None,
        retain_after_rm: bool = False,
    ) -> None:
        self.calls: list[tuple[tuple[str, ...], bytes, float, int, int]] = []
        self.start_failure = start_failure
        self.retain_after_rm = retain_after_rm
        self.container_name = ""
        self.container_present = False

    def execute(
        self,
        command: tuple[str, ...],
        *,
        stdin: bytes,
        timeout_seconds: float,
        stdout_limit: int,
        stderr_limit: int,
    ) -> DockerCommandResult:
        self.calls.append((command, stdin, timeout_seconds, stdout_limit, stderr_limit))
        verb = command[1]
        if verb == "image":
            return DockerCommandResult(0, f"{IMAGE_ID}\n".encode(), b"")
        if verb == "create":
            self.container_name = command[3].removeprefix("--name=")
            self.container_present = True
            return DockerCommandResult(0, f"{CONTAINER_ID}\n".encode(), b"")
        if verb == "container":
            self.assert_inspect_command(command)
            target = command[-1]
            if self.container_present and target in {self.container_name, CONTAINER_ID}:
                observation = f"{CONTAINER_ID}|/{self.container_name}\n".encode()
                return DockerCommandResult(0, observation, b"")
            return DockerCommandResult(
                1,
                b"\n",
                f"Error response from daemon: No such container: {target}\n".encode(),
            )
        if verb == "start":
            if self.start_failure is not None:
                raise self.start_failure
            return DockerCommandResult(0, f"{successful_probe()}\n".encode(), b"")
        if verb == "kill":
            return DockerCommandResult(0, f"{CONTAINER_ID}\n".encode(), b"")
        if verb == "rm":
            if not self.retain_after_rm:
                self.container_present = False
            return DockerCommandResult(0, f"{CONTAINER_ID}\n".encode(), b"")
        raise AssertionError(command)

    def assert_inspect_command(self, command: tuple[str, ...]) -> None:
        if command[2:4] != ("inspect", "--format={{.Id}}|{{.Name}}"):
            raise AssertionError(command)


class PoisonEnvironment(Mapping[str, str]):
    def __getitem__(self, key: str) -> str:
        raise AssertionError(f"credential mapping was read: {key}")

    def __iter__(self) -> Iterator[str]:
        raise AssertionError("credential mapping was iterated")

    def __len__(self) -> int:
        raise AssertionError("credential mapping length was read")


class DockerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.docker = self.root / "docker.exe"
        self.docker.write_bytes(b"test boundary only")


class CodexCodingPlanDockerCommandTests(DockerTestCase):
    def test_create_command_is_immutable_mount_free_and_network_none(self) -> None:
        command = build_docker_create_command(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            container_name="rwb-cp-" + ("c" * 32),
        )
        joined = " ".join(command)
        self.assertEqual(str(self.docker.resolve()), command[0])
        self.assertIn("--pull=never", command)
        self.assertIn("--network=none", command)
        self.assertIn("--read-only", command)
        self.assertIn("--user=65532:65532", command)
        self.assertIn("--cap-drop=ALL", command)
        self.assertIn("--security-opt=no-new-privileges:true", command)
        self.assertIn("--pids-limit=64", command)
        self.assertIn("--memory=536870912", command)
        self.assertIn("--memory-swap=536870912", command)
        self.assertIn("--cpus=1", command)
        self.assertIn("--ulimit=core=0:0", command)
        self.assertIn("--log-driver=none", command)
        self.assertIn("--entrypoint=/runtime/entrypoint.mjs", command)
        self.assertIn(IMAGE_ID, command)
        self.assertEqual("--probe", command[-1])
        self.assertNotIn("--mount", command)
        self.assertNotIn("--volume", command)
        self.assertNotIn("-v", command)
        self.assertNotIn(SECRET, joined)
        self.assertNotIn("API_KEY", joined)

    def test_command_rejects_mutable_image_name_and_nonabsolute_docker(self) -> None:
        with self.assertRaisesRegex(ValueError, "immutable sha256"):
            build_docker_create_command(
                docker_executable=self.docker,
                image_id="rwb/codex:latest",
                container_name="rwb-cp-" + ("c" * 32),
            )
        with self.assertRaisesRegex(ValueError, "absolute docker.exe"):
            build_docker_create_command(
                docker_executable="docker",
                image_id=IMAGE_ID,
                container_name="rwb-cp-" + ("c" * 32),
            )

    def test_private_frame_is_one_shot_and_repr_redacted(self) -> None:
        prompt = "Return a bounded coding plan."
        frame = docker_runtime._build_credential_frame(SECRET, prompt)
        self.assertNotIn(SECRET, repr(frame))
        payload = frame._consume()
        self.assertEqual(b"RWBCP001", payload[:8])
        credential_size = int.from_bytes(payload[8:12], "big")
        self.assertEqual(len(SECRET.encode()), credential_size)
        self.assertIn(SECRET.encode(), payload)
        self.assertIn(prompt.encode(), payload)
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "already-consumed"):
            frame._consume()
        payload[:] = b"\x00" * len(payload)

    def test_frame_rejects_credential_echo_and_oversize(self) -> None:
        with self.assertRaisesRegex(
            CodexCodingPlanRuntimeError, "credential-present-in-prompt"
        ):
            docker_runtime._build_credential_frame(SECRET, f"echo {SECRET}")
        with self.assertRaisesRegex(
            CodexCodingPlanRuntimeError, "credential-byte-limit"
        ):
            docker_runtime._build_credential_frame("x" * 16_385, "prompt")

    def test_exact_secret_scanner_covers_output_and_exception_chains(self) -> None:
        assert_no_exact_credential_disclosure(
            SECRET,
            stdout=b"safe output",
            stderr="safe error",
            error=RuntimeError("safe failure"),
        )
        for field in ("stdout", "stderr"):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(
                    CodexCodingPlanRuntimeError, "credential-disclosure-detected"
                ),
            ):
                assert_no_exact_credential_disclosure(
                    SECRET,
                    **{field: f"prefix {SECRET} suffix"},
                )
        with self.assertRaisesRegex(
            CodexCodingPlanRuntimeError, "credential-disclosure-detected"
        ):
            assert_no_exact_credential_disclosure(
                SECRET, stdout=b"prefix " + SECRET.encode() + b" suffix"
            )
        cause = RuntimeError(f"provider returned {SECRET}")
        wrapper = RuntimeError("outer")
        wrapper.__cause__ = cause
        with self.assertRaisesRegex(
            CodexCodingPlanRuntimeError, "credential-disclosure-detected"
        ) as captured:
            assert_no_exact_credential_disclosure(SECRET, error=wrapper)
        self.assertNotIn(SECRET, str(captured.exception))

    def test_command_result_repr_never_copies_captured_bytes(self) -> None:
        result = DockerCommandResult(1, SECRET.encode(), SECRET.encode())
        self.assertNotIn(SECRET, repr(result))
        self.assertIn("stdout=<", repr(result))


class CodexCodingPlanDockerHostTests(DockerTestCase):
    def test_probe_uses_create_start_attach_rm_and_no_secret(self) -> None:
        executor = RecordingExecutor()
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        result = host.probe()
        self.assertEqual(IMAGE_ID, result.image_id)
        self.assertEqual(CONTAINER_ID, result.container_id)
        verbs = [call[0][1] for call in executor.calls]
        self.assertEqual(
            [
                "image",
                "create",
                "container",
                "start",
                "container",
                "kill",
                "rm",
                "container",
                "container",
            ],
            verbs,
        )
        start = executor.calls[3]
        self.assertEqual(("start", "--attach", "--interactive"), start[0][1:4])
        self.assertEqual(CONTAINER_ID, start[0][4])
        self.assertEqual(b"", start[1])
        serialized = repr((executor.calls, result))
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn("ZHIPU_API_KEY", serialized)

    def test_start_failure_kills_and_removes_exact_generated_container(self) -> None:
        executor = RecordingExecutor(
            start_failure=CodexCodingPlanRuntimeError("docker-process-timeout")
        )
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "timeout"):
            host.probe()
        verbs = [call[0][1] for call in executor.calls]
        self.assertEqual(
            [
                "image",
                "create",
                "container",
                "start",
                "container",
                "kill",
                "rm",
                "container",
                "container",
            ],
            verbs,
        )
        created_name = executor.calls[1][0][3].removeprefix("--name=")
        self.assertEqual(created_name, executor.calls[2][0][-1])
        self.assertEqual(CONTAINER_ID, executor.calls[5][0][2])
        self.assertEqual(CONTAINER_ID, executor.calls[6][0][3])

    def test_create_timeout_still_kills_and_removes_generated_name(self) -> None:
        class CreateTimeoutExecutor(RecordingExecutor):
            def execute(
                self, command: tuple[str, ...], **kwargs: object
            ) -> DockerCommandResult:
                if command[1] == "create":
                    self.calls.append(
                        (
                            command,
                            kwargs["stdin"],
                            kwargs["timeout_seconds"],
                            kwargs["stdout_limit"],
                            kwargs["stderr_limit"],
                        )
                    )
                    self.container_name = command[3].removeprefix("--name=")
                    self.container_present = True
                    raise CodexCodingPlanRuntimeError("docker-process-timeout")
                return super().execute(command, **kwargs)

        executor = CreateTimeoutExecutor()
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "timeout"):
            host.probe()
        verbs = [call[0][1] for call in executor.calls]
        self.assertEqual(
            [
                "image",
                "create",
                "container",
                "kill",
                "rm",
                "container",
                "container",
            ],
            verbs,
        )
        generated_name = executor.calls[1][0][3].removeprefix("--name=")
        self.assertEqual(generated_name, executor.calls[2][0][-1])
        self.assertEqual(CONTAINER_ID, executor.calls[3][0][2])
        self.assertEqual(CONTAINER_ID, executor.calls[4][0][3])

    def test_live_gate_fails_before_reading_credential_mapping(self) -> None:
        executor = RecordingExecutor()
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        self.assertFalse(CODEX_CODING_PLAN_DOCKER_LIVE_READY)
        with self.assertRaisesRegex(
            CodexCodingPlanRuntimeError, "live-network-not-ready"
        ):
            host.run_live_from_environment(
                "prompt",
                credential_env="ZHIPU_API_KEY",
                environment=PoisonEnvironment(),
            )
        self.assertEqual([], executor.calls)

    def test_probe_rejects_incomplete_attestation_and_still_removes(self) -> None:
        class BadProbeExecutor(RecordingExecutor):
            def execute(
                self, command: tuple[str, ...], **kwargs: object
            ) -> DockerCommandResult:
                if command[1] == "start":
                    self.calls.append(
                        (
                            command,
                            kwargs["stdin"],
                            kwargs["timeout_seconds"],
                            kwargs["stdout_limit"],
                            kwargs["stderr_limit"],
                        )
                    )
                    document = json.loads(successful_probe())
                    document["network_interfaces"] = ["eth0", "lo"]
                    return DockerCommandResult(0, json.dumps(document).encode(), b"")
                return super().execute(command, **kwargs)

        executor = BadProbeExecutor()
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "attestation-failed"):
            host.probe()
        self.assertEqual(
            ["container", "container"],
            [executor.calls[-2][0][1], executor.calls[-1][0][1]],
        )

    def test_id_name_reconciliation_fails_closed_before_start(self) -> None:
        class MismatchExecutor(RecordingExecutor):
            def execute(
                self, command: tuple[str, ...], **kwargs: object
            ) -> DockerCommandResult:
                result = super().execute(command, **kwargs)
                if command[1] == "container" and self.container_present:
                    other_id = "c" * 64
                    return DockerCommandResult(
                        0,
                        f"{other_id}|/{self.container_name}\n".encode(),
                        b"",
                    )
                return result

        executor = MismatchExecutor()
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        with self.assertRaisesRegex(
            DockerCleanupUnverifiedError, "docker-cleanup-unverified"
        ) as captured:
            host.probe()
        self.assertIsInstance(
            captured.exception.primary_error, CodexCodingPlanRuntimeError
        )
        self.assertIn("reconcile", str(captured.exception.primary_error))
        self.assertNotIn("start", [call[0][1] for call in executor.calls])

    def test_primary_and_cleanup_failures_are_both_retained(self) -> None:
        executor = RecordingExecutor(
            start_failure=CodexCodingPlanRuntimeError("docker-process-timeout"),
            retain_after_rm=True,
        )
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        with self.assertRaisesRegex(
            DockerCleanupUnverifiedError, "docker-cleanup-unverified"
        ) as captured:
            host.probe()
        error = captured.exception
        self.assertEqual("docker-process-timeout", str(error.primary_error))
        self.assertEqual("docker-cleanup-unverified", str(error.cleanup_error))
        self.assertIs(error.cleanup_error, error.__cause__)

    def test_cleanup_success_requires_name_and_id_not_found(self) -> None:
        executor = RecordingExecutor()
        host = CodexCodingPlanDockerHost(
            docker_executable=self.docker,
            image_id=IMAGE_ID,
            executor=executor,
        )
        host.probe()
        final_targets = [executor.calls[-2][0][-1], executor.calls[-1][0][-1]]
        self.assertEqual([executor.container_name, CONTAINER_ID], final_targets)
        self.assertFalse(executor.container_present)

    def test_existing_parser_is_reused_without_identity_overclaim(self) -> None:
        payload = "\n".join(
            json.dumps(event)
            for event in (
                {"type": "thread.started", "thread_id": "thread-docker"},
                {"type": "turn.started"},
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": "bounded plan"},
                },
                {
                    "type": "turn.completed",
                    "usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 0,
                        "output_tokens": 5,
                    },
                },
            )
        )
        result = CodexCodingPlanDockerHost.parse_runtime_jsonl(payload)
        self.assertEqual("transport-completed", result.status)
        self.assertIsNone(result.actual_model)
        self.assertIsNone(result.actual_provider)


class BoundedDockerCommandExecutorTests(DockerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.windows = os.name == "nt"
        if self.windows:
            system_root = Path(os.environ.get("SYSTEMROOT", r"C:\Windows"))
            shutil.copy2(system_root / "System32" / "cmd.exe", self.docker)
        else:
            # The production boundary intentionally requires an absolute file
            # named docker.exe.  A self-contained POSIX stub avoids depending
            # on whether the active Python executable is relocatable.
            self.docker.write_text(
                "#!/bin/sh\n"
                'case "$1" in\n'
                "  ok) printf 'ok\\n' ;;\n"
                "  overflow) printf 'xxxxx\\n' ;;\n"
                "  timeout) while :; do :; done ;;\n"
                "  no-read) exit 0 ;;\n"
                "  *) exit 2 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            self.docker.chmod(0o700)
        self.executor = BoundedDockerCommandExecutor(environment={})

    def test_output_is_captured_with_a_hard_incremental_limit(self) -> None:
        ok_command = (
            (str(self.docker), "/d", "/c", "echo ok")
            if self.windows
            else (str(self.docker), "ok")
        )
        result = self.executor.execute(
            ok_command,
            stdin=b"",
            timeout_seconds=5.0,
            stdout_limit=4,
            stderr_limit=64,
        )
        self.assertEqual(0, result.returncode)
        self.assertEqual(b"ok\n", result.stdout.replace(b"\r\n", b"\n"))
        overflow_command = (
            (str(self.docker), "/d", "/c", "echo xxxxx")
            if self.windows
            else (str(self.docker), "overflow")
        )
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "stdout-limit"):
            self.executor.execute(
                overflow_command,
                stdin=b"",
                timeout_seconds=5.0,
                stdout_limit=4,
                stderr_limit=64,
            )

    def test_timeout_terminates_the_child(self) -> None:
        timeout_command = (
            (
                str(self.docker),
                "/d",
                "/c",
                "for /L %i in (1,1,100000000) do @rem",
            )
            if self.windows
            else (str(self.docker), "timeout")
        )
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "timeout"):
            self.executor.execute(
                timeout_command,
                stdin=b"",
                timeout_seconds=0.1,
                stdout_limit=64,
                stderr_limit=64,
            )

    def test_writer_terminates_when_child_exits_without_reading_stdin(self) -> None:
        no_read_command = (
            (str(self.docker), "/d", "/c", "exit /b 0")
            if self.windows
            else (str(self.docker), "no-read")
        )
        result = self.executor.execute(
            no_read_command,
            stdin=b"x" * 65_536,
            timeout_seconds=5.0,
            stdout_limit=64,
            stderr_limit=64,
        )
        self.assertEqual(0, result.returncode)


class CodexCodingPlanDockerAssetTests(unittest.TestCase):
    def test_image_and_npm_inputs_are_exactly_pinned(self) -> None:
        root = Path(__file__).resolve().parents[1] / "docker" / "codex-coding-plan"
        dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
        lock = json.loads((root / "package-lock.json").read_text(encoding="utf-8"))
        entrypoint = (root / "entrypoint.mjs").read_text(encoding="utf-8")
        manifest_path = root / "asset-manifest.sha256"
        manifest = manifest_path.read_text(encoding="utf-8").splitlines()
        self.assertIn(f"FROM {CODEX_CODING_PLAN_DOCKER_BASE_IMAGE}", dockerfile)
        package = lock["packages"]["node_modules/@openai/codex"]
        self.assertEqual(CODEX_CODING_PLAN_DOCKER_CLI_VERSION, package["version"])
        self.assertEqual(CODEX_CODING_PLAN_DOCKER_NPM_INTEGRITY, package["integrity"])
        self.assertIn("RWB_CODEX_CODING_PLAN_CREDENTIAL: frame.credential", entrypoint)
        self.assertNotIn("--env=RWB_CODEX_CODING_PLAN_CREDENTIAL", entrypoint)
        self.assertIn('const expected = "http://rwb-egress-proxy:3128"', entrypoint)
        self.assertIn("...approvedProxyEnvironment()", entrypoint)
        self.assertIn("proxy-environment-not-approved", entrypoint)
        self.assertIn("core_dump_limit_zero: coreDumpLimitZero", entrypoint)
        self.assertIn("for (const original of chunks) original.fill(0)", entrypoint)

        expected_assets = {
            "Dockerfile",
            "package.json",
            "package-lock.json",
            "entrypoint.mjs",
            "models.json",
        }
        observed_assets: set[str] = set()
        for record in manifest:
            digest, filename = record.split("  ", 1)
            self.assertEqual(64, len(digest))
            self.assertTrue(
                all(character in "0123456789abcdef" for character in digest)
            )
            observed_assets.add(filename)
            actual = hashlib.sha256((root / filename).read_bytes()).hexdigest()
            self.assertEqual(actual, digest)
        self.assertEqual(expected_assets, observed_assets)

        manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        self.assertEqual(64, len(manifest_digest))
        self.assertIn("ARG RWB_ASSET_MANIFEST_SHA256", dockerfile)
        self.assertIn(
            'io.research-workbench.asset-manifest.sha256="${RWB_ASSET_MANIFEST_SHA256}"',
            dockerfile,
        )
        self.assertIn(
            'io.research-workbench.live-policy="external-allowlisted-image-digest-required"',
            dockerfile,
        )
        self.assertNotIn("final-image-id", dockerfile)


if __name__ == "__main__":
    unittest.main()
