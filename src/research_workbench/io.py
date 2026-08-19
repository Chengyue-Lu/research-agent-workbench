from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}


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
