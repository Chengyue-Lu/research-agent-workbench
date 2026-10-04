"""Bounded Provider source closure, independently compiled without archive execution."""
from __future__ import annotations

import ast
import builtins
import enum
import functools
import hashlib
import importlib
import dataclasses
import dis
import typing
import inspect
import json
import math
from pathlib import Path, PurePath, PurePosixPath
import re
import reprlib
import sys
import time
from types import CodeType, FunctionType, MappingProxyType

KIND = "provider_source_closure"
VERSION = "1.0.0"
POLICY = "provider-source-closure-v1"
MAX_MODULES = 160
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
TRUSTED_BOUNDARIES = (
    "Python compiler/runtime and native references are trusted; archived source is never executed.",
    "Dependency implementation, generated dataclass/Enum methods, and cache behavior are outside explicit source attestation.",
    "This document binds source/callable/policy state; it does not qualify credentials, remote APIs, Session/Tool/Windows execution or task authority.",
)


class SourceClosureError(ValueError):
    """A bounded source closure could not be independently validated."""


NATIVE = {"time.monotonic": time.monotonic}
LRU_TYPE = functools._lru_cache_wrapper


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def _module_name(name):
    if not isinstance(name, str) or not name or not all(part.isidentifier() for part in name.split(".")):
        raise SourceClosureError("invalid declared module name")
    return name


def _path_for(source_root, module):
    base = Path(source_root).joinpath(*_module_name(module).split("."))
    for path in (base.with_suffix(".py"), base / "__init__.py"):
        if path.is_file() and not path.is_symlink():
            return path.resolve()
    raise SourceClosureError("declared source module unavailable: " + module)


def _imports(module, tree, *, is_package, namespace):
    edges = set()
    aliases = {}
    parts = module.split(".")
    edges.update(".".join(parts[:i]) for i in range(1, len(parts)))
    package = module if is_package else module.rpartition(".")[0]
    def imported(node):
        if node.level:
            base = package.split(".")
            if node.level > len(base):
                raise SourceClosureError("relative import leaves declared package")
            target = ".".join(base[:len(base) - node.level + 1])
            return target + ("." + node.module if node.module else "")
        return node.module or ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name.split(".")[0] in namespace:
                    edges.add(item.name)
        elif isinstance(node, ast.ImportFrom):
            target = imported(node)
            if target.split(".")[0] in namespace:
                edges.add(target)
                if node.module is None:
                    edges.update(target + "." + item.name for item in node.names if item.name != "*")
    for node in tree.body:
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = (item.name if item.asname else item.name.split(".")[0], None)
        elif isinstance(node, ast.ImportFrom):
            target = imported(node)
            for item in node.names:
                if item.name == "*":
                    raise SourceClosureError("star imports are outside closed alias policy")
                if target != "__future__":
                    aliases[item.asname or item.name] = (target, item.name)
    return sorted(edges - {module}), aliases


def code_state(code):
    def constant(value):
        if isinstance(value, CodeType):
            return {"code": code_state(value)}
        if isinstance(value, bytes):
            return {"bytes": value.hex()}
        if isinstance(value, (tuple, frozenset)):
            values = [constant(item) for item in value]
            if isinstance(value, frozenset):
                values.sort(key=lambda item: json.dumps(item, sort_keys=True))
            return {type(value).__name__: values}
        if isinstance(value, float):
            return {"float": value.hex()}
        if isinstance(value, complex):
            return {"complex": [value.real.hex(), value.imag.hex()]}
        if value is Ellipsis:
            return {"ellipsis": True}
        if value is None or isinstance(value, (str, int, bool)):
            return value
        raise ValueError("unsupported code constant")
    fields = ("co_names", "co_varnames", "co_freevars", "co_cellvars", "co_argcount", "co_posonlyargcount",
              "co_kwonlyargcount", "co_nlocals", "co_stacksize", "co_flags", "co_name", "co_qualname",
              "co_firstlineno")
    return {**{name: getattr(code, name) for name in fields}, "bytecode": code.co_code.hex(),
            "constants": [constant(item) for item in code.co_consts],
            "linetable": code.co_linetable.hex(), "exceptiontable": code.co_exceptiontable.hex()}


def compiled_functions(raw):
    compiled = compile(raw, "<archived-source-not-executed>", "exec", dont_inherit=True, optimize=sys.flags.optimize)
    result = {}
    def walk(code):
        for child in code.co_consts:
            if isinstance(child, CodeType):
                if not child.co_name.startswith("<") and child.co_flags & inspect.CO_NEWLOCALS:
                    result[child.co_qualname] = digest(code_state(child))
                walk(child)
    walk(compiled)
    return result


class ClosedSource:
    def __init__(self, archive):
        self.archive = archive
        self.values = {}
        self.active = set()
        self.gaps = []

    def lookup(self, module, name, local=None):
        if local and name in local:
            return local[name]
        key = (module, name)
        if key in self.values:
            return self.values[key]
        if key in self.active:
            raise ValueError("recursive source value")
        self.active.add(key)
        try:
            item = self.archive[module]
            for node in item["tree"].body:
                targets = node.targets if isinstance(node, ast.Assign) else ([node.target] if isinstance(node, ast.AnnAssign) else [])
                if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                    result = self.evaluate(module, node.value, {})
                    self.values[key] = result
                    return result
                if isinstance(node, ast.ClassDef) and node.name == name:
                    return {"source_class": module + "." + name}
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
                    return CallableRef(module + "." + name)
            imported = item["aliases"].get(name)
            if imported:
                target, attr = imported
                if target in self.archive and attr is not None:
                    return self.lookup(target, attr)
                symbol = target + ("." + attr if attr else "")
                if symbol in NATIVE:
                    return NativeRef(symbol)
                if symbol == "functools._lru_cache_wrapper":
                    return ExternalRef(symbol)
                return {"external_ref": symbol}
            raise ValueError("undeclared source value")
        finally:
            self.active.remove(key)

    def evaluate(self, module, node, local):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, float) and not math.isfinite(node.value):
                raise ValueError("nonfinite source literal")
            if isinstance(node.value, str) and len(node.value) > MAX_SOURCE_BYTES:
                raise ValueError("literal text bound")
            if type(node.value) is int and node.value.bit_length() > 4096:
                raise ValueError("literal integer bound")
            return node.value
        if isinstance(node, ast.Name):
            return self.lookup(module, node.id, local)
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            values = [self.evaluate(module, item, local) for item in node.elts]
            return tuple(values) if isinstance(node, ast.Tuple) else (set(values) if isinstance(node, ast.Set) else values)
        if isinstance(node, ast.Dict):
            return {self.evaluate(module, key, local): self.evaluate(module, value, local)
                    for key, value in zip(node.keys, node.values)}
        if isinstance(node, ast.Attribute):
            base = self.evaluate(module, node.value, local)
            if isinstance(base, RecordRef):
                if node.attr not in base.fields:
                    raise ValueError("unknown frozen-record field")
                return base.fields[node.attr]
            if isinstance(base, dict) and set(base) == {"source_class"}:
                full = base["source_class"]
                target, cls = full.rsplit(".", 1)
                class_node = next(item for item in self.archive[target]["tree"].body if isinstance(item, ast.ClassDef) and item.name == cls)
                for member in class_node.body:
                    if isinstance(member, ast.Assign) and any(isinstance(name, ast.Name) and name.id == node.attr for name in member.targets):
                        value = self.evaluate(target, member.value, {})
                        # Only literal-valued enum references are recognized.
                        return EnumRef(full, node.attr, value)
                raise ValueError("unsupported class attribute")
            if isinstance(base, dict) and set(base) == {"external_ref"}:
                symbol = base["external_ref"] + "." + node.attr
                if symbol in NATIVE:
                    return NativeRef(symbol)
                if symbol == "functools._lru_cache_wrapper":
                    return ExternalRef(symbol)
                flags = {"re.IGNORECASE": 2, "re.I": 2, "re.ASCII": 256, "re.A": 256, "re.UNICODE": 32, "re.U": 32}
                if symbol in flags:
                    return flags[symbol]
                raise ValueError("external attribute outside closed native references")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = self.evaluate(module, node.operand, local)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left, right = self.evaluate(module, node.left, local), self.evaluate(module, node.right, local)
            if isinstance(node.op, ast.Add):
                if isinstance(left, (str, tuple, list)) and isinstance(right, type(left)):
                    limit = MAX_SOURCE_BYTES if isinstance(left, str) else 10000
                    if len(left) + len(right) > limit: raise ValueError("source addition bound")
                return left + right
            if isinstance(node.op, ast.Mult):
                sequence, count = (left, right) if isinstance(left, (str, tuple, list)) else (right, left)
                if isinstance(sequence, (str, tuple, list)):
                    limit = MAX_SOURCE_BYTES if isinstance(sequence, str) else 10000
                    if type(count) is not int or len(sequence) * max(0, count) > limit: raise ValueError("source repetition bound")
                elif type(left) is not int or type(right) is not int or left.bit_length() + right.bit_length() > 4096:
                    raise ValueError("source multiplication bound")
                return left * right
            if isinstance(node.op, ast.BitOr): return left | right
            if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node.op, ast.Pow) and type(left) is int and type(right) is int and abs(left) <= 100 and 0 <= right <= 128:
                return left ** right
        if isinstance(node, ast.JoinedStr):
            return "".join(str(self.evaluate(module, item.value, local)) if isinstance(item, ast.FormattedValue) else item.value for item in node.values)
        if isinstance(node, (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
            if len(node.generators) != 1:
                raise ValueError("multiple comprehension generators")
            gen = node.generators[0]
            if gen.ifs or gen.is_async:
                raise ValueError("dynamic comprehension")
            items = list(self.evaluate(module, gen.iter, local))
            if len(items) > 100:
                raise ValueError("comprehension bound")
            def bind(target, value):
                if isinstance(target, ast.Name): return {target.id: value}
                if isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (tuple, list)) and len(target.elts) == len(value):
                    result = {}
                    for child, item in zip(target.elts, value): result.update(bind(child, item))
                    return result
                raise ValueError("unsupported comprehension target")
            envs = [{**local, **bind(gen.target, item)} for item in items]
            if isinstance(node, ast.DictComp):
                return {self.evaluate(module, node.key, env): self.evaluate(module, node.value, env) for env in envs}
            values = [self.evaluate(module, node.elt, env) for env in envs]
            return set(values) if isinstance(node, ast.SetComp) else values
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else None
            if name in {"MetricDefinition", "ScanRule", "_Missing"}:
                target = self.lookup(module, name)
                if not isinstance(target, dict) or "source_class" not in target:
                    raise ValueError("record constructor is not source declared")
                full = target["source_class"]
                fields = self.record_fields(full)
                if node.keywords or len(node.args) != len(fields):
                    raise ValueError("record arguments differ from closed declaration")
                return RecordRef(full, dict(zip(fields, (self.evaluate(module, arg, local) for arg in node.args))))
            if name == "TypeVar":
                if self.archive[module]["aliases"].get(name) != ("typing", "TypeVar") or node.keywords or len(node.args) != 1 or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                    raise ValueError("unsupported TypeVar")
                symbol = node.args[0].value
                self.check_typing_only(module, symbol)
                return TypeVarRef(symbol)
            args = [self.evaluate(module, item, local) for item in node.args]
            if not node.keywords and name in {"tuple", "list", "dict", "set", "frozenset", "MappingProxyType", "len"}:
                factories = {"tuple": tuple, "list": list, "dict": dict, "set": set, "frozenset": frozenset, "MappingProxyType": dict, "len": len}
                return factories[name](*args)
            if name == "Path" and self.archive[module]["aliases"].get(name) == ("pathlib", "Path") and not node.keywords and len(args) == 1 and isinstance(args[0], str):
                return PathRef(PurePosixPath(args[0]).as_posix())
            if name == "range" and not node.keywords and 1 <= len(args) <= 3 and all(type(value) is int and abs(value) <= 100 for value in args):
                result = list(range(*args))
                if len(result) > 100: raise ValueError("range bound")
                return result
            if isinstance(node.func, ast.Attribute) and node.func.attr == "removesuffix" and len(args) == 1:
                return self.evaluate(module, node.func.value, local).removesuffix(args[0])
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "re" and node.func.attr == "compile" and not node.keywords:
                return re.compile(*args)
        raise ValueError("outside closed source literal/reference language")

    def check_typing_only(self, module, symbol):
        tree = self.archive[module]["tree"]
        annotation_ids = set()
        for node in ast.walk(tree):
            for field in ("annotation", "returns"):
                annotation = getattr(node, field, None)
                if annotation is not None: annotation_ids.update(id(child) for child in ast.walk(annotation))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == symbol and isinstance(node.ctx, ast.Load) and id(node) not in annotation_ids:
                raise ValueError("TypeVar has a non-annotation source use")

    def record_fields(self, full):
        allowed = {
            "research_workbench.evaluation.manifest.MetricDefinition": ("metric_id", "definition", "unit", "direction"),
            "research_workbench.capability.archive_audit.ScanRule": ("rule_id", "severity", "pattern"),
            "research_workbench.context.handoff_transfer._Missing": (),
        }
        if full not in allowed: raise ValueError("record class outside named closed registry")
        module, name = full.rsplit(".", 1)
        node = next(item for item in self.archive[module]["tree"].body if isinstance(item, ast.ClassDef) and item.name == name)
        if node.bases or node.keywords: raise ValueError("record inheritance unsupported")
        fields = tuple(item.target.id for item in node.body if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.value is None)
        if fields != allowed[full]: raise ValueError("record field declaration differs")
        if not fields:
            if node.decorator_list or len(node.body) != 1 or not isinstance(node.body[0], ast.Pass): raise ValueError("sentinel class must be pass-only")
        else:
            if len(node.body) != len(fields) or len(node.decorator_list) != 1: raise ValueError("record has executable/custom declaration")
            decorator = node.decorator_list[0]
            if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Name) or self.archive[module]["aliases"].get(decorator.func.id) != ("dataclasses", "dataclass") or decorator.args or {kw.arg: ast.literal_eval(kw.value) for kw in decorator.keywords} != {"frozen": True, "slots": True}:
                raise ValueError("record requires frozen slots dataclass")
            annotations = tuple(ast.unparse(item.annotation) for item in node.body)
            expected = ("str",) * len(fields) if name == "MetricDefinition" else ("str", "str", "re.Pattern[str]")
            if annotations != expected: raise ValueError("record annotation differs")
        return fields


class EnumRef:
    def __init__(self, cls, member, value):
        self.cls, self.member, self.value = cls, member, value
    def __hash__(self): return hash((self.cls, self.member, self.value))
    def __eq__(self, other): return isinstance(other, EnumRef) and vars(self) == vars(other)


class NativeRef:
    def __init__(self, symbol): self.symbol = symbol


class ExternalRef:
    def __init__(self, symbol): self.symbol = symbol


class TypeVarRef:
    def __init__(self, name): self.name = name


class PathRef:
    def __init__(self, path): self.path = path


class RecordRef:
    def __init__(self, cls, fields): self.cls, self.fields = cls, fields


class CallableRef:
    def __init__(self, qualname): self.qualname = qualname


def plain(value):
    if isinstance(value, EnumRef):
        return {"enum": value.cls, "member": value.member, "value": plain(value.value)}
    if isinstance(value, enum.Enum):
        name = type(value).__module__ + "." + type(value).__qualname__
        mod, cls = name.rsplit(".", 1)
        if getattr(sys.modules[mod], cls)[value.name] is not value:
            raise ValueError("Enum member is not canonical loaded source reference")
        return {"enum": name, "member": value.name, "value": plain(value.value)}
    if isinstance(value, NativeRef): return {"native_ref": value.symbol}
    if isinstance(value, ExternalRef): return {"trusted_type": value.symbol}
    if value is LRU_TYPE: return {"trusted_type": "functools._lru_cache_wrapper"}
    if isinstance(value, TypeVarRef): return {"typing_only": value.name}
    if type(value) is typing.TypeVar:
        if value.__constraints__ or value.__bound__ is not None or value.__covariant__ or value.__contravariant__: raise ValueError("TypeVar runtime declaration differs")
        return {"typing_only": value.__name__}
    if isinstance(value, PathRef): return {"path_literal": value.path}
    if isinstance(value, PurePath): return {"path_literal": value.as_posix()}
    if isinstance(value, RecordRef): return {"closed_record": value.cls, "fields": {key: plain(item) for key, item in value.fields.items()}}
    if isinstance(value, CallableRef): return {"callable_ref": value.qualname}
    if isinstance(value, FunctionType):
        full = value.__module__ + "." + value.__qualname__
        module = sys.modules.get(value.__module__)
        if module is None or vars(module).get(value.__qualname__) is not value: raise ValueError("callable reference is not canonical top-level declaration")
        return {"callable_ref": full}
    full = type(value).__module__ + "." + type(value).__qualname__
    allowed = {
        "research_workbench.evaluation.manifest.MetricDefinition": ("metric_id", "definition", "unit", "direction"),
        "research_workbench.capability.archive_audit.ScanRule": ("rule_id", "severity", "pattern"),
        "research_workbench.context.handoff_transfer._Missing": (),
    }
    if full in allowed:
        mod, name = full.rsplit(".", 1)
        if vars(sys.modules[mod]).get(name) is not type(value): raise ValueError("record class is not canonical")
        fields = allowed[full]
        if fields:
            if not dataclasses.is_dataclass(value) or not type(value).__dataclass_params__.frozen or tuple(field.name for field in dataclasses.fields(value)) != fields or tuple(type(value).__slots__) != fields: raise ValueError("record runtime declaration differs")
            state = {key: plain(object.__getattribute__(value, key)) for key in fields}
        else:
            if vars(value): raise ValueError("sentinel has state")
            state = {}
        return {"closed_record": full, "fields": state}
    for symbol, target in NATIVE.items():
        if value is target: return {"native_ref": symbol}
    if isinstance(value, re.Pattern): return {"regex": value.pattern, "flags": int(value.flags)}
    if isinstance(value, (dict, MappingProxyType)):
        return {"mapping": sorted([[plain(k), plain(v)] for k, v in value.items()], key=lambda item: json.dumps(item[0], sort_keys=True))}
    if isinstance(value, (tuple, list, set, frozenset)):
        items = [plain(item) for item in value]
        if isinstance(value, (set, frozenset)): items.sort(key=lambda item: json.dumps(item, sort_keys=True))
        return {type(value).__name__: items}
    if isinstance(value, float) and not math.isfinite(value): raise ValueError("nonfinite runtime value")
    if value is None or isinstance(value, (str, int, bool, float)): return value
    raise ValueError("runtime value outside closed serialization")


def _declarations(tree):
    result = {}
    def walk(nodes, prefix=""):
        for node in nodes:
            if isinstance(node, ast.ClassDef): walk(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): result[prefix + node.name] = node
    walk(tree.body)
    return result


def declarations(raw):
    return _declarations(ast.parse(raw))


def _check_dataclass_metadata(cls):
    local = vars(cls)
    parameters = local.get("__dataclass_params__")
    fields = local.get("__dataclass_fields__")
    if "__dataclass_params__" in local or "__dataclass_fields__" in local:
        _fail(type(parameters) is dataclasses._DataclassParams and type(fields) is dict
              and all(type(field) is dataclasses.Field for field in fields.values()),
              "runtime dataclass metadata differs")


def runtime_functions(module):
    result = {}
    for value in vars(module).values():
        if isinstance(value, FunctionType) and value.__module__ == module.__name__:
            result[value.__qualname__] = value
        elif type(value) is LRU_TYPE and value.__wrapped__.__module__ == module.__name__:
            result[value.__wrapped__.__qualname__] = value
        elif isinstance(value, type) and value.__module__ == module.__name__:
            # Validate these payload types before isinstance inspects their
            # potentially overloaded __class__ during the member scan.
            _check_dataclass_metadata(value)
            for member in vars(value).values():
                if isinstance(member, (staticmethod, classmethod)): member = member.__func__
                if isinstance(member, property): member = member.fget
                if isinstance(member, FunctionType): result[member.__qualname__] = member
    return result


def _runtime():
    return {"implementation": sys.implementation.name, "version": list(sys.version_info[:3]),
            "optimization": sys.flags.optimize, "code_policy": "python-code-fields-v1"}


def _fail(condition, message):
    if not condition:
        raise SourceClosureError(message)


def _targets(node):
    return node.targets if isinstance(node, ast.Assign) else ([node.target] if isinstance(node, ast.AnnAssign) else [])


def _wrapping(item, node):
    wrappers = []
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id in {"staticmethod", "classmethod", "property"}:
            wrappers.append({"kind": dec.id})
        elif isinstance(dec, ast.Attribute) and dec.attr in {"setter", "deleter"}:
            raise SourceClosureError("property setters/deleters require explicit support")
        elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and item["aliases"].get(dec.func.id) == ("functools", "lru_cache"):
            _fail(not dec.args and all(kw.arg in {"maxsize", "typed"} for kw in dec.keywords), "unsupported lru_cache declaration")
            parameters = {"maxsize": 128, "typed": False}
            parameters.update({kw.arg: ast.literal_eval(kw.value) for kw in dec.keywords})
            _fail(type(parameters["typed"]) is bool and (parameters["maxsize"] is None or type(parameters["maxsize"]) is int), "unsupported lru_cache parameters")
            wrappers.append({"kind": "lru_cache", "parameters": parameters})
        elif isinstance(dec, ast.Name) and item["aliases"].get(dec.id) == ("abc", "abstractmethod"):
            wrappers.append({"kind": "abstractmethod"})
        else:
            raise SourceClosureError("callable decorator outside closed policy")
    return wrappers


def _class_node(item, qualname):
    nodes = item["tree"].body
    found = None
    for part in qualname.split("."):
        found = next((node for node in nodes if isinstance(node, ast.ClassDef) and node.name == part), None)
        if found is None: raise SourceClosureError("class declaration unavailable")
        nodes = found.body
    return found


def _class_policies(name, item, closed):
    result = {}
    def walk(nodes, prefix=""):
        for cls in nodes:
            if not isinstance(cls, ast.ClassDef): continue
            qual = prefix + cls.name
            fields = {}
            enum_class = any(isinstance(base, ast.Name) and item["aliases"].get(base.id) in {("enum", "Enum"), ("enum", "StrEnum"), ("enum", "IntEnum")} for base in cls.bases)
            for node in cls.body:
                if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None: continue
                # Generated dataclass field methods/default materialization retain
                # their declared trusted boundary. ClassVar and ordinary class
                # policy assignments are independently checked.
                if isinstance(node, ast.AnnAssign) and not (isinstance(node.annotation, ast.Subscript) and isinstance(node.annotation.value, ast.Name) and item["aliases"].get(node.annotation.value.id) == ("typing", "ClassVar")):
                    continue
                for target in _targets(node):
                    if not isinstance(target, ast.Name): raise SourceClosureError("complex class policy target")
                    if isinstance(node.value, ast.Name) and any(isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name == node.value.id for child in cls.body):
                        fields[target.id] = {"class_function": qual + "." + node.value.id}
                    else:
                        value = closed.evaluate(name, node.value, {})
                        if enum_class: value = EnumRef(name + "." + qual, target.id, value)
                        fields[target.id] = plain(value)
            result[qual] = {"policies": fields, "bases": [ast.dump(base, include_attributes=False) for base in cls.bases],
                            "decorators": [ast.dump(dec, include_attributes=False) for dec in cls.decorator_list]}
            walk(cls.body, qual + ".")
    walk(item["tree"].body)
    return result


def _claims(name, archive, closed):
    item = archive[name]
    defaults = {}
    wrappers = {}
    for qual, node in _declarations(item["tree"]).items():
        defaults[qual] = {"positional": [plain(closed.evaluate(name, value, {})) for value in node.args.defaults],
                          "keyword": {arg.arg: plain(closed.evaluate(name, value, {})) for arg, value in zip(node.args.kwonlyargs, node.args.kw_defaults) if value is not None}}
        wrappers[qual] = _wrapping(item, node)
    globals_ = {}
    for node in item["tree"].body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None: continue
        for target in _targets(node):
            if isinstance(target, ast.Name) and (target.id.lstrip("_").isupper() or target.id in {"__version__", "__all__"}):
                globals_[target.id] = plain(closed.lookup(name, target.id))
    return {"compiled_callables": compiled_functions(item["raw"]), "defaults": defaults,
            "wrappers": wrappers, "globals": globals_, "classes": _class_policies(name, item, closed),
            "aliases": {alias: {"module": target, "attribute": attr} for alias, (target, attr) in sorted(item["aliases"].items())}}


def _portable(path):
    _fail(isinstance(path, str) and path and "\\" not in path and ":" not in path, "nonportable FileRef path")
    pure = PurePosixPath(path)
    _fail(not pure.is_absolute() and all(part not in {".", ".."} for part in pure.parts) and pure.as_posix() == path, "unsafe FileRef path")
    return pure


def _read_ref(read_bytes, reference):
    _fail(isinstance(reference, dict) and set(reference) == {"path", "sha256"}, "invalid source FileRef")
    _portable(reference["path"])
    expected = reference["sha256"]
    _fail(isinstance(expected, str) and re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", expected) is not None, "invalid source FileRef hash")
    raw = read_bytes(reference)
    _fail(isinstance(raw, bytes) and len(raw) <= MAX_SOURCE_BYTES, "source byte bound")
    _fail(sha(raw) == expected.removeprefix("sha256:"), "source FileRef hash differs")
    return raw


def _document_archive(document, read_bytes):
    _fail(isinstance(document, dict) and set(document) == {"schema_version", "record_kind", "version", "policy", "roots", "compiler", "modules", "trusted_boundaries"}, "source closure document fields differ")
    _fail(document["schema_version"] == "0.1.0" and document["record_kind"] == KIND and document["version"] == VERSION and document["policy"] == POLICY, "source closure version unsupported")
    _fail(document["compiler"] == _runtime(), "source closure compiler/runtime differs")
    _fail(document["trusted_boundaries"] == list(TRUSTED_BOUNDARIES), "source closure trusted boundaries differ")
    roots = document["roots"]
    _fail(isinstance(roots, list) and roots and roots == sorted(set(roots)) and len(roots) <= MAX_MODULES, "invalid source roots")
    namespace = {_module_name(root).split(".")[0] for root in roots}
    modules = document["modules"]
    _fail(isinstance(modules, dict) and 0 < len(modules) <= MAX_MODULES, "source module count bound")
    archive = {}
    total = 0
    for name, value in modules.items():
        _module_name(name)
        _fail(name.split(".")[0] in namespace and isinstance(value, dict) and set(value) == {"source_ref", "is_package", "dependencies", "claims"}, "source module fields differ")
        _fail(type(value["is_package"]) is bool, "invalid package declaration")
        suffix = name.replace(".", "/") + ("/__init__.py" if value["is_package"] else ".py")
        path = value["source_ref"].get("path") if isinstance(value["source_ref"], dict) else None
        _fail(isinstance(path, str) and (path == suffix or path.endswith("/" + suffix)), "source reference package/module location differs")
        raw = _read_ref(read_bytes, value["source_ref"])
        total += len(raw)
        _fail(total <= MAX_TOTAL_BYTES, "source total byte bound")
        # This tree is private to this validation and never mutated or exposed.
        # FileRef bytes/hash and all runtime comparisons are still checked afresh.
        tree = ast.parse(raw)
        edges, aliases = _imports(name, tree, is_package=value["is_package"], namespace=namespace)
        _fail(edges == value["dependencies"], "source import graph claim differs: " + name)
        archive[name] = {"raw": raw, "tree": tree, "aliases": aliases, "dependencies": edges, "is_package": value["is_package"]}
    reached, pending = set(), list(roots)
    while pending:
        name = pending.pop()
        if name in reached: continue
        _fail(name in archive, "source dependency missing: " + name)
        reached.add(name)
        pending.extend(archive[name]["dependencies"])
    _fail(reached == set(archive), "extra source closure node")
    closed = ClosedSource(archive)
    for name in sorted(archive):
        _fail(_claims(name, archive, closed) == modules[name]["claims"], "source-derived claims differ: " + name)
    return archive


def verify_source_closure(document, *, read_bytes):
    """Independently compile pinned archived bytes; never import/execute them.

    The caller supplies a trusted outer FileRef through read_source_closure.
    Direct callers must independently bind the document to their own authority.
    """
    try:
        archive = _document_archive(document, read_bytes)
    except SourceClosureError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, SyntaxError, OverflowError) as exc:
        raise SourceClosureError("source closure outside supported closed grammar: " + type(exc).__name__) from None
    return {"policy": POLICY, "module_count": len(archive), "archived_execution": False,
            "source_refs": [document["modules"][name]["source_ref"] for name in sorted(archive)]}


def read_source_closure(reader, reference):
    """Read the externally pinned JSON document using EvaluationInputs or alike."""
    raw = _read_ref(reader.read_bytes, reference)
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError):
        raise SourceClosureError("invalid source closure JSON") from None
    verify_source_closure(document, read_bytes=reader.read_bytes)
    return document


def _canonical_class(module, qual):
    value = module
    for part in qual.split("."):
        value = vars(value).get(part)
        _fail(isinstance(value, type), "canonical source class missing")
    _fail(value.__module__ == module.__name__ and value.__qualname__ == qual, "source class identity differs")
    return value


def _base_reference(module, node):
    if isinstance(node, ast.Subscript):
        return _base_reference(module, node.value)
    if isinstance(node, ast.Name):
        value = vars(module).get(node.id, vars(builtins).get(node.id))
    elif isinstance(node, ast.Attribute):
        parent = _base_reference(module, node.value)
        value = vars(parent).get(node.attr)
    else:
        raise SourceClosureError("source class base outside canonical reference policy")
    _fail(value is not None, "canonical class base unavailable")
    return value


def _recursive_repr_namespace(member):
    if member.__code__ is reprlib.recursive_repr()(lambda self: None).__code__:
        return reprlib
    legacy = getattr(dataclasses, "_recursive_repr", None)
    if isinstance(legacy, FunctionType) and member.__code__ is legacy(lambda self: None).__code__:
        return dataclasses
    return None


def _generated_dataclass_repr(module, cls, member, item, node, namespace):
    # Python 3.13 uses reprlib's recursion wrapper rather than dataclasses' own
    # wrapper. Recognize that exact trusted wrapper, not arbitrary reprlib code
    # or a callable which merely advertises a __wrapped__ attribute.
    local = vars(cls)
    parameters = local.get("__dataclass_params__")
    field_metadata = local.get("__dataclass_fields__")
    if not (namespace is not None and member.__globals__ is vars(namespace)
            and member.__builtins__ is vars(builtins)
            and type(parameters) is dataclasses._DataclassParams
            and type(field_metadata) is dict
            and all(type(field) is dataclasses.Field for field in field_metadata.values())):
        return False
    if parameters.repr is not True:
        return False
    declared = False
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and item["aliases"].get(target.id) == ("dataclasses", "dataclass"):
            declared = True
        elif (isinstance(target, ast.Attribute) and target.attr == "dataclass"
              and isinstance(target.value, ast.Name)
              and item["aliases"].get(target.value.id) == ("dataclasses", None)):
            declared = True
    if not declared or member.__closure__ is None:
        return False
    cells = dict(zip(member.__code__.co_freevars, (cell.cell_contents for cell in member.__closure__)))
    inner = cells.get("user_function")
    expected_cells = {"repr_running", "user_function"}
    if namespace is reprlib:
        expected_cells.add("fillvalue")
        if type(cells.get("fillvalue")) is not str or cells["fillvalue"] != "...":
            return False
    if not (set(cells) == expected_cells
            and type(cells["repr_running"]) is set and type(inner) is FunctionType
            and inner.__globals__ is vars(module) and inner.__module__ == module.__name__
            and inner.__builtins__ is vars(builtins)
            and getattr(member, "__wrapped__", None) is inner
            and inner.__defaults__ is None and inner.__kwdefaults__ is None
            and inner.__closure__ is None):
        return False
    # Only generate a fresh standard-library repr from field names/flags. No
    # archived code, original class constructor, defaults or factories execute.
    fields = dataclasses.fields(cls)
    if any(type(field) is not dataclasses.Field or type(field.name) is not str
           or type(field.repr) is not bool or type(field.kw_only) is not bool for field in fields):
        return False
    reference = dataclasses.make_dataclass(
        "_ClosureRepr", [(field.name, object, dataclasses.field(repr=field.repr, kw_only=field.kw_only))
                         for field in fields], init=False, eq=False,
    )
    expected = vars(reference)["__repr__"].__wrapped__
    # Newer dataclasses compile several generated methods in one batch, so repr
    # can start on a different line. Normalize only that synthetic line offset.
    return code_state(inner.__code__.replace(co_firstlineno=1)) == code_state(expected.__code__.replace(co_firstlineno=1))


def _verify_class_layout(module, qual, cls, item):
    _check_dataclass_metadata(cls)
    node = _class_node(item, qual)
    expected_bases = tuple(_base_reference(module, base) for base in node.bases) or (object,)
    _fail(cls.__bases__ == expected_bases, "source class bases differ")
    declarations_ = {child.name for child in node.body if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for child in node.body:
        declarations_.update(target.id for target in _targets(child) if isinstance(target, ast.Name))
    # Known generated method bodies remain trusted. An unrelated injected Python
    # method does not become a generated method merely by occupying a class slot.
    trusted_files = {str(Path(inspect.getsourcefile(mod)).resolve()) for mod in (dataclasses, enum, typing)}
    generated = {"__init__", "__repr__", "__eq__", "__ne__", "__lt__", "__le__", "__gt__", "__ge__", "__hash__", "__setattr__", "__delattr__", "__getstate__", "__setstate__"}
    for attribute, member in vars(cls).items():
        if attribute in declarations_: continue
        if isinstance(member, (staticmethod, classmethod)): member = member.__func__
        if isinstance(member, property): member = member.fget
        if isinstance(member, FunctionType):
            filename = member.__code__.co_filename
            trusted = filename != "<string>" and str(Path(filename).resolve()) in trusted_files
            generated_method = dataclasses.is_dataclass(cls) and attribute in generated and filename == "<string>"
            namespace = _recursive_repr_namespace(member)
            if namespace is not None:
                # The legacy dataclasses wrapper must obey the same repr-slot
                # and inner-code rules; its filename cannot bless an injection.
                trusted = False
                generated_method = False
            repr_wrapper = attribute == "__repr__" and _generated_dataclass_repr(module, cls, member, item, node, namespace)
            _fail(trusted or generated_method or repr_wrapper, "undeclared runtime class callable: " + qual + "." + attribute)


def _verify_loaded(document, archive, *, source_root):
    checked = {"callables": 0, "defaults": 0, "aliases": 0, "globals": 0, "class_policies": 0}
    _fail(time.monotonic is NATIVE["time.monotonic"], "canonical native clock reference differs")
    # Import only source-declared current modules. This never imports archived
    # bytes or constructs a Provider/credential/Session instance.
    for name in sorted(archive):
        if name not in sys.modules:
            importlib.import_module(name)
    for name in sorted(archive):
        module = sys.modules.get(name)
        _fail(module is not None, "source runtime module unavailable: " + name)
        _fail(module.__name__ == name and module.__package__ == (name if archive[name]["is_package"] else name.rpartition(".")[0]), "canonical module metadata differs")
        file = inspect.getsourcefile(module)
        _fail(file is not None and Path(file).suffix == ".py" and not Path(file).is_symlink(), "runtime source unavailable: " + name)
        path = Path(file).resolve()
        _fail((path.name == "__init__.py") == archive[name]["is_package"], "loaded module/package declaration differs")
        # Source-root location cannot substitute a different canonical loaded file.
        if source_root is not None:
            try: candidate = _path_for(source_root, name)
            except SourceClosureError: candidate = None
            if candidate is not None: _fail(candidate == path, "loaded module source location differs: " + name)
        _fail(path.read_bytes() == archive[name]["raw"], "loaded source bytes differ: " + name)
        claims = document["modules"][name]["claims"]
        actual = runtime_functions(module)
        for qual, defaults in claims["defaults"].items():
            function = actual.get(qual)
            _fail(function is not None, "explicit source callable missing: " + name + "." + qual)
            wrappers = claims["wrappers"][qual]
            if "." in qual:
                owner, attribute = qual.rsplit(".", 1)
                descriptor = vars(_canonical_class(module, owner)).get(attribute)
                kinds = {wrapper["kind"] for wrapper in wrappers}
                expected_type = staticmethod if "staticmethod" in kinds else classmethod if "classmethod" in kinds else property if "property" in kinds else FunctionType
                _fail(type(descriptor) is expected_type, "source method descriptor differs")
                bound = descriptor.__func__ if isinstance(descriptor, (staticmethod, classmethod)) else descriptor.fget if isinstance(descriptor, property) else descriptor
                _fail(bound is function, "declared source method binding differs")
            else:
                _fail(vars(module).get(qual) is function, "declared source callable binding differs")
            cached = [wrapper for wrapper in wrappers if wrapper["kind"] == "lru_cache"]
            if cached:
                _fail(len(cached) == 1 and type(function) is LRU_TYPE and function.cache_parameters() == cached[0]["parameters"], "source cache wrapper differs")
                function = function.__wrapped__
            _fail(isinstance(function, FunctionType) and function.__globals__ is vars(module), "source callable global namespace differs")
            def check_builtins(code):
                for instruction in dis.get_instructions(code):
                    if instruction.opname == "LOAD_GLOBAL" and instruction.argval in vars(builtins):
                        symbol = instruction.argval
                        if symbol not in vars(module):
                            _fail(function.__builtins__.get(symbol) is vars(builtins)[symbol], "source callable builtin reference differs")
                        elif symbol not in {"__name__", "__doc__", "__package__", "__loader__", "__spec__"} and symbol not in claims["aliases"] and symbol not in claims["globals"] and symbol not in claims["classes"] and symbol not in claims["defaults"]:
                            raise SourceClosureError("undeclared runtime builtin shadow: " + symbol)
                for constant in code.co_consts:
                    if isinstance(constant, CodeType): check_builtins(constant)
            check_builtins(function.__code__)
            _fail(digest(code_state(function.__code__)) == claims["compiled_callables"].get(qual), "source callable code differs: " + name + "." + qual)
            if function.__closure__ is not None:
                _fail(function.__code__.co_freevars == ("__class__",) and len(function.__closure__) == 1 and function.__closure__[0].cell_contents is _canonical_class(module, qual.rsplit(".", 1)[0]), "source callable closure differs")
            _fail([plain(value) for value in (function.__defaults__ or ())] == defaults["positional"] and {key: plain(value) for key, value in (function.__kwdefaults__ or {}).items()} == defaults["keyword"], "source callable defaults differ: " + name + "." + qual)
            checked["callables"] += 1
            checked["defaults"] += 1
        for policy, expected in claims["globals"].items():
            _fail(policy in vars(module) and plain(vars(module)[policy]) == expected, "source global policy differs: " + name + "." + policy)
            checked["globals"] += 1
        for alias, reference in claims["aliases"].items():
            other = sys.modules.get(reference["module"])
            _fail(other is not None, "import alias target unavailable: " + name + "." + alias)
            target = other if reference["attribute"] is None else vars(other).get(reference["attribute"])
            _fail(target is not None and alias in vars(module) and vars(module)[alias] is target, "source import alias differs: " + name + "." + alias)
            checked["aliases"] += 1
        for qual, class_claim in claims["classes"].items():
            cls = _canonical_class(module, qual)
            _verify_class_layout(module, qual, cls, archive[name])
            for policy, expected in class_claim["policies"].items():
                _fail(policy in vars(cls), "source class policy missing")
                value = vars(cls)[policy]
                if isinstance(expected, dict) and set(expected) == {"class_function"}:
                    _fail(value is actual.get(expected["class_function"]), "class function alias differs")
                else:
                    _fail(plain(value) == expected, "source class policy differs: " + name + "." + qual + "." + policy)
                checked["class_policies"] += 1
    return checked


def verify_loaded_source_closure(document, *, read_bytes, source_root):
    """Bind independently derived claims to canonical currently loaded objects."""
    receipt = verify_source_closure(document, read_bytes=read_bytes)
    try:
        archive = _document_archive(document, read_bytes)
        checked = _verify_loaded(document, archive, source_root=source_root)
    except SourceClosureError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as exc:
        raise SourceClosureError("loaded source closure outside supported state: " + type(exc).__name__) from None
    return {**receipt, "actual_verified": True, "checked": checked}


def produce_source_closure(roots, *, source_root, project_root, archive_prefix):
    """Archive the import closure of actual declared Provider/runtime roots.

    Only declared imports and required package parents are traversed; the source
    directory is never enumerated. Unsupported policies reject production.
    """
    roots = sorted(set(_module_name(root) for root in roots))
    _fail(roots and len(roots) <= MAX_MODULES, "invalid source roots")
    namespace = {root.split(".")[0] for root in roots}
    prefix = _portable(archive_prefix)
    project = Path(project_root).resolve()
    source = Path(source_root).resolve()
    destination = project.joinpath(*prefix.parts)
    _fail(destination.resolve().is_relative_to(project), "source archive leaves project root")
    archive = {}
    pending = list(roots)
    total = 0
    while pending:
        name = pending.pop()
        if name in archive: continue
        _fail(len(archive) < MAX_MODULES, "source module count bound")
        loaded = sys.modules.get(name)
        path = inspect.getsourcefile(loaded) if loaded is not None else None
        path = Path(path).resolve() if path is not None else _path_for(source, name)
        _fail(path.suffix == ".py" and path.is_file() and not path.is_symlink(), "declared source unavailable")
        raw = path.read_bytes()
        total += len(raw)
        _fail(len(raw) <= MAX_SOURCE_BYTES and total <= MAX_TOTAL_BYTES, "source byte bound")
        is_package = path.name == "__init__.py"
        tree = ast.parse(raw)
        edges, aliases = _imports(name, tree, is_package=is_package, namespace=namespace)
        archive[name] = {"raw": raw, "tree": tree, "aliases": aliases, "dependencies": edges, "is_package": is_package}
        pending.extend(edges)
    closed = ClosedSource(archive)
    document = {"schema_version": "0.1.0", "record_kind": KIND, "version": VERSION, "policy": POLICY,
                "roots": roots, "compiler": _runtime(), "modules": {}, "trusted_boundaries": list(TRUSTED_BOUNDARIES)}
    try:
        for name in sorted(archive):
            item = archive[name]
            logical = name.replace(".", "/") + ("/__init__.py" if item["is_package"] else ".py")
            reference = {"path": (prefix / logical).as_posix(), "sha256": sha(item["raw"])}
            document["modules"][name] = {"source_ref": reference, "is_package": item["is_package"],
                                         "dependencies": item["dependencies"], "claims": _claims(name, archive, closed)}
        _verify_loaded(document, archive, source_root=source)
    except SourceClosureError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, SyntaxError, OSError, OverflowError) as exc:
        raise SourceClosureError("source closure production outside supported state: " + type(exc).__name__) from None
    destination.mkdir(parents=True, exist_ok=True)
    for name, item in archive.items():
        target = project.joinpath(*PurePosixPath(document["modules"][name]["source_ref"]["path"]).parts)
        _fail(not target.is_symlink() and target.resolve().is_relative_to(project), "unsafe archive target")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): _fail(target.read_bytes() == item["raw"], "existing archive source differs")
        else: target.write_bytes(item["raw"])
    return document
