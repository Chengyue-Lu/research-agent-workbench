# M14-005 first-candidate diagnostic

PR #115 was cross-owner approved on exact head and normally squash-merged to
`develop@cebae4b3d9116d750b5573afce77a3e0bfd2b12f`. Its actual protected
push CI run 36791544994 and clean-source live attestation passed.

The first release candidate was built independently from frozen source Git blobs
and current main parent. Source-owned preflight, public check and local Python
3.13 package install passed. Draft PR #116 produced successful hosted release
preflight on Python 3.11 and 3.13. Its merge-ref workflow and checker bytes matched
the source. Fresh ruleset/effective-rule reads and the read-only cutover preparer
passed. No release protection, main, tag or publication was changed.

An independent governance replay found that curated candidates correctly omit
development-only TASKS and workstream documents, while the checker still tried to
read them from the candidate. The new develop-side correction routes these reads
through a prerequisite-validated source and preserves fail-closed behavior for
missing or invalid trust inputs. The candidate must be rebuilt after correction
acceptance and actual protected source CI; draft PR #116 is diagnostic evidence.

The visible interactive call stream was not completely captured. This archive
records capture gaps instead of fabricating a complete event trace. Review and
integration status are tracked by the feature PR and its exact-head checks.
