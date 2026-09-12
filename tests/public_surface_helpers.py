"""Development-side checks over the bytes selected for a public source tree."""
from __future__ import annotations

import json
import posixpath
import re
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


PUBLIC_PAGES = (
    "README.md", "CHANGELOG.md", "docs/PROJECT_CHARTER.md", "docs/ARCHITECTURE.md",
    "docs/GETTING_STARTED.md", "docs/PUBLIC_GUIDE.md", "docs/SUPPORTED_FEATURES.md",
)
INTERNAL_PATH = re.compile(
    r"(?:^|[/\s`(])(?:TASKS\.md|STATUS\.md|ROADMAP\.md|DEVELOPMENT\.md|"
    r"DEVELOPMENT_HISTORY\.md|DEVELOP_TO_MAIN_RELEASE\.md|M_SERIES_IMPLEMENTATION_MAP\.md|"
    r"DEVELOPER_ARCHITECTURE_MAP\.md|workstreams/|history/|work/[^`\s]+|tests/)", re.I)
MILESTONE = re.compile(r"\b(?:M\d+-\d+|K-[A-Z0-9-]+)\b")


def selected_files(root: Path) -> dict[str, bytes]:
    """Use Git's source set, including proposed untracked inputs, never ignored build output."""
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).decode().split("\0")
    policy = json.loads((root / ".github/release-surface.yml").read_bytes())["policies"][-1]
    selected = set()
    for entry in policy["include"]:
        matches = {name for name in names if name == entry["path"] or (
            entry["kind"] == "tree" and name.startswith(entry["path"] + "/"))}
        if not matches:
            raise ValueError(f"missing include: {entry['path']}")
        selected.update(matches)
    return {name: (root / name).read_bytes() for name in sorted(selected)}


class HtmlLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.targets = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if value is not None and key in ("href", "src"):
                self.targets.append(value)
            if value is not None and (key == "id" or (tag == "a" and key == "name")):
                self.anchors.add(value)


def headings(text: str) -> set[str]:
    html = HtmlLinks()
    html.feed(text)
    anchors = set(html.anchors)
    counts = {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        anchors.add(slug if not count else f"{slug}-{count}")
    return anchors


def documentation_errors(files: dict[str, bytes]) -> list[str]:
    errors = [f"missing public page: {name}" for name in PUBLIC_PAGES if name not in files]
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        text = data.decode("utf-8")
        if INTERNAL_PATH.search(unquote(text)) or MILESTONE.search(text):
            errors.append(f"internal navigation or milestone: {name}")
        # Fenced examples are inspected for internal-path leakage above, but are not links.
        rendered = re.sub(r"^(```|~~~).*?^\1[^\n]*$", "", text, flags=re.M | re.S)
        html = HtmlLinks()
        html.feed(rendered)
        definitions = {key.casefold(): target for key, target in re.findall(
            r"^\s*\[([^\]]+)\]:\s*<?([^\s>]+)>?", rendered, re.M)}
        targets = re.findall(r"\[[^\]]*\]\(\s*<?([^\s)>]+)>?(?:\s+[^)]*)?\)", rendered)
        targets.extend(html.targets)
        targets.extend(definitions.values())
        for label, key in re.findall(r"\[([^\]]+)\]\[([^\]]*)\]", rendered):
            if (key or label).casefold() not in definitions:
                errors.append(f"undefined reference: {name} -> {key or label}")
        for target in targets:
            parsed = urlsplit(target)
            if parsed.scheme in ("http", "https", "mailto") or parsed.netloc:
                if INTERNAL_PATH.search(unquote(parsed.path)):
                    errors.append(f"internal external link: {name} -> {target}")
                continue
            path = unquote(parsed.path)
            if parsed.scheme or path.startswith("/") or "\\" in path:
                errors.append(f"nonportable link: {name} -> {target}")
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), path)) if path else name
            if resolved.startswith("../") or not (resolved in files or any(
                candidate.startswith(resolved.rstrip("/") + "/") for candidate in files
            )):
                errors.append(f"missing link: {name} -> {target}")
            elif parsed.fragment and resolved.endswith(".md") and resolved in files:
                if unquote(parsed.fragment) not in headings(files[resolved].decode("utf-8")):
                    errors.append(f"missing anchor: {name} -> {target}")
    return errors


def build_input_errors(files: dict[str, bytes]) -> list[str]:
    required = {"pyproject.toml", "MANIFEST.in", "README.md", "build_backend.py", "runtime-resources.json"}
    if "runtime-resources.json" in files:
        spec = json.loads(files["runtime-resources.json"])
        for catalog in spec["catalogs"]:
            required.add(catalog["path"])
            if "entry_kind" in catalog and catalog["path"] in files:
                required.update(row["document_path"] for row in json.loads(files[catalog["path"]])["entries"])
        required.update(row["path"] for row in spec["release_assets"])
    return [f"missing build input: {name}" for name in sorted(required - files.keys())]
