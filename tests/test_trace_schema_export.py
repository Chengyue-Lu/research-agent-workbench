"""Issue #21 deliverable 1: the exported trace schema bundle is
baseline-bound and independently sufficient to machine-validate a
recorded trace without any workbench source beside the bundle itself.
"""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.cli import main
from research_workbench.observability.trace import (
    TRACE_BASELINE,
    AgentTraceRecorder,
    TRACE_EVENTS_FILENAME,
    TRACE_INDEX_FILENAME,
    TRACE_MESSAGES_DIRNAME,
)
from research_workbench.observability.trace_schema import (
    MANIFEST_FILENAME,
    TRACE_SCHEMA_DOCUMENTS,
    TRACE_SCHEMA_REFERENCES,
    export_trace_schema_bundle,
    load_trace_schema_bundle,
)
from research_workbench.validation.schemas import SchemaCatalog

# The four trace documents plus the shared definition file are pinned to
# the current baseline. Editing any of them without bumping TRACE_BASELINE
# (and updating this pin in the same change) fails here, which is exactly
# the "schema change ships with a version change" discipline.
PINNED_TRACE_SCHEMA_SHA256 = {
    "agent-trace-index": "9bfdadb0cff569ce5b0be460251b05969598c7588d3a98e96d6c5665d759bffd",
    "agent-trace-actors": "7d1be7494e41b9395e352f621632651145f546264c03eb8bac468d6808b1eb67",
    "agent-trace-event": "fa467caf815c1db866ec3eb925ff31411f9cd3b77469aa8caa51937f8d5f7b85",
    "agent-trace-envelope": "66cce3b83f994c4a58cdfa4f7ad9a8c736c1826ba43545267be7c9844b49357b",
    "common": "f3dc4b04587bde0835720180b2f28c832973e5d5167ec0c5cb6a2090d85a9ccb",
}


def _record_trace(attempt_dir: Path) -> None:
    recorder = AgentTraceRecorder(
        attempt_dir,
        task_id="T-TRACE-SCHEMA",
        task_revision=1,
        attempt_id="AT-TS-001",
        task_snapshot={"task_id": "T-TRACE-SCHEMA", "revision": 1},
        accountable_owner="Huang Yi",
        actor_id="runtime-AT-TS-001",
        runtime_identity="model-api",
        provider="synthetic",
        read_allowlist=("inputs/**",),
        write_scope=("outputs/**",),
        tool_allowlist=("read_file",),
    )
    recorder.record(
        "provider-request",
        {"request": {"model": "synthetic-model", "prompt": "bounded fixture request"}},
    )
    recorder.record(
        "provider-response",
        {"response": {"model": "synthetic-model", "finish_reason": "complete"}},
    )
    recorder.record(
        "tool-result",
        {
            "operation_id": "OP-0001",
            "tool_name": "read_file",
            "status": "succeeded",
            "result": {"path": "inputs/paper.txt", "content_sha256": "1" * 64},
            "result_entered_context": True,
        },
    )
    recorder.record_attempt_status("completed", reason="fixture execution completed")
    recorder.seal()


def _envelope(path: Path) -> dict:
    raw = path.read_bytes()
    header, _body = raw[4:].split(b"---\n", 1)
    envelope = yaml.safe_load(header.decode("utf-8"))
    assert isinstance(envelope, dict)
    return envelope


class BundleExportTests(unittest.TestCase):
    def test_manifest_pins_baseline_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            manifest_path = export_trace_schema_bundle(Path(raw) / "bundle")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual("rwb-trace-schema-bundle", manifest["bundle_kind"])
            self.assertEqual(TRACE_BASELINE, manifest["baseline"])
            self.assertEqual("0.1.0", manifest["schema_version"])
            governed = {entry["document"]: entry["governs"] for entry in manifest["documents"]}
            self.assertEqual(
                {document for document, _ in TRACE_SCHEMA_DOCUMENTS},
                set(governed),
            )
            for entry in (*manifest["documents"], *manifest["references"]):
                bundled = manifest_path.parent / entry["file"]
                self.assertTrue(bundled.is_file(), entry["file"])
                self.assertEqual(hash_file(bundled), entry["sha256"])
                self.assertEqual(
                    hash_file(SchemaCatalog().directory / entry["file"]),
                    entry["sha256"],
                    "bundled schema must be byte-identical to the repository schema",
                )
            self.assertEqual(
                {document for document in TRACE_SCHEMA_REFERENCES},
                {entry["document"] for entry in manifest["references"]},
            )

    def test_reexport_into_the_same_directory_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "bundle"
            export_trace_schema_bundle(target)
            with self.assertRaises(FileExistsError):
                export_trace_schema_bundle(target)

    def test_loader_rejects_a_drifted_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "bundle"
            manifest_path = export_trace_schema_bundle(target)
            drifted = target / "agent-trace-event.schema.json"
            drifted.write_text(
                drifted.read_text(encoding="utf-8").replace('"0.1.0"', '"0.1.0 "'),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_trace_schema_bundle(manifest_path)

    def test_loader_resolves_cross_document_references(self) -> None:
        # agent-trace-envelope constrains actor ids through
        # agent-trace-actors#/$defs/actorId; that reference must resolve
        # from the bundle alone. A behavioral probe: the recorded envelope
        # validates, and an actor id violating the referenced pattern fails.
        with tempfile.TemporaryDirectory() as raw:
            workspace = Path(raw)
            attempt_dir = workspace / "AT-TS-001"
            _record_trace(attempt_dir)
            bundle = load_trace_schema_bundle(export_trace_schema_bundle(workspace / "bundle"))
            path = sorted((attempt_dir / TRACE_MESSAGES_DIRNAME).glob("*.trace"))[0]
            envelope = _envelope(path)
            self.assertEqual([], bundle.validate("agent-trace-envelope", envelope))
            broken = {**envelope, "receiver_actor_ids": ["actor id with spaces"]}
            self.assertNotEqual([], bundle.validate("agent-trace-envelope", broken))


class ExportedSchemaValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._stack = contextlib.ExitStack()
        self.addCleanup(self._stack.close)
        workspace = Path(self._stack.enter_context(tempfile.TemporaryDirectory()))
        self.attempt_dir = workspace / "AT-TS-001"
        _record_trace(self.attempt_dir)
        self.manifest_path = export_trace_schema_bundle(workspace / "bundle")
        self.bundle = load_trace_schema_bundle(self.manifest_path)

    def test_exported_schemas_validate_every_recorded_artifact(self) -> None:
        index = yaml.safe_load((self.attempt_dir / TRACE_INDEX_FILENAME).read_text(encoding="utf-8"))
        self.assertEqual([], self.bundle.validate("agent-trace-index", index))
        actors = yaml.safe_load((self.attempt_dir / "ACTORS.yaml").read_text(encoding="utf-8"))
        self.assertEqual([], self.bundle.validate("agent-trace-actors", actors))
        for line in (self.attempt_dir / TRACE_EVENTS_FILENAME).read_text(encoding="utf-8").splitlines():
            self.assertEqual([], self.bundle.validate("agent-trace-event", json.loads(line)))
        message_paths = sorted((self.attempt_dir / TRACE_MESSAGES_DIRNAME).glob("*.trace"))
        self.assertEqual(2, len(message_paths))
        for path in message_paths:
            self.assertEqual([], self.bundle.validate("agent-trace-envelope", _envelope(path)))

    def test_tampered_event_is_rejected_by_the_exported_schema(self) -> None:
        lines = (self.attempt_dir / TRACE_EVENTS_FILENAME).read_text(encoding="utf-8").splitlines()
        event = json.loads(lines[0])
        event["event_type"] = "not-a-trace-event"
        self.assertNotEqual([], self.bundle.validate("agent-trace-event", event))
        broken_sequence = json.loads(lines[0])
        broken_sequence["sequence"] = "first"
        self.assertNotEqual([], self.bundle.validate("agent-trace-event", broken_sequence))


class BaselineBindingTests(unittest.TestCase):
    def test_trace_schemas_are_pinned_to_the_current_baseline(self) -> None:
        catalog = SchemaCatalog()
        for document, pinned in PINNED_TRACE_SCHEMA_SHA256.items():
            source = catalog.directory / f"{document}.schema.json"
            self.assertEqual(
                pinned,
                hash_file(source),
                f"{document} drifted from the pinned hash: bump TRACE_BASELINE "
                "and update PINNED_TRACE_SCHEMA_SHA256 in the same change",
            )
        self.assertEqual("rwb-agent-trace-v0.1", TRACE_BASELINE)


class TraceExportCliTests(unittest.TestCase):
    def test_cli_exports_the_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "bundle"
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = main(["trace", "export-schema", "--out", str(target)])
            self.assertEqual(0, code)
            self.assertIn(TRACE_BASELINE, captured.getvalue())
            manifest = target / MANIFEST_FILENAME
            self.assertTrue(manifest.is_file())
            bundle = load_trace_schema_bundle(manifest)
            self.assertEqual(TRACE_BASELINE, bundle.baseline)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(2, main(["trace", "export-schema", "--out", str(target)]))


if __name__ == "__main__":
    unittest.main()
