"""Retained local budget checkpoints with real synthetic temporary files."""

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import traceback
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator

from research_workbench.adapters.models import conformance_budget_anchor as anchor_module
from research_workbench.adapters.models.conformance_journal import ConformanceJournalError, ConformanceUsageJournal
from research_workbench.adapters.models.port import Usage


class ConformanceBudgetAnchorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "synthetic.sqlite"
        self.anchor = self.root / "synthetic.anchor"
        self.namespace = str(uuid4())
        self.instances = []

    def tearDown(self):
        for instance in self.instances:
            instance.close()
        self.temp.cleanup()

    def create(self, *, db=None, anchor=None, total=1000):
        value = ConformanceUsageJournal.create(db or self.db, anchor_path=anchor or self.anchor,
            namespace=self.namespace, total_token_limit=total)
        self.instances.append(value)
        return value

    def reopen(self, *, db=None, anchor=None, total=1000):
        value = ConformanceUsageJournal.open(db or self.db, anchor_path=anchor or self.anchor,
            namespace=self.namespace, total_token_limit=total)
        self.instances.append(value)
        return value

    def known_failure(self, journal):
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.persist_send_intent(handle)
        journal.record_http_entry(handle)
        journal.settle(handle, usage=Usage(12, 3), successful=False, response_received=True)
        return handle

    def expect_halt(self, action):
        with self.assertRaises(ConformanceJournalError) as captured:
            action()
        self.assertIsNone(captured.exception.__cause__)
        self.assertIsNone(captured.exception.__context__)
        self.assertTrue(captured.exception.__suppress_context__)
        return captured.exception.code

    def test_explicit_v2_identity_header_and_readonly_snapshot_no_advance(self):
        journal = self.create()
        header = json.loads(self.anchor.read_bytes().splitlines()[0])
        self.assertEqual(2, header["database_schema_version"])
        self.assertEqual(2, journal._connection.execute("PRAGMA user_version").fetchone()[0])
        self.assertEqual(header["journal_identity"], journal._connection.execute("SELECT identity FROM budget_identity").fetchone()[0])
        before = self.anchor.read_bytes()
        snap = journal.snapshot()
        self.assertEqual(before, self.anchor.read_bytes())
        self.assertEqual("durable-caller-attested", snap["scope"])
        self.assertNotIn("anchor_path", snap)
        self.assertNotIn("journal_identity", snap)
        journal.start_attempt()
        after = self.anchor.read_bytes()
        self.assertEqual(2, len(after.splitlines()))
        journal.snapshot()
        self.assertEqual(after, self.anchor.read_bytes())

    def test_default_none_keeps_v1_schema_and_exact_snapshot_shape(self):
        legacy_path = self.root / "legacy.sqlite"
        legacy = ConformanceUsageJournal.create(legacy_path, namespace=self.namespace, total_token_limit=1000)
        self.instances.append(legacy)
        anchored = self.create()
        self.assertEqual(1, legacy._connection.execute("PRAGMA user_version").fetchone()[0])
        self.assertEqual({"meta", "events"}, {r[0] for r in legacy._connection.execute("SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")})
        self.assertEqual(legacy.snapshot(), anchored.snapshot())
        self.known_failure(legacy)
        self.known_failure(anchored)
        self.assertEqual(legacy.snapshot(), anchored.snapshot())
        self.expect_halt(lambda: ConformanceUsageJournal.open(self.db, namespace=self.namespace, total_token_limit=1000))

    def test_same_namespace_other_database_with_same_anchor_cannot_claim_or_open(self):
        journal = self.create()
        self.known_failure(journal)
        other = self.root / "other.sqlite"
        self.expect_halt(lambda: self.create(db=other))
        self.assertFalse(other.exists())
        self.expect_halt(lambda: self.reopen(db=other))
        self.assertFalse(other.exists())
        self.assertEqual(15, journal.snapshot()["known_total_tokens"])

    def test_other_anchor_is_explicit_caller_boundary_not_global_registry(self):
        first = self.create()
        second = self.create(db=self.root / "other.sqlite", anchor=self.root / "other.anchor")
        self.assertEqual(first.snapshot()["budget_namespace"], second.snapshot()["budget_namespace"])
        self.assertNotEqual(first._anchor.identity, second._anchor.identity)

    def test_existing_anchor_missing_database_never_recreates_on_open_or_create(self):
        journal = self.create()
        journal.close()
        self.db.unlink()
        self.expect_halt(self.reopen)
        self.expect_halt(self.create)
        self.assertFalse(self.db.exists())

    def test_header_exclusive_failure_and_alias_paths_do_not_initialize_database(self):
        self.anchor.write_bytes(b"retained-existing-claim\n")
        self.expect_halt(self.create)
        self.assertFalse(self.db.exists())
        self.expect_halt(lambda: self.create(db=self.root / "alias.sqlite", anchor=self.root / "alias.sqlite"))
        self.assertFalse((self.root / "alias.sqlite").exists())

    def test_initial_claim_fsync_failure_retains_claim_and_never_creates_database(self):
        with patch.object(anchor_module.os, "fsync", side_effect=OSError("SYNTHETIC-INITIAL-CLAIM")):
            self.expect_halt(self.create)
        self.assertTrue(self.anchor.exists())
        self.assertFalse(self.db.exists())
        self.expect_halt(self.create)
        self.expect_halt(self.reopen)
        self.assertFalse(self.db.exists())

    def test_namespace_limit_path_identity_and_closed_header_drift_halt(self):
        journal = self.create()
        original = self.anchor.read_bytes()
        header = json.loads(original.splitlines()[0])
        for update in ({"budget_namespace": str(uuid4())}, {"database_path": str(self.root / "other")},
                       {"journal_identity": str(uuid4())}, {"extra": True},
                       {"limits": {**header["limits"], "total_token_limit": 999}},
                       {"database_schema_version": 2.0}):
            with self.subTest(update=update):
                changed = {**header, **update}
                self.anchor.write_bytes((json.dumps(changed, sort_keys=True, separators=(",", ":")) + "\n").encode())
                self.expect_halt(journal.snapshot)
                self.expect_halt(self.reopen)
                self.anchor.write_bytes(original)
        journal._connection.execute("UPDATE budget_identity SET identity=?", (str(uuid4()),))
        self.expect_halt(journal.snapshot)

    def test_valid_prefix_database_rollback_detected_on_snapshot_and_reopen(self):
        journal = self.create()
        self.known_failure(journal)
        journal._connection.execute("DELETE FROM events WHERE seq>1")
        self.assertEqual("budget-anchor-drift", self.expect_halt(journal.snapshot))
        journal.close()
        self.assertEqual("budget-anchor-drift", self.expect_halt(self.reopen))

    def test_anchor_behind_database_and_anchor_ahead_database_halt(self):
        journal = self.create()
        header_only = self.anchor.read_bytes()
        journal.start_attempt()
        one = self.anchor.read_bytes()
        journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        two = self.anchor.read_bytes()
        self.anchor.write_bytes(one)
        self.assertEqual("budget-anchor-drift", self.expect_halt(journal.snapshot))
        self.anchor.write_bytes(two)
        journal._connection.execute("DELETE FROM events WHERE seq=2")
        self.assertEqual("budget-anchor-drift", self.expect_halt(journal.snapshot))
        self.assertNotEqual(header_only, one)

    def test_torn_missing_truncated_duplicate_and_modified_checkpoint_halt(self):
        journal = self.create()
        journal.start_attempt()
        original = self.anchor.read_bytes()
        lines = original.splitlines(keepends=True)
        for raw in (b"", original[:-1], original + b'{"seq":2', lines[0], original + lines[1],
                    lines[0] + lines[1].replace(b'"chain":"', b'"chain":"0', 1)):
            with self.subTest(raw_length=len(raw)):
                self.anchor.write_bytes(raw)
                self.expect_halt(journal.snapshot)
                self.expect_halt(self.reopen)
        self.anchor.write_bytes(original)
        self.anchor.unlink()
        self.assertEqual("budget-anchor-unavailable", self.expect_halt(journal.snapshot))
        self.assertEqual("budget-anchor-unavailable", self.expect_halt(self.reopen))
        self.assertFalse(self.anchor.exists())

    def test_same_instance_history_edit_does_not_get_reanchored(self):
        journal = self.create()
        journal.start_attempt()
        journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        before = self.anchor.read_bytes()
        journal._connection.execute("UPDATE events SET payload=? WHERE seq=2",
            ('{"attempt":1,"input":21,"ordinal":1,"output":10}',))
        self.expect_halt(journal.snapshot)
        self.assertEqual(before, self.anchor.read_bytes())

    def test_lexical_payload_history_drift_is_not_reanchored(self):
        journal = self.create()
        journal.start_attempt()
        before = self.anchor.read_bytes()
        journal._connection.execute("UPDATE events SET payload=? WHERE seq=1",
            ('{"refreeze": false, "ordinal": 1}',))
        self.assertEqual("budget-anchor-drift", self.expect_halt(journal.snapshot))
        self.assertEqual("budget-anchor-drift", self.expect_halt(self.reopen))
        self.assertEqual(before, self.anchor.read_bytes())

    def test_mutation_during_checkpoint_io_is_detected_before_commit(self):
        journal = self.create()
        original = anchor_module.ConformanceBudgetAnchor.checkpoint

        def mutate(anchor, events, *, previous_count):
            result = original(anchor, events, previous_count=previous_count)
            journal._connection.execute("UPDATE events SET payload=? WHERE seq=1", ('{"ordinal":1,"refreeze":true}',))
            return result

        with patch.object(anchor_module.ConformanceBudgetAnchor, "checkpoint", mutate):
            self.assertEqual("budget-anchor-drift", self.expect_halt(journal.start_attempt))
        self.assertEqual(0, journal._connection.execute("SELECT count(*) FROM events").fetchone()[0])
        self.assertEqual(2, len(self.anchor.read_bytes().splitlines()))
        self.expect_halt(self.reopen)

    def test_failed_commit_keeps_ahead_checkpoint_and_never_rewinds_it(self):
        journal = self.create()
        def deny_commit(operation, arg1, arg2, database, source):
            return sqlite3.SQLITE_DENY if operation == sqlite3.SQLITE_TRANSACTION and arg1 == "COMMIT" else sqlite3.SQLITE_OK

        journal._connection.set_authorizer(deny_commit)
        self.assertEqual("journal-storage-unavailable", self.expect_halt(journal.start_attempt))
        journal._connection.set_authorizer(None)
        self.assertEqual(0, journal._connection.execute("SELECT count(*) FROM events").fetchone()[0])
        self.assertEqual(2, len(self.anchor.read_bytes().splitlines()))
        self.expect_halt(journal.snapshot)
        journal.close()
        self.expect_halt(self.reopen)

    def test_failure_before_checkpoint_writes_rolls_back_without_consumption(self):
        journal = self.create()
        before = self.anchor.read_bytes()
        with patch.object(anchor_module.os, "open", side_effect=OSError("SYNTHETIC-AUTH-PATH")):
            self.expect_halt(journal.start_attempt)
        self.assertEqual(before, self.anchor.read_bytes())
        self.assertEqual(0, journal.snapshot()["events_committed"])

    def test_fsync_failure_keeps_checkpoint_and_halts_after_db_rollback(self):
        journal = self.create()
        with patch.object(anchor_module.os, "fsync", side_effect=OSError("SYNTHETIC-AUTH-FSYNC")):
            self.expect_halt(journal.start_attempt)
        self.assertEqual(2, len(self.anchor.read_bytes().splitlines()))
        self.expect_halt(journal.snapshot)
        self.expect_halt(self.reopen)

    def test_intent_and_unknown_usage_reopen_retain_hold_without_new_slots(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.persist_send_intent(handle)
        journal.close()
        restored = self.reopen()
        snap = restored.snapshot()
        self.assertEqual(30, snap["unresolved_reserved_tokens"])
        self.assertTrue(snap["blocked"])
        self.assertTrue(snap["recovery_required"])
        self.expect_halt(lambda: restored.start_attempt(repair_refreeze_confirmed=True))
        self.expect_halt(lambda: restored.reject_before_send(handle))
        other = self.create(db=self.root / "unknown.sqlite", anchor=self.root / "unknown.anchor")
        other.start_attempt()
        call = other.reserve(input_upper_tokens=20, output_upper_tokens=10)
        other.persist_send_intent(call)
        other.record_http_entry(call)
        self.expect_halt(lambda: other.settle(call, usage=None, successful=False, response_received=False))
        other.close()
        again = self.reopen(db=self.root / "unknown.sqlite", anchor=self.root / "unknown.anchor")
        self.assertEqual(30, again.snapshot()["unresolved_reserved_tokens"])
        self.assertTrue(again.snapshot()["blocked"])

    def test_cost_unknown_tokens_preserved_detached_snapshot_and_existing_schema(self):
        journal = self.create()
        journal.start_attempt()
        handle = journal.reserve(input_upper_tokens=20, output_upper_tokens=10)
        journal.persist_send_intent(handle)
        journal.record_http_entry(handle)
        marker = "SYNTHETIC-PRIVATE-CURRENCY"
        journal.settle(handle, usage=Usage(12, 3, provider_reported_cost=float("nan"), currency=marker),
            successful=False, response_received=True)
        snapshot = journal.snapshot()
        self.assertEqual(15, snapshot["known_total_tokens"])
        self.assertEqual("unknown", snapshot["cost"]["status"])
        self.assertNotIn(marker, json.dumps(snapshot))
        report_schema_path = Path(__file__).resolve().parents[1] / "schemas/v0.1.0/profile-conformance-report.schema.json"
        schema = json.loads(report_schema_path.read_text(encoding="utf-8"))
        Draft202012Validator(schema["properties"]["accounting"]).validate(snapshot)
        snapshot["calls"][0]["reported_usage"]["input_tokens"] = 999
        snapshot["limits"]["total_token_limit"] = 999
        self.assertEqual(15, journal.snapshot()["known_total_tokens"])
        self.assertEqual(1000, journal.snapshot()["limits"]["total_token_limit"])
        journal.close()
        self.assertEqual(15, self.reopen().snapshot()["known_total_tokens"])

    def test_two_connections_serialize_and_keep_exact_anchor_chain(self):
        first = self.create(total=50)
        second = self.reopen(total=50)
        first.start_attempt()
        barrier = threading.Barrier(3)
        accepted, refused = [], []

        def reserve(journal):
            barrier.wait()
            try:
                accepted.append(journal.reserve(input_upper_tokens=20, output_upper_tokens=10))
            except ConformanceJournalError as error:
                refused.append(error.code)

        workers = [threading.Thread(target=reserve, args=(journal,)) for journal in (first, second)]
        for worker in workers:
            worker.start()
        barrier.wait()
        for worker in workers:
            worker.join(5)
            self.assertFalse(worker.is_alive())
        self.assertEqual(1, len(accepted))
        self.assertEqual(["reservation-admission-refused"], refused)
        self.assertEqual(30, first.snapshot()["unresolved_reserved_tokens"])
        self.assertEqual(first.snapshot()["events_committed"], second.snapshot()["events_committed"])
        self.assertEqual(3, len(self.anchor.read_bytes().splitlines()))

    def test_real_subprocess_crash_after_checkpoint_before_commit_halts_reopen(self):
        journal = self.create()
        journal.close()
        script = (
            "import os\n"
            "from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal\n"
            "from research_workbench.adapters.models import conformance_budget_anchor as a\n"
            f"j=ConformanceUsageJournal.open({str(self.db)!r},anchor_path={str(self.anchor)!r},namespace={self.namespace!r},total_token_limit=1000)\n"
            "original=a.ConformanceBudgetAnchor.checkpoint\n"
            "def crash(self, events, *, previous_count):\n"
            "    original(self,events,previous_count=previous_count)\n"
            "    os._exit(0)\n"
            "a.ConformanceBudgetAnchor.checkpoint=crash\n"
            "j.start_attempt()\n"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, len(self.anchor.read_bytes().splitlines()))
        self.assertEqual("budget-anchor-drift", self.expect_halt(self.reopen))

    def test_real_subprocess_crash_after_committed_intent_keeps_unknown_hold(self):
        journal = self.create()
        journal.close()
        script = (
            "import os\n"
            "from research_workbench.adapters.models.conformance_journal import ConformanceUsageJournal\n"
            f"j=ConformanceUsageJournal.open({str(self.db)!r},anchor_path={str(self.anchor)!r},namespace={self.namespace!r},total_token_limit=1000)\n"
            "j.start_attempt()\n"
            "r=j.reserve(input_upper_tokens=20,output_upper_tokens=10)\n"
            "j.persist_send_intent(r)\n"
            "os._exit(0)\n"
        )
        result = subprocess.run([sys.executable, "-B", "-c", script], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        snap = self.reopen().snapshot()
        self.assertEqual(30, snap["unresolved_reserved_tokens"])
        self.assertTrue(snap["blocked"])
        self.assertEqual(0, snap["http_entry_observations"])

    def test_anchor_error_from_provider_except_never_exports_values_or_chains(self):
        journal = self.create()
        self.anchor.unlink()
        marker = "SYNTHETIC-PRIVATE-PROVIDER-AUTH"
        try:
            raise RuntimeError(marker)
        except RuntimeError:
            with self.assertRaises(ConformanceJournalError) as captured:
                journal.snapshot()
        error = captured.exception
        self.assertIsNone(error.__context__)
        self.assertIsNone(error.__cause__)
        self.assertNotIn(marker, str(error) + repr(error) + "".join(traceback.format_exception(error)))
        self.assertNotIn(str(self.db), str(error) + repr(error))


if __name__ == "__main__":
    unittest.main()
