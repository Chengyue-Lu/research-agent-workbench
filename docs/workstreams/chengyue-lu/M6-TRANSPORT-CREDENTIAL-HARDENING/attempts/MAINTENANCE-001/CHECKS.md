# Maintenance checks

## Frozen source and isolated offline regression

```json
{
  "base": "1c9cef27983e93362be33830f989e124ad3ccc41",
  "source_files": [
    {
      "path": "src/research_workbench/adapters/models/http.py",
      "sha256": "8185c96c3f9a880d83099cc9da0bbc8b057fc3c2ab862483a8f93c398e91ddee",
      "bytes": 8775
    },
    {
      "path": "src/research_workbench/adapters/models/base.py",
      "sha256": "48e7f2be2266622a9477cde3010081e7754ef7b0d0da45f8d4bd6b8ac702c465",
      "bytes": 17265
    },
    {
      "path": "src/research_workbench/adapters/models/configuration.py",
      "sha256": "0f837fb71ffd2d9c82993e9e3cfa3abb748526ea5b0e678b9110b52904eb7a94",
      "bytes": 7721
    },
    {
      "path": "src/research_workbench/adapters/models/openai.py",
      "sha256": "1bcdda1cbc4e0072d969ce4d08fa284c2401f9aea79f0065e43286013ef1ddc4",
      "bytes": 14903
    },
    {
      "path": "tests/test_provider_adapters.py",
      "sha256": "ae45011fa68f69c01f424d9ce54d1b0891b19c60305da05211370bf3415c29c8",
      "bytes": 30275
    },
    {
      "path": "tests/test_provider_transport_security.py",
      "sha256": "261aeeba1612e36d889ed77911d9d917e1c41559c55b7d467be86f094c475e92",
      "bytes": 19621
    }
  ],
  "focused_modules": [
    "tests.test_provider_adapters",
    "tests.test_provider_contract_branches",
    "tests.test_provider_conformance",
    "tests.test_provider_port",
    "tests.test_cli",
    "tests.test_provider_transport_security"
  ],
  "tests_passed": 62,
  "tests_failed": 0,
  "focused_log_sha256": "3a62bc2349f0f8811498c8cbf513219073eed631992cb925c6e94b55ec628c13",
  "isolated_receipt_sha256": "133ab7926409475ee8ce09e41a137281d3b263fa416b2e62f3a6657c0d6f2f67",
  "real_api_calls": 0,
  "real_credentials_read": false,
  "initial_missing_runtime": {
    "tests": 61,
    "passed": 53,
    "errors": 8,
    "log": "focused-tests.log",
    "reason": "missing ignored research_workbench._runtime_pin"
  },
  "task_definition_status_changes": false
}
```

Final test child used a literal non-secret environment allowlist, with no inherited environment. Socket and proxy discovery were denied. Existing adapter/Port/config/CLI/conformance paths plus twelve new security regression methods passed. No install, real key or API was used.

Redirect cases cover five status codes and same host / other HTTPS host / HTTP downgrade: fifteen cases each retain exactly one original POST and zero additional sends. Valid custom HTTPS hosts/ports/paths and three fake auth forms remain valid. URL rejection precedes resolve; public diagnostics do not reflect fake credentials/research values or attach the underlying exception. Unknown provider code/message is not public, while understood safe codes retain useful categories.

The initial missing-runtime errors are retained rather than rewritten. Root generated only the ignored runtime closure with the existing build backend after validating the absolute target stays inside the worktree and is not a symlink. Manifest SHA-256 `4e6b1be6107922e46354d5a3e23602ec724d76853d57434217184916960a4c54`.

## Integration and review

Actual diff-based component plan/run, documentation/public links and exact-head R2 PR governance are recorded by root after the source commit. Hosted CI and named human review remain separate; this summary is not live/account acceptance.

## Actual source-component and documentation checks

Source implementation commit `3adaf0f` selected adapters/docs plus the new changed test module, unknown paths0. Eight selected modules and the standard short regressions executed **92/92 PASS** (6.233 seconds). Existing model pool and API Session defaults are included. Plan SHA-256 `bf2cd5cff7e28913fc31535dc4de0dfc298ab567192c41cfba56028f061ed9ab`; native result SHA-256 `e1915aeb1eb7ffc53c07630e4b434f4ba6bc172c6c99f57729a1c640f414a001`.

Existing documentation/public checks: **23/23 PASS**, including internal Markdown links and public projection boundaries. Independent technical review: **12/12 PASS**, no remaining reproduced blocker on the same six source/test hashes; review SHA-256 `35ef9f36fe741fdbbf37ca46ecb8a8cf3ce3f3d85cd4883d0ed525bee0ac2cfb`. This is Agent evidence, not named Human approval. Final commit adds only this check summary; source/test blobs remain equal to the tested implementation. Exact-head PR metadata/governance and hosted CI are retained in the external PR/receipt. No full/coverage/live acceptance is claimed.
