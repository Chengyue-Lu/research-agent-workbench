# CHAIN-TOOL-PREP-011: API readonly Tool bridge

Agent Profile: bounded implementation worker; required-Skills=[]; accountable control owner 路诚钺, API reviewer 黄毅. Root is the sole product/API/Tool/Key/ledger test executor.

Read set: this Packet, API_FACTORY_TASK_PACKET, public entry driver ClientTool mapping and ApiSessionLimits interfaces, adapters/models/port.py ToolDefinition, adapters/models/session.py ClientTool declaration (locate by filename first if moved), tests/test_entry_bridge_flow.py readonly handler contract only. No actual API Attempt/project or credential files.

Ownership: runtime/synthetic_tool.py, TOOL_HANDOFF.md and TOOL_COMMUNICATIONS.md only. You are not alone; preserve all other edits. Budget 6 minutes / one round. No source/schema/registry changes, tests, imports executing products, API/Tool/Key/ledger, Git or project memory.

Prepare `create_synthetic_lookup(root, task, target_path='materials/intent.txt') -> ClientTool`: name `entry-api-bridge`; JSON arguments exactly path with an enum containing only the declared target; side_effect read-only. Validate the target against the supplied actual Task's exact input refs, portable root containment, SHA256 and UTF-8 on each invocation. Read only bounded text (4096 bytes max) from that exact file. Return a compact mapping with path, SHA256 and actual synthetic text; unknown path, extra fields, drift, unreadable/oversize input fail before returning success. Never expand a read set, write a file, fetch network data, create a Supply or claim formal qualification.

The caller will explicitly select/hash the handler and produce its actual Tool component, map refs, configure per-role bounded Session limits and feed the actual result into a fresh model request. Child number stays main's decision; this test does not introduce a mandatory global Tool or fixed child role count.

Output compact interface, source hash, AST/compile-only check, limitations and portable visible transmissions. Stop after delivery.
