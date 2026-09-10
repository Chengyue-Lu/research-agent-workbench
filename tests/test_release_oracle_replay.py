"""Replay the immutable independent M14-002 oracle as executable evidence."""
import io
import json
import runpy
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from tests import test_release_surface as fixtures


class ReleaseOracleReplayTests(unittest.TestCase):
    def test_frozen_oracle_reconstructs_pinned_blobs_and_prospective_tree(self):
        # Its seed lifecycle must not replace the main release suite's class state.
        class IsolatedCase(fixtures.ReleaseSurfaceTests):
            pass

        output = io.StringIO()
        path = Path(__file__).resolve().parents[1] / "work/M14-002/A-20260906-001/checks/independent_projection_oracle.py"
        with patch.object(fixtures, "ReleaseSurfaceTests", IsolatedCase), patch.object(sys, "path", list(sys.path)), redirect_stdout(output):
            runpy.run_path(str(path), run_name="__main__")
        report = json.loads(output.getvalue())
        self.assertEqual("PASS", report["result"])
        self.assertEqual("PASS", report["git_tree_oracle"])
        self.assertFalse(report["merge_eligible"])


if __name__ == "__main__":
    unittest.main()
