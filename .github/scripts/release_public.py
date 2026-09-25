"""Check a candidate's public links, build inputs and internal-path closure as data.

The checker runs from a clean, exact accepted source checkout. It never executes
candidate code and its receipt does not authorize a release merge.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt
import release_surface as surface


ROOT = Path(__file__).resolve().parents[2]
TOOL = ".github/scripts/release_public.py"


PUBLIC_PAGES = (
    "README.md", "CHANGELOG.md", "docs/PROJECT_CHARTER.md", "docs/ARCHITECTURE.md",
    "docs/GETTING_STARTED.md", "docs/PUBLIC_GUIDE.md", "docs/SUPPORTED_FEATURES.md",
)
INTERNAL_PATH = re.compile(
    r"(?:^|[/\s`(])(?:TASKS\.md|STATUS\.md|ROADMAP\.md|DEVELOPMENT\.md|"
    r"DEVELOPMENT_HISTORY\.md|DEVELOP_TO_MAIN_RELEASE\.md|M_SERIES_IMPLEMENTATION_MAP\.md|"
    r"DEVELOPER_ARCHITECTURE_MAP\.md|workstreams/|history/|tests/)", re.I)
ARCHIVE_LINK = re.compile(r"(?:^|/)work(?:/|$)", re.I)
MILESTONE = re.compile(r"\b(?:M\d+-\d+|K-[A-Z0-9-]+)\b")


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
    markdown = MarkdownIt("gfm-like")
    for name, data in files.items():
        if not name.endswith(".md"):
            continue
        text = data.decode("utf-8")
        if INTERNAL_PATH.search(unquote(text)) or MILESTONE.search(text):
            errors.append(f"internal navigation or milestone: {name}")
        # Parse rendered href/src values: Markdown entities, references and URI
        # autolinks have link semantics; code spans/blocks remain literal text.
        # HTMLParser decodes rendered attribute entities once, before urlsplit.
        html = HtmlLinks()
        html.feed(markdown.render(text))
        for target in html.targets:
            parsed = urlsplit(target)
            if parsed.scheme in ("http", "https", "mailto") or parsed.netloc:
                if INTERNAL_PATH.search(unquote(parsed.path)) or ARCHIVE_LINK.search(unquote(parsed.path)):
                    errors.append(f"internal external link: {name} -> {target}")
                continue
            path = unquote(parsed.path)
            if parsed.scheme or path.startswith("/") or "\\" in path:
                errors.append(f"nonportable link: {name} -> {target}")
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), path)) if path else name
            if INTERNAL_PATH.search(resolved) or ARCHIVE_LINK.search(resolved):
                errors.append(f"internal link: {name} -> {target}")
                continue
            if resolved.startswith("../") or not (resolved in files or any(
                candidate.startswith(resolved.rstrip("/") + "/") for candidate in files
            )):
                errors.append(f"missing link: {name} -> {target}")
            elif parsed.fragment and resolved.endswith(".md") and resolved in files:
                if unquote(parsed.fragment) not in headings(files[resolved].decode("utf-8")):
                    errors.append(f"missing anchor: {name} -> {target}")
    return errors


def build_input_errors(files: dict[str, bytes]) -> list[str]:
    required = {"pyproject.toml", "MANIFEST.in", "README.md", "LICENSE", "build_backend.py", "runtime-resources.json"}
    if "runtime-resources.json" in files:
        spec = json.loads(files["runtime-resources.json"])
        for catalog in spec["catalogs"]:
            required.add(catalog["path"])
            if "entry_kind" in catalog and catalog["path"] in files:
                required.update(row["document_path"] for row in json.loads(files[catalog["path"]])["entries"])
        required.update(row["path"] for row in spec["release_assets"])
    return [f"missing build input: {name}" for name in sorted(required - files.keys())]


def candidate_files(root: Path, candidate: str) -> dict[str, bytes]:
    """Read Git blobs from the exact candidate commit, never its working tree."""
    surface.require(re.fullmatch(surface.OID, candidate), 'exact candidate SHA required')
    return {path: surface.blob(root, oid)
            for path, (_, oid) in surface.entries(root, candidate).items()}


def check(root: Path, repository: str, source: str, candidate: str) -> dict:
    surface.require(re.fullmatch(surface.OID, source), 'exact source SHA required')
    surface.require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository), 'repository required')
    surface.require(surface.git(root, 'rev-parse', 'HEAD').decode().strip() == source,
                    'checkout must be exact source')
    surface.require(surface.git(root, 'rev-parse', '--is-shallow-repository').strip() == b'false',
                    'complete source history required')
    surface.require(not surface.git(root, 'status', '--porcelain', '--untracked-files=all'),
                    'source checkout must be clean')
    remote = surface.git(root, 'remote', 'get-url', 'origin').decode().strip()
    surface.require(remote in (f'https://github.com/{repository}', f'https://github.com/{repository}.git',
                               f'git@github.com:{repository}.git'), 'source origin mismatch')
    for path in (TOOL, surface.TOOL):
        surface.require(surface.git(root, 'show', f'{source}:{path}') == (root / path).read_bytes(),
                        f'source checker byte drift: {path}')
    files = candidate_files(root, candidate)
    forbidden_roots = ('tests/', 'work/', 'docs/workstreams/', 'docs/history/', '.codex/', '.agents/')
    forbidden = [path for path in files if path.startswith(forbidden_roots)]
    errors = [f'internal candidate path: {path}' for path in forbidden]
    errors.extend(documentation_errors(files))
    errors.extend(build_input_errors(files))
    surface.require(not errors, '; '.join(errors))
    return {'repository': repository, 'source': source, 'candidate': candidate,
            'files_checked': len(files), 'public_pages': len(PUBLIC_PAGES),
            'documentation': 'success', 'build_inputs': 'success', 'merge_eligible': False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--source', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    surface.require(not args.output.exists(), 'output already exists')
    result = check(ROOT, args.repository, args.source, args.candidate)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'result': 'PASS', 'candidate': args.candidate, 'merge_eligible': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
