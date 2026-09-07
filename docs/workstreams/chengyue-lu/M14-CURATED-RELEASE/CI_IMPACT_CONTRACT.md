# Proposed M14 release-surface CI consumer contract

Accountable owner: Chengyue-Lu. Status: proposed for cross-owner review on the isolated M14 acceptance branch. This declaration becomes selection authority only after it is accepted into a PR's base; candidate-side metadata cannot grant itself an exclusion.

The bounded executable is `.github/scripts/release_surface.py`. It implements the standalone frozen-Git export/check tool. Repository references identify its release-policy inclusion and `tests/test_release_surface.py` consumer. Installed Runtime resources, public package entrypoints and Provider/API execution do not import this helper. The release-surface test module exercises the whole export/check behavior and the critical policy's positive/negative acceptance inventory.

The contract selects the complete `test_release_surface` module, retains `.github/scripts/release_surface.py` as a critical impact-coverage subject, and keeps all existing shared impact-policy positive/negative IDs as explicit selected tests. Those shared IDs are six lightweight Provider methods; they do not require selecting the complete Provider suites. Global 90%, critical whole-file 95/90 and changed statement/outgoing branch 100/100 thresholds are unchanged.

The accepted base-side fingerprint binds the existing consumer inventory. A subsequent leaf change may use this boundary only while imports and the reviewed consumers remain unchanged. New/changed consumers add their downstream closure, an import change restores conservative dynamic consumers, and a missing fingerprint anchor retains the conservative graph. Selection-authority source edits still require the independently witnessed full behavioral floor.

`package_smoke=false` and `repository_smoke=false` describe a leaf-only change under this contract: the exporter checker is not installed Runtime code and does not change the repository schema/registry validator. Changes to those other surfaces retain their own obligations. Release-policy inputs, schemas, Runtime resources and publication integration are outside this single-file leaf declaration and continue through their own dependency analysis.

Acceptance must include a real Git candidate changing only the digest function, verified plan and selected test inventory, an actual passing impact run with both coverage checkers' applicable assertions, and rejection of a constant-zero digest by the selected tests. The result must distinguish this proposed-base experiment from hosted wall-clock savings. No release or merge authority is enabled by this contract.
