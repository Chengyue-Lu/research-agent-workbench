# Component CI production preparation

Owner Chengyue-Lu; TEST-PERF-002; R2; 2026-09-27.
User requested continuing PR105 implementation. The new producer handles PR content
and develop smoke, joins native results, and prepares separate full checkpoints.
Source-CI v2, manifest0.2 and source-owned version choice preserve legacy receipt
interpretation and dormant release authority. Current active contract remains v1.

Local evidence: first44PASS; release/mapping/schema67 cases yielded66PASS and one
obsolete workflow-selection assertion. Updating that expectation for the new direct
tests then passed that one case. Later source-version/preflight/docs17PASS.
Fresh wheel/install, eight real smoke steps and both installed manifest schema versions
passed. No whole-suite checkpoint, hosted speedup, activation or merge is claimed.
The first mapping failure and the previous legacy-CI coverage failure are retained.
The source manifest binds these local bytes only; future runs have separate identities.
Default main still needs an accepted checkpoint workflow deployment before scheduling.

[Summary](checks/summary.json), [manifest](checks/manifest.json), [raw evidence](checks/raw-evidence.zip).
