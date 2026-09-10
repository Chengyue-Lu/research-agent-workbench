---
schema_version: 0.1.0
message_id: MSG-0013
task_id: M14-001
task_revision: 1
attempt_id: A-20260905-001
sequence: 13
kind: assignment
sender_actor_id: main-agent
receiver_actor_ids: [test-auditor]
accountable_owner: Chengyue-Lu
created_at: "2026-09-05T03:39:43+08:00"
content_sha256: "11ffeb2b7033cfbff2daa48bc929094cae396defb128d26e76c5d75f17b6d5f9"
attachment_refs: []
redactions: []
capture_status: partial
capture_gap_event_id: EVT-0022
---
{"assignment":"Run the canonical full behavioral suite read-only: python tests/run_unittest_suite.py --suite full --json-output $env:TEMP\\rwb-m14-full.json --slowest 20. Report exact counts, wall time, and JSON path; do not edit."}
