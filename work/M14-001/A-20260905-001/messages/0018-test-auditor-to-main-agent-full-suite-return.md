---
schema_version: 0.1.0
message_id: MSG-0018
task_id: M14-001
task_revision: 1
attempt_id: A-20260905-001
sequence: 18
kind: handoff
sender_actor_id: test-auditor
receiver_actor_ids: [main-agent]
accountable_owner: Chengyue-Lu
created_at: "2026-09-05T03:51:01+08:00"
in_reply_to: MSG-0013
content_sha256: "598b2506d143d289a2dde50af0ee0bf25df78e937b5edef8639290d9126efb62"
attachment_refs: []
redactions:
  - redaction_id: RED-0001
    category: personal-data
    reason: "Replace the machine-specific temporary directory and local username with a temporary-location placeholder; the result JSON was not archived."
    field_path: result.json_path
capture_status: partial
capture_gap_event_id: EVT-0022
---
{"result":{"suite":"full","total":811,"passed":810,"skipped":1,"failed":0,"errors":0,"wall_seconds":715.434495,"exit_code":0,"json_path":"<temp>/rwb-m14-full.json"},"workspace_edits":false}
