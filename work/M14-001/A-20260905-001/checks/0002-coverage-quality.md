# Check 0002 — Coverage Policy v2

- environment: Windows, Python `3.14.6`, editable test dependencies installed
- suite command: `python -m coverage run --branch --data-file=$env:TEMP\rwb-m14.coverage tests/run_unittest_suite.py --suite coverage-quality --policy tests/coverage_policy.yaml --json-output $env:TEMP\rwb-m14-results.json --slowest 20`
- export command: `python -m coverage json --data-file=$env:TEMP\rwb-m14.coverage -o $env:TEMP\rwb-m14-coverage.json`
- policy command: `python .github/scripts/check_coverage_policy.py --policy tests/coverage_policy.yaml --coverage $env:TEMP\rwb-m14-coverage.json --test-results $env:TEMP\rwb-m14-results.json`
- exit code: `0`
- suite result: `750` tests run; `749` passed, `1` skipped because Windows symlink privilege was unavailable, `0` failed/errors; canonical duplicate check passed
- suite wall time: `445.964` seconds
- global line coverage: `91.53%` (Gate `>=90%`)
- governance checker coverage: `97.31%` line / `96.58%` branch (Gates `>=95%` / `>=90%`)
- critical modules: every declared module passed its independent line/branch thresholds
- policy result: `coverage-policy: PASS`
- transient result JSON SHA-256: `942a08bff3393004ea8fdb14748c5ea7480ac67e8eb03f88845cdc3cec289257`
- transient coverage JSON SHA-256: `e73dccfc0d78dc827a7dcbd6756000f374f6b56055056b848da27882788cc16b`
- evidence boundary: the temp JSON files are not durable archive inputs; this check file records the exact command, counts, thresholds, and hashes observed by the main agent
