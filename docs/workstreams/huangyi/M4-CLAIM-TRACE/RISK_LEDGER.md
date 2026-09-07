# M4-003 Risk Ledger

| Risk | Control and evidence | Owner |
|---|---|---|
| A formatted Claim looks like verified provenance | Legacy view explicitly has localization not requested; mapped mode validates exact files and reports unresolved edges | Huang Yi |
| Evidence identity or bytes drift | Existing ObjectRef resolution plus independent live FileRef hashes; wrong/missing/ambiguous refs tested | Huang Yi |
| Unused map entries hide dangling provenance | Exact Claim/Evidence/source identity sets; every declared binding checked once, including unused bindings; extra-entry regressions | Huang Yi |
| A relocated receipt or work record is mistaken for canonical promotion provenance | Canonical receipt path, exact workspace membership, allowed target zones and resolved path checks; mutations reuse one real producer | Huang Yi |
| Counterevidence or a retained negative outcome disappears | Separate relations and explicit retain-in-work disposition; real promotion consumer integration | Huang Yi |
| Structural localization is treated as Claim acceptance | Authority flags false; no mutation; Protocol ceiling retained; locator semantics remain human-reviewed | Chengyue Lu |
| Repeated validation dominates read-only use | One captured read set, shared provenance cache, no checker re-execution; actual open-count regression | Huang Yi |
| Source mapping invents a new identity authority | Map declares existing identity/file bindings only; no core ObjectRef or Research Object migration | Chengyue Lu |

Limits are located in the Claim document because the existing contract stores
strings, not independent provenance edges. Expanding that representation is
outside this Task. Historical checker execution, source truth, scientific
validity and M5 benefit are not established by this consumer.
