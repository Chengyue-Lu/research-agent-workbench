# Deterministic release surface

Owner: 路诚钺 (`Chengyue-Lu`). Contract: [ADR-0021](../decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md).
Task: [M14-002](../TASKS.md). Risk and review: [M14 workstream](../workstreams/chengyue-lu/M14-CURATED-RELEASE/README.md).

## Inputs and trust

`.github/scripts/release_surface.py` exports a staging tree or checks a generated candidate commit. Both operations
call the same projection function. The caller supplies an independent expectations document containing exact
repository, frozen source commit, current-main parent commit, policy version, release version and source-CI evidence.
The candidate manifest is never an expectations source. The caller must observe/fetch current remote refs and obtain
authentic CI evidence; this offline checker validates their binding and structure. M14-005 owns hosted attestation,
freshness, release readiness and topology activation.

The checker requires a complete SHA-1 Git repository, a clean tracked/untracked working tree, matching GitHub origin,
source ancestry in `refs/remotes/origin/develop`, and exact `refs/remotes/origin/main` equality to the expected parent.
Git replacement objects are disabled. Ignored source files are never read or selected: selection reads only frozen
Git objects. A changed working checkout cannot supply bytes to an export.

The trusted executable and its two Schema files must be byte-identical to those in the source commit. Install/use
the checker belonging to that source version; a candidate cannot supply a different generator implementation. No
policy entry can execute a command or select an arbitrary generator. The built-in `rwb-release-metadata@1.0.0`
generator emits canonical JSON from a closed set of source/parent/release/policy inputs and a bounded label.

## Policy and byte closure

The [policy](../../.github/release-surface.yml) is strict JSON, a subset of YAML, to avoid duplicate mapping keys,
aliases and implementation-dependent YAML coercions. Its [Schema](../../schemas/v0.1.0/release-surface-policy.schema.json)
permits only an ordered list of immutable policy versions. Every version visible anywhere in the source commit's
policy history must remain present with identical semantics. New versions append; removal, identity replacement
or a same-version rewrite fails. Comments and formatting are not a second policy input.

Includes use exact `file` or `tree` entries, with no glob interpretation. Every include must exist and have an
unambiguous kind; duplicate or overlapping selection fails. Broad `registry`, `.agents` and `.codex` roots are
rejected. The initial policy names individual Runtime catalog classes. Its source includes full product code and
Schemas, package metadata, `.gitattributes` and selected stable documents; public navigation and installed Runtime
closure remain owned by M14-004 and M14-003 respectively. This policy is an engineering projection baseline.

Paths must be relative POSIX, NFC-normalized and portable to Windows. Escape, empty/dot components, reserved device
names, trailing dots/spaces, casefold collisions (including directory prefixes), symlinks and gitlinks fail closed.
Selected UTF-8 text must use LF. Binary data is copied byte-for-byte. Each source output pins Git blob OID, mode,
size and SHA-256; generated outputs additionally pin generator identity/version/source hash and every input.

The [manifest Schema](../../schemas/v0.1.0/release-manifest.schema.json) closes source/parent trees, policy bytes,
excluded paths and every output. JSON uses UTF-8, LF, stable key/path sorting and no timestamps or random values.
`RELEASE_MANIFEST.json` is emitted last as an explicit special case: it does not contain its own hash or the final
tree hash. The checker reconstructs its canonical bytes and includes them when computing the complete Git tree.
The export/check result supplies the external manifest hash and full tree OID, without a self-reference cycle.

## Staging and prospective merge

`export` requires an existing empty absolute staging directory outside the source checkout. It creates all output
files exclusively, preserving bytes and executable modes where supported. It never overlays an old release tree.
The downstream caller must use the entire generated tree when creating a candidate with exactly the current-main
parent. Tests exercise that integration through an independent temporary Git index and `commit-tree` oracle.

`check` reconstructs selection, exclusions, generated outputs and manifest from the external expectations. It checks
candidate paths, blob identities, modes and bytes, then verifies the complete tree and Git's prospective merge tree.
Merge scratch objects go to a temporary object directory. The candidate must have one direct parent equal to the
expected current main; source is a content/provenance input, not a Git parent. A moving main invalidates the old
candidate. Consecutive release fixtures prove that an output present only in v1 is absent from v2 and its merge tree.

An optional staging-directory check also detects hidden/extra/empty directories, missing files, byte conversion and
symlinks/junctions. Windows filesystem executable bits are not authoritative; exact candidate Git modes are always
checked. Git object checks remain independent of working-tree line-ending conversion.

## Maintainer interface

Run from the repository's trusted source version, with caller-owned paths:

```text
python .github/scripts/release_surface.py export --repo <source-checkout> --expectations <trusted-input.json> --output <empty-absolute-staging>
python .github/scripts/release_surface.py check --repo <source-checkout> --expectations <trusted-input.json> --candidate <exact-commit> --directory <staging>
```

The expectations shape is `$defs.expectations` in the manifest Schema. Source CI is the `CI` workflow with a positive
run ID, the exact source/repository, success conclusion and all required governance/Python checks. Supplying these
fields does not prove their GitHub authenticity; protected-caller wiring remains a release-readiness prerequisite.

Both successful commands report `merge_eligible: false`. They do not create branches, commits, tags or remote
effects. M14-001 governance continues to reject all curated-release attempts until M14-005 cutover.

## Verification

`tests/test_release_surface.py` uses isolated Git repositories with synthetic release inputs. It independently
checks Git tree equality, repeated export, consecutive versions, source/generated provenance and rejection of
path/mode/byte/hash/history/parent attacks. No fixture source SHA is a real release freeze. Coverage Policy includes
the checker as a critical module with independent positive/negative evidence and line/branch gates of 95/90.
