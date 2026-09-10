# Independent selection authority witness

Owner: Chengyue-Lu; cross-owner review: let778750-cpu; TEST-PERF-002 / R2.

The candidate planner's FULL rule is useful behavior, but its self-verification does
not establish that the rule survived candidate modification. Selection-authority
review therefore consumes a witness executed from a separately fixed Git commit.
The candidate cannot supply or override that execution reference through its plan.

## Execution root and review procedure

The initial execution root is
[`1b543393ae71b9032359b739170d66ec0be08772`](https://github.com/Chengyue-Lu/research-agent-workbench/commit/1b543393ae71b9032359b739170d66ec0be08772),
published on `audit/test-perf-002-selection-witness`. Its isolated `ci.yml` workflow
has only a manual dispatch entry and read permissions. The implementation PR carries
the same [witness source](../../../../.github/scripts/selection_witness.py) for code
review and coverage; invoking that candidate copy is not independent evidence.

The cross-owner reviews and accepts the execution-root commit separately from the
candidate plan. A maintainer then dispatches the existing CI workflow on the audit branch with that independently pinned
SHA, passing the current PR number and its content CI run ID:

```sh
gh workflow run ci.yml --repo Chengyue-Lu/research-agent-workbench \
  --ref audit/test-perf-002-selection-witness \
  -f witness_sha=1b543393ae71b9032359b739170d66ec0be08772 \
  -f pr=66 -f run_id=CONTENT_RUN_ID
```

Before accepting the result, read the returned run with GitHub's API and require
`head_sha` to equal the independently accepted witness commit and the event to be
`workflow_dispatch`. Download `independent-selection-witness` from that run only.
Require PASS, the current repository/base/head/target and the exact content plan ID.
A candidate job, a candidate-proposed replacement SHA or a receipt from another run
cannot substitute. New base/head/plan or a changed execution root requires a fresh
witness run and appropriate review. Required behavioral, coverage, smoke and governance
checks must independently succeed on the same candidate. A witness PASS proves only
the behavioral floor, not that the requested tests were executed successfully.

The witness workflow checks out its own immutable SHA and installs only pinned
PyYAML. It uses `python -I`, no candidate imports or package installation, no candidate
caches and no archive extraction. It fetches candidate commits as bare Git objects;
the plan artifact is JSON data. Plan repository/base/head/merge-base/digest and merge
parents must match external GitHub/Git facts. Missing, malformed, stale or mismatched
inputs block. Python AST / YAML structure and Git modes determine changes to a fixed
authority inventory. Changed authority or stale base requires full behavior on both
Python versions. Ordinary R2 scope, coverage and smoke obligations remain independent.

## Bootstrap and enforcement boundary

The initial independent invocation is available without changing the default branch,
release state or remote protection. Accepting its execution root and current receipt
is an explicit cross-owner merge-review obligation. Existing required-check settings
do not automatically dispatch or enforce this extra witness; candidate aggregate green
alone cannot close this obligation. Automated mandatory deployment needs a separately
accepted trusted event entry and maintainer configuration. The manual witness does not
claim that platform-level enforcement has already been installed.

## Adversarial evidence

The regression executes a modified candidate planner after deleting its own FULL guard
and replacing `ci_dependencies.select()` with an empty selection. Its own worker accepts
the resulting focused plan. A separately committed witness, run in a new isolated process,
rejects that same plan. A candidate `yaml.py` cannot enter the witness process. Additional
tests cover source/pin drift, missing authority files, syntax/mode changes, scalar types,
stale bases, merge binding, digest tampering and malformed artifact inputs.
