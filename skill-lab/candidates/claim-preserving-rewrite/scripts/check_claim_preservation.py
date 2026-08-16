#!/usr/bin/env python3
"""Conservatively check surface invariants across a scientific rewrite."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


NUMBER = re.compile(
    r"(?<![A-Za-z0-9_])[-+]?(?:(?:\d+(?:[.,]\d+)?)|(?:\.\d+))(?:[eE][-+]?\d+)?%?"
)
CITATION = re.compile(
    r"(?:https?://[^\s)\]}>]+|\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+|"
    r"\[(?:\d+\s*(?:[-,–]\s*\d+\s*)*)\]|"
    r"\([^()\n]{1,100}\b(?:19|20)\d{2}[a-z]?\))",
    re.IGNORECASE,
)
NEGATION = re.compile(
    r"(?:未能|没有|并非|不能|不可|未|无|不|"
    r"\b(?:neither|nor|not|no|without|cannot|failed\s+to)\b)",
    re.IGNORECASE,
)
CAUSAL = re.compile(
    r"(?:导致|引起|造成|归因于|"
    r"\b(?:cause[ds]?|causing|led\s+to|leads?\s+to|results?\s+in|attribut(?:e|ed|es)\s+to)\b)",
    re.IGNORECASE,
)
STRENGTH_LEVELS = (
    re.compile(r"(?:可能|提示|一致|\b(?:may|might|could|suggests?|consistent\s+with)\b)", re.IGNORECASE),
    re.compile(r"(?:支持|表明|显示|\b(?:supports?|indicates?|shows?)\b)", re.IGNORECASE),
    re.compile(r"(?:证实|证明|确定|必然|\b(?:proves?|demonstrates?|establishes?|confirms?)\b)", re.IGNORECASE),
)


def _values(pattern: re.Pattern[str], text: str) -> Counter[str]:
    return Counter(match.group(0) for match in pattern.finditer(text))


def _strength(text: str) -> int:
    return max((level for level, pattern in enumerate(STRENGTH_LEVELS, 1) if pattern.search(text)), default=0)


def _result(code: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"code": code, "status": "pass" if passed else "fail", "detail": detail}


def _compare_counter(code: str, label: str, source: Counter[str], revision: Counter[str]) -> dict[str, Any]:
    if source == revision:
        return _result(code, True, f"{label} multiset preserved")
    removed = list((source - revision).elements())
    added = list((revision - source).elements())
    return _result(code, False, f"{label} drift: removed={removed!r} added={added!r}")


def _string_list(value: object, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    return value


def load_lock(path: Path | None) -> dict[str, list[str]]:
    if path is None:
        return {"protected_exact": [], "forbidden_in_revision": []}
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("lock must be a JSON object")
    unknown = set(value) - {"protected_exact", "forbidden_in_revision"}
    if unknown:
        raise ValueError("unknown lock fields: " + ", ".join(sorted(unknown)))
    return {
        "protected_exact": _string_list(value.get("protected_exact"), "protected_exact"),
        "forbidden_in_revision": _string_list(value.get("forbidden_in_revision"), "forbidden_in_revision"),
    }


def check(source: str, revision: str, lock: dict[str, list[str]]) -> dict[str, Any]:
    checks = [
        _result("CLAIM-SOURCE-EMPTY", bool(source.strip()), "source must contain non-whitespace text"),
        _result("CLAIM-REVISION-EMPTY", bool(revision.strip()), "revision must contain non-whitespace text"),
        _compare_counter("CLAIM-NUMBER-DRIFT", "numeric expression", _values(NUMBER, source), _values(NUMBER, revision)),
        _compare_counter("CLAIM-CITATION-DRIFT", "citation locator", _values(CITATION, source), _values(CITATION, revision)),
        _compare_counter("CLAIM-POLARITY-DRIFT", "negation marker", _values(NEGATION, source), _values(NEGATION, revision)),
    ]
    source_strength = _strength(source)
    revision_strength = _strength(revision)
    checks.append(
        _result(
            "CLAIM-STRENGTHENED",
            revision_strength <= source_strength,
            f"evidence-strength level source={source_strength} revision={revision_strength}",
        )
    )
    introduced_causal = list((_values(CAUSAL, revision) - _values(CAUSAL, source)).elements())
    checks.append(
        _result(
            "CLAIM-CAUSALITY-INTRODUCED",
            not introduced_causal,
            "no new causal markers" if not introduced_causal else f"new causal markers={introduced_causal!r}",
        )
    )
    for value in lock["protected_exact"]:
        checks.append(
            _result(
                "CLAIM-PROTECTED-TERM",
                value in source and value in revision,
                f"protected exact term {value!r} must occur in source and revision",
            )
        )
    for value in lock["forbidden_in_revision"]:
        checks.append(
            _result(
                "CLAIM-FORBIDDEN-TERM",
                value not in revision,
                f"forbidden revision term {value!r} must be absent",
            )
        )
    valid = all(item["status"] == "pass" for item in checks)
    return {
        "valid": valid,
        "checks": checks,
        "scope": "surface invariants only; scientific and semantic equivalence require human review",
    }


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_ref(path: Path, root: Path) -> dict[str, str]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"formal report subject is outside --root: {path}") from exc
    return {"path": relative, "sha256": _hash_file(resolved)}


def formal_report(
    report: dict[str, Any],
    *,
    source_path: Path,
    revision_path: Path,
    lock_path: Path | None,
    root: Path,
    report_id: str | None,
) -> dict[str, Any]:
    checker_path = Path(__file__).resolve()
    subject_paths = [source_path, revision_path]
    if lock_path is not None:
        subject_paths.append(lock_path)
    subjects = [_file_ref(path, root) for path in subject_paths]
    checker_ref = _file_ref(checker_path, root)
    if report_id is None:
        identity = "|".join(
            [checker_ref["sha256"], *(subject["sha256"] for subject in subjects)]
        ).encode("utf-8")
        report_id = "DCR-" + hashlib.sha256(identity).hexdigest()[:16]
    return {
        "schema_version": "0.1.0",
        "report_id": report_id,
        "checker": {
            "checker_id": "claim-preservation-surface-check",
            "version": "0.1.0",
            "source_ref": checker_ref,
        },
        "subject_refs": subjects,
        "status": "pass" if report["valid"] else "fail",
        "checks": report["checks"],
        "scope": report["scope"],
        "limitations": [
            "A pass checks surface invariants only and does not establish semantic or scientific equivalence."
        ],
    }


def main(argv: Iterable[str] | None = None) -> int:
    # Report text (including JSON with non-ASCII details) must not depend on the
    # host locale: parents capture pipes with their own default encoding.
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("revision")
    parser.add_argument("--lock")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--report-id")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    if args.output and args.json:
        parser.error("--output and --json are mutually exclusive")
    if (args.root or args.report_id) and not args.output:
        parser.error("--root and --report-id are only valid with --output")
    if args.output and not args.root:
        parser.error("--output requires --root")
    source_path = Path(args.source)
    revision_path = Path(args.revision)
    lock_path = Path(args.lock) if args.lock else None
    source = source_path.read_text(encoding="utf-8-sig")
    revision = revision_path.read_text(encoding="utf-8-sig")
    report = check(source, revision, load_lock(lock_path))
    if args.output:
        persisted = formal_report(
            report,
            source_path=source_path,
            revision_path=revision_path,
            lock_path=lock_path,
            root=Path(args.root),
            report_id=args.report_id,
        )
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(persisted, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"claim preservation report written: status={persisted['status']} output={output}")
    elif args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for item in report["checks"]:
            if item["status"] == "fail":
                print(f"ERROR {item['code']} {item['detail']}")
        if report["valid"]:
            print("OK surface claim locks preserved; scientific and semantic equivalence were not evaluated")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
