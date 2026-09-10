# Reproducing the intake

Use exact Git objects in a disposable checkout with Python available. All probes are read-only.
The dependency module used here is loaded from immutable Git bytes at the M14 head, not a mutable candidate.

```python
import subprocess
import types
from pathlib import Path

repo = Path.cwd()
head = "205559b25f7f0bd276094a4ac53db28354b7284d"
raw = subprocess.check_output(["git", "--no-replace-objects", "show", f"{head}:.github/scripts/ci_dependencies.py"])
dependencies = types.ModuleType("pinned_dependencies")
exec(compile(raw, ".github/scripts/ci_dependencies.py", "exec"), dependencies.__dict__)
for path in (
    "src/research_workbench/artifacts/claim_trace.py",
    ".github/scripts/release_surface.py",
    "src/research_workbench/capability/release_projection.py",
):
    selection, *_ = dependencies.select(repo, head, head, {path})
    print(path, len(selection["selected"]), len(selection["selected"]) + len(selection["excluded"]))
```

The saved certificates in `baseline.json` also contain complete selected/excluded lists and traversal chains.
This API call does not generate an actual PR plan, activate a reviewed leaf contract or execute any test.

Download `ci-plan` and `coverage-quality-evidence` from CI run `34131110394` using `gh run download`.
Their extracted file hashes and sizes are recorded in `baseline.json`; the archive retains the compact
derived evidence rather than duplicating the full coverage file. Read `ci-plan.json`,
`coverage-test-results.json`, and the Git-pinned `tests/coverage_policy.yaml` from the M14 head.
Repository suite membership for each executed ID is determined by its module's inclusion in
`suites.coverage-quality.modules` or its exact inclusion in `test_ids`.
The remaining 61 IDs and all their measured durations are preserved in the baseline data.
No module is imported or test executed to calculate this partition.

Job wall time is `completed_at - started_at` from the GitHub jobs API. Case-duration sums exclude setup
and are not the same measure as job or suite wall time. The 937.590517-second re-added subset is an
observed attribution in the existing instrumented run, not a counterfactual timing result.
