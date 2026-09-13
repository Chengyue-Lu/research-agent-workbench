# Portable Runtime resources

Task: [M14-003](../TASKS.md). Authority: [ADR-0021](../decisions/0021-CURATED-DEVELOP-TO-MAIN-RELEASE.md).

The [build backend](../../build_backend.py) generates a package-owned `RuntimeResourceManifest` from
[explicit catalog classes](../../runtime-resources.json). It includes published Schemas, Mode/Action,
Authority, Capability Requirement, Protocol Profile, Projection index and a no-Skill structural Task.
The manifest records each logical path, installed path, class, byte size and SHA-256. Its SHA-256 is pinned
separately in generated package code. Both the direct wheel and sdist-to-wheel build use the same source bytes.
Editable installs run the same generator; generated assets are local build outputs, with no checkout fallback.

## Roots and loading

| Root | Input and ownership |
|---|---|
| Project/filesystem | Explicit user documents and outputs; `rwb validate <paths> --root <project>` retains filesystem semantics |
| Runtime resources | Package-owned default, or an absolute override plus its externally supplied manifest SHA-256 |
| Integration config | Explicit platform configuration root; Codex files are read only through this input |

`SchemaCatalog()`, `CapabilityRequirementSet.load()`, `ProtocolProfileSet.load()` and
`SkillReleaseProjectionSet.load()` use packaged defaults. Explicit repository loaders retain their
`project_root` argument; Requirement loading uses the packaged Schema independently of that root.
`RuntimeResources.documents(kind)` supplies validated Mode, Action, Authority and other public catalog inputs.
The resource resolver does not consult CWD or environment variables. Python module selection remains the host's
responsibility; the clean-install Gate verifies imports originate in the installed environment.

The Phase C fresh actor loads the pinned Schema catalog before installing its data-read policy and
passes that in-memory catalog through document and Method Trace validation. Its guarded read surface
continues to include only staged case inputs and trusted Schemas; other Runtime catalog files remain blocked.

```shell
rwb resources check
rwb resources quickstart --output ./project/task.yaml
rwb validate ./project/task.yaml --root ./project
rwb resources check --runtime-root /absolute/resources --manifest-sha256 <trusted-digest>
```

The quickstart copies the wheel-owned Task bytes into a new output file and performs structural validation.
It does not run a research task or establish a Provider binding. The production Projection index is empty.

Maintainer commands require explicit inputs: `skills accepted --root`, `skills candidates --registry`,
`skills audit-archive --registry`, `skills eval assess --root --registry`, `providers list --registry`,
`providers probe/conformance --config`, and `models probe --config`. `runtime codex validate` requires
`--integration-root` (`--root` remains an explicit alias). `runtime codex render` takes separate `--root`
and `--integration-root` arguments for repository Skill resolution and platform configuration.

## Installed validation and conditional Skill assets

The installed-runtime validator checks the manifest pin, strict Schema, portable/casefold-safe paths,
file closure, bytes, hashes, index identities and references. Missing, corrupt, linked, reparse, extra,
orphan and unindexed resources fail closed. Mode/Action references must resolve to the same Mode identity.
Resource hashes are checked when read; a damaged install cannot borrow a missing file from a checkout.

Nonempty Projection indexes require exact immutable Skill manifest and package bytes. The manifest maps
their original logical paths into a controlled `releases/` namespace. The checker reconstructs package hashes
from logical relative names and exact bytes, verifies Projection/index/manifest identities and hashes, and
rejects unreferenced Skill assets. Individual release assets are enumerated in `release_assets`; the sdist
includes those exact source files. Legacy selectors, candidate/evaluation/lifecycle history, Provider baselines
and broad `.agents`/`.codex` roots are absent from the default resource catalog.

Repository publication validation continues to own Lifecycle, Evaluation, Human Decision and license/admission
truth. Installed validation consumes published bytes and does not reread that history or grant admission.
M14-005 continues to own release readiness and topology activation.
Curated surface policy `1.1.0` includes `build_backend.py`, `runtime-resources.json` and the declared
no-Skill input alongside the existing catalog classes. M14-004 checks this build-input closure together with
public navigation; the original M14-002 engineering policy version remains immutable. The structural Quickstart
now has a reusable [project scaffold](PROJECT_SCAFFOLD.md) with local Task/Profile inputs and an explicit Runtime pin;
the final M14-004 Quickstart acceptance remains a separate integration step.

## Verification

[Resource regressions](../../tests/test_runtime_resources.py) cover normal and malicious resource closures,
explicit roots, default poisoning and a synthetic nonempty Projection with logical-to-installed mapping.
The module is a critical 95% line / 90% branch surface in [Coverage Policy](../../tests/coverage_policy.yaml).

[Portable package smoke](../../.github/scripts/portable_package_smoke.py) builds both distribution routes,
compares every Runtime resource byte, installs each into fresh environments outside the checkout, and tests
isolated imports plus poisoned CWD/catalog search paths. Python 3.11 and 3.13 load all public catalog classes,
copy and validate the packaged no-Skill Task, and reject a corrupted installation. The existing repository
package smoke and full behavioral/coverage Gates remain required.
