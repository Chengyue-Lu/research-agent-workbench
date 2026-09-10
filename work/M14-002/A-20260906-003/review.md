# Review basis

User-provided review screenshot in the current task

P1 append-only deletion gap: the DAG carries inherited versions without requiring them to remain in each actual commit. A [1.0.0, 2.0.0] -> B [2.0.0] -> C [1.0.0, 2.0.0] can pass. Existing deletion coverage removes the entire policy file, not one version identity. Require ancestor version retention at every commit and retain legal merged non-prefix histories.
