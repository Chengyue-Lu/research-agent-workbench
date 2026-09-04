# Check 0004 — repository validation and package smoke

- executor: `governance-design-auditor` read-only subagent
- environment: Windows, Python `3.14.6`
- repository command: `PYTHONPATH=src python -m research_workbench validate examples registry --root .`
- repository result: exit `0`; `validated=183 errors=0 warnings=0`
- package topology source: `.github/workflows/ci.yml`
- package steps: build wheel; create independent venv; install wheel; run installed `rwb schema list`; run installed `rwb validate examples registry`; import package from empty cwd
- package result: every step exit `0`; `63` Schemas; installed validation `183/0/0`; import resolved from venv `site-packages`
- wheel: `research_agent_workbench-0.1.0-py3-none-any.whl`
- wheel SHA-256: `d8ad9c41f5f4ec0ef2b1a342e2401421c5a7643e70ec85229d7b6aed43fbbd84`
- tested tracked-worktree diff fingerprint: Git blob SHA-1 `76167acb47c538c32a0900da6a0264424ce71b3d`
- limitation: local Python 3.14 evidence cannot replace hosted Python 3.11/3.13 or exact PR-event governance
