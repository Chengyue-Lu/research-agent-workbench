"""Staged fresh-actor consumer for the Phase C bounded behavioral gates.

Run as a fresh process:

    python -m research_workbench.research_state.fresh_actor <case_dir> <answer_path>

Discipline (M10-003 acceptance):
- the actor receives the case directory from the runner and locates the
  active research state and its active method trace;
- every further file is opened ONLY by convention path from an exact ref
  (``objects/<id>.yaml``, ``failures/<id>.yaml``, ``decisions/<id>.yaml``,
  ``states/<id>.yaml``, ``tasks/<id>.yaml``);
- the actor never scans unrelated case files and never reads the original
  chat, the oracle notes, or the expected answer;
- every opened path is recorded in the answer's ``read_surface`` so the
  private oracle can verify the exact read closure;
- any closure problem blocks fail-closed instead of guessing.

Fixed choice set rule: ``choices.yaml`` declares each candidate action and
may mark it with ``repeats_failure_ref`` (the failure whose path it would
redo).  The actor refuses such choices while the revisit condition is unmet
(``known-failed-avoid``), marks them ``reviewable`` when the recorded
condition appears changed, and never auto-reruns anything: a reviewable path
is surfaced, not recommended.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from research_workbench.io import load_document
from research_workbench.research_state.closure import _parse_object_ref

CONVENTION_DIRS = ("objects", "failures", "decisions", "states", "tasks")


class RecordingLoader:
    """Opens documents only via ref convention and records every path."""

    def __init__(self, case_root: Path) -> None:
        self.case_root = Path(case_root).resolve()
        self.read_surface: list[str] = []
        self._cache: dict[str, Any] = {}

    def _open(self, path: Path) -> Any:
        relative = path.resolve().relative_to(self.case_root).as_posix()
        if relative not in self.read_surface:
            self.read_surface.append(relative)
        if relative not in self._cache:
            self._cache[relative] = load_document(path)
        return self._cache[relative]

    def load_active_state(self) -> Mapping[str, Any]:
        best: tuple[int, Mapping[str, Any]] | None = None
        for candidate in sorted((self.case_root / "states").glob("*.yaml")):
            document = self._open(candidate)
            if not isinstance(document, Mapping) or document.get("status") != "active":
                continue
            revision = document.get("revision", 0)
            if best is None or revision > best[0]:
                best = (revision, document)
        if best is None:
            raise ValueError("no active research state in case")
        return best[1]

    def load_trace_for(self, state_id: str) -> Mapping[str, Any]:
        for candidate in sorted((self.case_root / "traces").glob("*.yaml")):
            document = self._open(candidate)
            if (
                isinstance(document, Mapping)
                and document.get("status") == "active"
                and isinstance(document.get("subject_state_ref"), Mapping)
                and document["subject_state_ref"].get("object_id") == state_id
            ):
                return document
        raise ValueError(f"no active method trace for state {state_id}")

    def resolve_ref(self, raw_ref: Any) -> Mapping[str, Any]:
        object_id, revision, declared_sha256 = _parse_object_ref(raw_ref)
        for directory in CONVENTION_DIRS:
            for suffix in (".yaml", ".yml", ".json"):
                candidate = self.case_root / directory / f"{object_id}{suffix}"
                if not candidate.is_file():
                    continue
                document = self._open(candidate)
                if not isinstance(document, Mapping):
                    continue
                if revision is not None and document.get("revision") != revision:
                    continue
                # exact closure: a pinned ref must match the target's declared
                # object-content pin, fail-closed before the actor reads on
                if declared_sha256 is not None:
                    content_hash = document.get("content_hash")
                    if (
                        content_hash is None
                        or declared_sha256.removeprefix("sha256:").lower()
                        != str(content_hash).removeprefix("sha256:").lower()
                    ):
                        raise ValueError(
                            f"ref pin drift: {object_id}@{revision} sha256 does not "
                            "match the target's declared content_hash"
                        )
                return document
        raise ValueError(f"ref does not resolve by convention: {object_id}@{revision}")

    def load_declared(self, relative: str) -> Any:
        """Load a runner-declared fixture input (``*.yaml.txt`` on purpose).

        The ``.txt`` suffix keeps these fixtures out of repository document
        discovery; they are parsed here as plain YAML text instead.
        """

        path = self.case_root / relative
        if not path.is_file():
            raise ValueError(f"declared fixture input is missing: {relative}")
        text = path.read_text(encoding="utf-8")
        if relative not in self.read_surface:
            self.read_surface.append(relative)
        import yaml

        return yaml.safe_load(text)


def _ref_string(raw: Any) -> str:
    object_id, revision, _ = _parse_object_ref(raw)
    return f"{object_id}@{revision}"


def run_actor(case_dir: Path) -> dict[str, Any]:
    loader = RecordingLoader(case_dir)
    state = loader.load_active_state()
    state_id = state["state_id"]
    trace = loader.load_trace_for(state_id)

    loaded_entries: list[tuple[str, Mapping[str, Any]]] = []
    for entry in state.get("entries", []):
        if entry.get("disposition") != "current":
            continue
        document = loader.resolve_ref(entry["ref"])
        loaded_entries.append((_ref_string(entry["ref"]), document))

    key_evidence_refs: list[str] = []
    claim_limitations: list[dict[str, Any]] = []
    for identifier, document in loaded_entries:
        if document.get("object_type") != "claim":
            continue
        for raw in document.get("support_refs", []) + document.get("counterevidence_refs", []):
            key_evidence_refs.append(_ref_string(raw))
        claim_limitations.append(
            {"claim": identifier, "limitations": document.get("limitations", [])}
        )

    decision_effects: list[dict[str, Any]] = []
    for event in trace.get("events", []):
        if event.get("family") != "human-decision-applied":
            continue
        decision_ref = (event.get("refs") or {}).get("decision_ref")
        if decision_ref is None:
            continue
        decision = loader.resolve_ref(decision_ref)
        decision_effects.append(
            {
                "decision_id": decision.get("decision_id"),
                "decision_kind": decision.get("decision_kind"),
                "actor": decision.get("actor"),
                "rationale": decision.get("rationale"),
            }
        )

    known_failures: list[Mapping[str, Any]] = []
    for raw in state.get("revisit_refs", []):
        known_failures.append(loader.resolve_ref(raw))

    # runner-declared fixture inputs carry the .txt suffix on purpose: they
    # are runner fixtures, not schema documents, and must stay invisible to
    # repository document discovery (rwb validate).
    revisit_status: Mapping[str, Any] = loader.load_declared("revisit-status.yaml.txt")
    revisit_met = bool(revisit_status.get("revisit_condition_met", False))

    declared_choices = loader.load_declared("choices.yaml.txt")
    choices = (
        list(declared_choices.get("choices", []))
        if isinstance(declared_choices, Mapping)
        else []
    )

    known_failure_ids = {
        failure.get("failure_id") for failure in known_failures if isinstance(failure, Mapping)
    }
    classified: list[dict[str, Any]] = []
    for choice in choices:
        repeats = choice.get("repeats_failure_ref")
        if repeats in known_failure_ids:
            classification = "reviewable" if revisit_met else "known-failed-avoid"
        else:
            classification = "recommendable"
        classified.append(
            {"choice_id": choice.get("choice_id"), "classification": classification}
        )
    recommended = next(
        (item["choice_id"] for item in classified if item["classification"] == "recommendable"),
        None,
    )

    return {
        "status": "ok",
        "active_state": f"{state_id}@{state.get('revision')}",
        "key_evidence_refs": sorted(set(key_evidence_refs)),
        "claim_limitations": claim_limitations,
        "decision_effects": decision_effects,
        "open_items": [
            {"item_id": item.get("item_id"), "kind": item.get("kind"), "status": item.get("status")}
            for item in state.get("open_items", [])
        ],
        "invalidated_items": [
            item.get("item_id")
            for item in state.get("open_items", [])
            if item.get("status") == "invalidated"
        ],
        "known_failed_paths": [
            {
                "failure_id": failure.get("failure_id"),
                "learned_result": failure.get("learned_result"),
                "revisit_condition": failure.get("revisit_condition"),
                "revisit_condition_met": revisit_met,
            }
            for failure in known_failures
        ],
        "choices": classified,
        "recommended_action": recommended,
        "read_surface": sorted(loader.read_surface),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = argv if argv is not None else sys.argv[1:]
    if len(arguments) != 2:
        print(
            "usage: python -m research_workbench.research_state.fresh_actor <case_dir> <answer_path>",
            file=sys.stderr,
        )
        return 2
    case_dir = Path(arguments[0])
    answer_path = Path(arguments[1])
    try:
        answer = run_actor(case_dir)
    except Exception as exc:  # closure problems block instead of guessing
        answer_path.write_text(
            json.dumps({"status": "blocked", "problems": [str(exc)]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return 1
    answer_path.write_text(
        json.dumps(answer, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
