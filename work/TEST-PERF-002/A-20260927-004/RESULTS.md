# Local CI policy parsing cost evidence

TEST-PERF-002; owner Chengyue-Lu; source `815c3a95ff86118e0c8bba6ed9bbf98162584f6c`; accepted base `97d3b3d3141419b34ad47e0f42d9f01d0dfbd535`.

The comparison source725 is the unaccepted PR103 candidate. Original profiles, bounded old/new measurements and local validation retain their own source and execution identities. The diagnostic-demand cache was rejected after the real plan/report pipeline regressed; its graph-only gains are not adopted. The policy optimization caches only stock pure YAML parsing, returns independent copies, and bypasses changed parser configuration.

Three unprofiled pairs and one separately reported branch-mode pair cover two original cases, retaining all8/23 subtests. This is case-local cost evidence, not a whole-CI or hosted speedup. Original preparation, collector and aggregation failures remain in the raw evidence. Local source-matched correctness/coverage receipts are included without being renamed final committed-head plan, governance, independent witness or hosted Gates.

The impact-versus-execution design and M5 owner plan remain proposals; late incomplete M5 profiling is excluded. Production selection reduction, cross-commit execution reuse, release, tags and main are unchanged. Later publication and final Gates need their own identities.

- [Summary](checks/summary.json)
- [Original paths and hashes](checks/manifest.json)
- [Deduplicated exact payloads](checks/raw-evidence.zip)
