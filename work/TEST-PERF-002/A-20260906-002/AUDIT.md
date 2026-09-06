# Bounded review closeout audit

The user authorized fixing the latest review on PR #63. Cross-owner comment 5559639631 limits closeout to three P2 findings. Code edits stay in the existing planner/checker and tests; product source, quality floors and M-series state are unchanged.

P2-1 includes Python test metadata/content in the accepted consumer fingerprint. A real Git fixture demonstrates an added/evolved budget assertion passing before a leaf regression and failing afterward; the old plan now requires FULL. Test deletion also invalidates closure, and reviewed regrouping restores FOCUSED.

P2-2 binds physical diff lines and enclosing AST statement spans separately. A real coverage run exposes missing arc [2, 6] for a line-3 condition edit. The checker rejects the missing branch and accepts both paths. Conservative compound-statement spans may require more coverage than the physical diff. Unmappable lines require FULL.

P2-3 rejects missing, wrong or stale dispatch trigger SHAs during planning. Fresh PR head and exact merge candidate remain valid FULL recovery targets. Metadata matching is retained.

Evidence scope: local affected regressions and critical coverage are pinned to staged code bytes. One final-head hosted FULL run and human review remain acceptance requirements. No local full, full-coverage or installation suite was repeated for this closeout.
