#!/usr/bin/env python3
"""Conservatively check surface invariants across a scientific rewrite."""

from __future__ import annotations

import argparse
import json
import re
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


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("revision")
    parser.add_argument("--lock")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    source = Path(args.source).read_text(encoding="utf-8-sig")
    revision = Path(args.revision).read_text(encoding="utf-8-sig")
    report = check(source, revision, load_lock(Path(args.lock) if args.lock else None))
    if args.json:
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
