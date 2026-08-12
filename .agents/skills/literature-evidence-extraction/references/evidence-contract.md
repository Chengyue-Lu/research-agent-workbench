# Evidence contract

Create one repository Evidence object per atomic source-grounded statement.

Required fields:

- `object_type: evidence`
- stable `object_id`, `revision`, and workflow `status`
- `content_hash` equal to the assigned source file hash when a local source is used
- `kind` that identifies the evidence form without upgrading its strength
- `source_ref` pinned to the admitted source or input revision
- `locator` precise enough for another reviewer to find the passage
- `statement` that does not claim more than the located passage
- `quality_flags`, including access, extraction, conflict, or scope limitations

Prefer locators in this order: page plus table/figure/section, paragraph or line range, stable section heading, timestamp, then a clearly labeled metadata-only locator. `No stable locator` is a blocker, not a locator.

The Evidence object holds source-grounded content. Put agent inference, recommendations, unresolved questions, and source-weight decisions in the Handoff fields. A structurally valid record is not proof that the source is scientifically correct.
