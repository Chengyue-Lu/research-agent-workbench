from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml


SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}
_COPY_BUFFER_SIZE = 1024 * 1024


def _files_have_identical_bytes(left: Path, right: Path) -> bool:
    if left.stat().st_size != right.stat().st_size:
        return False
    with left.open("rb") as left_stream, right.open("rb") as right_stream:
        while True:
            left_block = left_stream.read(_COPY_BUFFER_SIZE)
            right_block = right_stream.read(_COPY_BUFFER_SIZE)
            if left_block != right_block:
                return False
            if not left_block:
                return True


def publish_staged_file_exclusive(
    staged_path: str | Path,
    final_path: str | Path,
    *,
    _link: Callable[[Path, Path], None] | None = None,
) -> bool:
    """Publish a same-volume staged file without replacing an existing target.

    Returns ``True`` when the hard link is created and ``False`` when the final
    path already contains identical bytes. A different existing target raises
    ``FileExistsError``. The staged path is never removed by this helper and
    must be treated as immutable until the caller removes it after closeout.

    This is a single-file process-crash safety primitive, not a multi-file or
    power-loss transaction. Cross-volume and unsupported hard-link operations
    fail closed; there is deliberately no copy or replace fallback.
    """

    staged = Path(staged_path)
    final = Path(final_path)
    if not staged.is_file():
        raise FileNotFoundError(staged)
    final.parent.mkdir(parents=True, exist_ok=True)
    link = _link or os.link
    try:
        link(staged, final)
    except FileExistsError as exc:
        if final.is_file() and _files_have_identical_bytes(staged, final):
            return False
        raise FileExistsError(
            exc.errno,
            f"refusing to overwrite existing file with different content: {final}",
            str(final),
        ) from exc
    return True


def write_text_exclusive(
    path: str | Path,
    content: str,
    *,
    _link: Callable[[Path, Path], None] | None = None,
) -> bool:
    """Flush text to a sibling temporary file, then publish it exclusively."""

    final = Path(path)
    final.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=final.parent,
            prefix=f".{final.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return publish_staged_file_exclusive(temporary_path, final, _link=_link)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_bytes_exclusive(
    path: str | Path,
    content: bytes,
    *,
    _link: Callable[[Path, Path], None] | None = None,
) -> bool:
    """Flush bytes to a sibling temporary file, then publish exclusively."""

    final = Path(path)
    final.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=final.parent,
            prefix=f".{final.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        return publish_staged_file_exclusive(temporary_path, final, _link=_link)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def write_yaml_exclusive(
    path: str | Path,
    document: Mapping[str, Any],
    *,
    _link: Callable[[Path, Path], None] | None = None,
) -> bool:
    """Serialize YAML and publish it with :func:`write_text_exclusive`."""

    content = yaml.safe_dump(dict(document), sort_keys=False, allow_unicode=True)
    return write_text_exclusive(path, content, _link=_link)


def load_document(path: str | Path) -> Any:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8") as stream:
        if file_path.suffix.lower() == ".json":
            return json.load(stream)
        if file_path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(stream)
    raise ValueError(f"unsupported document type: {file_path}")


def iter_documents(paths: list[str | Path]) -> list[Path]:
    found: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            found.extend(
                candidate
                for candidate in path.rglob("*")
                if candidate.is_file() and candidate.suffix.lower() in SUPPORTED_SUFFIXES
            )
        elif path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            found.append(path)
        else:
            raise FileNotFoundError(path)
    return sorted(set(found))
