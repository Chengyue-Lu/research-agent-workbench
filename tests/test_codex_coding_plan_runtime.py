import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from research_workbench.adapters.codex_coding_plan import (
    CODEX_CODING_PLAN_ATTESTATION_LIMITATIONS,
    CODEX_CODING_PLAN_BASE_URL,
    CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV,
    CODEX_CODING_PLAN_DISABLED_FEATURES,
    CODEX_CODING_PLAN_LIVE_READY,
    CODEX_CODING_PLAN_MODEL,
    CODEX_CODING_PLAN_MODEL_CATALOG,
    CODEX_CODING_PLAN_PROVIDER_ID,
    CodexCodingPlanLimits,
    CodexCodingPlanProcessResult,
    CodexCodingPlanRuntimeError,
    CodexCodingPlanRuntimeRunner,
    build_codex_coding_plan_command,
    parse_codex_coding_plan_jsonl,
)

CREDENTIAL_ENV = "RWB_CODEX_CODING_PLAN_KEY"
SECRET = "test-secret-that-must-never-be-persisted"


def write_model_catalog(root: Path) -> Path:
    path = root / "models.json"
    path.write_text(
        json.dumps(CODEX_CODING_PLAN_MODEL_CATALOG),
        encoding="utf-8",
    )
    return path


def write_fake_codex(root: Path) -> Path:
    name = "codex.exe" if os.name == "nt" else "codex"
    path = root / name
    path.write_bytes(b"offline test executable placeholder")
    return path


def success_jsonl(*, input_tokens: int = 40, output_tokens: int = 12) -> str:
    events = [
        {"type": "thread.started", "thread_id": "thread-test-001"},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {
                "id": "item-001",
                "type": "agent_message",
                "text": "A bounded coding plan.",
            },
        },
        {
            "type": "turn.completed",
            "usage": {
                "input_tokens": input_tokens,
                "cached_input_tokens": 10,
                "output_tokens": output_tokens,
                "reasoning_output_tokens": 2,
            },
        },
    ]
    return "\n".join(json.dumps(event) for event in events) + "\n"


class RecordingProcessRunner:
    def __init__(self, result: CodexCodingPlanProcessResult) -> None:
        self.result = result
        self.command: tuple[str, ...] | None = None
        self.cwd: Path | None = None
        self.environment_names: tuple[str, ...] = ()
        self.credential_present = False
        self.codex_home: Path | None = None
        self.codex_home_exists_during_call = False
        self.codex_home_files: tuple[str, ...] = ()
        self.model_catalog: object = None
        self.model_catalog_text = ""
        self.stdin: str | None = None
        self.timeout_seconds: float | None = None

    def __call__(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        env: dict[str, str],
        stdin: str,
        timeout_seconds: float,
    ) -> CodexCodingPlanProcessResult:
        self.command = command
        self.cwd = cwd
        self.environment_names = tuple(sorted(env))
        self.credential_present = (
            env.get(CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV) == SECRET
        )
        codex_home = env.get("CODEX_HOME")
        if isinstance(codex_home, str):
            self.codex_home = Path(codex_home)
            self.codex_home_exists_during_call = self.codex_home.is_dir()
            if self.codex_home_exists_during_call:
                self.codex_home_files = tuple(
                    sorted(path.name for path in self.codex_home.iterdir())
                )
                catalog = self.codex_home / "models.json"
                self.model_catalog_text = catalog.read_text(encoding="utf-8")
                self.model_catalog = json.loads(self.model_catalog_text)
        self.stdin = stdin
        self.timeout_seconds = timeout_seconds
        return self.result


class CodexCodingPlanCommandTests(unittest.TestCase):
    def test_command_freezes_provider_model_permissions_and_retries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            codex_home = root / "codex-home"
            binary_home = root / "binary"
            workspace.mkdir()
            codex_home.mkdir()
            binary_home.mkdir()
            catalog = write_model_catalog(codex_home)
            executable = write_fake_codex(binary_home)
            command = build_codex_coding_plan_command(
                isolated_workspace=workspace,
                model_catalog_json=catalog,
                codex_executable=executable,
            )

        self.assertEqual((str(executable), "exec"), command[:2])
        for flag in (
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--json",
            "--sandbox",
            "read-only",
            "--skip-git-repo-check",
        ):
            self.assertIn(flag, command)
        self.assertEqual("-", command[-1])
        self.assertEqual(CODEX_CODING_PLAN_MODEL, command[command.index("--model") + 1])

        overrides = {
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--config"
        }
        provider = f"model_providers.{CODEX_CODING_PLAN_PROVIDER_ID}"
        expected = {
            f'model_provider="{CODEX_CODING_PLAN_PROVIDER_ID}"',
            'model_reasoning_effort="low"',
            f'model_catalog_json="{catalog.as_posix()}"',
            'approval_policy="never"',
            'history.persistence="none"',
            "analytics.enabled=false",
            "feedback.enabled=false",
            'otel.exporter="none"',
            'otel.metrics_exporter="none"',
            'otel.trace_exporter="none"',
            "otel.log_user_prompt=false",
            'web_search="disabled"',
            "tools.web_search=false",
            f'{provider}.base_url="{CODEX_CODING_PLAN_BASE_URL}"',
            f'{provider}.env_key="{CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV}"',
            f'{provider}.wire_api="responses"',
            f"{provider}.request_max_retries=0",
            f"{provider}.stream_max_retries=0",
            f"{provider}.stream_idle_timeout_ms=30000",
        }
        self.assertTrue(expected.issubset(overrides), expected - overrides)
        self.assertNotIn("agents.enabled=false", overrides)

        disabled = [
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--disable"
        ]
        self.assertEqual(list(CODEX_CODING_PLAN_DISABLED_FEATURES), disabled)
        model = CODEX_CODING_PLAN_MODEL_CATALOG["models"][0]
        self.assertNotIn("apply_patch_tool_type", model)
        self.assertFalse(model["supports_parallel_tool_calls"])

    def test_command_contains_environment_name_but_never_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            codex_home = root / "codex-home"
            binary_home = root / "binary"
            workspace.mkdir()
            codex_home.mkdir()
            binary_home.mkdir()
            catalog = write_model_catalog(codex_home)
            executable = write_fake_codex(binary_home)
            command = build_codex_coding_plan_command(
                isolated_workspace=workspace,
                model_catalog_json=catalog,
                codex_executable=executable,
            )
        rendered = " ".join(command)
        self.assertIn(CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV, rendered)
        self.assertNotIn(CREDENTIAL_ENV, rendered)
        self.assertNotIn(SECRET, rendered)

    def test_workspace_and_executable_are_explicitly_restricted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            codex_home = root / "codex-home"
            binary_home = root / "binary"
            workspace.mkdir()
            codex_home.mkdir()
            binary_home.mkdir()
            catalog = write_model_catalog(codex_home)
            executable = write_fake_codex(binary_home)
            with self.assertRaisesRegex(ValueError, "absolute path"):
                build_codex_coding_plan_command(
                    isolated_workspace=Path("relative-workspace"),
                    model_catalog_json=catalog,
                    codex_executable=executable,
                )
            (workspace / "unexpected.txt").write_text("not empty", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be empty"):
                build_codex_coding_plan_command(
                    isolated_workspace=workspace,
                    model_catalog_json=catalog,
                    codex_executable=executable,
                )
            (root / "empty-workspace").mkdir()
            with self.assertRaisesRegex(ValueError, "absolute native"):
                build_codex_coding_plan_command(
                    isolated_workspace=(root / "empty-workspace"),
                    model_catalog_json=catalog,
                    codex_executable="codex",
                )

    def test_command_rejects_a_nonofficial_model_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "workspace"
            codex_home = root / "codex-home"
            binary_home = root / "binary"
            workspace.mkdir()
            codex_home.mkdir()
            binary_home.mkdir()
            catalog = codex_home / "models.json"
            catalog.write_text('{"models": []}', encoding="utf-8")
            executable = write_fake_codex(binary_home)
            with self.assertRaisesRegex(ValueError, "fixed GLM-5.3 catalog"):
                build_codex_coding_plan_command(
                    isolated_workspace=workspace,
                    model_catalog_json=catalog,
                    codex_executable=executable,
                )


class CodexCodingPlanParserTests(unittest.TestCase):
    def test_success_protocol_is_strict_and_usage_is_bounded(self) -> None:
        result = parse_codex_coding_plan_jsonl(success_jsonl())
        self.assertEqual("transport-completed", result.status)
        self.assertEqual("turn.completed", result.terminal_event)
        self.assertEqual("thread-test-001", result.thread_id)
        self.assertEqual("A bounded coding plan.", result.final_message)
        self.assertIsNotNone(result.usage)
        assert result.usage is not None
        self.assertEqual(52, result.usage.total_tokens)
        self.assertEqual(4, result.event_count)
        self.assertTrue(result.capture_complete)
        self.assertFalse(result.live_ready)
        self.assertFalse(CODEX_CODING_PLAN_LIVE_READY)

    def test_error_then_turn_failed_is_one_failure_outcome(self) -> None:
        events = [
            {"type": "thread.started", "thread_id": "thread-failed"},
            {"type": "turn.started"},
            {"type": "error", "message": "provider unavailable"},
            {"type": "turn.failed", "error": {"message": "provider unavailable"}},
        ]
        result = parse_codex_coding_plan_jsonl(
            "\n".join(json.dumps(event) for event in events)
        )
        self.assertEqual("runtime-failed", result.status)
        self.assertEqual("turn.failed", result.terminal_event)
        self.assertEqual("codex-error", result.failure_code)
        self.assertIsNone(result.usage)

    def test_codex_0124_item_error_precursor_is_safely_absorbed(self) -> None:
        events = [
            {"type": "thread.started", "thread_id": "thread-failed"},
            {
                "type": "item.completed",
                "item": {"id": "item-error", "type": "error", "message": "redacted"},
            },
            {"type": "turn.started"},
            {"type": "error", "message": "redacted"},
            {"type": "turn.failed", "error": {"message": "redacted"}},
        ]
        result = parse_codex_coding_plan_jsonl(
            "\n".join(json.dumps(event) for event in events)
        )
        self.assertEqual("runtime-failed", result.status)
        self.assertEqual("turn.failed", result.terminal_event)
        self.assertEqual("codex-error", result.failure_code)
        self.assertNotIn("redacted", repr(result))

    def test_error_without_turn_failed_is_a_bounded_eof_failure(self) -> None:
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "capture-incomplete"):
            parse_codex_coding_plan_jsonl(
                json.dumps({"type": "error", "message": "startup failure"})
            )

    def test_malformed_unknown_and_duplicate_terminal_records_are_rejected(
        self,
    ) -> None:
        with (
            self.subTest("invalid JSON"),
            self.assertRaisesRegex(CodexCodingPlanRuntimeError, "invalid-record"),
        ):
            parse_codex_coding_plan_jsonl("not-json")
        with (
            self.subTest("unknown event"),
            self.assertRaisesRegex(CodexCodingPlanRuntimeError, "unsupported"),
        ):
            parse_codex_coding_plan_jsonl(
                json.dumps({"type": "thread.started", "thread_id": "thread"})
                + "\n"
                + json.dumps({"type": "turn.started"})
                + "\n"
                + json.dumps({"type": "mystery.event"})
            )
        with self.subTest("duplicate terminal"):
            payload = success_jsonl() + json.dumps(
                {"type": "turn.failed", "error": {"message": "late"}}
            )
            with self.assertRaisesRegex(
                CodexCodingPlanRuntimeError, "multiple-terminal"
            ):
                parse_codex_coding_plan_jsonl(payload)

    def test_usage_beyond_caller_limit_is_rejected(self) -> None:
        limits = CodexCodingPlanLimits(max_total_tokens=50, max_output_tokens=20)
        with self.assertRaisesRegex(CodexCodingPlanRuntimeError, "total-token-limit"):
            parse_codex_coding_plan_jsonl(
                success_jsonl(input_tokens=40, output_tokens=12),
                limits=limits,
            )


class CodexCodingPlanRuntimeRunnerTests(unittest.TestCase):
    def test_injected_runner_gets_stdin_and_minimal_environment_without_network(
        self,
    ) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=0, stdout=success_jsonl(), stderr=""
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        prompt = "Return a coding plan only."
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            result = runner.run(
                prompt,
                isolated_workspace=workspace,
                credential_env=CREDENTIAL_ENV,
                environment={
                    CREDENTIAL_ENV: SECRET,
                    "PATH": "safe-test-path",
                    "OPENAI_API_KEY": "must-not-be-inherited",
                    "ANOTHER_SECRET": "must-not-be-inherited",
                },
            )

        self.assertEqual("transport-completed", result.status)
        self.assertTrue(process_runner.credential_present)
        self.assertEqual(
            tuple(
                sorted(
                    (
                        "APPDATA",
                        "CODEX_HOME",
                        "HOME",
                        "LOCALAPPDATA",
                        "NO_COLOR",
                        "RUST_BACKTRACE",
                        "TEMP",
                        "TMP",
                        "USERPROFILE",
                        CODEX_CODING_PLAN_CHILD_CREDENTIAL_ENV,
                    )
                )
            ),
            process_runner.environment_names,
        )
        self.assertTrue(process_runner.codex_home_exists_during_call)
        self.assertEqual(
            ("appdata", "home", "localappdata", "models.json", "temp"),
            process_runner.codex_home_files,
        )
        self.assertEqual(CODEX_CODING_PLAN_MODEL_CATALOG, process_runner.model_catalog)
        self.assertNotIn(SECRET, process_runner.model_catalog_text)
        assert process_runner.codex_home is not None
        self.assertFalse(process_runner.codex_home.exists())
        self.assertEqual(prompt, process_runner.stdin)
        assert process_runner.command is not None
        self.assertNotIn(prompt, process_runner.command)
        self.assertNotIn(SECRET, " ".join(process_runner.command))
        self.assertNotIn(SECRET, repr(result))

    def test_prompt_byte_limit_stops_before_process_runner(self) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=0, stdout=success_jsonl(), stderr=""
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
            limits=CodexCodingPlanLimits(max_prompt_bytes=8),
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(CodexCodingPlanRuntimeError, "prompt-byte-limit"),
        ):
            runner.run(
                "nine-byte!",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={CREDENTIAL_ENV: SECRET},
            )
        self.assertIsNone(process_runner.command)

    def test_workspace_mutation_fails_closed(self) -> None:
        class MutatingProcessRunner(RecordingProcessRunner):
            def __call__(
                self,
                command: tuple[str, ...],
                *,
                cwd: Path,
                env: dict[str, str],
                stdin: str,
                timeout_seconds: float,
            ) -> CodexCodingPlanProcessResult:
                result = super().__call__(
                    command,
                    cwd=cwd,
                    env=env,
                    stdin=stdin,
                    timeout_seconds=timeout_seconds,
                )
                (cwd / "unexpected.txt").write_text("mutation", encoding="utf-8")
                return result

        process_runner = MutatingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=0,
                stdout=success_jsonl(),
                stderr="",
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(
                CodexCodingPlanRuntimeError, "isolated-workspace-mutated"
            ),
        ):
            runner.run(
                "Return a coding plan only.",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={CREDENTIAL_ENV: SECRET},
            )

    def test_reported_failure_is_returned_without_provider_error_text(self) -> None:
        events = [
            {"type": "thread.started", "thread_id": "thread-failed"},
            {"type": "turn.started"},
            {"type": "error", "message": "sensitive upstream detail"},
            {"type": "turn.failed", "error": {"message": "sensitive upstream detail"}},
        ]
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=1,
                stdout="\n".join(json.dumps(event) for event in events),
                stderr="",
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with tempfile.TemporaryDirectory() as directory:
            result = runner.run(
                "Return a coding plan only.",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={CREDENTIAL_ENV: SECRET},
            )
        self.assertEqual("runtime-failed", result.status)
        self.assertEqual("codex-error", result.failure_code)
        self.assertNotIn("sensitive upstream detail", repr(result))

    def test_nonempty_stderr_fails_closed_without_exposing_text(self) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=1,
                stdout="",
                stderr="unknown model fallback to something else",
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(CodexCodingPlanRuntimeError, "stderr-not-empty"),
        ):
            runner.run(
                "Return a coding plan only.",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={CREDENTIAL_ENV: SECRET},
            )

    def test_credential_echo_is_blocked_and_exception_does_not_leak_value(self) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=1,
                stdout=json.dumps({"type": "error", "message": SECRET}),
                stderr="",
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(CodexCodingPlanRuntimeError) as raised,
        ):
            runner.run(
                "Return a coding plan only.",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={CREDENTIAL_ENV: SECRET},
            )
        self.assertEqual("credential-exposure-detected", raised.exception.code)
        self.assertNotIn(SECRET, str(raised.exception))

    def test_actual_provider_and_model_remain_explicitly_unverified(self) -> None:
        result = parse_codex_coding_plan_jsonl(success_jsonl())
        self.assertEqual(CODEX_CODING_PLAN_MODEL, result.requested_model)
        self.assertIsNone(result.actual_model)
        self.assertIsNone(result.actual_provider)
        self.assertFalse(result.model_identity_verified)
        self.assertEqual(CODEX_CODING_PLAN_ATTESTATION_LIMITATIONS, result.limitations)
        self.assertTrue(
            any(
                "actual model identity is unknown" in item
                for item in result.limitations
            )
        )

    def test_missing_credential_stops_before_process_runner(self) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=0, stdout=success_jsonl(), stderr=""
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(
                CodexCodingPlanRuntimeError, "credential-environment-missing"
            ),
        ):
            runner.run(
                "Return a coding plan only.",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={},
            )
        self.assertIsNone(process_runner.command)

    def test_default_live_host_is_disabled_before_credential_lookup(self) -> None:
        runner = CodexCodingPlanRuntimeRunner(codex_executable=sys.executable)
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(
                CodexCodingPlanRuntimeError, "live-runtime-not-ready"
            ),
        ):
            runner.run(
                "Return a coding plan only.",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={},
            )

    def test_credential_source_and_casefold_collisions_are_rejected(self) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=0,
                stdout=success_jsonl(),
                stderr="",
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            with self.assertRaisesRegex(ValueError, "approved Coding Plan"):
                runner.run(
                    "Return a coding plan only.",
                    isolated_workspace=workspace,
                    credential_env="HTTPS_PROXY",
                    environment={"HTTPS_PROXY": SECRET},
                )
            with self.assertRaisesRegex(
                CodexCodingPlanRuntimeError, "environment-name-collision"
            ):
                runner.run(
                    "Return a coding plan only.",
                    isolated_workspace=workspace,
                    credential_env=CREDENTIAL_ENV,
                    environment={
                        CREDENTIAL_ENV: SECRET,
                        "Path": "one",
                        "PATH": "two",
                    },
                )
        self.assertIsNone(process_runner.command)

    def test_credential_in_prompt_is_blocked_before_process_runner(self) -> None:
        process_runner = RecordingProcessRunner(
            CodexCodingPlanProcessResult(
                returncode=0,
                stdout=success_jsonl(),
                stderr="",
            )
        )
        runner = CodexCodingPlanRuntimeRunner(
            codex_executable=sys.executable,
            process_runner=process_runner,
        )
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaisesRegex(
                CodexCodingPlanRuntimeError, "credential-present-in-prompt"
            ),
        ):
            runner.run(
                f"Never send this: {SECRET}",
                isolated_workspace=Path(directory),
                credential_env=CREDENTIAL_ENV,
                environment={CREDENTIAL_ENV: SECRET},
            )
        self.assertIsNone(process_runner.command)

    def test_exit_code_and_terminal_event_must_agree(self) -> None:
        failure_events = [
            {"type": "thread.started", "thread_id": "thread-failed"},
            {"type": "turn.started"},
            {"type": "error", "message": "redacted"},
            {"type": "turn.failed", "error": {"message": "redacted"}},
        ]
        cases = (
            CodexCodingPlanProcessResult(
                returncode=1,
                stdout=success_jsonl(),
                stderr="",
            ),
            CodexCodingPlanProcessResult(
                returncode=0,
                stdout="\n".join(json.dumps(event) for event in failure_events),
                stderr="",
            ),
        )
        for process_result in cases:
            with self.subTest(returncode=process_result.returncode):
                process_runner = RecordingProcessRunner(process_result)
                runner = CodexCodingPlanRuntimeRunner(
                    codex_executable=sys.executable,
                    process_runner=process_runner,
                )
                with (
                    tempfile.TemporaryDirectory() as directory,
                    self.assertRaisesRegex(
                        CodexCodingPlanRuntimeError,
                        "process-exit-status-mismatch",
                    ),
                ):
                    runner.run(
                        "Return a coding plan only.",
                        isolated_workspace=Path(directory),
                        credential_env=CREDENTIAL_ENV,
                        environment={CREDENTIAL_ENV: SECRET},
                    )


if __name__ == "__main__":
    unittest.main()
