# Operational verification audit

Merged PR #63 selects FAST and FOCUSED correctly in controlled GitHub-hosted PR #64. FAST skips full compatibility/coverage/smoke jobs but closes both aggregates. FOCUSED executes both Python groups, impact coverage and its required downstream smoke. Body and label events retain the matching content plan without new content jobs. An active HEAD is automatically cancelled and the replacement succeeds. The probe is closed without merge.

Timing uses content-job start/end intervals and sums; governance and queue delay are excluded. Equivalent Provider literal changes preserve the AST. This is controlled operational evidence; natural product-change benchmarks and Issue #48 profiling remain separate.

The real develop integration run correctly chooses FULL but reveals one ambient-event fixture leak in all three suites. It was reproduced under push locally. Explicitly binding the synthetic PR input's event type repairs the fixture; the event matrix preserves coverage under push/dispatch/PR environments. Product planner validation and quality floors are unchanged. The test-content fingerprint is refreshed for the reviewed closure.
