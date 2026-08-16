from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path, PurePosixPath
from unittest import mock

import yaml

from research_workbench.artifacts.integrity import hash_file
from research_workbench.io import load_document
from research_workbench.observability import trace_recorder
from research_workbench.observability.trace_recorder import (
    ApiTraceMetadata,
    BoundaryCallStatus,
    CaptureGapKind,
    FrozenReadMetadata,
    FrozenTraceReference,
    TraceActorMetadata,
    TraceCaptureGap,
    TraceRecorderError,
    TraceTimeline,
    begin_api_trace,
    build_api_trace_bundle,
)
from research_workbench.validation.documents import Severity
from research_workbench.validation.trace import validate_agent_trace


class ApiTraceRecorderTests(unittest.TestCase):
    @staticmethod
    def _project(directory: str) -> Path:
        project = Path(directory) / "project"
        task_path = project / "tasks/TASK.yaml"
        task_path.parent.mkdir(parents=True)
        task_path.write_text(
            yaml.safe_dump(
                {
                    "task_id": "API-001",
                    "revision": 1,
                    "goal": "PROMPT-BODY-SENTINEL",
                    "source_excerpt": "SOURCE-BODY-SENTINEL",
                    "tool_arguments": "TOOL-ARGUMENT-SENTINEL",
                    "tool_result": "TOOL-RESULT-SENTINEL",
                    "provider_response_id": "RESPONSE-ID-SENTINEL",
                    "exception_text": "EXCEPTION-TEXT-SENTINEL",
                    "reasoning": "REASONING-SENTINEL",
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return project

    @staticmethod
    def _metadata(**changes: object) -> ApiTraceMetadata:
        metadata = ApiTraceMetadata(
            trace_id="TRACE-API-001-A-001",
            task_id="API-001",
            task_revision=1,
            attempt_id="A-001",
            baseline="0123456789abcdef",
            task_path="tasks/TASK.yaml",
            archive_root="archive/API-001/A-001",
            owner_actor_id="main-agent",
            coordinator_actor_id="main-agent",
            worker_actor_id="api-worker",
            actors=(
                TraceActorMetadata(
                    actor_id="main-agent",
                    actor_type="agent",
                    role="coordinator",
                    runtime_identity="fixture-main@0.1.0",
                    accountable_owner="路诚钺",
                ),
                TraceActorMetadata(
                    actor_id="api-worker",
                    actor_type="agent",
                    role="worker",
                    runtime_identity="fixture-api@0.1.0",
                    accountable_owner="黄毅",
                ),
            ),
            read_allowlist=("tasks/TASK.yaml",),
            write_scope=("archive/**",),
            tool_allowlist=("read_file",),
        )
        return replace(metadata, **changes)

    @staticmethod
    def _timeline(**changes: str) -> TraceTimeline:
        timeline = TraceTimeline(
            started_at="2026-08-16T00:00:00Z",
            assignment_at="2026-08-16T00:00:05Z",
            handoff_at="2026-08-16T00:00:30Z",
            finished_at="2026-08-16T00:00:35Z",
        )
        return replace(timeline, **changes)

    @staticmethod
    def _frozen_ref(path: str, payload: bytes) -> FrozenTraceReference:
        return FrozenTraceReference(path, hashlib.sha256(payload).hexdigest(), payload)

    @staticmethod
    def _events(index_path: Path) -> list[dict]:
        index = load_document(index_path)
        project_root = index_path.parents[3]
        ledger_path = project_root / index["event_ledger"]["path"]
        return [
            json.loads(line)
            for line in ledger_path.read_text(encoding="utf-8").splitlines()
        ]

    @staticmethod
    def _archive_bytes(archive: Path) -> dict[str, bytes]:
        return {
            path.relative_to(archive).as_posix(): path.read_bytes()
            for path in sorted(archive.rglob("*"))
            if path.is_file()
        }

    @classmethod
    def _begin(
        cls,
        project: Path,
        metadata: ApiTraceMetadata | None = None,
    ) -> trace_recorder.ApiTraceRecorder:
        timeline = cls._timeline()
        return begin_api_trace(
            project,
            metadata or cls._metadata(),
            started_at=timeline.started_at,
            assignment_at=timeline.assignment_at,
        )

    @classmethod
    def _finalize(
        cls,
        recorder: trace_recorder.ApiTraceRecorder,
        *,
        attempt_status: str = "completed",
        capture_gaps: tuple[TraceCaptureGap, ...] = (),
        timeline: TraceTimeline | None = None,
        observe_provider: bool = True,
    ) -> trace_recorder.TraceBundleResult:
        selected = timeline or cls._timeline()
        if observe_provider:
            call_number = recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:10Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            recorder.record_provider_call_finished(
                call_number,
                occurred_at="2026-08-16T00:00:12Z",
                status=BoundaryCallStatus.SUCCEEDED,
            )
        return recorder.finalize(
            attempt_status=attempt_status,
            handoff_at=selected.handoff_at,
            finished_at=selected.finished_at,
            capture_gaps=capture_gaps,
        )

    def test_policy_gapped_bundle_is_validator_compatible_and_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)
            archive = project / self._metadata().archive_root
            self.assertTrue(
                (
                    archive / "messages/0001-main-agent-to-api-worker-assignment.md"
                ).is_file()
            )
            self.assertFalse(
                (archive / "messages/0002-api-worker-to-main-agent-handoff.md").exists()
            )
            self.assertFalse((archive / "INDEX.yaml").exists())
            result = self._finalize(recorder)

            self.assertEqual(
                [
                    issue.code
                    for issue in validate_agent_trace(result.index_path, root=project)
                ],
                ["TRACE-CAPTURE-GAP"],
            )
            self.assertEqual(result.completeness, "gapped")
            self.assertEqual(result.message_count, 2)
            self.assertEqual(result.event_count, 11)
            self.assertEqual(result.index_sha256, hash_file(result.index_path))

            index = load_document(result.index_path)
            events = self._events(result.index_path)
            self.assertEqual(
                [event["sequence"] for event in events],
                list(range(1, len(events) + 1)),
            )
            self.assertEqual(
                [event["event_id"] for event in events],
                [f"EVT-{sequence:04d}" for sequence in range(1, len(events) + 1)],
            )
            self.assertEqual(
                [
                    event["payload"]["action"]
                    for event in events
                    if event["event_type"] == "message-capture"
                ],
                ["persisted-before-send", "persisted-before-use"],
            )
            self.assertEqual(
                [message["message_id"] for message in index["messages"]],
                ["MSG-0001", "MSG-0002"],
            )
            self.assertEqual(
                [message["capture_status"] for message in index["messages"]],
                ["partial", "partial"],
            )
            self.assertEqual(
                [message["capture_gap_event_id"] for message in index["messages"]],
                ["EVT-0001", "EVT-0001"],
            )
            for message in index["messages"]:
                self.assertEqual(
                    hash_file(project / message["path"]),
                    message["sha256"],
                )
            self.assertEqual(
                hash_file(project / index["event_ledger"]["path"]),
                index["event_ledger"]["sha256"],
            )

    def test_declared_gaps_are_sorted_contiguous_and_validate_as_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)
            result = self._finalize(
                recorder,
                capture_gaps=(
                    TraceCaptureGap(
                        CaptureGapKind.TOOL_CONTENT,
                        "2026-08-16T00:00:20Z",
                    ),
                    TraceCaptureGap(
                        CaptureGapKind.RUNTIME_EXPORT,
                        "2026-08-16T00:00:10Z",
                    ),
                ),
            )

            issues = validate_agent_trace(result.index_path, root=project)
            self.assertFalse(
                [issue for issue in issues if issue.severity == Severity.ERROR]
            )
            self.assertEqual(
                [(issue.code, issue.severity) for issue in issues],
                [("TRACE-CAPTURE-GAP", Severity.WARNING)],
            )
            self.assertEqual(result.completeness, "gapped")

            events = self._events(result.index_path)
            self.assertEqual(
                [event["sequence"] for event in events],
                list(range(1, len(events) + 1)),
            )
            gaps = [event for event in events if event["event_type"] == "capture-gap"]
            self.assertEqual(
                [gap["occurred_at"] for gap in gaps],
                [
                    "2026-08-16T00:00:05Z",
                    "2026-08-16T00:00:10Z",
                    "2026-08-16T00:00:20Z",
                ],
            )
            self.assertEqual(
                [gap["payload"]["reason_category"] for gap in gaps],
                ["policy-omission", "platform-unavailable", "policy-omission"],
            )

    def test_runtime_boundaries_are_persisted_sanitized_and_indexed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)
            provider_number = recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:08Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            recorder.record_provider_call_finished(
                provider_number,
                occurred_at="2026-08-16T00:00:12Z",
                status=BoundaryCallStatus.SUCCEEDED,
            )
            tool_number = recorder.record_tool_call_started(
                occurred_at="2026-08-16T00:00:15Z",
                tool_name="read_file",
            )
            recorder.record_tool_call_finished(
                tool_number,
                occurred_at="2026-08-16T00:00:18Z",
                status=BoundaryCallStatus.SUCCEEDED,
                result_char_count=97,
                frozen_read=FrozenReadMetadata(
                    path="tasks/TASK.yaml",
                    sha256=hash_file(project / "tasks/TASK.yaml"),
                ),
            )

            runtime_path = project / self._metadata().archive_root / "tool-events"
            records = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(runtime_path.glob("*.json"))
            ]
            self.assertEqual(
                [record["boundary_sequence"] for record in records],
                [1, 2, 3, 4],
            )
            self.assertEqual(
                [record["boundary_type"] for record in records],
                [
                    "provider-call-started",
                    "provider-call-finished",
                    "tool-call-started",
                    "tool-call-finished",
                ],
            )
            self.assertEqual(records[-1]["result_char_count"], 97)
            self.assertEqual(
                records[-1]["frozen_read"],
                {
                    "path": "tasks/TASK.yaml",
                    "sha256": hash_file(project / "tasks/TASK.yaml"),
                },
            )
            self.assertFalse((runtime_path.parent / "INDEX.yaml").exists())

            result = self._finalize(recorder, observe_provider=False)
            self.assertEqual(
                [
                    issue.code
                    for issue in validate_agent_trace(result.index_path, root=project)
                ],
                ["TRACE-CAPTURE-GAP"],
            )
            index = load_document(result.index_path)
            self.assertEqual(len(index["tool_event_refs"]), 4)
            self.assertEqual(
                index["tool_allowlist"],
                [{"tool_name": "read_file", "authorized_by": "TASK"}],
            )
            events = self._events(result.index_path)
            self.assertEqual(
                len(
                    [event for event in events if event["event_type"] == "content-read"]
                ),
                1,
            )

            prohibited_keys = {
                "prompt",
                "request_body",
                "response_body",
                "response_id",
                "arguments",
                "result_body",
                "call_id",
                "credentials",
                "exception",
                "reasoning",
            }
            self.assertTrue(
                prohibited_keys.isdisjoint(
                    {key for record in records for key in record}
                )
            )

    def test_seal_freezes_trace_only_payloads_and_hash_bound_closeout_refs(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            recorder = self._begin(project, metadata)
            provider_number = recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:10Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            recorder.record_provider_call_finished(
                provider_number,
                occurred_at="2026-08-16T00:00:12Z",
                status=BoundaryCallStatus.SUCCEEDED,
            )
            references = {
                "handoff_refs": (
                    self._frozen_ref(
                        f"{metadata.archive_root}/HANDOFF.yaml",
                        b"kind: handoff\nprivate: HANDOFF-PAYLOAD-SENTINEL\n",
                    ),
                ),
                "decision_refs": (
                    self._frozen_ref(
                        f"{metadata.archive_root}/decisions/selection.yaml",
                        b"kind: decision\nprivate: DECISION-PAYLOAD-SENTINEL\n",
                    ),
                ),
                "output_refs": (
                    self._frozen_ref(
                        f"{metadata.archive_root}/objects/z-result.yaml",
                        b"kind: output\nprivate: OUTPUT-Z-PAYLOAD-SENTINEL\n",
                    ),
                    self._frozen_ref(
                        f"{metadata.archive_root}/objects/a-result.yaml",
                        b"kind: output\nprivate: OUTPUT-A-PAYLOAD-SENTINEL\n",
                    ),
                ),
                "check_refs": (
                    self._frozen_ref(
                        f"{metadata.archive_root}/checks/report.yaml",
                        b"kind: check\nprivate: CHECK-PAYLOAD-SENTINEL\n",
                    ),
                ),
            }

            bundle = recorder.seal(
                attempt_status="completed",
                handoff_at=self._timeline().handoff_at,
                finished_at=self._timeline().finished_at,
                **references,
            )
            self.assertIs(
                bundle,
                recorder.seal(
                    attempt_status="completed",
                    handoff_at=self._timeline().handoff_at,
                    finished_at=self._timeline().finished_at,
                    **{
                        **references,
                        "output_refs": tuple(reversed(references["output_refs"])),
                    },
                ),
            )

            archive = project / metadata.archive_root
            self.assertFalse(
                (archive / "messages/0002-api-worker-to-main-agent-handoff.md").exists()
            )
            self.assertFalse((archive / "events.jsonl").exists())
            self.assertFalse((archive / "INDEX.yaml").exists())
            self.assertEqual(tuple(bundle.payloads)[-1], bundle.index_path)
            self.assertEqual(bundle.index_ref.path, bundle.index_path)
            self.assertEqual(
                hashlib.sha256(bundle.payloads[bundle.index_path]).hexdigest(),
                bundle.index_sha256,
            )

            closeout_paths = {
                reference.path for group in references.values() for reference in group
            }
            self.assertTrue(closeout_paths.isdisjoint(bundle.payloads))
            trace_bytes = b"\n".join(bundle.payloads.values())
            for sentinel in (
                b"HANDOFF-PAYLOAD-SENTINEL",
                b"DECISION-PAYLOAD-SENTINEL",
                b"OUTPUT-Z-PAYLOAD-SENTINEL",
                b"OUTPUT-A-PAYLOAD-SENTINEL",
                b"CHECK-PAYLOAD-SENTINEL",
            ):
                self.assertNotIn(sentinel, trace_bytes)
            with self.assertRaises(TypeError):
                bundle.payloads["unexpected"] = b"mutable"  # type: ignore[index]

            index = yaml.safe_load(bundle.payloads[bundle.index_path])
            for field_name, field_references in references.items():
                self.assertEqual(
                    index[field_name],
                    [
                        {
                            "path": reference.path,
                            "sha256": reference.sha256,
                        }
                        for reference in sorted(
                            field_references,
                            key=lambda item: item.path,
                        )
                    ],
                )
            event_path = index["event_ledger"]["path"]
            events = [
                json.loads(line)
                for line in bundle.payloads[event_path].decode("utf-8").splitlines()
            ]
            revisions = {
                event["payload"]["path"]: event
                for event in events
                if event["event_type"] == "file-revision"
            }
            for group in references.values():
                for reference in group:
                    self.assertEqual(
                        revisions[reference.path]["payload"],
                        {
                            "path": reference.path,
                            "action": "created",
                            "new_sha256": reference.sha256,
                            "new_revision": 1,
                        },
                    )
                    self.assertEqual(
                        metadata.coordinator_actor_id,
                        revisions[reference.path]["actor_id"],
                    )

            for group in references.values():
                for reference in group:
                    destination = project.joinpath(*PurePosixPath(reference.path).parts)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(reference.payload)
            for relative, payload in bundle.payloads.items():
                destination = project.joinpath(*PurePosixPath(relative).parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(payload)
            self.assertEqual(
                [
                    issue.code
                    for issue in validate_agent_trace(
                        project.joinpath(*PurePosixPath(bundle.index_path).parts),
                        root=project,
                    )
                ],
                ["TRACE-CAPTURE-GAP"],
            )

    def test_finalize_reuses_sealed_bundle_with_closeout_refs_idempotently(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            recorder = self._begin(project, metadata)
            provider_number = recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:10Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            recorder.record_provider_call_finished(
                provider_number,
                occurred_at="2026-08-16T00:00:12Z",
                status=BoundaryCallStatus.SUCCEEDED,
            )
            output_ref = self._frozen_ref(
                f"{metadata.archive_root}/objects/result.yaml",
                b"kind: output\n",
            )
            terminal = {
                "attempt_status": "completed",
                "handoff_at": self._timeline().handoff_at,
                "finished_at": self._timeline().finished_at,
                "output_refs": (output_ref,),
            }
            sealed = recorder.seal(**terminal)
            with self.assertRaisesRegex(TraceRecorderError, "is not published"):
                recorder.finalize(**terminal)
            archive = project / metadata.archive_root
            self.assertFalse(
                (archive / "messages/0002-api-worker-to-main-agent-handoff.md").exists()
            )
            self.assertFalse((archive / "events.jsonl").exists())
            self.assertFalse((archive / "INDEX.yaml").exists())

            output_path = project.joinpath(*PurePosixPath(output_ref.path).parts)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(output_ref.payload)

            first = recorder.finalize(**terminal)
            second = recorder.finalize(**terminal)

            self.assertEqual(first, second)
            self.assertEqual(first.index_sha256, sealed.index_sha256)
            self.assertEqual(
                [
                    issue.code
                    for issue in validate_agent_trace(first.index_path, root=project)
                ],
                ["TRACE-CAPTURE-GAP"],
            )
            with self.assertRaisesRegex(
                TraceRecorderError,
                "different terminal metadata or references",
            ):
                recorder.seal(
                    attempt_status="completed",
                    handoff_at=self._timeline().handoff_at,
                    finished_at=self._timeline().finished_at,
                )

    def test_seal_rejects_unfrozen_duplicate_and_escaping_closeout_refs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            recorder = self._begin(project, metadata)
            provider_number = recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:10Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            recorder.record_provider_call_finished(
                provider_number,
                occurred_at="2026-08-16T00:00:12Z",
                status=BoundaryCallStatus.SUCCEEDED,
            )
            path = f"{metadata.archive_root}/objects/result.yaml"
            valid = self._frozen_ref(path, b"result\n")
            terminal = {
                "attempt_status": "completed",
                "handoff_at": self._timeline().handoff_at,
                "finished_at": self._timeline().finished_at,
            }
            cases = (
                (
                    {
                        "output_refs": (
                            FrozenTraceReference(path, "0" * 64, b"result\n"),
                        )
                    },
                    "payload differs from its sha256",
                ),
                (
                    {
                        "handoff_refs": (valid,),
                        "output_refs": (valid,),
                    },
                    "duplicate closeout reference path",
                ),
                (
                    {
                        "handoff_refs": (valid,),
                        "output_refs": (
                            self._frozen_ref(
                                f"{metadata.archive_root}/objects/RESULT.yaml",
                                b"other\n",
                            ),
                        ),
                    },
                    "duplicate closeout reference path",
                ),
                (
                    {
                        "output_refs": (
                            self._frozen_ref(
                                f"{metadata.archive_root}/index.yaml",
                                b"not the Trace index\n",
                            ),
                        )
                    },
                    "collides with Trace-owned material",
                ),
                (
                    {
                        "output_refs": (
                            self._frozen_ref("../outside.yaml", b"outside\n"),
                        )
                    },
                    "cannot escape",
                ),
                (
                    {
                        "output_refs": (
                            self._frozen_ref(
                                "archive/another-attempt/result.yaml", b"x\n"
                            ),
                        )
                    },
                    "within the Attempt archive",
                ),
                (
                    {
                        "output_refs": (
                            FrozenTraceReference(
                                path,
                                valid.sha256,
                                "result\n",  # type: ignore[arg-type]
                            ),
                        )
                    },
                    "payload must be frozen bytes",
                ),
            )
            for arguments, message in cases:
                with (
                    self.subTest(message=message),
                    self.assertRaisesRegex(
                        TraceRecorderError,
                        message,
                    ),
                ):
                    recorder.seal(**terminal, **arguments)
                self.assertFalse(
                    (project / metadata.archive_root / "INDEX.yaml").exists()
                )
            with (
                mock.patch.object(
                    trace_recorder,
                    "resolve_within_root",
                    return_value=project.parent / "link-target",
                ),
                self.assertRaisesRegex(TraceRecorderError, "link or junction"),
            ):
                recorder.seal(**terminal, output_refs=(valid,))

    def test_seal_rejects_open_calls_identity_drift_and_post_seal_capture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            open_recorder = self._begin(project, metadata)
            open_recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:10Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            with self.assertRaisesRegex(TraceRecorderError, "call is still open"):
                open_recorder.seal(
                    attempt_status="completed",
                    handoff_at=self._timeline().handoff_at,
                    finished_at=self._timeline().finished_at,
                )
            self.assertFalse((project / metadata.archive_root / "INDEX.yaml").exists())

        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            drifted = self._begin(project, metadata)
            drifted.metadata = replace(metadata, attempt_id="A-DRIFTED")
            with self.assertRaisesRegex(
                TraceRecorderError, "metadata identity changed"
            ):
                drifted.record_provider_call_started(
                    occurred_at="2026-08-16T00:00:10Z",
                    provider_identity="fake-local",
                    model="fixture-model",
                )
            self.assertEqual(
                list((project / metadata.archive_root / "tool-events").iterdir()),
                [],
            )
            with self.assertRaisesRegex(
                TraceRecorderError, "metadata identity changed"
            ):
                drifted.seal(
                    attempt_status="completed",
                    handoff_at=self._timeline().handoff_at,
                    finished_at=self._timeline().finished_at,
                    capture_gaps=(
                        TraceCaptureGap(
                            CaptureGapKind.RUNTIME_EXPORT,
                            "2026-08-16T00:00:10Z",
                        ),
                    ),
                )

        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)
            provider_number = recorder.record_provider_call_started(
                occurred_at="2026-08-16T00:00:10Z",
                provider_identity="fake-local",
                model="fixture-model",
            )
            recorder.record_provider_call_finished(
                provider_number,
                occurred_at="2026-08-16T00:00:12Z",
                status=BoundaryCallStatus.SUCCEEDED,
            )
            recorder.seal(
                attempt_status="completed",
                handoff_at=self._timeline().handoff_at,
                finished_at=self._timeline().finished_at,
            )
            with self.assertRaisesRegex(TraceRecorderError, "after sealing"):
                recorder.record_provider_call_started(
                    occurred_at="2026-08-16T00:00:13Z",
                    provider_identity="fake-local",
                    model="fixture-model",
                )

    def test_missing_runtime_capture_requires_a_declared_gap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)

            with self.assertRaisesRegex(
                TraceRecorderError, "Provider boundaries are absent"
            ):
                self._finalize(recorder, observe_provider=False)
            self.assertFalse(
                (project / self._metadata().archive_root / "INDEX.yaml").exists()
            )

            result = self._finalize(
                recorder,
                observe_provider=False,
                capture_gaps=(
                    TraceCaptureGap(
                        CaptureGapKind.RUNTIME_EXPORT,
                        "2026-08-16T00:00:10Z",
                    ),
                ),
            )
            issues = validate_agent_trace(result.index_path, root=project)
            self.assertEqual(result.completeness, "gapped")
            self.assertFalse(
                [issue for issue in issues if issue.severity == Severity.ERROR]
            )

    def test_bundle_bytes_are_deterministic_across_project_roots(self) -> None:
        with (
            tempfile.TemporaryDirectory() as left_directory,
            tempfile.TemporaryDirectory() as right_directory,
        ):
            left = self._project(left_directory)
            right = self._project(right_directory)
            left_result = self._finalize(self._begin(left))
            right_result = self._finalize(
                self._begin(
                    right,
                    self._metadata(actors=tuple(reversed(self._metadata().actors))),
                )
            )

            self.assertEqual(left_result.index_sha256, right_result.index_sha256)
            self.assertEqual(
                self._archive_bytes(left_result.index_path.parent),
                self._archive_bytes(right_result.index_path.parent),
            )

    def test_archive_never_copies_task_payload_or_prohibited_record_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            result = self._finalize(
                self._begin(project),
                capture_gaps=(
                    TraceCaptureGap(
                        CaptureGapKind.PROVIDER_CONTENT,
                        "2026-08-16T00:00:15Z",
                    ),
                ),
            )

            archive_text = b"\n".join(
                self._archive_bytes(result.index_path.parent).values()
            ).decode("utf-8")
            for sentinel in (
                "PROMPT-BODY-SENTINEL",
                "SOURCE-BODY-SENTINEL",
                "TOOL-ARGUMENT-SENTINEL",
                "TOOL-RESULT-SENTINEL",
                "RESPONSE-ID-SENTINEL",
                "EXCEPTION-TEXT-SENTINEL",
                "REASONING-SENTINEL",
            ):
                self.assertNotIn(sentinel, archive_text)

            index = load_document(result.index_path)
            actors = load_document(result.index_path.parent / "ACTORS.yaml")
            documents: list[object] = [index, actors, *self._events(result.index_path)]
            prohibited_keys = {
                "prompt",
                "source_body",
                "tool_arguments",
                "tool_results",
                "response_id",
                "credentials",
                "exception_text",
                "reasoning",
            }

            def keys(value: object) -> set[str]:
                if isinstance(value, dict):
                    return set(value) | {
                        nested_key
                        for nested in value.values()
                        for nested_key in keys(nested)
                    }
                if isinstance(value, list):
                    return {
                        nested_key for nested in value for nested_key in keys(nested)
                    }
                return set()

            self.assertTrue(prohibited_keys.isdisjoint(keys(documents)))

    def test_secret_like_actor_metadata_is_rejected_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata(
                actors=(
                    self._metadata().actors[0],
                    replace(
                        self._metadata().actors[1],
                        runtime_identity="api_key:TOPSECRET",
                    ),
                )
            )

            with self.assertRaisesRegex(TraceRecorderError, "credential metadata"):
                self._begin(project, metadata)

            self.assertFalse((project / metadata.archive_root).exists())

    def test_write_failure_leaves_no_index_and_persists_no_exception_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            real_write = trace_recorder.write_text_exclusive
            call_count = 0

            def fail_during_ledger(path: Path, content: str) -> bool:
                nonlocal call_count
                call_count += 1
                if path.name == "events.jsonl":
                    raise OSError("WRITE-EXCEPTION-SENTINEL")
                return real_write(path, content)

            with (
                mock.patch.object(
                    trace_recorder,
                    "write_text_exclusive",
                    side_effect=fail_during_ledger,
                ),
                self.assertRaisesRegex(
                    TraceRecorderError,
                    "artifact publication failed",
                ),
            ):
                self._finalize(self._begin(project, metadata))

            archive = project / metadata.archive_root
            self.assertFalse((archive / "INDEX.yaml").exists())
            self.assertEqual(call_count, 6)
            for path in archive.rglob("*"):
                if path.is_file():
                    self.assertNotIn(
                        "WRITE-EXCEPTION-SENTINEL",
                        path.read_text(encoding="utf-8"),
                    )

    def test_index_verification_failure_removes_commit_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            real_write = trace_recorder.write_text_exclusive

            def omit_index(path: Path, content: str) -> bool:
                if path.name == "INDEX.yaml":
                    return True
                return real_write(path, content)

            with (
                mock.patch.object(
                    trace_recorder,
                    "write_text_exclusive",
                    side_effect=omit_index,
                ),
                self.assertRaisesRegex(TraceRecorderError, "index publication failed"),
            ):
                self._finalize(self._begin(project, metadata))

            self.assertFalse((project / metadata.archive_root / "INDEX.yaml").exists())

    def test_reserved_artifact_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            actors_path = project / metadata.archive_root / "ACTORS.yaml"
            actors_path.parent.mkdir(parents=True)
            actors_path.write_bytes(b"PREEXISTING-SENTINEL")

            with self.assertRaisesRegex(
                TraceRecorderError, "reserved boundary artifact"
            ):
                self._begin(project, metadata)

            self.assertEqual(actors_path.read_bytes(), b"PREEXISTING-SENTINEL")
            self.assertFalse((actors_path.parent / "INDEX.yaml").exists())

    def test_messages_target_file_is_rejected_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            metadata = self._metadata()
            messages_path = project / metadata.archive_root / "messages"
            messages_path.parent.mkdir(parents=True)
            messages_path.write_bytes(b"PREEXISTING-SENTINEL")

            with self.assertRaisesRegex(TraceRecorderError, "not a directory"):
                self._begin(project, metadata)

            self.assertEqual(messages_path.read_bytes(), b"PREEXISTING-SENTINEL")
            self.assertEqual(list(messages_path.parent.iterdir()), [messages_path])

    def test_invalid_start_metadata_fails_before_writes(self) -> None:
        cases = (
            (
                self._metadata(),
                self._timeline(assignment_at="2026-08-15T23:59:59Z"),
                "start must not follow assignment",
            ),
            (
                self._metadata(archive_root="../outside"),
                self._timeline(),
                "cannot escape",
            ),
            (
                self._metadata(
                    actors=(
                        replace(
                            self._metadata().actors[0],
                            accountable_owner="unknown",
                        ),
                        self._metadata().actors[1],
                    )
                ),
                self._timeline(),
                "identify a named owner",
            ),
        )
        for metadata, timeline, error in cases:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                project = self._project(directory)
                with self.assertRaisesRegex(TraceRecorderError, error):
                    begin_api_trace(
                        project,
                        metadata,
                        started_at=timeline.started_at,
                        assignment_at=timeline.assignment_at,
                    )
                self.assertFalse((project / "archive").exists())

    def test_invalid_finalization_is_fail_closed_after_assignment(self) -> None:
        cases = (
            ("running", self._timeline(), "terminal attempt_status"),
            (
                "completed",
                self._timeline(handoff_at="2026-08-15T23:59:59Z"),
                "finalization timeline must be monotonic",
            ),
        )
        for status, timeline, error in cases:
            with self.subTest(error=error), tempfile.TemporaryDirectory() as directory:
                project = self._project(directory)
                recorder = self._begin(project)
                with self.assertRaisesRegex(TraceRecorderError, error):
                    self._finalize(
                        recorder,
                        attempt_status=status,
                        timeline=timeline,
                    )
                archive = project / self._metadata().archive_root
                self.assertTrue((archive / "messages").is_dir())
                self.assertFalse((archive / "events.jsonl").exists())
                self.assertFalse((archive / "INDEX.yaml").exists())

    def test_finalize_is_idempotent_for_same_terminal_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)
            first = self._finalize(recorder)
            second = self._finalize(recorder, observe_provider=False)
            self.assertEqual(first, second)
            with self.assertRaisesRegex(
                TraceRecorderError, "different terminal metadata"
            ):
                self._finalize(
                    recorder,
                    attempt_status="failed",
                    observe_provider=False,
                )

    def test_task_drift_between_begin_and_finalize_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            recorder = self._begin(project)
            task_path = project / "tasks/TASK.yaml"
            task_path.write_text(
                task_path.read_text(encoding="utf-8") + "drift: true\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TraceRecorderError, "trusted Task changed"):
                self._finalize(recorder)

            archive = project / self._metadata().archive_root
            self.assertFalse((archive / "events.jsonl").exists())
            self.assertFalse((archive / "INDEX.yaml").exists())

    def test_retrospective_one_shot_is_declared_gapped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = self._project(directory)
            result = build_api_trace_bundle(
                project,
                self._metadata(),
                self._timeline(),
                attempt_status="completed",
            )

            issues = validate_agent_trace(result.index_path, root=project)
            self.assertEqual(result.completeness, "gapped")
            self.assertEqual(
                [(issue.code, issue.severity) for issue in issues],
                [("TRACE-CAPTURE-GAP", Severity.WARNING)],
            )
            events = self._events(result.index_path)
            self.assertEqual(
                [
                    event["payload"]["action"]
                    for event in events
                    if event["event_type"] == "message-capture"
                ],
                ["exported-delayed", "exported-delayed"],
            )


if __name__ == "__main__":
    unittest.main()
