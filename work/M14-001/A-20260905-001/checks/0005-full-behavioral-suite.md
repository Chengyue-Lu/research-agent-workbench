# Check 0005 — full behavioral suite

- executor: `test-auditor` read-only subagent
- environment: Windows, Python `3.14.6`
- command: `python tests/run_unittest_suite.py --suite full --json-output $env:TEMP\rwb-m14-full.json --slowest 20`
- exit code: `0`
- result: `811` total; `810` passed, `1` skipped, `0` failed, `0` errors
- wall time: `715.434495` seconds
- transient result JSON SHA-256: `4d420eee12c6941297d57d1156cb3df76df8fca7d6154869827eb1d7755f6f92`
- tested tracked-worktree diff fingerprint: Git blob SHA-1 `76167acb47c538c32a0900da6a0264424ce71b3d`
- limitation: local Python 3.14 evidence cannot replace hosted Python 3.11/3.13 on the future latest-base PR head
