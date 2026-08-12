from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

from research_workbench.capability.catalog import filter_candidates, load_candidates
from research_workbench.io import iter_documents, load_document
from research_workbench.validation.documents import Severity, load_and_validate


def _validate(args: argparse.Namespace) -> int:
    paths = iter_documents(args.paths)
    _, issues = load_and_validate(paths)
    for issue in issues:
        print(f"{issue.severity.upper():7} {issue.code:20} {issue.path}: {issue.message}")
    errors = sum(issue.severity == Severity.ERROR for issue in issues)
    warnings = sum(issue.severity == Severity.WARNING for issue in issues)
    print(f"validated={len(paths)} errors={errors} warnings={warnings}")
    return 1 if errors else 0


def _hash(args: argparse.Namespace) -> int:
    path = Path(args.path)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    print(f"sha256:{digest.hexdigest()}  {path}")
    return 0


def _skill_candidates(args: argparse.Namespace) -> int:
    candidates = filter_candidates(
        load_candidates(args.registry),
        status=args.status,
        mode=args.mode,
        capability=args.capability,
    )
    if args.json:
        print(json.dumps(candidates, ensure_ascii=False, indent=2))
        return 0
    print("candidate_id\tstatus\tkind\tcontext\tdecision")
    for candidate in candidates:
        print(
            f"{candidate['candidate_id']}\t{candidate['status']}\t{candidate['kind']}\t"
            f"{candidate['context_cost']}\t{candidate['decision']['action']}"
        )
    return 0


def _provider_list(args: argparse.Namespace) -> int:
    document = load_document(args.registry)
    providers = document.get("providers", [])
    if args.json:
        print(json.dumps(providers, ensure_ascii=False, indent=2))
        return 0
    print("provider\tapi_surface\tadapter_status")
    for provider in providers:
        print(f"{provider['provider']}\t{provider['api_surface']}\t{provider['adapter_status']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rwb", description="Research Agent Workbench utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="run deterministic document checks")
    validate.add_argument("paths", nargs="+", help="document files or directories")
    validate.set_defaults(handler=_validate)

    hash_parser = subparsers.add_parser("hash", help="calculate a SHA-256 content identifier")
    hash_parser.add_argument("path")
    hash_parser.set_defaults(handler=_hash)

    skills = subparsers.add_parser("skills", help="inspect the skill candidate registry")
    skill_subparsers = skills.add_subparsers(dest="skills_command", required=True)
    candidates = skill_subparsers.add_parser("candidates", help="list or filter candidates")
    candidates.add_argument("--registry", default="registry/skills/candidates.json")
    candidates.add_argument("--status")
    candidates.add_argument("--mode")
    candidates.add_argument("--capability")
    candidates.add_argument("--json", action="store_true")
    candidates.set_defaults(handler=_skill_candidates)

    providers = subparsers.add_parser("providers", help="inspect model provider baselines")
    provider_subparsers = providers.add_subparsers(dest="providers_command", required=True)
    provider_list = provider_subparsers.add_parser("list")
    provider_list.add_argument("--registry", default="registry/providers/capabilities.json")
    provider_list.add_argument("--json", action="store_true")
    provider_list.set_defaults(handler=_provider_list)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))
