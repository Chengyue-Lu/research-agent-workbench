"""Conservative, immutable base/head consumer graph for selective CI.

Imports and literal repository references are edges. Opaque execution and resource
access are explicit conservative edges, never evidence that a consumer is unrelated.
The graph is an additive supplement to the reviewed base-side contract groups.
"""
from __future__ import annotations

import ast
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
import subprocess


@lru_cache(maxsize=12)
def snapshot(repo, commit):
    command = ['git', '--no-replace-objects', '-C', str(repo)]
    listing = subprocess.run(command + ['ls-tree', '-r', '-z', commit], capture_output=True, check=True).stdout
    records = [row.split(b'\t', 1) for row in listing.split(b'\0') if row]
    paths = {path.decode(): meta.decode().split() for meta, path in records}
    python = sorted(path for path, meta in paths.items() if path.endswith('.py') and meta[0] in {'100644', '100755'})
    raw = subprocess.run(command + ['cat-file', '--batch'],
                         input=b''.join((paths[p][2] + '\n').encode() for p in python),
                         capture_output=True, check=True).stdout
    blobs, offset = {}, 0
    for path in python:
        end = raw.index(b'\n', offset)
        size = int(raw[offset:end].split()[-1])
        blobs[path] = raw[end + 1:end + 1 + size]
        offset = end + size + 2
    return paths, blobs


def module_name(path):
    name = path.removesuffix('.py').replace('/', '.')
    for prefix in ('src.', '.github.scripts.'):
        name = name.removeprefix(prefix)
    return name.removesuffix('.__init__')


def semantic(raw):
    """Ordinary comments/spacing do not change Python behavior; docstrings still do."""
    return ast.dump(ast.parse(raw), include_attributes=False)


def imports(raw):
    return sorted(ast.dump(node, include_attributes=False) for node in ast.walk(ast.parse(raw))
                  if isinstance(node, (ast.Import, ast.ImportFrom)))


def graph(blobs, paths):
    modules = defaultdict(set)
    for path in blobs:
        modules[module_name(path)].add(path)
        if path.startswith('tests/'):
            modules[module_name(path).removeprefix('tests.')].add(path)
    reverse = defaultdict(set)
    references = defaultdict(set)
    for dependency in paths:
        references[dependency].add(dependency)
        references[dependency.rsplit('/', 1)[-1]].add(dependency)
    opaque, resources, errors = set(), set(), []
    for path, raw in blobs.items():
        try:
            tree = ast.parse(raw)
        except (SyntaxError, UnicodeError):
            errors.append('unparseable Python dependency: ' + path)
            continue
        aliases = {}
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}

        def alias(name, target):
            if name in aliases and aliases[name] != target:
                opaque.add(path)
            aliases[name] = target

        def link(name):
            parts = name.split('.')
            for stop in range(1, len(parts) + 1):
                for dependency in modules.get('.'.join(parts[:stop]), ()):
                    if dependency != path:
                        reverse[dependency].add(path)

        def path_parts(node):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                return path_parts(node.left) + path_parts(node.right)
            return [node.value] if isinstance(node, ast.Constant) and isinstance(node.value, str) else [None]

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for item in node.names:
                    alias(item.asname or item.name.split('.')[0], item.name if item.asname else item.name.split('.')[0])
                    link(item.name)
            elif isinstance(node, ast.ImportFrom):
                package = module_name(path).split('.')
                if not path.endswith('/__init__.py'):
                    package.pop()
                prefix = '.'.join(package[:len(package) - node.level + 1]) if node.level else ''
                name = '.'.join(filter(None, (prefix, node.module)))
                link(name)
                for item in node.names:
                    full = name + '.' + item.name
                    alias(item.asname or item.name, full)
                    link(full)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.replace('\\', '/')
                link(value)
                # File literals are references. Dictionary keys such as 'tests' and
                # permission-zone names such as 'src' are not directory reads.
                for dependency in references.get(value.rstrip('/'), ()):
                    reverse[dependency].add(path)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                parent = parents.get(node)
                if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div):
                    continue
                parts = path_parts(node)
                while parts and parts[0] is None:
                    parts.pop(0)
                prefix = []
                for part in parts:
                    if part is None:
                        break
                    prefix.append(part)
                value = '/'.join(prefix).replace('\\', '/').strip('/')
                if value:
                    for dependency in paths:
                        if dependency == value or dependency.startswith(value + '/'):
                            reverse[dependency].add(path)

        def call_name(node):
            if isinstance(node, ast.Name):
                return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute):
                return call_name(node.value) + '.' + node.attr
            return ''

        for node in ast.walk(tree):
            if (isinstance(node, ast.Attribute) and node.attr in {'read_text', 'read_bytes', 'open', 'glob', 'rglob', 'iterdir'}) or (isinstance(node, ast.Name) and node.id == 'open'):
                resources.add(path)
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node.func)
            if name in {'__import__', 'importlib.import_module', 'runpy.run_module', 'runpy.run_path'}:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    link(node.args[0].value)
                else:
                    opaque.add(path)
            elif not name or name in {'eval', 'exec'} or name.startswith(('subprocess.', 'os.system', 'os.popen')):
                opaque.add(path)
            elif name.startswith('importlib.') and name.endswith(('exec_module', 'spec_from_file_location')):
                opaque.add(path)
            if name.endswith(('.read_text', '.read_bytes', '.open', '.glob', '.rglob', '.iterdir')) or name == 'open':
                resources.add(path)
    return reverse, opaque, resources, errors


@lru_cache(maxsize=12)
def commit_graph(repo, commit):
    paths, blobs = snapshot(repo, commit)
    return graph(blobs, paths)


def select(repo, base, head, seeds, reviewed_seeds=(), reviewed_consumers=(), reviewed_leaves=()):
    """Union old/new edges so removing an import or a consumer cannot hide impact."""
    before, old = snapshot(repo, base)
    after, new = snapshot(repo, head)
    reverse, opaque, resources, errors = defaultdict(set), set(), set(), []
    for commit in (base, head):
        edges, dynamic, readers, invalid = commit_graph(repo, commit)
        for dependency, consumers in edges.items():
            reverse[dependency].update(consumers)
        opaque.update(dynamic)
        resources.update(readers)
        errors.extend(invalid)
    forward = defaultdict(set)
    for dependency, consumers in reverse.items():
        for consumer in consumers:
            forward[consumer].add(dependency)
    reachable = {path for path in new if path.startswith('tests/test_')}
    pending = list(reachable)
    for consumer in pending:
        for dependency in forward[consumer] - reachable:
            reachable.add(dependency)
            pending.append(dependency)
    def walk(initial):
        trails = dict(initial)
        queue = list(trails)
        for path in queue:
            consumers = set(reverse[path])
            # Opaque execution consumes changed code, not every intermediate reader
            # of changed planner input data. The reviewed contract bounds old consumers.
            if path in seeds and path.endswith('.py') and not path.startswith('tests/test_'):
                consumers.update(opaque - set(reviewed_consumers) if path in reviewed_seeds else opaque)
            if not path.endswith(('.py', '.md')) and not path.startswith('work/'):
                consumers.update(resources)
            for consumer in sorted(consumers):
                if consumer not in trails:
                    trails[consumer] = trails[path] + [consumer]
                    queue.append(consumer)
        return trails

    trails = walk({path: [path] for path in sorted(set(seeds) - set(reviewed_seeds))})
    bounded = walk({path: [path] for path in sorted(reviewed_seeds)})
    # Old contract groups supply the complete reviewed consumer boundary. New or
    # changed consumers since its anchor add their whole downstream closure.
    additions = {p: chain for p, chain in bounded.items()
                 if p not in reviewed_consumers and p not in reviewed_leaves}
    trails.update(walk(additions))
    trails.update({p: [p] for p in reviewed_seeds})
    tests = {module_name(path).removeprefix('tests.'): chain for path, chain in trails.items()
             if path in new and path.startswith('tests/test_')}
    inventory = sorted(module_name(path).removeprefix('tests.') for path in new if path.startswith('tests/test_'))
    payload = json.dumps({'base': before, 'head': after}, sort_keys=True).encode()
    return {'algorithm': 'base-head-consumers-v1', 'inventory_sha256': hashlib.sha256(payload).hexdigest(),
            'selected': dict(sorted(tests.items())), 'excluded': sorted(set(inventory) - tests.keys()),
            'exclusion_reason': 'outside new dependency obligations or covered by reviewed contract boundary; base groups and explicit additions are applied separately',
            'opaque_consumers': sorted(opaque & trails.keys()), 'errors': sorted(set(errors)),
            'test_reachable_sources': sorted(reachable & set(seeds)),
            'affected_paths': sorted(trails)}, before, after, old, new
