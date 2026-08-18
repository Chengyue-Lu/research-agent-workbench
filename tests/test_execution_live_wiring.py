"""Live-provider wiring tests for the K-API execution runner (M6-004).

All tests are offline: provider construction never touches the network
(credentials resolve lazily at the outbound boundary), so these prove the
factory plumbing only — never live behaviour.
"""

import io
import shutil
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from research_workbench.adapters.models import (
    AnthropicMessagesProvider,
    build_live_provider,
)
from research_workbench.cli import main as cli_main
from research_workbench.execution import CompileError, build_provider_registry
from research_workbench.io import load_document


ROOT = Path(__file__).resolve().parents[1]

TASK_PATH = "examples/task-evidence.yaml"
PROFILE_PATH = "registry/agents/evidence-scout.yaml"
ASSIGNMENT_PATH = "examples/vertical-slice/evidence-assignment.yaml"
PROTOCOL_PATH = "examples/project-protocol.yaml"
CHECKER_PATH = "src/research_workbench/execution/checks.py"

ADAPTER_CONFIG = """\
schema_version: "0.1.0"
registry_kind: provider_adapters
adapters:
  - adapter_id: glm-anthropic-messages
    provider: anthropic
    enabled: true
    base_url: https://open.bigmodel.cn/api/anthropic
    credential_env: ANTHROPIC_AUTH_TOKEN
    model_env: RWB_GLM_MODEL
    capabilities: [text, tools, structured_output]
    live_conformance: pending
  - adapter_id: disabled-adapter
    provider: anthropic
    enabled: false
    base_url: https://example.invalid/v1
    credential_env: ANTHROPIC_AUTH_TOKEN
    model_env: RWB_GLM_MODEL
    capabilities: [text, tools, structured_output]
    live_conformance: pending
"""

POOL_CONFIG = """\
schema_version: "0.1.0"
registry_kind: model_pool
pool_id: local-glm-pool
selection_policy: explicit-slot-only
slots:
  - slot_id: worker
    role: worker
    provider_adapter: glm-anthropic-messages
    model_env: RWB_GLM_MODEL
    enabled: true
    capabilities: [text, tools, structured_output]
"""


def run_cli(arguments: list[str]) -> tuple[int, str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        code = cli_main(arguments)
    return code, stream.getvalue()


class BuildLiveProviderTests(unittest.TestCase):
    def test_model_override_skips_environment_read(self) -> None:
        from research_workbench.adapters.models.configuration import ProviderAdapterConfig

        config = ProviderAdapterConfig(
            adapter_id="glm-anthropic-messages",
            provider="anthropic",
            enabled=True,
            base_url="https://open.bigmodel.cn/api/anthropic",
            credential_env="ANTHROPIC_AUTH_TOKEN",
            model_env="RWB_GLM_MODEL",
            capabilities=frozenset({"text", "tools", "structured_output"}),
            live_conformance="pending",
        )
        with mock.patch.dict("os.environ", {}, clear=True):
            provider = build_live_provider(config, model="glm-5.3")

        self.assertIsInstance(provider, AnthropicMessagesProvider)
        snapshot = provider.capabilities()
        self.assertEqual(("glm-5.3",), snapshot.models)
        self.assertIn("structured_output", snapshot.supported)

    def test_default_behaviour_still_reads_environment(self) -> None:
        from research_workbench.adapters.models.configuration import ProviderAdapterConfig

        config = ProviderAdapterConfig(
            adapter_id="glm-anthropic-messages",
            provider="anthropic",
            enabled=True,
            base_url="https://open.bigmodel.cn/api/anthropic",
            credential_env="ANTHROPIC_AUTH_TOKEN",
            model_env="RWB_GLM_MODEL",
            capabilities=frozenset({"text", "tools", "structured_output"}),
            live_conformance="pending",
        )
        with mock.patch.dict("os.environ", {"RWB_GLM_MODEL": "glm-5.3"}, clear=True):
            provider = build_live_provider(config)
        self.assertEqual(("glm-5.3",), provider.capabilities().models)


class BuildProviderRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config_path = self.root / "adapters.local.yaml"
        self.config_path.write_text(ADAPTER_CONFIG, encoding="utf-8")

    def tearDown(self) -> None:
        self.directory.cleanup()

    def test_registry_is_built_under_the_adapter_id(self) -> None:
        registry = build_provider_registry(
            "glm-anthropic-messages",
            config_path=self.config_path,
            model="glm-5.3",
        )
        provider = registry.get("glm-anthropic-messages")
        self.assertEqual(("glm-5.3",), provider.capabilities().models)

    def test_without_config_path_the_blocker_stays(self) -> None:
        with self.assertRaises(CompileError) as caught:
            build_provider_registry("glm-anthropic-messages")
        self.assertEqual("EXEC-PROVIDER-NOT-CONFIGURED", caught.exception.code)

    def test_unknown_adapter_is_a_clean_error(self) -> None:
        with self.assertRaises(CompileError) as caught:
            build_provider_registry(
                "absent-adapter", config_path=self.config_path, model="glm-5.3"
            )
        self.assertEqual("EXEC-ADAPTER-UNKNOWN", caught.exception.code)

    def test_disabled_adapter_is_rejected(self) -> None:
        with self.assertRaises(CompileError) as caught:
            build_provider_registry(
                "disabled-adapter", config_path=self.config_path, model="glm-5.3"
            )
        self.assertEqual("EXEC-ADAPTER-DISABLED", caught.exception.code)


class ExecuteTaskWiringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = TemporaryDirectory()
        self.root = Path(self.directory.name)
        shutil.copytree(
            ROOT / "examples" / "fixtures", self.root / "examples" / "fixtures"
        )
        shutil.copytree(
            ROOT / ".agents" / "skills" / "literature-evidence-extraction",
            self.root / ".agents" / "skills" / "literature-evidence-extraction",
            dirs_exist_ok=True,
        )
        for relative in (TASK_PATH, PROTOCOL_PATH, ASSIGNMENT_PATH, PROFILE_PATH):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, target)
        (self.root / ".rwb").mkdir(exist_ok=True)
        (self.root / ".rwb" / "adapters.local.yaml").write_text(ADAPTER_CONFIG, encoding="utf-8")
        (self.root / ".rwb" / "pool.local.yaml").write_text(POOL_CONFIG, encoding="utf-8")
        checker = self.root / CHECKER_PATH
        checker.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / CHECKER_PATH, checker)

    def tearDown(self) -> None:
        self.directory.cleanup()

    def arguments(self, *extra: str) -> list[str]:
        return [
            "execute", "task", TASK_PATH,
            "--profile", PROFILE_PATH,
            "--assignment", ASSIGNMENT_PATH,
            "--slot", "worker",
            "--pool", ".rwb/pool.local.yaml",
            "--protocol", PROTOCOL_PATH,
            "--root", str(self.root),
            "--from-environment",
            *extra,
        ]

    def test_provider_config_without_model_variable_blocks_cleanly(self) -> None:
        with mock.patch.dict(
            "os.environ", {"ANTHROPIC_AUTH_TOKEN": "synthetic"}, clear=True
        ):
            code, output = run_cli(self.arguments("--provider-config", ".rwb/adapters.local.yaml"))

        self.assertEqual(2, code, output)
        self.assertIn("RWB_GLM_MODEL", output)
        self.assertFalse((self.root / "work").exists())
        self.assertFalse((self.root / "checkpoints").exists())

    def test_missing_model_variable_is_reported_before_any_write(self) -> None:
        from research_workbench.execution import execute_task

        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(CompileError) as caught:
                execute_task(
                    root=self.root,
                    task_path=TASK_PATH,
                    profile_path=PROFILE_PATH,
                    assignment_path=ASSIGNMENT_PATH,
                    slot="worker",
                    pool_path=".rwb/pool.local.yaml",
                    environment={},
                    protocol_path=PROTOCOL_PATH,
                    provider_config_path=".rwb/adapters.local.yaml",
                )
        self.assertEqual("EXEC-SLOT-INVALID", caught.exception.code)
        self.assertFalse((self.root / "work").exists())

    def test_local_configs_in_repo_parse(self) -> None:
        # These are git-ignored live-testing configs that only exist on the
        # developer's machine; a fresh checkout (CI) must skip, not fail.
        for name in ("provider-adapters.local.yaml", "execution-pool.local.yaml"):
            path = ROOT / ".rwb" / name
            if not path.exists():
                self.skipTest(f"{name} is a local-only config (git-ignored)")
            document = load_document(path)
            self.assertTrue(document, name)


if __name__ == "__main__":
    unittest.main()
