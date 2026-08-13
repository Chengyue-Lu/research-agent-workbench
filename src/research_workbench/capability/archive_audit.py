"""Read-only static audit for Skill packages inside a ZIP archive.

The scanner never extracts files, imports modules, executes scripts, resolves
URLs, or expands environment variables. Findings are conservative signals,
not proof that code is safe or malicious.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

import yaml

from research_workbench.capability.catalog import load_candidates


MAX_ARCHIVE_ENTRIES = 10_000
MAX_ARCHIVE_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_TEXT_ENTRY_BYTES = 2 * 1024 * 1024
MAX_TOTAL_TEXT_BYTES = 32 * 1024 * 1024
MAX_REPORTED_PATHS = 20

TEXT_SUFFIXES = frozenset(
    {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".py", ".ps1", ".sh", ".bat", ".cmd", ".js", ".ts"}
)
SCRIPT_SUFFIXES = frozenset({".py", ".ps1", ".sh", ".bat", ".cmd", ".js", ".ts"})
BINARY_SUFFIXES = frozenset({".exe", ".dll", ".so", ".dylib", ".jar", ".whl", ".bin"})


@dataclass(frozen=True, slots=True)
class ScanRule:
    rule_id: str
    severity: str
    pattern: re.Pattern[str]


RULES = (
    ScanRule("plaintext-http", "high", re.compile(r"(?<!https:)http://", re.IGNORECASE)),
    ScanRule("credential-access", "high", re.compile(
        r"(?:os\.environ|os\.getenv|process\.env|\$env:|localStorage)[^\n]{0,100}(?:token|secret|api[_-]?key|bind[_-]?key)",
        re.IGNORECASE,
    )),
    ScanRule("credential-literal", "high", re.compile(
        r"(?:sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|Bearer\s+[A-Za-z0-9._-]{24,})"
    )),
    ScanRule("package-install", "high", re.compile(
        r"(?:python\s+-m\s+pip\s+install|\bpip(?:3)?\s+install|\bnpm\s+(?:install|i)\b|\bpnpm\s+(?:install|add)\b|\bapt(?:-get)?\s+install|\bwinget\s+install|\bbrew\s+install)",
        re.IGNORECASE,
    )),
    ScanRule("process-execution", "high", re.compile(
        r"(?:subprocess\.|os\.system\s*\(|child_process|Start-Process|Invoke-Expression|shell\s*=\s*True)",
        re.IGNORECASE,
    )),
    ScanRule("dynamic-code", "high", re.compile(r"(?<![A-Za-z0-9_])(?:eval|exec)\s*\(", re.IGNORECASE)),
    ScanRule("destructive-file-operation", "high", re.compile(
        r"(?:rm\s+-rf|Remove-Item[^\n]{0,80}-Recurse|shutil\.rmtree|os\.(?:remove|unlink)\s*\(|Path\([^\n]+\)\.unlink\s*\()",
        re.IGNORECASE,
    )),
    ScanRule("external-write", "high", re.compile(
        r"(?:requests\.(?:post|put|patch|delete)|method\s*=\s*['\"](?:POST|PUT|PATCH|DELETE)|\btopiclab\s+(?:topics|notifications)[^\n]{0,80}(?:reply|like|favorite|create))",
        re.IGNORECASE,
    )),
    ScanRule("network-client", "medium", re.compile(
        r"(?:requests\.(?:get|post|put|patch|delete)|urllib\.request|httpx\.|aiohttp\.|Invoke-WebRequest|\bcurl\b|\bwget\b)",
        re.IGNORECASE,
    )),
    ScanRule("external-url", "medium", re.compile(r"https?://", re.IGNORECASE)),
    ScanRule("hardcoded-model-or-provider", "medium", re.compile(
        r"(?:\bgpt-[A-Za-z0-9._-]+|\bclaude-[A-Za-z0-9._-]+|\bgemini-[A-Za-z0-9._-]+|\bqwen[A-Za-z0-9._-]*|openrouter|dashscope)",
        re.IGNORECASE,
    )),
    ScanRule("absolute-local-path", "medium", re.compile(
        r"(?:[A-Za-z]:[\\/](?:Users|home|tmp|var|opt|workspace)[\\/]|/(?:home|Users|tmp|var|opt|workspace)/)",
        re.IGNORECASE,
    )),
)


@dataclass(slots=True)
class SignalAccumulator:
    occurrences: dict[str, int] = field(default_factory=dict)
    paths: dict[str, set[str]] = field(default_factory=dict)

    def scan(self, path: str, text: str) -> None:
        for rule in RULES:
            count = sum(1 for _ in rule.pattern.finditer(text))
            if count:
                self.occurrences[rule.rule_id] = self.occurrences.get(rule.rule_id, 0) + count
                self.paths.setdefault(rule.rule_id, set()).add(path)

    def to_list(self) -> list[dict[str, object]]:
        by_id = {rule.rule_id: rule for rule in RULES}
        severity_order = {"high": 0, "medium": 1, "info": 2}
        result: list[dict[str, object]] = []
        for rule_id in sorted(
            self.occurrences,
            key=lambda item: (severity_order[by_id[item].severity], item),
        ):
            paths = sorted(self.paths.get(rule_id, set()))
            result.append(
                {
                    "rule_id": rule_id,
                    "severity": by_id[rule_id].severity,
                    "occurrences": self.occurrences[rule_id],
                    "file_paths": paths[:MAX_REPORTED_PATHS],
                    "paths_truncated": len(paths) > MAX_REPORTED_PATHS,
                }
            )
        return result


def audit_skill_archive(
    archive_path: str | Path,
    *,
    source_id: str,
    expected_sha256: str | None = None,
    candidate_registry: str | Path | None = None,
    generated_at: str | None = None,
) -> dict[str, object]:
    path = Path(archive_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if not source_id.strip():
        raise ValueError("source_id must be non-empty")
    archive_hash = _hash_file(path)
    if expected_sha256 is not None:
        expected = expected_sha256.removeprefix("sha256:").lower()
        if archive_hash != expected:
            raise ValueError(
                f"archive hash mismatch: expected={expected} actual={archive_hash}"
            )

    candidate_paths: set[str] = set()
    if candidate_registry is not None:
        candidate_paths = {
            str(item["source_path"])
            for item in load_candidates(candidate_registry)
            if item.get("source_id") == source_id and isinstance(item.get("source_path"), str)
        }

    with zipfile.ZipFile(path) as archive:
        all_infos = archive.infolist()
        infos = [info for info in all_infos if not info.is_dir()]
        if len(all_infos) > MAX_ARCHIVE_ENTRIES:
            raise ValueError(f"archive exceeds entry limit: {len(all_infos)}")
        total_uncompressed = sum(info.file_size for info in infos)
        if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise ValueError(
                f"archive exceeds uncompressed size limit: {total_uncompressed}"
            )
        skill_infos = sorted(
            (info for info in infos if PurePosixPath(info.filename).name == "SKILL.md"),
            key=lambda item: item.filename,
        )
        if not skill_infos:
            raise ValueError("archive contains no SKILL.md files")
        prefixes = {
            info.filename: info.filename[: -len("SKILL.md")]
            for info in skill_infos
        }
        unsafe_paths = sorted(info.filename for info in infos if not _safe_archive_path(info.filename))
        duplicate_paths = _duplicates(info.filename for info in infos)
        encrypted_paths = sorted(info.filename for info in infos if info.flag_bits & 0x1)
        symlink_paths = sorted(info.filename for info in infos if _is_symlink(info))

        archive_signals = SignalAccumulator()
        skill_signals = {info.filename: SignalAccumulator() for info in skill_infos}
        text_values: dict[str, str] = {}
        text_hashes: dict[str, str] = {}
        skipped_text_paths: list[str] = []
        scanned_text_bytes = 0
        for info in sorted(infos, key=lambda item: item.filename):
            if Path(info.filename).suffix.lower() not in TEXT_SUFFIXES:
                continue
            if info.file_size > MAX_TEXT_ENTRY_BYTES or scanned_text_bytes + info.file_size > MAX_TOTAL_TEXT_BYTES:
                skipped_text_paths.append(info.filename)
                continue
            data = _read_bounded(archive, info, MAX_TEXT_ENTRY_BYTES)
            scanned_text_bytes += len(data)
            text = data.decode("utf-8", errors="replace")
            text_values[info.filename] = text
            text_hashes[info.filename] = hashlib.sha256(data).hexdigest()
            archive_signals.scan(info.filename, text)
            for skill_path, prefix in prefixes.items():
                if info.filename.startswith(prefix):
                    skill_signals[skill_path].scan(info.filename, text)

        skill_records: list[dict[str, object]] = []
        archive_script_count = 0
        for skill_info in skill_infos:
            skill_path = skill_info.filename
            if skill_path not in text_values:
                raise ValueError(f"SKILL.md could not be scanned within text limits: {skill_path}")
            prefix = prefixes[skill_path]
            package_infos = [
                info for info in infos if info.filename.startswith(prefix) and info.filename != skill_path
            ]
            scripts = sorted(
                info.filename
                for info in package_infos
                if Path(info.filename).suffix.lower() in SCRIPT_SUFFIXES
            )
            binaries = sorted(
                info.filename
                for info in package_infos
                if Path(info.filename).suffix.lower() in BINARY_SUFFIXES
            )
            licenses = sorted(
                info.filename
                for info in package_infos
                if PurePosixPath(info.filename).name.lower().startswith(("license", "copying"))
            )
            archive_script_count += len(scripts)
            skill_bytes = skill_info.file_size
            skill_text = text_values[skill_path]
            declared_name, frontmatter_status = _frontmatter_name(skill_text)
            skill_records.append(
                {
                    "source_path": skill_path,
                    "declared_name": declared_name,
                    "frontmatter_status": frontmatter_status,
                    "content_hash": f"sha256:{text_hashes[skill_path]}",
                    "instruction_bytes": skill_bytes,
                    "instruction_lines": len(skill_text.splitlines()),
                    "context_cost_estimate": _context_cost(skill_bytes),
                    "package_file_count": len(package_infos),
                    "script_file_count": len(scripts),
                    "script_paths_sample": scripts[:MAX_REPORTED_PATHS],
                    "script_paths_truncated": len(scripts) > MAX_REPORTED_PATHS,
                    "binary_file_count": len(binaries),
                    "binary_paths_sample": binaries[:MAX_REPORTED_PATHS],
                    "license_files": licenses[:MAX_REPORTED_PATHS],
                    "registered_candidate": skill_path in candidate_paths,
                    "signals": skill_signals[skill_path].to_list(),
                }
            )

    skill_paths = {str(item["source_path"]) for item in skill_records}
    unregistered = sorted(skill_paths - candidate_paths) if candidate_registry is not None else []
    stale_candidates = sorted(candidate_paths - skill_paths) if candidate_registry is not None else []
    timestamp = generated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "schema_version": "0.1.0",
        "report_id": f"SAA-{archive_hash[:16]}",
        "source_id": source_id,
        "generated_at": timestamp,
        "archive": {
            "name": path.name,
            "sha256": archive_hash,
            "size_bytes": path.stat().st_size,
        },
        "policy": {
            "mode": "read-only-static",
            "extracted": False,
            "executed": False,
            "network_used": False,
            "max_archive_entries": MAX_ARCHIVE_ENTRIES,
            "max_uncompressed_bytes": MAX_ARCHIVE_UNCOMPRESSED_BYTES,
            "max_text_entry_bytes": MAX_TEXT_ENTRY_BYTES,
            "max_total_text_bytes": MAX_TOTAL_TEXT_BYTES,
            "snippets_retained": False,
        },
        "summary": {
            "archive_entry_count": len(all_infos),
            "file_count": len(infos),
            "total_uncompressed_bytes": total_uncompressed,
            "skill_count": len(skill_records),
            "script_file_count": archive_script_count,
            "text_file_count_scanned": len(text_values),
            "text_bytes_scanned": scanned_text_bytes,
            "text_scan_complete": not skipped_text_paths,
            "registered_skill_count": len(skill_paths & candidate_paths),
            "unregistered_skill_count": len(unregistered),
        },
        "archive_integrity": {
            "unsafe_paths": unsafe_paths[:MAX_REPORTED_PATHS],
            "unsafe_paths_truncated": len(unsafe_paths) > MAX_REPORTED_PATHS,
            "duplicate_paths": duplicate_paths[:MAX_REPORTED_PATHS],
            "duplicate_paths_truncated": len(duplicate_paths) > MAX_REPORTED_PATHS,
            "encrypted_paths": encrypted_paths[:MAX_REPORTED_PATHS],
            "encrypted_paths_truncated": len(encrypted_paths) > MAX_REPORTED_PATHS,
            "symlink_paths": symlink_paths[:MAX_REPORTED_PATHS],
            "symlink_paths_truncated": len(symlink_paths) > MAX_REPORTED_PATHS,
            "skipped_text_paths": skipped_text_paths[:MAX_REPORTED_PATHS],
            "skipped_text_paths_truncated": len(skipped_text_paths) > MAX_REPORTED_PATHS,
        },
        "coverage": {
            "candidate_registry_checked": candidate_registry is not None,
            "unregistered_skill_paths": unregistered,
            "candidate_paths_missing_from_archive": stale_candidates,
        },
        "archive_signals": archive_signals.to_list(),
        "skills": skill_records,
        "limitations": [
            "Pattern matches are triage signals, not proof of malicious or safe behavior.",
            "No script, installer, command, network request, or imported module was executed.",
            "No file content or matched snippet is retained in this report.",
            "License presence is metadata only and still requires human legal review.",
            "Semantic method quality and incremental research value require separate evaluation.",
        ],
    }


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_bounded(archive: zipfile.ZipFile, info: zipfile.ZipInfo, limit: int) -> bytes:
    with archive.open(info, "r") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"archive entry exceeded read limit: {info.filename}")
    return data


def _safe_archive_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    return not path.is_absolute() and ".." not in path.parts and not re.match(r"^[A-Za-z]:", normalized)


def _duplicates(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        normalized = value.replace("\\", "/").casefold()
        if normalized in seen:
            duplicates.add(value)
        seen.add(normalized)
    return sorted(duplicates)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    unix_mode = (info.external_attr >> 16) & 0o170000
    return unix_mode == 0o120000


def _frontmatter_name(text: str) -> tuple[str | None, str]:
    if not text.startswith("---"):
        return None, "missing"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, "invalid"
    try:
        value = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, "invalid"
    if not isinstance(value, Mapping) or not isinstance(value.get("name"), str):
        return None, "invalid"
    return str(value["name"]), "parsed"


def _context_cost(instruction_bytes: int) -> str:
    if instruction_bytes <= 6 * 1024:
        return "low"
    if instruction_bytes <= 12 * 1024:
        return "medium"
    if instruction_bytes <= 24 * 1024:
        return "high"
    return "extreme"
