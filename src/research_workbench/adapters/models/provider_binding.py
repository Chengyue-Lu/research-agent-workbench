"""Explicit, file-backed binding closure for configured M6 Providers.

This observer does not authenticate remote model weights, resolve credentials,
select a Supply, or execute archived implementation files during cold replay.
"""

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import CodeType, FunctionType, MappingProxyType
from typing import Any

from research_workbench.evaluation.pins import EvaluationInputs, digest, file_ref, require


POLICY = "provider-binding-v2"
GRAPH_POLICY = "provider-binding-v3"
KIND = "provider_binding_manifest"
CONFIGURED_CLASS = "research_workbench.adapters.models.configured.ConfiguredProvider"
MODULES = tuple(f"research_workbench.adapters.models.{name}" for name in (
    "configured", "profile_configuration", "wire_codecs", "base", "http", "port", "provider_binding",
))
LIMITATIONS = (
    "Independent source checks cover explicit source-declared callables and closed first-party policy registries; generated dataclass methods and dependency behavior are not independently source-attested.",
    "Cold replay requires the frozen Python code runtime; remote provider/model/account authentication is not established.",
    "Injected transport/credential modules pin explicit class callables and source bytes, not arbitrary component module globals.",
)
GRAPH_LIMITATIONS = (
    "Independent source checks cover explicit source-declared callables and closed first-party policy registries; generated dataclass methods and dependency behavior are not independently source-attested.",
    "Cold replay requires the frozen Python code runtime; remote provider/model/account authentication is not established.",
    "The explicit source graph includes package initialization and declared helper dependencies under trusted compiler/native/dependency boundaries; it is not a complete live execution context or remote attestation.",
)
CONFORMANCE_ROOTS = (
    "research_workbench.adapters.models.profile_conformance",
    "research_workbench.adapters.models.profile_conformance_report",
)


def provider_source_roots(provider, *, include_conformance=False) -> tuple[str, ...]:
    """Derive source roots from the actual selected components, without selection."""
    require(type(include_conformance) is bool, "source graph option must be explicit")
    roots = {CONFIGURED_CLASS.rsplit(".", 1)[0], __name__,
             type(provider.transport).__module__, type(provider.credential).__module__}
    if include_conformance:
        roots.update(CONFORMANCE_ROOTS)
    return tuple(sorted(roots))


def _code_runtime() -> dict[str, Any]:
    return {"implementation": sys.implementation.name,
            "version": ".".join(str(item) for item in sys.version_info[:3]),
            "optimization": sys.flags.optimize, "fingerprint_policy": "python-code-fields-v1"}


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _class_name(value: Any) -> str:
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _normalize_code(code: CodeType) -> dict[str, Any]:
    # marshal bytes depend on object interning/reference sharing. Pin explicit
    # code fields instead; omit only the machine-local co_filename.
    def constant(value):
        if isinstance(value, CodeType):
            return {"code": _normalize_code(value)}
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
        require(value is None or isinstance(value, (str, int, bool)), "unsupported executable constant")
        return value

    return {"version": "python-code-fields-v1", "bytecode": code.co_code.hex(),
            "constants": [constant(item) for item in code.co_consts], "names": code.co_names,
            "varnames": code.co_varnames, "freevars": code.co_freevars, "cellvars": code.co_cellvars,
            "argcount": code.co_argcount, "posonlyargcount": code.co_posonlyargcount,
            "kwonlyargcount": code.co_kwonlyargcount, "nlocals": code.co_nlocals,
            "stacksize": code.co_stacksize, "flags": code.co_flags,
            "name": code.co_name, "qualname": code.co_qualname,
            "firstlineno": code.co_firstlineno, "linetable": code.co_linetable.hex(),
            "exceptiontable": code.co_exceptiontable.hex()}


def _code_hash(code: CodeType) -> str:
    return digest(_normalize_code(code))


def _compiled_callables(raw: bytes) -> dict[str, str]:
    compiled = compile(raw, "<provider-binding-source>", "exec", dont_inherit=True, optimize=sys.flags.optimize)
    result: dict[str, str] = {}

    def visit(code: CodeType) -> None:
        for child in code.co_consts:
            if isinstance(child, CodeType):
                # Class-body code is included in source bytes; functions are
                # independently matched against actual loaded Python methods.
                if not child.co_name.startswith("<") and child.co_flags & inspect.CO_NEWLOCALS:
                    result[child.co_qualname] = _code_hash(child)
                visit(child)

    visit(compiled)
    return result


def _runtime_callables(module) -> dict[str, FunctionType]:
    result: dict[str, FunctionType] = {}
    for value in vars(module).values():
        if isinstance(value, FunctionType) and value.__module__ == module.__name__:
            result[value.__qualname__] = value
        elif isinstance(value, type) and value.__module__ == module.__name__:
            for member in vars(value).values():
                if isinstance(member, (staticmethod, classmethod)):
                    member = member.__func__
                elif isinstance(member, property):
                    member = member.fget
                if isinstance(member, FunctionType):
                    result[member.__qualname__] = member
    return result


def _constant_plain(value: Any) -> Any:
    if isinstance(value, re.Pattern):
        return {"regex_pattern": value.pattern, "regex_flags": value.flags}
    if isinstance(value, Mapping):
        return {str(key): _constant_plain(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        return sorted((_constant_plain(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (tuple, list)):
        return [_constant_plain(item) for item in value]
    require(value is None or isinstance(value, (str, int, float, bool)), "unsupported Provider policy constant")
    return value


def _source_constants(raw: bytes, *, port_source: bytes | None = None) -> dict[str, Any]:
    """Interpret only the closed literal policy language, never execute source."""
    values: dict[str, Any] = {}
    if port_source is None:
        port = sys.modules.get("research_workbench.adapters.models.port")
        require(port is not None, "Provider Port module is not loaded")
        port_source = Path(inspect.getsourcefile(port)).read_bytes()
    enums = {}
    for node in ast.parse(port_source).body:
        if isinstance(node, ast.ClassDef):
            enums[node.name] = {target.id: ast.literal_eval(item.value)
                for item in node.body if isinstance(item, ast.Assign)
                for target in item.targets if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant)}

    def evaluate(node, local):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            require(node.id in local or node.id in values, "Provider policy constant has an undeclared dependency")
            return local[node.id] if node.id in local else values[node.id]
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            items = [evaluate(item, local) for item in node.elts]
            return tuple(items) if isinstance(node, ast.Tuple) else (set(items) if isinstance(node, ast.Set) else items)
        if isinstance(node, ast.Dict):
            return {evaluate(key, local): evaluate(value, local) for key, value in zip(node.keys, node.values)}
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "re":
                require(node.attr in {"IGNORECASE", "I", "ASCII", "A", "UNICODE", "U"}, "unsupported regex policy flag")
                return int(getattr(re, node.attr))
            require(node.value.id in enums and node.attr in enums[node.value.id], "unsupported Provider policy attribute")
            return enums[node.value.id][node.attr]
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left, local), evaluate(node.right, local)
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.BitOr):
                return left | right
        if isinstance(node, ast.JoinedStr):
            return "".join(str(evaluate(item.value, local)) if isinstance(item, ast.FormattedValue) else item.value for item in node.values)
        if isinstance(node, (ast.DictComp, ast.GeneratorExp, ast.SetComp, ast.ListComp)):
            require(len(node.generators) == 1 and not node.generators[0].ifs and not node.generators[0].is_async,
                    "unsupported Provider policy comprehension")
            generator = node.generators[0]
            require(isinstance(generator.target, ast.Name), "unsupported Provider policy comprehension target")
            items = list(evaluate(generator.iter, local))
            require(len(items) <= 100, "Provider policy comprehension exceeds the closed bound")
            if isinstance(node, ast.DictComp):
                return {evaluate(node.key, {**local, generator.target.id: item}):
                        evaluate(node.value, {**local, generator.target.id: item}) for item in items}
            result = [evaluate(node.elt, {**local, generator.target.id: item}) for item in items]
            return set(result) if isinstance(node, ast.SetComp) else result
        if isinstance(node, ast.Call) and not node.keywords:
            if isinstance(node.func, ast.Name) and node.func.id in {"frozenset", "set", "tuple", "list", "dict", "MappingProxyType"}:
                require(len(node.args) == 1, "unsupported Provider policy constructor")
                value = evaluate(node.args[0], local)
                if node.func.id in {"frozenset", "set"}:
                    return frozenset(value)
                if node.func.id in {"tuple", "list"}:
                    return tuple(value)
                return dict(value)
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "re" and node.func.attr == "compile":
                return re.compile(*(evaluate(item, local) for item in node.args))
            if isinstance(node.func, ast.Attribute) and node.func.attr == "removesuffix" and len(node.args) == 1:
                text, suffix = evaluate(node.func.value, local), evaluate(node.args[0], local)
                require(isinstance(text, str) and isinstance(suffix, str), "policy suffix requires literal strings")
                return text.removesuffix(suffix)
        require(False, "Provider policy constant is outside the closed literal language")

    for node in ast.parse(raw).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.lstrip("_").isupper():
                    values[target.id] = evaluate(node.value, {})
    return {name: _constant_plain(value) for name, value in values.items()}


def _source_defaults(raw: bytes, constants: Mapping[str, Any]) -> dict[str, Any]:
    result = {}

    def value(node):
        if isinstance(node, ast.Name) and node.id in constants:
            return constants[node.id]
        try:
            return _constant_plain(ast.literal_eval(node))
        except (ValueError, TypeError):
            require(False, "Provider callable default is outside the closed literal language")

    def visit(nodes, prefix=""):
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                visit(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result[prefix + node.name] = {
                    "defaults": [value(item) for item in node.args.defaults] or None,
                    "kwdefaults": {argument.arg: value(item) for argument, item in zip(node.args.kwonlyargs, node.args.kw_defaults)
                                   if item is not None} or None,
                }
    visit(ast.parse(raw).body)
    return result


def _source_state(module_name: str) -> tuple[Path, bytes, dict[str, Any]]:
    module = sys.modules.get(module_name)
    require(module is not None, "declared Provider implementation module is not loaded")
    source = inspect.getsourcefile(module)
    require(source is not None, "Provider implementation requires Python source bytes")
    path = Path(source).resolve()
    raw = path.read_bytes()
    compiled = _compiled_callables(raw)
    runtime = _runtime_callables(module)
    fingerprints: dict[str, str] = {}
    for name, function in runtime.items():
        if name in compiled:
            require(_code_hash(function.__code__) == compiled[name], "loaded Provider callable differs from source bytes")
            if function.__closure__ is not None:
                require(function.__code__.co_freevars == ("__class__",)
                        and len(function.__closure__) == 1
                        and isinstance(function.__closure__[0].cell_contents, type)
                        and function.__closure__[0].cell_contents.__module__ == module_name
                        and name.startswith(function.__closure__[0].cell_contents.__qualname__ + "."),
                        "Provider binding cannot pin dynamic callable closures")
            fingerprints[name] = compiled[name]
    # Nested local functions are covered by the enclosing function bytecode;
    # every source-declared top-level/class function must remain discoverable.
    declared = {name for name in compiled if ".<locals>." not in name}
    require(declared <= set(fingerprints), "Provider source callable is absent or replaced at runtime")
    # Only the fixed first-party semantic modules own policy registries. An
    # injected synthetic component module may also define test ROOT/fixtures;
    # those are not execution policy or portable remote attestations.
    constants = _source_constants(raw) if module_name in MODULES else {}
    require(all(name in vars(module) and _constant_plain(vars(module)[name]) == value for name, value in constants.items()),
            "loaded Provider policy registry differs from source constants")
    expected_defaults = _source_defaults(raw, constants)
    defaults = {name: {"defaults": _constant_plain(runtime[name].__defaults__),
                       "kwdefaults": _constant_plain(runtime[name].__kwdefaults__)} for name in fingerprints}
    require(defaults == expected_defaults, "loaded Provider callable defaults differ from source declarations")
    return path, raw, {"module": module_name, "source_sha256": hashlib.sha256(raw).hexdigest(),
                       "callables": fingerprints, "constants": constants,
                       "defaults": defaults,
                       "runtime_fingerprint": digest({"callables": fingerprints, "constants": constants, "defaults": defaults})}


def _descriptor(provider) -> dict[str, Any]:
    # Import only the explicit installed implementation, never source snapshots.
    from research_workbench.adapters.models.configured import ConfiguredProvider
    from research_workbench.adapters.models.http import UrllibTransport

    require(type(provider) is ConfiguredProvider, "configured binding requires the actual ConfiguredProvider class")
    require(_class_name(provider) == CONFIGURED_CLASS, "configured Provider class identity differs")
    profile = provider.profile.to_mapping()
    config = _plain(provider.resolved_config)
    require(profile["implementation"]["binding_policy_version"] == POLICY, "unsupported Provider binding policy")
    source = config["credential_source"]
    require(source["kind"] == "environment", "unsupported exact-binding credential source")
    expected_label = "env:" + source["name"]
    require(provider.credential.label == expected_label, "actual credential reference differs from resolved configuration")
    require(provider.model == config["model"] == profile["model"]["requested_id"], "actual resolved model differs")
    require(provider.timeout_seconds == config["transport"]["timeout_seconds"], "actual Provider timeout differs")
    transport = provider.transport
    require(type(transport.max_response_bytes) is int, "actual transport requires an explicit response byte bound")
    require(transport.max_response_bytes == config["transport"]["max_response_bytes"], "actual transport response bound differs")
    if type(transport) is not UrllibTransport:
        # A source-bound injected transport retains its own identity. A test
        # transport never becomes evidence for the production HTTPS transport.
        require(inspect.getsourcefile(type(transport)) is not None, "injected transport requires explicit file-bound source")
    for component, methods in ((transport, ("send",)), (provider.credential, ("available", "resolve"))):
        if type(component) is UrllibTransport:
            methods = ("send", "_read_bounded")
        for name in methods:
            method = getattr(component, name)
            require(inspect.ismethod(method) and method.__self__ is component
                    and method.__func__ is getattr(type(component), name),
                    "actual Provider component method was replaced")
    for name in ("generate", "capabilities", "binding_descriptor"):
        method = getattr(provider, name)
        require(inspect.ismethod(method) and method.__func__ is getattr(ConfiguredProvider, name),
                "configured Provider method was replaced")
    descriptor = {
        "adapter_class": CONFIGURED_CLASS,
        "adapter_version": profile["implementation"]["adapter_version"],
        "profile": profile,
        "resolved_config": config,
        "credential_reference": source,
        "transport_identity": {"class": _class_name(transport), "options": {
            "max_response_bytes": transport.max_response_bytes,
        }},
    }
    reference = getattr(provider, "_implementation_closure_ref", None)
    if reference is not None:
        descriptor["implementation_closure_ref"] = _plain(reference)
    require(_plain(provider.binding_descriptor()) == descriptor, "Provider descriptor differs from actual instance")
    return descriptor


def capture_configured_provider_binding(provider) -> Mapping[str, Any]:
    """Freeze actual nonsecret configuration and explicit loaded implementation.

    Standard-library/dependency behavior is not claimed as a portable attestation;
    the existing baseline runtime component separately pins the Python executable.
    """
    descriptor = _descriptor(provider)
    require(tuple(provider.required_binding_modules) == MODULES, "Provider helper closure differs from fixed policy")
    names = list(MODULES)
    for component in (provider.transport, provider.credential):
        module = type(component).__module__
        require(not module.startswith("__"), "binding component requires an explicit source module")
        if module not in names:
            names.append(module)
    sources = [_source_state(name)[2] for name in sorted(names)]
    # Imported first-party function aliases are also checked: a module must not
    # keep an obsolete/replaced helper behind a still-valid source file.
    for name in names:
        module = sys.modules[name]
        raw = Path(inspect.getsourcefile(module)).read_bytes()
        for node in ast.parse(raw).body:
            if isinstance(node, ast.ImportFrom) and node.module in names:
                for alias in node.names:
                    require(alias.name != "*" and vars(module).get(alias.asname or alias.name) is getattr(sys.modules[node.module], alias.name, None),
                            "Provider imported class/helper alias differs from declared source")
        for value in vars(module).values():
            if isinstance(value, FunctionType) and value.__module__ in names and value.__module__ != name:
                origin = sys.modules[value.__module__]
                require(getattr(origin, value.__name__, None) is value,
                        "Provider imported helper differs from its declared module")
    return _freeze({"descriptor": descriptor, "sources": sources, "code_runtime": _code_runtime()})


def assert_configured_provider_binding(provider, snapshot: Mapping[str, Any]) -> None:
    """Reobserve at use boundary before CredentialProvider.resolve/send."""
    require(_plain(capture_configured_provider_binding(provider)) == _plain(snapshot), "actual Provider binding drift")


@dataclass(frozen=True, slots=True)
class ProviderBindingManifest:
    document: Mapping[str, Any]

    @property
    def root(self) -> str:
        return digest({"canonical_policy": "provider-binding-manifest-canonical-v1", "manifest": self.document})

    def to_mapping(self) -> dict[str, Any]:
        return _plain(self.document)


def _write_bytes(root: Path, name: str, raw: bytes) -> dict[str, str]:
    require(isinstance(name, str) and "\\" not in name and ":" not in name and not name.startswith("/")
            and all(part not in {"", ".", ".."} for part in name.split("/")), "binding destination must be portable")
    target = (root / name).resolve()
    require(target.is_relative_to(root), "binding destination escapes project root")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(raw)
    return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}


def _json_bytes(document: Mapping[str, Any]) -> bytes:
    return (json.dumps(_plain(document), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def stage_provider_binding(provider, *, root: str | Path, destination: str,
                           source_closure=False, include_conformance=False) -> dict[str, str]:
    """Stage only the explicit actual configuration and declared source closure."""
    project = Path(root).resolve()
    require(type(source_closure) is bool and type(include_conformance) is bool,
            "Provider graph options must be explicit")
    require(source_closure or not include_conformance, "conformance graph requires source closure")
    require(source_closure or getattr(provider, "_implementation_closure_ref", None) is None,
            "source-bound Provider cannot stage a legacy binding manifest")
    snapshot = _plain(capture_configured_provider_binding(provider))
    descriptor = snapshot["descriptor"]
    refs = []
    for state in snapshot["sources"]:
        _path, raw, current = _source_state(state["module"])
        require(current == state, "Provider implementation changed during staging")
        source_ref = _write_bytes(project, f"{destination}/source/{state['module'].replace('.', '/')}.py", raw)
        refs.append({"module": state["module"], "source_ref": source_ref,
                     "runtime_fingerprint": state["runtime_fingerprint"], "callables": state["callables"],
                     "constants": state["constants"], "defaults": state["defaults"]})
    profile_ref = _write_bytes(project, f"{destination}/profile.json", _json_bytes(descriptor["profile"]))
    config_ref = _write_bytes(project, f"{destination}/resolved-config.json", _json_bytes(descriptor["resolved_config"]))
    manifest = {
        "schema_version": "0.1.0", "record_kind": KIND, "version": "1.0.0",
        "binding_policy_version": POLICY, "manifest_id": descriptor["resolved_config"]["adapter_id"],
        "adapter_class": descriptor["adapter_class"], "adapter_version": descriptor["adapter_version"],
        "provider_identity": descriptor["profile"]["identity"], "profile_ref": profile_ref,
        "resolved_config_ref": config_ref, "implementation_refs": refs,
        "transport_identity": descriptor["transport_identity"],
        "credential_reference": descriptor["credential_reference"],
        "credential_class": _class_name(provider.credential),
        "component_modules": {"transport": type(provider.transport).__module__,
                              "credential": type(provider.credential).__module__},
        "code_runtime": snapshot["code_runtime"],
        "limitations": list(LIMITATIONS),
        "model_policy": descriptor["profile"]["model"], "generation_policy": descriptor["profile"]["generation"],
    }
    if source_closure:
        from research_workbench.adapters.models.provider_source_closure import produce_source_closure
        roots = provider_source_roots(provider, include_conformance=include_conformance)
        graph = produce_source_closure(roots, source_root=Path(__file__).resolve().parents[3],
                                      project_root=project, archive_prefix=f"{destination}/graph/source")
        graph_ref = _write_bytes(project, f"{destination}/graph/closure.json", _json_bytes(graph))
        manifest.update(version="1.1.0", binding_policy_version=GRAPH_POLICY,
                        limitations=list(GRAPH_LIMITATIONS), implementation_closure_ref=graph_ref,
                        source_roots=list(roots))
    assert_configured_provider_binding(provider, snapshot)
    return _write_bytes(project, f"{destination}/manifest.json", _json_bytes(manifest))


def _visit_references(inputs: EvaluationInputs, value: Any) -> None:
    if isinstance(value, Mapping):
        if set(value) == {"path", "sha256"}:
            inputs.read_bytes(value)
        else:
            for child in value.values():
                _visit_references(inputs, child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _visit_references(inputs, child)


def _checked_source_closure(inputs, reference, *, actual=False):
    from research_workbench.adapters.models.provider_source_closure import (
        SourceClosureError, read_source_closure, verify_loaded_source_closure,
    )
    failed = False
    try:
        graph = read_source_closure(inputs, reference)
        if actual:
            verify_loaded_source_closure(graph, read_bytes=inputs.read_bytes,
                                         source_root=Path(__file__).resolve().parents[3])
    except SourceClosureError:
        failed = True
    if failed:
        raise EvaluationValidationError("Provider source closure validation failed")
    return graph


def read_provider_binding_manifest(
    inputs: EvaluationInputs, reference: Mapping[str, Any], *, expected_adapter: Mapping[str, Any] | None = None,
) -> ProviderBindingManifest:
    """Independently derive archived closure, without importing archived code."""
    document = inputs.read(reference, KIND)
    if document["version"] == "1.1.0":
        graph = _checked_source_closure(inputs, document["implementation_closure_ref"])
        expected_roots = {CONFIGURED_CLASS.rsplit(".", 1)[0], __name__,
                          *document["component_modules"].values()}
        roots = set(document["source_roots"])
        require(roots in (expected_roots, expected_roots | set(CONFORMANCE_ROOTS)),
                "Provider source roots differ from selected implementation")
        require(document["source_roots"] == sorted(roots) == graph["roots"],
                "Provider graph root identity differs")
    require(document["code_runtime"] == _code_runtime(),
            "Provider binding callable replay requires its frozen Python code runtime")
    profile = inputs.read(document["profile_ref"], "provider_api_profile")
    config = inputs.read(document["resolved_config_ref"])
    from research_workbench.adapters.models.profile_configuration import ProviderAdapterConfigV2
    candidate = dict(config)
    model = candidate.pop("model", None)
    candidate["model_selector"] = {"kind": "literal", "value": model}
    parsed = ProviderAdapterConfigV2.from_mapping(candidate)
    require(parsed.enabled, "binding resolved configuration is disabled")
    normalized = parsed.to_mapping()
    del normalized["model_selector"]
    normalized["model"] = model
    require(normalized == config, "binding resolved configuration is not a closed normalized mapping")
    require(inputs.read(config["profile_ref"]) == profile, "binding original profile reference differs from staged profile")
    require(set(config["capabilities"]) <= set(profile["implementation"]["capabilities"]),
            "binding configuration claims capabilities outside its profile")
    require(document["provider_identity"] == profile["identity"], "binding manifest Provider identity differs")
    require(document["adapter_version"] == profile["implementation"]["adapter_version"], "binding adapter version differs")
    require(document["model_policy"] == profile["model"] and document["generation_policy"] == profile["generation"],
            "binding model/generation policy differs")
    require(document["credential_reference"] == config["credential_source"], "binding credential reference differs")
    require(config["model"] == profile["model"]["requested_id"], "binding resolved model differs")
    require(document["transport_identity"]["options"]["max_response_bytes"] == config["transport"]["max_response_bytes"],
            "binding response bound differs")
    _visit_references(inputs, profile)
    _visit_references(inputs, config)
    modules = [item["module"] for item in document["implementation_refs"]]
    require(modules == sorted(set(modules)), "binding implementation modules are duplicated or unordered")
    require(document["transport_identity"]["class"].startswith(document["component_modules"]["transport"] + ".")
            and document["credential_class"].startswith(document["component_modules"]["credential"] + "."),
            "binding component class/module identity differs")
    required = set(MODULES) | set(document["component_modules"].values())
    require(set(modules) == required, "binding manifest omits or adds a declared implementation module")
    paths = [item["source_ref"]["path"] for item in document["implementation_refs"]]
    require(len(paths) == len(set(paths)), "binding implementation source paths are duplicated")
    archived_port = inputs.read_bytes(next(item["source_ref"] for item in document["implementation_refs"]
                                          if item["module"] == "research_workbench.adapters.models.port"))
    for item in document["implementation_refs"]:
        raw = inputs.read_bytes(item["source_ref"])
        compiled = _compiled_callables(raw)
        declared = {name for name in compiled if ".<locals>." not in name}
        require(set(item["callables"]) == declared, "binding archived callable closure differs")
        require(all(compiled[name] == value for name, value in item["callables"].items()),
                "binding archived callable differs from source bytes")
        expected_constants = _source_constants(raw, port_source=archived_port) if item["module"] in MODULES else {}
        require(expected_constants == item["constants"],
                "binding archived policy constants differ from source bytes")
        require(_source_defaults(raw, expected_constants) == item["defaults"], "binding archived callable defaults differ from source bytes")
        require(digest({"callables": item["callables"], "constants": item["constants"], "defaults": item["defaults"]}) == item["runtime_fingerprint"],
                "binding runtime callable/constant root differs")
    result = ProviderBindingManifest(_freeze(document))
    if expected_adapter is not None:
        require(dict(expected_adapter) == {"ref": document["adapter_class"], "version": document["adapter_version"],
                                          "content_hash": result.root}, "Provider closure differs from selected Protocol adapter")
    inputs.recheck()
    return result


def observe_provider_binding(provider, *, inputs: EvaluationInputs, manifest_ref: Mapping[str, Any]) -> dict[str, str]:
    """Match actual source/configuration to the already-selected manifest."""
    manifest = read_provider_binding_manifest(inputs, manifest_ref)
    document = manifest.to_mapping()
    actual = _plain(capture_configured_provider_binding(provider))
    descriptor = actual["descriptor"]
    require(descriptor["profile"] == inputs.read(document["profile_ref"]), "actual profile differs from binding manifest")
    require(descriptor["resolved_config"] == inputs.read(document["resolved_config_ref"]), "actual config differs from binding manifest")
    require(descriptor["transport_identity"] == document["transport_identity"]
            and descriptor["credential_reference"] == document["credential_reference"]
            and _class_name(provider.credential) == document["credential_class"], "actual Provider components differ from manifest")
    require(document["component_modules"] == {"transport": type(provider.transport).__module__,
                                             "credential": type(provider.credential).__module__},
            "actual Provider component modules differ from manifest")
    expected = [{"module": item["module"], "source_sha256": item["source_ref"]["sha256"],
                 "runtime_fingerprint": item["runtime_fingerprint"], "callables": item["callables"]}
                for item in document["implementation_refs"]]
    for state, item in zip(expected, document["implementation_refs"]):
        state["constants"] = item["constants"]
        state["defaults"] = item["defaults"]
    require(actual["sources"] == expected, "actual loaded Provider implementation differs from binding manifest")
    if document["version"] == "1.1.0":
        require(_plain(getattr(provider, "_implementation_closure_ref", None)) == document["implementation_closure_ref"],
                "actual Provider has not opted into selected source graph")
        _checked_source_closure(inputs, document["implementation_closure_ref"], actual=True)
        inputs.recheck()
    else:
        require(getattr(provider, "_implementation_closure_ref", None) is None,
                "source-bound Provider cannot use a legacy binding manifest")
    return {"ref": document["adapter_class"], "version": document["adapter_version"], "content_hash": manifest.root}
