"""Source-derived closure regressions, using local synthetic state only."""

from __future__ import annotations

import copy
import builtins
import dataclasses
import hashlib
import importlib
import json
import reprlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import FunctionType

from research_workbench.adapters.models import provider_source_closure as closure
from research_workbench.validation.schemas import SchemaCatalog

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/provider_source_closure_v1"
RUNTIME_ROOTS = (
    "research_workbench.adapters.models.configured",
    "research_workbench.adapters.models.provider_binding",
    "research_workbench.adapters.models.profile_conformance",
    "research_workbench.adapters.models.profile_conformance_report",
)


class PinnedReader:
    def __init__(self, root):
        self.root = root

    def read_bytes(self, ref):
        return self.root.joinpath(*ref["path"].split("/")).read_bytes()


class ProviderSourceClosureTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        sys.path.insert(0, str(FIXTURES))
        self.addCleanup(sys.path.remove, str(FIXTURES))
        self.provider = importlib.import_module("rwb_source_fixture.provider")
        self.document = closure.produce_source_closure(
            (self.provider.__name__,), source_root=FIXTURES,
            project_root=self.root, archive_prefix="source",
        )
        self.reader = PinnedReader(self.root)

    def verify(self, doc=None):
        return closure.verify_loaded_source_closure(
            self.document if doc is None else doc,
            read_bytes=self.reader.read_bytes, source_root=FIXTURES,
        )

    def write_document(self, doc=None):
        raw = json.dumps(self.document if doc is None else doc, sort_keys=True).encode()
        (self.root / "closure.json").write_bytes(raw)
        return {"path": "closure.json", "sha256": hashlib.sha256(raw).hexdigest()}

    def test_relative_lazy_parent_closure_and_schema(self):
        receipt = self.verify()
        self.assertEqual(receipt["module_count"], 4)
        self.assertFalse(receipt["archived_execution"])
        self.assertTrue(receipt["actual_verified"])
        self.assertIn("rwb_source_fixture", self.document["modules"])
        self.assertIn("rwb_source_fixture.lazy_helper", self.document["modules"])
        self.assertEqual([], SchemaCatalog(root=ROOT / "schemas").validate(closure.KIND, self.document))
        self.assertEqual(self.document, closure.read_source_closure(self.reader, self.write_document()))

    def test_imported_helper_monkeypatch_is_rejected(self):
        with patch.object(self.provider.helper, "transform", lambda value: "drift"):
            with self.assertRaises(closure.SourceClosureError):
                self.verify()

    def test_retained_original_callable_cannot_mask_replaced_binding(self):
        original = self.provider.helper.transform
        replacement = lambda value: "drift"
        package = sys.modules["rwb_source_fixture"]
        with patch.object(self.provider.helper, "retained_original", original, create=True), patch.object(self.provider.helper, "transform", replacement), patch.object(package, "transform", replacement), patch.object(self.provider, "source_alias", replacement):
            with self.assertRaisesRegex(closure.SourceClosureError, "callable binding differs"):
                self.verify()

    def test_undeclared_builtin_shadow_is_rejected(self):
        # typed currently has no builtin lookup; helper transform stays source
        # identical while cached invokes the source-declared helper. The actual
        # provider constructor resolves frozenset as a builtin in its body.
        with patch.object(self.provider, "frozenset", lambda value: "shadow", create=True):
            with self.assertRaisesRegex(closure.SourceClosureError, "builtin shadow"):
                self.verify()

    def test_stale_import_alias_is_rejected(self):
        with patch.object(self.provider, "source_alias", lambda value: "stale"):
            with self.assertRaisesRegex(closure.SourceClosureError, "import alias differs"):
                self.verify()

    def test_source_native_clock_default_is_independent_of_actual(self):
        function = self.provider.Provider.__init__
        original = function.__kwdefaults__
        with patch.object(function, "__kwdefaults__", {**original, "clock": lambda: 0}):
            with self.assertRaises(closure.SourceClosureError):
                self.verify()

    def test_class_policy_and_method_descriptor_drift_are_rejected(self):
        with patch.object(self.provider.Provider, "provider_name", "drift"):
            with self.assertRaisesRegex(closure.SourceClosureError, "class policy differs"):
                self.verify()
        with patch.object(self.provider.Provider, "request", self.provider.Provider.request):
            with self.assertRaisesRegex(closure.SourceClosureError, "method descriptor differs"):
                self.verify()

    def test_wrapper_configuration_drift_is_rejected(self):
        from functools import lru_cache
        with patch.object(self.provider, "cached", lru_cache(maxsize=8)(self.provider.cached.__wrapped__)):
            with self.assertRaisesRegex(closure.SourceClosureError, "cache wrapper differs"):
                self.verify()

    def test_global_policy_and_injected_class_method_are_rejected(self):
        with patch.object(self.provider.helper, "PREFIX", "changed:"):
            with self.assertRaisesRegex(closure.SourceClosureError, "global policy differs"):
                self.verify()
        with patch.object(self.provider.Provider, "injected", lambda self: "drift", create=True):
            with self.assertRaisesRegex(closure.SourceClosureError, "undeclared runtime class callable"):
                self.verify()

    def repr_fixture(self):
        source = self.root / "repr-runtime"
        source.mkdir()
        (source / "repr_source_fixture.py").write_text(
            "from dataclasses import dataclass, field\n"
            "@dataclass(frozen=True, slots=True, kw_only=True)\n"
            "class Record:\n"
            "    value: int\n"
            "    hidden: str = field(repr=False, default='hidden')\n"
            "@dataclass\n"
            "class Custom:\n"
            "    value: int\n"
            "    def __repr__(self):\n"
            "        return 'custom:' + str(self.value)\n",
            encoding="utf-8",
        )
        sys.path.insert(0, str(source))
        self.addCleanup(sys.path.remove, str(source))
        module = importlib.import_module("repr_source_fixture")
        self.addCleanup(sys.modules.pop, "repr_source_fixture", None)
        document = closure.produce_source_closure(
            (module.__name__,), source_root=source, project_root=self.root,
            archive_prefix="repr-source",
        )
        return module, document, source

    def test_generated_dataclass_repr_and_explicit_custom_repr_are_supported(self):
        module, document, source = self.repr_fixture()
        receipt = closure.verify_loaded_source_closure(
            document, read_bytes=self.reader.read_bytes, source_root=source,
        )
        self.assertTrue(receipt["actual_verified"])
        self.assertEqual("Record(value=1)", repr(module.Record(value=1)))
        self.assertEqual("custom:1", repr(module.Custom(1)))
        recursive = module.Record(value=None)
        object.__setattr__(recursive, "value", recursive)
        self.assertEqual("Record(value=...)", repr(recursive))

    def test_generated_repr_captured_builtins_must_be_canonical(self):
        module, document, source = self.repr_fixture()
        original = module.Record.__repr__
        calls = []

        def injected_id(value):
            calls.append("captured id")
            return builtins.id(value)

        class BuiltinsDict(dict):
            def __getitem__(self, name):
                calls.append("dict getter")
                return super().__getitem__(name)

        class BuiltinsMapping:
            def __getitem__(self, name):
                calls.append("mapping getter")
                return vars(builtins)[name]

        def clone_with_builtins(function, mapping):
            globals_ = function.__globals__
            previous = globals_["__builtins__"]
            try:
                globals_["__builtins__"] = mapping
                clone = FunctionType(function.__code__, globals_, function.__name__,
                                     function.__defaults__, function.__closure__)
            finally:
                globals_["__builtins__"] = previous
            clone.__dict__.update(function.__dict__)
            clone.__module__ = function.__module__
            clone.__qualname__ = function.__qualname__
            self.assertIs(previous, globals_["__builtins__"])
            return clone

        for label, mapping in (
            ("replaced captured id", {**vars(builtins), "id": injected_id}),
            ("dict subclass", BuiltinsDict(vars(builtins))),
            ("custom mapping", BuiltinsMapping()),
        ):
            replacement = clone_with_builtins(original, mapping)
            self.assertIs(original.__code__, replacement.__code__)
            self.assertIs(original.__globals__, replacement.__globals__)
            self.assertIs(original.__closure__, replacement.__closure__)
            self.assertIs(original.__wrapped__, replacement.__wrapped__)
            with self.subTest(label=label), patch.object(module.Record, "__repr__", replacement):
                with self.assertRaisesRegex(closure.SourceClosureError, "undeclared runtime class callable"):
                    closure.verify_loaded_source_closure(
                        document, read_bytes=self.reader.read_bytes, source_root=source,
                    )
                self.assertEqual([], calls)

        inner = clone_with_builtins(original.__wrapped__, {**vars(builtins), "id": injected_id})
        namespace = closure._recursive_repr_namespace(original)
        replacement = (reprlib.recursive_repr()(inner) if namespace is reprlib
                       else dataclasses._recursive_repr(inner))
        with patch.object(module.Record, "__repr__", replacement):
            with self.assertRaisesRegex(closure.SourceClosureError, "undeclared runtime class callable"):
                closure.verify_loaded_source_closure(
                    document, read_bytes=self.reader.read_bytes, source_root=source,
                )
            self.assertEqual([], calls)

    def test_injected_and_forged_repr_wrappers_remain_rejected(self):
        module, document, source = self.repr_fixture()
        original = module.Record.__repr__
        original_inner = original.__wrapped__

        def injected(self):
            return "drift"

        injected.__wrapped__ = original_inner
        forged_inner = FunctionType(
            injected.__code__.replace(co_filename="<string>", co_name="__repr__",
                                      co_qualname=original_inner.__code__.co_qualname),
            vars(module), "__repr__",
        )
        wrong_inner = reprlib.recursive_repr()(forged_inner)
        for label, replacement in (
            ("plain injected", injected),
            ("reprlib wrapped ordinary callable", reprlib.recursive_repr()(injected)),
            ("canonical wrapper with forged generated filename", wrong_inner),
        ):
            with self.subTest(label=label), patch.object(module.Record, "__repr__", replacement):
                with self.assertRaisesRegex(closure.SourceClosureError, "undeclared runtime class callable"):
                    closure.verify_loaded_source_closure(
                        document, read_bytes=self.reader.read_bytes, source_root=source,
                    )
        with patch.object(module.Record, "injected", original, create=True):
            with self.assertRaisesRegex(closure.SourceClosureError, "undeclared runtime class callable"):
                closure.verify_loaded_source_closure(
                    document, read_bytes=self.reader.read_bytes, source_root=source,
                )

    def test_repr_field_metadata_rejects_custom_objects_without_calling_them(self):
        module, document, source = self.repr_fixture()
        calls = []

        class Flag:
            def __bool__(self):
                calls.append("flag bool")
                return True

        class Label(str):
            def isidentifier(self):
                calls.append("label isidentifier")
                return True

        class FieldSubclass(dataclasses.Field):
            __slots__ = ()

            def __getattribute__(self, name):
                calls.append("field read:" + name)
                return super().__getattribute__(name)

        class ParametersSubclass(dataclasses._DataclassParams):
            __slots__ = ()

            def __getattribute__(self, name):
                calls.append("parameters read:" + name)
                return super().__getattribute__(name)

        field = module.Record.__dataclass_fields__["value"]
        injected_field = FieldSubclass(dataclasses.MISSING, dataclasses.MISSING, True, True, None, True, None, True)
        replacement_fields = {**module.Record.__dataclass_fields__, "value": injected_field}
        for label, context in (
            ("kw_only custom truth", patch.object(field, "kw_only", Flag())),
            ("field name string subclass", patch.object(field, "name", Label("value"))),
            ("Field subclass", patch.object(module.Record, "__dataclass_fields__", replacement_fields)),
            ("parameter subclass", patch.object(module.Record, "__dataclass_params__", object.__new__(ParametersSubclass))),
        ):
            with self.subTest(label=label), context:
                with self.assertRaisesRegex(closure.SourceClosureError, "undeclared runtime class callable|runtime dataclass metadata differs"):
                    closure.verify_loaded_source_closure(
                        document, read_bytes=self.reader.read_bytes, source_root=source,
                    )
                self.assertEqual([], calls)

    def test_wrong_outer_file_pin_is_rejected(self):
        reference = self.write_document()
        reference["sha256"] = "0" * 64
        with self.assertRaisesRegex(closure.SourceClosureError, "FileRef hash differs"):
            closure.read_source_closure(self.reader, reference)

    def test_coherently_rehashed_false_callable_claim_is_rejected(self):
        doc = copy.deepcopy(self.document)
        doc["modules"][self.provider.__name__]["claims"]["compiled_callables"]["typed"] = "0" * 64
        reference = self.write_document(doc)
        with self.assertRaisesRegex(closure.SourceClosureError, "source-derived claims differ"):
            closure.read_source_closure(self.reader, reference)

    def test_false_default_claim_is_rederived_from_source(self):
        doc = copy.deepcopy(self.document)
        doc["modules"][self.provider.__name__]["claims"]["defaults"]["Provider.__init__"]["keyword"]["clock"] = {"native_ref": "fabricated.clock"}
        with self.assertRaisesRegex(closure.SourceClosureError, "source-derived claims differ"):
            closure.read_source_closure(self.reader, self.write_document(doc))

    def test_missing_parent_and_archived_source_byte_drift_are_rejected(self):
        doc = copy.deepcopy(self.document)
        del doc["modules"]["rwb_source_fixture"]
        with self.assertRaisesRegex(closure.SourceClosureError, "dependency missing"):
            closure.verify_source_closure(doc, read_bytes=self.reader.read_bytes)
        ref = self.document["modules"]["rwb_source_fixture.helper"]["source_ref"]
        self.root.joinpath(*ref["path"].split("/")).write_bytes(b"raise AssertionError('archive must not execute')\n")
        with self.assertRaisesRegex(closure.SourceClosureError, "FileRef hash differs"):
            closure.verify_source_closure(self.document, read_bytes=self.reader.read_bytes)

    def test_typevar_runtime_use_and_unbounded_literal_expansion_are_rejected(self):
        for module, addition in (
            (self.provider.__name__, b"\ndef runtime_typevar_use():\n    return T\n"),
            ("rwb_source_fixture.helper", b'\nEXPANSION = "x" * (10 ** 100)\n'),
        ):
            doc = copy.deepcopy(self.document)
            reference = doc["modules"][module]["source_ref"]
            path = self.root.joinpath(*reference["path"].split("/"))
            original = path.read_bytes()
            altered = original + addition
            path.write_bytes(altered)
            reference["sha256"] = hashlib.sha256(altered).hexdigest()
            try:
                with self.assertRaises(closure.SourceClosureError):
                    closure.verify_source_closure(doc, read_bytes=self.reader.read_bytes)
            finally:
                path.write_bytes(original)

    def test_source_root_cannot_replace_loaded_module_file(self):
        other = self.root / "other/rwb_source_fixture"
        other.mkdir(parents=True)
        for path in (FIXTURES / "rwb_source_fixture").glob("*.py"):
            (other / path.name).write_bytes(path.read_bytes())
        with self.assertRaisesRegex(closure.SourceClosureError, "source location differs"):
            closure.verify_loaded_source_closure(self.document, read_bytes=self.reader.read_bytes, source_root=other.parent)

    def test_cold_subprocess_imports_no_product_and_executes_no_archive(self):
        reference = self.write_document()
        program = r'''
import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location("cold_source_observer",sys.argv[1])
observer=importlib.util.module_from_spec(spec);sys.modules[spec.name]=observer;spec.loader.exec_module(observer)
root=Path(sys.argv[2]);executed=[]
def audit(event,args):
    if event=="exec" and str(args[0].co_filename).startswith(str(root/"source")):
        executed.append(args[0].co_filename);raise AssertionError("archive execution forbidden")
    if event in {"socket.connect","socket.getaddrinfo"}: raise AssertionError("network forbidden")
sys.addaudithook(audit)
class Reader:
    def read_bytes(self,ref):return root.joinpath(*ref["path"].split("/")).read_bytes()
doc=observer.read_source_closure(Reader(),json.loads(sys.argv[3]))
receipt=observer.verify_source_closure(doc,read_bytes=Reader().read_bytes)
assert not any(name.startswith(("research_workbench","rwb_source_fixture")) for name in sys.modules)
assert not executed
print(json.dumps({"module_count":receipt["module_count"],"product_imports":0,"archive_exec":0}))
'''
        result = subprocess.run([sys.executable, "-I", "-c", program, str(Path(closure.__file__).resolve()), str(self.root), json.dumps(reference)], capture_output=True, text=True, timeout=30, check=True)
        self.assertEqual({"module_count": 4, "product_imports": 0, "archive_exec": 0}, json.loads(result.stdout))

    def test_actual_provider_graph_named_closed_registries_and_outside_seven_helper(self):
        source_root = Path(closure.__file__).resolve().parents[3]
        doc = closure.produce_source_closure(RUNTIME_ROOTS, source_root=source_root, project_root=self.root, archive_prefix="runtime")
        modules = doc["modules"]
        self.assertGreaterEqual(len(modules), 32)
        for name in ("research_workbench", "research_workbench.adapters", "research_workbench.evaluation", "research_workbench.validation"):
            self.assertTrue(modules[name]["is_package"])
        self.assertEqual({"typing_only": "T"}, modules["research_workbench.contracts.common"]["claims"]["globals"]["T"])
        self.assertIn("FIXED_METRIC_SET", modules["research_workbench.evaluation.manifest"]["claims"]["globals"])
        receipt = closure.verify_loaded_source_closure(doc, read_bytes=self.reader.read_bytes, source_root=source_root)
        self.assertGreater(receipt["checked"]["callables"], 400)
        pins = importlib.import_module("research_workbench.evaluation.pins")
        with patch.object(pins, "digest", lambda value: "outside-seven-drift"):
            with self.assertRaises(closure.SourceClosureError):
                closure.verify_loaded_source_closure(doc, read_bytes=self.reader.read_bytes, source_root=source_root)
        metrics = importlib.import_module("research_workbench.evaluation.manifest")
        metric = metrics.FIXED_METRIC_SET[0]
        original = metric.definition
        object.__setattr__(metric, "definition", "synthetic-registry-drift")
        try:
            with self.assertRaisesRegex(closure.SourceClosureError, "global policy differs"):
                closure.verify_loaded_source_closure(doc, read_bytes=self.reader.read_bytes, source_root=source_root)
        finally:
            object.__setattr__(metric, "definition", original)


if __name__ == "__main__":
    unittest.main()
