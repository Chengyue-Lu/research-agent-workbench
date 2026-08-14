"""Deterministic evidence checks evaluated at closeout.

These checks prove structure and provenance only: the structured model
output conforms to the frozen output schema, the evidence record carries
the pinned source hash, and the source locator is present. A pass never
asserts scientific correctness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from research_workbench.execution.compiler import EVIDENCE_OUTPUT_SCHEMA
from research_workbench.tasks import TaskPacket


CHECKER_ID = "k-api-2-closeout-checks"
CHECKER_VERSION = "0.1.0"
CHECKER_REPO_PATH = "src/research_workbench/execution/checks.py"

_EVIDENCE_VALIDATOR = Draft202012Validator(EVIDENCE_OUTPUT_SCHEMA)


@dataclass(frozen=True, slots=True)
class CheckOutcome:
    code: str
    status: str
    detail: str

    @property
    def passed(self) -> bool:
        return self.status == "pass"


def evaluate_evidence_checks(
    structured_output: Mapping[str, Any], task: TaskPacket
) -> tuple[CheckOutcome, ...]:
    """Run the deterministic checks that gate a contract-satisfied claim."""

    errors = sorted(
        _EVIDENCE_VALIDATOR.iter_errors(structured_output),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        pointer = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}" for part in first.absolute_path
        )
        schema_check = CheckOutcome(
            "EVIDENCE-SCHEMA",
            "fail",
            f"structured output violates the evidence contract at {pointer}: {first.message}",
        )
    else:
        schema_check = CheckOutcome(
            "EVIDENCE-SCHEMA",
            "pass",
            "structured output conforms to the frozen evidence-extraction schema",
        )

    expected_hash = task.input_refs[0].sha256 if task.input_refs else ""
    source_check = CheckOutcome(
        "SOURCE-HASH",
        "pass" if expected_hash else "fail",
        f"evidence content hash pinned to task input sha256 {expected_hash}"
        if expected_hash
        else "task has no input reference to pin the evidence source hash",
    )

    locator = str(structured_output.get("source_locator", "")).strip()
    locator_check = CheckOutcome(
        "SOURCE-LOCATOR",
        "pass" if locator else "fail",
        f"source locator recorded as {locator!r}" if locator else "source locator is empty",
    )
    return (schema_check, source_check, locator_check)


def session_checks(
    *, stop_reason: str, tool_failures: tuple[Mapping[str, Any], ...]
) -> tuple[CheckOutcome, ...]:
    """Checks recorded for sessions that did not reach a completed outcome."""

    failure_names = ", ".join(
        f"{entry.get('name')}:{entry.get('error')}" for entry in tool_failures
    )
    return (
        CheckOutcome(
            "STOP-REASON-RECORDED",
            "pass",
            f"session ended with machine stop reason {stop_reason!r}",
        ),
        CheckOutcome(
            "TOOL-FAILURES-RETAINED",
            "pass",
            f"tool failures retained in the handoff and receipt: {failure_names or 'none'}",
        ),
    )
