"""Conservative, immutable base/head consumer graph for selective CI.

Imports and literal repository references are edges. Opaque execution and resource
access are explicit conservative edges, never evidence that a consumer is unrelated.
The graph is an additive supplement to the reviewed base-side contract groups.
"""
from __future__ import annotations

import ast
import copy
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import PurePosixPath
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


def function_body_only(before, after):
    """A reviewed local contract cannot hide initialization or dependency changes.

    Keep definitions, imports, bindings, call expressions and string/resource inputs
    fixed. This deliberately accepts a smaller domain than arbitrary function edits.
    Unknown execution in a changed function retains the ordinary consumer closure.
    """
    trees = [ast.parse(raw) for raw in (before, after)]
    bodies = []
    for tree in trees:
        functions = {}
        def strip(nodes, prefix=''):
            for node in nodes:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = prefix + node.name
                    if key in functions:
                        return False
                    functions[key] = copy.deepcopy(node)
                    node.body = [ast.Pass()]
                elif isinstance(node, ast.ClassDef):
                    if not strip(node.body, prefix + node.name + '.'):
                        return False
            return True
        if not strip(tree.body):
            return False
        bodies.append(functions)
    if ast.dump(trees[0]) != ast.dump(trees[1]):
        return False
    for name, old in bodies[0].items():
        new = bodies[1][name]
        if ast.dump(old) == ast.dump(new):
            continue
        def boundary(node):
            return sorted(ast.dump(part) for part in ast.walk(node)
                          if isinstance(part, (ast.Call, ast.Import, ast.ImportFrom, ast.Name,
                                               ast.Global, ast.Nonlocal, ast.Attribute))
                          or isinstance(part, ast.Constant) and isinstance(part.value, str))
        if boundary(old) != boundary(new):
            return False
        for context, node in zip(trees, (old, new)):
            # Keep module/class imports and capability bindings when analyzing the
            # changed body. A detached function loses aliases such as child.run.
            scoped = ast.Module(body=[*context.body, node], type_ignores=[])
            if graph({'subject.py': ast.unparse(scoped).encode()}, {'subject.py'})[1]:
                return False
    return True


def graph(blobs, paths):
    modules = defaultdict(set)
    for path in blobs:
        modules[module_name(path)].add(path)
        if path.startswith('tests/'):
            modules[module_name(path).removeprefix('tests.')].add(path)
    reverse = defaultdict(set)
    references = defaultdict(set)
    for dependency in paths:
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
        @lru_cache(maxsize=None)
        def scope(node):
            while node in parents:
                node = parents[node]
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                    break
            return node

        bindings = defaultdict(lambda: defaultdict(list))
        import_targets = defaultdict(set)
        mutated_names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                mutated_names.update(node.names)
            if isinstance(node, ast.ImportFrom):
                for item in node.names:
                    import_targets[item.asname or item.name].add(str(node.module) + '.' + item.name)
            elif isinstance(node, ast.Import):
                for item in node.names:
                    import_targets[item.asname or item.name.split('.')[0]].add(item.name)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                parent = parents[node]
                bindings[scope(node)][node.id].append(parent.value if isinstance(parent, ast.Assign) else None)

        def value_of(node):
            values = bindings[scope(node)].get(node.id, []) if isinstance(node, ast.Name) else []
            return values[0] if len(values) == 1 else None

        def parameter(node, name):
            owner = scope(node)
            return isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and any(
                arg.arg == name for arg in (*owner.args.posonlyargs, *owner.args.args, *owner.args.kwonlyargs,
                                           *([owner.args.vararg] if owner.args.vararg else []),
                                           *([owner.args.kwarg] if owner.args.kwarg else [])))

        @lru_cache(maxsize=None)
        def lexical_values(node):
            """A nearer binding or an exported mutation prevents a fixed-root claim."""
            if node.id in mutated_names:
                return [None]
            owner = scope(node)
            while True:
                if bindings[owner].get(node.id):
                    return bindings[owner][node.id]
                if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    if any(arg.arg == node.id for arg in (*owner.args.posonlyargs, *owner.args.args,
                                                         *owner.args.kwonlyargs)):
                        return [None]
                    if any(arg is not None and arg.arg == node.id for arg in (owner.args.vararg, owner.args.kwarg)):
                        return [None]
                if owner is tree:
                    return []
                owner = scope(owner)
                # Method free variables do not resolve through the class namespace.
                while isinstance(owner, ast.ClassDef):
                    owner = scope(owner)

        def path_constructor(node):
            return (isinstance(node, ast.Name) and aliases.get(node.id) == 'pathlib.Path'
                    and import_targets[node.id] == {'pathlib.Path'}
                    and not lexical_values(node)
                    and not parameter(node, node.id))

        def literal_path(node, seen=frozenset()):
            """Resolve fixed pathlib roots from syntax; unknown roots stay unknown."""
            if node in seen:
                return None
            seen = seen | {node}
            if isinstance(node, ast.Name):
                if (node.id == '__file__' and not parameter(node, node.id)
                        and not lexical_values(node)):
                    return PurePosixPath(path)
                if parameter(node, node.id):
                    return None
                values = lexical_values(node)
                if len(values) == 1 and values[0] is not None:
                    return literal_path(values[0], seen)
            if isinstance(node, ast.Call):
                if path_constructor(node.func) and len(node.args) == 1:
                    return literal_path(node.args[0], seen)
                if isinstance(node.func, ast.Attribute) and node.func.attr in {'resolve', 'absolute'}:
                    return literal_path(node.func.value, seen)
            if isinstance(node, ast.Attribute) and node.attr == 'parent':
                value = literal_path(node.value, seen)
                return value.parent if value is not None and value != PurePosixPath('.') else None
            if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == 'parents'
                    and isinstance(node.slice, ast.Constant) and type(node.slice.value) is int):
                value = literal_path(node.value.value, seen)
                if value is not None and 0 <= node.slice.value < len(value.parents):
                    return value.parents[node.slice.value]
            return None

        def path_value(node, seen=frozenset()):
            if node in seen:
                return False
            seen = seen | {node}
            if isinstance(node, ast.Name):
                value = value_of(node)
                if value is not None:
                    return path_value(value, seen)
                owner = scope(node)
                if isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.id not in bindings[owner]:
                    return any(arg.arg == node.id and path_constructor(arg.annotation) for arg in
                               (*owner.args.posonlyargs, *owner.args.args, *owner.args.kwonlyargs))
            if isinstance(node, ast.Call):
                if path_constructor(node.func):
                    return True
                if isinstance(node.func, ast.Attribute) and node.func.attr in {'resolve', 'absolute'}:
                    return path_value(node.func.value, seen)
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                return path_value(node.left, seen)
            if isinstance(node, ast.IfExp):
                return path_value(node.body, seen) and path_value(node.orelse, seen)
            return False

        def name_only(node, seen=frozenset()):
            """Recognize lexical predicates, without crossing a read/call boundary."""
            if node in seen:
                return False
            seen = seen | {node}
            parent = parents.get(node)
            while isinstance(parent, (ast.Set, ast.List, ast.Tuple, ast.BinOp)):
                node, parent = parent, parents.get(parent)
            if isinstance(parent, (ast.Compare, ast.Expr)):
                return True
            if isinstance(parent, ast.Assign) and len(parent.targets) == 1:
                target = parent.targets[0]
                owner = scope(parent)
                if isinstance(target, ast.Name) and isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if any(isinstance(n, (ast.Global, ast.Nonlocal)) and target.id in n.names for n in ast.walk(owner)):
                        return False
                    uses = [n for n in ast.walk(owner) if isinstance(n, ast.Name)
                            and isinstance(n.ctx, ast.Load) and n.id == target.id]
                    if uses and all(scope(n) is owner and name_only(n, seen) for n in uses):
                        return True
            if isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute):
                receiver = parent.func.value
                if parent.func.attr in {'isdisjoint', 'issubset', 'issuperset'}:
                    return isinstance(receiver, ast.Set) or isinstance(value_of(receiver), (ast.Set, ast.SetComp))
                if parent.func.attr == 'is_relative_to':
                    # pathlib's lexical containment query never inspects the directory.
                    return path_value(receiver)
            return False

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
                parent = parents.get(node)
                if name_only(node) or isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div):
                    continue
                value = node.value.replace('\\', '/')
                link(value)
                # Whole path expressions are handled below. A bare filename with
                # an unresolved use remains ambiguous, including assignment and
                # helper-call inputs; do not silently assume the repository root.
                matches = {value} & set(paths)
                matches.update(references.get(value, ()))
                for dependency in matches:
                    reverse[dependency].add(path)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                parent = parents.get(node)
                if isinstance(parent, ast.BinOp) and isinstance(parent.op, ast.Div):
                    continue
                if name_only(node):
                    continue
                parts = path_parts(node)
                root_node = node
                while isinstance(root_node, ast.BinOp) and isinstance(root_node.op, ast.Div):
                    root_node = root_node.left
                resolved = literal_path(root_node)
                if parts and parts[0] is None:
                    parts = parts[1:]
                prefix = []
                for part in parts:
                    if part is None:
                        break
                    prefix.append(part)
                value = '/'.join(prefix).replace('\\', '/').strip('/')
                if value and resolved is not None:
                    value = (resolved / value).as_posix()
                if value:
                    for dependency in paths:
                        if dependency == value or dependency.startswith(value + '/'):
                            reverse[dependency].add(path)
                if not value or resolved is None:
                    # An unresolved leading segment must not hide a known suffix.
                    for part in parts:
                        for dependency in references.get(part, ()):
                            reverse[dependency].add(path)

        def call_name(node):
            if isinstance(node, ast.Name):
                return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute):
                return call_name(node.value) + '.' + node.attr
            return ''

        for node in ast.walk(tree):
            if isinstance(node, (ast.Name, ast.Attribute)):
                name = call_name(node)
                if name in {'importlib', 'subprocess', 'runpy', 'builtins', 'os'} and not isinstance(parents.get(node), ast.Attribute):
                    # A namespace stored/passed as a value can expose execution through
                    # later assignment/reflection. Keep its consumer without guessing aliases.
                    opaque.add(path)
                if (name in {'__import__', 'eval', 'exec', 'getattr', 'builtins.getattr',
                             'builtins.__import__', 'builtins.eval', 'builtins.exec',
                             'importlib.import_module', 'runpy.run_module', 'runpy.run_path'}
                        or name.startswith(('subprocess.', 'os.system', 'os.popen'))
                        or name.endswith(('.exec_module', '.spec_from_file_location'))):
                    parent = parents.get(node)
                    if not isinstance(parent, ast.Call) or parent.func is not node:
                        # Passing or binding an execution capability loses its argument
                        # boundary. Preserve that consumer even when later aliases vary.
                        opaque.add(path)
            if (isinstance(node, ast.Attribute) and node.attr in {'read_text', 'read_bytes', 'open', 'glob', 'rglob', 'iterdir'}) or (isinstance(node, ast.Name) and node.id == 'open'):
                resources.add(path)
            if not isinstance(node, ast.Call):
                continue
            name = call_name(node.func)
            if name in {'getattr', 'builtins.getattr'} and node.args:
                namespace = call_name(node.args[0])
                attribute = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else None
                if ((not namespace and attribute is None) or namespace.split('.')[0] in {'importlib', 'subprocess', 'runpy', 'builtins', 'os'}
                        or namespace.rsplit('.', 1)[-1] in {'loader', 'spec'}
                        or attribute in {'import_module', 'run_module', 'run_path', 'exec_module', 'spec_from_file_location',
                                         '__import__', 'eval', 'exec', 'run', 'Popen', 'system', 'popen'}):
                    # Reflection can store/pass a capability before calling it. Its
                    # consumer remains opaque without attempting points-to analysis.
                    opaque.add(path)
            if name in {'__import__', 'builtins.__import__', 'importlib.import_module', 'runpy.run_module', 'runpy.run_path'}:
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    link(node.args[0].value)
                else:
                    opaque.add(path)
            elif not name or name in {'eval', 'exec', 'builtins.eval', 'builtins.exec'} or name.startswith(('subprocess.', 'os.system', 'os.popen')):
                opaque.add(path)
            elif name.endswith(('.exec_module', '.spec_from_file_location')):
                opaque.add(path)
            if name.endswith(('.read_text', '.read_bytes', '.open', '.glob', '.rglob', '.iterdir')) or name == 'open':
                resources.add(path)
    return reverse, opaque, resources, errors


@lru_cache(maxsize=12)
def commit_graph(repo, commit):
    paths, blobs = snapshot(repo, commit)
    return graph(blobs, paths)


def test_evidence_closure(repo, commit, proof_names):
    """Follow known test-side implementation inputs without pinning production code."""
    paths, _ = snapshot(repo, commit)
    reverse, *_ = commit_graph(repo, commit)
    forward = defaultdict(set)
    for dependency, consumers in reverse.items():
        if dependency.startswith('tests/'):
            for consumer in consumers:
                forward[consumer].add(dependency)
    found = {'tests/' + name.split('.')[0] + '.py' for name in proof_names}
    pending = sorted(found)
    for path in pending:
        inputs = set(forward[path])
        if path.endswith('.py'):
            parts = path.split('/')
            # Package initializers execute even when the root uses an unqualified
            # test import. Namespace packages have no initializer to pin at this ref.
            inputs.update('/'.join(parts[:stop]) + '/__init__.py' for stop in range(1, len(parts))
                          if '/'.join(parts[:stop]) + '/__init__.py' in paths)
        for dependency in sorted(inputs - found):
            found.add(dependency)
            pending.append(dependency)
    return found


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
            'exclusion_reasons': {name: ('unchanged consumer covered by accepted base contract' if
                'tests/' + name + '.py' in bounded else 'outside base/head dependency closure')
                for name in sorted(set(inventory) - tests.keys())},
            'exclusion_reason': 'outside new dependency obligations or covered by reviewed contract boundary; base groups and explicit additions are applied separately',
            'opaque_consumers': sorted(opaque & trails.keys()), 'errors': sorted(set(errors)),
            'test_reachable_sources': sorted(reachable & set(seeds)),
            'affected_paths': sorted(trails)}, before, after, old, new
