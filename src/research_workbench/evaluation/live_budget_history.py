"""Explicit selected M6 plus Pilot archives, not a global continuity registry.

This reader proves the selected history, not that no omitted/outside ledger
exists. A named caller must select the complete set. Trial needs its own actual
producer before it may extend this prefix; it cannot impersonate a Pilot run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from research_workbench.evaluation.live_budget import PilotUsageJournal
from research_workbench.evaluation.live_inputs import LiveEvaluationInputs
from research_workbench.evaluation.live_preflight import FrozenLiveContext, VerifiedBudgetCheckpoint, _verify
from research_workbench.evaluation.live_verification import RetainedConformanceBudget
from research_workbench.evaluation.pins import digest, require, timestamp


@dataclass(frozen=True, repr=False)
class RetainedPilotBudget:
    """Explicit original paths/context; no executable journal or I/O port."""
    database: Path
    anchor: Path
    journal_identity: str
    inputs: LiveEvaluationInputs
    context: FrozenLiveContext

    def __post_init__(self):
        def select(_):
            require(type(self.inputs) is LiveEvaluationInputs and type(self.context) is FrozenLiveContext,
                    "original Pilot input/context required")
            require(type(self.journal_identity) is str and str(UUID(self.journal_identity)) == self.journal_identity,
                    "explicit retained Pilot identity required")
            object.__setattr__(self, "database", Path(self.database).resolve())
            object.__setattr__(self, "anchor", Path(self.anchor).resolve())
        _verify(select, {}, "retained Pilot selection")

    def __repr__(self):
        return "<independently selected retained Pilot budget>"

    def snapshot(self, prior):
        def read(_):
            require(type(prior) is VerifiedBudgetCheckpoint, "verified prior checkpoint required")
            return PilotUsageJournal.read_retained_snapshot(self.database, self.anchor,
                inputs=self.inputs, context=self.context, prior_reader=lambda: prior,
                journal_identity=self.journal_identity)
        return _verify(read, {}, "retained Pilot budget")


def _ready(snapshot):
    return (snapshot["usage_complete"] and snapshot["closed"] and snapshot["held_total_tokens"] == 0
            and snapshot["known_total_tokens"] <= snapshot["cumulative_token_limit"] <= 10_000_000)


def _checkpoint(reference, snapshot):
    require(_ready(snapshot), "retained history is incomplete or exceeds ceiling")
    return VerifiedBudgetCheckpoint(reference, snapshot["known_total_tokens"], 0,
                                    snapshot["cumulative_token_limit"], True)


@dataclass(frozen=True, repr=False)
class RetainedBudgetHistory:
    """Ordered archives with exact prior links and delta-only accumulation.

    Snapshot retains failed/unknown/not-started facts. Checkpoint refuses
    unresolved or unclosed history; stopped-but-fully-known failures may carry
    usage into a separately frozen run, without granting that run permission.
    """
    base: RetainedConformanceBudget
    runs: tuple[RetainedPilotBudget, ...] = ()

    def __post_init__(self):
        require(type(self.base) is RetainedConformanceBudget and type(self.runs) is tuple
                and len(self.runs) <= 64 and all(type(run) is RetainedPilotBudget for run in self.runs),
                "bounded explicit retained history selection required")

    def __repr__(self):
        return "<independently selected cumulative budget history>"

    def snapshot(self):
        return _verify(lambda _: self._snapshot(), {}, "retained budget history")

    def _snapshot(self):
        selected = [self.base, *self.runs]
        identities = [item.journal_identity for item in selected]
        run_ids = [run.context.run_id for run in self.runs]
        require(len(set(identities)) == len(identities) and len(set(run_ids)) == len(run_ids),
                "duplicate retained run or journal identity")
        paths = [os.path.normcase(str(path)) for item in selected for path in (item.database, item.anchor)]
        require(len(set(paths)) == len(paths), "retained paths overlap")
        base = self.base.snapshot()
        result = {"record_kind": "evaluation_live_budget_prefix", "version": "2.0.0",
            "base": {"journal_identity": self.base.journal_identity, "snapshot": base}, "runs": [],
            "known_total_tokens": base["known_total_tokens"], "held_total_tokens": 0,
            "cumulative_token_limit": min(base["limits"]["total_token_limit"], 10_000_000),
            "usage_complete": True, "closed": True}
        previous = base
        observations, previous_end = [], None
        for run in self.runs:
            frozen = timestamp(run.context.case_selection_frozen_at)
            require(previous_end is None or frozen >= previous_end,
                    "retained run was frozen before previous closeout")
            prior = _checkpoint(run.context.budget_checkpoint_ref, result)
            require(run.inputs.read(run.context.budget_checkpoint_ref) == previous,
                    "retained run does not inherit the exact previous checkpoint")
            actual = run.snapshot(prior)
            delta = {name: sum(c["usage"][name] for c in actual["calls"] if c["usage"] is not None
                              and type(c["usage"][name]) is int) for name in ("input_tokens", "output_tokens")}
            total = result["known_total_tokens"] + sum(delta.values())
            require(actual["known_total_tokens"] == total, "retained history double counts or drops usage")
            started = [a for a in actual["attempts"] if a["status"] != "not-started"]
            if started:
                start = timestamp(started[0]["started_at"])
                require(start >= frozen
                        and (previous_end is None or start >= previous_end), "retained runs are not chronological")
            closed = bool(started) and all(a["status"] in {"completed", "failed"} for a in started)
            closed = closed and (actual["stopped"] or len(started) == len(actual["attempts"]))
            result = {**result, "runs": [*result["runs"], {"snapshot": actual, "delta": delta}],
                "known_total_tokens": total, "held_total_tokens": actual["held_total_tokens"],
                "cumulative_token_limit": min(result["cumulative_token_limit"], actual["limits"]["cumulative_token_limit"]),
                "usage_complete": actual["usage_complete"], "closed": closed}
            observations.append((run, prior, actual))
            previous = result
            previous_end = timestamp(started[-1]["ended_at"]) if closed else None
        # Slow readers must not combine two versions of a mutable archive.
        require(self.base.snapshot() == base, "retained base changed during read")
        for run, prior, actual in observations:
            require(run.snapshot(prior) == actual, "retained Pilot changed during read")
            run.inputs.recheck()
        digest(result)  # Finite, detached actual snapshot only.
        return result

    def checkpoint(self, inputs, context):
        def read(_):
            pinned = inputs.read(context.budget_checkpoint_ref)
            actual = self._snapshot()
            require(actual == pinned, "retained prefix disagrees with frozen checkpoint")
            inputs.recheck()
            return _checkpoint(context.budget_checkpoint_ref, actual)
        return _verify(read, {}, "retained budget checkpoint")
