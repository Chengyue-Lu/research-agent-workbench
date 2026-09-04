# Check 0003 — stable implementation tree fingerprint and static validation

- baseline commit: `12d05dd130c718dd179e011292f9ada9f97bdf74`
- tested tracked-worktree diff fingerprint: Git blob SHA-1 `76167acb47c538c32a0900da6a0264424ce71b3d`
- fingerprint command: `git diff --binary HEAD | git hash-object --stdin`
- whitespace command: `git diff --check`
- compile command: `python -m compileall -q src tests .github/scripts`
- environment: Windows, Python `3.14.6`
- result: all commands exit `0`
- boundary: the fingerprint excludes this ignored Attempt Archive; later Archive-only changes do not alter the tested governance/product tree
