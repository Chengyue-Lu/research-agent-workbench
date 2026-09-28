"""Development-side selection of current policy files; validators live in release_public."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
try:
    from release_public import PUBLIC_PAGES, build_input_errors, documentation_errors
finally:
    sys.path.pop(0)


def selected_files(root: Path) -> dict[str, bytes]:
    """Include tracked and proposed untracked source inputs, not ignored build output."""
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).decode().split("\0")
    policy = json.loads((root / ".github/release-surface.yml").read_bytes())["policies"][-1]
    selected = set()
    for entry in policy["include"]:
        matches = {name for name in names if name == entry["path"] or (
            entry["kind"] == "tree" and name.startswith(entry["path"] + "/"))}
        if not matches:
            raise ValueError(f"missing include: {entry['path']}")
        selected.update(matches)
    return {name: (root / name).read_bytes() for name in sorted(selected)}
