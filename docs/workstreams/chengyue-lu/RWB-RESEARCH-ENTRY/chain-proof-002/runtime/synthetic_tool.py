"""Optional exact-file lookup for the explicitly selected synthetic bridge.

No Supply, qualification, permission, network access or write is created here.
Root alone may instantiate and exercise this candidate in an authorized Task.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from research_workbench.adapters.models.port import ToolDefinition
from research_workbench.adapters.models.session import ClientTool

MAX_TEXT_BYTES = 4096


def _portable(path: str) -> str:
    if (not isinstance(path, str) or not path or "\\" in path or ":" in path
            or any(ord(char) < 32 for char in path) or PurePosixPath(path).is_absolute()
            or any(part in {"", ".", ".."} for part in path.split("/"))):
        raise ValueError("Tool target must be a portable exact relative file path")
    return path


def _reference(task: Any, target: str) -> tuple[str, str, Any]:
    refs = task.get("input_refs", ()) if isinstance(task, Mapping) else getattr(task, "input_refs", ())
    matches = []
    for item in refs:
        path = item.get("path") if isinstance(item, Mapping) else getattr(item, "path", None)
        if path == target:
            digest = item.get("sha256") if isinstance(item, Mapping) else getattr(item, "sha256", None)
            revision = item.get("revision") if isinstance(item, Mapping) else getattr(item, "revision", None)
            if not isinstance(digest, str):
                raise ValueError("Tool target needs the actual Task SHA256 pin")
            digest = digest.lower().removeprefix("sha256:")
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError("Tool target has an invalid Task SHA256 pin")
            matches.append((path, digest, revision))
    if len(matches) != 1:
        raise ValueError("Tool target must have exactly one actual Task input reference")
    return matches[0]


def _file(root: Path, target: str) -> Path:
    candidate = root
    for part in target.split("/"):
        candidate = candidate / part
        if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
            raise ValueError("Tool target cannot traverse a filesystem link")
    resolved = candidate.resolve(strict=True)
    if root not in resolved.parents or not resolved.is_file():
        raise ValueError("Tool target must be an existing file within the explicit root")
    return resolved


def create_synthetic_lookup(root, task, target_path="materials/intent.txt") -> ClientTool:
    """Declare one optional read-only Tool; do not read target content at creation.

    The handler rechecks the supplied Task ref, containment, SHA and UTF-8 on
    every invocation. Payload classification and outbound permission remain the
    caller's responsibility under the selected Task/Profile/Supply/View.
    """
    target = _portable(target_path)
    root_path = Path(root).resolve(strict=True)
    if not root_path.is_dir():
        raise ValueError("Tool root must be an explicit existing directory")
    declared = _reference(task, target)

    def lookup(arguments: Mapping[str, Any]) -> dict[str, str]:
        if (not isinstance(arguments, Mapping) or set(arguments) != {"path"}
                or arguments["path"] != target):
            raise ValueError("Tool arguments must contain only the exact declared path")
        if _reference(task, target) != declared:
            raise ValueError("Tool target Task reference changed after declaration")
        path = _file(root_path, target)
        with path.open("rb") as stream:
            before = os.fstat(stream.fileno())
            if before.st_size > MAX_TEXT_BYTES:
                raise ValueError("Tool input exceeds the 4096-byte bound")
            raw = stream.read(MAX_TEXT_BYTES)
            after = os.fstat(stream.fileno())
        if (after.st_size > MAX_TEXT_BYTES or len(raw) != before.st_size
                or after.st_size != before.st_size
                or after.st_mtime_ns != before.st_mtime_ns
                or after.st_ctime_ns != before.st_ctime_ns):
            raise ValueError("Tool input changed during its bounded read")
        if _file(root_path, target) != path or _reference(task, target) != declared:
            raise ValueError("Tool path or Task reference changed during read")
        current = path.stat()
        if any(getattr(current, field) != getattr(after, field) for field in
               ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")):
            raise ValueError("Tool target file was replaced or changed during read")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != declared[1]:
            raise ValueError("Tool input SHA256 drift")
        text = raw.decode("utf-8", errors="strict")
        return {"path": target, "sha256": digest, "text": text}

    definition = ToolDefinition(
        name="entry-api-bridge",
        description="Read the single explicitly approved synthetic input by its exact Task pin.",
        input_schema={"type": "object", "properties": {
            "path": {"type": "string", "enum": [target]}},
            "required": ["path"], "additionalProperties": False},
        # Closed client-side validation does not claim remote strict support.
        strict=False,
    )
    return ClientTool(definition, lookup, side_effect="read-only")


__all__ = ["create_synthetic_lookup"]
