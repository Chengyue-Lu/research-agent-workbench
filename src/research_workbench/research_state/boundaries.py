"""Fixed authority ceilings shared by the Phase C runner and fresh actor."""

AUTHORITY_LIMITS = [
    "machine-gate-does-not-prove-reviewer-reconstruction",
    "machine-gate-does-not-prove-scientific-correctness",
    "machine-gate-does-not-complete-human-semantic-review",
    "machine-gate-does-not-complete-r2-closeout",
    "machine-gate-does-not-authorize-topic-5",
]

TRUSTED_RUNTIME_SCHEMA_SURFACE = [
    {
        "kind": "runtime",
        "locator": "python-and-research-workbench-preloaded-runtime",
        "assurance": "declared-preloaded",
    },
    {
        "kind": "schema",
        "locator": "schema-catalog:v0.1.0",
        "assurance": "read-only-allowlisted",
    },
]
