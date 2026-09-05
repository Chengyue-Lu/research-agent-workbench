# CHK-0007 — MSG-0018 temporary-path redaction

- performed_at: `2026-09-05T19:01:57.346534+00:00`
- authorization: the user explicitly requested fixing the [PR #60 review finding](https://github.com/Chengyue-Lu/research-agent-workbench/pull/60#discussion_r3941595405).
- source snapshot: `f8f9ad5a61ecd613299a4c7589b4e8dfbd3439ea`
- message: `messages/0018-test-auditor-to-main-agent-full-suite-return.md`
- redacted field: `result.json_path`
- replacement: `<temp>/rwb-m14-full.json`
- redaction metadata: `RED-0001`, category `personal-data`
- previous message file SHA-256: `640a40c46d9ac5e2f269b2afcd8a1485f610c079ae5006de9e7edc2e507c4d39`
- redacted message file SHA-256: `17c53a7a1cc69eb90775cbd7149236bb7afc3e367e13cf1cd934f2ccea573987`
- previous body SHA-256: `00bb3bf2fc64d4d8244ba6df262ca2da123759691eeb1841990006afd4598df3`
- redacted body SHA-256: `598b2506d143d289a2dde50af0ee0bf25df78e937b5edef8639290d9126efb62`

This is a user-authorized redaction of a historical archival summary, not a new message capture. The original message identity, timestamp, test counts, timings, exit code, and partial capture state remain unchanged. The original bytes remain identifiable by the source commit and previous hashes above. The placeholder describes the original temporary location; it does not assert that the result JSON was archived.

The envelope and Index now hash the redacted representation. Existing message/event/tool-result capture gaps, the historical event ledger, and safe-paused/frozen/gapped status remain intact. Validate this corrected archive with `python -m research_workbench trace validate --attempt work/M14-001/A-20260905-001 --root .`.
