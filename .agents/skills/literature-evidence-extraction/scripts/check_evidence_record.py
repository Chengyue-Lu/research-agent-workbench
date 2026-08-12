#!/usr/bin/env python3
"""Deterministically check one RWB Evidence object and an optional local source."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from research_workbench.io import load_document
from research_workbench.validation import SchemaCatalog


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record")
    parser.add_argument("--source")
    args = parser.parse_args()

    document = load_document(args.record)
    errors = SchemaCatalog().validate("research_object", document)
    if not isinstance(document, dict) or document.get("object_type") != "evidence":
        print("ERROR OBJECT-NOT-EVIDENCE")
        return 1
    if errors:
        for error in errors:
            print(f"ERROR SCHEMA-INVALID {error.pointer}: {error.message}")
        return 1
    if not str(document.get("locator", "")).strip():
        print("ERROR EVIDENCE-LOCATOR-MISSING")
        return 1
    if args.source:
        source = Path(args.source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        expected = str(document["content_hash"]).removeprefix("sha256:").lower()
        if digest != expected:
            print(f"ERROR EVIDENCE-SOURCE-HASH expected={expected} actual={digest}")
            return 1
    print("OK structural evidence checks passed; scientific correctness was not evaluated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
