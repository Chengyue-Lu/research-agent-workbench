import tempfile
import unittest
from pathlib import Path
from unittest import mock

from research_workbench.io import (
    load_document,
    publish_staged_file_exclusive,
    write_bytes_exclusive,
    write_text_exclusive,
    write_yaml_exclusive,
)


class ExclusivePublicationTests(unittest.TestCase):
    def test_staged_file_is_published_without_removing_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = root / "stage" / "artifact.yaml"
            final = root / "final" / "artifact.yaml"
            staged.parent.mkdir()
            staged.write_bytes(b"bounded artifact\n")

            published = publish_staged_file_exclusive(staged, final)

            self.assertTrue(published)
            self.assertEqual(b"bounded artifact\n", final.read_bytes())
            self.assertEqual(b"bounded artifact\n", staged.read_bytes())

    def test_identical_existing_target_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = root / "staged.txt"
            final = root / "final.txt"
            staged.write_bytes(b"same bytes\n")
            final.write_bytes(b"same bytes\n")

            published = publish_staged_file_exclusive(staged, final)

            self.assertFalse(published)
            self.assertEqual(b"same bytes\n", final.read_bytes())
            self.assertTrue(staged.exists())

    def test_different_existing_target_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staged = root / "staged.txt"
            final = root / "final.txt"
            staged.write_bytes(b"new bytes\n")
            final.write_bytes(b"authoritative bytes\n")

            with self.assertRaises(FileExistsError):
                publish_staged_file_exclusive(staged, final)

            self.assertEqual(b"authoritative bytes\n", final.read_bytes())
            self.assertEqual(b"new bytes\n", staged.read_bytes())

    def test_link_failure_leaves_no_final_or_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / "nested" / "result.txt"
            with mock.patch("research_workbench.io.os.link", side_effect=OSError("injected")):
                with self.assertRaisesRegex(OSError, "injected"):
                    write_text_exclusive(final, "complete content\n")

            self.assertFalse(final.exists())
            self.assertEqual([], list(final.parent.glob(f".{final.name}.*.tmp")))

    def test_text_and_yaml_writers_are_idempotent_and_parseable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text_path = root / "note.txt"
            yaml_path = root / "state.yaml"
            document = {"schema_version": "0.1.0", "next_actions": ["resume once"]}

            self.assertTrue(write_text_exclusive(text_path, "bounded text\n"))
            self.assertFalse(write_text_exclusive(text_path, "bounded text\n"))
            self.assertTrue(write_yaml_exclusive(yaml_path, document))
            self.assertFalse(write_yaml_exclusive(yaml_path, document))

            self.assertEqual("bounded text\n", text_path.read_text(encoding="utf-8"))
            self.assertEqual(document, load_document(yaml_path))

    def test_byte_writer_preserves_exact_payload_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "snapshot.bin"
            payload = b"\xef\xbb\xbfexact\r\nbytes\x00"

            self.assertTrue(write_bytes_exclusive(target, payload))
            self.assertFalse(write_bytes_exclusive(target, payload))
            self.assertEqual(payload, target.read_bytes())


if __name__ == "__main__":
    unittest.main()
