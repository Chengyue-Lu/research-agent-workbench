"""Optional API role-control factory over explicit pinned external facts.

This factory creates no conformance, source qualification or Human acceptance.
Dispatch and material authorization remain the responsibility of the caller.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Sequence

from research_workbench.capability.resolver import permission_policy_covers
from research_workbench.contracts.common import PermissionPolicy
from research_workbench.entry.binding import (
    EntryBindingError, freeze_capability_selection, freeze_execution_inputs,
)
from research_workbench.entry.driver import ObservedExecutionBinding
from research_workbench.entry.executor import FrozenRoleBinding
from research_workbench.entry.workflow import RoleInvocation
from research_workbench.execution.execution_view import PinnedExecutionInput
from research_workbench.execution.generic_closeout import CloseoutPin
from research_workbench.io import load_document_bytes
from research_workbench.validation.schemas import SchemaCatalog


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def _bytes(value):
    return (json.dumps(_plain(value), ensure_ascii=False, sort_keys=True,
                       indent=2, allow_nan=False) + "\n").encode("utf-8")


def _pin(value):
    path = value["path"] if isinstance(value, Mapping) else value.path
    digest = value["sha256"] if isinstance(value, Mapping) else value.sha256
    digest = digest.lower().removeprefix("sha256:")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise EntryBindingError("actual file SHA256 pin is required")
    return PinnedExecutionInput(path, digest)


def _path(root, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or ":" in relative or PurePosixPath(relative).is_absolute()
            or any(p in {"", ".", ".."} for p in relative.split("/"))):
        raise EntryBindingError("portable exact project-relative path required")
    result = (root / relative).resolve()
    if result == root or root not in result.parents:
        raise EntryBindingError("path escapes project root")
    return result


def _within(relative, anchor):
    anchor = anchor.removesuffix("/**").rstrip("/")
    return relative == anchor or relative.startswith(anchor + "/")


class ApiRoleBindingFactory:
    """Freeze one no-Skill Action/Requirement slice for each actual invocation.

    All pins belong to project root, including the actual call_intake outputs.
    observed_binding is an independent caller callback, never a selected View copy.
    archive_scope optionally chooses a Task-owned directory for each invocation;
    otherwise output_directory is used when within that Task, or its first plain
    write_scope anchor. The factory never runs the Host, Provider or Tool.
    """

    def __init__(self, root, *, provider,
                 observed_binding: Callable[[Any], ObservedExecutionBinding],
                 task_pin, profile_pin, method_pin, requirement_pin,
                 supplies: Sequence[Any], conformance_refs: Sequence[Any],
                 evidence_check: Callable, data_policy_pin, host_policy_pin,
                 timestamp: Callable[[], str], output_directory: str,
                 output_contract: str, action_ref: str | None = None,
                 planning_action_id: str | None = None,
                 archive_scope: Callable[[RoleInvocation], str] | None = None,
                 tools=(), tool_refs=None, session_limits=None,
                 host_clock=None, session_clock=None, schema_root=None):
        self.root = Path(root).resolve()
        self.catalog_root = Path(schema_root).resolve() if schema_root is not None else None
        self.catalog = SchemaCatalog(self.catalog_root)
        if not all(callable(item) for item in (observed_binding, evidence_check, timestamp)):
            raise EntryBindingError("independent observer, verifier and timestamp callbacks are required")
        if (sum(value is not None for value in (action_ref, planning_action_id)) != 1
                or not isinstance(action_ref or planning_action_id, str)
                or not (action_ref or planning_action_id).strip() or not output_contract):
            raise EntryBindingError("exactly one explicit Action/planning selector and output contract required")
        self.provider, self.observer = provider, observed_binding
        self.task_pin, self.profile_pin = _pin(task_pin), _pin(profile_pin)
        self.method_pin, self.requirement_pin = _pin(method_pin), _pin(requirement_pin)
        self.supplies = tuple(_pin(p) for p in supplies)
        self.conformance = tuple(_pin(p) for p in conformance_refs)
        self.data_policy, self.host_policy = _pin(data_policy_pin), _pin(host_policy_pin)
        if not self.supplies or not self.conformance:
            raise EntryBindingError("actual non-fixture Supply and typed evidence pins required")
        self.verifier, self.timestamp = evidence_check, timestamp
        self.output_directory, self.archive_scope = output_directory, archive_scope
        _path(self.root, output_directory)
        self.action_field = "action_ref" if action_ref is not None else "planning_action_id"
        self.action_ref = action_ref if action_ref is not None else planning_action_id
        self.output_contract = output_contract
        self.tools, self.tool_refs = tuple(tools), dict(tool_refs or {})
        if any(tool.side_effect != "read-only" for tool in self.tools):
            raise EntryBindingError("only explicitly readonly ClientTools are supported")
        if self.tools and session_limits is None:
            raise EntryBindingError("Tools require explicit Session limits")
        self.session_limits, self.host_clock = session_limits, host_clock
        self.session_clock = session_clock
        self.root_task = self._read(self.task_pin, "task_packet")
        self.root_method = self._read(self.method_pin, "method_resolution")
        self.profile = self._read(self.profile_pin, "agent_profile")
        self.requirement = self._read(self.requirement_pin, "capability_requirement")
        self._task_methods = {self.root_task["task_id"]: (self.root_task, self.task_pin, self.method_pin)}
        self._parent_methods = {self.root_task["task_id"]: self.method_pin}
        self._active_depth = {}
        self.records = []
        self._record_refs: list[PinnedExecutionInput] = []

    @property
    def record_refs(self) -> tuple[PinnedExecutionInput, ...]:
        """Pins of exclusively published records; never discover archive files."""
        return tuple(self._record_refs)

    def _read(self, pin, kind):
        path = _path(self.root, pin.path)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin.sha256:
            raise EntryBindingError("input pin drift: " + pin.path)
        document = load_document_bytes(path, raw)
        errors = self.catalog.validate(kind, document)
        if errors or not isinstance(document, Mapping):
            raise EntryBindingError("invalid pinned " + kind)
        return copy.deepcopy(dict(document))

    def _write(self, directory, name, document, kind=None):
        if kind and self.catalog.validate(kind, document):
            raise EntryBindingError("derived document schema invalid: " + kind)
        raw = _bytes(document)
        target = directory / name
        with target.open("xb") as stream:
            stream.write(raw)
        return PinnedExecutionInput(target.relative_to(self.root).as_posix(), hashlib.sha256(raw).hexdigest())

    def __call__(self, invocation: RoleInvocation) -> FrozenRoleBinding:
        if invocation.role not in {"main", "child", "handoff"}:
            raise EntryBindingError("factory does not implement intake or independent Guide")
        if type(invocation.ordinal) is not int or invocation.ordinal <= 0 or type(invocation.depth) is not int or invocation.depth < 0:
            raise EntryBindingError("actual positive invocation ordinal/nonnegative depth required")
        task = _plain(invocation.task)
        if self.catalog.validate("task_packet", task) or task.get("required_skills"):
            raise EntryBindingError("valid actual no-Skill Task required")
        if (task["agent_profile"] not in {self.profile["agent_profile_id"],
                self.profile["agent_profile_id"] + "@" + self.profile["version"]}
                or not permission_policy_covers(PermissionPolicy.from_mapping(self.profile["permission_ceiling"]),
                                                PermissionPolicy.from_mapping(task["permissions"]))):
            raise EntryBindingError("actual Task identity/permissions exceed supplied Profile")
        if self._read(self.profile_pin, "agent_profile") != self.profile:
            raise EntryBindingError("actual Profile changed before freeze")
        if self._read(self.requirement_pin, "capability_requirement") != self.requirement:
            raise EntryBindingError("actual Requirement changed before freeze")
        task_id = task["task_id"]
        known = self._task_methods.get(task_id)
        if known is not None and task != known[0]:
            raise EntryBindingError("Task identity reused with different actual content")
        if invocation.depth == 0 and task != self.root_task:
            raise EntryBindingError("initial/consuming main must use actual intake Task")
        parent = self._active_depth.get(invocation.depth - 1) if invocation.depth else None
        if known is None and parent is None:
            raise EntryBindingError("child has no actual invoked parent Method")
        parent_method_pin = known[2] if known else parent[2]
        parent_method = self._read(parent_method_pin, "method_resolution")
        requested = set(task["required_capabilities"])
        method_caps = {c for d in parent_method["action_decisions"] for c in d["capability_requirements"]}
        if requested != method_caps:
            raise EntryBindingError("child needs a new actual Method for changed capability demand")
        rid = self.requirement["requirement_id"]
        selected_actions = [d for d in parent_method["action_decisions"]
                            if d.get(self.action_field) == self.action_ref]
        if len(selected_actions) != 1 or rid not in selected_actions[0]["capability_requirements"]:
            raise EntryBindingError("selector must match one actual Method Action with supplied Requirement")
        root_name = self.archive_scope(invocation) if self.archive_scope else self.output_directory
        if not any(_within(root_name, a) for a in task["write_scope"]):
            if self.archive_scope is not None:
                raise EntryBindingError("explicit archive scope exceeds actual Task")
            root_name = task["write_scope"][0].removesuffix("/**")
        relative = root_name.rstrip("/") + f"/role-{invocation.ordinal:04d}-{hashlib.sha256(_bytes(task)).hexdigest()[:12]}"
        _path(self.root, relative)
        permissions = task["permissions"]
        if (permissions["filesystem"] not in {"worktree-write", "workspace-write"}
                or not any(_within(relative, a) for a in task["write_scope"])
                or not any(_within(relative, a) for a in permissions.get("allowed_roots", []))):
            raise EntryBindingError("actual Task cannot write this per-role archive")
        directory = _path(self.root, relative)
        directory.mkdir(parents=True, exist_ok=False)
        if known:
            task_pin, method_pin = known[1], known[2]
            if self._read(task_pin, "task_packet") != task:
                raise EntryBindingError("actual Task changed before role freeze")
        else:
            task_pin = self._write(directory, "child-task.json", task, "task_packet")
            derived = copy.deepcopy(parent_method)
            derived["resolution_id"] += "-child-" + hashlib.sha256(_bytes(task)).hexdigest()[:12]
            derived["task_ref"] = {"task_id": task_id, "revision": task.get("revision", 1), "sha256": task_pin.sha256}
            derived["limitations"] = list(dict.fromkeys([*derived["limitations"],
                "Child reuses actual parent Method obligations; this is not new method/Human acceptance."]))
            method_pin = self._write(directory, "child-method.json", derived, "method_resolution")
        evidence_docs = {p.path: self._read(p, "capability_conformance_evidence") for p in self.conformance}
        if any(d["evidence_kind"] == "deterministic-fixture" or d["scope"]["scope_kind"] == "synthetic-bounded-fixture"
               for d in evidence_docs.values()):
            raise EntryBindingError("fixture evidence cannot qualify this real entry slice")
        report_docs = {p.path: self._read(p, "capability_supply_report") for p in self.supplies}
        if any(d["observation_scope"] == "synthetic-bounded-fixture" or d["availability"]["scope"]["scope_kind"] == "fixture-only"
               or d["supply_identity"]["supply_kind"] == "skill" for d in report_docs.values()):
            raise EntryBindingError("fixture/Skill Supply not supported by this no-Skill factory")
        observed = self.observer(self.provider)
        if not isinstance(observed, ObservedExecutionBinding) or set(observed.binding) != {"provider", "adapter", "model", "runtime", "host"}:
            raise EntryBindingError("independent exact five-component observation required")
        if observed.binding["provider"]["ref"] != self.provider.capabilities().provider:
            raise EntryBindingError("actual Provider disagrees with observer")
        instant = self.timestamp()
        parsed = datetime.fromisoformat(instant.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise EntryBindingError("actual timezone-aware timestamp callback required")
        selected = freeze_capability_selection(self.root, task=task_pin, method=method_pin,
            requirement=self.requirement_pin, supplies=self.supplies,
            supporting_documents=[{"kind": "capability_conformance_evidence", "path": p.path, "sha256": p.sha256}
                                  for p in self.conformance], evidence_check=self.verifier,
            output_directory=relative + "/selection", resolution_id=f"ROLE-RES-{invocation.ordinal}",
            snapshot_id=f"ROLE-SNAP-{invocation.ordinal}", evaluated_at=instant,
            qualification="runtime-execution", schema_root=self.catalog_root)
        if selected.status != "satisfied" or selected.snapshot is None or selected.resolution is None:
            raise EntryBindingError("actual capability freeze blocked; see " + selected.summary_path)
        snapshot = self._read(selected.snapshot, "resolved_capability_snapshot")
        chosen = snapshot["selected_supply_report_ref"]
        if chosen["ref"] != observed.supply_report_ref:
            raise EntryBindingError("independently observed Supply differs from Resolver selection")
        supply_pin = PinnedExecutionInput(chosen["document_path"], chosen["content_hash"].removeprefix("sha256:"))
        supply = self._read(supply_pin, "capability_supply_report")
        refs = {p.path: p for p in self.conformance}
        used_evidence = []
        for item in supply["conformance_evidence"]:
            p = _pin(item["artifact_ref"])
            if p != refs.get(p.path):
                raise EntryBindingError("selected Supply evidence is not an actual supplied pin")
            used_evidence.append(p)
        binding = {"schema_version": "0.1.0", "binding_id": f"ROLE-BIND-{invocation.ordinal}", "revision": 1,
            "selected_supply_report_ref": observed.supply_report_ref, **_plain(observed.binding),
            "boundaries": {"supply_selection": False, "automatic_fallback": False,
                           "permission_grant": False, "method_decision": False}}
        binding_pin = self._write(directory, "observed-binding.json", binding, "execution_binding")
        documents = [("task_packet", task_pin), ("method_resolution", method_pin),
                     ("capability_requirement", self.requirement_pin), ("capability_supply_report", supply_pin),
                     ("capability_resolution", selected.resolution), ("resolved_capability_snapshot", selected.snapshot)]
        documents += [("capability_conformance_evidence", p) for p in used_evidence]
        edges = [(selected.snapshot, p, relation) for p, relation in (
            (task_pin, "snapshot-task"), (method_pin, "snapshot-method"),
            (self.requirement_pin, "snapshot-requirement"), (selected.resolution, "snapshot-resolution"),
            (supply_pin, "snapshot-supply"))]
        edges += [(selected.snapshot, p, "snapshot-conformance") for p in used_evidence]
        edges += [(method_pin, task_pin, "method-task"), (selected.resolution, method_pin, "resolution-method"),
                  (selected.resolution, self.requirement_pin, "resolution-requirement"),
                  (selected.resolution, supply_pin, "resolution-candidate-supply")]
        edges += [(supply_pin, p, "supply-conformance") for p in used_evidence]
        manifest = {"schema_version": "0.1.0", "bundle_id": f"ROLE-BUNDLE-{invocation.ordinal}", "revision": 1,
            "profile": "runtime-bundle", "execution_scope": {
                "kind": "action-capability-slice" if self.action_field == "action_ref" else "planning-capability-slice",
                self.action_field: self.action_ref,
                "requirement_id": rid, "task_capability_closure": {"required": list(task["required_capabilities"]),
                    "closed": [rid], "task_completion": False}},
            "entrypoint": {"kind": "resolved_capability_snapshot", "path": selected.snapshot.path, "sha256": selected.snapshot.sha256},
            "documents": [{"kind": kind, "path": p.path, "sha256": p.sha256} for kind, p in documents],
            "imports": [{"from_path": p.path, "to_path": q.path, "relation": relation} for p, q, relation in edges],
            "skill_extension": {"enabled": False},
            "boundaries": {"supply_selection": False, "execution_authority": False,
                           "permission_grant": False, "fallback_authority": False}}
        frozen = freeze_execution_inputs(self.root, manifest=manifest, agent_profile=self.profile_pin,
            data_policy=self.data_policy, host_policy=self.host_policy, execution_binding=binding_pin,
            output_directory=relative + "/execution-inputs", execution_at=instant,
            view_id=f"ROLE-VIEW-{invocation.ordinal}", schema_root=self.catalog_root)
        self._task_methods[task_id] = (copy.deepcopy(task), task_pin, method_pin)
        self._parent_methods.setdefault(task_id, parent_method_pin)
        self._active_depth = {depth: item for depth, item in self._active_depth.items() if depth < invocation.depth}
        self._active_depth[invocation.depth] = self._task_methods[task_id]
        record = {"role": invocation.role, "ordinal": invocation.ordinal, "depth": invocation.depth,
            "selected_action": {"field": self.action_field, "value": self.action_ref},
            "task": {"path": task_pin.path, "sha256": task_pin.sha256},
            "method": {"path": method_pin.path, "sha256": method_pin.sha256},
            "parent_method": {"path": self._parent_methods[task_id].path,
                              "sha256": self._parent_methods[task_id].sha256},
            "requirement": {"path": self.requirement_pin.path, "sha256": self.requirement_pin.sha256},
            "profile": {"path": self.profile_pin.path, "sha256": self.profile_pin.sha256},
            "observed_binding": {"path": binding_pin.path, "sha256": binding_pin.sha256},
            "selected_supply": {"path": supply_pin.path, "sha256": supply_pin.sha256},
            "conformance": [{"path": p.path, "sha256": p.sha256} for p in used_evidence],
            "resolution": {"path": selected.resolution.path, "sha256": selected.resolution.sha256},
            "snapshot": {"path": selected.snapshot.path, "sha256": selected.snapshot.sha256},
            "selection_summary": selected.summary_path, "execution_summary": frozen.summary_path,
            "evaluated_at": instant, "archive_scope": relative,
            "bundle": {"path": frozen.bundle.path, "sha256": frozen.bundle.sha256},
            "view": {"path": frozen.view.path, "sha256": frozen.view.sha256},
            "limitations": ["Exact local procedure evidence is not Provider live/Source/Human admission.",
                            "No Host, Provider or Tool is run by this factory."]}
        record_pin = self._write(directory, "FACTORY.json", record)
        self.records.append(record)
        self._record_refs.append(record_pin)
        return FrozenRoleBinding(bundle_ref=CloseoutPin(frozen.bundle.path, frozen.bundle.sha256),
            view_ref=CloseoutPin(frozen.view.path, frozen.view.sha256), provider=self.provider,
            binding_observer=self.observer, output_dir=relative + "/attempt",
            output_path=relative + "/result.txt", output_contract=self.output_contract,
            attempt_id=f"ROLE-{invocation.ordinal}", schema_root=self.catalog_root,
            tools=self.tools, tool_refs=dict(self.tool_refs), session_limits=self.session_limits,
            host_clock=self.host_clock, session_clock=self.session_clock)


__all__ = ["ApiRoleBindingFactory"]
