"""Offline exact source-input closure regressions; no scientific qualification."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from research_workbench.artifacts.admission import build_admission_mapping, sidecar_path_for
from research_workbench.entry.materials import MaterialInputError, read_material_inputs


RAW = "sources/raw/document.txt"
SIDECAR = sidecar_path_for(RAW)
DERIVATIVE = "artifacts/excerpt.txt"
CONTENT = "Explicit synthetic source text.\n".encode("utf-8")


class EntryMaterialsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, path, raw):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        return {"path": path, "sha256": hashlib.sha256(raw).hexdigest()}

    def admission(self, **changes):
        value = build_admission_mapping(original_filename="document.txt", admitted_path=RAW, content=CONTENT,
            origin={"uri": "https://example.org/synthetic-source"}, acquired_at="2026-10-11T00:00:00+08:00",
            operator="fixture", license_or_data_use="synthetic test input", parser_name="utf8-text",
            parser_version="1.0.0", sensitivity="fixture-only", egress_restriction="no-implied-upload")
        value.update(changes)
        return value

    def closure(self, document=None, *, derivative=False):
        raw = self.write(RAW, CONTENT)
        value = document or self.admission()
        derived = None
        if derivative:
            derived = self.write(DERIVATIVE, b"Selected excerpt.\n")
            value = copy.deepcopy(value)
            value["derivatives"] = [{**derived, "relation": "text-excerpt"}]
        sidecar = self.write(SIDECAR, yaml.safe_dump(value, sort_keys=False).encode("utf-8"))
        return [raw, sidecar] + ([derived] if derived is not None else [])

    def assert_code(self, expected, refs):
        with self.assertRaises(MaterialInputError) as caught:
            read_material_inputs(self.root, refs)
        self.assertEqual(expected, caught.exception.code)

    def test_ordinary_utf8_control_and_readme_need_no_admission(self):
        refs = [self.write("README.md", "普通材料\n".encode("utf-8")),
                self.write("controls/task.json", b'{"revision": 2}\n')]
        refs[1]["revision"] = 2
        snapshots = read_material_inputs(self.root, refs)
        self.assertEqual("普通材料\n", snapshots[0]["text"])
        self.assertEqual(2, snapshots[1]["revision"])
        self.assertTrue(all(item["material_provenance"]["kind"] == "ordinary-input" for item in snapshots))
        self.assertTrue(all(item["material_provenance"]["scientific_qualification"] == "not-established" for item in snapshots))

    def test_raw_and_explicit_sidecar_preserve_provenance_without_permission_grant(self):
        refs = self.closure()
        snapshots = read_material_inputs(self.root, refs)
        provenance = snapshots[0]["material_provenance"]
        self.assertEqual("raw-source", provenance["kind"])
        self.assertEqual("0.1.0", provenance["schema_version"])
        self.assertEqual("1.0.0", provenance["parser"]["version"])
        self.assertEqual(refs[1]["sha256"], provenance["admission_ref"]["sha256"])
        self.assertEqual(refs[0]["sha256"], provenance["raw_ref"]["sha256"])
        self.assertEqual("no-implied-upload", provenance["egress_restriction"])
        self.assertFalse(provenance["permission_grant"])
        self.assertEqual("not-established", provenance["scientific_qualification"])
        self.assertEqual("source-admission", snapshots[1]["material_provenance"]["kind"])

    def test_selected_derivative_consumes_only_exact_raw_sidecar_and_derived_pins(self):
        refs = self.closure(derivative=True)
        snapshots = read_material_inputs(self.root, reversed(refs))
        derived = next(item for item in snapshots if item["path"] == DERIVATIVE)
        self.assertEqual("source-derivative", derived["material_provenance"]["kind"])
        self.assertEqual("text-excerpt", derived["material_provenance"]["relation"])
        self.assertEqual(refs[-1]["sha256"], derived["material_provenance"]["derivative_ref"]["sha256"])

    def test_accepted_metadata_does_not_create_permission_or_scientific_acceptance(self):
        snapshots = read_material_inputs(self.root, self.closure(self.admission(metadata={"accepted": True})))
        provenance = snapshots[0]["material_provenance"]
        self.assertFalse(provenance["permission_grant"])
        self.assertEqual("not-established", provenance["scientific_qualification"])
        self.assertNotIn("accepted", provenance)

    def test_unselected_derivative_is_not_opened_even_when_missing_or_hash_wrong(self):
        document = self.admission(derivatives=[
            {"path": "unread/missing.txt", "sha256": "a" * 64, "relation": "text-excerpt"},
            {"path": "sources/inbox/unselected.txt", "sha256": "b" * 64, "relation": "metadata-only"}])
        refs = self.closure(document)
        original = Path.read_bytes
        opened = []
        def recorded(path):
            if path.is_relative_to(self.root):
                opened.append(path.relative_to(self.root).as_posix())
            return original(path)
        with patch.object(Path, "read_bytes", recorded):
            snapshots = read_material_inputs(self.root, refs)
        self.assertEqual([RAW, SIDECAR], opened)
        self.assertEqual(2, len(snapshots))

    def test_no_directory_scan_or_implicit_sidecar_read_for_raw(self):
        refs = self.closure()
        original = Path.read_bytes
        opened = []
        def recorded(path):
            if path.is_relative_to(self.root):
                opened.append(path.relative_to(self.root).as_posix())
            return original(path)
        with patch.object(Path, "read_bytes", recorded), patch.object(Path, "rglob", side_effect=AssertionError("no discovery")):
            self.assert_code("MATERIAL-ADMISSION-MISSING", refs[:1])
        self.assertEqual([RAW], opened)

    def test_sidecar_raw_metadata_does_not_grant_a_raw_read(self):
        refs = self.closure()
        original = Path.read_bytes
        opened = []
        def recorded(path):
            if path.is_relative_to(self.root):
                opened.append(path.relative_to(self.root).as_posix())
            return original(path)
        with patch.object(Path, "read_bytes", recorded):
            self.assert_code("MATERIAL-UNAUTHORIZED-REFERENCE", refs[1:])
        self.assertEqual([SIDECAR], opened)

    def test_hash_drift_in_raw_sidecar_and_derivative_each_blocks(self):
        for path in (RAW, SIDECAR, DERIVATIVE):
            with self.subTest(path=path):
                refs = self.closure(derivative=True)
                (self.root / path).write_bytes(b"drift\n")
                self.assert_code("MATERIAL-HASH-DRIFT", refs)

    def test_reference_tracks_changed_raw_but_old_admission_still_blocks(self):
        refs = self.closure()
        refs[0] = self.write(RAW, b"new independently pinned bytes\n")
        self.assert_code("MATERIAL-RAW-BINDING", refs)

    def test_wrong_raw_binding_cannot_substitute_another_source(self):
        refs = self.closure(self.admission(admitted_path="sources/raw/other.txt"))
        self.assert_code("MATERIAL-RAW-BINDING", refs)

    def test_malformed_schema_invalid_and_wrong_schema_version_sidecars_block(self):
        for value in (b"[unterminated", b"- scalar\n", self.admission(schema_version="9.0.0"),
                      self.admission(acquisition={"origin": {}, "acquired_at": "now", "operator": "fixture"})):
            with self.subTest(value=type(value).__name__):
                refs = self.closure()
                raw = value if isinstance(value, bytes) else yaml.safe_dump(value).encode("utf-8")
                refs[1] = self.write(SIDECAR, raw)
                self.assert_code("MATERIAL-ADMISSION-INVALID", refs)

    def test_sidecar_timestamp_requires_timezone(self):
        value = self.admission()
        value["acquisition"]["acquired_at"] = "2026-10-11T00:00:00"
        self.assert_code("MATERIAL-ADMISSION-INVALID", self.closure(value))

    def test_selected_derivative_hash_mismatch_in_sidecar_blocks(self):
        derived = self.write(DERIVATIVE, b"selected bytes")
        value = self.admission(derivatives=[{**derived, "sha256": "a" * 64, "relation": "text-excerpt"}])
        refs = self.closure(value) + [derived]
        self.assert_code("MATERIAL-DERIVATIVE-BINDING", refs)

    def test_duplicate_selected_derivative_and_self_relation_block(self):
        derived = self.write(DERIVATIVE, b"selected bytes")
        entry = {**derived, "relation": "text-excerpt"}
        for derivatives in ([entry, entry], [{"path": RAW, "sha256": hashlib.sha256(CONTENT).hexdigest(), "relation": "self"}]):
            with self.subTest(derivatives=derivatives):
                refs = self.closure(self.admission(derivatives=derivatives)) + [derived]
                self.assert_code("MATERIAL-DERIVATIVE-BINDING", refs)

    def test_selected_inbox_reference_is_rejected_before_content_read(self):
        pin = self.write("sources/inbox/input.txt", b"unadmitted\n")
        with patch.object(Path, "read_bytes", side_effect=AssertionError("inbox content must not open")):
            self.assert_code("MATERIAL-INBOX-UNADMITTED", [pin])

    def test_case_insensitive_source_zones_cannot_become_ordinary_inputs(self):
        inbox = self.write("sources/inbox/case-input.txt", b"unadmitted\n")
        inbox_alias = {**inbox, "path": "SoUrCeS/InBoX/case-input.txt"}
        if os.name == "nt":
            self.assertTrue((self.root / inbox_alias["path"]).samefile(self.root / inbox["path"]))
        else:
            self.assertFalse((self.root / inbox_alias["path"]).exists())
        with patch.object(Path, "read_bytes", side_effect=AssertionError("case-disguised inbox must not open")):
            self.assert_code("MATERIAL-INBOX-UNADMITTED", [inbox_alias])

        raw = self.write(RAW, CONTENT)
        raw_alias = {**raw, "path": "SOURCES/RAW/document.txt"}
        if os.name == "nt":
            self.assertTrue((self.root / raw_alias["path"]).samefile(self.root / RAW))
            with self.assertRaises(MaterialInputError) as caught:
                read_material_inputs(self.root, [raw_alias])
            self.assertIn(caught.exception.code, {"MATERIAL-RAW-BINDING", "MATERIAL-ADMISSION-MISSING"})
        else:
            self.assertFalse((self.root / raw_alias["path"]).exists())
            self.assert_code("MATERIAL-MISSING-INPUT", [raw_alias])

        # This spelling really exists on every platform: case-folding must
        # still require source admission rather than return ordinary text.
        mixed_raw = self.write("SoUrCeS/RaW/existing-case-input.txt", CONTENT)
        with self.assertRaises(MaterialInputError) as caught:
            read_material_inputs(self.root, [mixed_raw])
        self.assertIn(caught.exception.code, {"MATERIAL-RAW-BINDING", "MATERIAL-ADMISSION-MISSING"})

    def test_real_root_internal_symlinks_to_inbox_and_raw_are_rejected_without_reads(self):
        inbox = self.write("sources/inbox/linked-input.txt", b"unadmitted\n")
        raw = self.write("sources/raw/linked-input.txt", CONTENT)
        aliases = []
        for zone, pin, code in (("inbox", inbox, "MATERIAL-INBOX-UNADMITTED"),
                                ("raw", raw, "MATERIAL-RAW-BINDING")):
            link = self.root / ("ordinary-" + zone + "-link")
            target = (self.root / pin["path"]).parent
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                if os.name != "nt":
                    self.skipTest("real directory symlink unavailable: " + str(exc))
                # Junctions exercise the same real resolved-path boundary and
                # do not require Windows' symbolic-link privilege.
                created = subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if created.returncode:
                    self.skipTest("real symlink and junction unavailable")
            self.assertTrue(link.is_dir())
            self.assertEqual(target.resolve(), link.resolve())
            aliases.append(({**pin, "path": link.name + "/linked-input.txt"}, code))
        with patch.object(Path, "read_bytes", side_effect=AssertionError("source alias must reject before content reads")):
            for pin, code in aliases:
                with self.subTest(path=pin["path"]):
                    self.assert_code(code, [pin])

    def test_missing_invalid_outside_root_and_duplicate_pins_block(self):
        pin = self.write("README.md", b"ordinary\n")
        for code, refs in (("MATERIAL-MISSING-INPUT", [{"path": "missing.txt", "sha256": "a" * 64}]),
                           ("MATERIAL-INVALID-PIN", [{"path": "../outside.txt", "sha256": "a" * 64}]),
                           ("MATERIAL-INVALID-PIN", [{"path": "C:outside.txt", "sha256": "a" * 64}]),
                           ("MATERIAL-INVALID-PIN", [{"path": "README.md"}]),
                           ("MATERIAL-DUPLICATE-INPUT", [pin, pin])):
            with self.subTest(code=code, refs=refs):
                self.assert_code(code, refs)

    def test_revision_drift_blocks_on_same_captured_document_bytes(self):
        pin = self.write("controls/task.json", b'{"revision": 2}\n')
        pin["revision"] = 1
        self.assert_code("MATERIAL-REVISION-MISMATCH", [pin])

    def test_hash_and_text_are_from_one_capture_even_if_file_changes_after_read(self):
        pin = self.write("README.md", b"first captured text\n")
        original = Path.read_bytes
        reads = []
        def mutate_after_read(path):
            raw = original(path)
            if path == self.root / "README.md":
                reads.append(path)
                path.write_bytes(b"later mutation\n")
            return raw
        with patch.object(Path, "read_bytes", mutate_after_read):
            snapshots = read_material_inputs(self.root, [pin])
        self.assertEqual("first captured text\n", snapshots[0]["text"])
        self.assertEqual(1, len(reads))

    def test_sidecar_parses_same_captured_bytes_even_if_mutated_after_read(self):
        refs = self.closure()
        original = Path.read_bytes
        reads = []
        def mutate_after_read(path):
            raw = original(path)
            if path == self.root / SIDECAR:
                reads.append(path)
                path.write_bytes(b"not the captured sidecar\n")
            return raw
        with patch.object(Path, "read_bytes", mutate_after_read):
            snapshots = read_material_inputs(self.root, refs)
        self.assertEqual("raw-source", snapshots[0]["material_provenance"]["kind"])
        self.assertEqual(1, len(reads))

    def test_ordinary_admission_shaped_json_is_not_guessed_to_be_a_sidecar(self):
        pin = self.write("controls/source-metadata.json", json.dumps(self.admission()).encode("utf-8"))
        snapshot = read_material_inputs(self.root, [pin])[0]
        self.assertEqual("ordinary-input", snapshot["material_provenance"]["kind"])

    def test_nonraw_unproven_file_remains_explicitly_source_unverified(self):
        pin = self.write(DERIVATIVE, b"No explicit source relation\n")
        snapshot = read_material_inputs(self.root, [pin])[0]
        self.assertEqual("not-declared", snapshot["material_provenance"]["source_relation"])
        self.assertIn("No source relation", snapshot["material_provenance"]["gap"])

    def test_binary_material_is_unsupported_even_when_a_pdf_happens_to_decode_utf8(self):
        binary_path = "sources/raw/document.pdf"
        content = b"%PDF-1.4\nsynthetic binary-format header\n"
        raw = self.write(binary_path, content)
        value = self.admission(admitted_path=binary_path, sha256=raw["sha256"])
        sidecar = self.write(sidecar_path_for(binary_path), yaml.safe_dump(value).encode("utf-8"))
        self.assert_code("MATERIAL-UNSUPPORTED-FORMAT", [raw, sidecar])

    def test_invalid_utf8_input_is_not_pseudo_parsed(self):
        pin = self.write("materials/binary.bin", b"\xff\xfe\x00\x01")
        self.assert_code("MATERIAL-UNSUPPORTED-FORMAT", [pin])

    def test_legacy_per_file_and_aggregate_text_limits_remain_the_same(self):
        pin = self.write("ordinary/too-large.txt", b"a" * 1_048_577)
        self.assert_code("MATERIAL-TEXT-LIMIT", [pin])
        refs = [self.write(f"ordinary/{index}.txt", b"a" * 1_048_576) for index in range(4)]
        refs.append(self.write("ordinary/extra.txt", b"x"))
        self.assert_code("MATERIAL-TEXT-LIMIT", refs)


if __name__ == "__main__":
    unittest.main()
