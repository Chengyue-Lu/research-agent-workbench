"""Deterministic, dormant release projection from independently pinned Git inputs.

This command writes an empty staging directory or checks a candidate commit. It
does not create branches, commits, tags, remote actions, or merge authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
POLICY = ".github/release-surface.yml"
TOOL = ".github/scripts/release_surface.py"
MANIFEST = "RELEASE_MANIFEST.json"
SCHEMAS = {
    "policy": "schemas/v0.1.0/release-surface-policy.schema.json",
    "manifest": "schemas/v0.1.0/release-manifest.schema.json",
}
VERSION = "1.0.0"
OID = r"[0-9a-f]{40}"
REQUIRED_CHECKS = ["governance", "test (3.11)", "test (3.13)"]


class ReleaseError(ValueError):
    """A deterministic release prerequisite failed closed."""


def require(condition: Any, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse(data: bytes) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseError("expected strict UTF-8 JSON (the policy uses the JSON subset of YAML)") from exc


def validate(kind: str, value: Any, *, definition: str | None = None) -> None:
    schema = parse((ROOT / SCHEMAS[kind]).read_bytes())
    if definition:
        schema = {**schema, "$ref": f"#/$defs/{definition}"}
        # The referenced definition, not the manifest root, is the input contract.
        schema.pop("required", None)
        schema.pop("properties", None)
        schema.pop("additionalProperties", None)
    error = next(Draft202012Validator(schema).iter_errors(value), None)
    require(error is None, f"{kind} schema: {error.message if error else ''}")


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_NO_REPLACE_OBJECTS="1", GIT_TERMINAL_PROMPT="0")
    if env:
        environment.update(env)
    result = subprocess.run(["git", "-C", str(repo), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, env=environment, check=False)
    require(result.returncode == 0, f"Git {args[0]} failed")
    return result.stdout


def portable(path: str) -> str:
    require(bool(path) and not path.startswith("/") and "\\" not in path,
            f"non-relative POSIX path: {path!r}")
    require(unicodedata.normalize("NFC", path) == path, f"non-NFC path: {path!r}")
    for part in path.split("/"):
        require(part not in ("", ".", "..") and not part.endswith((".", " ")),
                f"ambiguous path: {path!r}")
        require(not re.search(r'[<>:"|?*\x00-\x1f\x7f]', part), f"unsafe path: {path!r}")
        name = part.split(".", 1)[0].casefold()
        require(name not in {".git", "con", "prn", "aux", "nul", "conin$", "conout$"}
                and not re.fullmatch(r"(?:com|lpt)[1-9¹²³]", name),
                f"reserved path: {path!r}")
        require(part.casefold() != ".git", f"Git administrative path: {path!r}")
    return path


def paths_unique(paths: list[str]) -> None:
    spellings: dict[str, str] = {}
    files = set(paths)
    require(len(paths) == len(files), "duplicate output path")
    for path in paths:
        portable(path)
        parts = path.split("/")
        for end in range(1, len(parts) + 1):
            prefix = "/".join(parts[:end])
            key = prefix.casefold()
            require(key not in spellings or spellings[key] == prefix, "casefold path collision")
            spellings[key] = prefix
            require(end == len(parts) or prefix not in files, "file/tree collision")


def entries(repo: Path, revision: str) -> dict[str, tuple[str, str]]:
    result = {}
    for record in git(repo, "ls-tree", "-rz", "--full-tree", revision).split(b"\0"):
        if not record:
            continue
        metadata, name = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode("ascii").split()
        require(kind == "blob" and mode in ("100644", "100755"), "symlink/gitlink/unsupported Git mode")
        try:
            path = name.decode("utf-8")
        except UnicodeError as exc:
            raise ReleaseError("Git path must be UTF-8") from exc
        result[path] = (mode, oid)
    paths_unique(list(result))
    return result


def blob(repo: Path, oid: str) -> bytes:
    data = git(repo, "cat-file", "blob", oid)
    require(object_id("blob", data) == oid, "Git blob integrity mismatch")
    return data


def object_id(kind: str, data: bytes) -> str:
    return hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()


def tree_id(files: dict[str, tuple[str, bytes]]) -> str:
    tree: dict = {}
    for path, (mode, data) in files.items():
        node = tree
        parts = path.split("/")
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = (mode, object_id("blob", data))

    def encode(node: dict) -> str:
        records = []
        for name, value in node.items():
            directory = isinstance(value, dict)
            mode, oid = ("40000", encode(value)) if directory else value
            records.append(((name + ("/" if directory else "")).encode("utf-8"),
                            mode.encode() + b" " + name.encode("utf-8") + b"\0" + bytes.fromhex(oid)))
        return object_id("tree", b"".join(record for _, record in sorted(records)))
    return encode(tree)


def policy_at(repo: Path, source: str, version: str, source_entries: dict) -> tuple[dict, bytes]:
    require(POLICY in source_entries, "source has no release surface policy")
    raw = blob(repo, source_entries[POLICY][1])
    policy = parse(raw)
    validate("policy", policy)
    versions = policy["policies"]
    identities = [item["version"] for item in versions]
    require(identities == sorted(set(identities), key=lambda v: tuple(map(int, v.split(".")))),
            "policy versions must be unique and increasing")
    by_version = {item["version"]: item for item in versions}
    require(version in by_version, "unknown policy version")
    # Every historical identity reachable from source must still be present with
    # exactly its original semantics, including identities on merged histories.
    history = git(repo, "log", "--full-history", "--format=%H", source, "--", POLICY).decode().splitlines()
    for commit in history:
        listing = git(repo, "ls-tree", commit, "--", POLICY).split()
        require(bool(listing), "release policy removed from source history")
        previous = parse(blob(repo, listing[2].decode()))
        validate("policy", previous)
        require(previous["policy_id"] == policy["policy_id"], "policy identity changed")
        for item in previous["policies"]:
            require(by_version.get(item["version"]) == item, "append-only policy version drift")
    return by_version[version], raw


def expectations(repo: Path, expected: dict) -> None:
    validate("manifest", expected, definition="expectations")
    require(git(repo, "rev-parse", "--show-object-format").strip() == b"sha1", "only SHA-1 Git repositories supported")
    require(git(repo, "rev-parse", "--is-shallow-repository").strip() == b"false", "complete source history required")
    require(not git(repo, "status", "--porcelain", "--untracked-files=all"), "dirty repository")
    remote = git(repo, "remote", "get-url", "origin").decode().strip()
    match = re.fullmatch(r"(?:https://github\.com/|git@github\.com:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?", remote)
    require(match and match[1].casefold() == expected["repository"].casefold(), "external repository mismatch")
    for key in ("source", "parent"):
        require(git(repo, "rev-parse", f"{expected[key]}^{{commit}}").decode().strip() == expected[key], "exact commit required")
    git(repo, "merge-base", "--is-ancestor", expected["source"], "refs/remotes/origin/develop")
    require(git(repo, "rev-parse", "refs/remotes/origin/main").decode().strip() == expected["parent"],
            "current main parent drift; regenerate")
    ci = expected["source_ci"]
    require(ci["repository"] == expected["repository"] and ci["sha"] == expected["source"], "CI source binding mismatch")
    require(sorted(ci["required_checks"]) == REQUIRED_CHECKS, "CI required-check closure mismatch")


def project(repo: Path, expected: dict) -> dict[str, tuple[str, bytes]]:
    """Recompute the complete output, never accepting candidate manifest claims."""
    expectations(repo, expected)
    source = expected["source"]
    listing = entries(repo, source)
    policy, policy_bytes = policy_at(repo, source, expected["policy_version"], listing)
    for path in (TOOL, *SCHEMAS.values()):
        require(path in listing and blob(repo, listing[path][1]) == (ROOT / path).read_bytes(),
                "source tool/schema differs from trusted checker")
    selected: set[str] = set()
    include_paths = []
    for include in policy["include"]:
        path = portable(include["path"])
        require(path not in ("registry", ".agents", ".codex"), "broad runtime/maintainer root inclusion")
        include_paths.append(path)
        matches = {name for name in listing if (name == path if include["kind"] == "file" else name.startswith(path + "/"))}
        require(matches and (include["kind"] != "tree" or path not in listing), "missing or ambiguous include")
        require(not selected.intersection(matches), "overlapping include")
        selected.update(matches)
    require(len(include_paths) == len(set(include_paths)), "duplicate include")
    require(".gitattributes" in selected, "byte-stability attributes must be explicitly included")
    require(MANIFEST not in selected, "manifest-last path cannot be source-derived")
    files: dict[str, tuple[str, bytes]] = {}
    outputs = []
    for path in sorted(selected):
        mode, oid = listing[path]
        data = blob(repo, oid)
        try:
            text = data.decode("utf-8") if b"\0" not in data else ""
        except UnicodeError:
            text = ""
        require("\r\n" not in text, "CRLF source text is not canonical LF")
        files[path] = mode, data
        outputs.append({"path": path, "origin": "source_blob", "mode": mode,
                        "blob": oid, "size": len(data), "sha256": digest(data)})
    generated_inputs = {"repository": expected["repository"], "source": source,
                        "parent": expected["parent"], "release_version": expected["release_version"],
                        "policy_version": expected["policy_version"], "policy_sha256": digest(policy_bytes)}
    for item in policy["generated"]:
        path = portable(item["path"])
        require(path not in files and path != MANIFEST, "generated/source/manifest overlap")
        inputs = {**generated_inputs, "label": item["label"]}
        data = canonical(inputs)
        files[path] = "100644", data
        outputs.append({"path": path, "origin": "generated", "mode": "100644",
                        "blob": object_id("blob", data), "size": len(data), "sha256": digest(data),
                        "generator": {"identity": "rwb-release-metadata", "version": VERSION,
                                      "path": TOOL, "sha256": digest((ROOT / TOOL).read_bytes()), "inputs": inputs}})
    paths_unique([*files, MANIFEST])
    manifest = {"schema_version": "0.1.0", "kind": "release_manifest", "expectations": expected,
                "source_tree": git(repo, "rev-parse", f"{source}^{{tree}}").decode().strip(),
                "parent_tree": git(repo, "rev-parse", f"{expected['parent']}^{{tree}}").decode().strip(),
                "policy": {"path": POLICY, "identity": "rwb-release-surface", "version": expected["policy_version"],
                           "sha256": digest(policy_bytes)},
                "excluded": sorted(set(listing) - selected),
                "outputs": sorted(outputs, key=lambda row: row["path"]),
                "manifest_rule": "manifest-last; closed tree includes these canonical bytes; no self hash"}
    validate("manifest", manifest)
    files[MANIFEST] = "100644", canonical(manifest)
    return files


def directory_files(directory: Path, expected: dict[str, tuple[str, bytes]]) -> dict[str, tuple[str, bytes]]:
    require(directory.is_dir(), "staging must be a real directory")
    no_links(directory)
    result = {}
    for base, dirs, names in os.walk(directory, followlinks=False):
        for name in dirs + names:
            path = Path(base) / name
            no_links(path)
            if name in dirs:
                prefix = path.relative_to(directory).as_posix() + "/"
                require(any(item.startswith(prefix) for item in expected), "unexpected staging directory")
        for name in names:
            path = Path(base) / name
            relative = path.relative_to(directory).as_posix()
            require(stat.S_ISREG(path.stat().st_mode), "staging special file forbidden")
            mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
            if os.name == "nt":
                # Windows cannot prove an executable bit; the candidate Git tree
                # is the authoritative mode check on that platform.
                mode = expected.get(relative, ("100644", b""))[0]
            result[relative] = mode, path.read_bytes()
    paths_unique(list(result))
    return result


def no_links(path: Path) -> None:
    for component in (path, *path.parents):
        require(not component.is_symlink() and not (
            getattr(component.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ), "staging link/junction forbidden")


def export(repo: Path, expected: dict, output: Path) -> dict:
    require(output.is_absolute(), "staging directory must be explicit and absolute")
    require(output.resolve() != repo.resolve() and repo.resolve() not in output.resolve().parents,
            "staging must be outside the source checkout")
    require(output.is_dir() and not any(output.iterdir()), "staging must already exist and be empty")
    no_links(output)
    files = project(repo, expected)
    for path, (mode, data) in files.items():
        target = output / path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(data)
        target.chmod(0o755 if mode == "100755" else 0o644)
    require(directory_files(output, files) == files, "staged projection differs after writing")
    return {"tree": tree_id(files), "manifest_sha256": digest(files[MANIFEST][1]),
            "files": len(files), "merge_eligible": False}


def check(repo: Path, expected: dict, candidate: str, *, directory: Path | None = None) -> dict:
    require(re.fullmatch(OID, candidate), "candidate must be an exact commit SHA")
    files = project(repo, expected)
    parents = git(repo, "rev-list", "--parents", "-n", "1", candidate).decode().split()
    require(parents == [candidate, expected["parent"]], "candidate must have exactly the expected current main parent")
    listing = entries(repo, candidate)
    require(set(listing) == set(files), "unexpected/missing/stale release output")
    candidate_manifest = blob(repo, listing[MANIFEST][1])
    parsed = parse(candidate_manifest)
    validate("manifest", parsed)
    require(canonical(parsed) == candidate_manifest, "manifest is not canonical JSON/LF")
    for path, (mode, data) in files.items():
        require(listing[path] == (mode, object_id("blob", data)), f"Git mode/blob drift: {path}")
        require(blob(repo, listing[path][1]) == data, f"source/generated byte drift: {path}")
    target = tree_id(files)
    require(git(repo, "rev-parse", f"{candidate}^{{tree}}").decode().strip() == target, "closed-tree mismatch")
    # Keep prospective-merge objects outside the caller's object database.
    objects = git(repo, "rev-parse", "--git-path", "objects").decode().strip()
    with tempfile.TemporaryDirectory(prefix="rwb-merge-") as temp:
        merged = git(repo, "merge-tree", "--write-tree", expected["parent"], candidate,
                     env={"GIT_OBJECT_DIRECTORY": temp,
                          "GIT_ALTERNATE_OBJECT_DIRECTORIES": str((repo / objects).resolve())})
    require(merged.decode().splitlines()[0] == target, "prospective merge-result differs from closed projection")
    if directory is not None:
        require(directory_files(directory, files) == files, "working projection byte/path/mode drift")
    return {"tree": target, "manifest_sha256": digest(candidate_manifest), "files": len(files),
            "merge_eligible": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("export", "check"))
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--expectations", type=Path, required=True,
                        help="trusted caller input, independent of candidate manifest")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--candidate")
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args(argv)
    try:
        expected = parse(args.expectations.read_bytes())
        if args.command == "export":
            require(args.output is not None and args.candidate is None and args.directory is None,
                    "export requires --output only")
            result = export(args.repo, expected, args.output)
        else:
            require(args.candidate is not None and args.output is None, "check requires --candidate")
            result = check(args.repo, expected, args.candidate, directory=args.directory)
        print(canonical(result).decode(), end="")
        return 0
    except (ReleaseError, OSError) as exc:
        print(f"release-surface: BLOCK: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
