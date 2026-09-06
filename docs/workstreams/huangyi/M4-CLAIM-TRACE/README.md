# M4-003 Claim evidence localization

Implementation: Huang Yi (`let778750-cpu`). Accountable Task/Claim owner and
cross-owner reviewer: Chengyue Lu (`Chengyue-Lu`). Risk: R2, because this is a
Claim-facing contract; no scientific or Claim acceptance authority is added.

Base: accepted `develop@6f0caf0` after PR #54. M4-003 is READY with M4-001,
M4-002 and M8-005 complete. M4-004 is a separate, parallel Task; M14 and M5
do not add implementation prerequisites to this slice.

The [contract](../../../implementation/CLAIM_TRACE_CONTRACT.md) extends the
existing `claim trace` command with a pinned evidence map. The map joins
existing identities to actual bytes and admission/promotion records, keeping
support, counterevidence, limitations and retained negative results visible.
Original Task acceptance and Research Object schemas remain unchanged.

See [risk ledger](RISK_LEDGER.md) and [verification](VALIDATION.md). Candidate
completion becomes shared project state only after named owner acceptance
and merge; CI does not make a scientific judgment.
