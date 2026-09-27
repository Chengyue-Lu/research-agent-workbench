# Component CI premerge preparation

Owner Chengyue-Lu; TEST-PERF-002; R2; 2026-09-27.

Develop metadata binds the exact PR component plan through the real API and Git
parents; a plan reference does not supply execution success. Legacy develop PR
automatic execution is retired in the candidate; develop push/source-CI and main
remain available during the separate checkpoint deployment stage.

Local9PASS + compatibility/docs36PASS, then4 affected metadata cases PASS after
live GitHub revealed a retained historical workflow display name. Original failure
and API identity are preserved. These are45 distinct tests. Live prior12b plan
binding is API sanity only, not current-head hosted execution. No coverage or
M14/M5 speedup ratio is claimed by these local results.

Read-only actual hard-ruleset payloads are review material, not approval to apply:
[before](checks/migration/before.json), [intersection](checks/migration/intersection.json),
[components](checks/migration/components.json), [rollback](checks/migration/rollback.json),
[hash manifest](checks/migration/manifest.json).

Only the required-check list differs. Protection mutation, actual merge, checkpoint
deployment and source/release activation are not performed. Later exact-head hosted
results remain separately identified; old evidence is not re-signed.

[Summary](checks/summary.json), [manifest](checks/manifest.json), [raw evidence](checks/raw-evidence.zip).
