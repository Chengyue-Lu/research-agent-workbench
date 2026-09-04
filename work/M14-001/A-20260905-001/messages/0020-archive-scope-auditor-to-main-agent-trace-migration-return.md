---
schema_version: 0.1.0
message_id: MSG-0020
task_id: M14-001
task_revision: 1
attempt_id: A-20260905-001
sequence: 20
kind: handoff
sender_actor_id: archive-scope-auditor
receiver_actor_ids: [main-agent]
accountable_owner: Chengyue-Lu
created_at: "2026-09-05T04:00:00+08:00"
in_reply_to: MSG-0019
content_sha256: "092aed97d06ad077df9113f2f5c90f30d9baf013ea095e071f9ee88d8a0e412b"
attachment_refs: []
redactions: []
capture_status: partial
capture_gap_event_id: EVT-0022
---
{"result":{"actors":"Add task_id, task_revision, attempt_id, and actor_type to ACTORS.yaml.","messages":"Use a YAML envelope plus one JSON body; index complete identity, actors, timestamps, body hash, file hash, and capture status. The existing reconstructed/compacted messages must remain partial and point to a messages capture-gap event.","index":"Remove legacy implementation_ref/status and use strict Agent Trace v0.1 task, actors, message, ledger, file-ref, and capture-gap projections.","events":"Replace narrative events with attempt lifecycle, one message-capture per indexed message, explicit capture-gap events, and the final safe-paused transition.","closeout":"Use attempt_status safe-paused, trace_status frozen, completeness gapped. Capture-gap warnings are retained but must not BLOCK validation."},"workspace_edits":false}
