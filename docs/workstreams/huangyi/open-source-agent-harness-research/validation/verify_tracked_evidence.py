from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


VALIDATION_ROOT = Path(__file__).resolve().parent
ATTEMPT = VALIDATION_ROOT / "attempts" / "A-20260823-CODEX-READONLY-05"
FIXTURES = VALIDATION_ROOT / "fixtures" / "codex"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def tracked_hashes() -> dict[str, str]:
    entries: dict[str, str] = {}
    for line in (ATTEMPT / "HASHES.sha256").read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        if not SHA256_RE.fullmatch(digest):
            raise AssertionError(f"invalid SHA-256: {digest}")
        if relative in entries:
            raise AssertionError(f"duplicate hash path: {relative}")
        entries[relative] = digest
    return entries


def main() -> None:
    hashes = tracked_hashes()
    sanitized_names = {
        "command-results.json",
        "protocol-summary.json",
        "schema-summary.json",
    }
    for name in sanitized_names:
        relative = f"sanitized/{name}"
        path = ATTEMPT / relative
        assert path.is_file(), f"missing canonical sanitized evidence: {relative}"
        assert sha256(path) == hashes[relative], f"hash mismatch: {relative}"

    fixture_names = {
        "command-results.json": "codex-app-server-command-results.v1.json",
        "protocol-summary.json": "codex-app-server-protocol-summary.v1.json",
        "schema-summary.json": "codex-app-server-schema-summary.v1.json",
    }
    for source_name, fixture_name in fixture_names.items():
        source = ATTEMPT / "sanitized" / source_name
        fixture = FIXTURES / fixture_name
        assert fixture.is_file(), f"missing public fixture: {fixture_name}"
        assert source.read_bytes() == fixture.read_bytes(), (
            f"public fixture differs from canonical sanitized source: {fixture_name}"
        )

    schema = load_json(ATTEMPT / "sanitized" / "schema-summary.json")
    assert schema["schema"] == "rwb.codex-app-server-schema-summary.v1"
    assert schema["stable_method_count"] == 181
    assert schema["experimental_method_count"] == 237
    experimental_only = schema["experimental_only_methods"]
    assert isinstance(experimental_only, list) and len(experimental_only) == 56
    assert "server/diagnostics" in experimental_only
    for bundle in schema["bundles"]:
        assert SHA256_RE.fullmatch(bundle["manifest_sha256"])
        assert bundle["file_count"] > 0
        assert bundle["total_bytes"] > 0

    protocol = load_json(ATTEMPT / "sanitized" / "protocol-summary.json")
    assert protocol["schema"] == "rwb.codex-app-server-readonly-probe.v1"
    safety = protocol["safety"]
    for field in (
        "model_requests_sent",
        "thread_methods_sent",
        "turn_methods_sent",
        "tool_methods_sent",
    ):
        assert safety[field] == 0
    assert safety["os_network_block_proven"] is False
    assert safety["external_write_absence_proven"] is False
    assert protocol["preinitialize"]["error_message"] == "Not initialized"
    assert protocol["handshake"]["codex_home_matches_isolated_root"] is True
    assert protocol["handshake"]["duplicate_initialize_error"] == "Already initialized"
    assert protocol["handshake"]["unknown_method_error_class"] == "unknown-variant"
    assert protocol["experimental_gate"]["gate_error"] == (
        "server/diagnostics requires experimentalApi capability"
    )
    for scenario in (
        protocol["preinitialize"],
        protocol["handshake"],
        protocol["experimental_gate"],
    ):
        assert scenario["observed_non_loopback_remote_count"] == 0
        assert scenario["exit_code"] == 0

    command_results = json.loads(
        (ATTEMPT / "sanitized" / "command-results.json").read_text(encoding="utf-8")
    )
    assert isinstance(command_results, list) and len(command_results) == 2
    assert [item["scenario"] for item in command_results] == [
        "schema-stable",
        "schema-experimental",
    ]
    assert all(item["exit_code"] == 0 for item in command_results)


if __name__ == "__main__":
    main()
    print("tracked Codex evidence verification: PASS")
