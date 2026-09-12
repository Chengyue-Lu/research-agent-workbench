"""Relocatable project templates using installed resources and explicit roots."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import tempfile
import tomllib
from pathlib import Path

import yaml

from research_workbench.resources import RuntimeResources, no_link, portable, require
from research_workbench.validation.schemas import SchemaCatalog


TEMPLATES = ("no-skill", "offline-demo", "minimal")
TEMPLATE_VERSION = "0.1.0"
DEMO_ROOT = Path(__file__).parent / "_templates/offline-demo/0.1.0"
DEMO_CATALOG_SHA256 = "bd6bb2f5f321adb1907b139bd96228d5b7256e147d3a658f512f7ede6e0b0f18"
DEMO_PATH = "examples/run-reconstruction/linear-recurrence"
DIRECTORIES = ("objects", "tasks", "profiles", "handoffs", "checkpoints", "work")


def _yaml(document):
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False).encode("utf-8")


def _protocol(project_id):
    return {
        "schema_version": "0.1.0", "project_id": project_id, "revision": 1,
        "question_refs": [], "active_modes": [], "claim_ceiling": ["unresolved"],
        "required_human_gates": ["approve_main_claim", "approve_external_release"],
        "budgets": {"max_parallel_subagents": 1, "max_delegation_depth": 1,
                    "coordination_cost_ratio_warn": 0.33},
        "context_policy": {"proactive_checkpoint": True, "main_raw_material": "on-demand"},
        "data_boundary": {"local_only": True, "external_upload_requires_approval": True},
    }


def _demo_files():
    """Read the versioned example closure without executing its code."""
    for path in (DEMO_ROOT, *DEMO_ROOT.parents):
        no_link(path)
    catalog_path = DEMO_ROOT / "catalog.json"
    no_link(catalog_path)
    data = catalog_path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == DEMO_CATALOG_SHA256, "template catalog hash drift")
    entries = json.loads(data)["files"]
    expected = {"catalog.json", *(entry["asset"] for entry in entries)}
    require({p.name for p in DEMO_ROOT.iterdir()} == expected, "template file closure drift")
    files = {}
    for entry in entries:
        asset = DEMO_ROOT / portable(entry["asset"])
        no_link(asset)
        content = asset.read_bytes()
        require(hashlib.sha256(content).hexdigest() == entry["sha256"], "template asset hash drift")
        files[portable(entry["output"])] = content
    # This is an adapted engineering fixture, pinned to the initializing interpreter.
    environment = json.loads(files["environment.json"])
    environment.update(python_implementation=platform.python_implementation(),
                       python_version=platform.python_version(), platform=sys.platform)
    files["environment.json"] = (json.dumps(environment, sort_keys=True, indent=2) + "\n").encode()
    manifest = yaml.safe_load(files["manifest.yaml"])
    environment_ref = dict(manifest["environment_ref"], sha256=hashlib.sha256(files["environment.json"]).hexdigest())
    manifest["environment_ref"] = environment_ref
    manifest["environment_binding"]["file_ref"] = dict(environment_ref)
    files["manifest.yaml"] = _yaml(manifest)
    return {f"{DEMO_PATH}/{name}": content for name, content in files.items()}


def _readme(template):
    text = """# Local research project

This project uses the installed Runtime catalog for Schemas, Modes, Actions,
Authority, Requirements, Protocol Profiles and published Skill projections.
Project files belong to this directory. Platform integrations have a separate,
explicit root. No Registry or Skill directory needs to be copied from a checkout.

Run these commands from this project directory (or pass its absolute path):

```shell
rwb project check .
rwb validate project-protocol.yaml --root .
```

`rwb-project.toml` records the template and exact Runtime manifest digest. Keep
the matching installed package when reopening a project. A changed resource pin
requires an explicit migration; reinitialization never overwrites a project.
The protocol retains human control of claims, release and external uploads.
"""
    if template != "minimal":
        text += """
The no-Skill Task and its local Profile are ready for structural validation:

```shell
rwb validate tasks/task.yaml profiles/local-no-skill.yaml --root .
```

Edit the goal, inputs, write scope and outputs for your bounded task. The template
does not select a Provider, provision credentials, or run a model. The installed
production Skill projection index may be empty.
"""
    if template == "offline-demo":
        text += f"""
## Offline engineering example

The files under `{DEMO_PATH}` are a synthetic integer-recurrence fixture.
The archived Run and expected trajectory are reference data, not a run performed
by initialization. Its environment binding is adapted to this Python interpreter.
Inspect `manifest.yaml` to locate exact code, input, parameter and expected-output
bytes. These commands check the pins without executing code:

```shell
rwb run check {DEMO_PATH}/manifest.yaml --root .
rwb hash {DEMO_PATH}/trajectory.csv
```

After inspecting the example code, explicitly reconstruct it in a fresh process:

```shell
rwb run reproduce {DEMO_PATH}/manifest.yaml --root . --attempt-dir work/demo/A-001
rwb validate work/demo/A-001/reconstruction-report.json --root .
```

The report locates the captured input and actual output evidence. A new attempt
directory is required for every run. A matched result proves this bounded file
reconstruction; it does not accept a scientific Claim. Reproduction is not an OS
sandbox and should only execute code you trust. Initialization never runs it.
"""
    return text.encode("utf-8")


def initialize_project(path, *, project_id=None, template="no-skill", resources=None):
    require(template in TEMPLATES, "unknown project template")
    requested = Path(path).absolute()
    for ancestor in (requested, *requested.parents):
        if ancestor.exists() or ancestor.is_symlink():
            no_link(ancestor)
    root = requested.resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"refusing to initialize a non-empty directory: {root}")
    identifier = project_id if project_id is not None else root.name
    require(isinstance(identifier, str) and bool(identifier.strip()), "project ID must be non-empty")
    resources = resources or RuntimeResources()
    resources.validate_catalog()
    catalog = SchemaCatalog(resource_reader=resources, root=resources.schema_root)
    protocol = _protocol(identifier)
    require(not catalog.validate("project_protocol", protocol), "invalid project protocol template")
    files = {"project-protocol.yaml": _yaml(protocol), "README.md": _readme(template)}
    metadata = {"format_version": "0.1.0", "project_id": identifier, "template": template,
                "template_version": TEMPLATE_VERSION,
                "runtime_manifest_sha256": hashlib.sha256((resources.root / "manifest.json").read_bytes()).hexdigest()}
    files["rwb-project.toml"] = ("\n".join(f"{key} = {json.dumps(value, ensure_ascii=False)}"
                                            for key, value in metadata.items()) + "\n").encode("utf-8")
    if template != "minimal":
        task = yaml.safe_load(resources.read("examples/quickstart/task-no-skill.yaml"))
        task["agent_profile"] = "local-no-skill"
        profile = {"schema_version": "0.1.0", "agent_profile_id": "local-no-skill", "version": "0.1.0",
                   "purpose": "Prepare one bounded local no-Skill handoff.",
                   "model_policy": {"class": "unbound"},
                   "permission_ceiling": {"filesystem": "worktree-write", "network": "forbidden",
                                          "external_write": False, "allowed_roots": ["work/QUICKSTART-001"]},
                   "allowed_tool_capabilities": ["document-read"], "default_context_policy": "isolated-task",
                   "delegation": {"allowed": False}, "output_contracts": ["handoff-packet"]}
        require(not catalog.validate("task_packet", task), "invalid no-Skill Task template")
        require(not catalog.validate("agent_profile", profile), "invalid local Profile template")
        files.update({"tasks/task.yaml": _yaml(task), "profiles/local-no-skill.yaml": _yaml(profile)})
    if template == "offline-demo":
        files.update(_demo_files())
    root.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".rwb-init-", dir=root.parent) as temporary:
        require(Path(temporary).resolve().parent == root.parent, "staging directory escaped project parent")
        stage = Path(temporary) / "project"
        stage.mkdir()
        for directory in DIRECTORIES:
            (stage / directory).mkdir()
        for name, content in files.items():
            target = stage / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        replaced_empty = root.exists()
        if replaced_empty:
            no_link(root)
            root.rmdir()  # Only an empty destination may be replaced.
        try:
            stage.rename(root)
        except OSError:
            if replaced_empty and not root.exists():
                root.mkdir()
            raise
    return {"project_id": identifier, "project_root": str(root), "runtime_root": str(resources.root),
            "runtime_manifest_sha256": metadata["runtime_manifest_sha256"], "template": template,
            "template_version": TEMPLATE_VERSION, "files": sorted(files), "executed": False}


def check_project(path, *, resources=None):
    """Validate project setup without executing a Task or discovering other roots."""
    root = Path(path).absolute()
    for ancestor in (root, *root.parents):
        no_link(ancestor)
    metadata_path = root / "rwb-project.toml"
    no_link(metadata_path)
    metadata = tomllib.loads(metadata_path.read_text(encoding="utf-8"))
    require(metadata.get("format_version") == "0.1.0", "unsupported project format; explicit migration required")
    require(metadata.get("template") in TEMPLATES and metadata.get("template_version") == TEMPLATE_VERSION,
            "unsupported project template version; explicit migration required")
    resources = resources or RuntimeResources()
    summary = resources.validate_catalog()
    require(metadata.get("runtime_manifest_sha256") == hashlib.sha256((resources.root / "manifest.json").read_bytes()).hexdigest(),
            "project Runtime pin differs from installed resources; use the matching package or an explicit migration")
    catalog = SchemaCatalog(resource_reader=resources, root=resources.schema_root)
    documents = [("project-protocol.yaml", "project_protocol")]
    if metadata["template"] != "minimal":
        documents += [("tasks/task.yaml", "task_packet"), ("profiles/local-no-skill.yaml", "agent_profile")]
    loaded = {}
    for name, kind in documents:
        target = root / name
        for component in (target, *target.parents[:target.parents.index(root)]):
            no_link(component)
        loaded[kind] = yaml.safe_load(target.read_bytes())
        require(not catalog.validate(kind, loaded[kind]), f"invalid project document: {name}")
    require(loaded["project_protocol"]["project_id"] == metadata.get("project_id"), "project identity mismatch")
    if "task_packet" in loaded:
        require(loaded["task_packet"]["agent_profile"] == loaded["agent_profile"]["agent_profile_id"], "Task/Profile identity mismatch")
    if metadata["template"] == "offline-demo":
        from research_workbench.artifacts.run_reconstruction import check_run_manifest
        manifest_path = root / DEMO_PATH / "manifest.yaml"
        for component in (manifest_path, *manifest_path.parents[:manifest_path.parents.index(root)]):
            no_link(component)
        require(not check_run_manifest(root, yaml.safe_load(manifest_path.read_bytes())), "offline example pins are invalid")
    return {"project_id": metadata["project_id"], "project_root": str(root), "runtime_root": str(resources.root),
            "runtime_manifest_sha256": metadata["runtime_manifest_sha256"], "template": metadata["template"],
            "resources": summary, "executed": False}
